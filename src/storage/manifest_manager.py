"""Dataset provenance and manifest manager."""

from datetime import datetime, timezone
import hashlib
import json
import os
from typing import Any, Dict, List, Optional, Set

from src.models.manifest import DatasetManifest


class ManifestManager:
    """
    Builds, hashes, stores, and validates dataset provenance manifests.
    """

    @staticmethod
    def compute_file_sha256(file_path: str) -> str:
        """Compute SHA-256 hash of a file on disk."""
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")
        hasher = hashlib.sha256()
        with open(file_path, "rb") as f:
            while chunk := f.read(65536):
                hasher.update(chunk)
        return hasher.hexdigest()

    @staticmethod
    def compute_config_hash(config_dict: Dict[str, Any]) -> str:
        """Compute deterministic SHA-256 hash of engine configuration."""
        canonical_json = json.dumps(config_dict, sort_keys=True)
        return hashlib.sha256(canonical_json.encode("utf-8")).hexdigest()

    @classmethod
    def create_manifest(
        cls,
        source_file: str,
        total_records: int,
        trade_count: int,
        quote_count: int,
        quarantine_count: int,
        min_timestamp_ns: int,
        max_timestamp_ns: int,
        symbols: Set[str],
        config_dict: Optional[Dict[str, Any]] = None,
        schema_version: str = "1.0.0",
    ) -> DatasetManifest:
        """Construct a new DatasetManifest."""
        file_hash = cls.compute_file_sha256(source_file) if os.path.exists(source_file) else "IN_MEMORY"
        config_hash = cls.compute_config_hash(config_dict or {})
        dataset_id = f"DS-{file_hash[:12]}-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"

        return DatasetManifest(
            dataset_id=dataset_id,
            schema_version=schema_version,
            created_at_utc=datetime.now(timezone.utc).isoformat(),
            source_file=source_file,
            total_records=total_records,
            trade_count=trade_count,
            quote_count=quote_count,
            quarantine_count=quarantine_count,
            min_timestamp_ns=min_timestamp_ns,
            max_timestamp_ns=max_timestamp_ns,
            sha256_checksum=file_hash,
            config_hash=config_hash,
            symbols=sorted(list(symbols)),
        )

    @classmethod
    def verify_manifest(cls, manifest: DatasetManifest, source_file: Optional[str] = None) -> bool:
        """Verify checksum integrity of source file against manifest."""
        target_file = source_file or manifest.source_file
        if not os.path.exists(target_file):
            return False
        current_hash = cls.compute_file_sha256(target_file)
        return current_hash == manifest.sha256_checksum
