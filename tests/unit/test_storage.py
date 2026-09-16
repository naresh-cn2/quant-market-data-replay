"""Unit tests for SQLite storage backend and manifest manager."""

from decimal import Decimal
import os
import tempfile
import unittest

from src.models.trade import TradeEvent, Side
from src.models.quote import QuoteEvent
from src.models.manifest import DatasetManifest
from src.storage.sqlite_store import SqliteStorageBackend
from src.storage.manifest_manager import ManifestManager


class TestStorage(unittest.TestCase):
    def setUp(self):
        self.db = SqliteStorageBackend(":memory:")

    def test_store_and_query_trades(self):
        t1 = TradeEvent("t1", "AAPL", 1_000_000_000, Decimal("150.25"), Decimal("100"), Side.BUY, "NASDAQ")
        t2 = TradeEvent("t2", "AAPL", 2_000_000_000, Decimal("150.50"), Decimal("200"), Side.SELL, "NASDAQ")
        self.db.store_trades_batch([t1, t2])

        events = list(self.db.query_stream("AAPL", 500_000_000, 2_500_000_000, ("TRADE",)))
        self.assertEqual(len(events), 2)
        self.assertEqual(events[0].price, Decimal("150.25"))
        self.assertEqual(events[1].price, Decimal("150.50"))

    def test_store_and_query_quotes(self):
        q1 = QuoteEvent(
            "q1", "AAPL", 1_500_000_000, Decimal("150.20"), Decimal("100"), Decimal("150.25"), Decimal("200"), "NASDAQ"
        )
        self.db.store_quote(q1)

        events = list(self.db.query_stream("AAPL", 1_000_000_000, 2_000_000_000, ("QUOTE",)))
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].bid_price, Decimal("150.20"))

    def test_store_and_get_manifest(self):
        manifest = DatasetManifest(
            dataset_id="DS-TEST-01",
            schema_version="1.0.0",
            created_at_utc="2026-09-16T12:00:00Z",
            source_file="sample.csv",
            total_records=100,
            trade_count=70,
            quote_count=30,
            quarantine_count=0,
            min_timestamp_ns=1_000_000_000,
            max_timestamp_ns=5_000_000_000,
            sha256_checksum="test_sha",
            config_hash="test_cfg",
            symbols=["AAPL"],
        )
        self.db.store_manifest(manifest)
        retrieved = self.db.get_manifest("DS-TEST-01")

        self.assertIsNotNone(retrieved)
        self.assertEqual(retrieved.dataset_id, "DS-TEST-01")
        self.assertEqual(retrieved.total_records, 100)

    def test_duplicate_event_handling_idempotency(self):
        t1 = TradeEvent("dup_trade", "AAPL", 1_000_000_000, Decimal("150.25"), Decimal("100"), Side.BUY, "NASDAQ")
        # Store twice
        self.db.store_trade(t1)
        self.db.store_trade(t1)

        events = list(self.db.query_stream("AAPL", 500_000_000, 1_500_000_000, ("TRADE",)))
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].event_id, "dup_trade")


if __name__ == "__main__":
    unittest.main()
