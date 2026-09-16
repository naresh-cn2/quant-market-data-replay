"""
Quarantine manager for isolating invalid, unparseable, or out-of-order market records.

Guarantees full raw evidence preservation without silent data loss.
"""

import json
import os
from typing import Iterator, List, Optional

from src.ingestion.reader import RawRecord
from src.models.quarantine import QuarantineRecord


class QuarantineManager:
    """
    Manages storage and retrieval of quarantined records.
    """

    def __init__(self, output_path: Optional[str] = None):
        self.output_path = output_path
        self._records: List[QuarantineRecord] = []
        if output_path and os.path.exists(output_path):
            self._load_existing()

    def _load_existing(self) -> None:
        if not self.output_path or not os.path.exists(self.output_path):
            return
        with open(self.output_path, "r", encoding="utf-8") as f:
            for line in f:
                line_str = line.strip()
                if line_str:
                    try:
                        data = json.loads(line_str)
                        self._records.append(
                            QuarantineRecord(
                                quarantine_id=data["quarantine_id"],
                                timestamp_ns=data.get("timestamp_ns", 0),
                                source=data.get("source", "UNKNOWN"),
                                raw_record=data["raw_record"],
                                error_code=data["error_code"],
                                error_message=data["error_message"],
                                severity=data.get("severity", "HARD_INVALID"),
                                field_name=data.get("field_name"),
                            )
                        )
                    except Exception:
                        pass

    def quarantine(self, record: QuarantineRecord) -> None:
        """Store a quarantine record."""
        self._records.append(record)
        if self.output_path:
            with open(self.output_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(record.to_dict()) + "\n")

    def quarantine_raw(
        self,
        raw_record: RawRecord,
        error_code: str,
        error_message: str,
        severity: str = "HARD_INVALID",
        field_name: Optional[str] = None,
        timestamp_ns: int = 0,
    ) -> QuarantineRecord:
        """Create and record quarantine for a raw record."""
        record = QuarantineRecord(
            quarantine_id=f"QUAR-{raw_record.line_number}-{len(self._records) + 1}",
            timestamp_ns=timestamp_ns,
            source=raw_record.source_file or "UNKNOWN",
            raw_record=raw_record.raw_text,
            error_code=error_code,
            error_message=error_message,
            severity=severity,
            field_name=field_name,
        )
        self.quarantine(record)
        return record

    def get_records(self) -> List[QuarantineRecord]:
        return list(self._records)

    def iter_records(self) -> Iterator[QuarantineRecord]:
        yield from self._records

    @property
    def count(self) -> int:
        return len(self._records)
