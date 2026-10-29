"""M05 butir 1 — kontrak container diverifikasi tanpa Docker.

Docker tidak tersedia di lingkungan ini, jadi `docker build` tidak bisa
dijalankan dan **tidak diklaim sudah**. Yang bisa diuji, dan diuji di sini,
adalah setiap hal yang biasanya membuat image gagal saat pertama kali dicoba:

1. Berkas yang di-COPY tidak ada, atau ada modul yang tertinggal.
2. `requirements-server.txt` kurang paket, sehingga server mati saat start.
3. Entrypoint-nya sendiri tidak menyala.

Poin ketiga yang paling penting: tes ini menyalin berkas-berkas yang persis
di-COPY Dockerfile ke direktori kosong, menjalankan `python api_server.py`
dengan env yang sama seperti di dalam container, lalu meminta `/api/health` dan
`/api/version`. Kalau ada satu modul tertinggal, prosesnya mati dan tes ini
gagal — persis seperti yang akan terjadi di dalam image, hanya lebih cepat dan
tanpa Docker.

Versi pertama Dockerfile ini menyebut `logger.py` yang tidak ada dan
melupakan sepuluh modul nyata, termasuk `applog` yang diimpor `database.py`
baris 30. Tes inilah yang membuat kesalahan semacam itu tidak bisa terulang
diam-diam.
"""
from __future__ import annotations

import ast
import json
import os
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile
import time
import unittest
import urllib.error
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parents[1]

#: Modul yang disebut di baris COPY Dockerfile. Dibaca dari berkasnya, bukan
#: ditulis ulang di sini, supaya tes menguji Dockerfile yang sebenarnya.
def _copied_files() -> list[str]:
    text = (ROOT / "Dockerfile").read_text(encoding="utf-8")
    # Baris COPY di Dockerfile ini memakai kelanjutan `\`, jadi baris-barisnya
    # harus disatukan lebih dulu. Versi pertama fungsi ini membaca per baris
    # dan hanya mendapat 5 dari 21 berkas — dan servernya benar-benar mati
    # dengan `ModuleNotFoundError: food_data`, yang membuktikan tes ini
    # menangkap kesalahan semacam itu.
    joined = re.sub(r"\\\n\s*", " ", text)
    out: list[str] = []
    for m in re.finditer(r"^COPY\s+(.*?)(?:\s+\./)?$", joined, re.M):
        chunk = m.group(1)
        if chunk.startswith("requirements-server.txt"):
            continue
        out.extend(f for f in chunk.split() if f.endswith(".py"))
    return out


#: Nama paket PyPI tidak selalu sama dengan nama modulnya.
PACKAGE_TO_MODULE = {
    "python-dateutil": "dateutil",
    "python-docx": "docx",
    "pillow": "PIL",
    "beautifulsoup4": "bs4",
    "python-dotenv": "dotenv",
    "pymupdf": "fitz",
    "python-pptx": "pptx",
    "youtube-transcript-api": "youtube_transcript_api",
    "ebooklib": "ebooklib",
}


def _server_modules() -> list[str]:
    """Modul server = yang di-COPY Dockerfile."""
    return _copied_files()


def _module_level_nodes(tree: ast.AST):
    """Node tingkat modul, tanpa masuk ke dalam fungsi atau kelas.

    Sengaja berhenti di FunctionDef/ClassDef: `import edge_tts` di dalam sebuah
    fungsi baru dijalankan saat fungsi itu dipanggil, jadi tidak menggagalkan
    start server dan tidak wajib ada di requirements. Versi pertama pemindai
    ini menyapu seluruh pohon dan menuntut `edge_tts`, `gtts`, dan `google` —
    ketiganya impor tertunda, dan server memang start normal tanpanya.
    """
    stack = list(getattr(tree, "body", []))
    while stack:
        node = stack.pop()
        yield node
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            continue
        for field in ("body", "orelse", "finalbody"):
            stack.extend(getattr(node, field, []) or [])
        for handler in getattr(node, "handlers", []) or []:
            stack.extend(handler.body)


def _bare_third_party_imports(modules: list[str]) -> set[str]:
    """Impor pihak ketiga tingkat modul yang TIDAK dibungkus try/except.

    Hanya inilah yang membuat server mati saat start. Yang terlindungi
    try/except tidak dihitung: server memang start normal tanpanya, dan
    memaksanya masuk requirements akan menarik dependensi yang tidak dipakai.
    """
    stdlib = set(sys.stdlib_module_names)
    local = {p.stem for p in ROOT.glob("*.py")}
    found: set[str] = set()
    for name in modules:
        path = ROOT / name
        if not path.exists():
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"))
        protected: set[int] = set()
        for node in _module_level_nodes(tree):
            if isinstance(node, ast.Try) and any(
                    h.type is not None and getattr(h.type, "id", "") in
                    ("ImportError", "ModuleNotFoundError", "Exception")
                    for h in node.handlers):
                for sub in _module_level_nodes(node):
                    if isinstance(sub, (ast.Import, ast.ImportFrom)):
                        protected.add(id(sub))
        for node in _module_level_nodes(tree):
            names = []
            if isinstance(node, ast.Import):
                names = [a.name.split(".")[0] for a in node.names]
            elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
                names = [node.module.split(".")[0]]
            for mod in names:
                if mod in stdlib or mod in local or id(node) in protected:
                    continue
                found.add(mod)
    return found


def _local_imports(modules: list[str]) -> set[str]:
    """Modul lokal yang diimpor modul server (harus ikut di-COPY)."""
    local = {p.stem for p in ROOT.glob("*.py")}
    need: set[str] = set()
    for name in modules:
        path = ROOT / name
        if not path.exists():
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for a in node.names:
                    if a.name.split(".")[0] in local:
                        need.add(a.name.split(".")[0])
            elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
                if node.module.split(".")[0] in local:
                    need.add(node.module.split(".")[0])
    return need - {pathlib.Path(m).stem for m in modules}


def _requirements(path: pathlib.Path) -> dict[str, str]:
    """{nama modul: nama paket} dari sebuah file requirements."""
    out = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.split("#")[0].strip()
        if not line:
            continue
        pkg = re.split(r"[<>=!~\[ ]", line)[0].strip()
        if pkg:
            out[PACKAGE_TO_MODULE.get(pkg.lower(), pkg)] = pkg
    return out


class DockerfileContractTest(unittest.TestCase):
    def test_dockerfile_and_companion_files_exist(self):
        for f in ("Dockerfile", "docker-compose.yml", ".dockerignore",
                  "requirements-server.txt"):
            self.assertTrue((ROOT / f).exists(), f"{f} tidak ada")

    def test_the_copy_list_is_not_empty(self):
        """Penjaga: regex yang rusak tidak boleh membuat semua tes di bawah lolos."""
        self.assertGreaterEqual(len(_copied_files()), 15,
                                "daftar COPY terbaca kosong — regex tes ini rusak")

    def test_every_copied_file_actually_exists(self):
        missing = [f for f in _copied_files() if not (ROOT / f).exists()]
        self.assertEqual(missing, [],
                         "Dockerfile menyalin berkas yang tidak ada: " + ", ".join(missing))

    def test_no_local_module_the_server_imports_is_left_behind(self):
        """Inilah yang membuat image gagal start, bukan gagal build."""
        missing = sorted(_local_imports(_server_modules()) - set(_copied_files()))
        self.assertEqual(
            missing, [],
            "modul lokal berikut diimpor server tapi tidak di-COPY: "
            + ", ".join(m + ".py" for m in missing))

    def test_server_requirements_cover_every_bare_import(self):
        have = _requirements(ROOT / "requirements-server.txt")
        need = _bare_third_party_imports(_server_modules())
        missing = sorted(need - set(have))
        self.assertEqual(
            missing, [],
            "requirements-server.txt tidak menutup impor telanjang: " + ", ".join(missing))

    def test_no_invented_packages(self):
        """Setiap paket server harus juga ada di requirements.txt desktop."""
        desktop = set(_requirements(ROOT / "requirements.txt").values())
        server = set(_requirements(ROOT / "requirements-server.txt").values())
        invented = sorted(p for p in server if p.lower() not in
                          {d.lower() for d in desktop})
        self.assertEqual(invented, [],
                         "paket ini tidak ada di requirements.txt: " + ", ".join(invented))

    def test_server_requirements_skip_the_desktop_only_packages(self):
        """Kalau PyQt6 masuk sini, pemisahan daftarnya tidak berguna."""
        server = {p.lower() for p in _requirements(ROOT / "requirements-server.txt").values()}
        for heavy in ("pyqt6", "matplotlib", "pymupdf", "yt-dlp", "edge-tts"):
            self.assertNotIn(heavy, server, f"{heavy} tidak dibutuhkan server")

    def test_image_does_not_run_as_root(self):
        text = (ROOT / "Dockerfile").read_text(encoding="utf-8")
        self.assertRegex(text, re.compile(r"^USER\s+\d+", re.M),
                         "image berjalan sebagai root")

    def test_container_binds_to_all_interfaces(self):
        """127.0.0.1 di dalam container tidak terjangkau dari luar."""
        text = (ROOT / "Dockerfile").read_text(encoding="utf-8")
        self.assertIn("CRAFTLIFE_API_HOST=0.0.0.0", text)

    def test_dockerignore_excludes_secrets_and_runtime_artifacts(self):
        text = (ROOT / ".dockerignore").read_text(encoding="utf-8")
        for entry in (".env", "craftlife.db", "logs/"):
            self.assertIn(entry, text, f"{entry} tidak dikecualikan dari konteks build")

    def test_compose_requires_a_jwt_secret_with_no_default(self):
        """Secret tanpa default: lebih baik gagal start daripada start tidak aman."""
        text = (ROOT / "docker-compose.yml").read_text(encoding="utf-8")
        self.assertIn("CRAFTLIFE_RULES_API", text)
        self.assertRegex(text, r"CRAFTLIFE_JWT_SECRET:\s*\"\$\{CRAFTLIFE_JWT_SECRET:\?")
        self.assertNotRegex(text, r"CRAFTLIFE_JWT_SECRET:-[^\}]")


class EntrypointTest(unittest.TestCase):
    """Menjalankan entrypoint persis seperti container, tanpa Docker.

    Dijalankan dalam **mode strict** (`CRAFTLIFE_RULES_API=1`), karena itulah
    cara container ini dimaksudkan berjalan. Alasannya ditemukan saat menulis
    tes ini, bukan direncanakan: `_ensure_user()` (api_server.py:873) hanya
    MEMILIH pengguna pertama dari tabel, tidak pernah membuatnya. Di desktop
    pengguna dibuat onboarding; di container dengan volume kosong tidak ada
    satu pun, sehingga setiap rute menjawab 401. Mode strict mengambil identitas
    dari JWT, jadi tidak bergantung pada pengguna pertama — dan itu memang
    arti "layanan multi-tenant" di butir roadmapnya.
    """

    SECRET = "container-test-secret-bukan-rahasia-produksi"
    SUB = "cccccccc-0000-0000-0000-0000000000c1"

    def _start(self, strict: bool):
        files = _copied_files()
        tmp = tempfile.mkdtemp(prefix="craftlife-image-")
        self.addCleanup(shutil.rmtree, tmp, True)
        for f in files:
            shutil.copy2(ROOT / f, os.path.join(tmp, f))

        env = dict(os.environ)
        env.update({
            "CRAFTLIFE_API_HOST": "127.0.0.1",   # loopback cukup untuk tes
            "CRAFTLIFE_API_PORT": "8791",
            "PYTHONPATH": tmp,
        })
        env.pop("CRAFTLIFE_JWT_SECRET", None)
        env.pop("CRAFTLIFE_RULES_API", None)

        # Basis data + satu pengguna tertaut disiapkan lebih dulu, meniru
        # volume yang sudah terisi. Tanpa ini tidak ada yang bisa diautentikasi.
        seed = (
            "import database as db;"
            "db.init_db();"
            "db.register_user('container','password123',display_name='Container');"
            "c=db.get_conn();"
            "c.execute(\"UPDATE users SET cloud_user_id=? WHERE id=(SELECT MIN(id) FROM users)\", "
            f"('{self.SUB}',));"
            "c.commit();c.close()")
        r = subprocess.run([sys.executable, "-c", seed], cwd=tmp, env=env,
                           capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, f"seed gagal: {r.stderr[-800:]}")

        if strict:
            env["CRAFTLIFE_RULES_API"] = "1"
            env["CRAFTLIFE_JWT_SECRET"] = self.SECRET

        proc = subprocess.Popen(
            [sys.executable, "api_server.py"], cwd=tmp, env=env,
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)

        def _stop():
            # terminate lalu wait: tanpa wait, prosesnya ditinggal berjalan dan
            # pipa stdout-nya bocor (ResourceWarning saat tes selesai).
            if proc.poll() is None:
                proc.terminate()
                try:
                    proc.wait(timeout=10)
                except Exception:
                    proc.kill()
            if proc.stdout:
                proc.stdout.close()

        self.addCleanup(_stop)

        base = "http://127.0.0.1:8791"
        deadline = time.time() + 120
        while time.time() < deadline:
            if proc.poll() is not None:
                body = proc.stdout.read() if proc.stdout else ""
                self.fail(
                    f"server mati dengan kode {proc.returncode} sebelum siap.\n"
                    f"Inilah yang akan terjadi di dalam image.\n--- output ---\n{body[-2500:]}")
            try:
                urllib.request.urlopen(f"{base}/api/health", timeout=3)
                break
            except urllib.error.HTTPError:
                break
            except Exception:
                time.sleep(0.5)
        return base

    def _get(self, base, path, token=None):
        req = urllib.request.Request(f"{base}{path}")
        if token:
            req.add_header("Authorization", f"Bearer {token}")
        try:
            with urllib.request.urlopen(req, timeout=15) as r:
                return r.status, json.loads(r.read().decode())
        except urllib.error.HTTPError as exc:
            raw = exc.read().decode("utf-8", "replace")
            try:
                return exc.code, json.loads(raw)
            except Exception:
                return exc.code, {"raw": raw}

    def test_healthcheck_endpoint_is_public(self):
        """HEALTHCHECK Dockerfile bergantung pada ini; kalau butuh auth, mati."""
        base = self._start(strict=True)
        status, body = self._get(base, "/api/health")
        self.assertEqual(status, 200, f"/api/health menjawab {status}: {body}")
        self.assertTrue(body.get("ok"))

    def test_strict_mode_rejects_anonymous_requests(self):
        """Tanpa JWT -> 401. Inilah kriteria penerimaan M05."""
        base = self._start(strict=True)
        status, body = self._get(base, "/api/version")
        self.assertEqual(status, 401, f"tanpa token seharusnya 401, dapat {status}: {body}")

    def test_a_valid_jwt_is_served_and_reports_the_real_version(self):
        """Bukti container berfungsi sebagai layanan, bukan hanya menyala."""
        from tests.test_m05b_tenant_scoping import make_jwt
        import tests.test_m05b_tenant_scoping as m05b
        base = self._start(strict=True)
        saved = m05b.SECRET
        m05b.SECRET = self.SECRET
        try:
            token = make_jwt(self.SUB)
        finally:
            m05b.SECRET = saved
        status, body = self._get(base, "/api/version", token)
        self.assertEqual(status, 200, f"dengan JWT sah seharusnya 200, dapat {status}: {body}")
        import updater
        self.assertEqual(str(body.get("version")), updater.APP_VERSION,
                         "/api/version tidak sama dengan APP_VERSION")

    def test_strict_mode_hides_the_database_path(self):
        """M05c: path absolut DB tidak boleh bocor dari layanan internet-facing."""
        from tests.test_m05b_tenant_scoping import make_jwt
        import tests.test_m05b_tenant_scoping as m05b
        base = self._start(strict=True)
        saved = m05b.SECRET
        m05b.SECRET = self.SECRET
        try:
            token = make_jwt(self.SUB)
        finally:
            m05b.SECRET = saved
        _status, body = self._get(base, "/api/version", token)
        self.assertNotIn("dbPath", body,
                         "dbPath bocor dari layanan strict mode")


if __name__ == "__main__":
    unittest.main(verbosity=2)
