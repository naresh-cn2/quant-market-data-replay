# Data Dictionary & Canonical Schemas

## 1. TradeEvent

| Field | Type | Description | Invariants / Constraints |
| :--- | :--- | :--- | :--- |
| `event_id` | `str` (SHA-256) | Deterministic unique event hash | 64 hex characters |
| `symbol` | `str` | Standardized ticker symbol | Uppercase, non-empty |
| `timestamp_ns` | `int` (64-bit) | UTC nanoseconds since epoch | $> 0$ |
| `price` | `Decimal` | Exact trade execution price | $> 0$ |
| `size` | `Decimal` | Exact trade quantity | $> 0$ |
| `side` | `Side` Enum | Aggressor order side | `BUY`, `SELL`, `UNKNOWN` |
| `source` | `str` | Data source / venue identifier | Non-empty |
| `sequence_id` | `Optional[int]` | Exchange sequence number | $\ge 0$ if present |

## 2. QuoteEvent (Top-of-Book / BBO)

| Field | Type | Description | Invariants / Constraints |
| :--- | :--- | :--- | :--- |
| `event_id` | `str` (SHA-256) | Deterministic unique event hash | 64 hex characters |
| `symbol` | `str` | Standardized ticker symbol | Uppercase, non-empty |
| `timestamp_ns` | `int` (64-bit) | UTC nanoseconds since epoch | $> 0$ |
| `bid_price` | `Decimal` | Best bid price | $\ge 0$ |
| `bid_size` | `Decimal` | Best bid quantity | $> 0$ |
| `ask_price` | `Decimal` | Best ask price | $\ge 0$ |
| `ask_size` | `Decimal` | Best ask quantity | $> 0$ |
| `source` | `str` | Data source / venue identifier | Non-empty |
| `sequence_id` | `Optional[int]` | Exchange sequence number | $\ge 0$ if present |

## 3. QuarantineRecord

| Field | Type | Description |
| :--- | :--- | :--- |
| `quarantine_id` | `str` | Unique quarantine identifier |
| `timestamp_ns` | `int` | Event timestamp or ingestion timestamp |
| `source` | `str` | Originating data source |
| `raw_record` | `str` | Exact unmutated raw input string |
| `error_code` | `str` | Machine-readable error classification code |
| `error_message` | `str` | Human-readable explanation of rejection |
| `severity` | `str` | `HARD_INVALID` or `FATAL_SYNTAX` |
| `field_name` | `Optional[str]` | Offending field name if identifiable |
