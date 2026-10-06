"""`check_boundary_types` — the graph's declared boundary against the edges that cross it.

⛔ WHY THIS FILE EXISTS. `input_type` / `output_type` go straight to `GraphBuilder`, and until
2026-10-06 nothing compared them to the design they belong to. A dead field would have been the
small version: `_port_type` reads them as the ORACLE for `check_subgraphs`, so a check that does
run, whose whole job is "the child fits the node", was comparing a node's contract against the
child's unverified claim about itself. Issue #21.

⚠️ The failure mode this file is written against is the repo's own recurring one, 7 for 7 across
#8, #18 and #19: **a check narrower than its claim.** A guard written beside the thing it guards
inherits the author's assumption about where the fact lives. So the broad test here is
`test_no_design_in_the_repo_is_flagged_or_silently_skipped`, which runs over every `GraphSpec` in
`examples/` rather than over the four this module authors.
"""
from __future__ import annotations

import importlib
from pathlib import Path

from graph_builder_spec import (
    END, START, EdgeSpec, GraphSpec, StepSpec, StrategySpec, SubgraphBinding,
    TransformEdgeSpec, VariableSpec, check_boundary_types)
from graph_builder_spec.checks import NOT_CHECKED, blocking

text = VariableSpec("text", str)
num = VariableSpec("num", int)
items = VariableSpec("items", list)

step = StepSpec("step", inputs=(text,), outputs=(text,))


def _design(**attrs) -> GraphSpec:
    base = {"name": "d", "nodes": (step,),
            "edges": (EdgeSpec(source=START, target=step, carries=text),
                      EdgeSpec(source=step, target=END, carries=text)),
            "input_type": str, "output_type": str}
    return type("D", (GraphSpec,), {**base, **attrs})()


listy = StepSpec("listy", inputs=(items,), outputs=(items,))


def _listy(**attrs) -> GraphSpec:
    """A design whose single step consumes and produces `items: list`, so only the declared
    boundary varies between cases."""
    base = {"name": "l", "nodes": (listy,),
            "edges": (EdgeSpec(source=START, target=listy, carries=items),
                      EdgeSpec(source=listy, target=END, carries=items))}
    return type("L", (GraphSpec,), {**base, **attrs})()


def _port(finding: str) -> str:
    """Which side a finding is about. Read out of the SENTENCE, because `about` deliberately does
    not carry a port name — see `check_boundary_types`."""
    return "input_type" if "input_type" in finding else "output_type"


async def same(ctx) -> str:
    return ctx.inputs


STRATEGY = StrategySpec("s", {step: same})


# ── the two failures, one per side ───────────────────────────────────────────────────────────

def test_a_lying_input_type_is_a_blocking_finding() -> None:
    findings = _design(input_type=int).coherence_check()
    assert len(findings) == 1, findings
    assert "input_type int" in findings[0] and "'text' (str)" in findings[0]
    assert findings[0].check == "check_boundary_types"
    assert findings[0].about == "", (
        "a boundary belongs to the design, not to a node — and `about` holds a node / edge / "
        "strategy name or nothing. A port name would be a fifth kind of value in a field "
        "test_every_finding_names_something_the_caller_can_look_up resolves.")
    assert blocking(findings)


def test_a_lying_output_type_is_a_blocking_finding() -> None:
    findings = _design(output_type=int).coherence_check()
    assert len(findings) == 1, findings
    assert "output_type int" in findings[0] and "'text' (str)" in findings[0]
    assert blocking(findings)


def test_render_refuses_a_design_whose_boundary_is_wrong() -> None:
    """A blocking finding must stop the build, not merely be reported. Otherwise the engine gets
    a signature the design contradicts and the mismatch surfaces at the caller."""
    import pytest

    from graph_builder_spec import SpecError

    with pytest.raises(SpecError):
        _design(output_type=int).render(STRATEGY)


def test_the_default_boundary_is_a_claim_and_is_reported() -> None:
    """`type(None)` is not an absence — `render()` hands it to `GraphBuilder` as the graph's real
    signature. A design that never declares a boundary and then wires a `str` across it is making
    a false claim, and there is no third state to tell it apart from a deliberate None design."""
    findings = _design(input_type=type(None), output_type=type(None)).coherence_check()
    assert len(findings) == 2, findings
    assert {_port(f) for f in findings} == {"input_type", "output_type"}, findings


# ── the direction of assignability differs per side, and both are legal shapes ────────────────

def test_the_input_may_be_WIDENED_on_the_way_in() -> None:
    """The graph receives `input_type` and the edge carries it onward, so a wider carried
    variable is correct. `examples/parallel.py` really does this: `input_type=list[int]` crossing
    an edge that carries `numbers: list`."""
    assert _listy(input_type=list[int], output_type=list).coherence_check() == []


def test_the_output_may_be_NARROWED_on_the_way_out() -> None:
    """The edge delivers and the graph promises, so a narrower delivered type is correct.
    `examples/ladder/stage10_no_basenode.py` really does this: `report: str` reaching an
    `output_type=object`."""
    assert _design(output_type=object).coherence_check() == []


def test_the_reverse_of_each_is_NOT_legal() -> None:
    """⛔ The half that makes the two tests above mean something. A check that accepted both
    directions on both sides would pass all four of these designs and prove nothing.

    ⚠️ `check_boundary_types` directly, not `coherence_check()`: narrowing on the way IN means
    declaring a wider boundary than the edge carries, and the only way to write that without
    also tripping `check_variables` is to isolate the rule under test."""
    narrowed_in = _listy(input_type=list, output_type=list)
    narrowed_in.__class__.input_type = object       # wider in than the edge carries
    assert [_port(f) for f in check_boundary_types(narrowed_in)] == ["input_type"]

    widened_out = _design(output_type=object)
    widened_out.__class__.output_type = int         # narrower out than the edge delivers
    assert [_port(f) for f in check_boundary_types(widened_out)] == ["output_type"]


# ── what actually arrives at END ─────────────────────────────────────────────────────────────

def test_a_transform_edge_is_compared_on_what_it_DELIVERS() -> None:
    """A `TransformEdgeSpec` reshapes ON THE WIRE, so the carried type is not what the caller
    gets. Comparing `carries` here would flag the correct design and pass the wrong one."""
    def length(v: str) -> int:
        return len(v)

    correct = _design(output_type=int,
                      edges=(EdgeSpec(source=START, target=step, carries=text),
                             TransformEdgeSpec(source=step, target=END, carries=text,
                                               delivers=num, apply=length)))
    assert correct.coherence_check() == []

    wrong = _design(output_type=str,
                    edges=(EdgeSpec(source=START, target=step, carries=text),
                           TransformEdgeSpec(source=step, target=END, carries=text,
                                             delivers=num, apply=length)))
    assert [_port(f) for f in wrong.coherence_check()] == ["output_type"]


# ── undecidable is reported, never passed ────────────────────────────────────────────────────

def test_an_undecidable_pair_is_stated_and_does_not_block() -> None:
    """`list[int]` against a declared `list[str]` cannot be settled by `issubclass`. A guess
    either way is worse than saying so — and NOT CHECKED must not stop a render."""
    nums = VariableSpec("nums", list[int])
    through = StepSpec("through", inputs=(nums,), outputs=(nums,))
    d = type("P", (GraphSpec,), {
        "name": "p", "nodes": (through,), "input_type": list[int], "output_type": list[str],
        "edges": (EdgeSpec(source=START, target=through, carries=nums),
                  EdgeSpec(source=through, target=END, carries=nums))})()
    findings = check_boundary_types(d)
    assert len(findings) == 1 and findings[0].startswith(NOT_CHECKED), findings
    assert not blocking(findings)
    assert "list[str]" in findings[0] and "list[int]" in findings[0], (
        "a generic alias must print its parameter — `__name__` is 'list' for both, which would "
        "render this finding as a complaint that list is not list")


def test_the_exact_repro_from_the_issue_on_a_REAL_example() -> None:
    """⚠️ Not a synthetic `_design`. Every other case here is a fixture this module authored, and
    a guard written beside the thing it guards inherits its author's assumptions — the repo's
    recurring defect, 7 for 7 across #8, #18 and #19. So this one subclasses a shipped example
    and reproduces #21's measurement verbatim: clean before, and it ran returning a `str`.
    """
    from examples.greeting import Greeting, trim_only

    class Lying(Greeting):
        name = "lying"
        input_type, output_type = int, int

    findings = Lying().coherence_check()
    assert len(findings) == 2, findings
    assert all(f.check == "check_boundary_types" for f in findings)
    assert blocking(findings)

    import pytest

    from graph_builder_spec import SpecError

    with pytest.raises(SpecError):
        Lying().render(trim_only)

    assert Greeting().coherence_check(trim_only) == [], (
        "the unmodified example must stay clean — otherwise this proves nothing about the lie")


# ── the consequence that made this worth fixing ──────────────────────────────────────────────

def test_a_subgraph_can_no_longer_pass_on_a_claim_nothing_verified() -> None:
    """⛔ THE ONE THAT MATTERS MOST. `check_subgraphs` compares a parent node's contract against
    `child.output_type`. Measured before the fix: a child declaring `output_type=int` while every
    edge in it carries `str` passed against a parent node declaring an int output, and the graph
    returned `'HELLO'`."""
    inner = StepSpec("inner", inputs=(text,), outputs=(text,))

    class Child(GraphSpec):
        name = "child"
        input_type, output_type = str, int          # the lie
        nodes = (inner,)
        edges = (EdgeSpec(source=START, target=inner, carries=text),
                 EdgeSpec(source=inner, target=END, carries=text))

    async def shout(ctx) -> str:
        return ctx.inputs.upper()

    child_strategy = StrategySpec("child_s", {inner: shout})
    produce = StepSpec("produce", inputs=(text,), outputs=(num,))

    class Parent(GraphSpec):
        name = "parent"
        input_type, output_type = str, int
        nodes = (produce,)
        edges = (EdgeSpec(source=START, target=produce, carries=text),
                 EdgeSpec(source=produce, target=END, carries=num))

    parent_strategy = StrategySpec(
        "parent_s", {produce: SubgraphBinding(graph=Child(), strategy=child_strategy)})

    assert blocking(Child().coherence_check(child_strategy)), "the child's own lie must be caught"
    assert blocking(Parent().coherence_check(parent_strategy)), (
        "the parent walks into the child, so the lie must surface there too")


# ── the broad one: calibration against the repo, not against this module ─────────────────────

EXAMPLES = Path(__file__).resolve().parent.parent / "examples"


def _designs_in_examples() -> dict[str, type]:
    """Every `GraphSpec` under `examples/`, discovered by FILE and imported without a net.

    ⛔ This was `pkgutil.walk_packages`, wrapped in `except Exception: continue`, and it was
    wrong in both halves — caught by Copilot on #22:

        examples/local/      has no `__init__.py`, so walk_packages never descended into it and
                             `examples.local.extraction.Extraction` was never checked
        except: continue     a module that failed to import was silently dropped, so the
                             calibration below could go green having checked nothing

    The `>= 8` floor let either omission pass. A missing input must never read as a pass —
    `.claude/rules/checks.md` — so discovery is by path and an import error is an error.
    """
    found: dict[str, type] = {}
    for path in sorted(EXAMPLES.rglob("*.py")):
        if "__pycache__" in path.parts:
            continue
        rel = path.relative_to(EXAMPLES.parent).with_suffix("")
        name = ".".join(rel.parts)
        m = importlib.import_module(name)          # ⛔ no try — a broken example is a failure
        for obj in vars(m).values():
            if isinstance(obj, type) and issubclass(obj, GraphSpec) and obj is not GraphSpec:
                found.setdefault(f"{obj.__module__}.{obj.__name__}", obj)
    return found


def test_discovery_reaches_every_example_FILE_not_every_example_package() -> None:
    """⚠️ The guard on the guard. `test_no_design_in_the_repo_is_flagged` is only as broad as
    this, and the first version of it quietly covered 14 of 15 designs."""
    modules = {q.rsplit(".", 1)[0] for q in _designs_in_examples()}
    assert "examples.local.extraction" in modules, (
        "examples/local has no __init__.py — a package-based walk skips it entirely")
    files = {p for p in EXAMPLES.rglob("*.py") if "__pycache__" not in p.parts}
    assert len(files) >= 14, f"only {len(files)} example files — discovery is looking in the wrong place"


def test_no_design_in_the_repo_is_flagged_or_silently_skipped() -> None:
    """⚠️ THE CALIBRATION, and the reason this is not a check nobody reads.

    A new blocking rule that fires on the repo's own examples is a rule that gets routed around.
    Measured when this landed: every boundary crossing in every example, 0 findings — and the one
    that was undecidable (`parallel.py`'s `list[int]` into `numbers: list`) is decidable because
    `_produces` compares a parameterised alias against its origin, not because the example was
    edited to suit the check.
    """
    designs = _designs_in_examples()
    assert len(designs) >= 15, f"only found {len(designs)} designs — this would pass vacuously"
    for qual, cls in sorted(designs.items()):
        findings = check_boundary_types(cls())
        assert findings == [], f"{qual}: {findings}"


# ── the regression Copilot found, and it was a raise rather than a wrong answer ───────────────

def test_a_typing_wrapper_whose_origin_is_not_a_class_does_not_CRASH_the_check() -> None:
    """⛔ `get_origin` does not always return a runtime class — it is `typing.Literal` for
    `Literal['ok']` and `typing.Annotated` for `Annotated[int, 'tag']`, and `issubclass` on
    either raises `TypeError: issubclass() arg 1 must be a class`.

    The first cut of the alias branch in `_produces` had no class guard, so a step annotated
    `-> Literal['ok', 'no']` made `coherence_check()` RAISE — and that method is documented
    "Never raises." A crash is not a conservative failure: every other finding in the sweep is
    lost with it.
    """
    from typing import Annotated, Literal

    from graph_builder_spec.checks import _produces

    assert _produces(Literal["ok", "no"], str) is None
    assert _produces(Annotated[int, "tag"], int) is None

    async def decide(ctx) -> Literal["ok", "no"]:
        return "ok"

    findings = _design().coherence_check(StrategySpec("literal_arm", {step: decide}))
    assert len(findings) == 1 and findings[0].startswith(NOT_CHECKED), findings
    assert not blocking(findings), "undecidable must not stop a render"
