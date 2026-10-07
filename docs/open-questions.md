# Three open questions, by running them

Each section is a **runnable probe** in `docs/`, its real output pasted below. Same convention as
`docs/probe_api.py` and `docs/probe_builder_features.py` — the output is not hand-written, so it
goes stale loudly rather than quietly.

```bash
uv run python3 docs/probe_problem_gap.py            # 1
uv run python3 docs/probe_about_across_nesting.py   # 2
uv run python3 docs/probe_object_and_paths.py       # 3
```

Issues: #10, #9, #1 + #2. Measured on `bbf2766`.

---

## 1. `GraphSpec.problem` (#10) — a requirement that evaporates

**The question:** a role says what every implementation must do. A reusable *graph* has its own
purpose. When you bind the graph to the role, who owns the brief?

**The failure:** the parent's role demands quotations. The child graph does not do quotations. All
types match, so nothing objects.

```
1. the parent's requirement, written down:
   extract.problem = 'Extract claims WITH a supporting quotation for each.'

2. can the CHILD state its own purpose, so the two could be compared?
   hasattr(GraphSpec, 'problem') = False   <-- THE GAP

3. coherence_check with the child bound to that role:
   []        <-- CLEAN. Paper->Claims lines up.

4. what it actually produces:
   text='Metformin lowers A1c'                               quote=''
   text='Fasting insulin was never measured'                 quote=''

   Every quote is empty. The requirement was in extract.problem, a string
   nothing compares to anything, and types cannot carry 'with a quotation'.
```

**Consequence:** `StepSpec.problem` exists and is the only place the requirement is written;
`GraphSpec.problem` does not exist, so there is nothing to compare it against. The rule to
implement: neither brief overrides, replaces or fills in the other, and a **missing** role brief
must never display the child's in its place — that makes a borrowed purpose read as the role's
requirement.

---

## 2. `about` (#9) — what it is, and why nesting breaks it

**The question:** you asked what `about` is. It is one of three attributes on a finding, so a
caller can branch on structure instead of regexing an English sentence.

```
PART 1 — `about` on a flat design. Three attributes per finding:

   about        check                  blocking  the sentence
   'orphan'     check_reachable        True      node 'orphan' is unreachable from START — its im...
   'orphan'     check_reachable        True      node 'orphan' cannot reach END — whatever it pro...
   'parse'      check_bindings         True      strategy 'partial' does not bind node 'parse'. E...
   'orphan'     check_bindings         True      strategy 'partial' does not bind node 'orphan'. ...

   A UI does nodes[f.about] to highlight the box. No regex on English.
   nodes['orphan'] -> StepSpec('orphan', (t: str) -> (t: str))


PART 2 — the SAME field, once a child graph is bound. ⛔ THE BUG:

   about='orphan'   resolves in the parent? False   node 'orphan' is unreachable from START ...
   about='orphan'   resolves in the parent? False   node 'orphan' cannot reach END — whateve...
   about='orphan'   resolves in the parent? False   node 'orphan' is unreachable from START ...
   about='orphan'   resolves in the parent? False   node 'orphan' cannot reach END — whateve...

   parent's nodes: ['step_a', 'step_b']
   abouts handed back: ['orphan', 'orphan', 'orphan', 'orphan']
   -> nodes['orphan'] would KeyError: the caller holds the parent.
   -> and the two children BOTH have a node called 'orphan', so their
      findings are spelled IDENTICALLY: 4 of them, indistinguishable.

   The fix #9 carries: about must become a PATH — 'step_a/orphan'.
```

**Consequence:** on a flat design `about` works — `nodes[f.about]` resolves and a UI can highlight
the box. Nested, **all four findings come back as `'orphan'`**, none of which is a node the caller
holds, and the two children's are spelled identically. `about` has to become a path
(`step_a/orphan`), which is why it rides along with the `GraphImplementation` rename instead of
landing on its own.

---

## 3. #1 and #2

**#1 asks:** where does a declaration claim something nothing verifies? Four places; three are
documented boundaries between what a spec checks and what an eval measures. **One is a real bug.**

**#2 asks:** should an edge be an ordered list of steps, like pydantic's `Path`?

```
========================================================================
#1 item 3 — `object` USED to switch the check off silently. Now it is refused.
========================================================================

A. the mistake, when the type is concrete — always caught:
   CAUGHT: 's' binds 'gate' to returns_a_string, which returns str — but 'gate' is declared to produce ...

B. `object`, which used to make the SAME mistake report CLEAN:
   REFUSED at declaration: 'verdict' is declared `object`, which accepts anything. That silently switches OFF type ...

C. the replacement — declare what actually flows, as a union:
   right impl  -> CLEAN
   wrong impl  -> 's' binds 'gate' to returns_a_string, which returns str — but 'gate' is declared to prod...

   ⛔ C IS WHY THE BAN ALONE WOULD NOT HAVE BEEN ENOUGH. `_produces` handled a union
   ANNOTATION and not a union DECLARATION, so `-> str` against `Urgent | Routine` came
   back NOT CHECKED. Banning `object` without that would have moved the silence, not
   removed it. Both halves shipped together.

D. and the examples that used `object` now declare the truth:
   stage9  verdict: examples.ladder.stage9_decision.Urgent | examples.ladder.stage9_decision.Routine
   stage10 verdict: examples.ladder.stage10_no_basenode.Plan | examples.ladder.stage10_no_basenode.NotAPlan
   stage10 checked: examples.ladder.stage10_no_basenode.TooThin | examples.ladder.stage10_no_basenode.Plan
   stage10 output_type: examples.ladder.stage10_no_basenode.NotAPlan | str
   both still check clean: True

========================================================================
#2 — fan out AND reshape on one wire. Not expressible.
========================================================================

What you want: carries a list, delivers ONE pmid per item.
  MapEdgeSpec  fans out      list -> paper
  then reshape               paper -> pmid     before it lands

  MapEdgeSpec(..., apply=...) -> TypeError: MapEdgeSpec.__init__() got an unexpected keyword argument 'apply'

  No single edge is both. The workaround is a step that exists only to unwrap:
    StepSpec('unwrap', (paper: str) -> (pmid: str))
    MapEdgeSpec(source=START, target=unwrap, carries=papers, delivers=paper)
    EdgeSpec(source=unwrap, target=rate, carries=pmid)
  ...which puts a BOX on the diagram for something that is not a stage.

⚠️ But the two are genuinely different KINDS of thing at build time:
   a map is rewritten into a real Fork NODE before the executor runs;
   a transform survives on the wire and is walked per completion.
   pydantic's own _flatten_paths asserts exactly that:
     assert not isinstance(item, MapMarker | BroadcastMarker),
            'These should be removed during Graph building'

   So our separate types say out loud what a uniform list would hide.
   TRIGGER to build it: the first real design that needs it. None does yet.
```

**Consequence for #1:** the fix is one `NOT CHECKED` line folded into the existing summary, not a
new rule. It costs rung 9 one honest line of output and makes the opt-out visible.

**Consequence for #2:** no, not yet — and the reason is mechanical rather than aesthetic. A `map`
becomes a real `Fork` node at build time and a `transform` does not, so our two types say out loud
what one uniform list would hide until `_flatten_paths`. The trigger is written down: the first
design that needs to fan out a collection *and* reshape each item before it lands, where the
alternative is a step that exists only to unwrap.
