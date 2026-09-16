"""Abstract storage backend interface."""

from abc import ABC, abstractmethod
from typing import Iterator, List, Optional, Tuple, Union

from src.models.trade import TradeEvent
from src.models.quote import QuoteEvent
from src.models.quarantine import QuarantineRecord
from src.models.manifest import DatasetManifest


class BaseStorageBackend(ABC):
    """Storage interface for canonical market data events, quarantine, and manifests."""

    @abstractmethod
    def store_trade(self, trade: TradeEvent) -> None:
        pass

    @abstractmethod
    def store_trades_batch(self, trades: List[TradeEvent]) -> None:
        pass

    @abstractmethod
    def store_quote(self, quote: QuoteEvent) -> None:
        pass

    @abstractmethod
    def store_quotes_batch(self, quotes: List[QuoteEvent]) -> None:
        pass

    @abstractmethod
    def store_quarantine(self, record: QuarantineRecord) -> None:
        pass

    @abstractmethod
    def store_manifest(self, manifest: DatasetManifest) -> None:
        pass

    @abstractmethod
    def get_manifest(self, dataset_id: str) -> Optional[DatasetManifest]:
        pass

    @abstractmethod
    def query_stream(
        self,
        symbol: str,
        start_ns: int,
        end_ns: int,
        event_types: Tuple[str, ...] = ("TRADE", "QUOTE"),
    ) -> Iterator[Union[TradeEvent, QuoteEvent]]:
        pass
