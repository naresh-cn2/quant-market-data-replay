"""Unit tests for bounded event reordering buffer."""

from decimal import Decimal
import unittest

from src.models.trade import TradeEvent, Side
from src.reorder.bounded_buffer import BoundedReorderBuffer


class TestBoundedReorderBuffer(unittest.TestCase):
    def test_in_order_events_buffered_and_flushed(self):
        # 1-second max lateness window
        buf = BoundedReorderBuffer(max_lateness_ns=1_000_000_000)

        t1 = TradeEvent("t1", "AAPL", 1_000_000_000, Decimal("100"), Decimal("10"), Side.BUY, "TEST")
        t2 = TradeEvent("t2", "AAPL", 1_500_000_000, Decimal("101"), Decimal("10"), Side.BUY, "TEST")
        t3 = TradeEvent("t3", "AAPL", 2_500_000_000, Decimal("102"), Decimal("10"), Side.BUY, "TEST")

        ready1, late1 = buf.process_event(t1)
        self.assertEqual(len(ready1), 0)
        self.assertIsNone(late1)

        ready2, late2 = buf.process_event(t2)
        self.assertEqual(len(ready2), 0)

        # t3 watermark becomes 2.5s - 1.0s = 1.5s -> t1 (1.0s) and t2 (1.5s) are ready
        ready3, late3 = buf.process_event(t3)
        self.assertEqual(len(ready3), 2)
        self.assertEqual(ready3[0].event_id, "t1")
        self.assertEqual(ready3[1].event_id, "t2")

        # Flush drains t3
        flushed = list(buf.flush())
        self.assertEqual(len(flushed), 1)
        self.assertEqual(flushed[0].event_id, "t3")

    def test_out_of_order_within_window_reordered(self):
        buf = BoundedReorderBuffer(max_lateness_ns=5_000_000_000)

        # Send t2 (2s) first, then t1 (1s)
        t2 = TradeEvent("t2", "AAPL", 2_000_000_000, Decimal("100"), Decimal("10"), Side.BUY, "TEST")
        t1 = TradeEvent("t1", "AAPL", 1_000_000_000, Decimal("100"), Decimal("10"), Side.BUY, "TEST")

        buf.process_event(t2)
        buf.process_event(t1)

        flushed = list(buf.flush())
        self.assertEqual(len(flushed), 2)
        # Verify strict timestamp ordering: t1 before t2
        self.assertEqual(flushed[0].event_id, "t1")
        self.assertEqual(flushed[1].event_id, "t2")

    def test_excessive_lateness_rejected_to_quarantine(self):
        buf = BoundedReorderBuffer(max_lateness_ns=1_000_000_000)

        t_future = TradeEvent("tf", "AAPL", 10_000_000_000, Decimal("100"), Decimal("10"), Side.BUY, "TEST")
        buf.process_event(t_future)
        # Watermark is now 10s - 1s = 9s

        # Event arriving at 5s is older than watermark 9s
        t_late = TradeEvent("tlate", "AAPL", 5_000_000_000, Decimal("100"), Decimal("10"), Side.BUY, "TEST")
        ready, late_rec = buf.process_event(t_late)

        self.assertEqual(len(ready), 0)
        self.assertIsNotNone(late_rec)
        self.assertEqual(late_rec.error_code, "ERR_EXCESSIVE_LATENESS")


if __name__ == "__main__":
    unittest.main()
