"""Unit tests for quarantine manager and persistence."""

import os
import tempfile
import unittest

from src.ingestion.reader import RawRecord
from src.models.quarantine import QuarantineRecord
from src.quarantine.manager import QuarantineManager


class TestQuarantineManager(unittest.TestCase):
    def test_quarantine_in_memory(self):
        mgr = QuarantineManager()
        raw = RawRecord(line_number=1, raw_text="bad,data", data={}, source_file="test.csv")
        rec = mgr.quarantine_raw(raw, "ERR_BAD", "Bad data format")

        self.assertEqual(mgr.count, 1)
        self.assertEqual(rec.raw_record, "bad,data")
        self.assertEqual(rec.error_code, "ERR_BAD")

    def test_quarantine_file_persistence(self):
        with tempfile.NamedTemporaryFile(delete=False, suffix=".jsonl") as tf:
            temp_path = tf.name

        try:
            mgr = QuarantineManager(output_path=temp_path)
            raw = RawRecord(line_number=10, raw_text="corrupt,row,10", data={}, source_file="feed.csv")
            mgr.quarantine_raw(raw, "ERR_CORRUPT", "Corrupted row")

            # Create new manager pointing to same file to verify reload
            mgr2 = QuarantineManager(output_path=temp_path)
            self.assertEqual(mgr2.count, 1)
            recs = mgr2.get_records()
            self.assertEqual(recs[0].raw_record, "corrupt,row,10")
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)


if __name__ == "__main__":
    unittest.main()
