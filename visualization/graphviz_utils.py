"""Builds Graphviz DOT source strings for derivation/AST trees and LR
automata. Rendered client-side by ``st.graphviz_chart`` — no local
Graphviz binary required.
"""
from __future__ import annotations

from parsers.lr_items import format_state


def _escape(text: str) -> str:
    return text.replace("\\", "\\\\").replace('"', '\\"')


def tree_to_dot(tree: dict, graph_name: str = "Arbol") -> str:
    lines = [
        f"digraph {graph_name} {{",
        'node [shape=box, style="rounded,filled", fillcolor="#EEF2FF", '
        'color="#6366F1", fontname="Helvetica", fontsize=12];',
        'edge [color="#94A3B8"];',
    ]
    counter = {"n": 0}

    def add(node) -> str:
        nid = f"n{counter['n']}"
        counter["n"] += 1
        label = _escape(str(node.get("label", "?")))
        children = node.get("children") or []
        shape_extra = "" if children else 'fillcolor="#DCFCE7", color="#16A34A"'
        lines.append(f'{nid} [label="{label}"{"," + shape_extra if shape_extra else ""}];')
        for child in children:
            cid = add(child)
            lines.append(f"{nid} -> {cid};")
        return nid

    add(tree)
    lines.append("}")
    return "\n".join(lines)


def automaton_to_dot(states, transitions, grammar, graph_name: str = "Automata", highlight=None) -> str:
    lines = [
        f"digraph {graph_name} {{",
        "rankdir=LR;",
        'node [shape=box, fontname="Consolas", fontsize=10, style=filled, fillcolor="#F8FAFC", color="#334155"];',
        'edge [fontname="Helvetica", fontsize=10, color="#6366F1"];',
    ]
    for i, state in enumerate(states):
        body = _escape(format_state(state, grammar)).replace("\\n", "\\l")
        fill = "#FDE68A" if highlight == i else "#F8FAFC"
        lines.append(f'I{i} [label="I{i}\\l{body}\\l", fillcolor="{fill}"];')
    for (i, sym), j in sorted(transitions.items(), key=lambda kv: (kv[0][0], str(kv[0][1]))):
        lines.append(f'I{i} -> I{j} [label="{_escape(sym)}"];')
    lines.append("}")
    return "\n".join(lines)
