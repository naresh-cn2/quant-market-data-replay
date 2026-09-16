"""Integration tests for provenance and dataset manifest validation."""

import json
import os
import tempfile
import unittest

from src.pipeline import MarketDataPipeline
from src.storage.manifest_manager import ManifestManager
from src.storage.sqlite_store import SqliteStorageBackend


class TestProvenanceManifest(unittest.TestCase):
    def setUp(self):
        self.fixtures_dir = os.path.join(os.path.dirname(__file__), "..", "fixtures")
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix=".db").name
        self.storage = SqliteStorageBackend(self.temp_db)
        self.pipeline = MarketDataPipeline(storage=self.storage)

    def tearDown(self):
        self.storage.close()
        if os.path.exists(self.temp_db):
            os.remove(self.temp_db)

    def test_manifest_creation_and_checksum_verification(self):
        csv_file = os.path.join(self.fixtures_dir, "sample_trades.csv")
        manifest = self.pipeline.process_file(csv_file)

        # Verify manifest stored in db
        retrieved = self.storage.get_manifest(manifest.dataset_id)
        self.assertIsNotNone(retrieved)
        self.assertEqual(retrieved.sha256_checksum, manifest.sha256_checksum)

        # Verify checksum matches source file
        self.assertTrue(ManifestManager.verify_manifest(retrieved, csv_file))


if __name__ == "__main__":
    unittest.main()
