# Migrating to 0.2.0 — `NodeSpec` → `StepSpec`

One rename. If your code only ever *constructed* nodes and strategies, the mechanical fix below
is the whole migration.

## The change

```python
normalize = NodeSpec("normalize", inputs=(raw,), outputs=(clean,))    # 0.1.0
normalize = StepSpec("normalize", inputs=(raw,), outputs=(clean,))    # 0.2.0
```

`NodeSpec` was the class you instantiate. It is now the **union of every declared box**:

```python
NodeSpec = StepSpec | JoinSpec | DecisionSpec        # a real runtime union
Bindable = StepSpec | TransformEdgeSpec              # everything a strategy binds
```

Both are real `types.UnionType` objects, so `isinstance(x, NodeSpec)` works.

## The mechanical fix

```bash
git ls-files '*.py' '*.md' | xargs sed -i 's/\bNodeSpec\b/StepSpec/g'
```

Then read back the **one** case where that is too aggressive — the trap below — and run the
verification at the foot of this page.

## What does NOT break

| | |
|---|---|
| `from graph_builder_spec import NodeSpec` | still works — `NodeSpec` is still exported |
| `def f(n: NodeSpec)` in your own code | still type-checks, and now accepts joins and decisions too |
| `JoinSpec`, `DecisionSpec`, `EdgeSpec`, `MapEdgeSpec`, `TransformEdgeSpec`, `VariableSpec`, `StrategySpec`, `SubgraphBinding`, `GraphSpec` | unchanged |
| `GraphSpec.nodes`, `.joins`, `.decisions`, `.edges` | unchanged. `nodes` still holds steps only |
| `check()`, `render()`, `diagram()`, `diff_diagram()`, `varies()`, `eval_battle()` | unchanged signatures |

**So an `ImportError` is not the failure mode.** Every missed call site fails at the call:

```
TypeError: 'types.UnionType' object is not callable
```

That is deliberate — a silent narrowing would have been worse than a loud stop.

## The one trap: do not narrow an annotation that means the union

The blanket `sed` turns *every* `NodeSpec` into `StepSpec`, including annotations where you meant
"any declared box". If your code has a helper that receives joins or decisions:

```python
def draw(boxes: tuple[NodeSpec, ...]) -> str: ...     # keep NodeSpec — it takes all three
def bind(step: NodeSpec, impl) -> None: ...           # -> StepSpec, it takes one kind
```

Find the candidates:

```bash
grep -rn 'StepSpec' --include=*.py . | grep -E 'tuple\[|list\[|Sequence\[|Iterable\['
```

Ask of each: **can a `JoinSpec` or a `DecisionSpec` arrive here?** If yes, put `NodeSpec` back.
This is exactly the bug the rename fixes — four annotations inside this library said
`tuple[NodeSpec, ...]` and were handed joins and decisions, and a type checker flagged every one.

`GraphSpec.nodes` is the reference case: it is steps only, and `(*nodes, *joins, *decisions)` is
the `NodeSpec` tuple.

## Also gone: `Endpoint`

Deleted. It was a `str` shaped like a type alias, exported in `__all__`, and referenced nowhere in
the repo. `NodeSpec` is what it was reaching for. If you imported it, the fix is `NodeSpec`.

## Verify you are done

**1. No constructor call survives.** This must print nothing:

```bash
grep -rn 'NodeSpec(' --include=*.py --include=*.md . | grep -v '.venv'
```

**2. Your specs still check clean** — the one that actually matters. Write a file and run it:

```python
from your.module import YourSpec, your_strategy

print(YourSpec().check(your_strategy) or "clean")
```

**3. Your own suite.**

```bash
pytest -q
```

Step 2 matters more than step 1. `check()` reads the declaration, so a spec that checks clean is a
spec whose nodes, edges and bindings all still line up — which a grep cannot tell you.
