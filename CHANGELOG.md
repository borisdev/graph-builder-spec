# Changelog

Format: [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
Versioning: [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### ⛔ Breaking — `object` is no longer a declarable type

```python
VariableSpec("verdict", object)          # SpecError, at declaration
VariableSpec("verdict", Plan | NotAPlan) # declare what actually flows
```

Boris, 2026-10-07: *"Stop allowing `object`."*

**Why.** `object` accepts anything, so `check_variable_types` could not decide — and it reported
**nothing**, which is `NOT CHECKED` and `0 FOUND` rendering identically, the one failure this
library exists to prevent. Measured before the change: the *same* wrong return type was caught
against a declared `int` and silent against a declared `object`. `#1` item 3.

A union is the replacement and is a better declaration besides: the types a `DecisionSpec`
branches on are exactly the union members, so the declaration now states what the routing
already assumed.

⚠️ **And the ban alone would have MOVED the silence rather than removed it.** `_produces` handled
a union *annotation* and not a union *declaration*, so `-> str` against a declared
`Urgent | Routine` still came back `NOT CHECKED`. Both halves ship together; a declared union now
decides — any member satisfying it is enough.

⚠️ `object` on a graph boundary (`input_type` / `output_type`) is now a **blocking finding** from
`check_boundary_types`, for the same reason.

⚠️ `check_boundary_types` now narrows an END edge by its `when=`. Without that, banning `object`
forced a *wider* `output_type` than the truth: `stage10`'s stop-early edge carries
`verdict: Plan | NotAPlan` but is `when=NotAPlan`, so only a `NotAPlan` can reach END along it,
and `output_type = NotAPlan | str` is correct. A branch type is a fact the declaration already
states.

**Migration.** Both examples that used it now declare unions, and the change immediately surfaced
**three real mismatches `object` had been hiding** — two implementations annotated `-> object`,
and the boundary imprecision above:

```
stage9  verdict      Urgent | Routine
stage10 verdict      Plan | NotAPlan
stage10 checked      TooThin | Plan
stage10 output_type  NotAPlan | str
```

⚠️ One migration trap, hit in this repo's own tests: with `from __future__ import annotations`,
`-> Again | Good` is a string resolved against the MODULE namespace. Classes defined inside a
test function are invisible to it and the check degrades to `NOT CHECKED` — honest, but the test
then asserts nothing. `object` hid that too, because it short-circuits before resolution.


### ⛔ Breaking — renamed to `graph-builder-spec`

```python
from workflow_workbench import GraphSpec     # before
from graph_builder_spec import GraphSpec     # after
```

| | before | after |
|---|---|---|
| distribution | `workflow-workbench` | `graph-builder-spec` |
| import package | `workflow_workbench` | `graph_builder_spec` |
| repository | `borisdev/workflow-workbench` | `borisdev/graph-builder-spec` |
| frontend source | `frontend/workflow-workbench/` | `frontend/graph-builder-spec/` |
| built island | `static/workflow-workbench.{js,css}` | `static/graph-builder-spec.{js,css}` |
| server env vars | `WORKFLOW_WORKBENCH_TOKEN` / `_STORE` | `GRAPH_BUILDER_SPEC_TOKEN` / `_STORE` |

**No alias, no shim.** A missing call site is an `ImportError` at the import, not a silent change
of behaviour — the same choice 0.2.0 made for `NodeSpec(...)` and 0.3.0 for `coherence_check()`.

⚠️ **The env-var rename fails CLOSED, which is why it is safe to do without an alias.** A stale
`WORKFLOW_WORKBENCH_TOKEN` is simply unset under the new name, and `serve()` raises `SystemExit`
rather than binding a non-localhost host unauthenticated — verified, not assumed. The process
refuses to start; it does not start without a token. `GRAPH_BUILDER_SPEC_STORE` falling back to
its default is a cosmetic path change, not an access-control one.

**Why.** The shipped subtitle is *"A declaration layer over Pydantic Graph Builder"*, and
`graph-builder-spec` is that sentence. It reuses **their** noun rather than inventing one
(`domain-language.md` #1 — before inventing a noun, look for one that exists), and `-spec`
matches `GraphSpec` / `StepSpec` / `StrategySpec`, the vocabulary a reader meets in the first
code block. `workflow-workbench` said nothing about what the library wraps.

Rejected: `pydantic-graph-spec` and `pydantic-graph-builder-spec` squat a namespace that belongs
to Pydantic's own packages; `graph-spec` collides with graph databases and GraphQL;
`workflow-spec` keeps a word the code uses and still says nothing about what is wrapped.

⚠️ **Downstream repos track `main`, not a sha**, so this breaks their next `uv sync` until their
dependency name is updated. GitHub redirects the old clone URL; the old **distribution name**
does not exist. `nobsmed-v2` and `ai_computer_use` are updated alongside.

⚠️ **Every `workflow-workbench` / `workflow_workbench` BELOW this entry is the former name**, left
as written. Those entries describe releases that really were published under it, and rewriting
them would make history describe a name that did not exist at the time.


### Added — `check_boundary_types`, the 13th rule

A `GraphSpec`'s declared `input_type` / `output_type` are now compared against the variables the
edges at START and END actually carry. They were never checked, and they go straight to
`GraphBuilder`:

```python
class Lying(Greeting):              # every edge in Greeting carries str
    input_type, output_type = int, int

Lying().coherence_check()           # [] — before
Lying().render(...).run_sync(inputs="  a  b  ")   # 'Hello, a  b!'  — a str
```

**A dead field would have been the small version.** `_port_type` reads those two fields as the
ORACLE for `check_subgraphs`, so a check that does run — whose whole job is *"the child fits the
node"* — was comparing a parent node's contract against the child's unverified claim about
itself. Measured: a child declaring `output_type=int` while every edge in it carries `str` passed
against a parent node declaring an int output, and the graph returned `'HELLO'`. Issue #21.

Assignability, not identity, and the direction differs per side: the input may be **widened** on
the way in (`input_type=list[int]` into an edge carrying `numbers: list` — `examples/parallel.py`
does this), the output **narrowed** on the way out (`report: str` reaching `output_type=object` —
`examples/ladder/stage10_no_basenode.py` does this).

⚠️ **The default `type(None)` is a claim, not an absence.** A design that never declares a
boundary and then wires a `str` across it is now reported, because that default reaches the
engine as the graph's real signature.

### Fixed — `_produces` called two spellings of one type undecidable

`list[int] is list[int]` is `False`, so identity alone reported *not decidable* for literally the
same type; and a parameterised alias was never compared against a bare declared type, although
`list[int]` plainly IS a `list`. Both now decide. This can only turn an undecidable into a
verdict — it cannot manufacture a finding where there was none — and it is why
`check_boundary_types` is clean on all 28 boundary crossings in `examples/` rather than printing
a permanent `NOT CHECKED` line on `parallel.py`.

`check_variable_types` reads the same helper and gains the same decidability.

⚠️ Only a **runtime class** origin is compared. `get_origin` is `typing.Literal` for
`Literal['ok']` and `typing.Annotated` for `Annotated[int, 'tag']`, and `issubclass` on either
raises — which the first cut of this did, through `coherence_check()`, a method documented
*"Never raises."* Those wrappers stay undecidable rather than being unwrapped; nothing has needed
unwrapping yet.

### Fixed — `_type_name` rendered `list[int]` and `list` identically

Its docstring said generic aliases have no `__name__`. Since 3.10 they do, and it is the bare
origin — so the bug was a WRONG name rather than a missing one, and a finding comparing those two
types read as a complaint that `list` is not `list`. Found while writing the message for the
check above, which compares exactly that pair.


## [0.3.0] — 2026-10-01

### ⛔ Breaking — `check()` is renamed to `coherence_check()`

**Step-by-step upgrade: [`docs/migration-0.3.md`](docs/migration-0.3.md).** One line:

```python
spec.check(strategy)              # 0.2.0
spec.coherence_check(strategy)    # 0.3.0
```

No alias. A missed call site is an `AttributeError` at the call, not a silent change of
behaviour — same choice 0.2.0 made when `NodeSpec(...)` became a `TypeError`.

**Why.** `check()` did not say what it checks, and the type it returns says `Coherence` — a word
that appeared nowhere else in the API. One concept was wearing two names, which is the thing the
house naming rule exists to prevent. `coherence_check()` grounds it.

`design_check()` was considered and rejected: `spec` *is* the design, so `spec.design_check()`
restates its own receiver.

**Unchanged:** the existing `check_*` functions, and the `check` field on a finding — both name
an individual check, which is what they still are.

**Added, and it is the twelfth:** `check_recursion`. The recursive-subgraph rule was enforced
inside `graph_spec.py`, so the generated rules table could not see it and said 11 while the code
enforced 12. The rule moved into `checks.py` and is exported; the CALL SITE did not move, because
a cycle has to stop the walk rather than be reported and walked into.

### Added — `coherence_check()` returns `CoherenceFinding`, not a bare `str`

**Backward compatible. No call site needs editing** — `CoherenceFinding` is a `str` subclass, so
`"x" in f`, `f.startswith(...)`, `"\n".join(findings)`, `f == "the message"`, sorting, hashing
and `repr()` in a printed list all behave exactly as before. Verified byte-for-byte across all 64
findings the test designs produce: nothing in the text moved.

```python
f = spec.coherence_check(strategy)[0]
f.check       # 'check_bindings' — the function that produced it
f.about       # 'compose' — a node name; 'source->target' for an edge; '' for the whole design
f.blocking    # True — False only for a `NOT CHECKED — …` stated gap

from workflow_workbench import blocking
blocking(findings)        # the filter `render()` uses; replaces startswith("NOT CHECKED")
```

**Why.** The findings were sentences, so the structure a caller needs was encoded in the prose.
`[f for f in findings if not f.startswith("NOT CHECKED")]` was load-bearing control flow in three
production call sites here and in both downstream repos — two different kinds of finding wearing
one type, told apart by a prefix match. `.claude/rules/checks.md`: *NOT CHECKED and 0 FOUND must
never render the same.* An agent using `coherence_check()` as its acceptance test could only regex it.

A frozen dataclass is tidier and costs a second breaking migration one release after `StepSpec`;
that is why the subclass wins. `blocking` is a bool rather than a severity enum — two states, and
no third has been observed.

- `CoherenceFinding`, `blocking()` and `NOT_CHECKED` are exported from the package root.
- `coherence_check()` and every `check_*` function are now annotated `list[CoherenceFinding]`.

### Upgrading

**The `check()` → `coherence_check()` rename above is breaking** — see the step above, not this
paragraph. What needs nothing is the FINDING REPRESENTATION: `CoherenceFinding` is a `str`
subclass, so every existing `f.startswith(...)`, `"\n".join(findings)` and `f == msg` keeps
working untouched. `uv lock --upgrade-package workflow-workbench` when you want the fields;
until then a pinned consumer is unaffected by either change.

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
