"""Dataset provenance and quality manifest model."""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass(frozen=True, slots=True)
class DatasetManifest:
    """
    Metadata manifest recording provenance, schema versions, record counts,
    timestamp bounds, and cryptographic checksums for an ingested dataset.
    """
    dataset_id: str
    schema_version: str
    created_at_utc: str
    source_file: str
    total_records: int
    trade_count: int
    quote_count: int
    quarantine_count: int
    min_timestamp_ns: int
    max_timestamp_ns: int
    sha256_checksum: str
    config_hash: str
    symbols: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "dataset_id": self.dataset_id,
            "schema_version": self.schema_version,
            "created_at_utc": self.created_at_utc,
            "source_file": self.source_file,
            "total_records": self.total_records,
            "trade_count": self.trade_count,
            "quote_count": self.quote_count,
            "quarantine_count": self.quarantine_count,
            "min_timestamp_ns": self.min_timestamp_ns,
            "max_timestamp_ns": self.max_timestamp_ns,
            "sha256_checksum": self.sha256_checksum,
            "config_hash": self.config_hash,
            "symbols": sorted(list(self.symbols)),
        }
