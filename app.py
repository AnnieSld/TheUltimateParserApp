"""Punto de entrada de la app (Streamlit). CS3402 Compiladores 2026-1,
Concurso de Desarrollo. Analiza gramáticas y cadenas con los 6 métodos de
parsing, mostrando tablas, autómatas, árboles de derivación y las
explicaciones del "asistente IA".

Este archivo es puramente de interfaz: toda la logica de parsing en si vive
en parsers/, ai/, visualization/ y utils/. Aca solo se arma la UI y se
conecta con esas funciones.

Detalle de Streamlit que vale la pena tener presente: las 9 pestañas
(st.tabs) se ejecutan TODAS en cada rerun, no solo la que esta visible --
por eso cada boton "Analizar cadena" necesita su propio key unico
(rd_run, ll1_run, lr_run_LR(0), etc.), si no Streamlit tira error de
key duplicada.
"""
from __future__ import annotations

import pandas as pd
import streamlit as st

from parsers.grammar import Grammar, GrammarError, EPSILON, ARROW, END
from parsers.examples import EXAMPLES
from parsers import recursive_descent
from parsers.ll1 import build_ll1_table, ll1_parse
from parsers.lr_tables import BUILDERS, lr_parse
from ai import explainer
from visualization.graphviz_utils import tree_to_dot, automaton_to_dot
from utils import history as history_util
from utils.export_pdf import build_pdf_report

st.set_page_config(page_title="The Ultimate Parser App", page_icon="🧩", layout="wide")

KEYBOARD_SYMBOLS = ["→", "ε", "|", "•", "$", "(", ")", "'"]

DEFAULT_EXAMPLE = "Expresiones aritméticas (con recursión izquierda)"


# ---------------------------------------------------------------------
# Session state bootstrap: Streamlit reejecuta este script completo en
# cada interaccion, asi que lo unico que persiste entre reruns es lo que
# se guarda en st.session_state (por eso la gramatica, la cadena y el
# historial viven aca y no en variables sueltas).
# ---------------------------------------------------------------------
if "grammar_text" not in st.session_state:
    st.session_state.grammar_text = EXAMPLES[DEFAULT_EXAMPLE]["grammar"]
if "input_string" not in st.session_state:
    st.session_state.input_string = EXAMPLES[DEFAULT_EXAMPLE]["input"]
if "history" not in st.session_state:
    st.session_state.history = []


def _append_symbol(sym: str):
    st.session_state.grammar_text += sym


def _load_example():
    ex = EXAMPLES[st.session_state.example_choice]
    st.session_state.grammar_text = ex["grammar"]
    st.session_state.input_string = ex["input"]


def _apply_transformed_grammar(new_text: str):
    st.session_state.grammar_text = new_text


# ---------------------------------------------------------------------
# Sidebar: grammar input, virtual keyboard, example picker, cadena
# ---------------------------------------------------------------------
with st.sidebar:
    st.title("🧩 Ultimate Parser App")
    st.caption("CS3402 Compiladores · Concurso de Desarrollo")

    st.selectbox(
        "Cargar gramática de ejemplo",
        list(EXAMPLES.keys()),
        key="example_choice",
        index=list(EXAMPLES.keys()).index(DEFAULT_EXAMPLE),
        on_change=_load_example,
    )

    st.text_area(
        "Gramática (una regla por línea: `A -> α | β`, usa ε para vacío)",
        key="grammar_text",
        height=180,
    )

    st.caption("Teclado virtual")
    kb_cols = st.columns(len(KEYBOARD_SYMBOLS))
    for col, sym in zip(kb_cols, KEYBOARD_SYMBOLS):
        col.button(sym, key=f"kb_{sym}", on_click=_append_symbol, args=(sym,))

    st.text_input("Cadena de entrada (tokens separados por espacios)", key="input_string")

    st.divider()
    if st.button("🗑️ Vaciar historial"):
        st.session_state.history.clear()


def tokenize(s: str) -> list[str]:
    return s.split()


def get_grammar() -> Grammar | None:
    try:
        return Grammar.parse(st.session_state.grammar_text)
    except GrammarError as e:
        st.error(f"Error en la gramática: {e}")
        return None


def first_follow_df(grammar: Grammar) -> pd.DataFrame:
    first = grammar.compute_first()
    follow = grammar.compute_follow(first)
    rows = []
    for nt in sorted(grammar.nonterminals):
        rows.append(
            {
                "No terminal": nt,
                "FIRST": ", ".join(sorted(first[nt])),
                "FOLLOW": ", ".join(sorted(follow[nt])),
            }
        )
    return pd.DataFrame(rows)


def productions_text(grammar: Grammar) -> str:
    lines = [f"[{p.index}] {p}" for p in grammar.productions]
    return "\n".join(lines)


MAX_DISPLAYED_STEPS = 300


def steps_df(steps) -> pd.DataFrame:
    # Si la gramatica tiene un ciclo (por ejemplo recursion izquierda que se
    # coló hasta aca), la traza puede tener miles de pasos -- mostrarla
    # completa hace que la tabla tarde bastante en renderizar, asi que se
    # recorta a los primeros y ultimos pasos con un aviso.
    if len(steps) > MAX_DISPLAYED_STEPS:
        st.caption(
            f"La traza tiene {len(steps)} pasos (posible ciclo); se muestran los primeros "
            f"{MAX_DISPLAYED_STEPS - 50} y los últimos 50."
        )
        steps = steps[: MAX_DISPLAYED_STEPS - 50] + steps[-50:]
    return pd.DataFrame(
        [{"#": s.step, "Pila": s.stack, "Entrada restante": s.input_remaining, "Acción": s.action} for s in steps]
    )


def show_ai_notes(grammar: Grammar):
    with st.expander("🤖 Notas del Asistente IA sobre esta gramática", expanded=False):
        for note in explainer.analyze_grammar(grammar):
            st.markdown(note)


def pdf_download_button(label, filename, title, grammar, sections):
    pdf_bytes = build_pdf_report(title, grammar.to_text(), sections)
    st.download_button(label, data=pdf_bytes, file_name=filename, mime="application/pdf")


# ---------------------------------------------------------------------
# Top-down renderers
# ---------------------------------------------------------------------
def render_recursive_descent(grammar: Grammar):
    st.subheader("Descenso Recursivo (backtracking)")
    show_ai_notes(grammar)
    st.code(productions_text(grammar), language="text")
    st.dataframe(first_follow_df(grammar), use_container_width=True, hide_index=True)

    if st.button("▶️ Analizar cadena", key="rd_run"):
        tokens = tokenize(st.session_state.input_string)
        result = recursive_descent.parse(grammar, tokens)
        history_util.add_entry(
            st.session_state.history, grammar.to_text(), "Descenso Recursivo", " ".join(tokens), result.accepted
        )
        if result.accepted:
            st.success("✅ Cadena ACEPTADA")
            st.graphviz_chart(tree_to_dot(result.tree, "ArbolRD"), use_container_width=True)
        else:
            st.error("❌ Cadena RECHAZADA")
            st.warning(explainer.explain_parse_error("Descenso Recursivo", result.error, grammar, tokens))

        with st.expander("Traza paso a paso (llamadas, coincidencias y retrocesos)"):
            for t in result.trace:
                icon = {"enter": "➡️", "match": "✅", "fail": "⚠️", "backtrack": "↩️"}[t.kind]
                st.text(("  " * t.depth) + f"{icon} {t.message}")

        pdf_download_button(
            "📄 Exportar PDF",
            "reporte_descenso_recursivo.pdf",
            "Descenso Recursivo",
            grammar,
            [
                ("FIRST / FOLLOW", [["No terminal", "FIRST", "FOLLOW"]] + first_follow_df(grammar).values.tolist()),
                ("Resultado", "ACEPTADA" if result.accepted else f"RECHAZADA: {result.error}"),
            ],
        )


def render_ll1(grammar: Grammar):
    st.subheader("Parser Predictivo LL(1)")
    show_ai_notes(grammar)
    st.code(productions_text(grammar), language="text")

    ff = first_follow_df(grammar)
    st.dataframe(ff, use_container_width=True, hide_index=True)

    ll1 = build_ll1_table(grammar)
    terminals = sorted(grammar.terminals) + [END]
    nts = sorted(grammar.nonterminals)
    table_rows = []
    for nt in nts:
        row = {"No terminal": nt}
        for t in terminals:
            row[t] = ll1.cell(nt, t)
        table_rows.append(row)
    table_df = pd.DataFrame(table_rows)
    st.markdown("**Tabla de análisis LL(1)**")
    st.dataframe(table_df, use_container_width=True, hide_index=True)

    if ll1.conflicts:
        st.warning(f"⚠️ Se encontraron {len(ll1.conflicts)} conflicto(s): la gramática NO es LL(1).")
        for msg in explainer.explain_ll1_conflicts(ll1.conflicts, grammar):
            st.markdown(f"- {msg}")
    else:
        st.success("✅ Sin conflictos: la gramática es LL(1).")

    if st.button("▶️ Analizar cadena", key="ll1_run"):
        tokens = tokenize(st.session_state.input_string)
        result = ll1_parse(ll1, tokens)
        history_util.add_entry(
            st.session_state.history, grammar.to_text(), "LL(1)", " ".join(tokens), result.accepted
        )
        if result.accepted:
            st.success("✅ Cadena ACEPTADA")
            st.graphviz_chart(tree_to_dot(result.tree, "ArbolLL1"), use_container_width=True)
        else:
            st.error("❌ Cadena RECHAZADA")
            st.warning(explainer.explain_parse_error("LL(1)", result.error, grammar, tokens))

        with st.expander("Traza paso a paso (pila / entrada / acción)"):
            st.dataframe(steps_df(result.steps), use_container_width=True, hide_index=True)

        pdf_download_button(
            "📄 Exportar PDF",
            "reporte_ll1.pdf",
            "Parser LL(1)",
            grammar,
            [
                ("FIRST / FOLLOW", [["No terminal", "FIRST", "FOLLOW"]] + ff.values.tolist()),
                ("Tabla LL(1)", [list(table_df.columns)] + table_df.values.tolist()),
                ("Resultado", "ACEPTADA" if result.accepted else f"RECHAZADA: {result.error}"),
            ],
        )


# ---------------------------------------------------------------------
# Bottom-up (LR family): una sola funcion para los 4 metodos, porque la
# unica diferencia real entre LR(0)/SLR(1)/LALR(1)/LR(1) esta en que
# construye distinto la tabla (BUILDERS[method]); la parte visual
# (automata, tablas ACTION/GOTO, conflictos, boton de analizar) es
# identica para los cuatro.
# ---------------------------------------------------------------------
def render_lr(method: str, grammar: Grammar):
    st.subheader(f"Análisis {method}")
    show_ai_notes(grammar)

    builder = BUILDERS[method]
    table = builder(grammar)

    st.markdown("**Gramática aumentada**")
    st.code(productions_text(table.aug_grammar), language="text")

    with st.expander(f"Autómata LR ({len(table.states)} estados)", expanded=False):
        st.graphviz_chart(automaton_to_dot(table.states, table.transitions, table.aug_grammar), use_container_width=True)

    terminals = sorted(grammar.terminals) + [END]
    nts = sorted(grammar.nonterminals)
    action_rows = []
    for i in range(len(table.states)):
        row = {"Estado": i}
        for t in terminals:
            row[t] = table.action_str(i, t)
        action_rows.append(row)
    goto_rows = []
    for i in range(len(table.states)):
        row = {"Estado": i}
        for nt in nts:
            j = table.goto.get((i, nt))
            row[nt] = "" if j is None else str(j)
        goto_rows.append(row)
    action_df = pd.DataFrame(action_rows)
    goto_df = pd.DataFrame(goto_rows)

    c1, c2 = st.columns(2)
    with c1:
        st.markdown("**Tabla ACTION**")
        st.dataframe(action_df, use_container_width=True, hide_index=True)
    with c2:
        st.markdown("**Tabla GOTO**")
        st.dataframe(goto_df, use_container_width=True, hide_index=True)

    if table.conflicts:
        st.warning(f"⚠️ Se encontraron {len(table.conflicts)} conflicto(s) en la tabla {method}.")
        for msg in explainer.explain_lr_conflicts(table.conflicts, grammar, table):
            st.markdown(f"- {msg}")
    else:
        st.success(f"✅ Sin conflictos: la gramática es {method}.")

    if st.button("▶️ Analizar cadena", key=f"lr_run_{method}"):
        tokens = tokenize(st.session_state.input_string)
        result = lr_parse(table, tokens)
        history_util.add_entry(
            st.session_state.history, grammar.to_text(), method, " ".join(tokens), result.accepted
        )
        if result.accepted:
            st.success("✅ Cadena ACEPTADA")
            st.graphviz_chart(tree_to_dot(result.tree, f"Arbol{method.replace('(', '').replace(')', '')}"), use_container_width=True)
        else:
            st.error("❌ Cadena RECHAZADA")
            st.warning(explainer.explain_parse_error(method, result.error, grammar, tokens))

        with st.expander("Traza paso a paso (pila / entrada / acción)"):
            st.dataframe(steps_df(result.steps), use_container_width=True, hide_index=True)

        pdf_download_button(
            "📄 Exportar PDF",
            f"reporte_{method.lower().replace('(', '').replace(')', '')}.pdf",
            f"Análisis {method}",
            grammar,
            [
                ("Tabla ACTION", [list(action_df.columns)] + action_df.values.tolist()),
                ("Tabla GOTO", [list(goto_df.columns)] + goto_df.values.tolist()),
                ("Resultado", "ACEPTADA" if result.accepted else f"RECHAZADA: {result.error}"),
            ],
        )


# ---------------------------------------------------------------------
# Compare tab
# ---------------------------------------------------------------------
def render_compare(grammar: Grammar):
    st.subheader("Comparación entre algoritmos")
    tokens = tokenize(st.session_state.input_string)
    rows = []

    ll1 = build_ll1_table(grammar)
    ll1_result = ll1_parse(ll1, tokens)
    rows.append(
        {
            "method": "LL(1)",
            "states": len(grammar.nonterminals),
            "conflicts": len(ll1.conflicts),
            "accepted": ll1_result.accepted and not ll1.conflicts,
        }
    )

    for method in ["LR(0)", "SLR(1)", "LALR(1)", "LR(1)"]:
        table = BUILDERS[method](grammar)
        res = lr_parse(table, tokens)
        rows.append(
            {
                "method": method,
                "states": len(table.states),
                "conflicts": len(table.conflicts),
                "accepted": res.accepted,
            }
        )

    df = pd.DataFrame(
        [
            {
                "Método": r["method"],
                "Estados": r["states"],
                "Conflictos": r["conflicts"],
                "¿Acepta la cadena?": "✅" if r["accepted"] else "❌",
                "¿Es aplicable sin conflictos?": "✅" if r["conflicts"] == 0 else "❌",
            }
            for r in rows
        ]
    )
    st.dataframe(df, use_container_width=True, hide_index=True)
    st.markdown(explainer.compare_methods_summary(rows))


# ---------------------------------------------------------------------
# AI assistant tab
# ---------------------------------------------------------------------
def render_ai_tab(grammar: Grammar):
    st.subheader("🤖 Asistente IA (heurísticas locales)")
    st.caption(
        "Explicaciones y sugerencias generadas por reglas propias del proyecto "
        "(sin llamar a un LLM externo), tal como pide la sección 3 del enunciado."
    )
    for note in explainer.analyze_grammar(grammar):
        st.markdown(note)

    c1, c2 = st.columns(2)
    with c1:
        if st.button("🛠️ Eliminar recursión izquierda"):
            new_g = grammar.eliminate_left_recursion()
            st.code(new_g.to_text(), language="text")
            st.button(
                "✅ Usar esta gramática",
                key="use_no_leftrec",
                on_click=_apply_transformed_grammar,
                args=(new_g.to_text(),),
            )
    with c2:
        if st.button("🛠️ Factorizar por la izquierda"):
            new_g = grammar.left_factor()
            st.code(new_g.to_text(), language="text")
            st.button(
                "✅ Usar esta gramática",
                key="use_factored",
                on_click=_apply_transformed_grammar,
                args=(new_g.to_text(),),
            )


def render_history_tab():
    st.subheader("🕘 Historial de análisis")
    if not st.session_state.history:
        st.info("Todavía no hay análisis registrados en esta sesión.")
        return
    rows = history_util.to_rows(st.session_state.history)
    st.dataframe(pd.DataFrame(rows[1:], columns=rows[0]), use_container_width=True, hide_index=True)


# ---------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------
st.title("The Ultimate Parser App")
st.caption("Analizador de gramáticas y cadenas · Top-Down y Bottom-Up · CS3402 Compiladores 2026-1")

grammar = get_grammar()

if grammar is not None:
    tabs = st.tabs(
        [
            "Descenso Recursivo",
            "LL(1)",
            "LR(0)",
            "SLR(1)",
            "LALR(1)",
            "LR(1)",
            "Comparar",
            "Asistente IA",
            "Historial",
        ]
    )
    with tabs[0]:
        render_recursive_descent(grammar)
    with tabs[1]:
        render_ll1(grammar)
    with tabs[2]:
        render_lr("LR(0)", grammar)
    with tabs[3]:
        render_lr("SLR(1)", grammar)
    with tabs[4]:
        render_lr("LALR(1)", grammar)
    with tabs[5]:
        render_lr("LR(1)", grammar)
    with tabs[6]:
        render_compare(grammar)
    with tabs[7]:
        render_ai_tab(grammar)
    with tabs[8]:
        render_history_tab()
