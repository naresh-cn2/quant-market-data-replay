"""Ingestion package for streaming raw market data."""

import os
from typing import Optional

from src.ingestion.reader import BaseMarketDataReader, RawRecord
from src.ingestion.csv_reader import CsvMarketDataReader
from src.ingestion.json_reader import JsonMarketDataReader


def create_reader(file_path: str, format_hint: Optional[str] = None) -> BaseMarketDataReader:
    """
    Factory function to instantiate the appropriate reader for a market data file.
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Market data file not found: {file_path}")

    ext = os.path.splitext(file_path)[1].lower()
    hint = format_hint.lower() if format_hint else ""

    if hint == "csv" or ext in (".csv", ".tsv", ".txt"):
        return CsvMarketDataReader(file_path)
    if hint in ("json", "jsonl", "ndjson") or ext in (".json", ".jsonl", ".ndjson"):
        return JsonMarketDataReader(file_path)

    # Default fallback: inspect first non-empty byte
    with open(file_path, "r", encoding="utf-8", errors="replace") as f:
        first_char = ""
        for line in f:
            stripped = line.strip()
            if stripped:
                first_char = stripped[0]
                break

    if first_char in ("{", "["):
        return JsonMarketDataReader(file_path)

    return CsvMarketDataReader(file_path)


__all__ = [
    "BaseMarketDataReader",
    "RawRecord",
    "CsvMarketDataReader",
    "JsonMarketDataReader",
    "create_reader",
]
