# Bounded Event Reordering

## 1. Problem Statement
Distributed matching engines and multi-cast network feeds (e.g. ITCH/OUCH, direct feeds) emit packets that may arrive slightly out of order due to network jitter, NIC buffers, and routing path differences.

Naive solutions either:
1. Load the entire multi-gigabyte/terabyte dataset into memory and sort globally ($O(N)$ memory failure).
2. Ignore out-of-order events, causing historical replay state corruptions.

## 2. Sliding Watermark Algorithm
The engine implements a bounded priority buffer with a sliding watermark:

1. Let $L$ be the configured maximum allowed lateness window in nanoseconds (e.g., $L = 5,000,000,000\text{ ns}$).
2. Maintain $T_{\max} = \max_{e \in \text{Seen}} (e.\text{timestamp\_ns})$.
3. Define the current watermark:
   $$\text{Watermark} = \max(0, T_{\max} - L)$$
4. For each incoming event $e$:
   - If $e.\text{timestamp\_ns} < \text{Watermark}$: Reject $e$ to Quarantine as `ERR_EXCESSIVE_LATENESS`.
   - Else: Insert $e$ into min-heap keyed by $(e.\text{timestamp\_ns}, e.\text{type\_priority}, e.\text{sequence\_id}, e.\text{event\_id})$.
5. While $\text{Heap.min}().\text{timestamp\_ns} \le \text{Watermark}$: Pop and emit the earliest event.
6. Upon stream completion (EOF): Flush all remaining heap items in strict sorted order.

## 3. Guarantees
- **Bounded Memory**: Memory is strictly bounded to $O(W)$, where $W$ is the maximum event count arriving within $L$ nanoseconds.
- **Monotonicity**: Emitted stream is strictly non-decreasing in timestamp.
- **Determinism**: Composite tie-breaking ensures identical ordering across runs.
