"""
End-to-End Market Data Processing Pipeline.

Coordinates Ingestion -> Normalization -> Validation -> Quarantine / Storage -> Manifest generation.
"""

from decimal import Decimal
import json
import os
from typing import Any, Dict, List, Optional, Set

from src.ingestion import create_reader
from src.models.trade import TradeEvent
from src.models.quote import QuoteEvent
from src.models.quarantine import QuarantineRecord
from src.models.manifest import DatasetManifest
from src.normalization.normalizer import EventNormalizer
from src.primitives.timestamp import parse_timestamp_ns
from src.quarantine.manager import QuarantineManager
from src.reorder.bounded_buffer import BoundedReorderBuffer
from src.storage.backend import BaseStorageBackend
from src.storage.manifest_manager import ManifestManager
from src.storage.sqlite_store import SqliteStorageBackend
from src.validation.engine import MarketDataValidator
from src.validation.rules import MarketDataValidationRules


class MarketDataPipeline:
    """
    Orchestrates streaming market data ingestion, validation, quarantine, and storage.
    """

    def __init__(
        self,
        storage: Optional[BaseStorageBackend] = None,
        config: Optional[Dict[str, Any]] = None,
        quarantine_file: Optional[str] = None,
    ):
        self.config = config or {}
        engine_cfg = self.config.get("engine", {})
        val_cfg = self.config.get("validation", {})

        self.storage = storage or SqliteStorageBackend(
            self.config.get("storage", {}).get("default_db_path", ":memory:")
        )
        self.normalizer = EventNormalizer()

        allow_crossed = val_cfg.get("allow_crossed_quotes", True)
        price_jump_threshold = Decimal(str(engine_cfg.get("price_jump_threshold_ratio", "0.20")))
        rules = MarketDataValidationRules(
            allow_crossed_quotes=allow_crossed,
            price_jump_threshold_ratio=price_jump_threshold,
        )
        self.validator = MarketDataValidator(rules)
        self.quarantine_mgr = QuarantineManager(output_path=quarantine_file)

        max_lateness_ns = int(engine_cfg.get("max_lateness_ns", 5_000_000_000))
        self.reorder_buffer = BoundedReorderBuffer(max_lateness_ns=max_lateness_ns)
        self.batch_size = int(engine_cfg.get("batch_commit_size", 10000))

    def process_file(self, file_path: str, format_hint: Optional[str] = None) -> DatasetManifest:
        """
        Process a market data file from raw records to storage and manifest.
        """
        reader = create_reader(file_path, format_hint=format_hint)

        total_records = 0
        trade_count = 0
        quote_count = 0
        quarantine_count = 0
        min_ts_ns = 2**63 - 1
        max_ts_ns = 0
        symbols_seen: Set[str] = set()

        trade_batch: List[TradeEvent] = []
        quote_batch: List[QuoteEvent] = []

        def flush_batches():
            if trade_batch:
                self.storage.store_trades_batch(trade_batch)
                trade_batch.clear()
            if quote_batch:
                self.storage.store_quotes_batch(quote_batch)
                quote_batch.clear()

        for raw_record in reader.read_records():
            total_records += 1
            result = self.normalizer.normalize(raw_record)

            if isinstance(result, QuarantineRecord):
                quarantine_count += 1
                self.quarantine_mgr.quarantine(result)
                self.storage.store_quarantine(result)
                continue

            # Candidate Canonical Event (Trade or Quote)
            val_res = self.validator.validate_event(result)
            if not val_res.is_valid:
                quarantine_count += 1
                primary_diag = val_res.diagnostics[0] if val_res.diagnostics else None
                err_code = primary_diag.code if primary_diag else "ERR_VALIDATION_FAILED"
                err_msg = primary_diag.message if primary_diag else "Validation failed"
                field_name = primary_diag.field if primary_diag else None

                quar_rec = self.quarantine_mgr.quarantine_raw(
                    raw_record=raw_record,
                    error_code=err_code,
                    error_message=err_msg,
                    severity="HARD_INVALID",
                    field_name=field_name,
                    timestamp_ns=result.timestamp_ns,
                )
                self.storage.store_quarantine(quar_rec)
                continue

            # Event is accepted (either clean or with soft warnings)
            ready_events, late_quar = self.reorder_buffer.process_event(result)

            if late_quar is not None:
                quarantine_count += 1
                self.quarantine_mgr.quarantine(late_quar)
                self.storage.store_quarantine(late_quar)

            for ready_event in ready_events:
                symbols_seen.add(ready_event.symbol)
                min_ts_ns = min(min_ts_ns, ready_event.timestamp_ns)
                max_ts_ns = max(max_ts_ns, ready_event.timestamp_ns)

                if isinstance(ready_event, TradeEvent):
                    trade_count += 1
                    trade_batch.append(ready_event)
                elif isinstance(ready_event, QuoteEvent):
                    quote_count += 1
                    quote_batch.append(ready_event)

                if len(trade_batch) + len(quote_batch) >= self.batch_size:
                    flush_batches()

        # Flush remaining events in reorder buffer
        for ready_event in self.reorder_buffer.flush():
            symbols_seen.add(ready_event.symbol)
            min_ts_ns = min(min_ts_ns, ready_event.timestamp_ns)
            max_ts_ns = max(max_ts_ns, ready_event.timestamp_ns)

            if isinstance(ready_event, TradeEvent):
                trade_count += 1
                trade_batch.append(ready_event)
            elif isinstance(ready_event, QuoteEvent):
                quote_count += 1
                quote_batch.append(ready_event)

        flush_batches()

        if min_ts_ns > max_ts_ns:
            min_ts_ns = 0
            max_ts_ns = 0

        manifest = ManifestManager.create_manifest(
            source_file=file_path,
            total_records=total_records,
            trade_count=trade_count,
            quote_count=quote_count,
            quarantine_count=quarantine_count,
            min_timestamp_ns=min_ts_ns,
            max_timestamp_ns=max_ts_ns,
            symbols=symbols_seen,
            config_dict=self.config,
        )

        self.storage.store_manifest(manifest)
        return manifest
