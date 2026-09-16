"""Adversarial tests for extreme out-of-order and lateness scenarios."""

from decimal import Decimal
import unittest

from src.models.trade import TradeEvent, Side
from src.reorder.bounded_buffer import BoundedReorderBuffer


class TestExtremeLateness(unittest.TestCase):
    def test_massive_lateness_stream(self):
        # 2-second max lateness window = 2_000_000_000 ns
        buf = BoundedReorderBuffer(max_lateness_ns=2_000_000_000)

        # Base time
        base_ts = 1_000_000_000_000

        # Event 1: at base_ts
        t1 = TradeEvent("t1", "AAPL", base_ts, Decimal("100"), Decimal("10"), Side.BUY, "TEST")
        buf.process_event(t1)

        # Event 2: advances clock by 10 seconds -> watermark is base_ts + 8s
        t2 = TradeEvent("t2", "AAPL", base_ts + 10_000_000_000, Decimal("101"), Decimal("10"), Side.BUY, "TEST")
        ready2, _ = buf.process_event(t2)
        # t1 should be emitted
        self.assertEqual(len(ready2), 1)
        self.assertEqual(ready2[0].event_id, "t1")

        # Event 3: arrives with timestamp base_ts + 1s (7 seconds behind watermark)
        t_late = TradeEvent("t_late", "AAPL", base_ts + 1_000_000_000, Decimal("102"), Decimal("10"), Side.BUY, "TEST")
        ready3, late_rec = buf.process_event(t_late)

        self.assertEqual(len(ready3), 0)
        self.assertIsNotNone(late_rec)
        self.assertEqual(late_rec.error_code, "ERR_EXCESSIVE_LATENESS")

        # Drain buffer
        flushed = list(buf.flush())
        self.assertEqual(len(flushed), 1)
        self.assertEqual(flushed[0].event_id, "t2")


if __name__ == "__main__":
    unittest.main()
