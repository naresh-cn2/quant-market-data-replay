"""Streaming JSON Lines and JSON Array reader for raw market data."""

from decimal import Decimal
import json
from typing import Iterator

from src.ingestion.reader import BaseMarketDataReader, RawRecord


class JsonMarketDataReader(BaseMarketDataReader):
    """
    Streaming JSON reader supporting JSON Lines (JSONL) and JSON Arrays.

    Enforces Decimal parsing for all numeric components via `parse_float=Decimal`
    to guarantee zero binary float precision degradation.
    """

    def read_records(self) -> Iterator[RawRecord]:
        # Peek first non-whitespace character to determine if JSON array or JSONL
        is_array = False
        with open(self.file_path, mode="r", encoding="utf-8", errors="replace") as f:
            for line in f:
                stripped = line.strip()
                if stripped:
                    if stripped.startswith("["):
                        is_array = True
                    break

        if is_array:
            yield from self._read_json_array()
        else:
            yield from self._read_json_lines()

    def _read_json_lines(self) -> Iterator[RawRecord]:
        with open(self.file_path, mode="r", encoding="utf-8", errors="replace") as f:
            line_number = 0
            for line in f:
                line_number += 1
                raw_text = line.rstrip("\r\n")
                if not raw_text.strip():
                    continue

                try:
                    # parse_float=Decimal ensures numeric floats are never converted to binary float
                    data = json.loads(raw_text, parse_float=Decimal)
                    if not isinstance(data, dict):
                        yield RawRecord(
                            line_number=line_number,
                            raw_text=raw_text,
                            data={"_parse_error": f"Expected JSON object, got {type(data).__name__}"},
                            source_file=self.file_path,
                        )
                        continue

                    yield RawRecord(
                        line_number=line_number,
                        raw_text=raw_text,
                        data=data,
                        source_file=self.file_path,
                    )
                except Exception as e:
                    yield RawRecord(
                        line_number=line_number,
                        raw_text=raw_text,
                        data={"_parse_error": f"JSON parse error: {str(e)}"},
                        source_file=self.file_path,
                    )

    def _read_json_array(self) -> Iterator[RawRecord]:
        with open(self.file_path, mode="r", encoding="utf-8", errors="replace") as f:
            content = f.read()

        try:
            array_data = json.loads(content, parse_float=Decimal)
            if not isinstance(array_data, list):
                yield RawRecord(
                    line_number=1,
                    raw_text=content[:200],
                    data={"_parse_error": "JSON document is not an array"},
                    source_file=self.file_path,
                )
                return

            for idx, item in enumerate(array_data, start=1):
                raw_item_str = json.dumps(item, default=str)
                if not isinstance(item, dict):
                    yield RawRecord(
                        line_number=idx,
                        raw_text=raw_item_str,
                        data={"_parse_error": f"Array element {idx} is not an object"},
                        source_file=self.file_path,
                    )
                    continue

                yield RawRecord(
                    line_number=idx,
                    raw_text=raw_item_str,
                    data=item,
                    source_file=self.file_path,
                )
        except Exception as e:
            yield RawRecord(
                line_number=1,
                raw_text=content[:200],
                data={"_parse_error": f"JSON Array parse error: {str(e)}"},
                source_file=self.file_path,
            )
