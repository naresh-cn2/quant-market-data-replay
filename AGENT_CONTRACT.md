# AI AGENT CONTRACT

Human = architect, decision authority and verification firewall.
Agent = implementation, test-generation, debugging and documentation worker.

Before coding:
1. Read SPEC.md.
2. Inspect repository.
3. Produce implementation plan and assumptions.
4. Stop for genuine requirement conflicts or irreversible architectural decisions.

Build order:
repository/tooling -> schemas/models -> timestamp/precision primitives -> ingestion -> normalization -> validation -> quarantine -> storage/manifest -> bounded reorder -> replay -> CLI/API -> tests -> integration -> adversarial validation -> benchmarks -> documentation.

Rules:
- Never fabricate test/benchmark results.
- Never silently drop invalid input.
- Never use float for canonical monetary/quantity state.
- Never silently change requirements.
- Never add dependencies without justification.
- Never implement live trading or real-money execution.
- Keep changes reviewable and reproducible.
