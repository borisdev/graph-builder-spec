"""#1 item 3 — `object` is now REFUSED — and #2, map-then-transform on one wire."""
from dataclasses import dataclass

from graph_builder_spec import (END, START, EdgeSpec, GraphSpec, MapEdgeSpec, SpecError,
                                StepSpec, StrategySpec, VariableSpec)

print("=" * 72)
print("#1 item 3 — `object` USED to switch the check off silently. Now it is refused.")
print("=" * 72)


@dataclass
class Urgent:
    text: str


@dataclass
class Routine:
    text: str


def design(var: VariableSpec, impl) -> tuple:
    gate = StepSpec("gate", inputs=(var,), outputs=(var,))
    cls = type("G", (GraphSpec,), {
        "name": "g", "input_type": var.type, "output_type": var.type, "nodes": (gate,),
        "edges": (EdgeSpec(source=START, target=gate, carries=var),
                  EdgeSpec(source=gate, target=END, carries=var))})
    return cls(), StrategySpec("s", {gate: impl})


async def returns_a_string(ctx) -> str:
    return "not what was declared"


async def triages(ctx) -> Urgent | Routine:
    return Urgent(ctx.inputs) if "chest" in ctx.inputs else Routine(ctx.inputs)


print("\nA. the mistake, when the type is concrete — always caught:")
spec, arm = design(VariableSpec("verdict", int), returns_a_string)
for f in spec.coherence_check(arm):
    print(f"   CAUGHT: {str(f)[:92]}...")

print("\nB. `object`, which used to make the SAME mistake report CLEAN:")
try:
    VariableSpec("verdict", object)
    print("   ...accepted?!")
except SpecError as e:
    print(f"   REFUSED at declaration: {str(e)[:88]}...")

print("\nC. the replacement — declare what actually flows, as a union:")
spec, arm = design(VariableSpec("verdict", Urgent | Routine), triages)
print(f"   right impl  -> {spec.coherence_check(arm) or 'CLEAN'}")
spec, bad = design(VariableSpec("verdict", Urgent | Routine), returns_a_string)
for f in spec.coherence_check(bad):
    print(f"   wrong impl  -> {str(f)[:88]}...")

print("\n   ⛔ C IS WHY THE BAN ALONE WOULD NOT HAVE BEEN ENOUGH. `_produces` handled a union")
print("   ANNOTATION and not a union DECLARATION, so `-> str` against `Urgent | Routine` came")
print("   back NOT CHECKED. Banning `object` without that would have moved the silence, not")
print("   removed it. Both halves shipped together.")

print("\nD. and the examples that used `object` now declare the truth:")
import examples.ladder.stage9_decision as s9
import examples.ladder.stage10_no_basenode as s10
print(f"   stage9  verdict: {s9.verdict.type}")
print(f"   stage10 verdict: {s10.verdict.type}")
print(f"   stage10 checked: {s10.checked.type}")
print(f"   stage10 output_type: {s10.Intake.output_type}")
print(f"   both still check clean: {s9.Triage().coherence_check() == [] and s10.Intake().coherence_check() == []}")

print()
print("=" * 72)
print("#2 — fan out AND reshape on one wire. Not expressible.")
print("=" * 72)

papers = VariableSpec("papers", list)
paper = VariableSpec("paper", str)
pmid = VariableSpec("pmid", str)
score = VariableSpec("score", float)

print("\nWhat you want: carries a list, delivers ONE pmid per item.")
print("  MapEdgeSpec  fans out      list -> paper")
print("  then reshape               paper -> pmid     before it lands\n")

rate = StepSpec("rate", inputs=(pmid,), outputs=(score,))
try:
    MapEdgeSpec(source=START, target=rate, carries=papers, delivers=paper,
                apply=lambda ctx: ctx.inputs.split(":")[0])
    print("  MapEdgeSpec(..., apply=...) -> accepted?!")
except TypeError as e:
    print(f"  MapEdgeSpec(..., apply=...) -> TypeError: {e}")

print("\n  No single edge is both. The workaround is a step that exists only to unwrap:")
unwrap = StepSpec("unwrap", inputs=(paper,), outputs=(pmid,))
print(f"    {unwrap!r}")
print("    MapEdgeSpec(source=START, target=unwrap, carries=papers, delivers=paper)")
print("    EdgeSpec(source=unwrap, target=rate, carries=pmid)")
print("  ...which puts a BOX on the diagram for something that is not a stage.")

print("\n⚠️ But the two are genuinely different KINDS of thing at build time:")
print("   a map is rewritten into a real Fork NODE before the executor runs;")
print("   a transform survives on the wire and is walked per completion.")
print("   pydantic's own _flatten_paths asserts exactly that:")
print("     assert not isinstance(item, MapMarker | BroadcastMarker),")
print("            'These should be removed during Graph building'")
print("\n   So our separate types say out loud what a uniform list would hide.")
print("   TRIGGER to build it: the first real design that needs it. None does yet.")
