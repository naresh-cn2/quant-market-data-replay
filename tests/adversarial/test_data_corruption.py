"""Adversarial tests for data corruption and boundary injection."""

import os
import tempfile
import unittest

from src.ingestion.csv_reader import CsvMarketDataReader
from src.normalization.normalizer import EventNormalizer
from src.models.quarantine import QuarantineRecord


class TestDataCorruption(unittest.TestCase):
    def test_corrupted_characters_and_injections(self):
        corrupted_lines = [
            "timestamp,symbol,price,size,side,source\n",
            "2026-09-16T10:00:00Z,AAPL,150.25,100,BUY,NASDAQ\n",
            "2026-09-16T10:00:00Z,AAPL; DROP TABLE trades;--,150.25,100,BUY,NASDAQ\n",
            "2026-09-16T10:00:00Z,AAPL,NaN,100,BUY,NASDAQ\n",
            "2026-09-16T10:00:00Z,AAPL,Infinity,100,BUY,NASDAQ\n",
            "2026-09-16T10:00:00Z,AAPL,1e9999999999,100,BUY,NASDAQ\n",
            "2026-09-16T10:00:00Z,AAPL,150.25,-9999999999,BUY,NASDAQ\n",
        ]

        with tempfile.NamedTemporaryFile(delete=False, mode="w", suffix=".csv", encoding="utf-8") as tf:
            tf.writelines(corrupted_lines)
            temp_path = tf.name

        try:
            reader = CsvMarketDataReader(temp_path)
            normalizer = EventNormalizer()

            quarantine_records = []
            valid_records = []

            for raw in reader.read_records():
                res = normalizer.normalize(raw)
                if isinstance(res, QuarantineRecord):
                    quarantine_records.append(res)
                else:
                    valid_records.append(res)

            # Valid should only be the first valid record
            # NaN, Infinity, huge overflow, negative size should be quarantined or caught in validation
            self.assertTrue(len(quarantine_records) >= 3)
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)


if __name__ == "__main__":
    unittest.main()
