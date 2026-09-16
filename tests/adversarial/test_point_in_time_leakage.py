"""Adversarial tests for point-in-time boundary violations and future event leakage."""

from decimal import Decimal
import unittest

from src.models.trade import TradeEvent, Side
from src.replay.engine import ReplayEngine
from src.storage.sqlite_store import SqliteStorageBackend


class TestPointInTimeLeakage(unittest.TestCase):
    def setUp(self):
        self.db = SqliteStorageBackend(":memory:")
        self.engine = ReplayEngine(self.db)

        # Store 10 trades at 1-second intervals from 1s to 10s
        trades = [
            TradeEvent(
                f"t{i}",
                "AAPL",
                i * 1_000_000_000,
                Decimal(f"150.{i:02d}"),
                Decimal("100"),
                Side.BUY,
                "NASDAQ",
            )
            for i in range(1, 11)
        ]
        self.db.store_trades_batch(trades)

    def test_zero_future_leakage(self):
        # Query window strictly up to 5.0 seconds
        query_start = 1_000_000_000
        query_end = 5_000_000_000

        replayed = list(self.engine.replay_stream("AAPL", query_start, query_end))

        # Must return exactly 5 events (t1 through t5)
        self.assertEqual(len(replayed), 5)
        self.assertEqual([e.event_id for e in replayed], ["t1", "t2", "t3", "t4", "t5"])

        # Assert no event has timestamp > 5_000_000_000
        for ev in replayed:
            self.assertLessEqual(ev.timestamp_ns, query_end)
            self.assertGreaterEqual(ev.timestamp_ns, query_start)


if __name__ == "__main__":
    unittest.main()
