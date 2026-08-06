# -*- coding: utf-8 -*-
"""
mathtools.py — Deteksi & konversi ekspresi matematika (LaTeX → Unicode).

Modul murni tanpa Qt sehingga bisa diuji di test_core.py (headless).
Dipakai oleh NotesPage:
  - Auto-konversi saat paste teks berisi LaTeX (masalah yang dilaporkan user:
    hasil copy "…\\frac{2^5\\cdot2^{-3}}{2^2}…" tampil mentah, bukan sebagai
    kalimat matematika).
  - Tombol konversi di toolbar math.
  - Pratinjau render mathtext (matplotlib) via find_math_chunks().
"""

import re

# ─────────────────────────────── Superskrip / subskrip ─────────────────────
_SUPERS = {
    "0": "⁰", "1": "¹", "2": "²", "3": "³", "4": "⁴",
    "5": "⁵", "6": "⁶", "7": "⁷", "8": "⁸", "9": "⁹",
    "+": "⁺", "-": "⁻", "=": "⁼", "(": "⁽", ")": "⁾",
    "a": "ᵃ", "b": "ᵇ", "c": "ᶜ", "d": "ᵈ", "e": "ᵉ", "f": "ᶠ",
    "g": "ᵍ", "h": "ʰ", "i": "ⁱ", "j": "ʲ", "k": "ᵏ", "l": "ˡ",
    "m": "ᵐ", "n": "ⁿ", "o": "ᵒ", "p": "ᵖ", "r": "ʳ", "s": "ˢ",
    "t": "ᵗ", "u": "ᵘ", "v": "ᵛ", "w": "ʷ", "x": "ˣ", "y": "ʸ", "z": "ᶻ",
}
_SUBS = {
    "0": "₀", "1": "₁", "2": "₂", "3": "₃", "4": "₄",
    "5": "₅", "6": "₆", "7": "₇", "8": "₈", "9": "₉",
    "+": "₊", "-": "₋", "=": "₌", "(": "₍", ")": "₎",
    "a": "ₐ", "e": "ₑ", "h": "ₕ", "i": "ᵢ", "j": "ⱼ", "k": "ₖ",
    "l": "ₗ", "m": "ₘ", "n": "ₙ", "o": "ₒ", "p": "ₚ", "r": "ᵣ",
    "s": "ₛ", "t": "ₜ", "u": "ᵤ", "v": "ᵥ", "x": "ₓ",
}

# ─────────────────────────────── Simbol LaTeX → Unicode ────────────────────
# Urutan penting: diproses terpanjang dulu (lihat _SYMBOL_KEYS).
_SYMBOLS = {
    "\\leftrightarrow": "↔", "\\Leftrightarrow": "⇔",
    "\\rightarrow": "→", "\\Rightarrow": "⇒",
    "\\leftarrow": "←", "\\Leftarrow": "⇐",
    "\\ldots": "…", "\\cdots": "⋯", "\\dots": "…",
    "\\cdot": "⋅", "\\times": "×", "\\div": "÷", "\\pm": "±", "\\mp": "∓",
    "\\ast": "∗", "\\star": "⋆", "\\circ": "∘",
    "\\leq": "≤", "\\geq": "≥", "\\neq": "≠", "\\approx": "≈",
    "\\equiv": "≡", "\\propto": "∝", "\\sim": "∼", "\\cong": "≅",
    "\\infty": "∞", "\\partial": "∂", "\\nabla": "∇", "\\aleph": "ℵ",
    "\\sum": "∑", "\\prod": "∏", "\\int": "∫", "\\oint": "∮",
    "\\in": "∈", "\\notin": "∉", "\\ni": "∋",
    "\\subset": "⊂", "\\supset": "⊃", "\\subseteq": "⊆", "\\supseteq": "⊇",
    "\\cup": "∪", "\\cap": "∩", "\\emptyset": "∅", "\\setminus": "∖",
    "\\forall": "∀", "\\exists": "∃", "\\neg": "¬",
    "\\land": "∧", "\\lor": "∨", "\\oplus": "⊕", "\\otimes": "⊗",
    "\\angle": "∠", "\\perp": "⊥", "\\parallel": "∥", "\\deg": "°",
    "\\alpha": "α", "\\beta": "β", "\\gamma": "γ", "\\delta": "δ",
    "\\epsilon": "ε", "\\varepsilon": "ε", "\\zeta": "ζ", "\\eta": "η",
    "\\theta": "θ", "\\vartheta": "ϑ", "\\iota": "ι", "\\kappa": "κ",
    "\\lambda": "λ", "\\mu": "μ", "\\nu": "ν", "\\xi": "ξ",
    "\\pi": "π", "\\rho": "ρ", "\\sigma": "σ", "\\tau": "τ",
    "\\upsilon": "υ", "\\phi": "φ", "\\varphi": "φ", "\\chi": "χ",
    "\\psi": "ψ", "\\omega": "ω",
    "\\Gamma": "Γ", "\\Delta": "Δ", "\\Theta": "Θ", "\\Lambda": "Λ",
    "\\Xi": "Ξ", "\\Pi": "Π", "\\Sigma": "Σ", "\\Phi": "Φ",
    "\\Psi": "Ψ", "\\Omega": "Ω",
    # Fungsi bernama → teks biasa
    "\\log": "log", "\\ln": "ln", "\\lg": "lg",
    "\\sin": "sin", "\\cos": "cos", "\\tan": "tan",
    "\\sec": "sec", "\\csc": "csc", "\\cot": "cot",
    "\\lim": "lim", "\\min": "min", "\\max": "max", "\\sup": "sup", "\\inf": "inf",
    "\\exp": "exp", "\\det": "det", "\\gcd": "gcd", "\\mod": "mod",
    # Escape karakter & spasi
    "\\%": "%", "\\&": "&", "\\#": "#", "\\$": "$", "\\_": "_",
    "\\{": "{", "\\}": "}",
    "\\left": "", "\\right": "",
    "\\,": " ", "\\;": " ", "\\:": " ", "\\!": "", "\\ ": " ",
}
_SYMBOL_KEYS = sorted(_SYMBOLS.keys(), key=len, reverse=True)

# Penanda bahwa sebuah teks mengandung LaTeX
_LATEX_MARKERS = (
    "\\frac", "\\sqrt", "\\dfrac", "\\tfrac", "\\binom", "\\sqrt[",
    "^{", "_{", "\\cdot", "\\times", "\\div", "\\pi", "\\infty",
    "\\sum", "\\prod", "\\int", "\\lim", "\\log", "\\ln",
    "\\sin", "\\cos", "\\tan", "\\alpha", "\\beta", "\\gamma", "\\delta",
    "\\theta", "\\lambda", "\\mu", "\\sigma", "\\omega", "\\leq", "\\geq",
    "\\neq", "\\approx", "\\pm", "\\rightarrow", "\\Rightarrow",
)


def has_latex(text: str) -> bool:
    """True bila teks kemungkinan mengandung ekspresi LaTeX."""
    if not text:
        return False
    t = text.lower()
    if "\\frac" in t or "\\sqrt" in t or "^{" in t or "_{" in t:
        return True
    return any(m in t for m in _LATEX_MARKERS)


def _to_sup(inner: str) -> str:
    return "".join(_SUPERS.get(ch, ch) for ch in inner)


def _to_sub(inner: str) -> str:
    return "".join(_SUBS.get(ch, ch) for ch in inner)


_SUP_BRACE_RE = re.compile(r"\^\{([^{}]*)\}")
_SUP_ONE_RE = re.compile(r"\^([0-9a-zA-Z+\-=()])")
_SUB_BRACE_RE = re.compile(r"_\{([^{}]*)\}")
_SUB_ONE_RE = re.compile(r"_([0-9a-zA-Z+\-=()])")
_CMD_RE = re.compile(r"\\(dfrac|tfrac|frac|sqrt|binom)")


def _ws(text: str, j: int) -> int:
    """Lewati spasi/tab mulai dari posisi j."""
    while j < len(text) and text[j] in " \t":
        j += 1
    return j


def _extract_braced(text: str, start: int):
    """Ambil isi grup {..} mulai dari start (harus '{') dengan depth counter —
    aman untuk nested braces. Return (inner, idx_setelah_'}') atau (None, start)."""
    if start >= len(text) or text[start] != "{":
        return None, start
    depth = 0
    for i in range(start, len(text)):
        if text[i] == "{":
            depth += 1
        elif text[i] == "}":
            depth -= 1
            if depth == 0:
                return text[start + 1:i], i + 1
    return None, start


def _convert_commands(out: str, _depth: int) -> str:
    """Ganti \\frac/\\dfrac/\\tfrac/\\sqrt/\\binom (rekursif, nested-brace aman)."""
    i, parts = 0, []
    while i < len(out):
        m = _CMD_RE.search(out, i)
        if not m:
            parts.append(out[i:])
            break
        parts.append(out[i:m.start()])
        cmd, j = m.group(1), _ws(out, m.end())

        if cmd == "sqrt":
            idx = None
            if j < len(out) and out[j] == "[":
                k = out.find("]", j)
                if k != -1:
                    idx, j = out[j + 1:k], _ws(out, k + 1)
            inner, j2 = _extract_braced(out, j)
            if inner is None:
                parts.append(out[m.start():m.end()])
                i = m.end()
                continue
            conv = latex_to_unicode(inner, _depth + 1)
            if idx is not None:
                parts.append(f"{_to_sup(latex_to_unicode(idx.strip(), _depth + 1))}√({conv})")
            else:
                parts.append(f"√({conv})")
            i = j2
        elif cmd in ("frac", "dfrac", "tfrac"):
            num, j2 = _extract_braced(out, j)
            if num is None:
                parts.append(out[m.start():m.end()])
                i = m.end()
                continue
            den, j3 = _extract_braced(out, _ws(out, j2))
            if den is None:
                parts.append(out[m.start():m.end()])
                i = m.end()
                continue
            parts.append(
                f"({latex_to_unicode(num.strip(), _depth + 1)})⁄({latex_to_unicode(den.strip(), _depth + 1)})")
            i = j3
        else:  # binom
            a, j2 = _extract_braced(out, j)
            if a is None:
                parts.append(out[m.start():m.end()])
                i = m.end()
                continue
            b, j3 = _extract_braced(out, _ws(out, j2))
            if b is None:
                parts.append(out[m.start():m.end()])
                i = m.end()
                continue
            parts.append(
                f"C({latex_to_unicode(a.strip(), _depth + 1)},{latex_to_unicode(b.strip(), _depth + 1)})")
            i = j3
    return "".join(parts)


def latex_to_unicode(text: str, _depth: int = 0) -> str:
    """Konversi LaTeX sederhana ke karakter Unicode matematika.

    Cakupan: \\frac/\\dfrac/\\tfrac, \\sqrt[n]{}, \\binom, pangkat & indeks
    (^{..}/^x/_{..}/_x), huruf Yunani & simbol umum. Bukan parser LaTeX penuh —
    di luar cakupan teks dibiarkan apa adanya (aman, tidak merusak).
    """
    if not text or _depth > 6:
        return text
    # 1) Perintah berstruktur (nested-brace aman via depth scanner)
    out = _convert_commands(text, _depth)

    # 2) Pangkat & indeks
    out = _SUP_BRACE_RE.sub(
        lambda m: _to_sup(latex_to_unicode(m.group(1), _depth + 1)), out)
    out = _SUP_ONE_RE.sub(lambda m: _to_sup(m.group(1)), out)
    out = _SUB_BRACE_RE.sub(
        lambda m: _to_sub(latex_to_unicode(m.group(1), _depth + 1)), out)
    out = _SUB_ONE_RE.sub(lambda m: _to_sub(m.group(1)), out)

    # 3) Simbol (terpanjang dulu agar \leq tidak kepotong \le dst.)
    for key in _SYMBOL_KEYS:
        if key in out:
            out = out.replace(key, _SYMBOLS[key])

    # 4) Perintah tak dikenal \something → teks polos 'something'
    out = re.sub(r"\\([a-zA-Z]+)", r"\1", out)
    return out


# Regex chunk untuk pratinjau render: potongan yang mengandung perintah LaTeX
_CHUNK_RE = re.compile(
    r"\\[dt]?frac\s*\{[^{}]*(\{[^{}]*\}[^{}]*)*\}\s*\{[^{}]*(\{[^{}]*\}[^{}]*)*\}"  # \frac (dgn 1 nested)
    r"|\\sqrt\s*(\[[^\]]*\])?\s*\{[^{}]*(\{[^{}]*\}[^{}]*)*\}"                      # \sqrt
    r"|[^\s]*(?:\\[a-zA-Z]+(?:\[[^\]]*\])?|\^\{[^{}]*\}|_\{[^{}]*\}|\^[0-9a-zA-Z]|_[0-9a-zA-Z])[^\s]*"  # token campuran
)


def find_math_chunks(text: str) -> list:
    """Ambil potongan-potongan ekspresi LaTeX dari teks (untuk pratinjau render
    mathtext). Mengembalikan list string unik, urut kemunculan."""
    if not text or not has_latex(text):
        return []
    seen, out = set(), []
    for m in _CHUNK_RE.finditer(text):
        chunk = m.group(0).strip(" \t,.;:!?()[]\"'")
        if not chunk or not has_latex(chunk):
            continue
        if chunk not in seen:
            seen.add(chunk)
            out.append(chunk)
    return out
