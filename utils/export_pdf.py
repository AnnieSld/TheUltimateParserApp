"""PDF export of grammar analysis / parsing tables (value-add feature #4)."""
from __future__ import annotations

from fpdf import FPDF


class _Report(FPDF):
    def header(self):
        self.set_font("Helvetica", "B", 14)
        self.set_text_color(60, 60, 90)
        self.cell(0, 10, "The Ultimate Parser App - Reporte", ln=True, align="C")
        self.set_draw_color(150, 150, 200)
        self.line(10, 20, 200, 20)
        self.ln(6)

    def footer(self):
        self.set_y(-15)
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(150, 150, 150)
        self.cell(0, 10, f"Página {self.page_no()}", align="C")


def _sanitize(text: str) -> str:
    # fpdf's core fonts are latin-1 only; swap the symbols we use for ASCII look-alikes.
    return (
        str(text)
        .replace("→", "->")
        .replace("•", ".")
        .replace("ε", "eps")
        .encode("latin-1", "replace")
        .decode("latin-1")
    )


def build_pdf_report(title: str, grammar_text: str, sections: list) -> bytes:
    """sections: list of (heading, table_rows) where table_rows is a list of
    tuples/lists (first row = header) OR a plain string of body text."""
    pdf = _Report(orientation="L", format="A4")
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()

    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(0, 8, _sanitize(title), ln=True)
    pdf.set_font("Courier", size=10)
    for line in grammar_text.splitlines():
        pdf.cell(0, 5, _sanitize(line), ln=True)
    pdf.ln(4)

    for heading, content in sections:
        pdf.set_font("Helvetica", "B", 11)
        pdf.set_text_color(70, 70, 130)
        pdf.cell(0, 8, _sanitize(heading), ln=True)
        pdf.set_text_color(0, 0, 0)

        if isinstance(content, str):
            pdf.set_font("Helvetica", size=9)
            for line in content.splitlines():
                pdf.multi_cell(0, 5, _sanitize(line))
            pdf.ln(2)
            continue

        rows = content
        if not rows:
            continue
        n_cols = len(rows[0])
        page_width = pdf.w - 2 * pdf.l_margin
        col_width = page_width / max(n_cols, 1)
        pdf.set_font("Helvetica", "B", 8)
        for cell in rows[0]:
            pdf.cell(col_width, 6, _sanitize(cell), border=1)
        pdf.ln()
        pdf.set_font("Helvetica", size=8)
        for row in rows[1:]:
            for cell in row:
                pdf.cell(col_width, 6, _sanitize(cell), border=1)
            pdf.ln()
        pdf.ln(4)

    return bytes(pdf.output())
