"""
Report generation pipeline for quantitative market microstructure.

Reads market events directly from the historical storage backend via ReplayEngine
and produces a standalone, self-contained HTML report with vector SVG charts.
"""

import os
from typing import Optional, Union

from src.analytics.metrics import MicrostructureMetricsCalculator, MicrostructureSummary
from src.analytics.visualizer import generate_html_report
from src.replay.engine import ReplayEngine
from src.storage.sqlite_store import SqliteStorageBackend


def generate_market_report(
    db_path: str,
    symbol: str,
    output_path: str,
    start_ns: int = 0,
    end_ns: int = 2**63 - 1,
) -> MicrostructureSummary:
    """
    Executes historical replay across the requested time window for a symbol,
    computes microstructure analytics, and renders a self-contained HTML visual report.

    Args:
        db_path: Path to the SQLite historical market data database.
        symbol: Ticker symbol to analyze.
        output_path: Target filesystem path for the generated HTML report.
        start_ns: Inclusive start timestamp in UTC nanoseconds.
        end_ns: Inclusive end timestamp in UTC nanoseconds.

    Returns:
        MicrostructureSummary containing all computed quantitative metrics and time series.
    """
    if not os.path.exists(db_path):
        raise FileNotFoundError(f"Database not found: {db_path}")

    storage = SqliteStorageBackend(db_path)
    try:
        replay_engine = ReplayEngine(storage)
        events = list(replay_engine.replay_stream(
            symbol=symbol,
            start_ns=start_ns,
            end_ns=end_ns,
            event_types=("TRADE", "QUOTE"),
        ))

        calculator = MicrostructureMetricsCalculator(symbol)
        summary = calculator.compute(events)

        html_content = generate_html_report(summary, db_path=db_path)

        out_dir = os.path.dirname(output_path)
        if out_dir:
            os.makedirs(out_dir, exist_ok=True)

        with open(output_path, "w", encoding="utf-8") as f:
            f.write(html_content)

        return summary
    finally:
        storage.close()
