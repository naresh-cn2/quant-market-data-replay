"""
Command-line interface for Quantitative Market Data & Historical Replay Infrastructure.
"""

import argparse
from decimal import Decimal
import json
import os
import sys
from typing import Optional

from src.ingestion import create_reader
from src.models.quarantine import QuarantineRecord
from src.normalization.normalizer import EventNormalizer
from src.pipeline import MarketDataPipeline
from src.primitives.timestamp import parse_timestamp_ns, format_timestamp_ns
from src.replay.engine import ReplayEngine
from src.storage.manifest_manager import ManifestManager
from src.storage.sqlite_store import SqliteStorageBackend
from src.validation.engine import MarketDataValidator
from src.validation.rules import MarketDataValidationRules
from src.analytics.report_generator import generate_market_report


def load_config(config_path: Optional[str]) -> dict:
    if config_path and os.path.exists(config_path):
        with open(config_path, "r", encoding="utf-8") as f:
            return json.load(f)
    default_cfg_path = os.path.join(os.path.dirname(__file__), "..", "..", "config", "default_config.json")
    if os.path.exists(default_cfg_path):
        with open(default_cfg_path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def cmd_ingest(args: argparse.Namespace) -> int:
    config = load_config(args.config)
    db_path = args.db or config.get("storage", {}).get("default_db_path", "market_data.db")
    storage = SqliteStorageBackend(db_path)

    pipeline = MarketDataPipeline(
        storage=storage,
        config=config,
        quarantine_file=args.quarantine_file,
    )

    print(f"[*] Ingesting file: {args.file} -> {db_path}...")
    manifest = pipeline.process_file(args.file, format_hint=args.format)

    print("\n[+] Ingestion Complete. Dataset Manifest:")
    print(json.dumps(manifest.to_dict(), indent=2))
    return 0


def cmd_validate(args: argparse.Namespace) -> int:
    config = load_config(args.config)
    reader = create_reader(args.file, format_hint=args.format)
    normalizer = EventNormalizer()
    rules = MarketDataValidationRules()
    validator = MarketDataValidator(rules)

    total_records = 0
    quarantine_count = 0
    warning_count = 0
    accepted_count = 0

    print(f"[*] Validating file: {args.file}...")

    for raw_record in reader.read_records():
        total_records += 1
        result = normalizer.normalize(raw_record)

        if isinstance(result, QuarantineRecord):
            quarantine_count += 1
            if args.verbose:
                print(f"  [HARD_INVALID] Line {raw_record.line_number}: {result.error_message}")
            continue

        val_res = validator.validate_event(result)
        if not val_res.is_valid:
            quarantine_count += 1
            if args.verbose:
                print(f"  [HARD_INVALID] Line {raw_record.line_number}: {val_res.diagnostics[0].message}")
        elif val_res.has_warnings:
            warning_count += 1
            accepted_count += 1
            if args.verbose:
                print(f"  [SOFT_WARNING] Line {raw_record.line_number}: {val_res.diagnostics[0].message}")
        else:
            accepted_count += 1

    print("\n[+] Validation Report:")
    print(f"  Total Records Processed: {total_records}")
    print(f"  Accepted Clean Events:   {accepted_count - warning_count}")
    print(f"  Accepted with Warnings:  {warning_count}")
    print(f"  Hard Invalids/Quarantine:{quarantine_count}")
    print(f"  Acceptance Rate:         {(accepted_count / total_records * 100) if total_records else 0:.2f}%")
    return 0


def cmd_replay(args: argparse.Namespace) -> int:
    storage = SqliteStorageBackend(args.db)
    engine = ReplayEngine(storage)

    try:
        start_ns = parse_timestamp_ns(args.start) if args.start else 0
        end_ns = parse_timestamp_ns(args.end) if args.end else (2**63 - 1)
    except Exception as e:
        print(f"[!] Invalid timestamp argument: {e}", file=sys.stderr)
        return 1

    event_types = tuple(t.strip().upper() for t in args.types.split(","))

    print(
        f"[*] Replaying symbol '{args.symbol}' from {format_timestamp_ns(start_ns)} to {format_timestamp_ns(end_ns)} (types: {event_types})...\n"
    )

    count = 0
    for event in engine.replay_stream(args.symbol, start_ns, end_ns, event_types):
        count += 1
        print(json.dumps(event.to_dict()))
        if args.limit and count >= args.limit:
            break

    print(f"\n[+] Replayed {count} events.")
    return 0


def cmd_manifest(args: argparse.Namespace) -> int:
    storage = SqliteStorageBackend(args.db)
    manifest = storage.get_manifest(args.dataset_id)
    if not manifest:
        print(f"[!] Manifest not found for dataset ID: {args.dataset_id}", file=sys.stderr)
        return 1

    print(json.dumps(manifest.to_dict(), indent=2))

    if args.verify:
        is_valid = ManifestManager.verify_manifest(manifest, args.file)
        if is_valid:
            print("[+] Checksum verification PASSED.")
        else:
            print("[!] Checksum verification FAILED.", file=sys.stderr)
            return 1
    return 0


def cmd_report(args: argparse.Namespace) -> int:
    try:
        start_ns = parse_timestamp_ns(args.start) if args.start else 0
        end_ns = parse_timestamp_ns(args.end) if args.end else (2**63 - 1)
    except Exception as e:
        print(f"[!] Invalid timestamp argument: {e}", file=sys.stderr)
        return 1

    print(f"[*] Generating quantitative market report for {args.symbol} from {args.db}...")
    try:
        summary = generate_market_report(
            db_path=args.db,
            symbol=args.symbol,
            output_path=args.output,
            start_ns=start_ns,
            end_ns=end_ns,
        )
    except Exception as e:
        print(f"[!] Report generation failed: {e}", file=sys.stderr)
        return 1

    print(f"\n[+] Microstructure Report Generated: {args.output}")
    print(f"  Symbol:                {summary.symbol}")
    print(f"  Total Ingested Events: {summary.total_events:,} (Trades: {summary.trade_count:,}, Quotes: {summary.quote_count:,})")
    print(f"  Total Volume Traded:   {summary.total_volume}")
    print(f"  Final Execution VWAP:  ${summary.final_vwap:.4f}")
    print(f"  Mean Relative Spread:  {summary.mean_relative_spread_bps:.2f} bps")
    print(f"  Volume Imbalance:      {float(summary.volume_imbalance_ratio) * 100:+.2f}%")
    med_us = summary.median_inter_arrival_ns / 1000.0
    p99_us = summary.p99_inter_arrival_ns / 1000.0
    print(f"  Inter-Arrival Latency: Median: {med_us:.1f}us | p99: {p99_us:.1f}us")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="market-replay",
        description="Quantitative Market Data & Historical Replay Infrastructure",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # Ingest
    p_ingest = subparsers.add_parser("ingest", help="Ingest raw market data file into canonical storage")
    p_ingest.add_argument("--file", required=True, help="Path to raw CSV or JSONL market data file")
    p_ingest.add_argument("--db", default=None, help="Path to SQLite database file")
    p_ingest.add_argument("--format", default=None, choices=["csv", "jsonl", "json"], help="Force format")
    p_ingest.add_argument("--quarantine-file", default=None, help="Path to output quarantine JSONL")
    p_ingest.add_argument("--config", default=None, help="Path to engine config JSON")
    p_ingest.set_defaults(func=cmd_ingest)

    # Validate
    p_val = subparsers.add_parser("validate", help="Validate raw market data without database mutation")
    p_val.add_argument("--file", required=True, help="Path to raw CSV or JSONL market data file")
    p_val.add_argument("--format", default=None, choices=["csv", "jsonl", "json"], help="Force format")
    p_val.add_argument("--config", default=None, help="Path to engine config JSON")
    p_val.add_argument("-v", "--verbose", action="store_true", help="Print per-record diagnostics")
    p_val.set_defaults(func=cmd_validate)

    # Replay
    p_rep = subparsers.add_parser("replay", help="Replay historical market data deterministically")
    p_rep.add_argument("--db", required=True, help="Path to SQLite database file")
    p_rep.add_argument("--symbol", required=True, help="Ticker symbol (e.g. AAPL)")
    p_rep.add_argument("--start", default=None, help="Start timestamp (ISO-8601 or epoch ns)")
    p_rep.add_argument("--end", default=None, help="End timestamp (ISO-8601 or epoch ns)")
    p_rep.add_argument("--types", default="TRADE,QUOTE", help="Comma-separated event types (TRADE,QUOTE)")
    p_rep.add_argument("--limit", type=int, default=None, help="Maximum events to output")
    p_rep.set_defaults(func=cmd_replay)

    # Manifest
    p_man = subparsers.add_parser("manifest", help="View or verify dataset manifest")
    p_man.add_argument("--db", required=True, help="Path to SQLite database file")
    p_man.add_argument("--dataset-id", required=True, help="Dataset ID to inspect")
    p_man.add_argument("--verify", action="store_true", help="Verify checksum against source file")
    p_man.add_argument("--file", default=None, help="Source file override for checksum verification")
    p_man.set_defaults(func=cmd_manifest)

    # Report
    p_rep_gen = subparsers.add_parser("report", help="Generate quantitative microstructure visual HTML report")
    p_rep_gen.add_argument("--db", required=True, help="Path to SQLite database file")
    p_rep_gen.add_argument("--symbol", required=True, help="Ticker symbol to analyze (e.g. AAPL)")
    p_rep_gen.add_argument("--output", default="market_report.html", help="Path to output HTML report file")
    p_rep_gen.add_argument("--start", default=None, help="Start timestamp (ISO-8601 or epoch ns)")
    p_rep_gen.add_argument("--end", default=None, help="End timestamp (ISO-8601 or epoch ns)")
    p_rep_gen.set_defaults(func=cmd_report)

    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
