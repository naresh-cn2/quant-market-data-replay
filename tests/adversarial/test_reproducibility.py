"""Adversarial reproducibility test."""

import os
import tempfile
import unittest

from src.pipeline import MarketDataPipeline
from src.replay.engine import ReplayEngine
from src.storage.sqlite_store import SqliteStorageBackend


class TestReproducibility(unittest.TestCase):
    def test_deterministic_reproducibility_across_databases(self):
        fixtures_dir = os.path.join(os.path.dirname(__file__), "..", "fixtures")
        csv_file = os.path.join(fixtures_dir, "sample_trades.csv")

        # Database 1
        db1_path = tempfile.NamedTemporaryFile(delete=False, suffix=".db").name
        # Database 2
        db2_path = tempfile.NamedTemporaryFile(delete=False, suffix=".db").name

        try:
            store1 = SqliteStorageBackend(db1_path)
            pipeline1 = MarketDataPipeline(storage=store1)
            manifest1 = pipeline1.process_file(csv_file)

            store2 = SqliteStorageBackend(db2_path)
            pipeline2 = MarketDataPipeline(storage=store2)
            manifest2 = pipeline2.process_file(csv_file)

            # Assert manifest properties match deterministically
            self.assertEqual(manifest1.sha256_checksum, manifest2.sha256_checksum)
            self.assertEqual(manifest1.config_hash, manifest2.config_hash)
            self.assertEqual(manifest1.total_records, manifest2.total_records)
            self.assertEqual(manifest1.trade_count, manifest2.trade_count)
            self.assertEqual(manifest1.quote_count, manifest2.quote_count)
            self.assertEqual(manifest1.min_timestamp_ns, manifest2.min_timestamp_ns)
            self.assertEqual(manifest1.max_timestamp_ns, manifest2.max_timestamp_ns)

            # Replay and assert identical event stream
            rep1 = list(ReplayEngine(store1).replay_stream("AAPL", 0, 2**63 - 1))
            rep2 = list(ReplayEngine(store2).replay_stream("AAPL", 0, 2**63 - 1))

            self.assertEqual(len(rep1), len(rep2))
            for e1, e2 in zip(rep1, rep2):
                self.assertEqual(e1.event_id, e2.event_id)
                self.assertEqual(e1.timestamp_ns, e2.timestamp_ns)
                self.assertEqual(e1.price, e2.price)
                self.assertEqual(e1.size, e2.size)
                self.assertEqual(e1.side, e2.side)

            store1.close()
            store2.close()
        finally:
            if os.path.exists(db1_path):
                os.remove(db1_path)
            if os.path.exists(db2_path):
                os.remove(db2_path)


if __name__ == "__main__":
    unittest.main()
