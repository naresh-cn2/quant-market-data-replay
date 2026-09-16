"""
Bounded out-of-order reordering buffer.

Maintains a sliding watermark window to reorder out-of-order events deterministically
in bounded O(W) memory, without performing global in-memory sorting of an unbounded stream.
"""

import heapq
from typing import Iterator, List, Optional, Tuple, Union

from src.models.trade import TradeEvent
from src.models.quote import QuoteEvent
from src.models.quarantine import QuarantineRecord


class BoundedReorderBuffer:
    """
    Priority buffer for bounded event reordering.

    Parameters:
    - max_lateness_ns: Maximum allowed out-of-order latency in nanoseconds (e.g. 5 seconds = 5_000_000_000 ns).
    """

    def __init__(self, max_lateness_ns: int = 5_000_000_000):
        if max_lateness_ns < 0:
            raise ValueError(f"max_lateness_ns cannot be negative: {max_lateness_ns}")
        self.max_lateness_ns = max_lateness_ns
        self._heap: List[Tuple[int, int, int, str, Union[TradeEvent, QuoteEvent]]] = []
        self._max_seen_timestamp_ns: int = 0
        self._watermark_ns: int = 0
        self._item_counter: int = 0  # Monotonic insertion counter for tie-breaking stability

    @property
    def watermark_ns(self) -> int:
        return self._watermark_ns

    @property
    def max_seen_timestamp_ns(self) -> int:
        return self._max_seen_timestamp_ns

    @property
    def buffered_count(self) -> int:
        return len(self._heap)

    def process_event(
        self, event: Union[TradeEvent, QuoteEvent]
    ) -> Tuple[List[Union[TradeEvent, QuoteEvent]], Optional[QuarantineRecord]]:
        """
        Process an incoming event through the bounded buffer.

        Returns:
        - Tuple of (ready_events_to_emit, late_quarantine_record_if_any)
        """
        self._item_counter += 1
        ts = event.timestamp_ns

        # Update max seen timestamp and calculate sliding watermark
        if ts > self._max_seen_timestamp_ns:
            self._max_seen_timestamp_ns = ts
            self._watermark_ns = max(0, self._max_seen_timestamp_ns - self.max_lateness_ns)

        # Check if event arrived past the bounded lateness watermark
        if self._watermark_ns > 0 and ts < self._watermark_ns:
            late_record = QuarantineRecord(
                quarantine_id=f"QUAR-LATE-{event.event_id[:8]}",
                timestamp_ns=ts,
                source=event.source,
                raw_record=str(event.to_dict()),
                error_code="ERR_EXCESSIVE_LATENESS",
                error_message=(
                    f"Event arrived at timestamp {ts} ns which is older than "
                    f"the current watermark {self._watermark_ns} ns "
                    f"(lateness: {self._watermark_ns - ts} ns > max {self.max_lateness_ns} ns)"
                ),
                severity="HARD_INVALID",
                field_name="timestamp_ns",
            )
            return [], late_record

        # Priority order: TRADE (1) before QUOTE (2) on equal timestamp
        type_priority = 1 if isinstance(event, TradeEvent) else 2
        seq_id = event.sequence_id if event.sequence_id is not None else self._item_counter

        heap_entry = (ts, type_priority, seq_id, event.event_id, event)
        heapq.heappush(self._heap, heap_entry)

        # Emit events whose timestamp is below the watermark
        ready: List[Union[TradeEvent, QuoteEvent]] = []
        while self._heap and self._heap[0][0] <= self._watermark_ns:
            _, _, _, _, ready_event = heapq.heappop(self._heap)
            ready.append(ready_event)

        return ready, None

    def flush(self) -> Iterator[Union[TradeEvent, QuoteEvent]]:
        """
        Drain all remaining buffered events in strict deterministic order.
        Called when the input stream reaches EOF.
        """
        while self._heap:
            _, _, _, _, ready_event = heapq.heappop(self._heap)
            yield ready_event
