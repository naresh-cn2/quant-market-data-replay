# Quantitative Microstructure Analytics & Visual Reporting Engine

## Overview

The Quantitative Microstructure Analytics and Visual Reporting Engine provides standalone, publication-grade analytical reporting directly on top of the deterministic historical market replay stream.

In strict alignment with the core project invariants:
- **Zero Binary Floating-Point Contamination**: All prices, volumes, notional amounts, spreads, and execution benchmarks are computed using exact arbitrary-precision `Decimal` arithmetic.
- **64-bit Integer UTC Nanoseconds**: All packet intervals, ordering guarantees, and latency distribution percentiles are calculated using integer nanosecond arithmetic.
- **Zero External Runtime Dependencies**: All charts are rendered natively using pure Python standard-library vector SVG generation without npm, Matplotlib, Plotly, or third-party CDNs. Reports are entirely self-contained HTML5 single files that open offline in any browser.

---

## Microstructure Metrics Formulation

### 1. Cumulative Volume-Weighted Average Price (VWAP)

For a sequence of trade fills $(P_1, V_1), (P_2, V_2), \dots, (P_t, V_t)$:

$$\text{VWAP}_t = \frac{\sum_{i=1}^t P_i \cdot V_i}{\sum_{i=1}^t V_i}$$

- Preserves exact decimal precision throughout the running summation.
- Serves as the primary institutional execution quality benchmark against individual fill prices.

### 2. Quoted and Relative Spread Dynamics

For a Top-of-Book Best Bid and Offer (BBO) quote $(P_t^{\text{bid}}, P_t^{\text{ask}})$:

$$\text{Quoted Spread}_t = P_t^{\text{ask}} - P_t^{\text{bid}}$$

$$\text{Midpoint}_t = \frac{P_t^{\text{bid}} + P_t^{\text{ask}}}{2}$$

$$\text{Relative Spread (bps)}_t = \frac{\text{Quoted Spread}_t}{\text{Midpoint}_t} \times 10{,}000$$

- **Crossed Quote Detection**: Highlights anomalous market states where $P_t^{\text{bid}} > P_t^{\text{ask}}$ (negative spread).
- **Locked Quote Detection**: Identifies states where $P_t^{\text{bid}} = P_t^{\text{ask}}$.

### 3. Cumulative Order Flow Imbalance Ratio (OFI)

Aggregates signed aggressor trade flow to measure buying versus selling pressure:

$$\text{OFI}_t = \frac{V_t^{\text{buy}} - V_t^{\text{sell}}}{V_t^{\text{buy}} + V_t^{\text{sell}}} \quad \in [-1.0, +1.0]$$

- $+1.0$: 100% buyer-initiated volume (strong buy pressure).
- $0.0$: Perfectly balanced two-sided execution.
- $-1.0$: 100% seller-initiated volume (strong sell pressure).

### 4. Inter-Arrival Latency and Jitter Distribution

For adjacent market events with timestamps $t_{i-1}$ and $t_i$:

$$\Delta t_i = \max(0, t_i - t_{i-1})$$

Calculates high-precision empirical percentiles across the feed:
- $p50$ (Median packet interval)
- $p90$ (90th percentile jitter)
- $p99$ (99th percentile tail latency risk)

---

## Visual Architecture

The visual engine produces standalone HTML5 documents featuring:

| Component | Description | Format |
|---|---|---|
| **Executive KPI Grid** | High-level summary cards (Cumulative Volume, Final VWAP, Mean Spread bps, Order Flow Imbalance, Median Jitter) | CSS Grid Card Layout |
| **Price & VWAP Trajectory** | Every trade fill plotted with side indicators (Green = Buy, Red = Sell) against continuous cumulative VWAP | Native Vector SVG |
| **Spread Dynamics** | Shaded area polygon illustrating relative spread expansion/compression with crossed-quote alerts | Native Vector SVG |
| **Order Flow Imbalance** | Zero-centered oscillator tracking directional volume dominance across replay time | Native Vector SVG |
| **Jitter Distribution** | Binned latency histogram annotated with vertical $p50$, $p90$, and $p99$ percentile markers | Native Vector SVG |
| **Microstructure Table** | Comprehensive tabular breakdown of all calculated metrics and unit invariant guarantees | Semantic HTML5 Table |

---

## CLI Usage

### Generate Microstructure Report

```bash
python main.py report --db market_data.db --symbol AAPL --output aapl_report.html
```

#### Optional Timestamp Filtering

Filter to a specific historical time window using ISO-8601 or epoch nanoseconds:

```bash
python main.py report \
  --db market_data.db \
  --symbol AAPL \
  --start "2026-09-16T10:00:00.000000000Z" \
  --end "2026-09-16T10:00:01.000000000Z" \
  --output aapl_window_report.html
```

---

## Programmatic API

```python
from src.analytics.report_generator import generate_market_report

summary = generate_market_report(
    db_path="market_data.db",
    symbol="AAPL",
    output_path="reports/aapl_analytics.html",
)

print(f"Total Volume: {summary.total_volume}")
print(f"Final VWAP:   ${summary.final_vwap}")
print(f"Mean Spread:  {summary.mean_relative_spread_bps:.2f} bps")
print(f"Median Delta: {summary.median_inter_arrival_ns / 1000.0:.1f} us")
```
