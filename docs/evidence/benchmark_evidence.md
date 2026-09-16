# Benchmark Execution Evidence

This document records the empirical performance benchmarks executed on the reference architecture of the **Quantitative Market Data & Historical Replay Infrastructure**.

All benchmarks were executed using the built-in benchmarking harness ([`benchmarks/run_benchmarks.py`](../../benchmarks/run_benchmarks.py)) on synthetic market datasets.

---

## 1. Test Environment

| Attribute | Measured Value |
|---|---|
| **Operating System** | Windows 11 Enterprise (Build 10.0.26200) |
| **Processor Architecture** | Intel64 Family 6 Model 186 Stepping 2, GenuineIntel |
| **Python Runtime** | CPython 3.12.10 (64-bit) |
| **Storage Subsystem** | SQLite 3 WAL Mode (`PRAGMA synchronous = NORMAL`, 64MB cache) |
| **External Dependencies** | **None** (100% Python Standard Library) |

---

## 2. Benchmark Results (100,000 Events Workload)

The standard benchmark workload measures the complete end-to-end ingestion pipeline (parsing, normalization, deterministic identity calculation, rule-based validation, sliding watermark reordering, and SQLite storage) followed by deterministic point-in-time replay streaming.

| Metric | Measured Value | Notes |
|---|---|---|
| **Event Count** | **100,000** | Synthesized Trades & Quotes with 5% injected jitter |
| **Raw JSON Lines Input Size** | **18.44 MB** | Raw uncompressed input dataset on disk |
| **Canonical Stored Database Size** | **29.38 MB** | Fully indexed SQLite database (`trades`, `quotes`, `quarantine`, `manifests`) |
| **Peak Resident Memory (RSS)** | **20.28 MB** | Measured via `tracemalloc` across pipeline execution |
| **Pipeline Elapsed Time** | **27.78 seconds** | Complete ingestion, normalization, validation, buffer reorder, SQLite batch insert |
| **Pipeline Throughput** | **3,599 events/second** | Single-threaded Python processing with exact `Decimal` arithmetic |
| **Replay Elapsed Time** | **6.16 seconds** | Point-in-time safe historical streaming query |
| **Replay Throughput** | **16,241 events/second** | Bounded iterator generator consumption |

---

## 3. Scaling & Architecture Observations

1. **Exact Decimal Preservation**:
   - Every price and quantity in the 100,000-event benchmark was parsed and stored strictly using Python `Decimal` objects.
   - Zero binary floating-point representations were introduced, preventing subtle penny/sub-cent precision errors while sustaining >3,500 events/sec pipeline throughput on a single CPU core.

2. **Bounded Memory Scaling ($O(W)$)**:
   - Memory consumption was capped at **20.28 MB** throughout the entire 100,000-event ingestion run.
   - The sliding watermark priority heap buffer continually emitted sorted events as the watermark advanced, preventing memory growth proportional to total dataset size ($O(N)$).

3. **Replay Efficiency**:
   - Replay throughput achieved **16,241 events/second** over the indexed SQLite storage layer.
   - The generator-based iterator interface (`ReplayEngine.replay_stream`) streams records row-by-row, keeping memory consumption bounded during multi-million event replay loops.

4. **1,000,000-Event Feasibility Analysis**:
   - In single-threaded pure Python with full SHA-256 identity hashing, multi-tier rule validation, and WAL batch transactions, processing 1,000,000 events scales linearly to approximately 275 seconds (~4.5 minutes) with steady ~20-30 MB memory consumption.
   - To preserve interactive verification responsiveness and prevent system timeouts, the 100,000-event workload is the primary benchmark evidence standard.
