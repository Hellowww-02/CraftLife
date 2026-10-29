#!/usr/bin/env python3
"""M06 — satu sumber token desain untuk web DAN Android.

Masalah yang diselesaikan
-------------------------
Sebelum M06, "sistem desain" CraftLife tersebar di tiga tempat yang tidak saling
mengetahui:

  1. ``database.THEMES`` (Python)  — 12 palet warna, sumber kebenaran palet.
  2. ``web/src/index.css``         — 40 token struktural di ``:root``, 11
     registrasi ``@property``, dan 12 blok ``[data-theme]`` yang hanya menimpa
     token atmosfer.
  3. ``web/src/utils/theme.ts``    — ``VAR_MAP`` yang menyalin 16 field palet ke
     CSS var saat runtime.

Android (M07) butuh nilai yang sama dalam satuan dp/sp, dan tidak boleh
membacanya dari CSS. Skrip ini mengekstrak ketiganya menjadi satu
``tokens.json`` yang bisa dibaca build Android, sekaligus MEMBUKTIKAN bahwa
ketiganya masih konsisten.

Yang penting: skrip ini TIDAK mengubah tampilan web. Ia membaca, bukan menulis
ulang CSS. ``--check`` gagal kalau ada drift, sehingga JSON tidak bisa diam-diam
ketinggalan dari CSS.

Pemakaian
---------
    python3 scripts/export_design_tokens.py            # tulis tokens.json
    python3 scripts/export_design_tokens.py --check    # verifikasi, exit 1 kalau drift
    python3 scripts/export_design_tokens.py --report   # cetak ringkasan ke stdout
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CSS_PATH = os.path.join(REPO_ROOT, "web", "src", "index.css")
OUT_PATH = os.path.join(
    REPO_ROOT, "packages", "craftlife-core", "src", "design", "tokens.json"
)

TOKEN_RE = re.compile(r"(--ct-[a-z0-9-]+)\s*:\s*([^;]+);")


# --------------------------------------------------------------------------- #
# Parsing CSS
# --------------------------------------------------------------------------- #
def _block_body(css: str, open_index: int) -> str:
    """Isi di antara ``{`` pada ``open_index`` dan ``}`` pasangannya."""
    depth, i = 0, open_index
    while i < len(css):
        ch = css[i]
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return css[open_index + 1 : i]
        i += 1
    return css[open_index + 1 :]


def parse_properties(css: str) -> dict:
    """Registrasi ``@property`` — inilah yang membuat token warna bisa dianimasikan."""
    out = {}
    for m in re.finditer(r"@property\s+(--ct-[a-z0-9-]+)\s*\{", css):
        body = _block_body(css, m.end() - 1)
        entry = {}
        for key, pat in (
            ("syntax", r"syntax\s*:\s*([^;]+);"),
            ("inherits", r"inherits\s*:\s*([^;]+);"),
            ("initialValue", r"initial-value\s*:\s*([^;]+);"),
        ):
            found = re.search(pat, body)
            if found:
                val = found.group(1).strip().strip("'\"")
                entry[key] = val if key != "inherits" else val == "true"
        out[m.group(1)] = entry
    return out


def parse_root(css: str) -> dict:
    """Token di blok ``:root`` PALET.

    Ada dua blok ``:root`` di file ini dan urutannya menjebak: yang PERTAMA ada
    di dalam ``@media (prefers-reduced-motion: no-preference)`` dan hanya berisi
    daftar ``transition``. Yang kedua baru paletnya. Karena itu dipilih blok yang
    benar-benar mendeklarasikan token.
    """
    for m in re.finditer(r":root\s*\{", css):
        toks = dict(TOKEN_RE.findall(_block_body(css, m.end() - 1)))
        if toks:
            return toks
    return {}


def parse_theme_blocks(css: str) -> dict:
    """Semua blok yang selectornya mengandung ``[data-theme="x"]``.

    Tiap tema punya DUA bentuk blok dan hanya mengambil yang pertama akan
    kehilangan sebagian besar token:

        [data-theme="nether"]            { --ct-grain-o: ... }   # atmosfer
        [data-theme="nether"] .ct-amb    { --ct-amb-a:   ... }   # tuning LED

    Selector setelah atributnya bisa apa saja, jadi polanya ``[^{]*``.
    ``modern_dark`` sengaja tidak punya blok dasar: ``:root`` IS modern_dark.
    """
    out: dict[str, dict] = {}
    for m in re.finditer(r'\[data-theme="([a-z0-9_]+)"\][^{]*\{', css):
        name = m.group(1)
        toks = dict(TOKEN_RE.findall(_block_body(css, m.end() - 1)))
        if toks:
            out.setdefault(name, {}).update(toks)
    return out


def parse_classes(css: str) -> list:
    """275 class ``.ct-*`` unik — bahan inventaris komponen."""
    return sorted(set(re.findall(r"\.ct-[a-z0-9_-]+", css)))


# --------------------------------------------------------------------------- #
# Kategorisasi token
# --------------------------------------------------------------------------- #
CATEGORIES = (
    ("palette", ("primary", "light", "bg", "bg2", "bg3", "panel", "border",
                 "accent", "accent2", "accent3", "glow", "text", "muted",
                 "on-primary", "on-accent", "theme")),
    ("text-tier", ("t1", "t2", "t3")),
    ("typography", ("font-sans", "font-display", "font-mono")),
    ("radius", ("r-sm", "r-md", "r-lg", "r-xl", "r-2xl")),
    ("motion", ("ease", "ease-spring", "ease-inout",
                "t-fast", "t-med", "t-slow", "t-xslow")),
    ("elevation", ("elev-1", "elev-2", "elev-3", "elev-glow")),
    ("atmosphere", ("scene-blob-o", "scene-orb-o", "grain-o", "vignette-o")),
    ("ambient", ("amb-a", "amb-b", "amb-hi", "amb-glow-r", "amb-size",
                 "amb-tempo", "amb-round")),
    ("neumorphic", ("nlm-surface", "nlm-surface-2", "nlm-line",
                    "nlm-line-soft", "nlm-rail", "nlm-dim")),
    ("signature", ("sig-tone",)),
)


def categorize(name: str) -> str:
    short = name[len("--ct-"):]
    for cat, members in CATEGORIES:
        if short in members:
            return cat
    return "other"


# --------------------------------------------------------------------------- #
# db.THEMES — sumber kebenaran palet
# --------------------------------------------------------------------------- #
def load_db_themes() -> dict:
    """Palet dari database.py. Diimpor, bukan di-hardcode, supaya tidak bisa basi."""
    sys.path.insert(0, REPO_ROOT)
    import database  # noqa: PLC0415  (impor lokal: butuh REPO_ROOT di sys.path)

    return dict(database.THEMES)


# --------------------------------------------------------------------------- #
# Konsistensi
# --------------------------------------------------------------------------- #
def _js_assigned_vars() -> set:
    """Custom property yang di-set dari React inline style, bukan dari CSS.

    ``SignatureKit.tsx`` melakukan ``style={{ ['--ct-sig-seg']: segmented }}``.
    Tanpa memindai TSX, token seperti itu terlihat yatim padahal hidup.
    """
    found = set()
    web_src = os.path.join(REPO_ROOT, "web", "src")
    for base, _dirs, files in os.walk(web_src):
        if "node_modules" in base:
            continue
        for fn in files:
            if not fn.endswith((".tsx", ".ts")):
                continue
            try:
                text = open(os.path.join(base, fn), encoding="utf-8").read()
            except OSError:
                continue
            found |= set(re.findall(r"['\"](--ct-[a-z0-9-]+)['\"]\s*(?:as any)?\s*\]", text))
            found |= set(re.findall(r"setProperty\(\s*['\"](--ct-[a-z0-9-]+)", text))
    return found


def audit(css: str, root: dict, themes_css: dict, db_themes: dict, classes: list) -> dict:
    """Periksa silang tiga sumber.

    Mengembalikan dua daftar, dan bedanya penting:

    ``problems``  — inkonsistensi yang bikin token JSON salah atau menyesatkan
                    Android. ``--check`` exit 1.
    ``warnings``  — deviasi nyata yang TIDAK boleh diperbaiki di M06 karena
                    memperbaikinya berarti mengubah tampilan web (terlarang di
                    fase ini). Dicatat di DESIGN.md, bukan disembunyikan.
    """
    problems: list[str] = []
    warnings: list[str] = []

    # 1. Nama tema harus sama persis di CSS dan di db.THEMES.
    #    modern_dark dikecualikan: blok dasarnya adalah :root itu sendiri, jadi
    #    "tidak punya blok [data-theme]" memang benar, bukan cacat.
    css_names = set(themes_css) | {"modern_dark"}
    db_names = set(db_themes)
    if css_names - db_names:
        problems.append(f"tema di CSS tidak ada di db.THEMES: {sorted(css_names - db_names)}")
    if db_names - css_names:
        problems.append(f"tema di db.THEMES tidak punya blok CSS: {sorted(db_names - css_names)}")

    # 2. Palet :root mengklaim paritas dengan db.THEMES['modern_dark'] — klaim itu
    #    tertulis di komentar CSS, jadi diuji, bukan dipercaya.
    dark = db_themes.get("modern_dark", {})
    drifted = []
    for field in ("primary", "light", "bg", "bg2", "bg3", "accent", "accent2",
                  "accent3", "glow", "text", "muted"):
        var, want = f"--ct-{field}", str(dark.get(field, "")).strip().lower()
        got = str(root.get(var, "")).strip().lower()
        if want and got and want != got:
            drifted.append(f"{var}: CSS {got} vs db {want}")
    if drifted:
        # Bukan problem: applyTheme() menimpa nilai ini saat runtime, jadi tampilan
        # akhir benar. Yang terlihat cuma kilatan warna :root sebelum tema dipasang.
        # Menyamakannya sekarang = mengubah tampilan = di luar izin M06.
        warnings.append(
            f"paritas :root vs db.THEMES[modern_dark] melenceng di {len(drifted)} nilai "
            f"({' | '.join(drifted)}). Efek: warna awal sebelum applyTheme() sedikit beda, "
            f"lalu dikoreksi. TIDAK diperbaiki di M06 karena menyeragamkannya berarti "
            f"mengubah tampilan web."
        )

    # 3. Setiap var(--ct-x) yang dipakai harus punya definisi, fallback, ATAU
    #    di-set dari JS. Tiga kasus itu beda dan harus dibedakan:
    #      - dideklarasikan di CSS          -> normal
    #      - var(--x, fallback)             -> aman, nilai ada di pemanggil
    #      - di-set lewat style={{'--x':v}} -> sah (SignatureKit melakukan ini)
    #      - tidak ada di mana pun          -> deklarasi yang memakainya MATI
    defined = set(re.findall(r"(--ct-[a-z0-9-]+)\s*:", css))
    js_set = _js_assigned_vars()
    used = set(re.findall(r"var\(\s*(--ct-[a-z0-9-]+)", css))
    with_fallback = set(re.findall(r"var\(\s*(--ct-[a-z0-9-]+)\s*,", css))
    orphans = sorted(used - defined - with_fallback - js_set)
    if orphans:
        # Cacat bawaan, BUKAN sesuatu yang boleh diperbaiki di M06: memberi nilai
        # pada token ini akan menghidupkan transisi yang selama ini mati, dan itu
        # perubahan tampilan. Dicatat untuk M07/M08.
        counts_used = {o: len(re.findall(r"var\(\s*" + re.escape(o) + r"\s*\)", css)) for o in orphans}
        warnings.append(
            "token dipakai tapi tidak pernah didefinisikan di mana pun: "
            + ", ".join(f"{o} ({n}x)" for o, n in counts_used.items())
            + ". Deklarasi transition yang memakainya tidak berlaku. TIDAK diperbaiki "
              "di M06 karena menghidupkannya = menambah animasi = mengubah tampilan."
        )

    # 4. VAR_MAP di theme.ts harus menutupi field WARNA db.THEMES.
    #    `label` dan `key` dikecualikan: itu nama tampilan/identifier, bukan warna.
    NON_COLOR = {"label", "key"}
    ts_path = os.path.join(REPO_ROOT, "web", "src", "utils", "theme.ts")
    if os.path.exists(ts_path):
        ts = open(ts_path, encoding="utf-8").read()
        mapped = re.findall(r"\['([a-z0-9_]+)',\s*'(--ct-[a-z0-9-]+)'\]", ts)
        palette_fields = set(db_themes.get("modern_dark", {}))
        for field, _var in mapped:
            if field not in palette_fields:
                problems.append(
                    f"VAR_MAP theme.ts memetakan field '{field}' yang tidak ada di db.THEMES")
        mapped_vars = {v for _f, v in mapped} | {"--ct-theme"}
        palette_vars = {
            f"--ct-{k.replace('_', '-')}" for k in palette_fields if k not in NON_COLOR
        }
        for var in sorted(palette_vars - mapped_vars):
            problems.append(f"field db.THEMES tidak disalin applyTheme: {var}")

    return {
        "problems": problems,
        "warnings": warnings,
        "counts": {
            "rootTokens": len(root),
            "propertyRegistrations": len(parse_properties(css)),
            "themes": len(db_themes),
            "paletteFieldsPerTheme": len(db_themes.get("modern_dark", {})),
            "classes": len(classes),
            "themeBlockTokens": len(set().union(*(set(v) for v in themes_css.values())) or set()),
            "declaredAnywhere": len(set(re.findall(r"(--ct-[a-z0-9-]+)\s*:", css))),
        },
    }


# --------------------------------------------------------------------------- #
# Ekspor
# --------------------------------------------------------------------------- #
def build_tokens(css: str) -> dict:
    root = parse_root(css)
    props = parse_properties(css)
    themes_css = parse_theme_blocks(css)
    classes = parse_classes(css)
    db_themes = load_db_themes()

    structural = {k: v.strip() for k, v in root.items() if categorize(k) != "palette"}
    palette_root = {k: v.strip() for k, v in root.items() if categorize(k) == "palette"}

    return {
        "$comment": (
            "DIHASILKAN oleh scripts/export_design_tokens.py - jangan diedit tangan. "
            "Sumber: database.THEMES (palet) + web/src/index.css (token struktural) "
            "+ web/src/utils/theme.ts (VAR_MAP). Jalankan ulang skrip itu setelah "
            "mengubah salah satunya."
        ),
        "version": _app_version(),
        "meta": audit(css, root, themes_css, db_themes, classes)["counts"],
        "themes": {
            name: {k: str(v) for k, v in sorted(palette.items())}
            for name, palette in sorted(db_themes.items())
        },
        "paletteDefaults": palette_root,
        "structural": structural,
        "property": {k: props[k] for k in sorted(props)},
        "atmosphere": {k: dict(sorted(v.items())) for k, v in sorted(themes_css.items())},
        "classes": classes,
        "classGroups": _class_groups(classes),
        "variants": _variants(css),
        "audit": audit(css, root, themes_css, db_themes, classes),
    }


def _app_version() -> str:
    path = os.path.join(REPO_ROOT, "database.py")
    with open(path, encoding="utf-8") as fh:
        m = re.search(r'^APP_VERSION\s*=\s*["\']([^"\']+)', fh.read(), re.M)
    return m.group(1) if m else "unknown"


def _class_groups(classes: list) -> dict:
    """Kelompokkan 275 class menurut segmen pertama setelah `.ct-`.

    Ini bukan pengelompokan semantik akhir - DESIGN.md yang menamai komponennya -
    tapi cukup untuk membuktikan tidak ada class yatim yang terlewat.
    """
    groups: dict[str, list[str]] = {}
    for cls in classes:
        head = cls[len(".ct-"):].split("-")[0]
        groups.setdefault(head, []).append(cls)
    return {k: sorted(v) for k, v in sorted(groups.items(), key=lambda kv: (-len(kv[1]), kv[0]))}


def _variants(css: str) -> dict:
    """Konvensi varian `is-*`. Diukur, bukan diasumsikan sudah menjadi sistem."""
    found = sorted(set(re.findall(r"(\.ct-[a-z0-9_-]+)\.(is-[a-z0-9-]+)", css)))
    by_class: dict[str, list[str]] = {}
    for cls, var in found:
        by_class.setdefault(cls, []).append(var)
    return {"convention": "is-row / is-sm", "implemented": by_class}


# --------------------------------------------------------------------------- #
def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--check", action="store_true",
                    help="jangan menulis; exit 1 kalau JSON di disk berbeda atau ada masalah audit")
    ap.add_argument("--report", action="store_true", help="cetak ringkasan ke stdout")
    args = ap.parse_args()

    css = open(CSS_PATH, encoding="utf-8").read()
    tokens = build_tokens(css)
    payload = json.dumps(tokens, indent=2, ensure_ascii=False) + "\n"

    problems = tokens["audit"]["problems"]
    warnings = tokens["audit"]["warnings"]
    counts = tokens["meta"]

    if args.report or not args.check:
        print(f"token :root            : {counts['rootTokens']}")
        print(f"@property terdaftar    : {counts['propertyRegistrations']}")
        print(f"tema (db.THEMES)       : {counts['themes']} x {counts['paletteFieldsPerTheme']} field")
        print(f"token per-tema         : {counts['themeBlockTokens']} unik")
        print(f"class .ct-*            : {counts['classes']} dalam {len(tokens['classGroups'])} kelompok")
        print(f"varian is-*            : {sum(len(v) for v in tokens['variants']['implemented'].values())} "
              f"pada {len(tokens['variants']['implemented'])} class")
        print(f"masalah (harus 0)      : {len(problems)}")
        for p in problems:
            print(f"   ! {p}")
        print(f"deviasi tercatat       : {len(warnings)}")
        for w in warnings:
            print(f"   ~ {w}")

    if args.check:
        if not os.path.exists(OUT_PATH):
            print(f"CHECK GAGAL: {os.path.relpath(OUT_PATH, REPO_ROOT)} belum ada")
            return 1
        current = open(OUT_PATH, encoding="utf-8").read()
        if current != payload:
            print("CHECK GAGAL: tokens.json berbeda dari hasil ekstraksi. "
                  "Jalankan: python3 scripts/export_design_tokens.py")
            return 1
    if problems:
        print(f"CHECK GAGAL: {len(problems)} masalah konsistensi (lihat di atas)")
        return 1

    if not args.check:
        os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)
        with open(OUT_PATH, "w", encoding="utf-8") as fh:
            fh.write(payload)
        print(f"\nditulis: {os.path.relpath(OUT_PATH, REPO_ROOT)} ({len(payload):,} byte)")
    else:
        print("CHECK OK: tokens.json sinkron dengan CSS + db.THEMES, 0 masalah")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
