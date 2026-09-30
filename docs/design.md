# Design notes

Why the pieces are shaped the way they are. The [README](../README.md) is the walkthrough; this is
the reasoning behind it.

## Four layers, and this library owns one of them

| layer | question | who answers it |
|---|---|---|
| problem | what outcome is needed? | you |
| specification | what must a valid workflow contain and guarantee? | `GraphSpec` |
| implementation | how does each node fulfil its role? | `StrategySpec`, over native Pydantic Graph steps |
| execution | how is it run? | Pydantic Graph |

`GraphSpec` is the inspectable design. `StrategySpec` binds it to native Pydantic Graph step
implementations. Execution stays Pydantic Graph's, and `render()` returns their real `Graph` — so
`iter()`, streaming and every other part of their API keep working
([`stage7_iter.py`](../examples/ladder/stage7_iter.py) drives one unchanged).

## What it owns, and what it does not

This library owns the specification — `GraphSpec`, `NodeSpec`, `EdgeSpec`, `VariableSpec`,
`StrategySpec` — plus the checks, the strategy diagrams, and `eval_battle`.

Pydantic Evals owns `Case`, `Dataset`, `Evaluator`, `LLMJudge` and `EvaluationReport`; they are
imported and used directly. There is no `EvalCase`, no `EvalSuite`, no `Grader`, no `EvalReport`,
no `EvalHarness`.

It is a **strategy layer over Pydantic Graph**, not a new general workflow framework.

## The three things it adds

**1. Node identity belongs to the SPECIFICATION, not the implementation.** Without an explicit
`node_id`, pydantic-graph names a node after the bound function — so two strategies over one
design get disjoint node sets and a comparison has nothing to align on. Measured both ways in
[`docs/probe_api.py`](probe_api.py), probes 5 and 5b.

**2. A per-edge variable check.** A node with two outputs of the same type can have its two
outgoing edges swapped. Every set still matches — produced == consumed — and the wiring is wrong.
Only a per-edge check sees it, and `tests/test_workflow_spec.py` proves the set comparison agrees
with the bug while the per-edge one catches it.

**3. A diagram of what VARIES between two strategies.** Two strategies over one design render
byte-identical mermaid from `Graph.render()`, because a built graph retains no trace of the
strategy that produced it. `diff_diagram()` reads the declaration instead.

## One node role, a step or a whole subgraph

A `NodeSpec` keeps a role's identity and typed boundary stable. A strategy fills it with one
callable:

```python
better = StrategySpec("better", {extract: better_extract})
```

…or with a complete child design:

```python
fancy = StrategySpec("fancy", {extract: SubgraphBinding(VerifiedExtraction(), verified)})
```

The child must match the node's input/output contract and share the parent's exact `state_type`
and `deps_type` — it runs on the parent's actual objects. It stays independently runnable and
checkable, and the parent keeps **one** node id either way, which is what a battle aligns on.
Where a node is wired straight to `START`/`END` and declares no variable, the graph's own
`input_type`/`output_type` is what the child is checked against.

See [`examples/subgraph.py`](../examples/subgraph.py) for the `naive` / `better` / `fancy`
comparison, and [`stage4_subgraph.py`](../examples/ladder/stage4_subgraph.py) on the ladder.

## Two battle modes, and they answer different questions

```
independent   each arm scored alone against a fixed rubric, then the NUMBERS are diffed.
              "did the average move?"   -> pydantic-evals owns this entirely
pairwise      one judge sees BOTH outputs for the same case, side by side, and picks a winner.
              "which one is better?"    -> pydantic-evals has nothing for this
```

`pydantic_evals.evaluators` exports no pairwise evaluator and `EvaluatorContext` carries exactly
one `output`, so `pairwise_battle` is the only thing here that is not a thin call into the
library. It shuffles A/B order per case, seeded, and reports how often the arm shown first won —
position bias produces a clean, confident, meaningless sweep otherwise.

**The replicate is not optional.** Run one strategy against itself first; whatever difference that
produces is the noise floor, and a real delta has to clear it. `per_case_spread()` rather than a
difference of averages: a replicate whose per-case scores moved +1 and −1 has identical averages,
so a difference of averages reports a floor of 0.0 and licenses noise as a result.

## Further reading

- [`how-it-runs.md`](how-it-runs.md) — Pydantic Graph's executor from the source, with a probe
  behind every claim
- [`parity.md`](parity.md) — every builder feature, and the two that cannot be declared
- [`ladder.md`](ladder.md) — eleven worked rungs
