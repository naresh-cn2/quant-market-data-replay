"""Canonical TradeEvent model."""

from dataclasses import dataclass, field
from decimal import Decimal
from enum import Enum
from typing import Any, Dict, Optional

from src.primitives.numeric import format_decimal


class Side(str, Enum):
    BUY = "BUY"
    SELL = "SELL"
    UNKNOWN = "UNKNOWN"

    @classmethod
    def from_str(cls, val: Optional[str]) -> "Side":
        if not val:
            return cls.UNKNOWN
        clean = str(val).strip().upper()
        if clean in ("B", "BUY", "BID", "1"):
            return cls.BUY
        if clean in ("S", "SELL", "ASK", "OFFER", "-1", "2"):
            return cls.SELL
        return cls.UNKNOWN


@dataclass(frozen=True, slots=True)
class TradeEvent:
    """
    Canonical Trade Event.

    Attributes:
    - event_id: Deterministic SHA-256 identifier.
    - symbol: Standardized uppercase instrument identifier.
    - timestamp_ns: UTC nanoseconds since epoch.
    - price: Exact trade price.
    - size: Exact trade quantity.
    - side: Aggressor trade side (BUY, SELL, UNKNOWN).
    - source: Venue / feed identifier.
    - sequence_id: Optional source sequence number.
    - raw_payload: Optional original unparsed data for provenance.
    """
    event_id: str
    symbol: str
    timestamp_ns: int
    price: Decimal
    size: Decimal
    side: Side
    source: str
    sequence_id: Optional[int] = None
    raw_payload: Optional[Dict[str, Any]] = field(default=None, repr=False, compare=False)

    @property
    def event_type(self) -> str:
        return "TRADE"

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation using exact decimal string values."""
        return {
            "event_type": "TRADE",
            "event_id": self.event_id,
            "symbol": self.symbol,
            "timestamp_ns": self.timestamp_ns,
            "price": format_decimal(self.price),
            "size": format_decimal(self.size),
            "side": self.side.value,
            "source": self.source,
            "sequence_id": self.sequence_id,
        }
