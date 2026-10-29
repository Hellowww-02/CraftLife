"""M13 — performa terukur (server lokal, batas longgar anti-regresi parah).

Yang diukur: latensi median endpoint kunci lewat soket sungguhan
(LiveApiServer, DB temporer). Batasnya sengaja 10x di atas angka normal
mesin CI — tujuannya menangkap regresi orde-besaran (query N+1 baru,
snapshot yang meledak), bukan memoles milidetik. Cold start / memori /
baterai Android adalah pengukuran perangkat: dicatat di QA_M13.md sebagai
menunggu bukti pengguna (keputusan 2026-10-23), tidak dikarang di sini.
"""
from __future__ import annotations

import json
import statistics
import time
import unittest
import urllib.request

from tests.harness import LiveApiServer

# Batas median per endpoint (ms). Angka normal lokal: 5–80 ms.
BUDGET_MS = {
    "/api/bootstrap": 2000,
    "/api/habits": 1000,
    "/api/cloud/status": 1000,
    "/api/leaderboard": 1000,
}


class PerformanceTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._server = LiveApiServer("m13_perf")
        cls._server.__enter__()
        cls.base = cls._server.base

    @classmethod
    def tearDownClass(cls):
        cls._server.__exit__(None, None, None)

    def _timed_get(self, path: str) -> float:
        # Mode lokal: _auth_ok memakai _ensure_user() (perilaku desktop
        # yang memang dijaga P1) — tanpa header pun terautentikasi.
        req = urllib.request.Request(f"{self.base}{path}")
        start = time.perf_counter()
        with urllib.request.urlopen(req, timeout=20) as resp:
            resp.read()
        return (time.perf_counter() - start) * 1000

    def test_key_endpoints_within_budget(self):
        # Pemanasan 1x (impor malas + koneksi pertama), lalu median 5x.
        report = {}
        for path, budget in BUDGET_MS.items():
            self._timed_get(path)
            samples = [self._timed_get(path) for _ in range(5)]
            median = statistics.median(samples)
            report[path] = round(median, 1)
            self.assertLess(median, budget,
                            f"{path} median {median:.0f} ms > {budget} ms")
        print("\nM13 perf median (ms):", json.dumps(report))

    def test_bootstrap_payload_not_exploding(self):
        req = urllib.request.Request(f"{self.base}/api/bootstrap")
        with urllib.request.urlopen(req, timeout=20) as resp:
            size = len(resp.read())
        # DB uji nyaris kosong; yang dijaga: tidak ada muatan statis raksasa
        # yang ikut terkirim per panggilan (katalog dsb. punya endpointnya).
        self.assertLess(size, 2 * 1024 * 1024, f"bootstrap {size} byte")
