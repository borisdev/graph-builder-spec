"""A ladder: one hello-world design, gaining one capability per rung.

Every rung is three things that must agree — a row in `docs/ladder.md`, the module here, and a
test in `tests/test_ladder.py`. If they ever disagree, the test is the one that goes red.

⚠️ `docs/ladder.md`, not the README: the README walks through `examples/greeting.py` instead, and
`test_the_ladder_doc_lists_every_rung_module` is what keeps a new rung from going unmentioned.

    their_hello           pydantic-graph alone. The control: what you get with no library.
    stage1_bare           the same design as a GraphSpec. One strategy.
    stage2_strategies     two strategies over ONE design.
    stage3_new_node       the design grows a node, and a partial strategy is refused.
    stage4_subgraph       one node implemented by a whole child design.
    stage5_battle         both strategies scored on the same cases, against a noise floor.
    stage6_diagrams       what varies between two arms — the picture theirs cannot draw.
    stage7_iter           `render()` returns a REAL Graph: their `iter()` works on it unchanged.

⚠️ The design is declared ONCE, in `stage1_bare`, and every later rung imports it. Declaring it
per stage would mean several `NodeSpec`s named "compose" with no relationship — which is the
duplication `check_names` reports, arriving inside the examples that demonstrate `check_names`.
"""
