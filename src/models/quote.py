"""Canonical QuoteEvent model."""

from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any, Dict, Optional

from src.primitives.numeric import format_decimal


@dataclass(frozen=True, slots=True)
class QuoteEvent:
    """
    Canonical Quote Event (Best Bid / Offer).

    Attributes:
    - event_id: Deterministic SHA-256 identifier.
    - symbol: Standardized uppercase instrument identifier.
    - timestamp_ns: UTC nanoseconds since epoch.
    - bid_price: Exact best bid price.
    - bid_size: Exact best bid quantity.
    - ask_price: Exact best ask price.
    - ask_size: Exact best ask quantity.
    - source: Venue / feed identifier.
    - sequence_id: Optional source sequence number.
    - raw_payload: Optional original unparsed data for provenance.
    """
    event_id: str
    symbol: str
    timestamp_ns: int
    bid_price: Decimal
    bid_size: Decimal
    ask_price: Decimal
    ask_size: Decimal
    source: str
    sequence_id: Optional[int] = None
    raw_payload: Optional[Dict[str, Any]] = field(default=None, repr=False, compare=False)

    @property
    def event_type(self) -> str:
        return "QUOTE"

    @property
    def is_crossed(self) -> bool:
        """Returns True if ask_price < bid_price (crossed market)."""
        return self.ask_price < self.bid_price

    @property
    def is_locked(self) -> bool:
        """Returns True if ask_price == bid_price (locked market)."""
        return self.ask_price == self.bid_price

    @property
    def spread(self) -> Decimal:
        """Returns bid-ask spread: ask_price - bid_price."""
        return self.ask_price - self.bid_price

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation using exact decimal string values."""
        return {
            "event_type": "QUOTE",
            "event_id": self.event_id,
            "symbol": self.symbol,
            "timestamp_ns": self.timestamp_ns,
            "bid_price": format_decimal(self.bid_price),
            "bid_size": format_decimal(self.bid_size),
            "ask_price": format_decimal(self.ask_price),
            "ask_size": format_decimal(self.ask_size),
            "source": self.source,
            "sequence_id": self.sequence_id,
        }
