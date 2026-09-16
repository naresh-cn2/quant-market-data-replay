"""Abstract base for streaming market data ingestion readers."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Dict, Iterator, Optional


@dataclass(frozen=True, slots=True)
class RawRecord:
    """A raw unparsed input record with line number and source provenance."""
    line_number: int
    raw_text: str
    data: Dict[str, Any]
    source_file: Optional[str] = None


class BaseMarketDataReader(ABC):
    """Abstract reader interface for streaming input market data."""

    def __init__(self, file_path: str):
        self.file_path = file_path

    @abstractmethod
    def read_records(self) -> Iterator[RawRecord]:
        """Stream raw records one by one without buffering entire files in memory."""
        pass
