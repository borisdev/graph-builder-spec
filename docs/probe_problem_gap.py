"""#10 — a parent's requirement disappears into a child graph, and every check passes."""
from dataclasses import dataclass, field

from graph_builder_spec import (END, START, EdgeSpec, GraphSpec, StepSpec, StrategySpec,
                                SubgraphBinding, VariableSpec)


@dataclass
class Paper:
    text: str


@dataclass
class Claim:
    text: str
    quote: str = ""          # ⬅ the PARENT requires this to be filled


@dataclass
class Claims:
    items: list = field(default_factory=list)


paper = VariableSpec("paper", Paper)
claims = VariableSpec("claims", Claims)

# ── THE PARENT: its role spells out the requirement ────────────────────────────────
extract = StepSpec("extract", inputs=(paper,), outputs=(claims,),
                   problem="Extract claims WITH a supporting quotation for each.")


class Pipeline(GraphSpec):
    name = "pipeline"
    input_type, output_type = Paper, Claims
    nodes = (extract,)
    edges = (EdgeSpec(source=START, target=extract, carries=paper),
             EdgeSpec(source=extract, target=END, carries=claims))


# ── THE CHILD: written elsewhere. Its job is "extract factual claims". No quotes. ──
find = StepSpec("find_sentences", inputs=(paper,), outputs=(claims,))


class ExtractFactualClaims(GraphSpec):
    name = "extract_factual_claims"
    input_type, output_type = Paper, Claims
    nodes = (find,)
    edges = (EdgeSpec(source=START, target=find, carries=paper),
             EdgeSpec(source=find, target=END, carries=claims))


async def sentences(ctx) -> Claims:
    return Claims(items=[Claim(text=s.strip()) for s in ctx.inputs.text.split(".") if s.strip()])


child = StrategySpec("child", {find: sentences})
arm = StrategySpec("arm", {extract: SubgraphBinding(graph=ExtractFactualClaims(), strategy=child)})

print("1. the parent's requirement, written down:")
print(f"   extract.problem = {extract.problem!r}")
print()
print("2. can the CHILD state its own purpose, so the two could be compared?")
print(f"   hasattr(GraphSpec, 'problem') = {hasattr(GraphSpec, 'problem')}   <-- THE GAP")
print()
print("3. coherence_check with the child bound to that role:")
print(f"   {Pipeline().coherence_check(arm)}        <-- CLEAN. Paper->Claims lines up.")
print()
print("4. what it actually produces:")
out = Pipeline().render(arm).run_sync(
    inputs=Paper(text="Metformin lowers A1c. Fasting insulin was never measured."))
for c in out.items:
    print(f"   text={c.text!r:52} quote={c.quote!r}")
print()
print("   Every quote is empty. The requirement was in extract.problem, a string")
print("   nothing compares to anything, and types cannot carry 'with a quotation'.")
