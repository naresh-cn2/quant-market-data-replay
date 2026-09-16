"""Unit tests for canonical domain models."""

from decimal import Decimal
import unittest

from src.models.trade import TradeEvent, Side
from src.models.quote import QuoteEvent
from src.models.validation import ValidationResult, ValidationStatus, DiagnosticRecord
from src.models.quarantine import QuarantineRecord
from src.models.manifest import DatasetManifest


class TestDomainModels(unittest.TestCase):
    def test_trade_event_creation_and_dict(self):
        trade = TradeEvent(
            event_id="test_trade_123",
            symbol="AAPL",
            timestamp_ns=1789552800000000000,
            price=Decimal("150.25"),
            size=Decimal("100"),
            side=Side.BUY,
            source="NASDAQ",
        )
        self.assertEqual(trade.event_type, "TRADE")
        self.assertEqual(trade.symbol, "AAPL")
        self.assertEqual(trade.price, Decimal("150.25"))

        d = trade.to_dict()
        self.assertEqual(d["event_type"], "TRADE")
        self.assertEqual(d["price"], "150.25")
        self.assertEqual(d["size"], "100")
        self.assertEqual(d["side"], "BUY")

    def test_quote_event_creation_and_properties(self):
        quote = QuoteEvent(
            event_id="test_quote_123",
            symbol="AAPL",
            timestamp_ns=1789552800000000000,
            bid_price=Decimal("150.20"),
            bid_size=Decimal("500"),
            ask_price=Decimal("150.25"),
            ask_size=Decimal("600"),
            source="NASDAQ",
        )
        self.assertEqual(quote.event_type, "QUOTE")
        self.assertFalse(quote.is_crossed)
        self.assertFalse(quote.is_locked)
        self.assertEqual(quote.spread, Decimal("0.05"))

        crossed_quote = QuoteEvent(
            event_id="test_quote_456",
            symbol="AAPL",
            timestamp_ns=1789552800000000000,
            bid_price=Decimal("150.30"),
            bid_size=Decimal("500"),
            ask_price=Decimal("150.20"),
            ask_size=Decimal("600"),
            source="NASDAQ",
        )
        self.assertTrue(crossed_quote.is_crossed)

    def test_validation_result_logic(self):
        res = ValidationResult()
        self.assertEqual(res.status, ValidationStatus.ACCEPTED)
        self.assertTrue(res.is_valid)

        res.add_warning("WARN_01", "Minor warning", "price")
        self.assertEqual(res.status, ValidationStatus.SOFT_WARNING)
        self.assertTrue(res.is_valid)
        self.assertTrue(res.has_warnings)

        res.add_error("ERR_01", "Fatal error", "size")
        self.assertEqual(res.status, ValidationStatus.HARD_INVALID)
        self.assertFalse(res.is_valid)

    def test_quarantine_record_serialization(self):
        rec = QuarantineRecord(
            quarantine_id="Q-001",
            timestamp_ns=1789552800000000000,
            source="TEST",
            raw_record="corrupt,line,data",
            error_code="ERR_PARSE",
            error_message="Bad data",
        )
        d = rec.to_dict()
        self.assertEqual(d["quarantine_id"], "Q-001")
        self.assertEqual(d["error_code"], "ERR_PARSE")

    def test_manifest_serialization(self):
        manifest = DatasetManifest(
            dataset_id="DS-001",
            schema_version="1.0.0",
            created_at_utc="2026-09-16T10:00:00Z",
            source_file="test.csv",
            total_records=100,
            trade_count=60,
            quote_count=35,
            quarantine_count=5,
            min_timestamp_ns=1000,
            max_timestamp_ns=5000,
            sha256_checksum="abc123hash",
            config_hash="cfg123hash",
            symbols=["AAPL", "MSFT"],
        )
        d = manifest.to_dict()
        self.assertEqual(d["total_records"], 100)
        self.assertEqual(d["symbols"], ["AAPL", "MSFT"])


if __name__ == "__main__":
    unittest.main()
