"""Unit tests for normalization and event identity."""

from decimal import Decimal
import unittest

from src.ingestion.reader import RawRecord
from src.models.trade import TradeEvent, Side
from src.models.quote import QuoteEvent
from src.models.quarantine import QuarantineRecord
from src.normalization.identity import generate_trade_id, generate_quote_id
from src.normalization.normalizer import EventNormalizer


class TestNormalization(unittest.TestCase):
    def setUp(self):
        self.normalizer = EventNormalizer()

    def test_normalize_valid_trade(self):
        raw = RawRecord(
            line_number=1,
            raw_text="2026-09-16T10:00:00Z,AAPL,150.25,100,BUY,NASDAQ",
            data={
                "timestamp": "2026-09-16T10:00:00Z",
                "symbol": "aapl",
                "price": "150.25",
                "size": "100",
                "side": "BUY",
                "source": "NASDAQ",
            },
        )
        event = self.normalizer.normalize(raw)
        self.assertIsInstance(event, TradeEvent)
        self.assertEqual(event.symbol, "AAPL")
        self.assertEqual(event.price, Decimal("150.25"))
        self.assertEqual(event.size, Decimal("100"))
        self.assertEqual(event.side, Side.BUY)
        self.assertEqual(event.source, "NASDAQ")
        self.assertTrue(len(event.event_id) == 64)

    def test_normalize_valid_quote(self):
        raw = RawRecord(
            line_number=1,
            raw_text="2026-09-16T10:00:00Z,MSFT,320.00,100,320.10,200,NYSE",
            data={
                "timestamp": "2026-09-16T10:00:00Z",
                "symbol": "msft",
                "bid_price": "320.00",
                "bid_size": "100",
                "ask_price": "320.10",
                "ask_size": "200",
                "source": "NYSE",
            },
        )
        event = self.normalizer.normalize(raw)
        self.assertIsInstance(event, QuoteEvent)
        self.assertEqual(event.symbol, "MSFT")
        self.assertEqual(event.bid_price, Decimal("320.00"))
        self.assertEqual(event.ask_price, Decimal("320.10"))

    def test_normalize_missing_fields_returns_quarantine(self):
        raw = RawRecord(
            line_number=5,
            raw_text="2026-09-16T10:00:00Z,,150.25,100,BUY,NASDAQ",
            data={
                "timestamp": "2026-09-16T10:00:00Z",
                "symbol": "",
                "price": "150.25",
                "size": "100",
            },
        )
        result = self.normalizer.normalize(raw)
        self.assertIsInstance(result, QuarantineRecord)
        self.assertEqual(result.error_code, "ERR_MISSING_SYMBOL")
        self.assertEqual(result.raw_record, raw.raw_text)

    def test_deterministic_event_identity(self):
        id1 = generate_trade_id("AAPL", 1789552800000000000, "150.25", "100", "BUY", "NASDAQ")
        id2 = generate_trade_id("AAPL", 1789552800000000000, "150.25", "100", "BUY", "NASDAQ")
        id3 = generate_trade_id("AAPL", 1789552800000000000, "150.26", "100", "BUY", "NASDAQ")

        self.assertEqual(id1, id2)
        self.assertNotEqual(id1, id3)


if __name__ == "__main__":
    unittest.main()
