# Benchmark Methodology & Performance Measurement

## 1. Methodology
Performance measurements are taken using `benchmarks/run_benchmarks.py` across standardized synthetic workloads (100,000 and 1,000,000 events) featuring:
- Realistic price random walks.
- Realistic quote spreads and volume distributions.
- 5% injected out-of-order latency jitter (within a 500ms sliding window).
- Alternating trade and quote sequences.

## 2. Key Metrics Tracked
- **Pipeline Throughput**: End-to-end processing rate (events/second) through Ingestion -> Normalization -> Validation -> Bounded Reordering -> SQLite Storage Commit.
- **Replay Throughput**: Streaming extraction rate (events/second) from indexed database through PointInTimeGuard.
- **Peak Resident Memory (RSS)**: Measured using `tracemalloc` to confirm $O(1)$ constant/bounded memory scaling.
- **Data Footprint**: Raw payload size vs compressed/indexed database file size.
