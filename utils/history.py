"""In-session analysis history (value-add feature: 'Historial de análisis')."""
from __future__ import annotations

from datetime import datetime


def add_entry(history: list, grammar_text: str, method: str, input_string: str, accepted: bool, extra: str = ""):
    history.insert(
        0,
        {
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "grammar": grammar_text,
            "method": method,
            "input": input_string,
            "resultado": "Aceptada" if accepted else "Rechazada",
            "detalle": extra,
        },
    )
    del history[50:]  # keep it bounded


def to_rows(history: list):
    rows = [["#", "Hora", "Método", "Cadena", "Resultado"]]
    for i, h in enumerate(history):
        rows.append([str(i + 1), h["timestamp"], h["method"], h["input"], h["resultado"]])
    return rows
