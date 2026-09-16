# Architecture Specification — Project P01

## 1. Executive Summary

Project P01 is a deterministic, point-in-time safe market data foundation for quantitative research, backtesting, and simulation engines.

```
RAW MARKET DATA -> INGESTION -> NORMALIZATION -> VALIDATION -> QUARANTINE / STORAGE -> POINT-IN-TIME ACCESS -> DETERMINISTIC REPLAY
```

## 2. Core Architectural Pillars

### 2.1 Exact Numeric Representation (Zero Float Contamination)
Binary floating point types (`float`) cannot represent decimal fractions precisely (e.g., $0.1 + 0.2 \ne 0.3$). In quantitative market infrastructure, float errors cause rounding drift, invalid spread calculations, and corrupted execution fills. In P01, all canonical prices and quantities are strictly represented using `Decimal` or exact integer-scaled fixed point.

### 2.2 Strict Nanosecond UTC Timestamps
All timestamps are converted and stored as 64-bit integer nanoseconds since UNIX epoch (1970-01-01T00:00:00Z). Timestamps preserve sub-microsecond precision from exchange matching engines.

### 2.3 Bounded Event Reordering (Sliding Watermark)
Real-world market feeds experience packet jitter and out-of-order delivery. Unbounded in-memory sorting on massive datasets causes $O(N)$ memory exhaustion. P01 implements a bounded priority buffer (min-heap) governed by a configurable lateness watermark:
$$\text{Watermark} = \max(\text{Timestamp}_{\text{seen}}) - \text{MaxLateness}$$
Events older than the watermark threshold are routed to quarantine as `ERR_EXCESSIVE_LATENESS`, bounding memory consumption to $O(W)$.

### 2.4 Point-in-Time Historical Replay
Backtesting models must never look into the future. The replay engine exposes an iterator/generator interface enforcing $t_{\text{start}} \le \text{timestamp\_ns} \le t_{\text{end}}$ with monotonic non-decreasing event progression.

### 2.5 Data Quality & Quarantine Isolation
Invalid or corrupted records are never silently dropped. Non-compliant records are classified with structured diagnostic codes, packaged with unmutated raw source payloads into `QuarantineRecord` entities, and recorded in quarantine stores.
