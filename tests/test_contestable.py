"""The flagship example, and the honesty property that makes it worth shipping.

⛔ `contestable.py` exists to demonstrate that a design is INSPECTABLE BEFORE IT IS IMPLEMENTED.
If it ever grows real implementations, or starts printing a score, it stops making that point and
becomes a second greeting example.
"""
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

from examples.contestable import Assessment, by_agreement, by_recency, weigh
from graph_builder_spec import blocking

ROOT = Path(__file__).resolve().parent.parent


def test_the_design_is_coherent_with_nothing_implemented() -> None:
    """The whole pitch in one assertion: a design with zero implementations still checks."""
    assert Assessment().coherence_check() == []


def test_stubs_are_structurally_complete_and_block_nothing() -> None:
    spec = Assessment()
    assert blocking(spec.coherence_check(by_recency)) == []
    assert blocking(spec.coherence_check(by_agreement)) == []


def test_the_diff_isolates_exactly_the_one_contested_stage() -> None:
    """⛔ THE ATTRIBUTION CLAIM, asserted rather than asserted-about. The README says the
    difference is attributable to a NAMED STAGE; this is what that means."""
    spec = Assessment()
    assert set(spec.varies(by_recency, by_agreement)) == {"weigh"}
    # ⚠️ Asserted PER NODE, not as a substring over the whole diagram — a substring test passes
    # while the highlight sits on the wrong box, which is the only thing this test is for.
    diff = spec.diff_diagram(by_recency, by_agreement)
    assert varies_in(diff, "weigh"), diff
    for shared in ("gather", "screen", "compose"):
        assert shared_in(diff, shared), diff
        assert not varies_in(diff, shared), f"{shared} is highlighted and should not be"


def test_every_contested_stage_states_its_problem() -> None:
    """A stage declared as a judgement call with no brief is the thing `problem` exists for.
    This example is the one place that must model it."""
    for node in Assessment.nodes:
        assert node.problem, f"{node.name} declares no `problem` — it is the implementer's brief"
        assert len(node.problem) > 60, f"{node.name}'s problem is too short to be a brief"
        assert node.name not in node.problem.split(".")[0].lower(), (
            f"{node.name}'s problem restates its name instead of naming the difficulty")


def test_the_example_never_prints_a_score() -> None:
    """⛔ THE HONESTY PROPERTY, and the reason this test is worth more than the others.

    Implementations are stubs, so any number resembling a score would be fabricated. The example
    says so in prose; this makes it true in fact, and goes red the day someone 'helpfully' wires
    a battle to stubs.
    """
    out = subprocess.run([sys.executable, "-m", "examples.contestable"],
                         cwd=ROOT, capture_output=True, text=True, timeout=120)
    assert out.returncode == 0, out.stderr
    assert "DELIBERATELY ABSENT" in out.stdout
    # ⛔ ANY decimal, not just `0.x`. The old class missed a perfect 1.0 — the most
    # flattering number a fabricated score can be, and the one most likely to get printed.
    scores = re.findall(r"\b\d+\.\d+\b|\bscore[d]?\s*[:=]\s*[\d.]+", out.stdout, re.I)
    assert not scores, f"the stub example printed something score-shaped: {scores}"


def test_the_stub_names_say_stub_in_the_picture() -> None:
    """`diagram(strategy)` prints the bound function's name, so the drawing itself must admit
    nothing is implemented rather than implying an algorithm is behind each box."""
    drawn = Assessment().diagram(by_recency)
    assert drawn.count("_stub") >= 4, "the diagram does not show these as stubs"
    assert weigh.problem, "the contested stage must carry its brief"


# ⚠️ A varying node is now a SUBGRAPH with one box per arm, not a box with a `:::varies` class
# on it. `subgraph x["t"]:::cls` is a parse error in mermaid 11 (verified with mermaid-cli), so
# the class channel every other node uses is unavailable here and the highlight is a `style`
# line. These two helpers keep the tests asserting the FACT — this node reads as varying — so
# they survive the next rendering change without being rewritten again.

def varies_in(diagram: str, node: str) -> bool:
    """`node` is drawn as a highlighted subgraph containing its arms."""
    return (f'subgraph {node}[' in diagram
            and f"style {node} fill:#fde68a" in diagram)


def shared_in(diagram: str, node: str) -> bool:
    """`node` is drawn as one plain box."""
    return any(ln.strip().startswith(f"{node}[") and ln.strip().endswith(":::shared")
               for ln in diagram.splitlines())
