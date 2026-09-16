"""Unit tests for market data validation rules and diagnostics."""

from decimal import Decimal
import unittest

from src.models.trade import TradeEvent, Side
from src.models.quote import QuoteEvent
from src.models.validation import ValidationStatus
from src.validation.engine import MarketDataValidator
from src.validation.rules import MarketDataValidationRules


class TestValidation(unittest.TestCase):
    def setUp(self):
        self.validator = MarketDataValidator()

    def test_valid_trade_accepted(self):
        trade = TradeEvent(
            event_id="t1",
            symbol="AAPL",
            timestamp_ns=1789552800000000000,
            price=Decimal("150.25"),
            size=Decimal("100"),
            side=Side.BUY,
            source="NASDAQ",
        )
        res = self.validator.validate_event(trade)
        self.assertEqual(res.status, ValidationStatus.ACCEPTED)
        self.assertTrue(res.is_valid)

    def test_negative_trade_price_hard_invalid(self):
        trade = TradeEvent(
            event_id="t2",
            symbol="AAPL",
            timestamp_ns=1789552800000000000,
            price=Decimal("-10.00"),
            size=Decimal("100"),
            side=Side.BUY,
            source="NASDAQ",
        )
        res = self.validator.validate_event(trade)
        self.assertEqual(res.status, ValidationStatus.HARD_INVALID)
        self.assertFalse(res.is_valid)
        self.assertEqual(res.diagnostics[0].code, "ERR_NON_POSITIVE_PRICE")

    def test_zero_trade_size_hard_invalid(self):
        trade = TradeEvent(
            event_id="t3",
            symbol="AAPL",
            timestamp_ns=1789552800000000000,
            price=Decimal("150.00"),
            size=Decimal("0"),
            side=Side.BUY,
            source="NASDAQ",
        )
        res = self.validator.validate_event(trade)
        self.assertEqual(res.status, ValidationStatus.HARD_INVALID)
        self.assertEqual(res.diagnostics[0].code, "ERR_NON_POSITIVE_SIZE")

    def test_crossed_quote_is_soft_warning(self):
        quote = QuoteEvent(
            event_id="q1",
            symbol="AAPL",
            timestamp_ns=1789552800000000000,
            bid_price=Decimal("150.30"),
            bid_size=Decimal("100"),
            ask_price=Decimal("150.20"),
            ask_size=Decimal("100"),
            source="NASDAQ",
        )
        res = self.validator.validate_event(quote)
        self.assertEqual(res.status, ValidationStatus.SOFT_WARNING)
        self.assertTrue(res.is_valid)
        self.assertEqual(res.diagnostics[0].code, "WARN_CROSSED_MARKET")

    def test_large_price_jump_is_soft_warning(self):
        trade1 = TradeEvent(
            event_id="t4",
            symbol="AAPL",
            timestamp_ns=1789552800000000000,
            price=Decimal("100.00"),
            size=Decimal("100"),
            side=Side.BUY,
            source="NASDAQ",
        )
        trade2 = TradeEvent(
            event_id="t5",
            symbol="AAPL",
            timestamp_ns=1789552801000000000,
            price=Decimal("150.00"),  # +50% jump
            size=Decimal("100"),
            side=Side.BUY,
            source="NASDAQ",
        )
        self.validator.validate_event(trade1)
        res2 = self.validator.validate_event(trade2)

        self.assertEqual(res2.status, ValidationStatus.SOFT_WARNING)
        self.assertTrue(res2.is_valid)
        self.assertEqual(res2.diagnostics[0].code, "WARN_LARGE_PRICE_JUMP")


if __name__ == "__main__":
    unittest.main()
