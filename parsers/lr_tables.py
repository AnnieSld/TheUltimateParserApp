"""Arma las tablas ACTION/GOTO para toda la familia LR (LR0, SLR1, LALR1,
LR1) a partir de los automatas de lr_items.py, y simula el parsing
shift-reduce paso a paso sobre esas tablas. Los cuatro metodos comparten
practicamente toda la logica: la unica diferencia real esta en QUE
lookahead se usa para decidir si conviene reducir (ver build_*_table).
"""
from __future__ import annotations

from dataclasses import dataclass, field

from .grammar import Grammar, EPSILON, END
from .lr_items import (
    eff_body,
    build_lr0_states,
    build_lr1_states,
    build_lalr1_states,
    format_state,
)

SHIFT = "shift"
REDUCE = "reduce"
ACCEPT = "accept"


@dataclass
class Conflict:
    state: int
    symbol: str
    kind: str  # "shift-reduce" | "reduce-reduce"
    actions: list


@dataclass
class ParsingTable:
    method: str
    aug_grammar: Grammar
    states: list
    transitions: dict
    action: dict = field(default_factory=dict)
    goto: dict = field(default_factory=dict)
    conflicts: list = field(default_factory=list)

    def action_str(self, state, symbol):
        act = self.action.get((state, symbol))
        if act is None:
            return ""
        if act[0] == SHIFT:
            return f"d{act[1]}"  # desplazar (shift) al estado act[1]
        if act[0] == REDUCE:
            return f"r{act[1]}"  # reducir con la producción act[1]
        if act[0] == ACCEPT:
            return "acc"
        return ""


def _record_action(table: ParsingTable, state, symbol, new_action):
    key = (state, symbol)
    existing = table.action.get(key)
    if existing is not None and existing != new_action:
        kind = "reduce-reduce" if existing[0] == REDUCE and new_action[0] == REDUCE else "shift-reduce"
        table.conflicts.append(
            Conflict(state=state, symbol=symbol, kind=kind, actions=[existing, new_action])
        )
        # Cuando hay conflicto se deja registrado (para mostrarlo en la UI y
        # explicarlo), pero igual hay que dejar la tabla usable para poder
        # simular algo: la convencion mas comun es preferir shift, que es lo
        # que resuelve el clasico dangling-else "bien" por default.
        if new_action[0] == SHIFT or existing[0] == ACCEPT:
            table.action[key] = new_action
        return
    table.action[key] = new_action


def _fill_shifts_and_gotos(table: ParsingTable):
    for (i, sym), j in table.transitions.items():
        if sym in table.aug_grammar.terminals:
            _record_action(table, i, sym, (SHIFT, j))
        elif sym in table.aug_grammar.nonterminals:
            table.goto[(i, sym)] = j


def build_lr0_table(orig_grammar: Grammar) -> ParsingTable:
    # LR(0) es el mas simple y el mas conflictivo: no mira nada de la
    # entrada para decidir si reducir, asi que si un estado tiene un item
    # completo, reduce para CUALQUIER simbolo (all_lookaheads de aca abajo).
    # Es justo esto lo que hace que gramaticas normales, como la de
    # expresiones con + y *, ya tengan conflictos en LR(0) puro.
    aug = orig_grammar.augmented()
    states, transitions = build_lr0_states(aug)
    table = ParsingTable("LR(0)", aug, states, transitions)
    _fill_shifts_and_gotos(table)

    all_lookaheads = orig_grammar.terminals | {END}
    for i, state in enumerate(states):
        for (p_idx, dot) in state:
            body = eff_body(aug.productions[p_idx])
            if dot != len(body):
                continue
            prod = aug.productions[p_idx]
            if p_idx == 0:
                _record_action(table, i, END, (ACCEPT,))
            else:
                for t in all_lookaheads:
                    _record_action(table, i, t, (REDUCE, p_idx))
    return table


def build_slr1_table(orig_grammar: Grammar) -> ParsingTable:
    # Mismo automata que LR(0) (build_lr0_states), la unica diferencia esta
    # en que ahora solo se reduce cuando el simbolo que viene esta en
    # FOLLOW(cabeza) en vez de para cualquier simbolo -- ese solo cambio
    # elimina bastantes conflictos sin tener que rehacer el automata.
    aug = orig_grammar.augmented()
    states, transitions = build_lr0_states(aug)
    table = ParsingTable("SLR(1)", aug, states, transitions)
    _fill_shifts_and_gotos(table)

    first = aug.compute_first()
    follow = aug.compute_follow(first)

    for i, state in enumerate(states):
        for (p_idx, dot) in state:
            body = eff_body(aug.productions[p_idx])
            if dot != len(body):
                continue
            if p_idx == 0:
                _record_action(table, i, END, (ACCEPT,))
            else:
                head = aug.productions[p_idx].head
                for t in follow[head]:
                    _record_action(table, i, t, (REDUCE, p_idx))
    return table


def _lr1_style_table(method_name, orig_grammar: Grammar, states, transitions) -> ParsingTable:
    aug = orig_grammar.augmented()
    table = ParsingTable(method_name, aug, states, transitions)
    _fill_shifts_and_gotos(table)

    for i, state in enumerate(states):
        for (p_idx, dot, la) in state:
            body = eff_body(aug.productions[p_idx])
            if dot != len(body):
                continue
            if p_idx == 0:
                _record_action(table, i, END, (ACCEPT,))
            else:
                _record_action(table, i, la, (REDUCE, p_idx))
    return table


def build_lr1_table(orig_grammar: Grammar) -> ParsingTable:
    aug = orig_grammar.augmented()
    first = aug.compute_first()
    states, transitions = build_lr1_states(aug, first)
    return _lr1_style_table("LR(1)", orig_grammar, states, transitions)


def build_lalr1_table(orig_grammar: Grammar) -> ParsingTable:
    aug = orig_grammar.augmented()
    first = aug.compute_first()
    states, transitions = build_lalr1_states(aug, first)
    return _lr1_style_table("LALR(1)", orig_grammar, states, transitions)


BUILDERS = {
    "LR(0)": build_lr0_table,
    "SLR(1)": build_slr1_table,
    "LALR(1)": build_lalr1_table,
    "LR(1)": build_lr1_table,
}


# ---------------------------------------------------------------------
# Simulation
# ---------------------------------------------------------------------
@dataclass
class ParseStep:
    step: int
    stack: str
    input_remaining: str
    action: str


@dataclass
class ParseResult:
    accepted: bool
    steps: list
    error: str = ""
    derivation_prod_indices: list = field(default_factory=list)
    tree: dict | None = None


def lr_parse(table: ParsingTable, tokens: list) -> ParseResult:
    # Parsing shift-reduce de manual: una pila de estados (stack) mas una
    # pila paralela de simbolos/nodos, y en cada paso se mira la tabla
    # ACTION segun (estado tope, simbolo actual). node_stack no hace falta
    # para aceptar o rechazar la cadena, esta solo para poder armar el
    # arbol de derivacion al final (cada reduccion junta los hijos que
    # acaba de sacar de la pila en un nodo nuevo).
    aug = table.aug_grammar
    stack = [0]
    symbol_stack = []
    node_stack = []
    input_tokens = list(tokens) + [END]
    pos = 0
    steps = []
    prod_sequence = []

    step_no = 0
    while True:
        state = stack[-1]
        look = input_tokens[pos]
        act = table.action.get((state, look))
        stack_repr = str(stack[0]) if not symbol_stack else f"{stack[0]} " + " ".join(
            f"{sym} {stack[idx+1]}" for idx, sym in enumerate(symbol_stack)
        )
        remaining = " ".join(input_tokens[pos:])
        step_no += 1

        if act is None:
            expected = sorted({sym for (s, sym) in table.action if s == state})
            msg = (
                f"Error sintáctico: en el estado {state} no hay acción para "
                f"el símbolo '{look}'. Se esperaba uno de: {', '.join(expected) if expected else '(nada, tabla vacía)'}."
            )
            steps.append(ParseStep(step_no, stack_repr, remaining, f"ERROR: {msg}"))
            return ParseResult(False, steps, msg, prod_sequence, None)

        if act[0] == SHIFT:
            steps.append(ParseStep(step_no, stack_repr, remaining, f"desplazar (shift) -> estado {act[1]}"))
            symbol_stack.append(look)
            node_stack.append({"label": look, "children": []})
            stack.append(act[1])
            pos += 1
        elif act[0] == REDUCE:
            prod = aug.productions[act[1]]
            body = eff_body(prod)
            steps.append(ParseStep(step_no, stack_repr, remaining, f"reducir por [{act[1]}] {prod}"))
            prod_sequence.append(act[1])
            children = []
            for _ in range(len(body)):
                stack.pop()
                symbol_stack.pop()
                children.insert(0, node_stack.pop())
            if not children:
                children = [{"label": EPSILON, "children": []}]
            top_state = stack[-1]
            goto_state = table.goto.get((top_state, prod.head))
            if goto_state is None:
                msg = f"Error interno: no hay GOTO desde el estado {top_state} con '{prod.head}'."
                steps.append(ParseStep(step_no, stack_repr, remaining, f"ERROR: {msg}"))
                return ParseResult(False, steps, msg, prod_sequence, None)
            symbol_stack.append(prod.head)
            node_stack.append({"label": prod.head, "children": children})
            stack.append(goto_state)
        elif act[0] == ACCEPT:
            steps.append(ParseStep(step_no, stack_repr, remaining, "ACEPTAR"))
            root = node_stack[-1] if node_stack else {"label": aug.productions[0].head, "children": []}
            return ParseResult(True, steps, "", prod_sequence, root)

        if step_no > 5000:
            msg = "Se excedió el número máximo de pasos (posible ciclo)."
            steps.append(ParseStep(step_no, "...", "...", f"ERROR: {msg}"))
            return ParseResult(False, steps, msg, prod_sequence, None)
