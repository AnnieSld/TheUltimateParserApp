"""A handful of textbook grammars used to pre-populate the UI."""

EXAMPLES = {
    "Expresiones aritméticas (con recursión izquierda)": {
        "grammar": "E -> E + T | T\nT -> T * F | F\nF -> ( E ) | id",
        "input": "id + id * id",
    },
    "Expresiones aritméticas (lista para LL(1))": {
        "grammar": (
            "E -> T Ep\n"
            "Ep -> + T Ep | ε\n"
            "T -> F Tp\n"
            "Tp -> * F Tp | ε\n"
            "F -> ( E ) | id"
        ),
        "input": "id + id * id",
    },
    "If-then-else (conflicto shift/reduce, dangling else)": {
        "grammar": "S -> if E then S | if E then S else S | other\nE -> id",
        "input": "if id then if id then other else other",
    },
    "Asignación simple": {
        "grammar": "S -> id = E\nE -> E + id | id",
        "input": "id = id + id",
    },
    "Gramática con prefijos comunes (necesita factorización)": {
        "grammar": "S -> id = E | id ( L )\nE -> id\nL -> id",
        "input": "id = id",
    },
    "Palíndromos con a/b (ambigua para cualquier LR(k) — no es DCFL)": {
        "grammar": "S -> a S a | b S b | a | b | ε",
        "input": "a b b a",
    },
    "Símbolos de una letra sin espacios (S -> AB)": {
        "grammar": "S -> AB\nA -> aA | ε\nB -> b",
        "input": "a a b",
    },
}
