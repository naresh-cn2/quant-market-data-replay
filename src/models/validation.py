"""Validation models and diagnostic representations."""

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional


class ValidationStatus(str, Enum):
    ACCEPTED = "ACCEPTED"
    SOFT_WARNING = "SOFT_WARNING"
    HARD_INVALID = "HARD_INVALID"


@dataclass(frozen=True, slots=True)
class DiagnosticRecord:
    """Structured diagnostic message for validation issues."""
    code: str
    message: str
    field: Optional[str] = None
    severity: ValidationStatus = ValidationStatus.HARD_INVALID

    def to_dict(self) -> dict:
        return {
            "code": self.code,
            "message": self.message,
            "field": self.field,
            "severity": self.severity.value,
        }


@dataclass(slots=True)
class ValidationResult:
    """Outcome of validating a candidate market data event."""
    status: ValidationStatus = ValidationStatus.ACCEPTED
    diagnostics: List[DiagnosticRecord] = field(default_factory=list)

    @property
    def is_valid(self) -> bool:
        return self.status != ValidationStatus.HARD_INVALID

    @property
    def has_warnings(self) -> bool:
        return self.status == ValidationStatus.SOFT_WARNING

    def add_error(self, code: str, message: str, field_name: Optional[str] = None) -> None:
        self.status = ValidationStatus.HARD_INVALID
        self.diagnostics.append(
            DiagnosticRecord(code=code, message=message, field=field_name, severity=ValidationStatus.HARD_INVALID)
        )

    def add_warning(self, code: str, message: str, field_name: Optional[str] = None) -> None:
        if self.status != ValidationStatus.HARD_INVALID:
            self.status = ValidationStatus.SOFT_WARNING
        self.diagnostics.append(
            DiagnosticRecord(code=code, message=message, field=field_name, severity=ValidationStatus.SOFT_WARNING)
        )
