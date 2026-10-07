# The four open questions you asked about

Not committed yet — written for a read-through. The GitHub issues stay canonical; this is one
page so you don't have to open four tabs. Every number and every output below was produced by
running the code on `main` (`bbf2766`), today.

---

## 1. "Pattern catalogue" (#13) — what it is, and why I'd drop it

### What someone proposed

A `patterns/` directory of reusable workflow shapes, each with Alexander-style prose — recurring
problem, context, why this arrangement helps, tradeoffs, how it varies, how to evaluate, relation
to other patterns. The pitch: a library of *named arrangements* you reach for, like "Pipeline" or
"Fan-out / reduce", rather than examples you read once.

### Why it is nothing today

```
examples/
  greeting.py            2 steps. Has a battle. Its own docstring says it is NOT contestable.
  contestable.py         4 judgement-call stages. Has a TEST FORBIDDING a score.
  parallel.py            fan-out + join. No dataset.
  counter.py             loop-back. No dataset.
  subgraph.py            nested graph. No dataset.
  ladder/stage1..10      11 teaching rungs, deliberately repetitive.
  local/extraction.py    no dataset.
```

A "pattern" was supposed to be distinguishable from an example by being *measured* — importable
by name, shipping a `Dataset` and ≥2 strategies, with a recorded noise floor. **Measured against
that bar, the count is zero**, and it is zero in all 15 designs. So the catalogue is an empty
directory with a manifesto.

### The actual failure mode

With no checkable test, "pattern" degrades into *whatever someone wrote six paragraphs about* —
which is `spec-as-code.md`'s exact prohibition: a confidently wrong doc is worse than no doc,
because a missing doc makes you read the code.

### ⭐ Recommendation: drop it

- `examples/` already does the job, and the **ladder** (11 rungs, each adding one concept) is a
  better teaching device than a catalogue because its order is enforced by tests.
- A registry with zero members is an abstraction with no caller — `project.md`'s standing rule.
- **The double-check, so this is not just my opinion:** if the idea were load-bearing, something
  would already be reaching for it. Grepped: `pattern` appears in no type name, no module, no
  public export, and no test. It exists only in issue prose.

Build it the day two designs genuinely share an arrangement and someone wants to pick between
them by name. Not before.

---

## 2. `GraphSpec.problem` (#10) — a brief that disappears across a boundary

### The field that exists

```python
normalize = StepSpec("normalize", inputs=(raw_name,), outputs=(clean_name,),
                     problem="How much of what the caller typed counts as the name?")
```

`StepSpec.problem` is **the problem, never the solution** — what *every* implementation of this
role must deal with. Measured: `'problem' in StepSpec.__dataclass_fields__` → `True`.

### The field that does not

`hasattr(GraphSpec, 'problem')` → **`False`**. A reusable graph cannot state its own purpose.

### Why that is a real bug, in one worked case

A parent declares a role. A child graph is bound as its implementation.

```python
# the PARENT's role — note what it demands
extract = StepSpec("extract", inputs=(paper,), outputs=(claims,),
                   problem="Extract claims WITH a supporting quotation for each.")

# the CHILD graph, written elsewhere, reused here
class ExtractFactualClaims(GraphSpec):      # its own purpose: "extract factual claims"
    input_type, output_type = Paper, Claims  # ...and nothing says "no quotations"
    ...

StrategySpec("arm", {extract: GraphImplementation(graph=ExtractFactualClaims(), strategy=...)})
```

`coherence_check()` passes. The types line up — `Paper` in, `Claims` out — and **types cannot
carry "with a supporting quotation."** The parent's requirement is silently dropped, and the only
place it was ever written down is the parent's `problem` string, which nothing compares against
anything.

### The rule, and the part that is easy to get wrong

```
StepSpec.problem    what EVERY implementation of this role must address
GraphSpec.problem   this reusable graph's OWN problem
```

**Neither overrides, replaces, or fills in the other.** Specifically: when the role's brief is
missing, the child's brief must *not* be shown in its place — that would make a borrowed purpose
read as the role's requirement. And absence must stay distinguishable from a written brief,
because an empty `problem` means *nothing is claimed*, not *this stage is easy*.

### Out of scope, deliberately

- **No `rubric` field.** A rubric belongs where something can run it. Grepped: no `step_battle`,
  no `run_step`, no `StepRunner` exists.
- **No mandatory prose.** A required brief makes the ones written to satisfy a type checker
  indistinguishable from the ones written because somebody thought about the problem.

### ⚠️ The known trap

`StepSpec.problem` reached the payload and stopped there for a whole release — it was in the JSON
and never rendered. It now shows in the Panel with browser tests. **The same mistake is available
to `GraphSpec.problem`**: adding the field is 3 lines, and it is worthless until a surface shows it.

---

## 3. What `about` is (#9's real work)

### What it is

Every finding from `coherence_check()` is a `CoherenceFinding` — a `str` subclass, so it prints
and compares exactly like the plain string it used to be, but carrying three extra attributes:

```python
f = CoherenceFinding("orphan is unreachable", check="check_reachable", about="orphan")

str(f)       # 'orphan is unreachable'   <- byte-identical to the old plain string
f.check      # 'check_reachable'         <- which rule produced it
f.about      # 'orphan'                  <- WHAT IT IS ABOUT
f.blocking   # True                      <- defect, vs a `NOT CHECKED` stated gap
```

`about` exists so a caller can **branch on structure instead of regexing the sentence**. A UI
highlighting the offending node does `nodes[f.about]`; without it, it would parse English.

### Its documented value space — exactly four kinds

```
"normalize"          a node / join / decision name
"propose->cite"      source->target, for a finding about an edge
"trim_only"          a strategy name
""                   the whole design (e.g. "no edge reaches END")
```

`test_every_finding_names_something_the_caller_can_look_up` enforces that set — it asserts every
non-empty `about` resolves to something the caller actually holds. That is why, when I added
`check_boundary_types` yesterday, I wrote `about="input_type"` and then **reverted it**: a port
name would be a fifth kind, and quietly widening a field other code resolves is a vocabulary
change, not an implementation detail.

### The bug #9 has to fix

A child graph's findings are propagated to the parent **unchanged**, so their `about` is relative
to the *child*:

```python
parent.coherence_check(strategy)
# -> [... about="orphan" ...]
#
#    `orphan` is a node in the CHILD. The caller holds the parent.
#    nodes["orphan"] -> KeyError. And two different children with a node of
#    the same name produce two findings that are spelled identically.
```

So `about` needs to carry a **path** across a nesting boundary — something like
`"extract/orphan"` — which changes what the field means and is why it rides along with the
`SubgraphBinding` → `GraphImplementation` rename rather than landing separately.

---

## 4. #1 and #2, plainly

### #1 — "four places the declaration outruns the check"

A catalogue of places a `GraphSpec` **claims** something nothing verifies. Three are documented
boundaries; **one is a real bug.**

| | claim | status |
|---|---|---|
| **3** | `VariableSpec("v", object)` silently disables type checking for that variable | ⛔ **the bug** |
| 1 | a step can return the *wrong value* of the right type | boundary: spec vs eval |
| 2 | a `-> int` annotation is not enforced by Python | boundary: complements a type checker |
| 4 | a streaming node has no useful return annotation | already honest — reports `NOT CHECKED` |

**Why #3 is the bug, measured today:**

```python
verdict = VariableSpec("verdict", object)       # examples/ladder/stage9_decision.py does this
async def returns_anything(ctx) -> str: ...     # declared to produce `object`

coherence_check()          -> CLEAN   (no mention of `object`)
coherence_check(strategy)  -> CLEAN   (nothing said about `object` accepting anything)
```

Declaring `object` turns the check off **and says nothing**, which is `checks.md`'s headline
prohibition: `NOT CHECKED` and `0 FOUND` must never render the same. The fix is one `NOT CHECKED`
line folded into the existing summary — the opt-out becomes visible instead of invisible. Cost:
rung 9's output gains one honest line.

### #2 — should an edge be a list of steps?

Pydantic's own edge is an ordered list of markers, so theirs composes and ours does not:

```python
# THEIRS — measured against 2.35.1, runs, returns ['ADA','GRACE']
g.edge_from(g.start_node).map().transform(lambda ctx: ctx.inputs["name"]).to(shout)

# OURS — not expressible. MapEdgeSpec and TransformEdgeSpec are separate types,
# and no single edge can be both.
```

**The answer is currently no, and the reason is not taste.** The two are different *kinds* of
thing at build time:

```python
# _flatten_paths, pydantic's graph_builder.py
assert not isinstance(item, MapMarker | BroadcastMarker), 'These should be removed during Graph building'
```

A `map` is rewritten into a real `Fork` **node** before the executor runs; a `transform` survives
on the wire and is walked per completion. Our two types say that out loud where a uniform list
hides it. Their `Path` field is literally called `working_items` — an accumulator left behind by
method chaining, which is the natural shape of a fluent builder and not of a literal declaration.

**The trigger to build it**, written down so nobody re-argues it: the first design that wants to
fan out a collection *and* reshape each item before it lands — `carries=list[Paper]`,
`delivers=pmid` — where the alternative is a step that exists only to unwrap. Nothing in 11 ladder
rungs or 6 nobsmed arms needs it yet.
