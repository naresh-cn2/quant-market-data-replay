"""
Unit tests for quantitative microstructure metrics calculation and SVG rendering.
"""

from decimal import Decimal
import unittest

from src.analytics.metrics import MicrostructureMetricsCalculator
from src.analytics.svg_charts import (
    render_empty_chart,
    render_jitter_distribution_svg,
    render_price_vwap_svg,
    render_spread_dynamics_svg,
    render_volume_imbalance_svg,
)
from src.analytics.visualizer import generate_html_report
from src.models.quote import QuoteEvent
from src.models.trade import Side, TradeEvent


class TestMicrostructureMetrics(unittest.TestCase):
    def test_empty_events(self):
        calc = MicrostructureMetricsCalculator("AAPL")
        summary = calc.compute([])
        self.assertEqual(summary.symbol, "AAPL")
        self.assertEqual(summary.total_events, 0)
        self.assertEqual(summary.trade_count, 0)
        self.assertEqual(summary.quote_count, 0)
        self.assertEqual(summary.total_volume, Decimal("0"))
        self.assertEqual(summary.final_vwap, Decimal("0"))

    def test_vwap_and_volume_calculation(self):
        events = [
            TradeEvent(
                event_id="t1",
                timestamp_ns=1_000_000_000,
                symbol="AAPL",
                price=Decimal("10.00"),
                size=Decimal("100"),
                side=Side.BUY,
                source="TEST",
            ),
            TradeEvent(
                event_id="t2",
                timestamp_ns=2_000_000_000,
                symbol="AAPL",
                price=Decimal("20.00"),
                size=Decimal("300"),
                side=Side.SELL,
                source="TEST",
            ),
        ]
        calc = MicrostructureMetricsCalculator("AAPL")
        summary = calc.compute(events)

        self.assertEqual(summary.total_events, 2)
        self.assertEqual(summary.trade_count, 2)
        self.assertEqual(summary.quote_count, 0)
        self.assertEqual(summary.total_volume, Decimal("400"))
        self.assertEqual(summary.total_notional, Decimal("7000.00"))
        self.assertEqual(summary.final_vwap, Decimal("17.5"))
        self.assertEqual(summary.buy_volume, Decimal("100"))
        self.assertEqual(summary.sell_volume, Decimal("300"))
        self.assertEqual(summary.volume_imbalance_ratio, Decimal("-0.5"))

    def test_spread_and_crossed_quotes(self):
        events = [
            QuoteEvent(
                event_id="q1",
                timestamp_ns=1_000_000_000,
                symbol="AAPL",
                bid_price=Decimal("100.00"),
                bid_size=Decimal("10"),
                ask_price=Decimal("102.00"),
                ask_size=Decimal("10"),
                source="TEST",
            ),
            # Crossed quote: bid 105 > ask 104
            QuoteEvent(
                event_id="q2",
                timestamp_ns=2_000_000_000,
                symbol="AAPL",
                bid_price=Decimal("105.00"),
                bid_size=Decimal("10"),
                ask_price=Decimal("104.00"),
                ask_size=Decimal("10"),
                source="TEST",
            ),
        ]
        calc = MicrostructureMetricsCalculator("AAPL")
        summary = calc.compute(events)

        self.assertEqual(summary.quote_count, 2)
        self.assertEqual(summary.crossed_quote_count, 1)
        self.assertEqual(len(summary.spread_points), 2)
        self.assertEqual(summary.spread_points[0].quoted_spread, Decimal("2.00"))
        self.assertFalse(summary.spread_points[0].is_crossed)
        self.assertEqual(summary.spread_points[1].quoted_spread, Decimal("-1.00"))
        self.assertTrue(summary.spread_points[1].is_crossed)

    def test_inter_arrival_jitter(self):
        events = [
            TradeEvent(
                event_id="t1",
                timestamp_ns=1000,
                symbol="AAPL",
                price=Decimal("150.00"),
                size=Decimal("10"),
                side=Side.BUY,
                source="TEST",
            ),
            TradeEvent(
                event_id="t2",
                timestamp_ns=3000,  # delta = 2000 ns
                symbol="AAPL",
                price=Decimal("150.10"),
                size=Decimal("10"),
                side=Side.BUY,
                source="TEST",
            ),
            TradeEvent(
                event_id="t3",
                timestamp_ns=8000,  # delta = 5000 ns
                symbol="AAPL",
                price=Decimal("150.20"),
                size=Decimal("10"),
                side=Side.BUY,
                source="TEST",
            ),
        ]
        calc = MicrostructureMetricsCalculator("AAPL")
        summary = calc.compute(events)

        self.assertEqual(summary.min_inter_arrival_ns, 2000)
        self.assertEqual(summary.max_inter_arrival_ns, 5000)
        self.assertEqual(len(summary.inter_arrival_deltas_us), 2)
        self.assertIn(2.0, summary.inter_arrival_deltas_us)
        self.assertIn(5.0, summary.inter_arrival_deltas_us)


class TestSvgCharts(unittest.TestCase):
    def test_empty_charts_render(self):
        empty_svg = render_empty_chart("Test Chart", "No data")
        self.assertIn("<svg", empty_svg)
        self.assertIn("</svg>", empty_svg)
        self.assertIn("Test Chart", empty_svg)
        self.assertIn("No data", empty_svg)

    def test_price_vwap_svg(self):
        events = [
            TradeEvent(
                event_id="t1",
                timestamp_ns=1_000_000_000,
                symbol="AAPL",
                price=Decimal("150.00"),
                size=Decimal("100"),
                side=Side.BUY,
                source="TEST",
            ),
            TradeEvent(
                event_id="t2",
                timestamp_ns=2_000_000_000,
                symbol="AAPL",
                price=Decimal("151.00"),
                size=Decimal("200"),
                side=Side.SELL,
                source="TEST",
            ),
        ]
        calc = MicrostructureMetricsCalculator("AAPL")
        summary = calc.compute(events)
        svg = render_price_vwap_svg(summary.vwap_points, "AAPL")

        self.assertIn("<svg", svg)
        self.assertIn("</svg>", svg)
        self.assertIn("AAPL Price", svg)
        self.assertIn("Cumulative VWAP", svg)

    def test_spread_dynamics_svg(self):
        events = [
            QuoteEvent(
                event_id="q1",
                timestamp_ns=1_000_000_000,
                symbol="AAPL",
                bid_price=Decimal("150.00"),
                bid_size=Decimal("100"),
                ask_price=Decimal("150.10"),
                ask_size=Decimal("100"),
                source="TEST",
            )
        ]
        calc = MicrostructureMetricsCalculator("AAPL")
        summary = calc.compute(events)
        svg = render_spread_dynamics_svg(summary.spread_points, "AAPL")

        self.assertIn("<svg", svg)
        self.assertIn("</svg>", svg)
        self.assertIn("Relative Spread Dynamics", svg)

    def test_volume_imbalance_svg(self):
        events = [
            TradeEvent(
                event_id="t1",
                timestamp_ns=1_000_000_000,
                symbol="AAPL",
                price=Decimal("150.00"),
                size=Decimal("100"),
                side=Side.BUY,
                source="TEST",
            )
        ]
        calc = MicrostructureMetricsCalculator("AAPL")
        summary = calc.compute(events)
        svg = render_volume_imbalance_svg(summary.imbalance_points, "AAPL")

        self.assertIn("<svg", svg)
        self.assertIn("</svg>", svg)
        self.assertIn("Cumulative Order Flow Imbalance", svg)

    def test_jitter_distribution_svg(self):
        deltas = [1.5, 2.0, 3.5, 10.0, 50.0]
        svg = render_jitter_distribution_svg(
            deltas_us=deltas,
            p50_ns=2000,
            p90_ns=35000,
            p99_ns=50000,
            symbol="AAPL",
        )
        self.assertIn("<svg", svg)
        self.assertIn("</svg>", svg)
        self.assertIn("Inter-Arrival Jitter", svg)

    def test_generate_html_report(self):
        events = [
            TradeEvent(
                event_id="t1",
                timestamp_ns=1_000_000_000,
                symbol="AAPL",
                price=Decimal("150.00"),
                size=Decimal("100"),
                side=Side.BUY,
                source="TEST",
            )
        ]
        calc = MicrostructureMetricsCalculator("AAPL")
        summary = calc.compute(events)
        html = generate_html_report(summary, db_path="test.db")

        self.assertIn("<!DOCTYPE html>", html)
        self.assertIn("<title>AAPL Quantitative Market Report</title>", html)
        self.assertIn("Exact Decimal Precision", html)
        self.assertIn("Execution VWAP", html)


if __name__ == "__main__":
    unittest.main()
