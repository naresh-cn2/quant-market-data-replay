"""Integration tests for the complete market data pipeline."""

from decimal import Decimal
import os
import tempfile
import unittest

from src.pipeline import MarketDataPipeline
from src.replay.engine import ReplayEngine
from src.storage.sqlite_store import SqliteStorageBackend


class TestEndToEndPipeline(unittest.TestCase):
    def setUp(self):
        self.fixtures_dir = os.path.join(os.path.dirname(__file__), "..", "fixtures")
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix=".db").name
        self.storage = SqliteStorageBackend(self.temp_db)
        self.pipeline = MarketDataPipeline(storage=self.storage)

    def tearDown(self):
        self.storage.close()
        if os.path.exists(self.temp_db):
            os.remove(self.temp_db)

    def test_pipeline_csv_ingest_and_replay(self):
        csv_file = os.path.join(self.fixtures_dir, "sample_trades.csv")
        manifest = self.pipeline.process_file(csv_file)

        self.assertEqual(manifest.total_records, 5)
        self.assertEqual(manifest.trade_count, 5)
        self.assertEqual(manifest.quote_count, 0)
        self.assertEqual(manifest.quarantine_count, 0)
        self.assertIn("AAPL", manifest.symbols)
        self.assertIn("MSFT", manifest.symbols)

        # Replay AAPL trades
        engine = ReplayEngine(self.storage)
        aapl_events = list(engine.replay_stream("AAPL", 0, 2**63 - 1))
        self.assertEqual(len(aapl_events), 3)
        self.assertEqual(aapl_events[0].price, Decimal("150.25"))

        # Replay MSFT trades
        msft_events = list(engine.replay_stream("MSFT", 0, 2**63 - 1))
        self.assertEqual(len(msft_events), 2)
        self.assertEqual(msft_events[0].price, Decimal("320.10"))

    def test_pipeline_malformed_csv_quarantine_integrity(self):
        malformed_csv = os.path.join(self.fixtures_dir, "malformed_data.csv")
        manifest = self.pipeline.process_file(malformed_csv)

        # Malformed CSV contains 7 lines:
        # Valid: line 1 (150.25), line 7 (150.75) -> 2 valid
        # Invalid: invalid ts, missing sym, negative px, zero sz, corrupt columns -> 5 quarantined
        self.assertEqual(manifest.total_records, 7)
        self.assertEqual(manifest.trade_count, 2)
        self.assertEqual(manifest.quarantine_count, 5)


if __name__ == "__main__":
    unittest.main()
