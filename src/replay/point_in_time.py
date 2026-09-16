"""
Point-in-Time access control and historical state safety guard.

Ensures no future events beyond the current query boundary or replay clock
are ever visible to research consumers.
"""

from typing import Optional, Union

from src.models.trade import TradeEvent
from src.models.quote import QuoteEvent


class PointInTimeGuard:
    """
    Guards stream consumption against lookahead bias and future-event leakage.
    """

    def __init__(self, start_ns: int, end_ns: int):
        if start_ns > end_ns:
            raise ValueError(f"start_ns ({start_ns}) cannot be greater than end_ns ({end_ns})")
        self.start_ns = start_ns
        self.end_ns = end_ns
        self._current_time_ns: int = start_ns
        self._last_emitted_ts: int = 0

    @property
    def current_time_ns(self) -> int:
        return self._current_time_ns

    def is_visible(self, event: Union[TradeEvent, QuoteEvent]) -> bool:
        """
        Verify if an event is strictly visible within the current [start_ns, end_ns] window.
        """
        ts = event.timestamp_ns
        if ts < self.start_ns or ts > self.end_ns:
            return False

        # Verify monotonicity (timestamp must not decrease in a replay stream)
        if ts < self._last_emitted_ts:
            raise ValueError(
                f"Stream monotonicity violation: event timestamp {ts} < previous {self._last_emitted_ts}"
            )

        self._last_emitted_ts = ts
        self._current_time_ns = ts
        return True
