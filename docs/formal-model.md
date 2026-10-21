# Handoff: the formal model, made precise

**Repository:** `borisdev/graph-builder-spec`
**Status:** proposed replacement for the four-line model in two earlier handoffs. Not implemented;
nothing in the library changes. This is notation plus a mapping onto code that already exists.

**What this is for:** one page that states what the library *is*, precisely enough that the claims
in the README are theorems rather than slogans — and short enough to sit near the top of it.

---

## 0. Why the previous two notations were replaced

Both earlier versions were elegant and both under-described the library. The defects are specific:

```
version 1:   C := Oₙ ∘ ⋯ ∘ O₂ ∘ O₁
```

`∘` is **sequential composition only**, so this says every workflow is a chain. The library has
`JoinSpec` (several inputs arriving at one node) and parallel stages. The handoff noticed and added
a prose disclaimer — *"the model must not be restricted to linear pipelines"* — which is the
notation conceding that it does not cover the thing it models.

```
version 2:   Compose(A, B) = C        M(C), M(C′)
```

This dropped the **types**, which were the one thing version 1 got right. `Compose` with no typing
rule cannot say which combinations are legal, and "which combinations are legal" is the entire
product.

Both also hid the same thing, which turns out to be a live bug rather than a nicety: **the
environment a strategy runs in** (model name, temperature, backend). See §5.

---

## 1. The one sentence

> **A design is syntax. A strategy is semantics.**

Everything below is that sentence with the parts named. It is also why `coherence_check()` needs no
implementations: checking a design is checking *syntax*, and syntax does not run.

---

## 2. Objects — what travels on a wire

```
E = (entity, state)
```

An **object** is an entity in a declared state. Not a Python type: a *type plus a stage*.
`(stack_graph, "graded")` and `(stack_graph, "ranked")` are two different objects that happen to
share one Python class.

```
A, B ::= I | E | A ⊗ B
```

Objects compose, because a step can take or return more than one thing:

- `E` — a single entity state.
- `A ⊗ B` — *"an A and a B together"*. This is the **tensor** (read it as "and"), and it is what a
  two-input step consumes. `⊗` is not a choice between A and B; both are present.
- `I` — the **unit**: nothing at all, the empty product. A source step consumes `I`, which is what
  `START` means. A sink produces `I` (`END`).

Two laws, stated because the checker relies on them:

```
A ⊗ I = A              adding nothing changes nothing
(A ⊗ B) ⊗ C = A ⊗ (B ⊗ C)      grouping does not matter
A ⊗ B ≅ B ⊗ A          the order of a step's inputs does not matter  (the "symmetry")
```

The third is why a `JoinSpec` gathering two arrivals does not care which lands first.

---

## 3. Generators — the declared operators

```
o : A → B            a declared operator (a StepSpec), from object A to object B
O = { o₁, o₂, … }    the signature: every operator the language admits
```

A **generator** is one declared transformation, with its input object and output object fixed in the
declaration. It is a *name with a type*, and nothing else — no body, no model, no prompt. Those are
semantics and arrive in §4.

`O` is the **signature** of the language: the finite vocabulary a composer may use. This is the
formal version of *"the developer owns the language."* A composition naming an operator outside `O`
is not a sentence in the language, and the checker rejects it on that ground alone.

---

## 4. Terms — the designs, and what makes one legal

```
T(O)       every well-formed composition over the signature O
```

`T(O)` is built from the generators by exactly two combinators:

```
sequential     f : A → B      g : B → C          g ∘ f : A → C
               ──────────────────────────────────────────────
               legal only when f's output object IS g's input object

parallel       f : A → B      g : C → D
               ──────────────────────────────────────────────
               f ⊗ g : A ⊗ C → B ⊗ D             both run; neither feeds the other
```

A member `C ∈ T(O)` is a **term**: a complete, typed, well-formed design. The two rules are the
whole of well-formedness, and both are checkable by reading — no code, no execution, no LLM.

> **`coherence_check()` answers exactly one question: is this a member of `T(O)`?**

Three consequences worth spelling out, because each is a library behaviour:

- **Nothing need be implemented.** A term is syntax. (This is the README's *"8 of the 13 rules need
  nothing implemented."*)
- **A dangling or unproduced object is a type mismatch at a joint**, not a runtime error.
- **Two operators sharing a Python type are still distinguishable**, because objects are
  `(entity, state)` and the joint rule compares *objects*, not classes. This is the formal reason a
  `VariableSpec`/`EntityStateSpec` cannot be replaced by its model.

### Closure — a term is reusable as a generator

```
C ∈ T(O)   with boundary A → B      ⟹      O′ = O ∪ { c : A → B }
```

A finished design, taken whole, may be **adjoined to the signature as a new operator**. It then
composes wherever any operator of that boundary composes, and the thing using it cannot tell it
apart from a primitive.

That is SICP's third leg — *means of abstraction* — and in this library it is **already built**:
`SubgraphBinding` is a whole child design (`GraphSpec` + `StrategySpec`) used as one node's
implementation. **No change is needed for closure.** It is worth stating in the model because
closure is what makes `T(O)` a *language* rather than a menu.

---

## 5. Strategies — the semantics, and the index that was missing

```
σ : T(O) → 𝒦
```

A **strategy** is a *structure-preserving interpretation*: it sends each object to a real Python
type and each operator to a real callable, respecting both combinators:

```
σ(g ∘ f) = σ(g) ∘ σ(f)              composition maps to composition
σ(f ⊗ g) = σ(f) ⊗ σ(g)              parallel maps to parallel
```

Two facts follow, and both are library behaviours rather than coincidences:

**(a) A strategy is fixed by its action on the generators alone.** `T(O)` is *freely* generated, so
once you have chosen `σ(o)` for every `o ∈ O`, the value of `σ` on every term is forced. Which is
why:

> **A partial strategy is not a strategy at all.** It is undefined on a generator, so it is not an
> interpretation — hence the library *refuses* it rather than warning. (README: *"a partial strategy
> makes 'what varies between these arms' unanswerable without reading both files."*)

**(b) The difference between two strategies is a set.**

```
varies(σ, σ′) = { o ∈ O : σ(o) ≠ σ′(o) }
```

Literally what `spec.varies()` returns: the generators where the two interpretations disagree.

### `𝒦` is stochastic, and that is not a detail

```
𝒦 = Python types, with STOCHASTIC maps between them
```

An LLM step is not a function. The same input may give a different output. So `σ` does not land in
functions; it lands in **kernels** (input ↦ a distribution over outputs). One consequence, and it
explains a design decision from the mathematics:

> **A noise floor is forced by the target category, not chosen.** `B(C, σ, σ, D, M)` — the same
> strategy against itself — would be identically zero if `σ` were deterministic. It is not, so the
> A/A arm is a measurement rather than a formality, and reporting a battle without it compares two
> draws and calls it a difference.

### The environment index — this is the live bug

A step's behaviour also depends on an environment: model name, temperature, backend, retriever,
timeout. In this library that is `deps`. So a strategy is really a *family*:

```
σ_d          the strategy σ, run under environment d
```

Both earlier notations omitted `d`, and omitting it is exactly how the gap went unnoticed. Made
visible, the correctness condition is one line (see §6).

Concretely in this repo: `one_shot_41` and `one_shot_52` bind the **identical** implementation and
differ only in `deps.lm_key`. So `σ = σ′` and `varies()` correctly reports that nothing varies —
while `d ≠ d′`, and a battle between them would report a difference the design says cannot exist.

---

## 6. Battles — the experiment, and when it is defined

```
B(C, σ_d, σ′_d′, D, M)
```

| | |
|---|---|
| `C ∈ T(O)` | **one** term — the shared design. Both arms are interpretations *of this* |
| `σ_d, σ′_d′` | the two arms: strategies, each with its environment |
| `D` | the dataset: inputs of type `σ(A)` where `A` is `C`'s input object |
| `M` | measures on outputs: accuracy, cost, latency, a rubric, a judge |

**The definedness condition, which is the whole claim:**

```
B(C, σ_d, σ′_d′, D, M)   is defined   ⟺   d = d′
```

Read: *a comparison exists only when the two arms differ in the strategy and in nothing else.*

Two halves, in different states today:

```
one term C          ✅ enforced structurally. eval_battle takes exactly one `spec`
                       parameter — "there is nowhere to put the second design"
d = d′              ⛔ NOT enforced. eval_battle has no deps parameter; deps reach a run
                       through a caller-supplied `run` closure the library never sees,
                       and BattleResult records no conditions
```

So the honest claim today is **"comparable designs, recorded conditions"**, and the fix is the
missing half: record `(C-hash, σ-name, d, D-id, code-revision)` per result and refuse the comparison
when any field but `σ` differs. The refusal *is* the definedness condition, implemented.

---

## 7. Symbol table

| symbol | read as | in the library |
|---|---|---|
| `E = (entity, state)` | an entity in a declared state | `EntityStateSpec` (proposed) / `VariableSpec` (today) |
| `⊗` | "and" — several objects together | a step's multi-input / `JoinSpec` |
| `I` | nothing; the empty object | `START` consumes it, `END` produces it |
| `o : A → B` | a declared operator | `StepSpec` |
| `O` | the signature — the whole admitted vocabulary | the declared nodes, plus the registry |
| `∘` | sequential composition | an `EdgeSpec` joining two nodes |
| `T(O)` | every well-formed design over `O` | `GraphSpec` instances that pass `coherence_check` |
| `C ∈ T(O)` | one design | a `GraphSpec` |
| `σ` | an interpretation: operators ↦ callables | `StrategySpec` |
| `𝒦` | Python types with stochastic maps | real step bodies, which may call a model |
| `d` | the environment a strategy runs under | `deps` / `deps_type` |
| `D` | the evaluation cases | the dataset passed to `eval_battle` |
| `M` | the measures | graders, judges, rubrics, cost, latency |
| `B(…)` | a battle | `eval_battle()` |
| `varies(σ, σ′)` | where two interpretations differ | `spec.varies()` |

---

## 8. The whole model, as it would appear in the README

```
E = (entity, state)                  an entity in a declared state
A ::= I | E | A ⊗ B                  objects compose:  ⊗ is "and",  I is "nothing"

o : A → B                            a declared operator        ← the developer's vocabulary
O = { o₁ … oₙ }                      the signature

T(O)   closed under   g ∘ f          sequential, when the objects meet
                      f ⊗ g          parallel
                      C adjoined     a finished design, reused as an operator
                                     ← every legal design. SYNTAX. runs nothing.

σ : T(O) → 𝒦                         an implementation         ← SEMANTICS
                                     fixed by its action on O alone
σ_d                                  …under environment d

B(C, σ_d, σ′_d′, D, M)   defined ⟺  d = d′
                                     one design, two implementations, one dataset,
                                     one set of measures — or no comparison at all
```

Four lines of structure, one line of correctness. The claims then read off it:

| claim | what it is in the model |
|---|---|
| validate before implementing | membership in `T(O)` is a question about syntax |
| named stages, not just types | objects are `(entity, state)`, so the joint rule sees stages |
| composable | `T(O)` is closed, and a term is adjoinable as a generator |
| one design, many implementations | one `C`, many `σ` |
| what varies is attributable | `varies(σ, σ′) ⊆ O` |
| comparable by construction, or refused | the `d = d′` condition on `B` |

---

## 9. What this model deliberately does NOT say

Stated so that nobody reads a type check as a correctness proof.

- **A state is a label, not a predicate.** `(rod, "heated")` says *which object* a wire carries. It
  does not establish that a runtime rod was heated. The model guarantees compatibility at the
  joints; it says nothing about truth.
- **It says nothing about whether `M` is meaningful.** `M` is given. A badly chosen measure makes a
  well-formed battle worthless, and no amount of structure fixes that.
- **Membership in `T(O)` is not usefulness.** Every one of the 120 orderings of five same-typed
  steps may be a legal term under a weak signature; the point of entity states is to make most of
  them illegal, not all of them.
- **Branching is not modelled.** A decision whose *output object* depends on a value would need
  **coproducts** (`o : A → B + C`, read "B or C"). `⊗` is "and"; `+` would be "or". The library has
  decision nodes today, so this is the first honest extension — and it should be added as `+`
  rather than smuggled in as prose.
- **Loops are not modelled.** Feedback would need a trace operator. Out of scope until something
  needs it.
- **`d` is modelled as an index, not as structure.** Whether the environment belongs to the
  interpretation (as here) or to the design (the library puts `deps_type` on the spec) is a genuine
  open question — see below.

---

## 10. What I want reviewed

1. **Does `EdgeSpec` + `JoinSpec` actually implement `⊗` with the symmetry**, or only a restricted
   form of it? If inputs are ordered in a way that matters, the third law above is false and the
   notation must weaken.
2. **Branching:** the library has decision nodes. Does the model need `+` (coproducts) now, and what
   does `coherence_check` currently do with a node whose output object depends on a value?
3. **Where does `d` belong** — indexing the interpretation (`σ_d`, as proposed) or declared by the
   design (`deps_type`, as the code has it)? These disagree, and the answer decides whether
   `comparable()` compares a field of the design or of the run.
4. **Should `𝒦` be stochastic explicitly in the README?** It is what forces the noise floor, so it
   earns its line — but it also asks the reader to accept "not functions" early.
5. **Notation for the README:** plain Unicode in a fenced block (bulletproof, renders everywhere) or
   LaTeX (`$$…$$`, which GitHub renders but which breaks in plain-text contexts). Recommendation:
   Unicode in a fence; keep LaTeX for a paper.
6. **One thing to verify rather than believe:** whether `SubgraphBinding` is accepted everywhere a
   `StepSpec` is. If it is, §4's closure claim is already true in code and needs only documenting.
