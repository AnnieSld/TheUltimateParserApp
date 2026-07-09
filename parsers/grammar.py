"""Grammar representation and analysis utilities shared by every parser.

Handles: parsing grammar text, FIRST/FOLLOW sets, nullable symbols,
left-recursion detection/elimination and left-factoring — the building
blocks every parser (top-down or bottom-up) in this app relies on.
"""
from __future__ import annotations

from dataclasses import dataclass, field

EPSILON = "ε"          # ε
END = "$"                   # end-of-input marker
DOT = "•"              # • (used only for display of LR items)
ARROW = "→"            # →

EPSILON_ALIASES = {EPSILON, "epsilon", "eps", "lambda", "λ", ""}


class GrammarError(ValueError):
    """Raised when the grammar text cannot be parsed or is unusable."""


@dataclass(frozen=True)
class Production:
    index: int
    head: str
    body: tuple  # tuple[str, ...], EPSILON alone means empty body

    def __str__(self) -> str:
        rhs = " ".join(self.body) if self.body != (EPSILON,) else EPSILON
        return f"{self.head} {ARROW} {rhs}"

    @property
    def is_epsilon(self) -> bool:
        return self.body == (EPSILON,)


@dataclass
class Grammar:
    start_symbol: str
    productions: list  # list[Production]
    terminals: set = field(default_factory=set)
    nonterminals: set = field(default_factory=set)

    # ------------------------------------------------------------------
    # Parsing grammar text
    # ------------------------------------------------------------------
    @classmethod
    def parse(cls, text: str) -> "Grammar":
        lines = [ln.strip() for ln in text.splitlines()]
        lines = [ln for ln in lines if ln and not ln.startswith("#")]
        if not lines:
            raise GrammarError("La gramática está vacía.")

        # Pass 1: split each rule into (head, [raw alternative strings]) and
        # collect every declared nonterminal (every left-hand side). We need
        # the *complete* set before tokenizing bodies, so a nonterminal used
        # on the right-hand side of an earlier rule is still recognized.
        raw_rules = []
        nonterminals = set()
        first_head = None

        for ln in lines:
            if ARROW in ln:
                sep = ARROW
            elif "->" in ln:
                sep = "->"
            elif "::=" in ln:
                sep = "::="
            else:
                raise GrammarError(
                    f"No se encontró '->' ni '{ARROW}' en la línea: {ln!r}"
                )
            head, _, rhs = ln.partition(sep)
            head = head.strip()
            if not head:
                raise GrammarError(f"Falta el no terminal (lado izquierdo) en: {ln!r}")
            if first_head is None:
                first_head = head
            nonterminals.add(head)

            alts = [alt.strip() for alt in rhs.split("|")]
            raw_rules.append((head, alts))

        # Pass 2: tokenize each alternative. Symbols separated by whitespace
        # are always taken as-is (this is what lets multi-character terminals
        # like `id`, `then`, `else` work). Within a single whitespace-free
        # word, any declared nonterminal name found inside it is peeled off
        # as its own symbol (longest name first) — this is what makes the
        # very common single-letter style `S -> AB`, `A -> aA` work exactly
        # like `S -> A B`, `A -> a A` without requiring the user to space
        # every symbol out by hand.
        nts_by_len_desc = sorted(nonterminals, key=len, reverse=True)

        def segment_word(word: str):
            if word in nonterminals:
                return [word]
            tokens = []
            pending = ""
            i, n = 0, len(word)
            while i < n:
                match = next((nt for nt in nts_by_len_desc if word.startswith(nt, i)), None)
                if match:
                    if pending:
                        tokens.append(pending)
                        pending = ""
                    tokens.append(match)
                    i += len(match)
                else:
                    pending += word[i]
                    i += 1
            if pending:
                tokens.append(pending)
            return tokens

        def tokenize_alt(alt: str):
            if alt.strip() in EPSILON_ALIASES:
                return [EPSILON]
            tokens = []
            for word in alt.split():
                tokens.extend(segment_word(word))
            return tokens

        productions = []
        idx = 0
        for head, alts in raw_rules:
            for alt in alts:
                productions.append(Production(idx, head, tuple(tokenize_alt(alt))))
                idx += 1

        terminals = set()
        for p in productions:
            for sym in p.body:
                if sym == EPSILON:
                    continue
                if sym not in nonterminals:
                    terminals.add(sym)

        if terminals & nonterminals:
            raise GrammarError("Un símbolo no puede ser terminal y no terminal a la vez.")

        g = cls(
            start_symbol=first_head,
            productions=productions,
            terminals=terminals,
            nonterminals=nonterminals,
        )
        g.validate()
        return g

    def validate(self) -> None:
        if self.start_symbol not in self.nonterminals:
            raise GrammarError("No se pudo determinar el símbolo inicial.")
        for p in self.productions:
            if p.head not in self.nonterminals:
                raise GrammarError(f"No terminal desconocido: {p.head}")

    # ------------------------------------------------------------------
    # Basic queries
    # ------------------------------------------------------------------
    def productions_for(self, nonterminal: str):
        return [p for p in self.productions if p.head == nonterminal]

    def to_text(self) -> str:
        by_head = {}
        for p in self.productions:
            by_head.setdefault(p.head, []).append(p)
        lines = []
        for head, prods in by_head.items():
            alts = " | ".join(
                (EPSILON if p.is_epsilon else " ".join(p.body)) for p in prods
            )
            lines.append(f"{head} {ARROW} {alts}")
        return "\n".join(lines)

    # ------------------------------------------------------------------
    # Augmentation (needed by every LR-family parser)
    # ------------------------------------------------------------------
    def augmented(self) -> "Grammar":
        new_start = self.start_symbol + "'"
        while new_start in self.nonterminals:
            new_start += "'"
        new_prod = Production(0, new_start, (self.start_symbol,))
        shifted = [
            Production(i + 1, p.head, p.body) for i, p in enumerate(self.productions)
        ]
        return Grammar(
            start_symbol=new_start,
            productions=[new_prod] + shifted,
            terminals=set(self.terminals),
            nonterminals=set(self.nonterminals) | {new_start},
        )

    # ------------------------------------------------------------------
    # FIRST / FOLLOW / nullable
    # ------------------------------------------------------------------
    def compute_nullable(self) -> set:
        nullable = set()
        changed = True
        while changed:
            changed = False
            for p in self.productions:
                if p.head in nullable:
                    continue
                if p.is_epsilon or all(sym in nullable for sym in p.body):
                    nullable.add(p.head)
                    changed = True
        return nullable

    def compute_first(self):
        nullable = self.compute_nullable()
        first = {t: {t} for t in self.terminals}
        first[EPSILON] = {EPSILON}
        for nt in self.nonterminals:
            first[nt] = set()

        changed = True
        while changed:
            changed = False
            for p in self.productions:
                before = len(first[p.head])
                first[p.head] |= self._first_of_sequence(p.body, first, nullable)
                if len(first[p.head]) > before:
                    changed = True
        return first

    @staticmethod
    def _first_of_sequence(seq, first, nullable) -> set:
        result = set()
        if not seq or seq == (EPSILON,):
            return {EPSILON}
        all_nullable = True
        for sym in seq:
            if sym == EPSILON:
                continue
            result |= (first.get(sym, {sym}) - {EPSILON})
            if sym not in nullable:
                all_nullable = False
                break
        if all_nullable:
            result.add(EPSILON)
        return result

    def first_of_sequence(self, seq, first=None, nullable=None) -> set:
        first = first or self.compute_first()
        nullable = nullable if nullable is not None else self.compute_nullable()
        return self._first_of_sequence(tuple(seq), first, nullable)

    def compute_follow(self, first=None):
        first = first or self.compute_first()
        nullable = self.compute_nullable()
        follow = {nt: set() for nt in self.nonterminals}
        follow[self.start_symbol].add(END)

        changed = True
        while changed:
            changed = False
            for p in self.productions:
                body = p.body
                for i, sym in enumerate(body):
                    if sym not in self.nonterminals:
                        continue
                    rest = body[i + 1 :]
                    first_rest = self._first_of_sequence(rest, first, nullable)
                    before = len(follow[sym])
                    follow[sym] |= (first_rest - {EPSILON})
                    if EPSILON in first_rest or not rest:
                        follow[sym] |= follow[p.head]
                    if len(follow[sym]) > before:
                        changed = True
        return follow

    # ------------------------------------------------------------------
    # Diagnostics used by the AI-heuristics module
    # ------------------------------------------------------------------
    def direct_left_recursive_nonterminals(self):
        result = []
        for nt in self.nonterminals:
            for p in self.productions_for(nt):
                if p.body and p.body[0] == nt:
                    result.append(nt)
                    break
        return result

    def indirect_left_recursive_pairs(self):
        """Very small fixed-point search for A =>+ A... (indirect left recursion)."""
        nullable = self.compute_nullable()
        reaches = {nt: set() for nt in self.nonterminals}
        for p in self.productions:
            if p.body:
                for sym in p.body:
                    if sym not in self.nonterminals:
                        break
                    reaches[p.head].add(sym)
                    if sym not in nullable:
                        break
        changed = True
        while changed:
            changed = False
            for nt in self.nonterminals:
                new = set()
                for r in reaches[nt]:
                    new |= reaches.get(r, set())
                before = len(reaches[nt])
                reaches[nt] |= new
                if len(reaches[nt]) > before:
                    changed = True
        return [nt for nt in self.nonterminals if nt in reaches[nt]]

    def eliminate_left_recursion(self) -> "Grammar":
        """Standard textbook algorithm (direct recursion only, no cycles)."""
        order = sorted(self.nonterminals)
        by_head = {nt: [list(p.body) for p in self.productions_for(nt)] for nt in order}

        for i, ai in enumerate(order):
            for aj in order[:i]:
                new_rules = []
                for body in by_head[ai]:
                    if body and body[0] == aj:
                        for other in by_head[aj]:
                            replacement = (other if other != [EPSILON] else []) + body[1:]
                            new_rules.append(replacement if replacement else [EPSILON])
                    else:
                        new_rules.append(body)
                by_head[ai] = new_rules

            alpha, beta = [], []
            for body in by_head[ai]:
                if body and body[0] == ai:
                    alpha.append(body[1:])
                else:
                    beta.append(body)
            if alpha:
                new_nt = ai + "'"
                while new_nt in order or new_nt in by_head:
                    new_nt += "'"
                by_head[ai] = [b + [new_nt] for b in beta] if beta else [[new_nt]]
                by_head[new_nt] = [a + [new_nt] for a in alpha] + [[EPSILON]]
                order.append(new_nt)

        productions = []
        idx = 0
        nonterminals = set(order)
        for nt in order:
            for body in by_head[nt]:
                productions.append(Production(idx, nt, tuple(body)))
                idx += 1
        return Grammar(
            start_symbol=self.start_symbol,
            productions=productions,
            terminals=set(self.terminals),
            nonterminals=nonterminals,
        )

    def left_factor(self) -> "Grammar":
        """Repeated common-prefix factoring, textbook algorithm."""
        by_head = {}
        order = []
        for p in self.productions:
            by_head.setdefault(p.head, []).append(list(p.body))
            if p.head not in order:
                order.append(p.head)

        changed = True
        counter = 0
        while changed:
            changed = False
            for nt in list(order):
                bodies = by_head[nt]
                prefix_map = {}
                for body in bodies:
                    first_sym = body[0] if body and body[0] != EPSILON else None
                    prefix_map.setdefault(first_sym, []).append(body)
                needs_factor = {k: v for k, v in prefix_map.items() if k is not None and len(v) > 1}
                if not needs_factor:
                    continue
                changed = True
                new_bodies = []
                for first_sym, group in prefix_map.items():
                    if first_sym is None or len(group) == 1:
                        new_bodies.extend(group)
                        continue
                    prefix_len = 1
                    while True:
                        candidate = prefix_len + 1
                        if all(len(b) >= candidate and b[candidate - 1] == group[0][candidate - 1] for b in group):
                            prefix_len = candidate
                        else:
                            break
                    counter += 1
                    new_nt = f"{nt}{counter}'"
                    while new_nt in order:
                        counter += 1
                        new_nt = f"{nt}{counter}'"
                    prefix = group[0][:prefix_len]
                    new_bodies.append(list(prefix) + [new_nt])
                    order.append(new_nt)
                    by_head[new_nt] = [
                        (b[prefix_len:] if b[prefix_len:] else [EPSILON]) for b in group
                    ]
                by_head[nt] = new_bodies

        productions = []
        idx = 0
        for nt in order:
            for body in by_head[nt]:
                productions.append(Production(idx, nt, tuple(body)))
                idx += 1
        return Grammar(
            start_symbol=self.start_symbol,
            productions=productions,
            terminals=set(self.terminals),
            nonterminals=set(order),
        )
