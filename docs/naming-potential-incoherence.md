# `potential_incoherence` and `subject` — the proposal, with the cost

Two renames you asked about. The first one has a fork in it that changes the work by ~20 names,
so it needs your call before I write it.

---

## 1. `check` → `potential_incoherence`

### ⛔ The fact that decides the shape

**13 check functions produce 30 distinct findings.** `check_reachable` alone produces five:

```
no edge leaves START — nothing in this design can ever run
no edge reaches END — this design produces no output
node X is unreachable from START — its implementation never runs
node X cannot reach END — whatever it produces is discarded
edge E references node Y, which is not in `nodes`
```

Those are five different things to fix. So:

```
13 members  = the CHECKERS       check_reachable, check_names, ...
30 members  = the INCOHERENCES   unreachable_from_start, no_path_to_end, ...
```

**If the field is called `potential_incoherence`, its values have to be the second kind.**
`potential_incoherence="check_reachable"` names a function, not an incoherence — a field promising
more precision than its value delivers, which is the failure this repo keeps catching.

### ⭐ Recommendation: one enumerated field, and `check` becomes derived

```python
finding.potential_incoherence   # PotentialIncoherence.UNREACHABLE_FROM_START   <- the enum
finding.check                   # "check_reachable"  <- derived via ONE table, not stored
```

Each incoherence belongs to exactly one check, so the mapping is many-to-one and total. Deriving
`check` from a single table means the two **cannot** drift, and one test asserts the table covers
every member. Storing both independently is how one concept gets two names.

### The 30 names, grouped by the check that owns them

| check | proposed members |
|---|---|
| `check_names` | `DUPLICATE_NODE_NAME` |
| `check_reachable` | `NOTHING_LEAVES_START` · `NOTHING_REACHES_END` · `UNREACHABLE_FROM_START` · `NO_PATH_TO_END` · `EDGE_REFERENCES_UNDECLARED_NODE` |
| `check_variables` | `SOURCE_DOES_NOT_DECLARE_CARRIED` · `TARGET_DOES_NOT_CONSUME_DELIVERED` |
| `check_step_arity` | `STEP_DECLARES_SEVERAL_INPUTS` · `CONCURRENT_ARRIVALS_WITHOUT_JOIN` |
| `check_decisions` | `DECISION_HAS_NO_BRANCHES` · `BRANCH_WITHOUT_WHEN` · `AMBIGUOUS_BRANCH_TYPE` · `WHEN_ON_A_NON_DECISION_EDGE` |
| `check_transform_edges` | `TRANSFORM_BOTH_FIXED_AND_BOUND` · `TRANSFORM_NEITHER_FIXED_NOR_BOUND` · `TRANSFORM_IS_ASYNC` |
| `check_fan_out_rejoins` | `FAN_OUT_REACHES_END_WITHOUT_JOIN` |
| `check_boundary_types` | `BOUNDARY_TYPE_MISMATCH` · `BOUNDARY_IS_OBJECT` · `BOUNDARY_TYPE_NOT_CHECKED` |
| `check_bindings` | `NODE_NOT_BOUND` · `BINDING_FOR_UNDECLARED_NODE` |
| `check_implementations` | `IMPLEMENTATION_WRONG_ARITY` · `IMPLEMENTATION_NOT_CHECKED` |
| `check_variable_types` | `RETURN_TYPE_MISMATCH` · `RETURN_TYPE_NOT_CHECKED` |
| `check_subgraphs` | `CHILD_INPUT_MISMATCH` · `CHILD_OUTPUT_MISMATCH` · `CHILD_PORT_NOT_CHECKED` |
| `check_recursion` | `RECURSIVE_BINDING` |

⚠️ Note the `*_NOT_CHECKED` members. A stated gap is **not** an incoherence — it is the absence of
a verdict. They are in the enum because every finding needs a value, and `blocking` already
distinguishes them, but it is worth knowing the enum mixes two kinds of thing. The alternative is
`potential_incoherence=None` on a stated gap, which is arguably more honest and means every
consumer must handle `None`.

### ⛔ YOUR CALL

| | cost | what you get |
|---|---|---|
| **A. the 30** | ~30 names coined, every finding site edited, one mapping table + test | a consumer can branch on the exact defect |
| **B. the 13** | mechanical rename of existing values | coarse filtering, and the field name overstates the value |

**I recommend A**, because B's field name does not survive contact with its own values. But A is
30 new words in the vocabulary, which is yours to approve.

---

## 2. `about` → `subject`, plus a kind

### Why `subject` and not your other candidates

**The word already exists in this repo**, which is the deciding argument — reuse it rather than
coin a synonym:

```
checks.py:547       "⚠️ `about` follows the SUBJECT of each sentence, not the loop variable"
reference.py:57     "what a check returns — the second table's subject"
test_workflow_spec  test_about_follows_the_subject_of_the_sentence_not_the_loop_variable
```

- `suspect_code` — ⛔ wrong twice. A `NOT CHECKED` finding has **no suspect**, and it is not
  *code* — it is a declaration. The word would make every stated gap read as an accusation.
- `spec_object_name` — accurate but says nothing a reader needs; `subject` is shorter and is the
  word the code already uses.

### But your two-field instinct is right, and here is the measurement

**You cannot tell the kinds apart by looking at the value.** Only edges are distinguishable:

```
"normalize"       a node      }
"trim_only"       a strategy  } INDISTINGUISHABLE — both are bare names
"propose->cite"   an edge       distinguishable, by the arrow
""                the design    distinguishable, by being empty
```

So a consumer that wants to branch on kind has to guess. That is the real conflation your
`spec_object_type` instinct found.

### ⭐ Recommendation

```python
finding.subject        # "step_a::orphan"
finding.subject_kind   # SubjectKind.NODE | EDGE | STRATEGY | DESIGN
```

- **`::` for nesting, pytest-style** — exactly your suggestion, and it reads as "inside" to anyone
  who has read a pytest node id. This is what #9 needs: a child's finding currently comes back as
  `"orphan"`, which is not a node the caller holds, and two children with an `orphan` each produce
  findings spelled identically.
- **`subject_kind` as an enum, not derived from the string.** Deriving it would mean guessing a
  node from a strategy, which is the thing that cannot be done.
- `DESIGN` rather than `""` for a whole-design finding, so the kind is always a real value and
  `subject` being empty is not load-bearing.

### Scope note

This is a **breaking change twice over**: `about` is read in both downstream repos, and the `::`
path changes values that were previously bare names. Pairs naturally with #9 (`GraphImplementation`
at 0.4.0), which is already a clean break — doing them together costs one migration instead of two.
