"""
Deterministic historical market data replay engine.

Provides generator/iterator based point-in-time safe streaming of market events.
"""

from typing import Iterator, Optional, Tuple, Union

from src.models.trade import TradeEvent
from src.models.quote import QuoteEvent
from src.replay.point_in_time import PointInTimeGuard
from src.storage.backend import BaseStorageBackend


class ReplayEngine:
    """
    Historical market data replay engine.
    """

    def __init__(self, storage: BaseStorageBackend):
        self.storage = storage

    def replay_stream(
        self,
        symbol: str,
        start_ns: int,
        end_ns: int,
        event_types: Tuple[str, ...] = ("TRADE", "QUOTE"),
    ) -> Iterator[Union[TradeEvent, QuoteEvent]]:
        """
        Replay market data stream deterministically for a symbol and time window.

        Yields:
        - TradeEvent or QuoteEvent in strictly deterministic, point-in-time safe order.
        """
        guard = PointInTimeGuard(start_ns, end_ns)
        stream = self.storage.query_stream(symbol, start_ns, end_ns, event_types)

        for event in stream:
            if guard.is_visible(event):
                yield event
