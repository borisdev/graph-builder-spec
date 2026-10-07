"""`PotentialIncoherence` — 33 members, and `check` derived from exactly one table.

⛔ WHY THIS FILE EXISTS. `check` used to be STORED alongside the message, which meant two
readings of one fact and nothing stopping them disagreeing. It is now a property over `_OWNER`.
The whole value of that is the table being total and the only source — so these tests assert
BOTH directions and every check owning at least one member, rather than spot-checking a few
members the author happened to think of.
"""
from __future__ import annotations

import copy
import inspect
import pickle

import pytest

from graph_builder_spec import checks
from graph_builder_spec.checks import (
    NOT_CHECKED,
    CoherenceFinding,
    PotentialIncoherence,
    _OWNER,
)


def test_every_member_has_an_owner_and_every_owner_entry_is_a_member() -> None:
    """⛔ BOTH DIRECTIONS. A member missing from the table makes `finding.check` a KeyError at
    read time, far from the construction that caused it; an entry for a member that no longer
    exists is a stale row the completeness half cannot see."""
    assert set(PotentialIncoherence) == set(_OWNER), {
        "members with no owner": sorted(str(m) for m in set(PotentialIncoherence) - set(_OWNER)),
        "owners for no member": sorted(str(m) for m in set(_OWNER) - set(PotentialIncoherence)),
    }


def test_every_check_function_owns_at_least_one_incoherence() -> None:
    """⚠️ THE ONE THAT CATCHES A NEW CHECK. Adding `check_foo` without naming what it can find
    leaves it unable to construct a finding at all — but nothing would say so until someone hit
    the path. A check that owns nothing is either unfinished or dead."""
    declared = {n for n in checks.__all__ if n.startswith("check_")}
    owning = set(_OWNER.values())
    assert declared == owning, {
        "checks that own no incoherence": sorted(declared - owning),
        "owners that are not declared checks": sorted(owning - declared),
    }


def test_check_is_derived_and_agrees_with_the_table_for_every_member() -> None:
    """Not one sample — all 33."""
    for member in PotentialIncoherence:
        f = CoherenceFinding("a message", potential_incoherence=member)
        assert f.check == _OWNER[member], member


def test_check_cannot_be_set_to_disagree_with_the_table() -> None:
    """The property has no setter, which is the point: `blocking` was a writable attribute
    documented as derived, and `finding.blocking = False` made it disagree with `blocking()` on
    the same message. Deriving on read means they cannot differ."""
    f = CoherenceFinding("x", potential_incoherence=PotentialIncoherence.NODE_NOT_BOUND)
    with pytest.raises(AttributeError):
        f.check = "check_names"                      # type: ignore[misc]


def test_it_is_a_str_enum_so_existing_comparisons_keep_working() -> None:
    """The reason it is a `StrEnum` and not an `Enum`: a consumer comparing to a plain string,
    JSON-encoding it, or sorting it behaves as before. Same argument as `CoherenceFinding`
    being a `str` subclass."""
    m = PotentialIncoherence.UNREACHABLE_FROM_START
    assert m == "unreachable_from_start"
    assert f"{m}" == "unreachable_from_start"
    # sorts by VALUE like a string would — "no_path_to_end" < "unreachable_from_start"
    assert sorted([m, PotentialIncoherence.NO_PATH_TO_END]) == [PotentialIncoherence.NO_PATH_TO_END, m]


def test_the_member_names_describe_the_DEFECT_not_the_checker() -> None:
    """⛔ THE WHOLE REASON THIS IS NOT 13 MEMBERS. `check_reachable` reports five different things
    to fix, so a field called `potential_incoherence` holding `"check_reachable"` would name a
    function rather than an incoherence — a value that does not deliver what the field promises.
    """
    assert not any(str(m).startswith("check_") for m in PotentialIncoherence), (
        "a member is named after a check function, not after what is wrong")
    reachable = [m for m, c in _OWNER.items() if c == "check_reachable"]
    assert len(reachable) == 5, sorted(str(m) for m in reachable)


@pytest.mark.parametrize("member", list(PotentialIncoherence))
def test_a_finding_survives_pickle_and_copy_for_every_member(member) -> None:
    """`__reduce__` carries `potential_incoherence` now. Parametrised over all 33 because the
    previous reducer broke on a field it did not carry and the oracle did not cover it."""
    f = CoherenceFinding("the message", potential_incoherence=member, about="n")
    for rebuilt in (pickle.loads(pickle.dumps(f)), copy.copy(f), copy.deepcopy(f)):
        assert str(rebuilt) == "the message"
        assert rebuilt.potential_incoherence is member
        assert rebuilt.check == _OWNER[member]
        assert rebuilt.about == "n"


def test_the_not_checked_members_are_the_non_blocking_ones() -> None:
    """⚠️ The enum deliberately mixes two kinds of thing — defects and stated gaps — because
    every finding needs a value. `blocking` is what tells them apart, and it is derived from the
    MESSAGE, not from the member. So this asserts the naming convention holds rather than that
    the two are wired together: a `*_NOT_CHECKED` member whose message lacks the prefix would be
    a finding that claims a gap and blocks like a defect.
    """
    gap_members = [m for m in PotentialIncoherence if str(m).endswith("_not_checked")]
    assert len(gap_members) >= 3, sorted(str(m) for m in gap_members)
    for m in gap_members:
        stated = CoherenceFinding(f"{NOT_CHECKED} — we did not look", potential_incoherence=m)
        assert not stated.blocking, m


def test_every_finding_the_checks_construct_names_a_real_member() -> None:
    """⚠️ Reads the SOURCE, because a construction site is only exercised by the design that
    trips it and no test corpus hits all 31. A typo'd member is an AttributeError at the moment
    something finally goes wrong, which is the worst time to find it."""
    src = inspect.getsource(checks)
    names = {str(m).upper() for m in PotentialIncoherence}
    used = {ln.split("PotentialIncoherence.")[1].split(")")[0].split(",")[0].strip()
            for ln in src.splitlines() if "PotentialIncoherence." in ln and "_OWNER" not in ln}
    used = {u for u in used if u.isupper()}
    assert used, "found no PotentialIncoherence.X references — this would pass vacuously"
    unknown = {u for u in used if u.replace("_", "").upper() not in
               {n.replace("_", "") for n in names}}
    assert not unknown, f"construction sites reference members that do not exist: {sorted(unknown)}"
