# CraftLife Rules API — image server headless (M05 butir 1).
#
# APA YANG DIVERIFIKASI, DAN APA YANG TIDAK
# -----------------------------------------
# Docker TIDAK tersedia di lingkungan pengembangan tempat image ini ditulis,
# jadi **image ini belum pernah di-build**. Yang sudah diverifikasi lewat
# `tests/test_m05_container.py`:
#
#   * setiap berkas yang di-COPY di sini benar-benar ada di repo;
#   * `requirements-server.txt` menutup SEMUA impor pihak ketiga telanjang di
#     modul server (diturunkan lewat AST, bukan ditulis dari ingatan);
#   * tidak ada paket karangan — setiap entri ada di `requirements.txt`;
#   * entrypoint yang dideklarasikan di CMD benar-benar menyala dan menjawab
#     `/api/health` serta `/api/version` saat dijalankan persis seperti di
#     dalam container (env sama, direktori kerja bersih).
#
# Yang belum terbukti: `docker build` itu sendiri. Jalankan
# `docker build -f Dockerfile -t craftlife-api .` sebelum memakainya.
#
# Kenapa tidak memakai requirements.txt
# -------------------------------------
# `requirements.txt` menarik PyQt6, PyQt6-WebEngine, matplotlib, PyMuPDF,
# yt-dlp, dan Edge-TTS — semuanya milik desktop. Server tidak membutuhkan
# satu pun. Satu-satunya impor PyQt6 di jalur server ada di `database.py:49`
# dan sudah dibungkus `try/except ImportError`, jadi image headless aman
# tanpanya. Memakai daftar penuh akan membuat image beberapa ratus MB lebih
# besar tanpa menambah satu pun kemampuan.

FROM python:3.12-slim AS runtime

# Python tidak menulis .pyc dan tidak mem-buffer stdout, supaya log container
# muncul saat itu juga — tanpa ini `docker logs` terlihat menggantung.
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# curl dipakai HEALTHCHECK. tini memberi PID 1 yang meneruskan sinyal, sehingga
# `docker stop` menutup server dengan anggun alih-alih menunggu timeout SIGKILL.
RUN apt-get update \
 && apt-get install -y --no-install-recommends curl tini \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements-server.txt ./
RUN pip install --no-cache-dir -r requirements-server.txt

# Hanya modul server. `web/`, `MainPyQt6.py`, dan artefak runtime sengaja tidak
# ikut — lihat .dockerignore.
#
# Daftar ini DITURUNKAN dari impor nyata modul server lewat AST, dan
# `tests/test_m05_container.py` menegakkannya: kalau seseorang menambah modul
# lokal baru yang diimpor server, tes itu gagal sampai daftarnya diperbarui.
# Versi pertama Dockerfile ini menyebut `logger.py` yang tidak ada dan
# melupakan sepuluh modul yang benar-benar dipakai — termasuk `applog`, yang
# diimpor `database.py` di baris 30, sehingga server tidak akan start sama
# sekali.
COPY api_server.py database.py cloud_api.py studio_api.py life_api.py \
     cloud_service.py cloud_config.py storage.py storage_postgres.py \
     translations.py updater.py \
     applog.py food_data.py holidays.py learning_helper.py mathtools.py \
     music_downloader.py rules_auth.py rules_guard.py sync_service.py \
     web_shell.py ./

# Data dan cadangan hidup di volume, bukan di lapisan image.
RUN mkdir -p /data/backups && chown -R 10001:0 /data /app

# Jalan sebagai pengguna non-root. Kalau server ini suatu hari terekspos,
# penyerang yang menembusnya tidak langsung memegang root container.
USER 10001

# 0.0.0.0, bukan 127.0.0.1: di dalam container, loopback tidak terjangkau dari
# luar. Ini juga alasan `docker run -p` akan gagal kalau host dibiarkan default.
ENV CRAFTLIFE_API_HOST=0.0.0.0 \
    CRAFTLIFE_API_PORT=8765 \
    CRAFTLIFE_DATA_DIR=/data

EXPOSE 8765

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
  CMD curl -fsS "http://127.0.0.1:8765/api/health" || exit 1

ENTRYPOINT ["/usr/bin/tini", "--"]
CMD ["python", "api_server.py"]
