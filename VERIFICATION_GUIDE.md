# Engineering Verification Guide

## Automated Verification

Run the comprehensive test suite:
```bash
python -m unittest discover tests
```

Record exact test count, failures, errors, and skips.

Run sample CLI validation:
```bash
python main.py validate --file tests/fixtures/sample_trades.csv -v
```

Run quantitative microstructure visual report generation:
```bash
python main.py ingest --file tests/fixtures/sample_trades.csv --db sample_market.db
python main.py ingest --file tests/fixtures/sample_quotes.csv --db sample_market.db
python main.py report --db sample_market.db --symbol AAPL --output sample_aapl_report.html
```

Run performance benchmark verification:
```bash
python -m benchmarks.run_benchmarks --count 100000 --format jsonl
```

## Manual Architecture & Code Audit

Verify against system specifications:
- Canonical price and size representations use `Decimal` or exact fixed-point (zero binary `float` in canonical state).
- Canonical timestamps are strict integer nanoseconds in UTC.
- Invalid or non-positive values are quarantined with unmutated raw payloads preserved, never silently dropped.
- Warnings (`SOFT_WARNING`) are distinguished from hard invalid rejections (`HARD_INVALID`).
- Replay stream uses generator/iterator consumption for bounded memory scaling.
- Point-in-time safety is strictly enforced: no event with $t > t_{\text{current}}$ leaks into historical replay state.
- Equal timestamps follow deterministic tie-breaking.
- Bounded out-of-order reordering is enforced via a sliding watermark priority buffer.
- Dataset provenance, manifests, cryptographic SHA-256 checksums, and versioned configuration hashes exist.
- Performance benchmark numbers are real, measured, and reproducible.
- Zero secrets, API keys, or live execution/trading integrations exist in the codebase.
- Architecture, data flow, and failure handling modes can be defended.
