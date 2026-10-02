"""`StepSpec.problem` — the implementer's brief, and what its absence must not mean."""
from __future__ import annotations

from workflow_workbench import EdgeSpec, END, START, GraphSpec, StepSpec, VariableSpec
from workflow_workbench.devserver import spec_payload
from workflow_workbench.payload import WorkflowReport


def test_problem_defaults_to_empty_and_is_additive() -> None:
    """Every existing declaration keeps working — the field is new and optional."""
    assert StepSpec("x").problem == ""


def test_problem_reaches_the_browser_payload() -> None:
    """⚠️ A field nothing consumes is decoration. This is its consumer: the tool you open to
    READ a design is where the brief has to appear."""
    v = VariableSpec("v", str)
    hard = StepSpec("hard", inputs=(v,), outputs=(v,),
                    problem="Two reasonable implementations disagree completely.")

    class D(GraphSpec):
        name = "d"
        input_type, output_type = str, str
        nodes = (hard,)
        edges = (EdgeSpec(source=START, target=hard, carries=v),
                 EdgeSpec(source=hard, target=END, carries=v))

    payload = WorkflowReport.model_validate(spec_payload(D(), []))
    node = next(n for n in payload.nodes if n.id == "hard")
    assert node.problem == "Two reasonable implementations disagree completely."


def test_an_absent_brief_is_distinguishable_from_a_written_one() -> None:
    """⛔ `""` means NOBODY WROTE ONE. It must never be readable as "this stage is easy" — an
    unwritten brief and a stage with no judgement in it are different facts, and conflating them
    is `checks.md`'s NOT CHECKED versus 0 FOUND in another costume."""
    assert StepSpec("a").problem == ""
    assert StepSpec("b", problem="x").problem == "x"
    assert StepSpec("a").problem != "none", "absence must not be spelled as a claim"
