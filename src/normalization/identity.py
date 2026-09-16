"""Deterministic event identity generator."""

import hashlib
from typing import Optional


def generate_trade_id(
    symbol: str,
    timestamp_ns: int,
    price_str: str,
    size_str: str,
    side: str,
    source: str,
    sequence_id: Optional[int] = None,
) -> str:
    """
    Generate deterministic SHA-256 hash identifying a TradeEvent.
    """
    seq_part = str(sequence_id) if sequence_id is not None else "NONE"
    payload = f"TRADE|{symbol.upper()}|{timestamp_ns}|{price_str}|{size_str}|{side.upper()}|{source}|{seq_part}"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def generate_quote_id(
    symbol: str,
    timestamp_ns: int,
    bid_price_str: str,
    bid_size_str: str,
    ask_price_str: str,
    ask_size_str: str,
    source: str,
    sequence_id: Optional[int] = None,
) -> str:
    """
    Generate deterministic SHA-256 hash identifying a QuoteEvent.
    """
    seq_part = str(sequence_id) if sequence_id is not None else "NONE"
    payload = (
        f"QUOTE|{symbol.upper()}|{timestamp_ns}|{bid_price_str}|{bid_size_str}|"
        f"{ask_price_str}|{ask_size_str}|{source}|{seq_part}"
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()
