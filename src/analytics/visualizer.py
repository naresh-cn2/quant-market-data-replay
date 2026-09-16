"""
HTML5 Quantitative Market Report visualizer.

Generates self-contained, high-resolution dark-mode analytical reports
with embedded vector SVG charts and KPI cards.
"""

from decimal import Decimal
from typing import Optional

from src.analytics.metrics import MicrostructureSummary
from src.analytics.svg_charts import (
    render_jitter_distribution_svg,
    render_price_vwap_svg,
    render_spread_dynamics_svg,
    render_volume_imbalance_svg,
)
from src.primitives.numeric import format_decimal


def _fmt_dec(val: Decimal, places: int = 2) -> str:
    """Format Decimal with thousands separator and specific precision."""
    if val is None:
        return "0"
    if places == 0:
        return f"{val:,.0f}"
    return f"{val:,.{places}f}"


def generate_html_report(
    summary: MicrostructureSummary,
    db_path: str = "market_data.db",
) -> str:
    """
    Renders an end-to-end self-contained HTML5 market microstructure report.
    """
    vwap_svg = render_price_vwap_svg(summary.vwap_points, summary.symbol)
    spread_svg = render_spread_dynamics_svg(summary.spread_points, summary.symbol)
    imbalance_svg = render_volume_imbalance_svg(summary.imbalance_points, summary.symbol)
    jitter_svg = render_jitter_distribution_svg(
        summary.inter_arrival_deltas_us,
        summary.median_inter_arrival_ns,
        summary.p90_inter_arrival_ns,
        summary.p99_inter_arrival_ns,
        summary.symbol,
    )

    # Calculate percentages and formatting
    imb_ratio_val = float(summary.volume_imbalance_ratio)
    imb_color = "#00E676" if imb_ratio_val > 0.05 else ("#FF5252" if imb_ratio_val < -0.05 else "#94A3B8")
    imb_pct = imb_ratio_val * 100.0

    min_us = summary.min_inter_arrival_ns / 1000.0
    med_us = summary.median_inter_arrival_ns / 1000.0
    p90_us = summary.p90_inter_arrival_ns / 1000.0
    p99_us = summary.p99_inter_arrival_ns / 1000.0
    max_us = summary.max_inter_arrival_ns / 1000.0

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{summary.symbol} Quantitative Market Report</title>
  <style>
    :root {{
      --bg-dark: #0B0E14;
      --card-bg: #111622;
      --card-border: #1E2638;
      --text-main: #F0F4F8;
      --text-muted: #8E9AA8;
      --accent-blue: #00B0FF;
      --accent-green: #00E676;
      --accent-red: #FF5252;
      --accent-purple: #7C4DFF;
      --font-mono: "SF Mono", "Consolas", "Liberation Mono", Menlo, Courier, monospace;
      --font-sans: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
    }}
    * {{
      box-sizing: border-box;
      margin: 0;
      padding: 0;
    }}
    body {{
      background-color: var(--bg-dark);
      color: var(--text-main);
      font-family: var(--font-sans);
      line-height: 1.5;
      padding: 32px 24px;
      -webkit-font-smoothing: antialiased;
    }}
    .container {{
      max-width: 1200px;
      margin: 0 auto;
    }}
    header {{
      display: flex;
      flex-wrap: wrap;
      justify-content: space-between;
      align-items: flex-end;
      padding-bottom: 24px;
      border-bottom: 1px solid var(--card-border);
      margin-bottom: 32px;
      gap: 16px;
    }}
    .header-title h1 {{
      font-size: 28px;
      font-weight: 700;
      letter-spacing: -0.5px;
      color: #FFFFFF;
      display: flex;
      align-items: center;
      gap: 12px;
    }}
    .symbol-tag {{
      background: rgba(0, 176, 255, 0.12);
      color: var(--accent-blue);
      padding: 4px 12px;
      border-radius: 6px;
      font-size: 18px;
      font-weight: 600;
      border: 1px solid rgba(0, 176, 255, 0.3);
    }}
    .header-subtitle {{
      color: var(--text-muted);
      font-size: 14px;
      margin-top: 6px;
    }}
    .badges {{
      display: flex;
      gap: 8px;
      flex-wrap: wrap;
    }}
    .badge {{
      background: #182030;
      color: #94A3B8;
      font-size: 12px;
      font-weight: 500;
      padding: 4px 10px;
      border-radius: 4px;
      border: 1px solid #232E45;
    }}
    .grid-kpi {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
      gap: 16px;
      margin-bottom: 32px;
    }}
    .kpi-card {{
      background: var(--card-bg);
      border: 1px solid var(--card-border);
      border-radius: 8px;
      padding: 20px;
      position: relative;
      overflow: hidden;
      transition: transform 0.2s ease, border-color 0.2s ease;
    }}
    .kpi-card:hover {{
      border-color: #2D3A54;
      transform: translateY(-2px);
    }}
    .kpi-label {{
      color: var(--text-muted);
      font-size: 12px;
      text-transform: uppercase;
      letter-spacing: 0.8px;
      font-weight: 600;
      margin-bottom: 8px;
    }}
    .kpi-value {{
      font-size: 24px;
      font-weight: 700;
      font-family: var(--font-mono);
      color: #FFFFFF;
    }}
    .kpi-subtext {{
      color: var(--text-muted);
      font-size: 12px;
      margin-top: 6px;
      font-family: var(--font-sans);
    }}
    .chart-section {{
      display: flex;
      flex-direction: column;
      gap: 24px;
      margin-bottom: 32px;
    }}
    .chart-card {{
      background: var(--card-bg);
      border: 1px solid var(--card-border);
      border-radius: 8px;
      padding: 16px;
    }}
    .chart-header {{
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 12px;
      padding: 0 8px;
    }}
    .chart-title {{
      font-size: 15px;
      font-weight: 600;
      color: #F8FAFC;
    }}
    .chart-description {{
      font-size: 12px;
      color: var(--text-muted);
    }}
    .stats-table-card {{
      background: var(--card-bg);
      border: 1px solid var(--card-border);
      border-radius: 8px;
      padding: 24px;
      margin-bottom: 32px;
    }}
    .stats-table-title {{
      font-size: 16px;
      font-weight: 600;
      margin-bottom: 16px;
      color: #F8FAFC;
    }}
    table {{
      width: 100%;
      border-collapse: collapse;
      font-size: 13px;
    }}
    th {{
      text-align: left;
      padding: 10px 12px;
      color: var(--text-muted);
      border-bottom: 1px solid var(--card-border);
      text-transform: uppercase;
      font-size: 11px;
      letter-spacing: 0.5px;
    }}
    td {{
      padding: 12px;
      border-bottom: 1px solid #161D2C;
      font-family: var(--font-mono);
    }}
    tr:last-child td {{
      border-bottom: none;
    }}
    footer {{
      margin-top: 48px;
      padding-top: 20px;
      border-top: 1px solid var(--card-border);
      display: flex;
      justify-content: space-between;
      font-size: 12px;
      color: #64748B;
    }}
  </style>
</head>
<body>
  <div class="container">
    <header>
      <div class="header-title">
        <h1>Microstructure Report <span class="symbol-tag">{summary.symbol}</span></h1>
        <div class="header-subtitle">Deterministic Quantitative Market Data Replay &amp; Liquidity Profile &bull; Source: {db_path}</div>
      </div>
      <div class="badges">
        <span class="badge">Exact Decimal Precision</span>
        <span class="badge">64-bit UTC Nanoseconds</span>
        <span class="badge">Deterministic Ordering</span>
      </div>
    </header>

    <!-- KPI Section -->
    <div class="grid-kpi">
      <div class="kpi-card">
        <div class="kpi-label">Cumulative Volume</div>
        <div class="kpi-value">{_fmt_dec(summary.total_volume, 0)}</div>
        <div class="kpi-subtext">Trades: {summary.trade_count:,} | Quotes: {summary.quote_count:,}</div>
      </div>

      <div class="kpi-card">
        <div class="kpi-label">Execution VWAP</div>
        <div class="kpi-value">${_fmt_dec(summary.final_vwap, 4)}</div>
        <div class="kpi-subtext">Range: ${_fmt_dec(summary.min_price, 2)} &ndash; ${_fmt_dec(summary.max_price, 2)}</div>
      </div>

      <div class="kpi-card">
        <div class="kpi-label">Mean Relative Spread</div>
        <div class="kpi-value" style="color: var(--accent-purple);">{_fmt_dec(summary.mean_relative_spread_bps, 2)} bps</div>
        <div class="kpi-subtext">Quoted Spread: ${_fmt_dec(summary.mean_quoted_spread, 4)} | Crossed: {summary.crossed_quote_count}</div>
      </div>

      <div class="kpi-card">
        <div class="kpi-label">Order Flow Imbalance</div>
        <div class="kpi-value" style="color: {imb_color};">{imb_pct:+.2f}%</div>
        <div class="kpi-subtext">Buy Vol: {_fmt_dec(summary.buy_volume, 0)} | Sell Vol: {_fmt_dec(summary.sell_volume, 0)}</div>
      </div>

      <div class="kpi-card">
        <div class="kpi-label">Median Arrival Delta (p50)</div>
        <div class="kpi-value" style="color: var(--accent-blue);">{med_us:.1f} &mu;s</div>
        <div class="kpi-subtext">p90: {p90_us:.1f}&mu;s | p99: {p99_us:.1f}&mu;s</div>
      </div>
    </div>

    <!-- Charts Section -->
    <div class="chart-section">
      <div class="chart-card">
        <div class="chart-header">
          <div class="chart-title">Price Execution Trajectory &amp; Cumulative Volume-Weighted Average Price</div>
          <div class="chart-description">Every fill plotted against running institutional benchmark</div>
        </div>
        {vwap_svg}
      </div>

      <div class="chart-card">
        <div class="chart-header">
          <div class="chart-title">Top-of-Book Relative Spread Dynamics</div>
          <div class="chart-description">Instantaneous quoted spread in basis points (ap - bp) / mid &times; 10,000</div>
        </div>
        {spread_svg}
      </div>

      <div class="chart-card">
        <div class="chart-header">
          <div class="chart-title">Signed Order Flow Imbalance Ratio</div>
          <div class="chart-description">Aggressor flow ratio (Buy - Sell) / (Buy + Sell) reflecting buyer/seller pressure</div>
        </div>
        {imbalance_svg}
      </div>

      <div class="chart-card">
        <div class="chart-header">
          <div class="chart-title">Packet Inter-Arrival Latency &amp; Jitter Distribution</div>
          <div class="chart-description">High-precision &Delta;t distribution with median, 90th, and 99th percentile markers</div>
        </div>
        {jitter_svg}
      </div>
    </div>

    <!-- Microstructure Metrics Table -->
    <div class="stats-table-card">
      <div class="stats-table-title">Microstructure Summary &amp; Latency Profiles</div>
      <table>
        <thead>
          <tr>
            <th>Metric</th>
            <th>Value</th>
            <th>Unit / Invariant</th>
          </tr>
        </thead>
        <tbody>
          <tr>
            <td>Total Ingested Events</td>
            <td>{summary.total_events:,}</td>
            <td>Deterministic Replay Sequence</td>
          </tr>
          <tr>
            <td>Trade Executions</td>
            <td>{summary.trade_count:,}</td>
            <td>Discrete trade prints</td>
          </tr>
          <tr>
            <td>Top-of-Book Quotes</td>
            <td>{summary.quote_count:,}</td>
            <td>BBO updates</td>
          </tr>
          <tr>
            <td>Cumulative Turnover / Notional</td>
            <td>${_fmt_dec(summary.total_notional, 2)}</td>
            <td>Exact Decimal arithmetic</td>
          </tr>
          <tr>
            <td>Volume Imbalance Ratio</td>
            <td>{summary.volume_imbalance_ratio}</td>
            <td>Bounded [-1.0, 1.0]</td>
          </tr>
          <tr>
            <td>Mean Quoted Spread</td>
            <td>${_fmt_dec(summary.mean_quoted_spread, 4)}</td>
            <td>Ask price &minus; Bid price</td>
          </tr>
          <tr>
            <td>Mean Relative Spread</td>
            <td>{_fmt_dec(summary.mean_relative_spread_bps, 2)} bps</td>
            <td>Spread relative to midpoint in basis points</td>
          </tr>
          <tr>
            <td>Crossed Quote Instances</td>
            <td>{summary.crossed_quote_count}</td>
            <td>Bid price &gt; Ask price anomalies</td>
          </tr>
          <tr>
            <td>Min Inter-Arrival Latency</td>
            <td>{min_us:.3f} &mu;s ({summary.min_inter_arrival_ns:,} ns)</td>
            <td>64-bit UTC timestamp delta</td>
          </tr>
          <tr>
            <td>Median Inter-Arrival Latency (p50)</td>
            <td>{med_us:.3f} &mu;s ({summary.median_inter_arrival_ns:,} ns)</td>
            <td>50th percentile jitter</td>
          </tr>
          <tr>
            <td>90th Percentile Latency (p90)</td>
            <td>{p90_us:.3f} &mu;s ({summary.p90_inter_arrival_ns:,} ns)</td>
            <td>90th percentile jitter</td>
          </tr>
          <tr>
            <td>99th Percentile Latency (p99)</td>
            <td>{p99_us:.3f} &mu;s ({summary.p99_inter_arrival_ns:,} ns)</td>
            <td>99th percentile jitter tail risk</td>
          </tr>
          <tr>
            <td>Max Inter-Arrival Latency</td>
            <td>{max_us:.3f} &mu;s ({summary.max_inter_arrival_ns:,} ns)</td>
            <td>Maximum observed packet interval</td>
          </tr>
        </tbody>
      </table>
    </div>

    <footer>
      <div>Quantitative Market Data &amp; Historical Replay Infrastructure &bull; P01 Analytics</div>
      <div>Generated with zero external dependencies</div>
    </footer>
  </div>
</body>
</html>
"""
    return html
