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

    # ── P55: operator & relasi tambahan (AMS dsb.) ──
    "\\oiint": "∯", "\\oiiint": "∰",
    "\\varsubsetneqq": "⊊", "\\varsupsetneqq": "⊋",
    "\\nleqslant": "≰", "\\ngeqslant": "≱", "\\nleq": "≰", "\\ngeq": "≱",
    "\\nsubseteq": "⊈", "\\nsupseteq": "⊉",
    "\\triangleq": "≜", "\\coloneqq": "≔", "\\eqqcolon": "≕",
    "\\lessgtr": "≶", "\\gtrless": "≷", "\\lesssim": "≲", "\\gtrsim": "≳",
    "\\circledast": "⊛", "\\circledcirc": "⊚", "\\boxdot": "⊡", "\\intercal": "⊺",
    "\\curvearrowright": "↷", "\\curvearrowleft": "↶",
    "\\circlearrowright": "↻", "\\circlearrowleft": "↺",
    "\\dashrightarrow": "⇢", "\\dashleftarrow": "⇠",
    "\\rightleftharpoons": "⇌", "\\rightrightarrows": "⇉", "\\leftleftarrows": "⇇",
    "\\nrightarrow": "↛", "\\nleftarrow": "↚", "\\nRightarrow": "⇏", "\\nLeftrightarrow": "⇎",
    "\\complement": "∁", "\\smallsetminus": "∖",
    # Kimia & fisika umum (P55)
    "\\degree": "°", "\\celsius": "℃", "\\micro": "µ", "\\angstrom": "Å", "\\AA": "Å",
    "\\Bbbk": "𝕜",
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
    "\\boldsymbol", "\\overset", "\\underset", "\\stackrel", "\\substack", "\\begin{", "\\oiint",
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
            # P55: pecahan cerdas — a/b untuk token sederhana,
            # (a+b)/(c+d) untuk ekspresi majemuk (bukan lagi (a)⁄(b) selalu).
            parts.append(
                f"{_wrap_frac(latex_to_unicode(num.strip(), _depth + 1))}"
                f"/{_wrap_frac(latex_to_unicode(den.strip(), _depth + 1))}")
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


# ── P55: dukungan tambahan ──────────────────────────────────────────────────
# Aksen → combining Unicode (ditempel SETELAH isi): \overline{x} → x̅, \vec{v} → v⃗.
_ACCENTS = {
    "overrightarrow": "⃗", "overleftarrow": "⃖",
    "overline": "̅", "underline": "̲",
    "widehat": "̂", "widetilde": "̃",
    "hat": "̂", "tilde": "̃", "bar": "̄",
    "vec": "⃗", "dot": "̇", "ddot": "̈",
    "check": "̌", "breve": "̆", "acute": "́",
    "grave": "̀", "mathring": "̊",
}
_ACCENT_RE = re.compile(
    r"\\(overrightarrow|overleftarrow|overline|underline|widehat|widetilde|"
    r"hat|tilde|bar|vec|ddot|dot|check|breve|acute|grave|mathring)\s*\{([^{}]*)\}")


def _accent_sub(_depth):
    def _sub(m):
        return latex_to_unicode(m.group(2), _depth + 1) + _ACCENTS[m.group(1)]
    return _sub


_OVERSET_RE = re.compile(r"\\(?:overset|stackrel)\s*\{([^{}]*)\}\s*\{([^{}]*)\}")
_UNDERSET_RE = re.compile(r"\\underset\s*\{([^{}]*)\}\s*\{([^{}]*)\}")
_SUBSTACK_RE = re.compile(r"\\substack\s*\{([^{}]*)\}")
_XRIGHT_RE = re.compile(r"\\xrightarrow(?:\[[^\]]*\])?\s*\{([^{}]*)\}")
_XLEFT_RE = re.compile(r"\\xleftarrow(?:\[[^\]]*\])?\s*\{([^{}]*)\}")

_ENV_DELIMS = {
    "cases": ("{", "}"), "pmatrix": ("(", ")"), "bmatrix": ("[", "]"),
    "vmatrix": ("|", "|"), "Bmatrix": ("{", "}"), "matrix": ("", ""), "array": ("", ""),
}
_ENV_RE = re.compile(r"\\begin\{(cases|pmatrix|bmatrix|vmatrix|Bmatrix|matrix|array\*?)\}(.*?)\\end\{\1\}", re.S)


def _env_sub(_depth):
    def _sub(m):
        env = m.group(1).rstrip("*")
        sep = "│" if env == "cases" else "; "
        rows = [latex_to_unicode(r.strip(), _depth + 1).replace("&", " ")
                for r in m.group(2).split("\\\\") if r.strip()]
        lo, hi = _ENV_DELIMS.get(env, ("", ""))
        # '{' asli akan dibuang oleh cleanup braces di akhir latex_to_unicode —
        # pakai placeholder lalu dipulihkan di langkah terakhir.
        if lo == "{":
            lo, hi = "\x01", "\x02"
        return lo + sep.join(rows) + hi
    return _sub


# \boldsymbol: Latin/Greek/digit → Mathematical Bold (𝐚, 𝜶, 𝟎).
_BOLD_GR = {
    "α": "𝜶", "β": "𝜷", "γ": "𝜸", "δ": "𝜹", "ε": "𝜺", "ζ": "𝜻",
    "η": "𝜼", "θ": "𝜽", "ι": "𝜾", "κ": "𝜿", "λ": "𝝀", "μ": "𝝁",
    "ν": "𝝂", "ξ": "𝝃", "π": "𝝅", "ρ": "𝝆", "σ": "𝝈", "τ": "𝝉",
    "υ": "𝝊", "φ": "𝝋", "χ": "𝝌", "ψ": "𝝍", "ω": "𝝎",
}
_BOLD_GR_U = {
    "Γ": "𝚪", "Δ": "𝚫", "Θ": "𝚯", "Λ": "𝚲", "Ξ": "𝚰", "Π": "𝚷",
    "Σ": "𝚺", "Φ": "𝚽", "Ψ": "𝚿", "Ω": "𝛀",
}
_BOLDSYMBOL_RE = re.compile(r"\\boldsymbol\s*\{([^{}]*)\}")


def _bold_char(ch):
    o = ord(ch)
    if 0x61 <= o <= 0x7A:
        return chr(0x1D41E + o - 0x61)   # a..z → 𝐚..
    if 0x41 <= o <= 0x5A:
        return chr(0x1D400 + o - 0x41)   # A..Z → 𝐀..
    if 0x30 <= o <= 0x39:
        return chr(0x1D7CE + o - 0x30)   # 0..9 → 𝟎..
    return _BOLD_GR.get(ch) or _BOLD_GR_U.get(ch) or ch


# Pecahan cerdas (P55): token atomik tanpa kurung, sisanya dibungkus.
_ATOMIC_RE = re.compile(r"^[0-9A-Za-z.]+$")


def _wrap_frac(s):
    if _ATOMIC_RE.match(s) or (s.startswith("(") and s.endswith(")")):
        return s
    return "(" + s + ")"


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

    # P55: aksen kini combining Unicode (lihat _ACCENT_RE).
    # P55: aksen sebagai COMBINING character (bukan dibuang): \overline{x} → x̅.
    out = _ACCENT_RE.sub(_accent_sub(_depth), out)
    out = re.sub(r"\\(?:overbrace|underbrace)\s*\{([^{}]*)\}", r"\1", out)

    # P55: \overset{X}{Y} / \stackrel{X}{Y} → Y + superskrip(X); \underset → subskrip.
    out = _OVERSET_RE.sub(lambda m: latex_to_unicode(m.group(2), _depth + 1)
                          + _to_sup(latex_to_unicode(m.group(1), _depth + 1)), out)
    out = _UNDERSET_RE.sub(lambda m: latex_to_unicode(m.group(2), _depth + 1)
                           + _to_sub(latex_to_unicode(m.group(1), _depth + 1)), out)
    # P55: \substack{a\\b} → superskrip bertumpuk (dipakai di limit ∑).
    out = _SUBSTACK_RE.sub(lambda m: "".join(
        _to_sup(latex_to_unicode(seg.strip(), _depth + 1))
        for seg in m.group(1).split("\\\\") if seg.strip()), out)
    # P55: \xrightarrow[text]{X} → panah panjang + superskrip(X).
    out = _XRIGHT_RE.sub(lambda m: "⟶" + _to_sup(latex_to_unicode(m.group(1), _depth + 1)), out)
    out = _XLEFT_RE.sub(lambda m: "⟵" + _to_sup(latex_to_unicode(m.group(1), _depth + 1)), out)
    # P55: environment cases & matrix → bentuk flat (baris dipisah │ / ;).
    out = _ENV_RE.sub(_env_sub(_depth), out)
    # P55: \boldsymbol{X} → Mathematical Bold.
    out = _BOLDSYMBOL_RE.sub(lambda m: "".join(
        _bold_char(c) for c in latex_to_unicode(m.group(1), _depth + 1)), out)
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
    # P55: pulihkan kurung environment cases/matrix (placeholder \x01/\x02).
    out = out.replace("\x01", "{").replace("\x02", "}")
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
