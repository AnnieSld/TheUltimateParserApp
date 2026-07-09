"""Construccion de la tabla predictiva LL(1) y simulacion con pila. Es el
metodo top-down "de verdad" (a diferencia del descenso recursivo con
backtracking): en vez de probar alternativas y retroceder, la tabla ya le
dice al parser exactamente que produccion usar mirando un solo simbolo de
anticipacion -- por eso una gramatica con conflictos en esta tabla
directamente no es LL(1), no hay forma de "arreglarlo" en la simulacion.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from .grammar import Grammar, EPSILON, END


@dataclass
class LL1Table:
    grammar: Grammar
    table: dict            # (nonterminal, terminal) -> production index
    conflicts: list        # list of ((nt, terminal), existing_idx, new_idx)
    first: dict
    follow: dict

    def cell(self, nt, t):
        idx = self.table.get((nt, t))
        if idx is None:
            return ""
        return f"{nt} -> {' '.join(self.grammar.productions[idx].body)}"


def build_ll1_table(grammar: Grammar) -> LL1Table:
    # Regla del libro: si A -> alpha y 'a' esta en FIRST(alpha), se coloca
    # esa produccion en [A, a]. Si ademas alpha puede derivar en vacio,
    # tambien se coloca en [A, b] para cada b en FOLLOW(A) -- porque en ese
    # caso alpha "desaparece" y lo que decide es lo que viene despues de A.
    # Si dos producciones distintas quieren la misma celda, es un conflicto
    # y la gramatica no es LL(1).
    first = grammar.compute_first()
    follow = grammar.compute_follow(first)
    nullable = grammar.compute_nullable()
    table = {}
    conflicts = []

    for p in grammar.productions:
        body = () if p.is_epsilon else p.body
        first_alpha = grammar._first_of_sequence(body, first, nullable)
        for t in first_alpha - {EPSILON}:
            key = (p.head, t)
            if key in table and table[key] != p.index:
                conflicts.append((key, table[key], p.index))
            else:
                table[key] = p.index
        if EPSILON in first_alpha:
            for t in follow[p.head]:
                key = (p.head, t)
                if key in table and table[key] != p.index:
                    conflicts.append((key, table[key], p.index))
                else:
                    table[key] = p.index

    return LL1Table(grammar, table, conflicts, first, follow)


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


def ll1_parse(ll1: LL1Table, tokens: list) -> ParseResult:
    # Parsing dirigido por tabla: la pila empieza con el simbolo inicial, y
    # en cada paso se mira (tope de la pila, simbolo actual de la entrada).
    # Si el tope es terminal tiene que calzar exacto con la entrada; si es
    # no terminal, se busca en la tabla que produccion aplicar y se
    # reemplaza el tope por su cuerpo (al reves, para que quede en orden).
    # Los nodos del arbol se arman en paralelo, sin afectar el parsing en si.
    grammar = ll1.grammar
    root = {"label": grammar.start_symbol, "children": None}
    stack = [None, root]  # None is the END sentinel node
    input_tokens = list(tokens) + [END]
    pos = 0
    steps = []
    prod_sequence = []
    step_no = 0

    def sym_of(node):
        return END if node is None else node["label"]

    while stack:
        top_node = stack[-1]
        top = sym_of(top_node)
        cur = input_tokens[pos]
        stack_repr = " ".join(sym_of(n) for n in reversed(stack))
        remaining = " ".join(input_tokens[pos:])
        step_no += 1

        if top == END and cur == END:
            steps.append(ParseStep(step_no, stack_repr, remaining, "ACEPTAR"))
            return ParseResult(True, steps, "", prod_sequence, root)

        if top in grammar.terminals or top == END:
            if top == cur:
                steps.append(ParseStep(step_no, stack_repr, remaining, f"emparejar '{top}'"))
                stack.pop()
                pos += 1
            else:
                msg = f"Error sintáctico: se esperaba '{top}' pero se encontró '{cur}'."
                steps.append(ParseStep(step_no, stack_repr, remaining, f"ERROR: {msg}"))
                return ParseResult(False, steps, msg, prod_sequence, root)
        else:
            key = (top, cur)
            prod_idx = ll1.table.get(key)
            if prod_idx is None:
                expected = sorted(t for (nt, t) in ll1.table if nt == top)
                msg = (
                    f"Error sintáctico: no hay producción para [{top}, {cur}] en la tabla LL(1). "
                    f"Símbolos esperados para '{top}': {', '.join(expected) if expected else '(ninguno)'}."
                )
                steps.append(ParseStep(step_no, stack_repr, remaining, f"ERROR: {msg}"))
                return ParseResult(False, steps, msg, prod_sequence, root)
            prod = grammar.productions[prod_idx]
            steps.append(ParseStep(step_no, stack_repr, remaining, f"aplicar [{prod_idx}] {prod}"))
            prod_sequence.append(prod_idx)
            stack.pop()
            if prod.is_epsilon:
                top_node["children"] = [{"label": EPSILON, "children": []}]
            else:
                child_nodes = [{"label": sym, "children": None} for sym in prod.body]
                top_node["children"] = child_nodes
                for child in reversed(child_nodes):
                    stack.append(child)

        if step_no > 5000:
            msg = "Se excedió el número máximo de pasos (posible ciclo)."
            steps.append(ParseStep(step_no, "...", "...", f"ERROR: {msg}"))
            return ParseResult(False, steps, msg, prod_sequence, root)

    return ParseResult(False, steps, "Pila vacía sin aceptar.", prod_sequence, root)
