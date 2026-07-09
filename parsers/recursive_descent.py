"""Descenso recursivo generico, con backtracking. Ojo: esto NO es un parser
generado a mano por cada no terminal como saldria en un compilador real --
es una version generica que prueba cada alternativa en el orden en que
aparece en la gramatica y retrocede si falla, dejando registrado cada
llamado/coincidencia/retroceso para poder mostrarlo paso a paso en la UI.

Con gramaticas que tienen recursion izquierda esto se cuelga (llama a la
misma funcion sin haber avanzado en la entrada), asi que antes de intentar
nada se revisa eso y se corta con un mensaje en vez de dejar que reviente.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from .grammar import Grammar, EPSILON

MAX_STEPS = 20000


class StepGuardExceeded(Exception):
    pass


@dataclass
class Trace:
    depth: int
    message: str
    kind: str  # "enter" | "match" | "fail" | "backtrack"


@dataclass
class ParseResult:
    accepted: bool
    trace: list
    error: str = ""
    tree: dict | None = None


def parse(grammar: Grammar, tokens: list) -> ParseResult:
    direct_left_rec = grammar.direct_left_recursive_nonterminals()
    if direct_left_rec:
        return ParseResult(
            False,
            [],
            "No se puede ejecutar el descenso recursivo: la gramática tiene recursión "
            f"izquierda directa en {', '.join(sorted(set(direct_left_rec)))}. Un parser de "
            "descenso recursivo entraría en un ciclo infinito (llamaría a la misma función "
            "sin avanzar en la entrada). Ve a la pestaña «Asistente IA» y usa «Eliminar "
            "recursión izquierda» antes de analizar con este método.",
            None,
        )

    trace: list[Trace] = []
    steps = {"n": 0}

    def tick():
        steps["n"] += 1
        if steps["n"] > MAX_STEPS:
            raise StepGuardExceeded()

    def match(pos, symbol, depth):
        tick()
        if symbol in grammar.terminals:
            cur = tokens[pos] if pos < len(tokens) else None
            if cur == symbol:
                trace.append(Trace(depth, f"emparejar terminal '{symbol}'", "match"))
                return True, pos + 1, {"label": symbol, "children": []}
            trace.append(
                Trace(depth, f"se esperaba '{symbol}' y se encontró '{cur if cur else 'fin de entrada'}'", "fail")
            )
            return False, pos, None

        trace.append(Trace(depth, f"llamar a {symbol}(...)", "enter"))
        for prod in grammar.productions_for(symbol):
            body = () if prod.is_epsilon else prod.body
            trace.append(Trace(depth + 1, f"intentar {prod}", "enter"))
            cur_pos = pos
            children = []
            ok = True
            for sym in body:
                success, cur_pos, node = match(cur_pos, sym, depth + 2)
                if not success:
                    ok = False
                    break
                children.append(node)
            if ok:
                if not body:
                    children = [{"label": EPSILON, "children": []}]
                return True, cur_pos, {"label": symbol, "prod": str(prod), "children": children}
            trace.append(Trace(depth + 1, f"retroceder (backtrack) desde {prod}", "backtrack"))
        trace.append(Trace(depth, f"{symbol}: ninguna alternativa funcionó en la posición {pos}", "fail"))
        return False, pos, None

    try:
        success, pos, tree = match(0, grammar.start_symbol, 0)
    except StepGuardExceeded:
        return ParseResult(
            False,
            trace[-200:],
            "Se excedió el número máximo de pasos: probablemente la gramática tiene "
            "recursión izquierda, lo que provoca un ciclo infinito en el descenso recursivo.",
            None,
        )
    except RecursionError:
        return ParseResult(
            False,
            trace[-200:],
            "Se alcanzó el límite de recursión de Python: la gramática probablemente tiene "
            "recursión izquierda indirecta (A ⇒⁺ Aα). Revisa las notas del Asistente IA.",
            None,
        )

    if success and pos == len(tokens):
        return ParseResult(True, trace, "", tree)
    if success and pos != len(tokens):
        return ParseResult(
            False, trace, f"Se reconoció un prefijo válido pero sobran símbolos desde la posición {pos}.", tree
        )
    return ParseResult(False, trace, "La cadena no pertenece al lenguaje generado por la gramática.", None)
