"""Validation engine orchestrator."""

from typing import Optional, Union

from src.models.trade import TradeEvent
from src.models.quote import QuoteEvent
from src.models.validation import ValidationResult
from src.validation.diagnostics import ValidationMetrics
from src.validation.rules import MarketDataValidationRules


class MarketDataValidator:
    """
    Market data validator coordinating rule checking and diagnostics collection.
    """

    def __init__(self, rules: Optional[MarketDataValidationRules] = None):
        self.rules = rules or MarketDataValidationRules()
        self.metrics = ValidationMetrics()

    def validate_event(self, event: Union[TradeEvent, QuoteEvent]) -> ValidationResult:
        result = self.rules.validate(event)
        self.metrics.record(result.status, result.diagnostics)
        return result
