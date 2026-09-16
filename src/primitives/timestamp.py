"""
Timestamp primitives for quantitative market data.

All canonical timestamps are represented as 64-bit integer nanoseconds in UTC
since the Unix epoch (1970-01-01T00:00:00.000000000Z).
"""

from datetime import datetime, timezone
import re
from typing import Union

# Pre-compiled ISO-8601 regex supporting optional fractional seconds up to 9 digits
ISO_PATTERN = re.compile(
    r"^(\d{4})-(\d{2})-(\d{2})[T ](\d{2}):(\d{2}):(\d{2})(?:\.(\d+))?(?:Z|([+-]\d{2}:?\d{2}))?$"
)

# Epoch timestamp boundaries for unit heuristics
NS_THRESHOLD = 10**17    # e.g., > 1973 in ns
US_THRESHOLD = 10**14    # e.g., > 1973 in us
MS_THRESHOLD = 10**11    # e.g., > 1973 in ms

MIN_TIMESTAMP_NS = 0                      # 1970-01-01
MAX_TIMESTAMP_NS = 4102444800 * 10**9     # 2100-01-01


def parse_timestamp_ns(value: Union[str, int, float]) -> int:
    """
    Parse a raw timestamp value into integer nanoseconds UTC.

    Supports:
    - ISO-8601 UTC string (e.g., '2026-09-16T12:00:00.123456789Z')
    - Integer / string nanoseconds, microseconds, milliseconds, seconds
    - Rejects invalid formats, NaN, negative values, and out-of-range dates
    """
    if value is None:
        raise ValueError("Timestamp cannot be None")

    if isinstance(value, float):
        # Disallow float nan / inf
        if value != value or abs(value) == float("inf"):
            raise ValueError(f"Invalid float timestamp: {value}")
        # Convert float seconds (e.g. 1726488000.123456)
        if value < 0:
            raise ValueError(f"Negative timestamp not allowed: {value}")
        sec_part = int(value)
        frac_part = int(round((value - sec_part) * 1_000_000_000))
        ts_ns = sec_part * 1_000_000_000 + frac_part
        if not (MIN_TIMESTAMP_NS <= ts_ns <= MAX_TIMESTAMP_NS):
            raise ValueError(f"Timestamp nanoseconds out of range: {ts_ns}")
        return ts_ns

    if isinstance(value, int):
        return _normalize_epoch_integer(value)

    if isinstance(value, str):
        val_str = value.strip()
        if not val_str:
            raise ValueError("Empty timestamp string")

        # Try parsing integer string first
        if val_str.isdigit() or (val_str.startswith("-") and val_str[1:].isdigit()):
            int_val = int(val_str)
            return _normalize_epoch_integer(int_val)

        # Try ISO-8601 parsing
        return _parse_iso_string(val_str)

    raise ValueError(f"Unsupported timestamp type: {type(value).__name__}")


def _normalize_epoch_integer(val: int) -> int:
    """Normalize integer epoch value to nanoseconds based on magnitude."""
    if val < 0:
        raise ValueError(f"Negative epoch timestamp not allowed: {val}")

    if val >= NS_THRESHOLD:
        ts_ns = val
    elif val >= US_THRESHOLD:
        ts_ns = val * 1_000
    elif val >= MS_THRESHOLD:
        ts_ns = val * 1_000_000
    else:
        # Seconds
        ts_ns = val * 1_000_000_000

    if not (MIN_TIMESTAMP_NS <= ts_ns <= MAX_TIMESTAMP_NS):
        raise ValueError(f"Timestamp nanoseconds out of range: {ts_ns}")
    return ts_ns


def _parse_iso_string(val_str: str) -> int:
    """Parse ISO-8601 string to integer nanoseconds UTC with sub-microsecond preservation."""
    match = ISO_PATTERN.match(val_str)
    if not match:
        # Fallback to standard datetime parser if matching standard ISO formats
        try:
            # Replace Z with +00:00 for fromisoformat
            clean_str = val_str.replace("Z", "+00:00")
            dt = datetime.fromisoformat(clean_str)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            else:
                dt = dt.astimezone(timezone.utc)
            sec = int(dt.timestamp())
            microsec = dt.microsecond
            ts_ns = sec * 1_000_000_000 + microsec * 1_000
            if not (MIN_TIMESTAMP_NS <= ts_ns <= MAX_TIMESTAMP_NS):
                raise ValueError(f"Timestamp out of range: {ts_ns}")
            return ts_ns
        except Exception as e:
            raise ValueError(f"Unparseable ISO timestamp: {val_str}") from e

    year, month, day, hour, minute, second, frac, tz = match.groups()
    base_dt = datetime(
        int(year), int(month), int(day),
        int(hour), int(minute), int(second),
        tzinfo=timezone.utc
    )

    # Offset if present
    offset_ns = 0
    if tz:
        tz_clean = tz.replace(":", "")
        tz_sign = -1 if tz_clean[0] == "-" else 1
        tz_hours = int(tz_clean[1:3])
        tz_mins = int(tz_clean[3:5])
        offset_ns = tz_sign * (tz_hours * 3600 + tz_mins * 60) * 1_000_000_000

    base_ns = int(base_dt.timestamp()) * 1_000_000_000 - offset_ns

    # Nanosecond fractional part (up to 9 digits)
    nanos = 0
    if frac:
        frac_padded = (frac + "000000000")[:9]
        nanos = int(frac_padded)

    ts_ns = base_ns + nanos
    if not (MIN_TIMESTAMP_NS <= ts_ns <= MAX_TIMESTAMP_NS):
        raise ValueError(f"Timestamp nanoseconds out of range: {ts_ns}")
    return ts_ns


def format_timestamp_ns(timestamp_ns: int) -> str:
    """Format nanoseconds UTC integer into ISO-8601 string with 9 decimal places."""
    if timestamp_ns < 0:
        raise ValueError(f"Invalid timestamp_ns: {timestamp_ns}")

    secs = timestamp_ns // 1_000_000_000
    nanos = timestamp_ns % 1_000_000_000
    dt = datetime.fromtimestamp(secs, tz=timezone.utc)
    return f"{dt.strftime('%Y-%m-%d %H:%M:%S')}.{nanos:09d}Z"
