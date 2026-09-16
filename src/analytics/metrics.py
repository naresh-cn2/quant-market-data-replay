"""
Market microstructure metrics calculator for quantitative analysis.

All financial and volume calculations strictly preserve exact Decimal precision.
All timing calculations operate on 64-bit integer nanoseconds UTC.
"""

from dataclasses import dataclass, field
from decimal import Decimal
import math
from typing import Dict, List, Optional, Tuple, Union

from src.models.trade import TradeEvent, Side
from src.models.quote import QuoteEvent
from src.primitives.numeric import format_decimal


@dataclass
class SpreadMetricPoint:
    timestamp_ns: int
    bid_price: Decimal
    ask_price: Decimal
    quoted_spread: Decimal
    relative_spread_bps: Decimal
    is_crossed: bool


@dataclass
class PriceVwapPoint:
    timestamp_ns: int
    price: Decimal
    size: Decimal
    cumulative_volume: Decimal
    cumulative_vwap: Decimal
    side: str


@dataclass
class VolumeImbalancePoint:
    timestamp_ns: int
    cumulative_buy_volume: Decimal
    cumulative_sell_volume: Decimal
    volume_imbalance: Decimal  # (Buy - Sell) / (Buy + Sell)


@dataclass
class MicrostructureSummary:
    symbol: str
    total_events: int = 0
    trade_count: int = 0
    quote_count: int = 0
    total_volume: Decimal = field(default_factory=lambda: Decimal("0"))
    total_notional: Decimal = field(default_factory=lambda: Decimal("0"))
    final_vwap: Decimal = field(default_factory=lambda: Decimal("0"))
    min_price: Decimal = field(default_factory=lambda: Decimal("0"))
    max_price: Decimal = field(default_factory=lambda: Decimal("0"))
    last_price: Decimal = field(default_factory=lambda: Decimal("0"))
    mean_quoted_spread: Decimal = field(default_factory=lambda: Decimal("0"))
    mean_relative_spread_bps: Decimal = field(default_factory=lambda: Decimal("0"))
    crossed_quote_count: int = 0
    buy_volume: Decimal = field(default_factory=lambda: Decimal("0"))
    sell_volume: Decimal = field(default_factory=lambda: Decimal("0"))
    volume_imbalance_ratio: Decimal = field(default_factory=lambda: Decimal("0"))
    min_inter_arrival_ns: int = 0
    median_inter_arrival_ns: int = 0
    p90_inter_arrival_ns: int = 0
    p99_inter_arrival_ns: int = 0
    max_inter_arrival_ns: int = 0

    # Time series points for plotting
    spread_points: List[SpreadMetricPoint] = field(default_factory=list)
    vwap_points: List[PriceVwapPoint] = field(default_factory=list)
    imbalance_points: List[VolumeImbalancePoint] = field(default_factory=list)
    inter_arrival_deltas_us: List[float] = field(default_factory=list)


class MicrostructureMetricsCalculator:
    """
    Computes market microstructure metrics from a stream of TradeEvent and QuoteEvent instances.
    """

    def __init__(self, symbol: str):
        self.symbol = symbol.upper()

    def compute(
        self, events: List[Union[TradeEvent, QuoteEvent]]
    ) -> MicrostructureSummary:
        summary = MicrostructureSummary(symbol=self.symbol)
        summary.total_events = len(events)

        if not events:
            return summary

        cum_vol = Decimal("0")
        cum_notional = Decimal("0")
        cum_buy_vol = Decimal("0")
        cum_sell_vol = Decimal("0")

        total_spread_sum = Decimal("0")
        total_rel_spread_sum = Decimal("0")
        spread_count = 0

        last_ts_ns: Optional[int] = None
        inter_arrival_deltas_ns: List[int] = []

        prices: List[Decimal] = []

        for ev in events:
            # Latency / arrival delta tracking
            if last_ts_ns is not None:
                delta_ns = max(0, ev.timestamp_ns - last_ts_ns)
                inter_arrival_deltas_ns.append(delta_ns)
                summary.inter_arrival_deltas_us.append(delta_ns / 1_000.0)
            last_ts_ns = ev.timestamp_ns

            if isinstance(ev, TradeEvent):
                summary.trade_count += 1
                trade_px = ev.price
                trade_sz = ev.size
                prices.append(trade_px)

                cum_vol += trade_sz
                trade_notional = trade_px * trade_sz
                cum_notional += trade_notional
                current_vwap = cum_notional / cum_vol if cum_vol > Decimal(0) else trade_px

                if ev.side == Side.BUY:
                    cum_buy_vol += trade_sz
                elif ev.side == Side.SELL:
                    cum_sell_vol += trade_sz

                tot_trade_vol = cum_buy_vol + cum_sell_vol
                imbalance = (
                    (cum_buy_vol - cum_sell_vol) / tot_trade_vol
                    if tot_trade_vol > Decimal(0)
                    else Decimal("0")
                )

                summary.vwap_points.append(
                    PriceVwapPoint(
                        timestamp_ns=ev.timestamp_ns,
                        price=trade_px,
                        size=trade_sz,
                        cumulative_volume=cum_vol,
                        cumulative_vwap=current_vwap,
                        side=ev.side.value,
                    )
                )

                summary.imbalance_points.append(
                    VolumeImbalancePoint(
                        timestamp_ns=ev.timestamp_ns,
                        cumulative_buy_volume=cum_buy_vol,
                        cumulative_sell_volume=cum_sell_vol,
                        volume_imbalance=imbalance,
                    )
                )

            elif isinstance(ev, QuoteEvent):
                summary.quote_count += 1
                bp = ev.bid_price
                ap = ev.ask_price
                quoted_spread = ap - bp
                mid = (bp + ap) / Decimal("2")

                if mid > Decimal(0):
                    rel_bps = (quoted_spread / mid) * Decimal("10000")
                else:
                    rel_bps = Decimal("0")

                if ev.is_crossed:
                    summary.crossed_quote_count += 1

                total_spread_sum += quoted_spread
                total_rel_spread_sum += rel_bps
                spread_count += 1

                summary.spread_points.append(
                    SpreadMetricPoint(
                        timestamp_ns=ev.timestamp_ns,
                        bid_price=bp,
                        ask_price=ap,
                        quoted_spread=quoted_spread,
                        relative_spread_bps=rel_bps,
                        is_crossed=ev.is_crossed,
                    )
                )

        # Aggregate metrics
        summary.total_volume = cum_vol
        summary.total_notional = cum_notional
        summary.final_vwap = cum_notional / cum_vol if cum_vol > Decimal(0) else Decimal("0")
        summary.buy_volume = cum_buy_vol
        summary.sell_volume = cum_sell_vol
        tot_signed = cum_buy_vol + cum_sell_vol
        summary.volume_imbalance_ratio = (
            (cum_buy_vol - cum_sell_vol) / tot_signed
            if tot_signed > Decimal(0)
            else Decimal("0")
        )

        if prices:
            summary.min_price = min(prices)
            summary.max_price = max(prices)
            summary.last_price = prices[-1]

        if spread_count > 0:
            summary.mean_quoted_spread = total_spread_sum / Decimal(spread_count)
            summary.mean_relative_spread_bps = total_rel_spread_sum / Decimal(spread_count)

        if inter_arrival_deltas_ns:
            sorted_deltas = sorted(inter_arrival_deltas_ns)
            n = len(sorted_deltas)
            summary.min_inter_arrival_ns = sorted_deltas[0]
            summary.median_inter_arrival_ns = sorted_deltas[n // 2]
            summary.p90_inter_arrival_ns = sorted_deltas[min(n - 1, int(n * 0.90))]
            summary.p99_inter_arrival_ns = sorted_deltas[min(n - 1, int(n * 0.99))]
            summary.max_inter_arrival_ns = sorted_deltas[-1]

        return summary
