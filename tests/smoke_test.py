"""Quick end-to-end sanity check of the parsing engine (no Streamlit).

Run with: python tests/smoke_test.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from parsers.grammar import Grammar, GrammarError, EPSILON
from parsers.examples import EXAMPLES
from parsers import recursive_descent
from parsers.ll1 import build_ll1_table, ll1_parse
from parsers.lr_tables import BUILDERS, lr_parse
from ai import explainer

failures = []


def check(cond, msg):
    if not cond:
        failures.append(msg)
        print(f"FAIL: {msg}")
    else:
        print(f"ok:   {msg}")


def run():
    for name, ex in EXAMPLES.items():
        print(f"\n=== {name} ===")
        try:
            g = Grammar.parse(ex["grammar"])
        except GrammarError as e:
            check(False, f"[{name}] no parseó la gramática: {e}")
            continue
        tokens = ex["input"].split()

        # FIRST/FOLLOW must not crash and must be non-empty for start symbol
        first = g.compute_first()
        follow = g.compute_follow(first)
        check(g.start_symbol in follow, f"[{name}] FOLLOW contiene al símbolo inicial")

        # Recursive descent (skip actual run if direct left recursion, still must not hang thanks to guard)
        rd = recursive_descent.parse(g, tokens)
        check(True, f"[{name}] descenso recursivo terminó (aceptó={rd.accepted})")

        # LL(1)
        ll1 = build_ll1_table(g)
        ll1_res = ll1_parse(ll1, tokens)
        check(True, f"[{name}] LL(1) terminó (conflictos={len(ll1.conflicts)}, aceptó={ll1_res.accepted})")

        # LR family
        for method in ["LR(0)", "SLR(1)", "LALR(1)", "LR(1)"]:
            table = BUILDERS[method](g)
            res = lr_parse(table, tokens)
            check(len(table.states) > 0, f"[{name}] {method} construyó {len(table.states)} estados")
            print(f"      {method}: conflictos={len(table.conflicts)} aceptó={res.accepted}")

        # AI heuristics must not crash
        notes = explainer.analyze_grammar(g)
        check(len(notes) > 0, f"[{name}] el asistente IA generó {len(notes)} nota(s)")

    # Grammar transformations
    left_rec_g = Grammar.parse(EXAMPLES["Expresiones aritméticas (con recursión izquierda)"]["grammar"])
    fixed = left_rec_g.eliminate_left_recursion()
    check(
        not fixed.direct_left_recursive_nonterminals(),
        "eliminate_left_recursion() elimina toda la recursión izquierda directa",
    )
    ll1_fixed = build_ll1_table(fixed)
    ll1_res = ll1_parse(ll1_fixed, "id + id * id".split())
    check(ll1_res.accepted, "la gramática sin recursión izquierda es aceptada por LL(1) para 'id + id * id'")

    factor_g = Grammar.parse(EXAMPLES["Gramática con prefijos comunes (necesita factorización)"]["grammar"])
    factored = factor_g.left_factor()
    ll1_factored = build_ll1_table(factored)
    check(len(ll1_factored.conflicts) == 0, "left_factor() produce una gramática LL(1) sin conflictos")

    # Regression: symbols glued together without spaces (S -> AB, A -> aA) must
    # be segmented into individual declared symbols, not read as one literal token.
    glued_g = Grammar.parse("S -> AB\nA -> aA | \nB -> b")
    check(
        glued_g.productions[0].body == ("A", "B"),
        "'S -> AB' se tokeniza como los símbolos 'A' 'B', no como un token literal 'AB'",
    )
    glued_first = glued_g.compute_first()
    glued_follow = glued_g.compute_follow(glued_first)
    check(glued_first["S"] == {"a", "b"}, f"FIRST(S) = {{a, b}} para la gramática pegada (obtuve {glued_first['S']})")
    check(glued_first["A"] == {"a", EPSILON}, f"FIRST(A) incluye 'a' y ε (obtuve {glued_first['A']})")
    check(glued_follow["A"] == {"b"}, f"FOLLOW(A) = {{b}} (obtuve {glued_follow['A']})")
    check(glued_follow["B"] == {"$"}, f"FOLLOW(B) = {{$}} (obtuve {glued_follow['B']})")

    # Known-conflict grammar: if-then-else must show a shift-reduce conflict in every LR method
    ite_g = Grammar.parse(EXAMPLES["If-then-else (conflicto shift/reduce, dangling else)"]["grammar"])
    for method in ["LR(0)", "SLR(1)", "LALR(1)", "LR(1)"]:
        table = BUILDERS[method](ite_g)
        check(len(table.conflicts) >= 1, f"if-then-else produce conflicto(s) en {method} (dangling else)")

    print("\n" + "=" * 60)
    if failures:
        print(f"{len(failures)} FALLO(S):")
        for f in failures:
            print(" -", f)
        sys.exit(1)
    print("Todas las verificaciones pasaron correctamente.")


if __name__ == "__main__":
    run()
