"""
Synthetic market data dataset generator for benchmarking and stress testing.
"""

from decimal import Decimal
import json
import os
import random
import time
from typing import Iterator, Optional


def generate_synthetic_trades_and_quotes(
    num_events: int = 100_000,
    symbol: str = "AAPL",
    start_time_ns: int = 1_789_552_800_000_000_000,  # 2026-09-16 10:00:00 UTC
    out_of_order_pct: float = 0.05,
    max_jitter_ns: int = 500_000_000,  # 500ms
    seed: int = 42,
) -> Iterator[dict]:
    """
    Generate synthetic stream of trade and quote dictionaries.
    """
    rng = random.Random(seed)
    current_px = Decimal("150.00")
    current_ts = start_time_ns

    for i in range(num_events):
        # Time increment (100us to 5ms)
        ts_inc = rng.randint(100_000, 5_000_000)
        current_ts += ts_inc

        # Inject jitter for out-of-order testing
        event_ts = current_ts
        if rng.random() < out_of_order_pct:
            jitter = rng.randint(-max_jitter_ns, max_jitter_ns)
            event_ts = max(0, current_ts + jitter)

        # Price random walk (-0.05 to +0.05)
        px_step = Decimal(str(rng.randint(-5, 5))) / Decimal("100")
        current_px = max(Decimal("1.00"), current_px + px_step)

        if rng.random() < 0.4:
            # Trade event
            size = rng.choice([10, 25, 50, 100, 200, 500, 1000])
            side = rng.choice(["BUY", "SELL"])
            yield {
                "event_type": "TRADE",
                "timestamp": event_ts,
                "symbol": symbol,
                "price": f"{current_px:.2f}",
                "size": str(size),
                "side": side,
                "source": "SYNTH_FEED",
                "sequence_id": i + 1,
            }
        else:
            # Quote event
            spread = Decimal(str(rng.randint(1, 5))) / Decimal("100")
            bid_px = current_px - (spread / 2)
            ask_px = current_px + (spread / 2)
            bid_sz = rng.choice([100, 200, 500, 1000])
            ask_sz = rng.choice([100, 200, 500, 1000])
            yield {
                "event_type": "QUOTE",
                "timestamp": event_ts,
                "symbol": symbol,
                "bid_price": f"{bid_px:.2f}",
                "bid_size": str(bid_sz),
                "ask_price": f"{ask_px:.2f}",
                "ask_size": str(ask_sz),
                "source": "SYNTH_FEED",
                "sequence_id": i + 1,
            }


def write_synthetic_dataset_csv(file_path: str, num_events: int = 100_000) -> None:
    """Write synthetic dataset to CSV file using buffered output."""
    os.makedirs(os.path.dirname(os.path.abspath(file_path)), exist_ok=True)
    with open(file_path, "w", encoding="utf-8", buffering=1024 * 1024) as f:
        f.write("timestamp,symbol,price,size,side,source\n")
        rng = random.Random(42)
        curr_ts = 1_789_552_800_000_000_000
        curr_px = Decimal("150.00")
        buf = []
        for i in range(num_events):
            curr_ts += rng.randint(100_000, 2_000_000)
            curr_px = max(Decimal("1.00"), curr_px + Decimal(str(rng.randint(-5, 5))) / Decimal("100"))
            size = rng.choice([10, 50, 100, 200, 500])
            side = rng.choice(["BUY", "SELL"])
            buf.append(f"{curr_ts},AAPL,{curr_px:.2f},{size},{side},SYNTH\n")
            if len(buf) >= 10000:
                f.writelines(buf)
                buf.clear()
        if buf:
            f.writelines(buf)


def write_synthetic_dataset_jsonl(file_path: str, num_events: int = 100_000) -> None:
    """Write synthetic dataset to JSONL file using buffered output."""
    os.makedirs(os.path.dirname(os.path.abspath(file_path)), exist_ok=True)
    with open(file_path, "w", encoding="utf-8", buffering=1024 * 1024) as f:
        buf = []
        for event in generate_synthetic_trades_and_quotes(num_events=num_events):
            buf.append(json.dumps(event) + "\n")
            if len(buf) >= 10000:
                f.writelines(buf)
                buf.clear()
        if buf:
            f.writelines(buf)
