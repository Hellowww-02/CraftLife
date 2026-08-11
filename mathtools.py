# -*- coding: utf-8 -*-
"""
mathtools.py — Deteksi & konversi ekspresi matematika (LaTeX → Unicode).

Modul murni tanpa Qt sehingga bisa diuji di test_core.py (headless).
Dipakai oleh NotesPage:
  - Auto-konversi saat paste teks berisi LaTeX
  - Tombol konversi di toolbar math.
  - Pratinjau render mathtext (matplotlib) via find_math_chunks().

FIX 5: Coverage diperluas hingga >200 simbol LaTeX populer,
termasuk semua Greek, operators AMS, arrows, delimiters, functions,
dan penanganan \\mathbb, \\mathbf, \\mathcal, spacing, dll.
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
    # Arrows (panjang dulu)
    "\\Leftrightarrow": "⇔", "\\Longleftrightarrow": "⟺",
    "\\leftrightarrow": "↔", "\\longleftrightarrow": "⟷",
    "\\Longrightarrow": "⟹", "\\Longleftarrow": "⟸",
    "\\Rightarrow": "⇒", "\\Leftarrow": "⇐",
    "\\longrightarrow": "⟶", "\\longleftarrow": "⟵",
    "\\rightarrow": "→", "\\leftarrow": "←",
    "\\hookrightarrow": "↪", "\\hookleftarrow": "↩",
    "\\rightharpoonup": "⇀", "\\rightharpoondown": "⇁",
    "\\leftharpoonup": "↼", "\\leftharpoondown": "↽",
    "\\mapsto": "↦", "\\longmapsto": "⟼",
    "\\nearrow": "↗", "\\searrow": "↘", "\\swarrow": "↙", "\\nwarrow": "↖",
    "\\uparrow": "↑", "\\downarrow": "↓", "\\updownarrow": "↕",
    "\\Uparrow": "⇑", "\\Downarrow": "⇓", "\\Updownarrow": "⇕",
    "\\iff": "⇔", "\\implies": "⇒", "\\impliedby": "⇐",

    # Dots & ellipsis
    "\\ldots": "…", "\\cdots": "⋯", "\\vdots": "⋮", "\\ddots": "⋱", "\\dots": "…",
    "\\dotsc": "…", "\\dotsb": "⋯", "\\dotsm": "⋯", "\\dotso": "…",

    # Binary operators
    "\\cdot": "⋅", "\\times": "×", "\\div": "÷", "\\pm": "±", "\\mp": "∓",
    "\\ast": "∗", "\\star": "⋆", "\\circ": "∘", "\\bullet": "•", "\\bigcirc": "○",
    "\\diamond": "⋄", "\\bigtriangleup": "△", "\\bigtriangledown": "▽",
    "\\oplus": "⊕", "\\ominus": "⊖", "\\otimes": "⊗", "\\oslash": "⊘", "\\odot": "⊙",
    "\\uplus": "⊎", "\\sqcap": "⊓", "\\sqcup": "⊔",
    "\\vee": "∨", "\\wedge": "∧", "\\cap": "∩", "\\cup": "∪",
    "\\dagger": "†", "\\ddagger": "‡", "\\wr": "≀", "\\amalg": "∐",
    "\\lhd": "⊲", "\\rhd": "⊳", "\\unlhd": "⊴", "\\unrhd": "⊵",
    "\\Box": "□", "\\Diamond": "◇",

    # Relations
    "\\leq": "≤", "\\le": "≤", "\\geq": "≥", "\\ge": "≥",
    "\\neq": "≠", "\\ne": "≠", "\\approx": "≈", "\\simeq": "≃", "\\cong": "≅", "\\asymp": "≍",
    "\\equiv": "≡", "\\propto": "∝", "\\sim": "∼",
    "\\ll": "≪", "\\gg": "≫", "\\prec": "≺", "\\succ": "≻",
    "\\preceq": "⪯", "\\succeq": "⪰", "\\preccurlyeq": "≼", "\\succcurlyeq": "≽",
    "\\subset": "⊂", "\\supset": "⊃", "\\subseteq": "⊆", "\\supseteq": "⊇",
    "\\sqsubset": "⊏", "\\sqsupset": "⊐", "\\sqsubseteq": "⊑", "\\sqsupseteq": "⊒",
    "\\in": "∈", "\\notin": "∉", "\\ni": "∋", "\\owns": "∋",
    "\\mid": "∣", "\\nmid": "∤", "\\parallel": "∥", "\\nparallel": "∦",
    "\\perp": "⊥", "\\bowtie": "⋈", "\\Join": "⋈", "\\smile": "⌣", "\\frown": "⌢",
    "\\models": "⊨", "\\vdash": "⊢", "\\dashv": "⊣",
    "\\leqq": "≦", "\\geqq": "≧", "\\leqslant": "≤", "\\geqslant": "≥",
    "\\subsetneq": "⊊", "\\supsetneq": "⊋", "\\subseteqq": "⫅", "\\supseteqq": "⫆",

    # Big operators
    "\\sum": "∑", "\\prod": "∏", "\\coprod": "∐", "\\int": "∫", "\\iint": "∬", "\\iiint": "∭", "\\oint": "∮", "\\bigoint": "∮",
    "\\bigcup": "⋃", "\\bigcap": "⋂", "\\bigsqcup": "⨆", "\\biguplus": "⨄",
    "\\bigvee": "⋁", "\\bigwedge": "⋀", "\\bigoplus": "⨁", "\\bigotimes": "⨂", "\\bigodot": "⨀",

    # Set & logic
    "\\emptyset": "∅", "\\varnothing": "∅", "\\setminus": "∖",
    "\\forall": "∀", "\\exists": "∃", "\\nexists": "∄", "\\neg": "¬", "\\lnot": "¬",
    "\\land": "∧", "\\lor": "∨", "\\top": "⊤", "\\bot": "⊥",

    # Geometry & misc
    "\\angle": "∠", "\\measuredangle": "∡", "\\sphericalangle": "∢",
    "\\perp": "⊥", "\\parallel": "∥", "\\deg": "°", "\\prime": "′", "\\backprime": "‵",
    "\\hbar": "ℏ", "\\hslash": "ℏ", "\\ell": "ℓ", "\\wp": "℘", "\\Re": "ℜ", "\\Im": "ℑ", "\\mho": "℧",
    "\\aleph": "ℵ", "\\beth": "ℶ", "\\gimel": "ℷ", "\\daleth": "ℸ",
    "\\imath": "ı", "\\jmath": "ȷ", "\\eth": "ð", "\\clubsuit": "♣", "\\diamondsuit": "♦", "\\heartsuit": "♥", "\\spadesuit": "♠",
    "\\flat": "♭", "\\natural": "♮", "\\sharp": "♯", "\\surd": "√",
    "\\infty": "∞", "\\partial": "∂", "\\nabla": "∇", "\\triangle": "△", "\\Delta": "Δ",
    "\\Box": "□", "\\Diamond": "◇", "\\neg": "¬",

    # Greek lower
    "\\alpha": "α", "\\beta": "β", "\\gamma": "γ", "\\delta": "δ",
    "\\epsilon": "ε", "\\varepsilon": "ε", "\\zeta": "ζ", "\\eta": "η",
    "\\theta": "θ", "\\vartheta": "ϑ", "\\iota": "ι", "\\kappa": "κ",
    "\\lambda": "λ", "\\mu": "μ", "\\nu": "ν", "\\xi": "ξ",
    "\\pi": "π", "\\varpi": "ϖ", "\\rho": "ρ", "\\varrho": "ϱ", "\\sigma": "σ", "\\varsigma": "ς", "\\tau": "τ",
    "\\upsilon": "υ", "\\phi": "φ", "\\varphi": "φ", "\\chi": "χ",
    "\\psi": "ψ", "\\omega": "ω",
    # Greek upper
    "\\Gamma": "Γ", "\\Delta": "Δ", "\\Theta": "Θ", "\\Lambda": "Λ",
    "\\Xi": "Ξ", "\\Pi": "Π", "\\Sigma": "Σ", "\\Phi": "Φ",
    "\\Psi": "Ψ", "\\Omega": "Ω", "\\Upsilon": "Υ",

    # Functions (→ plain text)
    "\\arcsin": "arcsin", "\\arccos": "arccos", "\\arctan": "arctan",
    "\\arcsec": "arcsec", "\\arccsc": "arccsc", "\\arccot": "arccot",
    "\\sinh": "sinh", "\\cosh": "cosh", "\\tanh": "tanh", "\\coth": "coth",
    "\\log": "log", "\\ln": "ln", "\\lg": "lg",
    "\\sin": "sin", "\\cos": "cos", "\\tan": "tan",
    "\\sec": "sec", "\\csc": "csc", "\\cot": "cot",
    "\\lim": "lim", "\\liminf": "liminf", "\\limsup": "limsup",
    "\\min": "min", "\\max": "max", "\\sup": "sup", "\\inf": "inf",
    "\\exp": "exp", "\\det": "det", "\\gcd": "gcd", "\\mod": "mod", "\\bmod": "bmod", "\\pmod": "pmod",
    "\\arg": "arg", "\\dim": "dim", "\\hom": "hom", "\\ker": "ker", "\\deg": "deg",

    # Delimiters / brackets unicode
    "\\langle": "⟨", "\\rangle": "⟩",
    "\\lfloor": "⌊", "\\rfloor": "⌋", "\\lceil": "⌈", "\\rceil": "⌉",
    "\\lbrace": "{", "\\rbrace": "}", "\\lbrack": "[", "\\rbrack": "]",
    "\\vert": "|", "\\Vert": "‖",

    # Accents / decorations → strip or simple
    "\\hat": "", "\\widehat": "", "\\tilde": "", "\\widetilde": "", "\\bar": "",
    "\\overline": "", "\\underline": "", "\\vec": "", "\\dot": "", "\\ddot": "",
    "\\check": "", "\\breve": "", "\\acute": "", "\\grave": "", "\\mathring": "",

    # Font commands → strip (keep content)
    "\\mathbb": "", "\\mathbf": "", "\\mathrm": "", "\\mathit": "", "\\mathsf": "", "\\mathtt": "",
    "\\mathcal": "", "\\mathfrak": "", "\\mathscr": "", "\\mathbf": "", "\\textbf": "", "\\textit": "", "\\textrm": "",

    # Size & spacing → space or empty
    "\\left": "", "\\right": "", "\\big": "", "\\Big": "", "\\bigg": "", "\\Bigg": "",
    "\\bigl": "", "\\bigr": "", "\\bigm": "", "\\Bigl": "", "\\Bigr": "", "\\biggl": "", "\\biggr": "",
    "\\,": " ", "\\;": " ", "\\:": " ", "\\!": "", "\\ ": " ", "\\quad": "  ", "\\qquad": "   ",
    "\\enspace": " ", "\\emsp": "  ", "\\thinspace": " ", "\\negthinspace": "", "\\medspace": " ", "\\thickspace": " ",

    # Misc escapes
    "\\%": "%", "\\&": "&", "\\#": "#", "\\$": "$", "\\_": "_",
    "\\{": "{", "\\}": "}",
    "\\text": "", "\\mbox": "", "\\hbox": "",

    # Over/under braces
    "\\overbrace": "", "\\underbrace": "", "\\overrightarrow": "→", "\\overleftarrow": "←",
    "\\xrightarrow": "→", "\\xleftarrow": "←",
}
_SYMBOL_KEYS = sorted(_SYMBOLS.keys(), key=len, reverse=True)

# Penanda bahwa sebuah teks mengandung LaTeX
_LATEX_MARKERS = (
    "\\frac", "\\cfrac", "\\dfrac", "\\tfrac", "\\binom", "\\choose", "\\sqrt", "\\sqrt[",
    "^{", "_{", "\\cdot", "\\times", "\\div", "\\pi", "\\infty",
    "\\sum", "\\prod", "\\coprod", "\\int", "\\iint", "\\iiint", "\\oint", "\\bigcup", "\\bigcap",
    "\\lim", "\\log", "\\ln", "\\sin", "\\cos", "\\tan", "\\arcsin", "\\sinh",
    "\\alpha", "\\beta", "\\gamma", "\\delta", "\\epsilon", "\\theta", "\\lambda", "\\mu", "\\sigma", "\\omega",
    "\\leq", "\\geq", "\\neq", "\\approx", "\\pm", "\\rightarrow", "\\Rightarrow", "\\Leftrightarrow",
    "\\hbar", "\\ell", "\\wp", "\\forall", "\\exists", "\\in", "\\notin", "\\subset", "\\supset",
    "\\cup", "\\cap", "\\emptyset", "\\angle", "\\perp", "\\hbar", "\\mathbb", "\\mathbf", "\\mathcal",
    "\\overline", "\\hat", "\\tilde", "\\vec", "\\langle", "\\rangle", "\\lfloor", "\\rfloor",
)


def has_latex(text: str) -> bool:
    """True bila teks kemungkinan mengandung ekspresi LaTeX."""
    if not text:
        return False
    t = text.lower()
    if "\\frac" in t or "\\cfrac" in t or "\\sqrt" in t or "^{" in t or "_{" in t:
        return True
    return any(m.lower() in t for m in _LATEX_MARKERS)


def _to_sup(inner: str) -> str:
    return "".join(_SUPERS.get(ch, ch) for ch in inner)


def _to_sub(inner: str) -> str:
    return "".join(_SUBS.get(ch, ch) for ch in inner)


_SUP_BRACE_RE = re.compile(r"\^\{([^{}]*)\}")
_SUP_ONE_RE = re.compile(r"\^([0-9a-zA-Z+\-=()])")
_SUB_BRACE_RE = re.compile(r"_\{([^{}]*)\}")
_SUB_ONE_RE = re.compile(r"_([0-9a-zA-Z+\-=()])")
_CMD_RE = re.compile(r"\\(cfrac|dfrac|tfrac|frac|sqrt|binom)")

# For generic \command{...} like \mathbb{R} → R, \mathbf{x}→x
_GENERIC_CMD_RE = re.compile(r"\\(?:mathbb|mathbf|mathrm|mathit|mathsf|mathtt|mathcal|mathfrak|mathscr|textbf|textit|textrm|text|mbox|hbox)\s*\{([^{}]*)\}")

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
    """Ganti \\frac/\\dfrac/\\tfrac/\\cfrac/\\sqrt/\\binom (rekursif, nested-brace aman)."""
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
        elif cmd in ("frac", "dfrac", "tfrac", "cfrac"):
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


def _strip_generic_font_commands(text: str) -> str:
    """\\mathbb{R} -> R, \\mathbf{x} -> x etc."""
    # Iteratif karena nested
    for _ in range(5):
        new = _GENERIC_CMD_RE.sub(r"\1", text)
        if new == text:
            break
        text = new
    return text


def latex_to_unicode(text: str, _depth: int = 0) -> str:
    """Konversi LaTeX sederhana ke karakter Unicode matematika.

    Cakupan diperluas: \\frac/\\cfrac/\\dfrac/\\tfrac, \\sqrt[n]{}, \\binom, pangkat & indeks
    (^{..}/^x/_{..}/_x), huruf Yunani & simbol umum AMS, panah, delimiter, fungsi.
    Bukan parser LaTeX penuh — di luar cakupan teks dibiarkan apa adanya (aman).
    """
    if not text or _depth > 8:
        return text
    # 0) Strip font wrappers like \mathbb{R}
    out = _strip_generic_font_commands(text)
    # 1) Perintah berstruktur (nested-brace aman via depth scanner)
    out = _convert_commands(out, _depth)

    # Handle \choose: {n \choose k} -> C(n,k)
    # Pattern: {inner \choose inner}
    # Simple: replace "\choose" with ","
    # We'll handle two forms: \binom already done; also handle {a \choose b}
    out = re.sub(r"\{\s*([^{}]+?)\s*\\choose\s+([^{}]+?)\s*\}", r"C(\1,\2)", out)
    out = re.sub(r"([^\s{}]+)\s*\\choose\s+([^\s{}]+)", r"C(\1,\2)", out)

    # Handle \overline, \underline, \hat etc wrapping: \overline{abc} -> abc
    out = re.sub(r"\\(?:overline|underline|hat|widehat|tilde|widetilde|bar|vec|dot|ddot|check|breve|acute|grave|mathring)\s*\{([^{}]*)\}", r"\1", out)
    out = re.sub(r"\\(?:overbrace|underbrace)\s*\{([^{}]*)\}", r"\1", out)

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

    # 4) Perintah tak dikenal \something → teks polos 'something' (tapi preserve angka)
    out = re.sub(r"\\([a-zA-Z]+)", r"\1", out)
    # Cleanup sisa braces ganda? keep single braces for readability
    out = out.replace("{", "").replace("}", "")
    # Normalize whitespace
    out = re.sub(r"[ \t]{2,}", " ", out)
    return out.strip()


# Regex chunk untuk pratinjau render: potongan yang mengandung perintah LaTeX
_CHUNK_RE = re.compile(
    r"\\[a-zA-Z]+\s*(?:\[[^\]]*\])?\s*\{[^{}]*(\{[^{}]*\}[^{}]*)*\}\s*\{[^{}]*(\{[^{}]*\}[^{}]*)*\}"  # \cmd{ }{ }
    r"|\\[a-zA-Z]+\s*(?:\[[^\]]*\])?\s*\{[^{}]*(\{[^{}]*\}[^{}]*)*\}"  # \cmd{ }
    r"|\\[a-zA-Z]+"  # \cmd
    r"|[^\\s]*\^\{[^{}]*\}[^\\s]*"  # ^{ }
    r"|[^\\s]*_\{[^{}]*\}[^\\s]*"  # _{ }
    r"|\^[0-9a-zA-Z]"  # ^x
    r"|_[0-9a-zA-Z]"  # _x
)


def find_math_chunks(text: str) -> list:
    """Ambil potongan-potongan ekspresi LaTeX dari teks (untuk pratinjau render
    mathtext). Mengembalikan list string unik, urut kemunculan."""
    if not text or not has_latex(text):
        return []
    seen, out = set(), []
    for m in _CHUNK_RE.finditer(text):
        chunk = m.group(0).strip(" \t,.;:!?()[]\"'")
        if not chunk or len(chunk) < 2:
            continue
        if not has_latex(chunk):
            continue
        if chunk not in seen:
            seen.add(chunk)
            out.append(chunk)
    # Fallback: if none found but has_latex True, return whole text as one chunk
    if not out and has_latex(text):
        return [text.strip()[:200]]
    return out
