"""Adversarial tests for deterministic tie-breaking on equal timestamps."""

from decimal import Decimal
import unittest

from src.models.trade import TradeEvent, Side
from src.models.quote import QuoteEvent
from src.replay.engine import ReplayEngine
from src.storage.sqlite_store import SqliteStorageBackend


class TestTieBreaking(unittest.TestCase):
    def test_deterministic_equal_timestamp_ordering(self):
        db = SqliteStorageBackend(":memory:")
        engine = ReplayEngine(db)

        # 3 events sharing the exact same nanosecond timestamp
        shared_ts = 1_789_552_800_000_000_000

        trade_a = TradeEvent("t_alpha", "AAPL", shared_ts, Decimal("150.00"), Decimal("100"), Side.BUY, "NASDAQ")
        trade_b = TradeEvent("t_beta", "AAPL", shared_ts, Decimal("150.05"), Decimal("50"), Side.SELL, "NASDAQ")
        quote_a = QuoteEvent("q_alpha", "AAPL", shared_ts, Decimal("150.00"), Decimal("100"), Decimal("150.05"), Decimal("100"), "NASDAQ")

        # Insert in arbitrary order
        db.store_trades_batch([trade_b, trade_a])
        db.store_quote(quote_a)

        # Replay multiple times to verify 100% deterministic reproducibility
        first_run = [e.event_id for e in engine.replay_stream("AAPL", 0, 2**63 - 1)]
        second_run = [e.event_id for e in engine.replay_stream("AAPL", 0, 2**63 - 1)]

        self.assertEqual(first_run, second_run)
        # Trades have event_type_priority=1, Quotes have event_type_priority=2
        # Within Trades, t_alpha comes before t_beta by event_id
        self.assertEqual(first_run, ["t_alpha", "t_beta", "q_alpha"])


if __name__ == "__main__":
    unittest.main()
