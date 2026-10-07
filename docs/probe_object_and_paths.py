"""#1 item 3 (`object` silently disables a check) and #2 (map-then-transform)."""
from graph_builder_spec import (END, START, EdgeSpec, GraphSpec, MapEdgeSpec, StepSpec,
                                StrategySpec, TransformEdgeSpec, VariableSpec)

print("=" * 72)
print("#1 item 3 — THE SAME MISTAKE, caught once and silent once")
print("=" * 72)


def design(var: VariableSpec, impl) -> tuple:
    gate = StepSpec("gate", inputs=(var,), outputs=(var,))
    cls = type("G", (GraphSpec,), {
        "name": "g", "input_type": var.type, "output_type": var.type, "nodes": (gate,),
        "edges": (EdgeSpec(source=START, target=gate, carries=var),
                  EdgeSpec(source=gate, target=END, carries=var))})
    return cls(), StrategySpec("s", {gate: impl})


async def returns_a_string(ctx) -> str:          # ⬅ the implementation is a str
    return "not what was declared"


# A: the variable is declared `int`. The impl returns `str`.
spec, arm = design(VariableSpec("verdict", int), returns_a_string)
print("\nA. VariableSpec('verdict', int)   + an impl annotated -> str")
for f in spec.coherence_check(arm):
    print(f"   CAUGHT: {str(f)[:96]}...")

# B: the variable is declared `object`. The impl returns `str`. SAME mistake.
spec, arm = design(VariableSpec("verdict", object), returns_a_string)
print("\nB. VariableSpec('verdict', object) + the SAME impl")
print(f"   {spec.coherence_check(arm) or 'CLEAN — and NOTHING says the check was skipped'}")
print("\n   `object` accepts anything, so the check cannot decide — correct. But it")
print("   reports nothing, so NOT CHECKED and 0 FOUND render identically.")
print("   The fix is one NOT CHECKED line, not a new rule.")
print("\n   And it is not hypothetical — this is in a shipped example:")
import examples.ladder.stage9_decision as s9
print(f"   examples/ladder/stage9_decision.py: "
      f"{[f'{v.name}: object' for v in (s9.verdict,) if v.type is object]}")

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
