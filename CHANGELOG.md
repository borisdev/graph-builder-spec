# Changelog

Format: [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
Versioning: [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.2.0] — 2026-09-30

### ⛔ Breaking — `NodeSpec` is renamed to `StepSpec`

**Step-by-step upgrade: [`docs/migration-0.2.md`](docs/migration-0.2.md).** One-line summary:

```python
NodeSpec("normalize", inputs=(a,), outputs=(b,))    # 0.1.0
StepSpec("normalize", inputs=(a,), outputs=(b,))    # 0.2.0
```

`NodeSpec` still exists and is now a **type alias**, not a class:

```python
NodeSpec = StepSpec | JoinSpec | DecisionSpec        # every box a design declares
```

So `NodeSpec(...)` raises `TypeError` while `x: NodeSpec` keeps type-checking. A call site that
instantiated it fails loudly; one that only annotated with it is unaffected.

**Why.** `NodeSpec` named the general concept and meant one specific kind. Pydantic Graph puts
START and END inside `graph.nodes` and calls `step` / `join` / `decision` the kinds — and this
repo's own wire format already agreed (`payload.Node` carries `kind: str = "step"`). Two of three
layers spoke that vocabulary; the declaration layer did not, which forced a second word
(`Endpoint`) for a set that already had one.

### Added

- `NodeSpec` as an alias for `StepSpec | JoinSpec | DecisionSpec` — every declared box.
- `Bindable` = `StepSpec | TransformEdgeSpec` — everything a strategy must bind. A
  `TransformEdgeSpec` left open is a variation point declared in `edges`, so `StrategySpec` was
  never steps-only; its annotation said otherwise and rejected the documented form.
- `LICENSE` (MIT), plus `readme`, `license` and project URLs in `pyproject.toml`.
- `docs/migration-0.2.md`, and this file.

### Removed

- `Endpoint`. It was a `str` shaped like a type alias, was exported in `__all__`, and had **zero
  references anywhere in the repo**. Superseded by `NodeSpec`.

### Changed

- Four annotations that were false are now true as written. `check_names`, `check_reachable`,
  `check_variables` and `check_fan_out_rejoins` all declared `tuple[NodeSpec, ...]` and were
  called with joins and decisions in that tuple. Same types at runtime; a type checker stops
  disagreeing with the code.
- `GraphSpec._check`'s local `endpoints` is now `declared`, annotated `tuple[NodeSpec, ...]`.
- `eval_battle` names each arm's task callable, so pydantic-evals' progress bar prints the
  strategy name instead of `<lambda>` for every arm.
- README rebuilt around one runnable walkthrough ([`examples/greeting.py`](examples/greeting.py)),
  with the eleven-rung ladder, the builder-feature table and the design rationale moved to
  `docs/`. Every figure in it is asserted by `tests/test_greeting.py` — including that the mermaid
  block *is* `diff_diagram()`'s output.
- `workflow_workbench.parity` writes `docs/parity.md` (was: the README appendix) and grew
  `--write`, so the derived table is never pasted by hand.

## [0.1.0]

Initial: `GraphSpec`, `StrategySpec`, `SubgraphBinding`, the checks, the diagrams, `eval_battle`,
the report viewer.
