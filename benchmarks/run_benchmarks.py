"""
Performance benchmark runner for Quantitative Market Data & Historical Replay Infrastructure.
"""

import argparse
import os
import platform
import sys
import tempfile
import time
import tracemalloc

from benchmarks.dataset_generator import write_synthetic_dataset_csv, write_synthetic_dataset_jsonl
from src.pipeline import MarketDataPipeline
from src.replay.engine import ReplayEngine
from src.storage.sqlite_store import SqliteStorageBackend


def run_benchmark(num_events: int = 100_000, dataset_format: str = "jsonl") -> dict:
    tracemalloc.start()
    temp_dir = tempfile.mkdtemp()
    temp_data_file = os.path.join(temp_dir, f"benchmark_data.{dataset_format}")
    temp_db_file = os.path.join(temp_dir, "benchmark.db")

    try:
        print(f"[*] Generating {num_events:,} synthetic events ({dataset_format})...")
        t0 = time.perf_counter()
        if dataset_format == "csv":
            write_synthetic_dataset_csv(temp_data_file, num_events=num_events)
        else:
            write_synthetic_dataset_jsonl(temp_data_file, num_events=num_events)
        gen_time = time.perf_counter() - t0
        print(f"    Generation completed in {gen_time:.2f}s ({num_events / gen_time:,.0f} events/s)")

        file_size_mb = os.path.getsize(temp_data_file) / (1024 * 1024)

        # 1. Pipeline Ingestion + Normalization + Validation + Storage
        print(f"[*] Executing End-to-End Pipeline on {num_events:,} events...")
        storage = SqliteStorageBackend(temp_db_file)
        pipeline = MarketDataPipeline(storage=storage)

        t_start = time.perf_counter()
        manifest = pipeline.process_file(temp_data_file)
        t_pipeline = time.perf_counter() - t_start

        pipeline_throughput = num_events / t_pipeline if t_pipeline > 0 else 0
        print(f"    Pipeline completed in {t_pipeline:.2f}s ({pipeline_throughput:,.0f} events/s)")

        # 2. Historical Replay Stream
        print(f"[*] Executing Deterministic Replay Stream...")
        replay_engine = ReplayEngine(storage)
        t_replay_start = time.perf_counter()
        replayed_count = 0
        for _ in replay_engine.replay_stream("AAPL", 0, 2**63 - 1):
            replayed_count += 1
        t_replay = time.perf_counter() - t_replay_start
        replay_throughput = replayed_count / t_replay if t_replay > 0 else 0
        print(f"    Replay completed in {t_replay:.2f}s ({replay_throughput:,.0f} events/s, total {replayed_count:,} events)")

        current_mem, peak_mem = tracemalloc.get_traced_memory()
        peak_mem_mb = peak_mem / (1024 * 1024)
        db_size_mb = os.path.getsize(temp_db_file) / (1024 * 1024)

        storage.close()

        results = {
            "num_events": num_events,
            "format": dataset_format,
            "raw_file_size_mb": file_size_mb,
            "db_size_mb": db_size_mb,
            "pipeline_time_s": t_pipeline,
            "pipeline_throughput_eps": pipeline_throughput,
            "replay_time_s": t_replay,
            "replay_throughput_eps": replay_throughput,
            "peak_memory_mb": peak_mem_mb,
            "python_version": platform.python_version(),
            "platform": platform.platform(),
            "processor": platform.processor() or platform.machine(),
            "manifest": manifest.to_dict(),
        }

        return results

    finally:
        tracemalloc.stop()
        if os.path.exists(temp_data_file):
            os.remove(temp_data_file)
        if os.path.exists(temp_db_file):
            os.remove(temp_db_file)
        if os.path.exists(temp_dir):
            try:
                os.rmdir(temp_dir)
            except Exception:
                pass


def main():
    parser = argparse.ArgumentParser(description="P01 Performance Benchmark Runner")
    parser.add_argument("--count", type=int, default=100000, help="Number of events to benchmark (e.g. 100000 or 1000000)")
    parser.add_argument("--format", choices=["jsonl", "csv"], default="jsonl", help="Dataset format")
    args = parser.parse_args()

    results = run_benchmark(num_events=args.count, dataset_format=args.format)

    print("\n" + "=" * 60)
    print("BENCHMARK EXECUTION REPORT")
    print("=" * 60)
    print(f"Platform:              {results['platform']}")
    print(f"Processor:             {results['processor']}")
    print(f"Python Version:        {results['python_version']}")
    print(f"Workload Event Count:  {results['num_events']:,}")
    print(f"Raw Input Size:        {results['raw_file_size_mb']:.2f} MB")
    print(f"Database Stored Size:  {results['db_size_mb']:.2f} MB")
    print(f"Peak Memory (RSS):     {results['peak_memory_mb']:.2f} MB")
    print("-" * 60)
    print(f"Pipeline Throughput:   {results['pipeline_throughput_eps']:,.0f} events/sec ({results['pipeline_time_s']:.2f}s)")
    print(f"Replay Throughput:     {results['replay_throughput_eps']:,.0f} events/sec ({results['replay_time_s']:.2f}s)")
    print("=" * 60)


if __name__ == "__main__":
    main()
