"""Unit tests for deterministic replay engine and point-in-time guard."""

from decimal import Decimal
import unittest

from src.models.trade import TradeEvent, Side
from src.models.quote import QuoteEvent
from src.replay.engine import ReplayEngine
from src.replay.point_in_time import PointInTimeGuard
from src.storage.sqlite_store import SqliteStorageBackend


class TestReplayEngine(unittest.TestCase):
    def setUp(self):
        self.db = SqliteStorageBackend(":memory:")
        self.engine = ReplayEngine(self.db)

        # Populate events
        self.db.store_trades_batch([
            TradeEvent("t1", "AAPL", 1_000_000_000, Decimal("150.00"), Decimal("100"), Side.BUY, "NASDAQ"),
            TradeEvent("t2", "AAPL", 2_000_000_000, Decimal("150.10"), Decimal("100"), Side.BUY, "NASDAQ"),
            TradeEvent("t3", "AAPL", 3_000_000_000, Decimal("150.20"), Decimal("100"), Side.BUY, "NASDAQ"),
        ])
        self.db.store_quotes_batch([
            QuoteEvent("q1", "AAPL", 1_500_000_000, Decimal("150.00"), Decimal("50"), Decimal("150.10"), Decimal("50"), "NASDAQ"),
            QuoteEvent("q2", "AAPL", 2_500_000_000, Decimal("150.10"), Decimal("50"), Decimal("150.20"), Decimal("50"), "NASDAQ"),
        ])

    def test_deterministic_interleaved_replay(self):
        events = list(self.engine.replay_stream("AAPL", 500_000_000, 3_500_000_000))
        self.assertEqual(len(events), 5)

        # Expected chronological order: t1 (1.0s) -> q1 (1.5s) -> t2 (2.0s) -> q2 (2.5s) -> t3 (3.0s)
        expected_ids = ["t1", "q1", "t2", "q2", "t3"]
        actual_ids = [e.event_id for e in events]
        self.assertEqual(actual_ids, expected_ids)

    def test_replay_window_boundary_enforcement(self):
        # Only query between 1.2s and 2.2s -> should return q1 (1.5s) and t2 (2.0s)
        events = list(self.engine.replay_stream("AAPL", 1_200_000_000, 2_200_000_000))
        self.assertEqual(len(events), 2)
        self.assertEqual(events[0].event_id, "q1")
        self.assertEqual(events[1].event_id, "t2")

    def test_point_in_time_guard_boundary(self):
        guard = PointInTimeGuard(1_000_000_000, 2_000_000_000)
        t_inside = TradeEvent("t_in", "AAPL", 1_500_000_000, Decimal("100"), Decimal("10"), Side.BUY, "TEST")
        t_future = TradeEvent("t_out", "AAPL", 2_500_000_000, Decimal("100"), Decimal("10"), Side.BUY, "TEST")

        self.assertTrue(guard.is_visible(t_inside))
        self.assertFalse(guard.is_visible(t_future))


if __name__ == "__main__":
    unittest.main()
