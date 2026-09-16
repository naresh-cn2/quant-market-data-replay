"""
Integration test for market report generation end-to-end.
"""

from decimal import Decimal
import os
import tempfile
import unittest

from src.analytics.report_generator import generate_market_report
from src.models.quote import QuoteEvent
from src.models.trade import Side, TradeEvent
from src.storage.sqlite_store import SqliteStorageBackend


class TestReportGenerationIntegration(unittest.TestCase):
    def setUp(self):
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self.tmp_dir.name, "test_market.db")
        self.report_path = os.path.join(self.tmp_dir.name, "reports", "AAPL_report.html")

        # Seed sample data into SQLite
        storage = SqliteStorageBackend(self.db_path)
        try:
            # 5 trades
            for i in range(5):
                ts = 1_700_000_000_000_000_000 + (i * 100_000)
                storage.store_trade(
                    TradeEvent(
                        event_id=f"t_{i}",
                        timestamp_ns=ts,
                        symbol="AAPL",
                        price=Decimal(f"150.{i}0"),
                        size=Decimal("100"),
                        side=Side.BUY if i % 2 == 0 else Side.SELL,
                        source="TEST",
                    )
                )
            # 5 quotes
            for i in range(5):
                ts = 1_700_000_000_000_050_000 + (i * 100_000)
                storage.store_quote(
                    QuoteEvent(
                        event_id=f"q_{i}",
                        timestamp_ns=ts,
                        symbol="AAPL",
                        bid_price=Decimal("150.00"),
                        bid_size=Decimal("10"),
                        ask_price=Decimal("150.15"),
                        ask_size=Decimal("10"),
                        source="TEST",
                    )
                )
        finally:
            storage.close()

    def tearDown(self):
        self.tmp_dir.cleanup()

    def test_generate_market_report_end_to_end(self):
        summary = generate_market_report(
            db_path=self.db_path,
            symbol="AAPL",
            output_path=self.report_path,
        )

        self.assertEqual(summary.symbol, "AAPL")
        self.assertEqual(summary.total_events, 10)
        self.assertEqual(summary.trade_count, 5)
        self.assertEqual(summary.quote_count, 5)
        self.assertEqual(summary.total_volume, Decimal("500"))
        self.assertGreater(summary.final_vwap, Decimal("150.00"))
        self.assertGreater(summary.mean_relative_spread_bps, Decimal("0"))

        # Verify HTML file created
        self.assertTrue(os.path.exists(self.report_path))
        with open(self.report_path, "r", encoding="utf-8") as f:
            content = f.read()

        self.assertIn("<!DOCTYPE html>", content)
        self.assertIn("AAPL", content)
        self.assertIn("Microstructure Report", content)
        self.assertIn("Execution VWAP", content)
        self.assertIn("<svg", content)
        self.assertIn("Cumulative Order Flow Imbalance", content)


if __name__ == "__main__":
    unittest.main()
