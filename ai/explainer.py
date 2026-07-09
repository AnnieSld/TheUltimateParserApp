"""El "asistente IA" de la app, pero sin llamar a ningun modelo: son puras
reglas locales que miran el resultado de parsers/grammar.py y
parsers/lr_tables.py (recursion izquierda, prefijos comunes, conflictos en
las tablas) y arman una explicacion en español. La seccion 3 del enunciado
pide justamente esto: explicar errores y sugerir arreglos para gramaticas
ambiguas o no-LL(1).
"""
from __future__ import annotations

from parsers.grammar import Grammar, EPSILON


def analyze_grammar(grammar: Grammar) -> list[str]:
    """High-level, natural-language diagnostics about the grammar itself."""
    notes = []

    direct = grammar.direct_left_recursive_nonterminals()
    if direct:
        notes.append(
            "⚠️ Recursión izquierda directa detectada en: "
            + ", ".join(sorted(set(direct)))
            + ". Esto impide construir un parser de descenso recursivo o LL(1) "
            "que termine correctamente (entrará en un ciclo infinito). "
            "Usa el botón «Eliminar recursión izquierda» para transformarla automáticamente."
        )
    else:
        indirect = [nt for nt in grammar.indirect_left_recursive_pairs() if nt not in direct]
        if indirect:
            notes.append(
                "⚠️ Posible recursión izquierda indirecta involucrando: "
                + ", ".join(sorted(set(indirect)))
                + ". Revisa las derivaciones A ⇒⁺ Aα."
            )

    # Common-prefix (needs left-factoring) check, independent of LL(1) table.
    needs_factor = []
    for nt in grammar.nonterminals:
        prefixes = {}
        for p in grammar.productions_for(nt):
            first_sym = p.body[0] if p.body and p.body[0] != EPSILON else None
            if first_sym:
                prefixes.setdefault(first_sym, 0)
                prefixes[first_sym] += 1
        if any(c > 1 for c in prefixes.values()):
            needs_factor.append(nt)
    if needs_factor:
        notes.append(
            "⚠️ Se detectaron prefijos comunes (necesitan factorización izquierda) en: "
            + ", ".join(sorted(needs_factor))
            + ". Usa «Factorizar por la izquierda» para que un parser predictivo pueda "
            "decidir la alternativa correcta viendo un solo símbolo de anticipación."
        )

    if not notes:
        notes.append(
            "✅ No se detectó recursión izquierda directa ni prefijos comunes evidentes. "
            "Es un buen candidato para LL(1); revisa igual la tabla por si hay conflictos "
            "de FIRST/FOLLOW entre alternativas."
        )
    return notes


def explain_ll1_conflicts(conflicts, grammar: Grammar) -> list[str]:
    msgs = []
    for (key, old_idx, new_idx) in conflicts:
        nt, terminal = key
        p_old = grammar.productions[old_idx]
        p_new = grammar.productions[new_idx]
        msgs.append(
            f"Conflicto en la celda [{nt}, {terminal}]: tanto «{p_old}» como «{p_new}» "
            f"podrían aplicarse al ver el símbolo '{terminal}'. Esto significa que la "
            "gramática NO es LL(1): con un solo símbolo de anticipación el parser no "
            "puede decidir. Suele arreglarse factorizando por la izquierda o "
            "reescribiendo la gramática para que las alternativas de un mismo no "
            "terminal tengan conjuntos FIRST (y, si hay ε, FOLLOW) disjuntos."
        )
    return msgs


def _suggest_shift_reduce_fix(conflict, grammar, table) -> str:
    # No es magia: son un par de patrones conocidos (operador recursivo,
    # dangling-else) que se detectan mirando la produccion involucrada, y si
    # no calza con ninguno se cae a una sugerencia generica de precedencia.
    reduce_actions = [a for a in conflict.actions if a[0] == "reduce"]
    if not reduce_actions:
        return ""
    prod = table.aug_grammar.productions[reduce_actions[0][1]]
    if len(prod.body) >= 2 and prod.head in prod.body:
        return (
            f"Sugerencia concreta: «{prod}» es una regla de operador recursivo. Separa los "
            "niveles de precedencia en no terminales distintos (p. ej. expresión → término "
            "((+|-) término)*, término → factor ((*|/) factor)*, factor → ...), en vez de "
            "dejar que el motor decida por convención cuál operador 'gana'."
        )
    if "else" in grammar.terminals and conflict.symbol == "else":
        return (
            "Sugerencia concreta: es el patrón clásico 'dangling else'. Desplazar (la "
            "opción por defecto de este motor) asocia el 'else' con el 'if' abierto más "
            "cercano, que es la semántica usual en la mayoría de lenguajes — en ese caso el "
            "conflicto es inofensivo y puedes ignorarlo. Si no es la semántica que quieres, "
            "separa las reglas en 'sentencia cerrada' (con else, sin ifs pendientes) y "
            "'sentencia abierta' (if sin else) para eliminarlo explícitamente."
        )
    return (
        "Sugerencia concreta: define una precedencia/asociatividad explícita para el "
        f"símbolo '{conflict.symbol}', o reescribe la gramática separando los casos que "
        "compiten en no terminales distintos para que el parser no tenga que adivinar."
    )


def _suggest_reduce_reduce_fix(conflict, table) -> str:
    reduce_actions = [a for a in conflict.actions if a[0] == "reduce"]
    prods = [table.aug_grammar.productions[a[1]] for a in reduce_actions]
    if len(prods) >= 2 and prods[0].body == prods[1].body:
        return (
            f"Sugerencia concreta: «{prods[0].head}» y «{prods[1].head}» generan exactamente "
            "el mismo cuerpo de producción; probablemente representan el mismo concepto "
            "duplicado. Unifícalos en un solo no terminal."
        )
    if len(prods) >= 2:
        return (
            f"Sugerencia concreta: revisa si «{prods[0].head}» y «{prods[1].head}» pueden "
            "generar la misma subcadena en este punto de la entrada. Si representan cosas "
            "distintas que hoy se ven iguales (p. ej. un identificador que podría ser "
            "variable o llamada a función), necesitas más contexto/lookahead del que da "
            "LR(1) puro para distinguirlos (a veces requiere un análisis semántico posterior)."
        )
    return "Revisa si dos no terminales distintos se solapan en su función."


def explain_lr_conflicts(conflicts, grammar, table) -> list[str]:
    msgs = []
    for c in conflicts:
        actions_desc = []
        for act in c.actions:
            if act[0] == "shift":
                actions_desc.append(f"desplazar al estado {act[1]}")
            elif act[0] == "reduce":
                actions_desc.append(f"reducir por «{table.aug_grammar.productions[act[1]]}»")
            elif act[0] == "accept":
                actions_desc.append("aceptar")
        if c.kind == "shift-reduce":
            explanation = (
                "Un conflicto desplazar/reducir suele indicar ambigüedad real en la "
                "gramática (p. ej. el clásico 'dangling else', o falta de precedencia/"
                "asociatividad definida entre operadores). El motor eligió desplazar "
                "por convención, pero conviene revisar la regla involucrada."
            )
            suggestion = _suggest_shift_reduce_fix(c, grammar, table)
        else:
            explanation = (
                "Un conflicto reducir/reducir casi siempre significa que la gramática "
                "es ambigua: dos producciones distintas pueden derivar exactamente la "
                "misma cadena en este contexto. Revisa si dos no terminales se solapan "
                "en su función."
            )
            suggestion = _suggest_reduce_reduce_fix(c, table)
        msgs.append(
            f"Estado {c.state}, símbolo '{c.symbol}': "
            + " vs. ".join(actions_desc)
            + f". {explanation} {suggestion}"
        )
    return msgs


def explain_parse_error(method: str, error: str, grammar: Grammar, tokens: list) -> str:
    if not error:
        return ""
    hint = ""
    known = grammar.terminals
    unknown = [t for t in tokens if t not in known]
    if unknown:
        hint = (
            " Pista: el/los símbolo(s) "
            + ", ".join(f"'{u}'" for u in sorted(set(unknown)))
            + f" no aparecen como terminales de la gramática ({', '.join(sorted(known))}). "
            "Revisa que hayas separado los tokens con espacios y que coincidan exactamente "
            "con los terminales declarados."
        )
    return f"[{method}] {error}{hint}"


def compare_methods_summary(rows: list[dict]) -> str:
    """rows: [{method, states, conflicts, accepted}] -> short natural-language summary."""
    lines = []
    for r in rows:
        status = "✅ acepta la cadena" if r.get("accepted") else "❌ no la acepta / no aplica"
        conflict_note = (
            f", {r['conflicts']} conflicto(s) en la tabla" if r.get("conflicts") else ", sin conflictos"
        )
        lines.append(f"- **{r['method']}**: {r['states']} estados{conflict_note} — {status}")
    lines.append(
        "\nEn general, la potencia de reconocimiento crece así: "
        "LR(0) ⊂ SLR(1) ⊆ LALR(1) ⊆ LR(1). Una gramática puede tener conflictos en LR(0) o "
        "SLR(1) y sin embargo ser perfectamente manejable por LALR(1) o LR(1), a costa de "
        "tablas (mucho) más grandes en el caso de LR(1)."
    )
    return "\n".join(lines)
