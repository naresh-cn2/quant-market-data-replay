"""Quarantine record model."""

from dataclasses import dataclass
from typing import Any, Dict, Optional


@dataclass(frozen=True, slots=True)
class QuarantineRecord:
    """
    Quarantine record capturing corrupt, unparseable, or invalid inputs.

    Guarantees raw unmutated payload preservation and structured diagnosis.
    """
    quarantine_id: str
    timestamp_ns: int
    source: str
    raw_record: str
    error_code: str
    error_message: str
    severity: str = "HARD_INVALID"
    field_name: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "quarantine_id": self.quarantine_id,
            "timestamp_ns": self.timestamp_ns,
            "source": self.source,
            "raw_record": self.raw_record,
            "error_code": self.error_code,
            "error_message": self.error_message,
            "severity": self.severity,
            "field_name": self.field_name,
        }
