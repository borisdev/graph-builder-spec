"""Eval-layer tests, against a REAL `pydantic_evals.Dataset` — no mocks of the library."""
from __future__ import annotations

import pytest

from pydantic_evals import Case, Dataset
from pydantic_evals.evaluators import Evaluator, EvaluatorContext

from graph_builder_spec import (END, START, EdgeSpec, GraphSpec, SpecError, StepSpec,
                                 StrategySpec, VariableSpec)
from graph_builder_spec.evals import BattleResult, eval_battle, pairwise_battle

text = VariableSpec("text", str)
work = StepSpec("work", inputs=(text,), outputs=(text,))


class Job(GraphSpec):
    name = "job"
    input_type, output_type = str, str
    nodes = (work,)
    edges = (EdgeSpec(source=START, target=work, carries=text), EdgeSpec(source=work, target=END, carries=text))


async def shout(ctx) -> str:
    return ctx.inputs.upper()


async def pad(ctx) -> str:
    return ctx.inputs + "!!!"


loud = StrategySpec("loud", {work: shout})
padded = StrategySpec("padded", {work: pad})


class Length(Evaluator[str, str]):
    def evaluate(self, ctx: EvaluatorContext[str, str]) -> float:
        return float(len(ctx.output))


def dataset() -> Dataset:
    return Dataset(name="t", evaluators=[Length()],
                   cases=[Case(name="c1", inputs="ab"), Case(name="c2", inputs="cdef")])


def test_battle_runs_both_arms_on_the_same_cases():
    res = eval_battle(Job(), loud, padded, dataset())
    assert isinstance(res, BattleResult)
    assert res.label_a == "loud" and res.label_b == "padded"
    assert len(res.report_a.cases) == len(res.report_b.cases) == 2
    assert [c.name for c in res.report_a.cases] == [c.name for c in res.report_b.cases]


def test_battle_returns_native_reports_not_a_copy():
    """The stop condition: reuse pydantic-evals' own report type rather than re-implement it."""
    from pydantic_evals.reporting import EvaluationReport
    res = eval_battle(Job(), loud, padded, dataset())
    assert isinstance(res.report_a, EvaluationReport)
    assert isinstance(res.report_b, EvaluationReport)


def test_labels_survive_into_the_report():
    res = eval_battle(Job(), loud, padded, dataset())
    assert res.report_a.name == "loud"
    assert res.report_b.name == "padded"


def test_deltas_are_computed_per_metric():
    res = eval_battle(Job(), loud, padded, dataset())
    # loud preserves length; padded adds 3 chars per case.
    assert res.deltas()["Length"] == pytest.approx(3.0)


def test_a_replicate_is_detected_and_labelled():
    res = eval_battle(Job(), loud, loud, dataset())
    assert res.is_replicate
    assert "REPLICATE" in repr(res)


def test_replicate_of_a_deterministic_strategy_has_a_zero_floor():
    res = eval_battle(Job(), loud, loud, dataset())
    assert res.deltas()["Length"] == 0.0
    assert res.per_case_spread()["Length"] == 0.0


def test_per_case_spread_does_not_cancel_where_averages_do():
    """⛔ THE REGRESSION FOR THE NOISE-FLOOR BUG.

    Two cases drift +1 and −1. The AVERAGES are identical, so a difference-of-averages reports a
    floor of 0.0 — and a real +0.5 gain elsewhere would then read as signal. The per-case spread
    reports 1.0, which is the honest bar.
    """
    a = _fake_report({"c1": 5.0, "c2": 5.0})
    b = _fake_report({"c1": 6.0, "c2": 4.0})
    res = BattleResult("s", "a", "b", a, b, is_replicate=True)

    assert res.deltas()["m"] == 0.0            # the averages agree — the trap
    assert res.per_case_spread()["m"] == 1.0   # the drift is real and reported


def test_battle_refuses_a_strategy_that_does_not_satisfy_the_spec():
    from graph_builder_spec import SpecError
    with pytest.raises(SpecError):
        eval_battle(Job(), loud, StrategySpec("empty", {}), dataset())


def test_one_spec_argument_makes_cross_design_comparison_unexpressible():
    """Fairness is structural: `eval_battle` has exactly one `spec` parameter, so there is
    nowhere to put a second design."""
    import inspect
    params = list(inspect.signature(eval_battle).parameters)
    assert params[0] == "spec"
    assert sum(1 for p in params if "spec" in p) == 1


# ── pairwise mode ───────────────────────────────────────────────────────────────────────────

def test_pairwise_judge_never_sees_which_arm_is_which_and_order_is_shuffled():
    seen_first: list[str] = []

    def judge(inputs, first, second):
        seen_first.append(first)
        return ("first", "picked the first one")     # a deliberately position-biased judge

    cases = [Case(name=f"c{i}", inputs="x" * i) for i in range(1, 9)]
    res = pairwise_battle(Job(), loud, padded, cases, judge=judge, seed=0)

    assert len(res.verdicts) == 8
    # Order really varied — both arms appeared first at least once.
    assert len({v.shown_first for v in res.verdicts}) == 2
    # And the bias is measurable, which is the point of recording `shown_first`.
    bias = res.position_bias()
    assert bias["first_shown_won"] == bias["total_decided"] == 8


def test_pairwise_tally_counts_winners():
    def judge(inputs, first, second):
        return ("second", "")

    cases = [Case(name="c1", inputs="ab")]
    res = pairwise_battle(Job(), loud, padded, cases, judge=judge, seed=1)
    assert sum(res.tally().values()) == 1


def test_pairwise_is_reproducible_under_a_seed():
    def judge(inputs, first, second):
        return ("tie", "")

    cases = [Case(name=f"c{i}", inputs="x") for i in range(6)]
    a = pairwise_battle(Job(), loud, padded, cases, judge=judge, seed=7)
    b = pairwise_battle(Job(), loud, padded, cases, judge=judge, seed=7)
    assert [v.shown_first for v in a.verdicts] == [v.shown_first for v in b.verdicts]


# ── helpers ─────────────────────────────────────────────────────────────────────────────────

class _Score:
    def __init__(self, value: float):
        self.value = value


class _Case:
    def __init__(self, name: str, scores: dict[str, float]):
        self.name = name
        self.scores = {k: _Score(v) for k, v in scores.items()}


class _Report:
    """Minimal stand-in for an EvaluationReport, used ONLY where the arithmetic is under test and
    running two real graphs would add nothing. Every other test here uses the real library."""

    def __init__(self, per_case: dict[str, float]):
        self.cases = [_Case(n, {"m": v}) for n, v in per_case.items()]
        self._avg = sum(per_case.values()) / len(per_case)

    def averages(self):
        return type("A", (), {"scores": {"m": _Score(self._avg)}})()


def _fake_report(per_case: dict[str, float]) -> _Report:
    return _Report(per_case)


# ── run_count: N runs, N numbers, no verdict ────────────────────────────────────────────────

def test_run_count_reports_every_run_and_editorialises_about_none_of_them() -> None:
    """#11, re-specced. Boris, 2026-10-07: *"JUST SIMPLY REPORT 3 runs 3 numbers .... w a
    optional arg for run_count=int."*

    ⛔ What this asserts is as much about what is ABSENT as what is present: there is no mean, no
    spread, no winner and no refusal. The earlier design ran an automatic A/A arm and declined to
    name a winner inside the noise — a judgement made on the caller's behalf, at 50% more compute
    on every battle. Three numbers are strictly more information than a verdict derived from them.
    """
    from examples.greeting import Greeting, dataset, normalize_spaces, trim_only

    spec, data = Greeting(), dataset()
    r = eval_battle(spec, trim_only, normalize_spaces, data, run_count=3)

    scores = r.run_scores()
    assert set(scores) == {"trim_only", "normalize_spaces"}
    for arm, metrics in scores.items():
        for metric, values in metrics.items():
            assert len(values) == 3, f"{arm}/{metric} gave {len(values)} runs, not 3"
    # deterministic implementations, so all three agree — which is the signal, not a problem
    assert scores["trim_only"]["ExactMatch"] == [0.5, 0.5, 0.5]
    assert scores["normalize_spaces"]["ExactMatch"] == [1.0, 1.0, 1.0]

    assert not hasattr(r, "mean"), "a mean would hide exactly what run_count exists to show"
    assert not hasattr(r, "winner"), "naming a winner is the caller's call, not this layer's"


def test_run_count_defaults_to_one_so_this_is_additive() -> None:
    """Every existing caller keeps its behaviour, and `report_a` stays the first run."""
    from examples.greeting import Greeting, dataset, normalize_spaces, trim_only

    spec, data = Greeting(), dataset()
    r = eval_battle(spec, trim_only, normalize_spaces, data)
    assert all(len(v) == 1 for m in r.run_scores().values() for v in m.values())
    assert r.deltas()["ExactMatch"] == pytest.approx(0.50)
    assert r.report_a is not None and r.report_b is not None


def test_run_count_below_one_is_refused_rather_than_silently_doing_nothing() -> None:
    """`run_count=0` would return a result with no runs in it — a battle that measured nothing,
    reported as a battle. `checks.md`: a skipped check must never render as a value."""
    from examples.greeting import Greeting, dataset, normalize_spaces, trim_only

    with pytest.raises(SpecError):
        eval_battle(Greeting(), trim_only, normalize_spaces, dataset(), run_count=0)
