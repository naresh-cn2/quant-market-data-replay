# Validation Rules & Diagnostics Matrix

## 1. Classification Hierarchy

The validation engine categorizes incoming observations into three strict tiers:

1. **`ACCEPTED`**: Fully conforming events that satisfy all structural, domain, and precision invariants.
2. **`SOFT_WARNING`**: Unusual but legitimate market conditions. Events are flagged with diagnostic records and stored normally in the canonical stream.
3. **`HARD_INVALID`**: Corrupt, unparseable, or mathematically impossible records. Events are rejected from canonical storage and diverted to the Quarantine sink.

## 2. Rule Specifications

| Rule Code | Tier | Trigger Condition | Rationale & Handling |
| :--- | :--- | :--- | :--- |
| `ERR_MISSING_SYMBOL` | `HARD_INVALID` | Empty or whitespace ticker symbol | Cannot attribute market event to instrument. |
| `ERR_INVALID_TIMESTAMP` | `HARD_INVALID` | $T \le 0$ or unparseable format | Chronological order cannot be established. |
| `ERR_NON_POSITIVE_PRICE` | `HARD_INVALID` | Trade price $\le 0$ | Trade executions must occur at positive price. |
| `ERR_NON_POSITIVE_SIZE` | `HARD_INVALID` | Trade or Quote size $\le 0$ | Zero or negative volume is structurally invalid. |
| `ERR_NEGATIVE_BID_PRICE` | `HARD_INVALID` | Bid price $< 0$ | Negative equity bids are invalid. |
| `ERR_NEGATIVE_ASK_PRICE` | `HARD_INVALID` | Ask price $< 0$ | Negative equity asks are invalid. |
| `WARN_CROSSED_MARKET` | `SOFT_WARNING` | $\text{ask\_price} < \text{bid\_price}$ | Occurs during fragmented routing / auction crosses. Logged but accepted. |
| `WARN_LOCKED_MARKET` | `SOFT_WARNING` | $\text{ask\_price} == \text{bid\_price}$ | Zero spread lock condition. Logged and accepted. |
| `WARN_LARGE_PRICE_JUMP` | `SOFT_WARNING` | $|\Delta P| / P_{\text{prev}} > 20\%$ | Major price move (flash news / volatility). Accepted without corruption bias. |
| `WARN_ZERO_BID_PRICE` | `SOFT_WARNING` | Bid price $= 0$ | Wide one-sided market / no bid interest. Accepted. |
| `ERR_EXCESSIVE_LATENESS` | `HARD_INVALID` | $T_{\text{event}} < \text{Watermark}$ | Arrived past bounded reorder window. Quarantined to preserve monotonic replay. |
