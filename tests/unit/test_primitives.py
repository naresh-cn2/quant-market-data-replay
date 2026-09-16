"""Unit tests for timestamp and numeric primitives."""

from decimal import Decimal
import unittest

from src.primitives.numeric import (
    parse_decimal,
    validate_positive,
    validate_non_negative,
    format_decimal,
)
from src.primitives.timestamp import (
    parse_timestamp_ns,
    format_timestamp_ns,
)


class TestTimestampPrimitives(unittest.TestCase):
    def test_parse_iso_string_with_nanos(self):
        ts_str = "2026-09-16T10:00:00.123456789Z"
        expected_ns = 1789552800123456789
        ts_ns = parse_timestamp_ns(ts_str)
        self.assertEqual(ts_ns, expected_ns)

    def test_parse_iso_string_standard(self):
        ts_str = "2026-09-16T10:00:00Z"
        expected_ns = 1789552800000000000
        ts_ns = parse_timestamp_ns(ts_str)
        self.assertEqual(ts_ns, expected_ns)

    def test_parse_integer_nanos(self):
        ts_ns_val = 1789552800123456789
        self.assertEqual(parse_timestamp_ns(ts_ns_val), ts_ns_val)
        self.assertEqual(parse_timestamp_ns(str(ts_ns_val)), ts_ns_val)

    def test_parse_integer_millis(self):
        ts_ms = 1789552800123
        expected_ns = ts_ms * 1_000_000
        self.assertEqual(parse_timestamp_ns(ts_ms), expected_ns)

    def test_parse_integer_seconds(self):
        ts_sec = 1789552800
        expected_ns = ts_sec * 1_000_000_000
        self.assertEqual(parse_timestamp_ns(ts_sec), expected_ns)

    def test_parse_float_rejected_or_converted(self):
        ts_float = 1789552800.5
        expected_ns = 1789552800500000000
        self.assertEqual(parse_timestamp_ns(ts_float), expected_ns)

    def test_invalid_timestamps_raise_error(self):
        with self.assertRaises(ValueError):
            parse_timestamp_ns("")
        with self.assertRaises(ValueError):
            parse_timestamp_ns("INVALID_DATE_STRING")
        with self.assertRaises(ValueError):
            parse_timestamp_ns(-100)
        with self.assertRaises(ValueError):
            parse_timestamp_ns(float("nan"))

    def test_format_timestamp_ns(self):
        ts_ns = 1789552800123456789
        formatted = format_timestamp_ns(ts_ns)
        self.assertIn("2026-09-16 10:00:00.123456789Z", formatted)


class TestNumericPrimitives(unittest.TestCase):
    def test_parse_decimal_from_string(self):
        d = parse_decimal("150.25", "price")
        self.assertIsInstance(d, Decimal)
        self.assertEqual(d, Decimal("150.25"))

    def test_parse_decimal_with_symbols(self):
        d = parse_decimal("$1,250.75", "price")
        self.assertEqual(d, Decimal("1250.75"))

    def test_parse_decimal_rejects_binary_float_by_default(self):
        with self.assertRaises(ValueError) as ctx:
            parse_decimal(150.25, "price")
        self.assertIn("Binary float passed", str(ctx.exception))

    def test_parse_decimal_with_integer(self):
        d = parse_decimal(100, "size")
        self.assertEqual(d, Decimal("100"))

    def test_parse_decimal_invalid_strings(self):
        with self.assertRaises(ValueError):
            parse_decimal("abc", "price")
        with self.assertRaises(ValueError):
            parse_decimal("", "price")
        with self.assertRaises(ValueError):
            parse_decimal(None, "price")

    def test_validate_positive(self):
        validate_positive(Decimal("0.01"), "price")
        with self.assertRaises(ValueError):
            validate_positive(Decimal("0.00"), "price")
        with self.assertRaises(ValueError):
            validate_positive(Decimal("-5.00"), "price")

    def test_validate_non_negative(self):
        validate_non_negative(Decimal("0.00"), "price")
        validate_non_negative(Decimal("10.50"), "price")
        with self.assertRaises(ValueError):
            validate_non_negative(Decimal("-0.01"), "price")

    def test_format_decimal(self):
        d = Decimal("150.2500")
        self.assertEqual(format_decimal(d), "150.2500")

    def test_parse_decimal_high_precision_preservation(self):
        # 18 decimal places (e.g. crypto wei / micro-cents)
        precise_str = "0.000000000000000001"
        d = parse_decimal(precise_str, "size")
        self.assertEqual(d, Decimal(precise_str))
        self.assertEqual(format_decimal(d), precise_str)

    def test_timestamp_boundary_limits(self):
        # Min epoch
        self.assertEqual(parse_timestamp_ns(0), 0)
        # Out of range negative
        with self.assertRaises(ValueError):
            parse_timestamp_ns(-1)
        # Out of range future (> year 2100)
        with self.assertRaises(ValueError):
            parse_timestamp_ns(5000000000 * 10**9)


if __name__ == "__main__":
    unittest.main()
