"""Streaming CSV reader for raw market data."""

import csv
from typing import Iterator

from src.ingestion.reader import BaseMarketDataReader, RawRecord


class CsvMarketDataReader(BaseMarketDataReader):
    """
    Streaming CSV reader.

    Reads lines lazily, strips whitespace, handles headers, and preserves
    exact raw line content. Never converts numeric fields to binary floats.
    """

    def read_records(self) -> Iterator[RawRecord]:
        with open(self.file_path, mode="r", encoding="utf-8", errors="replace") as f:
            line_number = 0
            header_line = None
            headers = None

            for line in f:
                line_number += 1
                raw_text = line.rstrip("\r\n")

                if not raw_text.strip():
                    continue

                if headers is None:
                    # Parse header line
                    header_line = raw_text
                    reader = csv.reader([raw_text])
                    headers = [h.strip() for h in next(reader)]
                    continue

                # Parse data line
                try:
                    reader = csv.reader([raw_text])
                    row = next(reader)
                except Exception as e:
                    # Corrupt CSV formatting line
                    yield RawRecord(
                        line_number=line_number,
                        raw_text=raw_text,
                        data={"_parse_error": f"CSV parse error: {str(e)}"},
                        source_file=self.file_path,
                    )
                    continue

                if len(row) != len(headers):
                    yield RawRecord(
                        line_number=line_number,
                        raw_text=raw_text,
                        data={
                            "_parse_error": f"Column count mismatch: expected {len(headers)}, got {len(row)}"
                        },
                        source_file=self.file_path,
                    )
                    continue

                row_dict = {h: val.strip() for h, val in zip(headers, row)}
                yield RawRecord(
                    line_number=line_number,
                    raw_text=raw_text,
                    data=row_dict,
                    source_file=self.file_path,
                )
