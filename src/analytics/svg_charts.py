"""
Pure standard-library SVG chart generator for quantitative market microstructure.

Produces self-contained, responsive, dark-mode SVG vector graphics with zero external
dependencies (no matplotlib, no plotly, no npm).
"""

from decimal import Decimal
import math
from typing import List, Optional, Tuple

from src.analytics.metrics import (
    PriceVwapPoint,
    SpreadMetricPoint,
    VolumeImbalancePoint,
)


def _format_coord(val: float) -> str:
    """Format float coordinates to 2 decimal places to minimize SVG size."""
    return f"{val:.2f}"


def _downsample_series(series: list, max_points: int = 400) -> list:
    """Systematically downsample series if points exceed max_points to keep SVGs compact."""
    if len(series) <= max_points:
        return series
    step = len(series) / max_points
    return [series[int(i * step)] for i in range(max_points)] + [series[-1]]


def render_empty_chart(title: str, message: str, width: int = 900, height: int = 300) -> str:
    """Renders a sleek placeholder when no data points are present."""
    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" width="100%" height="{height}" class="chart-svg">
  <rect width="{width}" height="{height}" fill="#111622" rx="8"/>
  <rect x="1" y="1" width="{width - 2}" height="{height - 2}" fill="none" stroke="#1E2638" stroke-width="1" rx="8"/>
  <text x="30" y="40" fill="#F0F4F8" font-family="system-ui, -apple-system, sans-serif" font-size="14" font-weight="600">{title}</text>
  <text x="{width / 2}" y="{height / 2 + 5}" fill="#64748B" font-family="system-ui, -apple-system, sans-serif" font-size="13" text-anchor="middle">{message}</text>
</svg>"""


def render_price_vwap_svg(
    points: List[PriceVwapPoint],
    symbol: str,
    width: int = 900,
    height: int = 320,
) -> str:
    """
    Renders execution price time series and cumulative VWAP curve.
    Includes buy/sell trade points and dynamic price scale.
    """
    if not points:
        return render_empty_chart("Price &amp; Cumulative VWAP Execution Trajectory", "No trade events recorded for symbol")

    sampled = _downsample_series(points, max_points=350)

    # Geometry
    pad_left = 75
    pad_right = 35
    pad_top = 55
    pad_bottom = 45
    plot_w = width - pad_left - pad_right
    plot_h = height - pad_top - pad_bottom

    # Ranges
    all_prices = [float(p.price) for p in sampled] + [float(p.cumulative_vwap) for p in sampled]
    min_px = min(all_prices)
    max_px = max(all_prices)
    if min_px == max_px:
        min_px *= 0.99
        max_px *= 1.01

    px_span = max_px - min_px
    min_ts = sampled[0].timestamp_ns
    max_ts = sampled[-1].timestamp_ns
    ts_span = max(1, max_ts - min_ts)

    def x_coord(ts: int) -> float:
        return pad_left + ((ts - min_ts) / ts_span) * plot_w

    def y_coord(px: float) -> float:
        return pad_top + plot_h - ((px - min_px) / px_span) * plot_h

    # Build price path and VWAP path
    vwap_coords = [(x_coord(p.timestamp_ns), y_coord(float(p.cumulative_vwap))) for p in sampled]
    vwap_path = "M " + " L ".join(f"{_format_coord(x)},{_format_coord(y)}" for x, y in vwap_coords)

    # Trade markers
    trade_circles: List[str] = []
    for p in sampled:
        cx = _format_coord(x_coord(p.timestamp_ns))
        cy = _format_coord(y_coord(float(p.price)))
        color = "#00E676" if p.side == "BUY" else ("#FF5252" if p.side == "SELL" else "#94A3B8")
        trade_circles.append(
            f'<circle cx="{cx}" cy="{cy}" r="3.5" fill="{color}" fill-opacity="0.85" stroke="#0B0E14" stroke-width="0.8">'
            f'<title>Time: {p.timestamp_ns}ns | Px: {p.price} | Sz: {p.size} | Side: {p.side}</title></circle>'
        )

    # Grid & Y-ticks
    grid_lines: List[str] = []
    y_ticks: List[str] = []
    num_y_ticks = 5
    for i in range(num_y_ticks + 1):
        tick_val = min_px + (px_span * (i / num_y_ticks))
        y_pos = y_coord(tick_val)
        y_str = _format_coord(y_pos)
        grid_lines.append(f'<line x1="{pad_left}" y1="{y_str}" x2="{width - pad_right}" y2="{y_str}" stroke="#1E2638" stroke-width="1" stroke-dasharray="3,3"/>')
        y_ticks.append(f'<text x="{pad_left - 12}" y="{_format_coord(y_pos + 4)}" fill="#8E9AA8" font-family="system-ui, sans-serif" font-size="11" text-anchor="end">${tick_val:.2f}</text>')

    # Time ticks (start, mid, end)
    x_ticks = [
        f'<text x="{pad_left}" y="{height - 18}" fill="#8E9AA8" font-family="system-ui, sans-serif" font-size="11" text-anchor="start">T+0s</text>',
        f'<text x="{pad_left + plot_w / 2}" y="{height - 18}" fill="#8E9AA8" font-family="system-ui, sans-serif" font-size="11" text-anchor="middle">Elapsed: {(ts_span / 1e9 / 2):.2f}s</text>',
        f'<text x="{width - pad_right}" y="{height - 18}" fill="#8E9AA8" font-family="system-ui, sans-serif" font-size="11" text-anchor="end">{(ts_span / 1e9):.2f}s</text>',
    ]

    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" width="100%" height="{height}" class="chart-svg">
  <!-- Card Background -->
  <rect width="{width}" height="{height}" fill="#111622" rx="8"/>
  <rect x="1" y="1" width="{width - 2}" height="{height - 2}" fill="none" stroke="#1E2638" stroke-width="1" rx="8"/>

  <!-- Title & Legend -->
  <text x="{pad_left}" y="32" fill="#F0F4F8" font-family="system-ui, -apple-system, sans-serif" font-size="14" font-weight="600">{symbol} Price &amp; Cumulative VWAP Execution Trajectory</text>

  <g transform="translate({width - pad_right - 280}, 20)">
    <circle cx="10" cy="10" r="4" fill="#00E676"/>
    <text x="20" y="14" fill="#94A3B8" font-family="system-ui, sans-serif" font-size="11">Buy Trade</text>
    <circle cx="85" cy="10" r="4" fill="#FF5252"/>
    <text x="95" y="14" fill="#94A3B8" font-family="system-ui, sans-serif" font-size="11">Sell Trade</text>
    <line x1="160" y1="10" x2="185" y2="10" stroke="#00B0FF" stroke-width="2.5"/>
    <text x="195" y="14" fill="#94A3B8" font-family="system-ui, sans-serif" font-size="11">Cumulative VWAP</text>
  </g>

  <!-- Grid & Ticks -->
  {''.join(grid_lines)}
  {''.join(y_ticks)}
  {''.join(x_ticks)}

  <!-- Data Series -->
  <path d="{vwap_path}" fill="none" stroke="#00B0FF" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"/>
  {''.join(trade_circles)}
</svg>"""


def render_spread_dynamics_svg(
    points: List[SpreadMetricPoint],
    symbol: str,
    width: int = 900,
    height: int = 280,
) -> str:
    """
    Renders Top-of-Book quoted spread and relative spread in basis points (bps).
    Highlights crossed quotes in prominent warning red/amber.
    """
    if not points:
        return render_empty_chart("Bid-Ask Spread Dynamics &amp; Relative Liquidity", "No quote events recorded for symbol")

    sampled = _downsample_series(points, max_points=350)

    pad_left = 75
    pad_right = 35
    pad_top = 50
    pad_bottom = 45
    plot_w = width - pad_left - pad_right
    plot_h = height - pad_top - pad_bottom

    bps_values = [float(p.relative_spread_bps) for p in sampled]
    min_bps = min(bps_values)
    max_bps = max(bps_values)
    if min_bps == max_bps:
        min_bps = max(0.0, min_bps * 0.9)
        max_bps = max_bps * 1.1 + 1.0

    min_ts = sampled[0].timestamp_ns
    max_ts = sampled[-1].timestamp_ns
    ts_span = max(1, max_ts - min_ts)

    def x_coord(ts: int) -> float:
        return pad_left + ((ts - min_ts) / ts_span) * plot_w

    def y_coord(bps: float) -> float:
        return pad_top + plot_h - ((bps - min_bps) / (max_bps - min_bps)) * plot_h

    # Area polygon for relative spread
    coords = [(x_coord(p.timestamp_ns), y_coord(float(p.relative_spread_bps))) for p in sampled]
    baseline_y = pad_top + plot_h

    path_points = " ".join(f"{_format_coord(x)},{_format_coord(y)}" for x, y in coords)
    area_d = f"M {_format_coord(coords[0][0])},{_format_coord(baseline_y)} L {path_points} L {_format_coord(coords[-1][0])},{_format_coord(baseline_y)} Z"
    line_d = "M " + " L ".join(f"{_format_coord(x)},{_format_coord(y)}" for x, y in coords)

    # Highlight crossed quote warnings
    crossed_markers: List[str] = []
    for p in sampled:
        if p.is_crossed:
            cx = _format_coord(x_coord(p.timestamp_ns))
            cy = _format_coord(y_coord(float(p.relative_spread_bps)))
            crossed_markers.append(
                f'<circle cx="{cx}" cy="{cy}" r="5" fill="#FF1744" stroke="#FFE57F" stroke-width="1.5">'
                f'<title>CROSSED QUOTE: Bid {p.bid_price} >= Ask {p.ask_price}</title></circle>'
            )

    # Grid & Y-ticks
    grid_lines: List[str] = []
    y_ticks: List[str] = []
    num_y_ticks = 4
    for i in range(num_y_ticks + 1):
        tick_val = min_bps + ((max_bps - min_bps) * (i / num_y_ticks))
        y_pos = y_coord(tick_val)
        y_str = _format_coord(y_pos)
        grid_lines.append(f'<line x1="{pad_left}" y1="{y_str}" x2="{width - pad_right}" y2="{y_str}" stroke="#1E2638" stroke-width="1" stroke-dasharray="3,3"/>')
        y_ticks.append(f'<text x="{pad_left - 12}" y="{_format_coord(y_pos + 4)}" fill="#8E9AA8" font-family="system-ui, sans-serif" font-size="11" text-anchor="end">{tick_val:.1f} bps</text>')

    x_ticks = [
        f'<text x="{pad_left}" y="{height - 18}" fill="#8E9AA8" font-family="system-ui, sans-serif" font-size="11" text-anchor="start">T+0s</text>',
        f'<text x="{pad_left + plot_w / 2}" y="{height - 18}" fill="#8E9AA8" font-family="system-ui, sans-serif" font-size="11" text-anchor="middle">Elapsed: {(ts_span / 1e9 / 2):.2f}s</text>',
        f'<text x="{width - pad_right}" y="{height - 18}" fill="#8E9AA8" font-family="system-ui, sans-serif" font-size="11" text-anchor="end">{(ts_span / 1e9):.2f}s</text>',
    ]

    crossed_svg = ("\n  " + "".join(crossed_markers)) if crossed_markers else ""

    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" width="100%" height="{height}" class="chart-svg">
  <defs>
    <linearGradient id="spreadGrad" x1="0%" y1="0%" x2="0%" y2="100%">
      <stop offset="0%" stop-color="#7C4DFF" stop-opacity="0.45"/>
      <stop offset="100%" stop-color="#7C4DFF" stop-opacity="0.02"/>
    </linearGradient>
  </defs>
  <rect width="{width}" height="{height}" fill="#111622" rx="8"/>
  <rect x="1" y="1" width="{width - 2}" height="{height - 2}" fill="none" stroke="#1E2638" stroke-width="1" rx="8"/>

  <text x="{pad_left}" y="32" fill="#F0F4F8" font-family="system-ui, -apple-system, sans-serif" font-size="14" font-weight="600">{symbol} Top-of-Book Relative Spread Dynamics (Basis Points)</text>

  <g transform="translate({width - pad_right - 180}, 20)">
    <rect x="0" y="5" width="12" height="8" fill="#7C4DFF" rx="2"/>
    <text x="18" y="13" fill="#94A3B8" font-family="system-ui, sans-serif" font-size="11">Relative Spread (bps)</text>
  </g>

  {''.join(grid_lines)}
  {''.join(y_ticks)}
  {''.join(x_ticks)}

  <path d="{area_d}" fill="url(#spreadGrad)"/>
  <path d="{line_d}" fill="none" stroke="#7C4DFF" stroke-width="2"/>{crossed_svg}
</svg>"""


def render_volume_imbalance_svg(
    points: List[VolumeImbalancePoint],
    symbol: str,
    width: int = 900,
    height: int = 280,
) -> str:
    """
    Renders signed order flow volume imbalance ratio: (Buy - Sell) / (Buy + Sell).
    Bounded between -1.0 (pure seller dominance) and +1.0 (pure buyer dominance).
    """
    if not points:
        return render_empty_chart("Order Flow Volume Imbalance Ratio", "No trades available to compute flow imbalance")

    sampled = _downsample_series(points, max_points=350)

    pad_left = 75
    pad_right = 35
    pad_top = 50
    pad_bottom = 45
    plot_w = width - pad_left - pad_right
    plot_h = height - pad_top - pad_bottom

    min_ts = sampled[0].timestamp_ns
    max_ts = sampled[-1].timestamp_ns
    ts_span = max(1, max_ts - min_ts)

    # Imbalance is strictly [-1.0, 1.0]
    def x_coord(ts: int) -> float:
        return pad_left + ((ts - min_ts) / ts_span) * plot_w

    def y_coord(imb: float) -> float:
        # +1.0 at pad_top, 0.0 at pad_top + plot_h/2, -1.0 at pad_top + plot_h
        return pad_top + (plot_h / 2.0) - (imb * (plot_h / 2.0))

    zero_y = _format_coord(y_coord(0.0))
    plus_1_y = _format_coord(y_coord(1.0))
    minus_1_y = _format_coord(y_coord(-1.0))

    coords = [(x_coord(p.timestamp_ns), y_coord(float(p.volume_imbalance))) for p in sampled]
    line_d = "M " + " L ".join(f"{_format_coord(x)},{_format_coord(y)}" for x, y in coords)

    grid_lines = [
        f'<line x1="{pad_left}" y1="{plus_1_y}" x2="{width - pad_right}" y2="{plus_1_y}" stroke="#1E2638" stroke-width="1" stroke-dasharray="3,3"/>',
        f'<line x1="{pad_left}" y1="{zero_y}" x2="{width - pad_right}" y2="{zero_y}" stroke="#475569" stroke-width="1.2"/>',
        f'<line x1="{pad_left}" y1="{minus_1_y}" x2="{width - pad_right}" y2="{minus_1_y}" stroke="#1E2638" stroke-width="1" stroke-dasharray="3,3"/>',
    ]

    y_ticks = [
        f'<text x="{pad_left - 12}" y="{_format_coord(y_coord(1.0) + 4)}" fill="#00E676" font-family="system-ui, sans-serif" font-size="11" text-anchor="end">+1.0 (Buy)</text>',
        f'<text x="{pad_left - 12}" y="{_format_coord(y_coord(0.0) + 4)}" fill="#8E9AA8" font-family="system-ui, sans-serif" font-size="11" text-anchor="end">0.0 (Neutral)</text>',
        f'<text x="{pad_left - 12}" y="{_format_coord(y_coord(-1.0) + 4)}" fill="#FF5252" font-family="system-ui, sans-serif" font-size="11" text-anchor="end">-1.0 (Sell)</text>',
    ]

    x_ticks = [
        f'<text x="{pad_left}" y="{height - 18}" fill="#8E9AA8" font-family="system-ui, sans-serif" font-size="11" text-anchor="start">T+0s</text>',
        f'<text x="{pad_left + plot_w / 2}" y="{height - 18}" fill="#8E9AA8" font-family="system-ui, sans-serif" font-size="11" text-anchor="middle">Elapsed: {(ts_span / 1e9 / 2):.2f}s</text>',
        f'<text x="{width - pad_right}" y="{height - 18}" fill="#8E9AA8" font-family="system-ui, sans-serif" font-size="11" text-anchor="end">{(ts_span / 1e9):.2f}s</text>',
    ]

    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" width="100%" height="{height}" class="chart-svg">
  <rect width="{width}" height="{height}" fill="#111622" rx="8"/>
  <rect x="1" y="1" width="{width - 2}" height="{height - 2}" fill="none" stroke="#1E2638" stroke-width="1" rx="8"/>

  <text x="{pad_left}" y="32" fill="#F0F4F8" font-family="system-ui, -apple-system, sans-serif" font-size="14" font-weight="600">{symbol} Cumulative Order Flow Imbalance Ratio</text>

  <!-- Shaded Bands -->
  <rect x="{pad_left}" y="{plus_1_y}" width="{plot_w}" height="{float(zero_y) - float(plus_1_y)}" fill="#00E676" fill-opacity="0.04"/>
  <rect x="{pad_left}" y="{zero_y}" width="{plot_w}" height="{float(minus_1_y) - float(zero_y)}" fill="#FF5252" fill-opacity="0.04"/>

  {''.join(grid_lines)}
  {''.join(y_ticks)}
  {''.join(x_ticks)}

  <path d="{line_d}" fill="none" stroke="#00E5FF" stroke-width="2.2" stroke-linejoin="round"/>
</svg>"""


def render_jitter_distribution_svg(
    deltas_us: List[float],
    p50_ns: int,
    p90_ns: int,
    p99_ns: int,
    symbol: str,
    width: int = 900,
    height: int = 280,
) -> str:
    """
    Renders inter-arrival jitter / latency distribution histogram with percentile markers.
    """
    if not deltas_us:
        return render_empty_chart("Packet Inter-Arrival Latency / Jitter Distribution", "Insufficient events to measure delta latency")

    pad_left = 75
    pad_right = 35
    pad_top = 50
    pad_bottom = 45
    plot_w = width - pad_left - pad_right
    plot_h = height - pad_top - pad_bottom

    # Bin into 25 logarithmic or linear bins up to 99th percentile to remove extreme outlier squashing
    p99_us = p99_ns / 1_000.0
    max_val_us = max(p99_us * 1.5, 10.0)
    num_bins = 24
    bin_size = max_val_us / num_bins

    bins = [0] * num_bins
    for d in deltas_us:
        idx = min(num_bins - 1, int(d / bin_size))
        bins[idx] += 1

    max_bin_count = max(bins) if bins else 1
    if max_bin_count == 0:
        max_bin_count = 1

    bar_w = (plot_w / num_bins) * 0.85
    bar_gap = (plot_w / num_bins) * 0.15

    bars: List[str] = []
    for i, count in enumerate(bins):
        bx = pad_left + i * (bar_w + bar_gap)
        bar_h = (count / max_bin_count) * plot_h
        by = pad_top + plot_h - bar_h
        bars.append(
            f'<rect x="{_format_coord(bx)}" y="{_format_coord(by)}" width="{_format_coord(bar_w)}" height="{_format_coord(bar_h)}" fill="#38BDF8" fill-opacity="0.8" rx="2">'
            f'<title>Range: {i*bin_size:.1f}-{(i+1)*bin_size:.1f}μs | Count: {count}</title></rect>'
        )

    # Marker lines for p50, p90, p99
    def us_to_x(us: float) -> float:
        ratio = min(1.0, us / max_val_us)
        return pad_left + ratio * plot_w

    markers = []
    for label, val_ns, color in [("p50", p50_ns, "#00E676"), ("p90", p90_ns, "#FFB300"), ("p99", p99_ns, "#FF1744")]:
        val_us = val_ns / 1000.0
        mx = _format_coord(us_to_x(val_us))
        markers.append(
            f'<line x1="{mx}" y1="{pad_top}" x2="{mx}" y2="{pad_top + plot_h}" stroke="{color}" stroke-width="1.8" stroke-dasharray="4,3"/>'
            f'<text x="{mx}" y="{pad_top - 8}" fill="{color}" font-family="system-ui, sans-serif" font-size="10" font-weight="600" text-anchor="middle">{label}: {val_us:.1f}μs</text>'
        )

    x_ticks = [
        f'<text x="{pad_left}" y="{height - 18}" fill="#8E9AA8" font-family="system-ui, sans-serif" font-size="11" text-anchor="start">0 μs</text>',
        f'<text x="{pad_left + plot_w / 2}" y="{height - 18}" fill="#8E9AA8" font-family="system-ui, sans-serif" font-size="11" text-anchor="middle">{max_val_us / 2:.1f} μs</text>',
        f'<text x="{width - pad_right}" y="{height - 18}" fill="#8E9AA8" font-family="system-ui, sans-serif" font-size="11" text-anchor="end">{max_val_us:.1f} μs</text>',
    ]

    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" width="100%" height="{height}" class="chart-svg">
  <rect width="{width}" height="{height}" fill="#111622" rx="8"/>
  <rect x="1" y="1" width="{width - 2}" height="{height - 2}" fill="none" stroke="#1E2638" stroke-width="1" rx="8"/>

  <text x="{pad_left}" y="32" fill="#F0F4F8" font-family="system-ui, -apple-system, sans-serif" font-size="14" font-weight="600">{symbol} Inter-Arrival Jitter / Latency Distribution (Microseconds)</text>

  <!-- Bars -->
  {''.join(bars)}

  <!-- Percentile Markers -->
  {''.join(markers)}

  <!-- Ticks -->
  {''.join(x_ticks)}
</svg>"""
