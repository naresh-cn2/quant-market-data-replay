# TOP1 P01 — Quantitative Market Data & Historical Replay Infrastructure
## System Specification v2.0

### Mission
Build a professional quantitative-finance research-data foundation:
RAW MARKET DATA -> INGESTION -> NORMALIZATION -> VALIDATION -> QUARANTINE -> STORAGE -> POINT-IN-TIME ACCESS -> DETERMINISTIC REPLAY.

### Module 01 integration
P01 is the sole flagship build for Module 01: AI-Native Quantitative Systems Engineering.
The project integrates quantitative reasoning, financial market-data concepts, systems engineering, testing, and AI-agent-driven development.

### Professional capabilities
- market-data modeling and event-driven architecture
- timestamp and ordering correctness
- exact monetary/quantity representation
- data-quality engineering and quarantine
- deterministic replay and point-in-time safety
- provenance, reproducibility and auditability
- testing, adversarial validation and benchmarking
- API/CLI and repository engineering
- polyglot engineering with justified language boundaries
- specification-driven AI-agent development

### V1 event families
TRADE and QUOTE.

### Input
CSV, JSON Lines, and JSON arrays where practical.

### Canonical TradeEvent
event_id, symbol, timestamp_ns (integer UTC nanoseconds), price (Decimal/fixed-point; never binary float in canonical state), size (Decimal/fixed-point), side (BUY/SELL/UNKNOWN), source.

### Canonical QuoteEvent
event_id, symbol, timestamp_ns, bid_price, bid_size, ask_price, ask_size, source.

### Core invariants
1. Canonical timestamps are integer UTC nanoseconds.
2. Canonical monetary and quantity values use Decimal/fixed-point, never binary float.
3. Invalid/non-positive values are explicitly classified and quarantined where applicable; never silently dropped.
4. Every accepted event has deterministic identity.
5. Equal timestamps have deterministic tie-breaking.
6. Reordering uses a bounded lateness window; no unrestricted global sort while claiming constant memory.
7. No future event may become visible to a historical replay state before its timestamp.
8. Identical dataset/config/version/range produces deterministic replay.
9. Raw-source evidence is preserved; normalization never silently mutates source truth.
10. Dataset provenance, schema/version, checksum and quality metadata are recorded.
11. Configuration affecting interpretation is versioned.
12. Failures are observable through structured diagnostics.

### Validation classification
At minimum:
- HARD_INVALID
- SOFT_WARNING
- ACCEPTED

A large price move is not automatically corruption. Distinguish unusual-but-valid observations from structurally invalid records.

### Replay
Required API concept:
replay_stream(symbol, start_ns, end_ns, event_types=("TRADE","QUOTE"))

Replay must be generator/iterator based, deterministic, point-in-time safe, and explicit about range semantics and equal-timestamp ordering.

### Architecture
raw -> ingestion -> normalization -> validation -> quarantine/storage -> manifest -> point-in-time access -> replay -> downstream research/backtest consumers.

### Language policy
Use multiple languages only where justified:
- Python: reference/orchestration/research tooling.
- SQL: metadata, indexing, inspection and analytical queries.
- Bash: reproducible workflows and CI.
- C++: only after a measured bottleneck justifies a performance prototype.
- JSON/YAML/TOML: schemas/configuration/provenance.
- Markdown: technical evidence.
- GitHub Actions YAML: CI.

Do not add languages for cosmetic complexity.

### Testing
Unit, integration, malformed-input, precision, timestamp-boundary, duplicate, out-of-order, reorder-window, point-in-time leakage, deterministic replay, quarantine-preservation, CLI and benchmark-smoke tests. No skipped assertions may hide incomplete work.

### Security
No secrets, credentials, live trading, real-money execution, or uncontrolled network dependency. Review dependencies.

### Benchmarking
Measure actual ingestion, normalization, validation, storage and replay throughput, memory, dataset size and environment. Never fabricate results. Correctness comes first.

### Definition of Done
Architecture, schemas, ingestion, validation/quarantine, deterministic identity, bounded reordering, storage/manifest, point-in-time replay, integration/adversarial tests, real benchmarks, documentation, and human verification gate all complete.
