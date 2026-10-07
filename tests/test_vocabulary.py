"""The vocabulary, asserted — so `node` cannot quietly mean `step` again.

⛔ `NodeSpec` named the general concept and meant one specific kind for the whole of 0.1.x, which
forced a second word (`Endpoint`) for a set that already had one. Pydantic Graph puts START and END
inside `graph.nodes` and calls `step` / `join` / `decision` the KINDS; `payload.Node` already
agreed via `kind: str = "step"`. Only the declaration layer did not.

These are cheap, and they are the only thing that would notice the drift coming back.
"""
from __future__ import annotations

import inspect
from pathlib import Path

import pytest

import graph_builder_spec as ww
from graph_builder_spec import Bindable, DecisionSpec, JoinSpec, NodeSpec, StepSpec


def test_stepspec_is_the_class_you_instantiate() -> None:
    assert inspect.isclass(StepSpec)
    assert StepSpec("normalize").name == "normalize"


def test_nodespec_is_the_union_of_every_declared_box() -> None:
    """⚠️ A REAL runtime union, not a string. `Endpoint` was a `str` shaped like an alias, so it
    could never be used in an annotation or an isinstance — which is why nothing ever used it."""
    assert not inspect.isclass(NodeSpec)
    assert isinstance(StepSpec("s"), NodeSpec)
    assert isinstance(JoinSpec("j", lambda a, b: a, initial=0), NodeSpec)
    assert isinstance(DecisionSpec("d"), NodeSpec)


def test_bindable_is_narrower_than_nodespec_and_that_is_the_point() -> None:
    """A join and a decision are declared boxes with NO implementation, so a strategy binds
    neither. Conflating the two axes is how a join ends up demanding an implementation."""
    assert isinstance(StepSpec("s"), Bindable)
    assert not isinstance(DecisionSpec("d"), Bindable)
    assert not isinstance(JoinSpec("j", lambda a, b: a, initial=0), Bindable)


def test_the_old_constructor_fails_loudly() -> None:
    """A silent narrowing would be worse than a stop. `docs/migration-0.2.md` quotes this error."""
    with pytest.raises(TypeError):
        NodeSpec("normalize")          # type: ignore[operator]


def test_endpoint_is_gone_and_stays_gone() -> None:
    """It was a `str` in `__all__` with zero references. Deleted, not renamed."""
    assert not hasattr(ww, "Endpoint")
    src = Path(inspect.getfile(StepSpec)).read_text()
    assert src, "spec.py read as empty — the assertion below would pass vacuously"
    assert "Endpoint" not in src


def test_both_unions_are_exported() -> None:
    """An alias nobody can import is a comment. `Endpoint` was in `__all__` and unusable."""
    for name in ("StepSpec", "NodeSpec", "Bindable"):
        assert name in ww.__all__, name
        assert getattr(ww, name, None) is not None, name
