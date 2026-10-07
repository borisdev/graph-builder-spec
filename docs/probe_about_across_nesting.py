"""#9 — what `about` is, and why it stops working the moment a graph is nested."""
from graph_builder_spec import (END, START, EdgeSpec, GraphSpec, StepSpec, StrategySpec,
                                SubgraphBinding, VariableSpec)

t = VariableSpec("t", str)


# ── PART 1: what `about` IS, on a flat design with three different defects ─────────
load = StepSpec("load", inputs=(t,), outputs=(t,))
parse = StepSpec("parse", inputs=(t,), outputs=(t,))
orphan = StepSpec("orphan", inputs=(t,), outputs=(t,))      # wired to nothing


class Flat(GraphSpec):
    name = "flat"
    input_type, output_type = str, str
    nodes = (load, parse, orphan)
    edges = (EdgeSpec(source=START, target=load, carries=t),
             EdgeSpec(source=load, target=parse, carries=t),
             EdgeSpec(source=parse, target=END, carries=t))


async def passthrough(ctx) -> str:
    return ctx.inputs


partial = StrategySpec("partial", {load: passthrough})      # parse + orphan unbound

print("PART 1 — `about` on a flat design. Three attributes per finding:\n")
print(f"   {'about':<12} {'check':<22} {'blocking':<9} the sentence")
for f in Flat().coherence_check(partial):
    print(f"   {f.about!r:<12} {f.check:<22} {str(f.blocking):<9} {str(f)[:48]}...")

print("\n   A UI does nodes[f.about] to highlight the box. No regex on English.")
nodes = {n.name: n for n in Flat().nodes}
hit = [f for f in Flat().coherence_check(partial) if f.about in nodes][0]
print(f"   nodes[{hit.about!r}] -> {nodes[hit.about]!r}")


# ── PART 2: the same thing, NESTED. `about` now names the child's node. ────────────
inner_ok = StepSpec("inner_ok", inputs=(t,), outputs=(t,))
inner_orphan = StepSpec("orphan", inputs=(t,), outputs=(t,))     # same NAME as above


def child_graph(label: str) -> type:
    return type(label, (GraphSpec,), {
        "name": label, "input_type": str, "output_type": str,
        "nodes": (inner_ok, inner_orphan),
        "edges": (EdgeSpec(source=START, target=inner_ok, carries=t),
                  EdgeSpec(source=inner_ok, target=END, carries=t))})


child_s = StrategySpec("child_s", {inner_ok: passthrough, inner_orphan: passthrough})
step_a = StepSpec("step_a", inputs=(t,), outputs=(t,))
step_b = StepSpec("step_b", inputs=(t,), outputs=(t,))


class Parent(GraphSpec):
    name = "parent"
    input_type, output_type = str, str
    nodes = (step_a, step_b)
    edges = (EdgeSpec(source=START, target=step_a, carries=t),
             EdgeSpec(source=step_a, target=step_b, carries=t),
             EdgeSpec(source=step_b, target=END, carries=t))


arm = StrategySpec("arm", {
    step_a: SubgraphBinding(graph=child_graph("ChildOne")(), strategy=child_s),
    step_b: SubgraphBinding(graph=child_graph("ChildTwo")(), strategy=child_s)})

print("\n\nPART 2 — the SAME field, once a child graph is bound. ⛔ THE BUG:\n")
findings = Parent().coherence_check(arm)
parent_nodes = {n.name for n in Parent().nodes}
for f in findings:
    resolves = f.about in parent_nodes or f.about == ""
    print(f"   about={f.about!r:<10} resolves in the parent? {resolves}   {str(f)[:40]}...")

ab = [f.about for f in findings if f.about]
print(f"\n   parent's nodes: {sorted(parent_nodes)}")
print(f"   abouts handed back: {ab}")
print(f"   -> nodes[{ab[0]!r}] would KeyError: the caller holds the parent.")
print(f"   -> and the two children BOTH have a node called 'orphan', so their")
print(f"      findings are spelled IDENTICALLY: {ab.count('orphan')} of them, indistinguishable.")
print("\n   The fix #9 carries: about must become a PATH — 'step_a/orphan'.")
