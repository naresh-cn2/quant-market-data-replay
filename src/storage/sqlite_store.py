"""
SQLite storage backend for canonical market data, quarantine, and manifests.
"""

from decimal import Decimal
import json
import sqlite3
from typing import Iterator, List, Optional, Tuple, Union

from src.models.trade import TradeEvent, Side
from src.models.quote import QuoteEvent
from src.models.quarantine import QuarantineRecord
from src.models.manifest import DatasetManifest
from src.primitives.numeric import parse_decimal, format_decimal
from src.storage.backend import BaseStorageBackend


class SqliteStorageBackend(BaseStorageBackend):
    """
    SQLite storage backend with WAL mode and composite indexing.
    """

    def __init__(self, db_path: str = ":memory:"):
        self.db_path = db_path
        self._conn = sqlite3.connect(db_path)
        self._conn.row_factory = sqlite3.Row
        self._init_db()

    def _init_db(self) -> None:
        with self._conn:
            # Enable WAL mode for high concurrency / throughput
            if self.db_path != ":memory:":
                self._conn.execute("PRAGMA journal_mode=WAL;")
            self._conn.execute("PRAGMA synchronous=NORMAL;")
            self._conn.execute("PRAGMA temp_store=MEMORY;")
            self._conn.execute("PRAGMA cache_size=-64000;")

            # Trades table
            self._conn.execute("""
                CREATE TABLE IF NOT EXISTS trades (
                    event_id TEXT PRIMARY KEY,
                    symbol TEXT NOT NULL,
                    timestamp_ns INTEGER NOT NULL,
                    price TEXT NOT NULL,
                    size TEXT NOT NULL,
                    side TEXT NOT NULL,
                    source TEXT NOT NULL,
                    sequence_id INTEGER
                );
            """)
            self._conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_trades_sym_ts
                ON trades(symbol, timestamp_ns, event_id);
            """)

            # Quotes table
            self._conn.execute("""
                CREATE TABLE IF NOT EXISTS quotes (
                    event_id TEXT PRIMARY KEY,
                    symbol TEXT NOT NULL,
                    timestamp_ns INTEGER NOT NULL,
                    bid_price TEXT NOT NULL,
                    bid_size TEXT NOT NULL,
                    ask_price TEXT NOT NULL,
                    ask_size TEXT NOT NULL,
                    source TEXT NOT NULL,
                    sequence_id INTEGER
                );
            """)
            self._conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_quotes_sym_ts
                ON quotes(symbol, timestamp_ns, event_id);
            """)

            # Quarantine table
            self._conn.execute("""
                CREATE TABLE IF NOT EXISTS quarantine (
                    quarantine_id TEXT PRIMARY KEY,
                    timestamp_ns INTEGER NOT NULL,
                    source TEXT NOT NULL,
                    raw_record TEXT NOT NULL,
                    error_code TEXT NOT NULL,
                    error_message TEXT NOT NULL,
                    severity TEXT NOT NULL,
                    field_name TEXT
                );
            """)

            # Manifests table
            self._conn.execute("""
                CREATE TABLE IF NOT EXISTS manifests (
                    dataset_id TEXT PRIMARY KEY,
                    schema_version TEXT NOT NULL,
                    created_at_utc TEXT NOT NULL,
                    source_file TEXT NOT NULL,
                    total_records INTEGER NOT NULL,
                    trade_count INTEGER NOT NULL,
                    quote_count INTEGER NOT NULL,
                    quarantine_count INTEGER NOT NULL,
                    min_timestamp_ns INTEGER NOT NULL,
                    max_timestamp_ns INTEGER NOT NULL,
                    sha256_checksum TEXT NOT NULL,
                    config_hash TEXT NOT NULL,
                    symbols_json TEXT NOT NULL
                );
            """)

    def store_trade(self, trade: TradeEvent) -> None:
        with self._conn:
            self._conn.execute(
                """
                INSERT OR REPLACE INTO trades (
                    event_id, symbol, timestamp_ns, price, size, side, source, sequence_id
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    trade.event_id,
                    trade.symbol,
                    trade.timestamp_ns,
                    format_decimal(trade.price),
                    format_decimal(trade.size),
                    trade.side.value,
                    trade.source,
                    trade.sequence_id,
                ),
            )

    def store_trades_batch(self, trades: List[TradeEvent]) -> None:
        if not trades:
            return
        params = [
            (
                t.event_id,
                t.symbol,
                t.timestamp_ns,
                format_decimal(t.price),
                format_decimal(t.size),
                t.side.value,
                t.source,
                t.sequence_id,
            )
            for t in trades
        ]
        with self._conn:
            self._conn.executemany(
                """
                INSERT OR REPLACE INTO trades (
                    event_id, symbol, timestamp_ns, price, size, side, source, sequence_id
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                params,
            )

    def store_quote(self, quote: QuoteEvent) -> None:
        with self._conn:
            self._conn.execute(
                """
                INSERT OR REPLACE INTO quotes (
                    event_id, symbol, timestamp_ns, bid_price, bid_size, ask_price, ask_size, source, sequence_id
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    quote.event_id,
                    quote.symbol,
                    quote.timestamp_ns,
                    format_decimal(quote.bid_price),
                    format_decimal(quote.bid_size),
                    format_decimal(quote.ask_price),
                    format_decimal(quote.ask_size),
                    quote.source,
                    quote.sequence_id,
                ),
            )

    def store_quotes_batch(self, quotes: List[QuoteEvent]) -> None:
        if not quotes:
            return
        params = [
            (
                q.event_id,
                q.symbol,
                q.timestamp_ns,
                format_decimal(q.bid_price),
                format_decimal(q.bid_size),
                format_decimal(q.ask_price),
                format_decimal(q.ask_size),
                q.source,
                q.sequence_id,
            )
            for q in quotes
        ]
        with self._conn:
            self._conn.executemany(
                """
                INSERT OR REPLACE INTO quotes (
                    event_id, symbol, timestamp_ns, bid_price, bid_size, ask_price, ask_size, source, sequence_id
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                params,
            )

    def store_quarantine(self, record: QuarantineRecord) -> None:
        with self._conn:
            self._conn.execute(
                """
                INSERT OR REPLACE INTO quarantine (
                    quarantine_id, timestamp_ns, source, raw_record, error_code, error_message, severity, field_name
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    record.quarantine_id,
                    record.timestamp_ns,
                    record.source,
                    record.raw_record,
                    record.error_code,
                    record.error_message,
                    record.severity,
                    record.field_name,
                ),
            )

    def store_quarantine_batch(self, records: List[QuarantineRecord]) -> None:
        if not records:
            return
        params = [
            (
                r.quarantine_id,
                r.timestamp_ns,
                r.source,
                r.raw_record,
                r.error_code,
                r.error_message,
                r.severity,
                r.field_name,
            )
            for r in records
        ]
        with self._conn:
            self._conn.executemany(
                """
                INSERT OR REPLACE INTO quarantine (
                    quarantine_id, timestamp_ns, source, raw_record, error_code, error_message, severity, field_name
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                params,
            )

    def store_manifest(self, manifest: DatasetManifest) -> None:
        with self._conn:
            self._conn.execute(
                """
                INSERT OR REPLACE INTO manifests (
                    dataset_id, schema_version, created_at_utc, source_file, total_records,
                    trade_count, quote_count, quarantine_count, min_timestamp_ns, max_timestamp_ns,
                    sha256_checksum, config_hash, symbols_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    manifest.dataset_id,
                    manifest.schema_version,
                    manifest.created_at_utc,
                    manifest.source_file,
                    manifest.total_records,
                    manifest.trade_count,
                    manifest.quote_count,
                    manifest.quarantine_count,
                    manifest.min_timestamp_ns,
                    manifest.max_timestamp_ns,
                    manifest.sha256_checksum,
                    manifest.config_hash,
                    json.dumps(manifest.symbols),
                ),
            )

    def get_manifest(self, dataset_id: str) -> Optional[DatasetManifest]:
        cursor = self._conn.cursor()
        cursor.execute("SELECT * FROM manifests WHERE dataset_id = ?", (dataset_id,))
        row = cursor.fetchone()
        if not row:
            return None
        return DatasetManifest(
            dataset_id=row["dataset_id"],
            schema_version=row["schema_version"],
            created_at_utc=row["created_at_utc"],
            source_file=row["source_file"],
            total_records=row["total_records"],
            trade_count=row["trade_count"],
            quote_count=row["quote_count"],
            quarantine_count=row["quarantine_count"],
            min_timestamp_ns=row["min_timestamp_ns"],
            max_timestamp_ns=row["max_timestamp_ns"],
            sha256_checksum=row["sha256_checksum"],
            config_hash=row["config_hash"],
            symbols=json.loads(row["symbols_json"]),
        )

    def query_stream(
        self,
        symbol: str,
        start_ns: int,
        end_ns: int,
        event_types: Tuple[str, ...] = ("TRADE", "QUOTE"),
    ) -> Iterator[Union[TradeEvent, QuoteEvent]]:
        """
        Stream events from database in strict deterministic order.
        Orders by: timestamp_ns ASC, event_type_priority ASC, event_id ASC.
        """
        symbol_upper = symbol.strip().upper()
        include_trades = "TRADE" in event_types
        include_quotes = "QUOTE" in event_types

        queries = []
        params = []

        if include_trades:
            queries.append("""
                SELECT
                    'TRADE' AS event_type,
                    1 AS event_type_priority,
                    event_id, symbol, timestamp_ns, price, size, side, source, sequence_id,
                    NULL AS bid_price, NULL AS bid_size, NULL AS ask_price, NULL AS ask_size
                FROM trades
                WHERE symbol = ? AND timestamp_ns >= ? AND timestamp_ns <= ?
            """)
            params.extend([symbol_upper, start_ns, end_ns])

        if include_quotes:
            queries.append("""
                SELECT
                    'QUOTE' AS event_type,
                    2 AS event_type_priority,
                    event_id, symbol, timestamp_ns, NULL AS price, NULL AS size, NULL AS side, source, sequence_id,
                    bid_price, bid_size, ask_price, ask_size
                FROM quotes
                WHERE symbol = ? AND timestamp_ns >= ? AND timestamp_ns <= ?
            """)
            params.extend([symbol_upper, start_ns, end_ns])

        if not queries:
            return

        union_sql = " UNION ALL ".join(queries)
        final_sql = f"{union_sql} ORDER BY timestamp_ns ASC, event_type_priority ASC, event_id ASC"

        cursor = self._conn.cursor()
        cursor.execute(final_sql, params)

        for row in cursor:
            ev_type = row["event_type"]
            if ev_type == "TRADE":
                yield TradeEvent(
                    event_id=row["event_id"],
                    symbol=row["symbol"],
                    timestamp_ns=row["timestamp_ns"],
                    price=parse_decimal(row["price"], "price"),
                    size=parse_decimal(row["size"], "size"),
                    side=Side.from_str(row["side"]),
                    source=row["source"],
                    sequence_id=row["sequence_id"],
                )
            elif ev_type == "QUOTE":
                yield QuoteEvent(
                    event_id=row["event_id"],
                    symbol=row["symbol"],
                    timestamp_ns=row["timestamp_ns"],
                    bid_price=parse_decimal(row["bid_price"], "bid_price"),
                    bid_size=parse_decimal(row["bid_size"], "bid_size"),
                    ask_price=parse_decimal(row["ask_price"], "ask_price"),
                    ask_size=parse_decimal(row["ask_size"], "ask_size"),
                    source=row["source"],
                    sequence_id=row["sequence_id"],
                )

    def close(self) -> None:
        self._conn.close()
