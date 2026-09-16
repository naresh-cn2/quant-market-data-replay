# Historical Replay Semantics & Point-in-Time Safety

## 1. Replay API Signature
```python
def replay_stream(
    symbol: str,
    start_ns: int,
    end_ns: int,
    event_types: Tuple[str, ...] = ("TRADE", "QUOTE")
) -> Iterator[Union[TradeEvent, QuoteEvent]]
```

## 2. Point-in-Time Safety Guarantees
- **No Future Leakage**: No event with timestamp $T > t_{\text{query\_end}}$ is ever yielded.
- **Strict Monotonicity**: Replayed events yield in monotonically non-decreasing timestamp order ($T_{i+1} \ge T_i$).
- **Streaming Iterator**: Events are streamed lazily using generators, preventing memory spikes during backtests spanning years of tick data.
- **Deterministic Equal-Timestamp Ordering**:
  When two events have identical nanosecond timestamps ($T_A = T_B$):
  1. Event Type Priority: `TRADE` (1) precedes `QUOTE` (2).
  2. Sequence ID: Lower sequence number precedes higher.
  3. Event Hash ID: Lexicographical comparison of 64-char SHA-256 identifier.
