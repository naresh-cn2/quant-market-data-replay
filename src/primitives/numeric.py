"""
Exact numeric primitives for market data prices and quantities.

Guarantees zero binary floating-point contamination by enforcing exact Decimal
arithmetic and strict parsing.
"""

from decimal import Decimal, InvalidOperation
from typing import Any, Union


def parse_decimal(
    value: Any,
    field_name: str = "value",
    allow_float: bool = False
) -> Decimal:
    """
    Parse a numeric value into an exact Decimal.

    Parameters:
    - value: The input value (str, int, Decimal).
    - field_name: Contextual field name for error diagnostics.
    - allow_float: If False (default), passing a float raises ValueError to prevent
      silent precision loss.
    """
    if value is None:
        raise ValueError(f"Field '{field_name}' cannot be None")

    if isinstance(value, Decimal):
        if value.is_nan() or value.is_infinite():
            raise ValueError(f"Field '{field_name}' cannot be NaN or Infinite")
        return value

    if isinstance(value, int):
        return Decimal(value)

    if isinstance(value, float):
        if not allow_float:
            raise ValueError(
                f"Binary float passed for '{field_name}' ({value}). "
                "Floating-point values are prohibited to prevent precision loss. "
                "Pass as string or integer."
            )
        # If float explicitly allowed, convert via repr to avoid binary artifacts
        if value != value or abs(value) == float("inf"):
            raise ValueError(f"Field '{field_name}' cannot be NaN or Infinite: {value}")
        return Decimal(str(value))

    if isinstance(value, str):
        val_str = value.strip()
        # Strip commas and currency symbols if present
        clean_str = val_str.replace(",", "").replace("$", "").replace("€", "").replace("£", "")

        # Reject abnormally long strings or huge scientific notation
        if len(clean_str) > 64:
            raise ValueError(f"Numeric string too long for '{field_name}' ({len(clean_str)} chars): '{value[:30]}...'")

        # Check for scientific notation with unreasonable exponent
        if "e" in clean_str.lower():
            parts = clean_str.lower().split("e")
            if len(parts) == 2 and parts[1].lstrip("+-").isdigit():
                exp = int(parts[1])
                if abs(exp) > 50:
                    raise ValueError(f"Exponent too large for '{field_name}': {exp}")

        try:
            d = Decimal(clean_str)
            if d.is_nan() or d.is_infinite():
                raise ValueError(f"Field '{field_name}' parsed to NaN/Infinite: {value}")
            return d
        except (InvalidOperation, Exception) as e:
            raise ValueError(f"Invalid decimal string for '{field_name}': '{value}'") from e

    raise ValueError(
        f"Unsupported type for '{field_name}': {type(value).__name__} (value: {value})"
    )


def validate_positive(val: Decimal, field_name: str = "value") -> None:
    """Validate that a Decimal value is strictly positive (> 0)."""
    if val <= Decimal(0):
        raise ValueError(f"Field '{field_name}' must be strictly positive (> 0), got: {val}")


def validate_non_negative(val: Decimal, field_name: str = "value") -> None:
    """Validate that a Decimal value is non-negative (>= 0)."""
    if val < Decimal(0):
        raise ValueError(f"Field '{field_name}' must be non-negative (>= 0), got: {val}")


def format_decimal(val: Decimal) -> str:
    """Format Decimal into deterministic standardized string representation."""
    if not isinstance(val, Decimal):
        raise ValueError(f"Expected Decimal, got {type(val).__name__}")
    # Normalize trailing zeros and prevent scientific notation for standard prices
    # Format as standard fixed-point representation
    return f"{val:f}"
