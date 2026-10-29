"""M06 — token desain adalah satu sumber, dan klaim a11y-nya benar-benar dihitung.

Tiga hal diuji di sini, dan ketiganya dulu cuma klaim di komentar CSS:

1. ``tokens.json`` tidak boleh ketinggalan dari ``index.css`` / ``db.THEMES``.
2. 12 tema terpetakan lengkap: setiap tema punya semua field palet, dan setiap
   token yang dipakai CSS punya definisi atau fallback.
3. Kontras warna memenuhi ≥ 4,5:1 — DIHITUNG dari nilai hex nyata, bukan
   diasumsikan. Kalau ada tema yang gagal, tes ini menyebut temanya.

Tidak ada yang di-mock: skrip ekspor dijalankan sebagai fungsi nyata terhadap
file CSS yang ada di repo.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import unittest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "scripts"))
sys.path.insert(0, REPO)

import export_design_tokens as edt  # noqa: E402

CSS = os.path.join(REPO, "web", "src", "index.css")
TOKENS = os.path.join(REPO, "packages", "craftlife-core", "src", "design", "tokens.json")

EXPECTED_THEMES = 12
EXPECTED_ROOT_TOKENS = 40
EXPECTED_CLASSES = 275


# --------------------------------------------------------------------------- #
# WCAG 2.x relative luminance & contrast ratio
# --------------------------------------------------------------------------- #
def _channel(c: float) -> float:
    c /= 255.0
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def luminance(rgb: tuple) -> float:
    r, g, b = rgb
    return 0.2126 * _channel(r) + 0.7152 * _channel(g) + 0.0722 * _channel(b)


def contrast(a: str, b: str) -> float:
    la, lb = luminance(_to_rgb(a)), luminance(_to_rgb(b))
    hi, lo = max(la, lb), min(la, lb)
    return (hi + 0.05) / (lo + 0.05)


def _to_rgb(color: str) -> tuple:
    """#rgb, #rrggbb, atau rgba(r,g,b,a) di atas latar gelap default."""
    color = color.strip()
    if color.startswith("rgba(") or color.startswith("rgb("):
        nums = [float(x) for x in re.findall(r"[-\d.]+", color)]
        r, g, b = nums[0], nums[1], nums[2]
        if len(nums) >= 4:  # alpha di atas --ct-bg default
            a = nums[3]
            base = _to_rgb("#0b0b16")
            r, g, b = (c * a + bc * (1 - a) for c, bc in zip((r, g, b), base))
        return (r, g, b)
    h = color.lstrip("#")
    if len(h) == 3:
        h = "".join(ch * 2 for ch in h)
    return tuple(int(h[i : i + 2], 16) for i in (0, 2, 4))


# --------------------------------------------------------------------------- #
class TokenExportTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.css = open(CSS, encoding="utf-8").read()
        cls.tokens = edt.build_tokens(cls.css)

    def test_tokens_file_exists_and_is_current(self):
        self.assertTrue(os.path.exists(TOKENS), f"{TOKENS} belum dibuat")
        on_disk = open(TOKENS, encoding="utf-8").read()
        expected = json.dumps(self.tokens, indent=2, ensure_ascii=False) + "\n"
        self.assertEqual(
            on_disk, expected,
            "tokens.json berbeda dari hasil ekstraksi — jalankan "
            "python3 scripts/export_design_tokens.py",
        )

    def test_check_mode_exits_zero(self):
        r = subprocess.run(
            [sys.executable, "scripts/export_design_tokens.py", "--check"],
            cwd=REPO, capture_output=True, text=True,
        )
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)

    def test_audit_reports_no_hard_problems(self):
        self.assertEqual(
            self.tokens["audit"]["problems"], [],
            "audit menemukan inkonsistensi antar sumber token",
        )

    def test_the_extractor_actually_reads_the_real_css(self):
        """Anti-vakuitas: kalau parser rusak dan mengembalikan dict kosong,
        tes-tes lain bisa lolos sambil membandingkan kekosongan."""
        self.assertEqual(len(self.tokens["themes"]), EXPECTED_THEMES)
        self.assertEqual(self.tokens["meta"]["rootTokens"], EXPECTED_ROOT_TOKENS)
        self.assertEqual(self.tokens["meta"]["classes"], EXPECTED_CLASSES)
        self.assertIn("--ct-ease", self.tokens["structural"])
        self.assertEqual(
            self.tokens["structural"]["--ct-ease"], "cubic-bezier(0.22, 1, 0.36, 1)"
        )

    def test_parser_takes_the_palette_root_not_the_transition_root(self):
        """Ada dua blok :root; yang pertama hanya berisi daftar transition.
        Salah pilih blok = seluruh ekspor kosong dan sunyi."""
        root = edt.parse_root(self.css)
        self.assertIn("--ct-primary", root)
        self.assertIn("--ct-r-sm", root)

    def test_theme_blocks_include_the_ambient_descendant_selector(self):
        """`[data-theme=x] .ct-amb { ... }` harus ikut terbaca, bukan cuma
        `[data-theme=x] { ... }`."""
        blocks = edt.parse_theme_blocks(self.css)
        # Blok dasar memberi atmosfer, blok .ct-amb menyetel LED. Yang di-override
        # per tema hanyalah round/tempo/glow-r/size — amb-a/b/hi tetap di class dasar.
        nether = blocks["nether"]
        self.assertIn("--ct-scene-blob-o", nether, "blok [data-theme] dasar tidak terbaca")
        self.assertIn("--ct-amb-tempo", nether, "blok [data-theme] .ct-amb tidak terbaca")


class ThemeCompletenessTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.css = open(CSS, encoding="utf-8").read()
        cls.tokens = edt.build_tokens(cls.css)
        cls.themes = cls.tokens["themes"]

    def test_twelve_themes_each_with_a_full_palette(self):
        self.assertEqual(len(self.themes), EXPECTED_THEMES)
        fields = set(self.themes["modern_dark"])
        self.assertEqual(len(fields), 16)
        for name, palette in self.themes.items():
            self.assertEqual(
                set(palette), fields, f"tema {name} tidak punya field palet lengkap"
            )
            for field, value in palette.items():
                self.assertTrue(str(value).strip(), f"{name}.{field} kosong")

    def test_every_theme_has_a_css_atmosphere_block(self):
        """modern_dark diwakili :root, jadi yang wajib punya blok = 11 sisanya."""
        atmosphere = self.tokens["atmosphere"]
        for name in self.themes:
            if name == "modern_dark":
                continue
            self.assertIn(name, atmosphere, f"tema {name} tidak punya blok [data-theme]")

    def test_no_token_used_without_a_definition_or_fallback(self):
        defined = set(re.findall(r"(--ct-[a-z0-9-]+)\s*:", self.css))
        defined |= edt._js_assigned_vars()
        used = set(re.findall(r"var\(\s*(--ct-[a-z0-9-]+)", self.css))
        fallback = set(re.findall(r"var\(\s*(--ct-[a-z0-9-]+)\s*,", self.css))
        # --ct-t cacat bawaan yang sengaja TIDAK diperbaiki di M06 (lihat DESIGN.md)
        known = {"--ct-t"}
        self.assertEqual(sorted(used - defined - fallback - known), [])

    def test_every_theme_key_is_a_valid_css_identifier(self):
        for name in self.themes:
            self.assertRegex(name, r"^[a-z][a-z0-9_]*$", f"nama tema {name} tidak aman utk selector")


class ContrastTest(unittest.TestCase):
    """Klaim gate: kontras ≥ 4,5:1. Di sini dihitung, bukan dipercaya."""

    @classmethod
    def setUpClass(cls):
        cls.css = open(CSS, encoding="utf-8").read()
        cls.themes = edt.build_tokens(cls.css)["themes"]

    def test_body_text_on_background_meets_4_5(self):
        failures = []
        for name, p in self.themes.items():
            ratio = contrast(p["text"], p["bg"])
            if ratio < 4.5:
                failures.append(f"{name}: text/bg = {ratio:.2f}")
        self.assertEqual(failures, [], "kontras teks terhadap latar di bawah 4,5:1")

    def test_muted_text_on_background_meets_3_for_large(self):
        """Teks sekunder jarang dipakai untuk body copy; ambang 3:1 (teks besar)."""
        failures = []
        for name, p in self.themes.items():
            ratio = contrast(p["muted"], p["bg"])
            if ratio < 3.0:
                failures.append(f"{name}: muted/bg = {ratio:.2f}")
        self.assertEqual(failures, [], "kontras muted terhadap latar di bawah 3:1")

    # Utang kontras M06 (5 tema on_primary di bawah 4,5:1) DIBAYAR di M13
    # (2026-10-23): warna primary/accent digelapkan 6-12% (sakura: teks
    # digelapkan) sampai semua pasangan >= 4,5:1. Daftar ini sekarang
    # KOSONG dan harus tetap kosong — tema baru yang gagal kontras harus
    # diperbaiki warnanya, bukan ditambahkan ke daftar utang.
    KNOWN_LOW_CONTRAST: dict = {}

    def test_themes_that_pass_contrast_keep_passing(self):
        failures = []
        for name, p in self.themes.items():
            if name in self.KNOWN_LOW_CONTRAST:
                continue
            ratio = contrast(p["on_primary"], p["primary"])
            if ratio < 4.5:
                failures.append(f"{name}: on_primary/primary = {ratio:.2f}")
        self.assertEqual(failures, [], "tema yang tadinya lolos kini di bawah 4,5:1")

    def test_known_contrast_debt_is_pinned_and_documented(self):
        """Utang kontras sudah lunas di M13; test ini menjaga tidak ada
        utang baru yang diselundupkan lewat daftar pengecualian."""
        for name, expected in self.KNOWN_LOW_CONTRAST.items():
            actual = contrast(self.themes[name]["on_primary"], self.themes[name]["primary"])
            self.assertAlmostEqual(
                actual, expected, delta=0.02,
                msg=f"kontras {name} bergeser dari {expected} ke {actual:.2f}; "
                    f"perbarui DESIGN.md dan utang kontrasnya",
            )
        self.assertEqual(
            len(self.KNOWN_LOW_CONTRAST), 0,
            "utang kontras baru muncul - perbaiki warnanya, jangan daftarkan",
        )

    def test_the_contrast_function_is_not_vacuous(self):
        """Kalau contrast() selalu mengembalikan angka besar, ketiga tes di atas
        lolos tanpa membuktikan apa pun."""
        self.assertGreater(contrast("#ffffff", "#000000"), 20)
        self.assertLess(contrast("#777777", "#888888"), 1.5)
        self.assertAlmostEqual(contrast("#000000", "#000000"), 1.0, places=3)


class InventoryTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.css = open(CSS, encoding="utf-8").read()
        cls.tokens = edt.build_tokens(cls.css)

    def test_class_inventory_covers_every_ct_class_in_the_css(self):
        real = set(re.findall(r"\.ct-[a-z0-9_-]+", self.css))
        self.assertEqual(set(self.tokens["classes"]), real)
        self.assertEqual(len(self.tokens["classes"]), EXPECTED_CLASSES)

    def test_groups_account_for_every_class_exactly_once(self):
        flat = [c for members in self.tokens["classGroups"].values() for c in members]
        self.assertEqual(len(flat), EXPECTED_CLASSES)
        self.assertEqual(len(set(flat)), EXPECTED_CLASSES, "ada class masuk dua kelompok")

    def test_signaturekit_is_the_largest_group_and_stays_distinct(self):
        """M06 melarang SignatureKit diratakan ke Material default."""
        groups = self.tokens["classGroups"]
        self.assertIn("sig", groups)
        # 52 class unik terukur. Angka 65 yang beredar adalah jumlah KEMUNCULAN
        # (satu class bisa muncul di beberapa selector), bukan jumlah class.
        self.assertGreaterEqual(
            len(groups["sig"]), 50,
            "kelompok signature menyusut — periksa apakah ada yang diratakan",
        )

    def test_variant_convention_is_measured_not_assumed(self):
        variants = self.tokens["variants"]["implemented"]
        self.assertIn(".ct-nlm-railbtn", variants)
        self.assertEqual(
            sorted(variants[".ct-nlm-railbtn"]), ["is-active", "is-row", "is-sm"]
        )
        total = sum(len(v) for v in variants.values())
        self.assertGreaterEqual(total, 15, "jumlah varian is-* menyusut")


if __name__ == "__main__":
    unittest.main()
