"""Validation rules and thresholds for canonical market data events."""

from decimal import Decimal
from typing import Dict, Optional, Union

from src.models.trade import TradeEvent
from src.models.quote import QuoteEvent
from src.models.validation import ValidationResult


class MarketDataValidationRules:
    """
    Validation rules distinguishing HARD_INVALID errors from SOFT_WARNING anomalies.
    """

    def __init__(
        self,
        allow_crossed_quotes: bool = True,
        price_jump_threshold_ratio: Decimal = Decimal("0.20"),
    ):
        self.allow_crossed_quotes = allow_crossed_quotes
        self.price_jump_threshold_ratio = price_jump_threshold_ratio
        # Track last valid price per symbol for price jump detection
        self._last_prices: Dict[str, Decimal] = {}

    def validate(self, event: Union[TradeEvent, QuoteEvent]) -> ValidationResult:
        result = ValidationResult()

        if isinstance(event, TradeEvent):
            self._validate_trade(event, result)
        elif isinstance(event, QuoteEvent):
            self._validate_quote(event, result)
        else:
            result.add_error("ERR_UNKNOWN_EVENT_TYPE", f"Unknown event type: {type(event).__name__}")

        return result

    def _validate_trade(self, trade: TradeEvent, result: ValidationResult) -> None:
        # Hard check: Symbol
        if not trade.symbol or not trade.symbol.strip():
            result.add_error("ERR_INVALID_SYMBOL", "Trade symbol is empty", "symbol")

        # Hard check: Timestamp
        if trade.timestamp_ns <= 0:
            result.add_error("ERR_INVALID_TIMESTAMP", f"Timestamp must be > 0, got {trade.timestamp_ns}", "timestamp_ns")

        # Hard check: Price <= 0
        if trade.price <= Decimal(0):
            result.add_error("ERR_NON_POSITIVE_PRICE", f"Trade price must be > 0, got {trade.price}", "price")

        # Hard check: Size <= 0
        if trade.size <= Decimal(0):
            result.add_error("ERR_NON_POSITIVE_SIZE", f"Trade size must be > 0, got {trade.size}", "size")

        # Soft check: Large price jump
        if trade.symbol in self._last_prices and trade.price > Decimal(0):
            last_px = self._last_prices[trade.symbol]
            if last_px > Decimal(0):
                pct_change = abs(trade.price - last_px) / last_px
                if pct_change >= self.price_jump_threshold_ratio:
                    result.add_warning(
                        "WARN_LARGE_PRICE_JUMP",
                        f"Trade price {trade.price} shifted {pct_change * 100:.2f}% from previous {last_px}",
                        "price",
                    )

        if result.is_valid:
            self._last_prices[trade.symbol] = trade.price

    def _validate_quote(self, quote: QuoteEvent, result: ValidationResult) -> None:
        # Hard check: Symbol
        if not quote.symbol or not quote.symbol.strip():
            result.add_error("ERR_INVALID_SYMBOL", "Quote symbol is empty", "symbol")

        # Hard check: Timestamp
        if quote.timestamp_ns <= 0:
            result.add_error("ERR_INVALID_TIMESTAMP", f"Timestamp must be > 0, got {quote.timestamp_ns}", "timestamp_ns")

        # Hard check: Bid / Ask prices cannot be negative (< 0)
        if quote.bid_price < Decimal(0):
            result.add_error("ERR_NEGATIVE_BID_PRICE", f"Bid price cannot be negative, got {quote.bid_price}", "bid_price")
        if quote.ask_price < Decimal(0):
            result.add_error("ERR_NEGATIVE_ASK_PRICE", f"Ask price cannot be negative, got {quote.ask_price}", "ask_price")

        # Hard check: Bid / Ask size must be strictly positive (> 0)
        if quote.bid_size <= Decimal(0):
            result.add_error("ERR_NON_POSITIVE_BID_SIZE", f"Bid size must be > 0, got {quote.bid_size}", "bid_size")
        if quote.ask_size <= Decimal(0):
            result.add_error("ERR_NON_POSITIVE_ASK_SIZE", f"Ask size must be > 0, got {quote.ask_size}", "ask_size")

        # Soft check: Zero bid price (e.g. deep out of money / wide market)
        if quote.bid_price == Decimal(0):
            result.add_warning("WARN_ZERO_BID_PRICE", "Bid price is 0 (one-sided market)", "bid_price")

        # Soft check: Locked market (bid == ask)
        if quote.is_locked:
            result.add_warning("WARN_LOCKED_MARKET", f"Locked market: bid {quote.bid_price} == ask {quote.ask_price}")

        # Soft check: Crossed market (ask < bid)
        if quote.is_crossed:
            if self.allow_crossed_quotes:
                result.add_warning(
                    "WARN_CROSSED_MARKET",
                    f"Crossed market: ask {quote.ask_price} < bid {quote.bid_price} (spread: {quote.spread})",
                )
            else:
                result.add_error(
                    "ERR_CROSSED_MARKET",
                    f"Crossed market rejected: ask {quote.ask_price} < bid {quote.bid_price}",
                )
