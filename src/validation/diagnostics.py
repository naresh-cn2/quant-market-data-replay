"""Structured diagnostic logging and metrics collector for validation."""

from dataclasses import dataclass, field
from typing import Dict, List

from src.models.validation import DiagnosticRecord, ValidationStatus


@dataclass
class ValidationMetrics:
    """Summary metrics of a validation run."""
    total_validated: int = 0
    total_accepted: int = 0
    total_soft_warnings: int = 0
    total_hard_invalids: int = 0
    error_counts_by_code: Dict[str, int] = field(default_factory=dict)
    warning_counts_by_code: Dict[str, int] = field(default_factory=dict)

    def record(self, status: ValidationStatus, diagnostics: List[DiagnosticRecord]) -> None:
        self.total_validated += 1
        if status == ValidationStatus.ACCEPTED:
            self.total_accepted += 1
        elif status == ValidationStatus.SOFT_WARNING:
            self.total_accepted += 1
            self.total_soft_warnings += 1
            for d in diagnostics:
                self.warning_counts_by_code[d.code] = self.warning_counts_by_code.get(d.code, 0) + 1
        elif status == ValidationStatus.HARD_INVALID:
            self.total_hard_invalids += 1
            for d in diagnostics:
                self.error_counts_by_code[d.code] = self.error_counts_by_code.get(d.code, 0) + 1

    def to_dict(self) -> dict:
        return {
            "total_validated": self.total_validated,
            "total_accepted": self.total_accepted,
            "total_soft_warnings": self.total_soft_warnings,
            "total_hard_invalids": self.total_hard_invalids,
            "error_counts": self.error_counts_by_code,
            "warning_counts": self.warning_counts_by_code,
        }
