"""Unit tests for raw data ingestion readers."""

from decimal import Decimal
import os
import unittest

from src.ingestion import create_reader, CsvMarketDataReader, JsonMarketDataReader


class TestIngestionReaders(unittest.TestCase):
    def setUp(self):
        self.fixtures_dir = os.path.join(os.path.dirname(__file__), "..", "fixtures")

    def test_csv_reader_streaming(self):
        csv_file = os.path.join(self.fixtures_dir, "sample_trades.csv")
        reader = CsvMarketDataReader(csv_file)
        records = list(reader.read_records())

        self.assertEqual(len(records), 5)
        self.assertEqual(records[0].line_number, 2)
        self.assertEqual(records[0].data["symbol"], "AAPL")
        self.assertEqual(records[0].data["price"], "150.25")
        self.assertIn("150.25", records[0].raw_text)

    def test_json_lines_reader_streaming(self):
        jsonl_file = os.path.join(self.fixtures_dir, "sample_trades.jsonl")
        reader = JsonMarketDataReader(jsonl_file)
        records = list(reader.read_records())

        self.assertEqual(len(records), 3)
        self.assertEqual(records[0].data["symbol"], "AAPL")
        self.assertEqual(records[0].data["price"], "150.25")

    def test_malformed_csv_parsing(self):
        malformed_csv = os.path.join(self.fixtures_dir, "malformed_data.csv")
        reader = CsvMarketDataReader(malformed_csv)
        records = list(reader.read_records())

        # Should read all rows without throwing unhandled exceptions
        self.assertTrue(len(records) >= 6)
        # Verify the corrupt column count row contains parse error key
        corrupt_recs = [r for r in records if "_parse_error" in r.data]
        self.assertTrue(len(corrupt_recs) >= 1)

    def test_json_array_reader_streaming(self):
        import tempfile
        content = '[{"symbol": "AAPL", "price": "150.25", "timestamp": "2026-09-16T10:00:00Z"}, {"symbol": "AAPL", "price": "150.30", "timestamp": "2026-09-16T10:00:01Z"}]'
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".json", encoding="utf-8") as tf:
            tf.write(content)
            temp_path = tf.name
        try:
            reader = JsonMarketDataReader(temp_path)
            records = list(reader.read_records())
            self.assertEqual(len(records), 2)
            self.assertEqual(records[0].data["symbol"], "AAPL")
            self.assertEqual(records[0].data["price"], "150.25")
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)

    def test_create_reader_factory(self):
        csv_file = os.path.join(self.fixtures_dir, "sample_trades.csv")
        jsonl_file = os.path.join(self.fixtures_dir, "sample_trades.jsonl")

        r1 = create_reader(csv_file)
        self.assertIsInstance(r1, CsvMarketDataReader)

        r2 = create_reader(jsonl_file)
        self.assertIsInstance(r2, JsonMarketDataReader)


if __name__ == "__main__":
    unittest.main()
