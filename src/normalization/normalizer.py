"""
Market data normalizer.

Maps heterogeneous vendor/exchange payloads to canonical TradeEvent and QuoteEvent
models while enforcing zero binary floating-point contamination.
"""

from decimal import Decimal
import json
import os
from typing import Any, Dict, List, Optional, Tuple, Union

from src.ingestion.reader import RawRecord
from src.models.trade import TradeEvent, Side
from src.models.quote import QuoteEvent
from src.models.quarantine import QuarantineRecord
from src.normalization.identity import generate_trade_id, generate_quote_id
from src.primitives.numeric import parse_decimal, format_decimal
from src.primitives.timestamp import parse_timestamp_ns


class NormalizationError(Exception):
    """Raised when record normalization fails due to invalid syntax or missing required fields."""
    def __init__(self, message: str, code: str = "ERR_NORM_SYNTAX", field_name: Optional[str] = None):
        super().__init__(message)
        self.code = code
        self.field_name = field_name


class EventNormalizer:
    """
    Normalizes raw market data records into canonical TradeEvent or QuoteEvent.
    """

    def __init__(self, schema_mappings_path: Optional[str] = None):
        self.mappings = self._load_mappings(schema_mappings_path)

    def _load_mappings(self, path: Optional[str]) -> Dict[str, Any]:
        if path and os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f).get("default", {})

        # Default alias sets
        return {
            "trade": {
                "symbol": ["symbol", "ticker", "sym", "instrument", "s"],
                "timestamp": ["timestamp", "timestamp_ns", "ts", "time", "datetime", "transact_time", "t"],
                "price": ["price", "px", "last_price", "p", "trade_price"],
                "size": ["size", "qty", "volume", "vol", "sz", "quantity", "trade_size", "v", "q"],
                "side": ["side", "direction", "aggressor_side", "action"],
                "source": ["source", "exchange", "venue", "feed", "src"]
            },
            "quote": {
                "symbol": ["symbol", "ticker", "sym", "instrument", "s"],
                "timestamp": ["timestamp", "timestamp_ns", "ts", "time", "datetime", "quote_time", "t"],
                "bid_price": ["bid_price", "bid_px", "bid", "bidprice", "bp", "best_bid_price", "b"],
                "bid_size": ["bid_size", "bid_sz", "bid_qty", "bidsize", "bs", "best_bid_size", "bq"],
                "ask_price": ["ask_price", "ask_px", "ask", "askprice", "ap", "offer", "best_ask_price", "a"],
                "ask_size": ["ask_size", "ask_sz", "ask_qty", "asksize", "as", "offer_size", "best_ask_size", "aq"],
                "source": ["source", "exchange", "venue", "feed", "src"]
            }
        }

    def _extract_field(self, data: Dict[str, Any], aliases: List[str]) -> Tuple[Optional[str], Any]:
        """Case-insensitive extraction of field by alias list."""
        data_lower = {k.lower(): (k, v) for k, v in data.items()}
        for alias in aliases:
            if alias.lower() in data_lower:
                orig_key, val = data_lower[alias.lower()]
                return orig_key, val
        return None, None

    def detect_event_type(self, data: Dict[str, Any]) -> str:
        """Infer whether record is a TRADE or QUOTE."""
        # Check explicit type field
        type_val = data.get("event_type") or data.get("type") or data.get("record_type")
        if type_val:
            type_str = str(type_val).upper()
            if "TRADE" in type_str or type_str in ("T", "TRD"):
                return "TRADE"
            if "QUOTE" in type_str or type_str in ("Q", "BBO", "NBBO"):
                return "QUOTE"

        # Check quote-specific fields
        quote_keys = self.mappings.get("quote", {})
        for field in ("bid_price", "ask_price", "bid", "ask"):
            aliases = quote_keys.get(field, [field])
            _, val = self._extract_field(data, aliases)
            if val is not None:
                return "QUOTE"

        # Default to TRADE
        return "TRADE"

    def normalize(
        self, raw_record: RawRecord
    ) -> Union[TradeEvent, QuoteEvent, QuarantineRecord]:
        """
        Normalize a raw record into a Canonical event or QuarantineRecord.
        """
        data = raw_record.data

        # Check for reader parsing errors
        if "_parse_error" in data:
            return QuarantineRecord(
                quarantine_id=f"QUAR-{raw_record.line_number}",
                timestamp_ns=0,
                source=raw_record.source_file or "UNKNOWN",
                raw_record=raw_record.raw_text,
                error_code="ERR_PARSE_FAILURE",
                error_message=data["_parse_error"],
                severity="FATAL_SYNTAX",
            )

        event_type = self.detect_event_type(data)

        try:
            if event_type == "QUOTE":
                return self._normalize_quote(raw_record)
            return self._normalize_trade(raw_record)
        except NormalizationError as ne:
            return QuarantineRecord(
                quarantine_id=f"QUAR-{raw_record.line_number}",
                timestamp_ns=0,
                source=raw_record.source_file or "UNKNOWN",
                raw_record=raw_record.raw_text,
                error_code=ne.code,
                error_message=str(ne),
                severity="HARD_INVALID",
                field_name=ne.field_name,
            )
        except Exception as e:
            return QuarantineRecord(
                quarantine_id=f"QUAR-{raw_record.line_number}",
                timestamp_ns=0,
                source=raw_record.source_file or "UNKNOWN",
                raw_record=raw_record.raw_text,
                error_code="ERR_NORM_UNEXPECTED",
                error_message=f"Unexpected normalization failure: {str(e)}",
                severity="HARD_INVALID",
            )

    def _normalize_trade(self, raw_record: RawRecord) -> TradeEvent:
        data = raw_record.data
        trade_aliases = self.mappings.get("trade", {})

        # Symbol
        _, sym_val = self._extract_field(data, trade_aliases.get("symbol", ["symbol"]))
        if sym_val is None or str(sym_val).strip() == "":
            raise NormalizationError("Missing required symbol", "ERR_MISSING_SYMBOL", "symbol")
        symbol = str(sym_val).strip().upper()

        # Timestamp
        _, ts_val = self._extract_field(data, trade_aliases.get("timestamp", ["timestamp"]))
        if ts_val is None:
            raise NormalizationError("Missing required timestamp", "ERR_MISSING_TIMESTAMP", "timestamp")
        try:
            timestamp_ns = parse_timestamp_ns(ts_val)
        except Exception as e:
            raise NormalizationError(f"Invalid timestamp '{ts_val}': {str(e)}", "ERR_INVALID_TIMESTAMP", "timestamp")

        # Price
        _, price_val = self._extract_field(data, trade_aliases.get("price", ["price"]))
        if price_val is None:
            raise NormalizationError("Missing required trade price", "ERR_MISSING_PRICE", "price")
        try:
            price = parse_decimal(price_val, "price")
        except Exception as e:
            raise NormalizationError(f"Invalid trade price '{price_val}': {str(e)}", "ERR_INVALID_PRICE", "price")

        # Size
        _, size_val = self._extract_field(data, trade_aliases.get("size", ["size"]))
        if size_val is None:
            raise NormalizationError("Missing required trade size", "ERR_MISSING_SIZE", "size")
        try:
            size = parse_decimal(size_val, "size")
        except Exception as e:
            raise NormalizationError(f"Invalid trade size '{size_val}': {str(e)}", "ERR_INVALID_SIZE", "size")

        # Side
        _, side_val = self._extract_field(data, trade_aliases.get("side", ["side"]))
        side = Side.from_str(str(side_val) if side_val is not None else None)

        # Source
        _, src_val = self._extract_field(data, trade_aliases.get("source", ["source"]))
        source = str(src_val).strip() if src_val is not None else (raw_record.source_file or "DEFAULT")

        # Sequence ID
        seq_id = None
        if "sequence_id" in data or "seq" in data:
            raw_seq = data.get("sequence_id", data.get("seq"))
            if raw_seq is not None and str(raw_seq).isdigit():
                seq_id = int(raw_seq)

        event_id = generate_trade_id(
            symbol=symbol,
            timestamp_ns=timestamp_ns,
            price_str=format_decimal(price),
            size_str=format_decimal(size),
            side=side.value,
            source=source,
            sequence_id=seq_id,
        )

        return TradeEvent(
            event_id=event_id,
            symbol=symbol,
            timestamp_ns=timestamp_ns,
            price=price,
            size=size,
            side=side,
            source=source,
            sequence_id=seq_id,
            raw_payload=data,
        )

    def _normalize_quote(self, raw_record: RawRecord) -> QuoteEvent:
        data = raw_record.data
        quote_aliases = self.mappings.get("quote", {})

        # Symbol
        _, sym_val = self._extract_field(data, quote_aliases.get("symbol", ["symbol"]))
        if sym_val is None or str(sym_val).strip() == "":
            raise NormalizationError("Missing required symbol", "ERR_MISSING_SYMBOL", "symbol")
        symbol = str(sym_val).strip().upper()

        # Timestamp
        _, ts_val = self._extract_field(data, quote_aliases.get("timestamp", ["timestamp"]))
        if ts_val is None:
            raise NormalizationError("Missing required timestamp", "ERR_MISSING_TIMESTAMP", "timestamp")
        try:
            timestamp_ns = parse_timestamp_ns(ts_val)
        except Exception as e:
            raise NormalizationError(f"Invalid timestamp '{ts_val}': {str(e)}", "ERR_INVALID_TIMESTAMP", "timestamp")

        # Bid Price
        _, bp_val = self._extract_field(data, quote_aliases.get("bid_price", ["bid_price"]))
        if bp_val is None:
            raise NormalizationError("Missing required bid_price", "ERR_MISSING_BID_PRICE", "bid_price")
        try:
            bid_price = parse_decimal(bp_val, "bid_price")
        except Exception as e:
            raise NormalizationError(f"Invalid bid_price '{bp_val}': {str(e)}", "ERR_INVALID_BID_PRICE", "bid_price")

        # Bid Size
        _, bs_val = self._extract_field(data, quote_aliases.get("bid_size", ["bid_size"]))
        if bs_val is None:
            raise NormalizationError("Missing required bid_size", "ERR_MISSING_BID_SIZE", "bid_size")
        try:
            bid_size = parse_decimal(bs_val, "bid_size")
        except Exception as e:
            raise NormalizationError(f"Invalid bid_size '{bs_val}': {str(e)}", "ERR_INVALID_BID_SIZE", "bid_size")

        # Ask Price
        _, ap_val = self._extract_field(data, quote_aliases.get("ask_price", ["ask_price"]))
        if ap_val is None:
            raise NormalizationError("Missing required ask_price", "ERR_MISSING_ASK_PRICE", "ask_price")
        try:
            ask_price = parse_decimal(ap_val, "ask_price")
        except Exception as e:
            raise NormalizationError(f"Invalid ask_price '{ap_val}': {str(e)}", "ERR_INVALID_ASK_PRICE", "ask_price")

        # Ask Size
        _, as_val = self._extract_field(data, quote_aliases.get("ask_size", ["ask_size"]))
        if as_val is None:
            raise NormalizationError("Missing required ask_size", "ERR_MISSING_ASK_SIZE", "ask_size")
        try:
            ask_size = parse_decimal(as_val, "ask_size")
        except Exception as e:
            raise NormalizationError(f"Invalid ask_size '{as_val}': {str(e)}", "ERR_INVALID_ASK_SIZE", "ask_size")

        # Source
        _, src_val = self._extract_field(data, quote_aliases.get("source", ["source"]))
        source = str(src_val).strip() if src_val is not None else (raw_record.source_file or "DEFAULT")

        # Sequence ID
        seq_id = None
        if "sequence_id" in data or "seq" in data:
            raw_seq = data.get("sequence_id", data.get("seq"))
            if raw_seq is not None and str(raw_seq).isdigit():
                seq_id = int(raw_seq)

        event_id = generate_quote_id(
            symbol=symbol,
            timestamp_ns=timestamp_ns,
            bid_price_str=format_decimal(bid_price),
            bid_size_str=format_decimal(bid_size),
            ask_price_str=format_decimal(ask_price),
            ask_size_str=format_decimal(ask_size),
            source=source,
            sequence_id=seq_id,
        )

        return QuoteEvent(
            event_id=event_id,
            symbol=symbol,
            timestamp_ns=timestamp_ns,
            bid_price=bid_price,
            bid_size=bid_size,
            ask_price=ask_price,
            ask_size=ask_size,
            source=source,
            sequence_id=seq_id,
            raw_payload=data,
        )
