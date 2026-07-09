"""Generic LR item / closure / goto / canonical-collection engine.

LR(0) items are ``(prod_index, dot)``.
LR(1) items are ``(prod_index, dot, lookahead)``.

LR(0), SLR(1) reuse the LR(0) automaton. LR(1) builds its own canonical
collection; LALR(1) builds the LR(1) collection and merges states that
share the same *core* (set of (prod, dot) pairs, ignoring lookaheads) —
the standard, simplest-to-explain construction for a teaching tool.
"""
from __future__ import annotations

from .grammar import EPSILON, END, DOT, ARROW


def eff_body(prod):
    """Body of a production with epsilon normalized to an empty tuple."""
    return () if prod.is_epsilon else prod.body


# ---------------------------------------------------------------------
# LR(0)
# ---------------------------------------------------------------------
def lr0_closure(items, grammar):
    items = set(items)
    changed = True
    while changed:
        changed = False
        for (p_idx, dot) in list(items):
            body = eff_body(grammar.productions[p_idx])
            if dot < len(body):
                sym = body[dot]
                if sym in grammar.nonterminals:
                    for q in grammar.productions_for(sym):
                        new_item = (q.index, 0)
                        if new_item not in items:
                            items.add(new_item)
                            changed = True
    return frozenset(items)


def lr0_goto(items, symbol, grammar):
    moved = set()
    for (p_idx, dot) in items:
        body = eff_body(grammar.productions[p_idx])
        if dot < len(body) and body[dot] == symbol:
            moved.add((p_idx, dot + 1))
    return lr0_closure(moved, grammar) if moved else frozenset()


def build_lr0_states(grammar):
    """``grammar`` must already be augmented (start production index 0)."""
    start_state = lr0_closure({(0, 0)}, grammar)
    states = [start_state]
    transitions = {}
    symbols = sorted(grammar.terminals | grammar.nonterminals)
    changed = True
    while changed:
        changed = False
        for i in range(len(states)):
            for sym in symbols:
                tgt = lr0_goto(states[i], sym, grammar)
                if not tgt:
                    continue
                if tgt not in states:
                    states.append(tgt)
                    changed = True
                j = states.index(tgt)
                transitions[(i, sym)] = j
    return states, transitions


# ---------------------------------------------------------------------
# LR(1)
# ---------------------------------------------------------------------
def _first_with_end(grammar, first):
    if END not in first:
        first = dict(first)
        first[END] = {END}
    return first


def lr1_closure(items, grammar, first):
    first = _first_with_end(grammar, first)
    nullable = grammar.compute_nullable()
    items = set(items)
    changed = True
    while changed:
        changed = False
        for (p_idx, dot, la) in list(items):
            body = eff_body(grammar.productions[p_idx])
            if dot < len(body):
                sym = body[dot]
                if sym in grammar.nonterminals:
                    beta = body[dot + 1 :]
                    seq = tuple(beta) + (la,)
                    lookaheads = grammar._first_of_sequence(seq, first, nullable)
                    for q in grammar.productions_for(sym):
                        for b in lookaheads:
                            if b == EPSILON:
                                continue
                            new_item = (q.index, 0, b)
                            if new_item not in items:
                                items.add(new_item)
                                changed = True
    return frozenset(items)


def lr1_goto(items, symbol, grammar, first):
    moved = set()
    for (p_idx, dot, la) in items:
        body = eff_body(grammar.productions[p_idx])
        if dot < len(body) and body[dot] == symbol:
            moved.add((p_idx, dot + 1, la))
    return lr1_closure(moved, grammar, first) if moved else frozenset()


def build_lr1_states(grammar, first):
    start_state = lr1_closure({(0, 0, END)}, grammar, first)
    states = [start_state]
    transitions = {}
    symbols = sorted(grammar.terminals | grammar.nonterminals)
    changed = True
    while changed:
        changed = False
        for i in range(len(states)):
            for sym in symbols:
                tgt = lr1_goto(states[i], sym, grammar, first)
                if not tgt:
                    continue
                if tgt not in states:
                    states.append(tgt)
                    changed = True
                j = states.index(tgt)
                transitions[(i, sym)] = j
    return states, transitions


def build_lalr1_states(grammar, first):
    """Merge LR(1) states that share the same core."""
    lr1_states, lr1_trans = build_lr1_states(grammar, first)

    core_to_indices = {}
    for i, st in enumerate(lr1_states):
        core = frozenset((p, d) for (p, d, _la) in st)
        core_to_indices.setdefault(core, []).append(i)

    cores = list(core_to_indices.keys())
    old_to_new = {}
    for new_idx, core in enumerate(cores):
        for old_idx in core_to_indices[core]:
            old_to_new[old_idx] = new_idx

    merged_states = []
    for core in cores:
        merged = set()
        for old_idx in core_to_indices[core]:
            merged |= lr1_states[old_idx]
        merged_states.append(frozenset(merged))

    merged_trans = {}
    for (i, sym), j in lr1_trans.items():
        merged_trans[(old_to_new[i], sym)] = old_to_new[j]

    return merged_states, merged_trans


# ---------------------------------------------------------------------
# Display helpers
# ---------------------------------------------------------------------
def format_item(item, grammar):
    if len(item) == 2:
        p_idx, dot = item
        la = None
    else:
        p_idx, dot, la = item
    prod = grammar.productions[p_idx]
    body = eff_body(prod)
    parts = list(body)
    parts.insert(dot, DOT)
    rhs = " ".join(parts) if parts else DOT
    s = f"{prod.head} {ARROW} {rhs}"
    if la is not None:
        s += f" , {la}"
    return s


def format_state(state, grammar):
    return "\n".join(sorted(format_item(it, grammar) for it in state))
