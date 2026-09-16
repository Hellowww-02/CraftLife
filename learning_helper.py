# pyright: reportMissingImports=false
# -*- coding: utf-8 -*-
"""
learning_helper.py — Backend untuk Learning Page ala NotebookLM
Mendukung Gemini API (cloud) dengan fallback mock jika tidak ada API key.
"""

import os
import re
import json
import textwrap
import traceback

# A08: SDK resmi saat ini adalah `google.genai` (paket `google-genai`).
# `google.generativeai` sudah END OF SUPPORT (tidak lagi menerima update/bugfix),
# jadi ia hanya dipakai sebagai jaring pengaman bila `google.genai` belum terpasang.
genai = None                     # modul SDK yang aktif (baru ATAU lama)
LEGACY_SDK = False               # True bila terpaksa memakai google.generativeai
SDK_NAME = "google.genai"
try:
    from google import genai  # type: ignore  # paket: google-genai
    GEMINI_AVAILABLE = True
    GEMINI_IMPORT_ERROR = ""
except Exception as e:
    try:
        import google.generativeai as genai  # type: ignore  # deprecated
        GEMINI_AVAILABLE = True
        GEMINI_IMPORT_ERROR = ""
        LEGACY_SDK = True
        SDK_NAME = "google.generativeai"
        print(
            "[learning_helper] PERINGATAN: `google.genai` tidak ditemukan — memakai "
            "`google.generativeai` yang sudah END OF SUPPORT. Jalankan: pip install -U google-genai"
        )
    except Exception as e2:
        # Optional AI dependency must never prevent the whole desktop app from starting.
        GEMINI_AVAILABLE = False
        GEMINI_IMPORT_ERROR = f"{e} / {e2}"
        genai = None

# ── Chunking ─────────────────────────────────────────────────────────────
def chunk_text(text: str, chunk_size: int = 800, overlap: int = 100):
    """Potong text jadi chunks untuk RAG."""
    if not text:
        return []
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunk = text[start:end]
        # Coba potong di titik terdekat biar rapi
        if end < len(text):
            last_dot = chunk.rfind('. ')
            if last_dot > chunk_size * 0.6:
                chunk = chunk[:last_dot+1]
                end = start + len(chunk)
        chunks.append(chunk.strip())
        start = end - overlap
        if start < 0:
            start = 0
        if start >= len(text):
            break
    return [c for c in chunks if c.strip()]

# ── Extractors ───────────────────────────────────────────────────────────
def extract_from_pdf(path: str) -> str:
    try:
        # Coba PyMuPDF dulu (paling bagus)
        import fitz  # type: ignore
        doc = fitz.open(path)
        text = ""
        for page in doc:
            text += page.get_text() + "\n"
        return text
    except ImportError:
        pass
    try:
        import PyPDF2  # type: ignore
        reader = PyPDF2.PdfReader(path)
        text = ""
        for page in reader.pages:
            text += (page.extract_text() or "") + "\n"
        return text
    except Exception as e:
        return f"[Gagal baca PDF: {e}]"

def extract_from_docx(path: str) -> str:
    try:
        from docx import Document
        doc = Document(path)
        return "\n".join([p.text for p in doc.paragraphs])
    except Exception as e:
        return f"[Gagal baca DOCX: {e}]"

def extract_from_txt(path: str) -> str:
    try:
        with open(path, 'r', encoding='utf-8', errors='ignore') as f:
            return f.read()
    except:
        try:
            with open(path, 'r', encoding='latin-1') as f:
                return f.read()
        except Exception as e:
            return f"[Gagal baca TXT: {e}]"

def fetch_website_text(url: str) -> str:
    try:
        import requests
        from html.parser import HTMLParser
        class TextExtractor(HTMLParser):
            def __init__(self):
                super().__init__()
                self.texts = []
                self.skip = False
            def handle_starttag(self, tag, attrs):
                if tag in ('script','style','nav','header','footer'):
                    self.skip = True
            def handle_endtag(self, tag):
                if tag in ('script','style','nav','header','footer'):
                    self.skip = False
            def handle_data(self, data):
                if not self.skip and data.strip():
                    self.texts.append(data.strip())
        resp = requests.get(url, timeout=10, headers={'User-Agent':'Mozilla/5.0'})
        resp.raise_for_status()
        parser = TextExtractor()
        parser.feed(resp.text)
        text = " ".join(parser.texts)
        # Bersihkan whitespace
        text = re.sub(r'\s+', ' ', text)
        return text[:50000]  # batasi 50k char
    except Exception as e:
        return f"[Gagal fetch website: {e}]"

def fetch_youtube_transcript(url: str) -> str:
    # Coba youtube-transcript-api
    try:
        from youtube_transcript_api import YouTubeTranscriptApi  # type: ignore
        # Extract video id
        vid = None
        if "v=" in url:
            vid = url.split("v=")[1].split("&")[0]
        elif "youtu.be/" in url:
            vid = url.split("youtu.be/")[1].split("?")[0]
        elif "youtube.com" in url:
            # fallback
            m = re.search(r'v=([A-Za-z0-9_-]{11})', url)
            if m:
                vid = m.group(1)
        if vid:
            trans = YouTubeTranscriptApi.get_transcript(vid, languages=['id','en'])
            text = " ".join([t['text'] for t in trans])
            return text
    except Exception:
        pass
    # Fallback: coba pakai yt-dlp untuk ambil auto subtitle? Untuk MVP, kasih pesan
    return "[Transcript Youtube tidak ditemukan. Coba paste manual transcript atau gunakan link website.]"

# ── Gemini ───────────────────────────────────────────────────────────────
def _clean_model_name(model_name: str) -> str:
    """`models/gemini-2.5-flash` → `gemini-2.5-flash` (SDK baru tidak pakai prefix)."""
    name = str(model_name or "").strip().replace("models/", "")
    if name == "gemini-pro":
        name = "gemini-1.5-flash"
    return name


def _new_sdk_client(api_key: str):
    """Buat klien `google.genai`. Dipisah agar mudah di-mock saat uji."""
    return genai.Client(api_key=api_key.strip())


def _extract_text(resp) -> str:
    """Ambil teks dari respons SDK (dua bentuk: `.text` atau daftar `parts`)."""
    text = getattr(resp, "text", None)
    if text:
        return text
    try:
        parts = resp.candidates[0].content.parts
        return "".join([p.text for p in parts if getattr(p, "text", None)])
    except Exception:
        return ""


def _generate_once(api_key: str, model_name: str, prompt: str, temperature: float = 0.7) -> str:
    """Satu panggilan generate dengan SDK aktif. Raise RuntimeError bila gagal."""
    clean_name = _clean_model_name(model_name)
    if LEGACY_SDK:
        genai.configure(api_key=api_key.strip())  # type: ignore[attr-defined]
        model = genai.GenerativeModel(clean_name)  # type: ignore[attr-defined]
        resp = model.generate_content(prompt, generation_config={"temperature": temperature})
        if not getattr(resp, "candidates", None):
            raise RuntimeError("blocked")
        return _extract_text(resp)
    from google.genai import types  # type: ignore
    client = _new_sdk_client(api_key)
    resp = client.models.generate_content(
        model=clean_name,
        contents=prompt,
        config=types.GenerateContentConfig(temperature=temperature),
    )
    text = _extract_text(resp)
    if not text:
        raise RuntimeError("empty response")
    return text


def _get_model(api_key: str, model_name: str = "gemini-2.5-flash"):
    """Validasi API key & kembalikan penanda model yang siap dipakai.

    A08: hanya untuk kompatibilitas pemanggil lama (`call_gemini` kini memakai
    `_generate_once`). Mengembalikan `((sdk, clean_name), None)` atau `(None, pesan)`.
    """
    if not api_key or not api_key.strip():
        return None, "API Key Gemini belum diisi. Isi di Settings → Learning AI"
    if not (api_key.startswith("AIza") or api_key.startswith("AQ.")):
        return None, "API Key terlihat tidak valid (harus diawali AIza... atau AQ...)"
    if not GEMINI_AVAILABLE:
        return None, GEMINI_IMPORT_ERROR or "SDK Gemini belum terpasang"
    return (SDK_NAME, _clean_model_name(model_name)), None


def call_gemini(prompt: str, api_key: str, system_instruction: str = None, model_name: str = "gemini-2.5-flash", temperature: float = 0.7) -> str:
    """Panggil Gemini (SDK `google.genai`) dengan fallback model bila 429/404.

    Return teks jawaban, atau pesan ramah-pengguna (prefixed `[MOCK ...]`) yang
    membuat UI tetap bisa menampilkan sesuatu walau key/quota bermasalah.
    """
    models_to_try = [
        model_name,
        "gemini-2.5-flash",
        "gemini-2.5-pro",
        "gemini-2.5-flash-lite",
        "gemini-2.0-flash",
        "gemini-1.5-flash",
        "gemma-4-26b-a4b-it",
    ]
    seen = set()
    unique_models = []
    for m in models_to_try:
        clean = _clean_model_name(m)
        if clean and clean not in seen:
            seen.add(clean)
            unique_models.append(m)

    full_prompt = prompt
    if system_instruction:
        full_prompt = f"System: {system_instruction}\n\nUser: {prompt}"

    if not GEMINI_AVAILABLE:
        return (
            f"[MOCK - {GEMINI_IMPORT_ERROR}]\n\nPrompt preview:\n{prompt[:600]}..."
            "\n\nPasang SDK: pip install -U google-genai (isi API Key di Learning → 🔑 API Key)."
        )
    if not api_key or not api_key.strip():
        return "[MOCK - API key belum diisi]\n\nIsi API Key Gemini di Learning → 🔑 API Key untuk hasil real."

    last_error = None
    for m in unique_models:
        try:
            return _generate_once(api_key, m, full_prompt, temperature)
        except Exception as e:
            err_str = str(e)
            last_error = err_str
            if any(tok in err_str.lower() for tok in ("429", "quota", "exceeded", "404", "not found", "empty response")):
                print(f"[Gemini] {_clean_model_name(m)} tidak tersedia/quota, coba model berikutnya...")
                continue
            traceback.print_exc()
            return f"[Error Gemini ({_clean_model_name(m)}): {e}]"

    # Semua model gagal → coba satu model apa pun yang benar-benar tersedia.
    hint = ""
    try:
        if not LEGACY_SDK:
            client = _new_sdk_client(api_key)
            names = [getattr(x, "name", "") for x in client.models.list()]
            names = [n for n in names if n]
            if names:
                hint = f"\nModels tersedia: {', '.join(names[:5])}"
                for n in names[:3]:
                    if _clean_model_name(n) in seen:
                        continue
                    try:
                        return _generate_once(api_key, n, full_prompt, temperature)
                    except Exception:
                        continue
    except Exception as e:
        hint = f"\nListModels gagal: {e}"

    sdk_hint = (
        "SDK aktif: **google.genai** ✅"
        if not LEGACY_SDK
        else "SDK aktif: google.generativeai ⚠️ (deprecated) → jalankan `pip install -U google-genai`"
    )
    return (
        "[Quota/Model Error] Gemini menolak semua model.\n\n"
        f"{sdk_hint}\n\n"
        "Penyebab paling sering untuk key baru `AQ...`:\n"
        "1. **Generative Language API belum di-Enable** (404) → Buka https://console.cloud.google.com/apis/library/generativelanguage.googleapis.com → pilih project → **Enable** → tunggu 1 menit\n"
        "2. Quota 0 → tunggu 2 menit atau buat key baru di **New Project**\n"
        "3. Model lama (gemini-pro/1.5-pro) sudah deprecate → sudah di-handle otomatis\n\n"
        "Langkah cepat:\n"
        "1. Enable API di link atas\n"
        "2. pip install -U google-genai\n"
        "3. Coba chat lagi dengan topik simpel `hai`\n"
        "4. Cek https://aistudio.google.com/app/apikey → Usage\n\n"
        f"Detail: {str(last_error)[:600] if last_error else 'Unknown'}{hint}"
    )


# ── RAG sederhana (keyword search, tanpa vector DB) ─────────────────────
def find_relevant_chunks(all_chunks: list, query: str, top_k: int = 3):
    """Cari chunks paling relevan via keyword overlap (simple BM25-like)."""
    if not all_chunks or not query:
        return all_chunks[:top_k]
    q_words = set(re.findall(r'\w+', query.lower()))
    scored = []
    for chunk in all_chunks:
        c_words = set(re.findall(r'\w+', chunk.lower()))
        # Jaccard + length bonus
        overlap = len(q_words & c_words)
        # Bonus jika ada frase exact
        bonus = 2 if query.lower() in chunk.lower() else 0
        score = overlap + bonus
        # Panjang chunk yang mirip query lebih tinggi
        scored.append((score, chunk))
    scored.sort(key=lambda x: x[0], reverse=True)
    # Ambil top_k, jika score 0 semua, ambil chunk pertama
    result = [c for s,c in scored[:top_k] if s>0]
    if not result:
        result = [c for _,c in scored[:top_k]]
    return result

# ── Language detection for generated audio ─────────────────────────────
_LANGUAGE_NAMES = {
    "id": "bahasa Indonesia", "en": "English", "es": "español",
    "fr": "français", "de": "Deutsch", "ja": "日本語", "ko": "한국어",
    "zh": "中文", "pt": "português", "ar": "العربية", "ru": "русский",
}


def detect_content_language(text: str) -> str:
    """Detect the dominant language from user/transcript text, independent of app settings."""
    sample = str(text or "").lower()
    if re.search(r"[\u3040-\u30ff]", sample):
        return "ja"
    if re.search(r"[\uac00-\ud7af]", sample):
        return "ko"
    if re.search(r"[\u0600-\u06ff]", sample):
        return "ar"
    if re.search(r"[\u0400-\u04ff]", sample):
        return "ru"
    if re.search(r"[\u4e00-\u9fff]", sample):
        return "zh"

    words = re.findall(r"[a-zà-ÿ]+", sample)
    counts = {key: 0 for key in ("id", "en", "es", "fr", "de", "pt")}
    stopwords = {
        "id": {"yang", "dan", "atau", "dengan", "untuk", "dari", "adalah", "tidak", "ini", "itu", "kita", "mari", "bagaimana", "mengapa", "karena", "dalam", "akan", "bisa", "sudah", "belum", "sebagai", "pada", "juga", "jadi", "tentang", "saya", "kamu", "jelaskan", "pelajari", "bahas", "contoh", "ringkas"},
        "en": {"the", "and", "or", "with", "for", "from", "is", "are", "this", "that", "we", "you", "how", "why", "because", "in", "will", "can", "have", "has", "as", "on", "also", "about", "what", "let", "please", "explain", "learn", "today", "discuss", "example", "summarize"},
        "es": {"el", "la", "los", "las", "y", "con", "para", "desde", "es", "son", "esto", "que", "nosotros", "como", "por", "porque", "en", "puede", "también"},
        "fr": {"le", "la", "les", "et", "avec", "pour", "depuis", "est", "sont", "ce", "que", "nous", "vous", "comment", "pourquoi", "dans", "peut", "aussi"},
        "de": {"der", "die", "das", "und", "oder", "mit", "für", "von", "ist", "sind", "dies", "wir", "sie", "wie", "warum", "weil", "kann", "auch"},
        "pt": {"o", "a", "os", "as", "e", "com", "para", "de", "é", "são", "isso", "que", "nós", "como", "porque", "em", "pode", "também"},
    }
    for word in words:
        for language, vocabulary in stopwords.items():
            if word in vocabulary:
                counts[language] += 1
    best = max(counts, key=counts.get)
    if counts[best] > 0:
        return best
    # Indonesian is the product's primary content language; use it only when
    # the actual text provides no detectable signal.
    return "id"


def language_display_name(language: str) -> str:
    return _LANGUAGE_NAMES.get(language, language.upper() if language else "")


def podcast_voice_pair(language: str, seed_text: str = ""):
    """Choose a locale-correct pair; English has several deterministic variations."""
    language = language if language in _LANGUAGE_NAMES else "en"
    pairs = {
        "id": [("id-ID-ArdiNeural", "id-ID-GadisNeural")],
        "en": [
            ("en-US-AndrewNeural", "en-US-AvaNeural"),
            ("en-US-BrianNeural", "en-US-EmmaNeural"),
            ("en-US-GuyNeural", "en-US-JennyNeural"),
        ],
        "es": [("es-ES-AlvaroNeural", "es-ES-XimenaNeural")],
        "fr": [("fr-FR-HenriNeural", "fr-FR-DeniseNeural")],
        "de": [("de-DE-ConradNeural", "de-DE-KatjaNeural")],
        "ja": [("ja-JP-KeitaNeural", "ja-JP-NanamiNeural")],
        "ko": [("ko-KR-InJoonNeural", "ko-KR-SunHiNeural")],
        "zh": [("zh-CN-YunxiNeural", "zh-CN-XiaoxiaoNeural")],
        "pt": [("pt-BR-AntonioNeural", "pt-BR-FranciscaNeural")],
        "ar": [("ar-SA-HamedNeural", "ar-SA-ZariyahNeural")],
        "ru": [("ru-RU-DmitryNeural", "ru-RU-SvetlanaNeural")],
    }
    options = pairs[language]
    index = sum(ord(char) for char in str(seed_text or "")) % len(options)
    return options[index]


# ── Studio Generators ────────────────────────────────────────────────────
def generate_studio_content(studio_type: str, query: str, context_chunks: list, api_key: str,
                            language_hint: str = None, count: int = None,
                            mc_count: int = None, essay_count: int = None,
                            difficulty: str = None, language: str = None, style: str = None,
                            length: str = None, depth: int = None, branches: int = None,
                            subs: int = None, sections: list = None, exercises: int = None,
                            faq_count: int = None, granularity: str = None,
                            absolute_dates: bool = None, focus: str = None,
                            instructions: str = None) -> str:
    """Generate konten Studio berdasarkan type.

    A04: quiz memakai DUA counter terpisah — `mc_count` (pilihan ganda) dan `essay_count`
    (esai), masing-masing 0–30 dan **total gabungan ≤ 30** (dijaga di sini juga, bukan
    hanya di UI). Default bila tidak dikirim: **10 PG + 5 esai**.
    `count` lama tetap dihormati (backward compatible) → dibagi 2/3 PG : 1/3 esai;
    `count` juga masih dipakai flashcards (5–30, default 15).

    A05: opsi konfigurasi per tipe (semua OPSIONAL). Bila tidak ada satu pun yang dikirim,
    prompt & hasil **identik dengan sebelumnya** (zero-regression):
      - `difficulty`  : easy | mixed | hard            (quiz, flashcards)
      - `language`    : id | en                        (semua tipe; None = deteksi otomatis)
      - `style`       : term|qa|formula (kartu) · casual|formal|debate (podcast)
                        brief|detail (FAQ jawaban) · bullets|narrative (ringkasan)
      - `length`      : short | standard | deep        (podcast jumlah giliran, ringkasan kata)
      - `depth`/`branches`/`subs` : mind map (1–3 / 3–8 / 2–6)
      - `sections`    : study guide (summary, concepts, examples, practice, conclusion)
      - `exercises`   : study guide 3–10 soal latihan
      - `faq_count`   : FAQ 5–15 Q&A
      - `granularity` : day|week|month|year + `absolute_dates` (timeline)
      - `focus` / `instructions` : arahan bebas user (ditempel ke prompt tipe apa pun)
    """
    context = "\n\n---\n\n".join(context_chunks[:6])  # batasi 6 chunks biar tidak kepanjangan
    if not context.strip():
        context = "(Tidak ada source, jawab berdasarkan pengetahuan umum)"
    detected_language = language_hint or detect_content_language(
        f"{query}\n{' '.join(context_chunks[:3])}"
    )
    # A05: opsi bahasa user mengalahkan deteksi otomatis (kecuali 'auto'/None).
    if language in ("id", "en"):
        detected_language = language
    language_name = _LANGUAGE_NAMES.get(detected_language, "English")
    try:
        n = int(count)
    except (TypeError, ValueError):
        n = 0

    def _clamp_cnt(value, lo, hi):
        if value is None or value == "":
            return None
        try:
            return max(lo, min(hi, int(value)))
        except (TypeError, ValueError):
            return None

    # A04: dua counter terpisah — Pilihan Ganda & Essay (default 10 + 5, total ≤ 30).
    mc_in = _clamp_cnt(mc_count, 0, 30)
    essay_in = _clamp_cnt(essay_count, 0, 30)
    if studio_type == "quiz":
        if mc_in is None and essay_in is None:
            # Jalur lama (backward compatible): satu `count` (default 15) → 2/3 PG : 1/3 esai.
            total = max(10, min(30, n or 15))
            quiz_mc = min(total, max(0, round(total * 2 / 3)))
            quiz_essay = total - quiz_mc
        else:
            quiz_mc = mc_in if mc_in is not None else 0
            quiz_essay = essay_in if essay_in is not None else 0
            if quiz_mc + quiz_essay <= 0:
                quiz_mc, quiz_essay = 10, 5          # tidak boleh 0 soal sama sekali
            if quiz_mc + quiz_essay > 30:
                # Guard sisi server: total gabungan maksimum 30 soal.
                quiz_essay = max(0, 30 - min(30, quiz_mc))
        quiz_count = quiz_mc + quiz_essay
    else:
        quiz_count, quiz_mc, quiz_essay = 15, 10, 5
    if studio_type == "flashcards":
        # A05: rentang kartu 5–30 (dulu 10–30) — default tetap 15.
        n = max(5, min(30, n or 15))
    flash_count = n if studio_type == "flashcards" else 15

    # A04: catatan tambahan di prompt bila salah satu jenis soal dimatikan (0 soal).
    count_note = ""
    if studio_type == "quiz":
        if quiz_mc == 0:
            count_note = "JANGAN buat soal pilihan ganda sama sekali (hanya esai)."
        elif quiz_essay == 0:
            count_note = "JANGAN buat soal esai sama sekali (hanya pilihan ganda)."
        else:
            count_note = "Campur keduanya sesuai jumlah di atas."

    # ══════════════════════════════════════════════════════════════════════════
    #  A05 — opsi konfigurasi per tipe (semua opsional, default = perilaku lama)
    # ══════════════════════════════════════════════════════════════════════════
    _diff_map = {
        "easy": "MUDAH — fokus ingatan & pemahaman dasar, kalimat sederhana.",
        "mixed": "CAMPURAN — variasikan dari ingatan dasar sampai penerapan.",
        "hard": "SULIT — dominan analisis, sintesis, dan studi kasus kompleks.",
    }
    difficulty_line = (f"\nTINGKAT KESULITAN: {_diff_map[difficulty]}"
                       if difficulty in _diff_map else "")

    focus_line = f"\nFOKUS KHUSUS (utamakan bagian ini): {str(focus).strip()}" if str(focus or "").strip() else ""
    instr_line = (f"\nINSTRUKSI TAMBAHAN DARI USER (WAJIB dipatuhi selama tidak melanggar format output): "
                  f"{str(instructions).strip()}") if str(instructions or "").strip() else ""
    # Ditempel ke SEMUA prompt di bawah (durutan: kesulitan → fokus → instruksi).
    extra = difficulty_line + focus_line + instr_line

    # Podcast / Audio Overview
    _host_map = {
        "casual": "Santai & akrab — bahasa sehari-hari, sesekali lelucon ringan, seperti dua teman ngobrol.",
        "formal": "Formal & edukatif — bahasa baku dan sopan, penjelasan runut dan terstruktur.",
        "debate": "Diskusi kritis — Host B aktif menantang asumsi Host A, ada bantahan dan sanggahan sehat.",
    }
    _turns_map = {"short": "6-8", "standard": "14-24", "deep": "26-36"}
    host_note = _host_map.get(style, "")
    host_line = f"\nGAYA PEMBAWA ACARA: {host_note}" if host_note else ""
    turns_line = _turns_map.get(length, "14-24")

    # Flashcards
    _card_map = {
        "term": "Setiap kartu: sisi depan = ISTILAH/konsep singkat, sisi belakang = DEFINISI jelas. Buat kartu istilah kunci.",
        "qa": "Setiap kartu: sisi depan = PERTANYAAN, sisi belakang = JAWABAN singkat dan jelas.",
        "formula": "Setiap kartu: sisi depan = RUMUS/ekspresi (tulis teksnya bila tidak bisa simbol), sisi belakang = ARTI & penggunaan rumus.",
    }
    card_line = f"\nGAYA KARTU: {_card_map[style]}" if style in _card_map else ""

    # Mind map
    depth_i = _clamp_cnt(depth, 1, 3) or 2
    branches_i = _clamp_cnt(branches, 3, 8) or 5
    subs_i = _clamp_cnt(subs, 2, 6) or 3
    if depth_i == 1:
        mind_line = (f"\nSTRUKTUR: {branches_i} cabang utama, tiap cabang {subs_i} sub (satu tingkat, "
                     f"sub berupa teks biasa — JANGAN bercabang lagi).")
    else:
        mind_line = (f"\nSTRUKTUR: {branches_i} cabang utama, tiap cabang {subs_i} sub. Kedalaman maksimum "
                     f"{depth_i} tingkat — sub boleh berupa object {{\"label\": \"...\", \"children\": [...]}} "
                     f"untuk tingkat lanjutan, atau teks biasa bila sudah paling dalam.")

    # Study guide
    _sec_names = {
        "summary": "Ringkasan Utama", "concepts": "Konsep Kunci (dengan penjelasan)",
        "examples": "Contoh Penting", "practice": "Latihan Soal", "conclusion": "Kesimpulan",
    }
    sec_list = [k for k in ("summary", "concepts", "examples", "practice", "conclusion")
                if isinstance(sections, (list, tuple)) and k in sections]
    if not sec_list:
        sec_list = ["summary", "concepts", "examples", "practice", "conclusion"]
    exercises_i = _clamp_cnt(exercises, 3, 10) or 3
    sec_lines = "\n".join(
        f"## {i + 1}. {_sec_names[k]}" + (f" ({exercises_i} soal + jawaban)" if k == "practice" else "")
        for i, k in enumerate(sec_list)
    )

    # FAQ
    faq_i = _clamp_cnt(faq_count, 5, 15) or 8
    _ans_map = {
        "brief": "Singkat: 1-2 kalimat langsung ke inti.",
        "detail": "Detail: 1 paragraf pendek (3-5 kalimat) yang menjelaskan alasan/contoh.",
    }
    faq_style_line = f"\nGAYA JAWABAN: {_ans_map[style]}" if style in _ans_map else ""

    # Timeline
    _gran_map = {
        "day": "Harian (format tanggal YYYY-MM-DD bila tersedia)",
        "week": "Mingguan (mis. Minggu ke-1 / pekan tanggal ...)",
        "month": "Bulanan (mis. Januari 2024)",
        "year": "Tahunan (mis. 2024)",
    }
    gran_line = f"\nGRANULARITAS WAKTU: {_gran_map[granularity]}." if granularity in _gran_map else ""
    abs_line = ("\nSertakan tanggal/kurun waktu absolut bila sumber menyebutkannya."
                if absolute_dates else
                "\nJANGAN mengarang tanggal absolut; pakai urutan relatif (Tahap 1, 2, 3) bila sumber tidak jelas.")

    # Summary
    _sum_len = {"short": "maksimal 150 kata", "standard": "sekitar 200-400 kata",
                "deep": "mendalam, 500-800 kata dengan sub-poin"}
    sum_len_line = f"\nPANJANG: {_sum_len[length]}" if length in _sum_len else ""
    _sum_style = {"bullets": "Gaya Poin-poin: bullet list ringkas per ide utama.",
                  "narrative": "Gaya Naratif: paragraf mengalir yang saling terhubung."}
    sum_style_line = f"\nGAYA: {_sum_style[style]}" if style in _sum_style else ""

    prompts = {
        "audio_overview": f"""Buat dialog podcast edukasi dengan DUA HOST yang benar-benar saling berbicara, bertanya, menanggapi, dan menyimpulkan materi.

BAHASA OUTPUT WAJIB: {language_name}. Gunakan bahasa ini untuk SETIAP giliran percakapan, terlepas dari bahasa antarmuka aplikasi.{host_line}{extra}

KARAKTER HOST:
- Host A: pembawa acara utama yang hangat, percaya diri, terstruktur, dan pandai menjelaskan konsep rumit dengan analogi.
- Host B: co-host yang penasaran, spontan, kritis, kadang humoris, aktif bertanya, memberi contoh, menantang asumsi, dan merangkum dengan bahasanya sendiri.

ALUR KREATIF:
- Mulai dengan cold open atau pertanyaan pemancing yang langsung menarik perhatian.
- Buat {turns_line} giliran bicara yang bergantian secara natural.
- Variasikan panjang giliran: reaksi singkat, pertanyaan tajam, penjelasan, contoh sehari-hari, mini-kuis, dan rangkuman.
- Sisipkan minimal satu analogi, satu contoh konkret, satu momen salah paham yang diluruskan, dan satu mini-kuis.
- Akhiri dengan takeaway yang kuat dan ajakan mencoba menerapkan materi.
- Hindari pengulangan frasa seperti “menarik”, “pertanyaan bagus”, atau pola tanya-jawab yang monoton.
- Setiap giliran maksimal 1-3 kalimat agar terdengar seperti percakapan asli.
- Jangan tulis narator, judul, heading, bullet list, petunjuk panggung, efek suara, atau teks di luar dialog.
- Jangan gunakan Markdown.
- Jika ada rumus, tuliskan cara mengucapkannya secara natural dalam {language_name}, bukan simbol LaTeX mentah.
- Output HANYA baris dialog dengan format mesin berikut, satu giliran per baris:
HOST_A|Kalimat pembuka yang menarik...
HOST_B|Tanggapan atau pertanyaan yang natural...
HOST_A|Penjelasan dengan analogi atau contoh...
HOST_B|Respons, tantangan, atau rangkuman...

Konteks:\n{context}\n\nTopik: {query or 'Rangkum semua sources'}""",

        "mind_map": f"""Buatkan struktur MIND MAP dalam format JSON untuk visualisasi.{mind_line}
Bahasa label: {language_name}.{extra}
Konteks:\n{context}\n\nTopik: {query or 'Topik utama'}

Format JSON WAJIB seperti ini (jangan tambah markdown):
{{"central": "Topik Utama", "branches": [{{"label": "Cabang 1", "children": [{{"label": "sub 1", "children": [{{"label": "anak 1", "children": []}}]}}, "sub 2"]}}, {{"label": "Cabang 2", "children": []}}]}}
Setiap elemen `children` boleh berupa teks ATAU object {{"label": ..., "children": [...]}} (maksimal kedalaman {depth_i}).""",

        "study_guide": f"""Buatkan STUDY GUIDE lengkap dari konteks berikut.
Bahasa: {language_name}.{extra}
Konteks:\n{context}\n\nBuat dengan format (HANYA bagian berikut, urut, tanpa bagian lain):
# Study Guide: [Judul]
{sec_lines}
Topik: {query or 'Semua materi'}""",

        "quiz": f"""Buatkan QUIZ interaktif (seperti fitur Quiz di NotebookLM) dari konteks berikut.
Konteks:\n{context}\n\nTopik: {query or 'Semua materi'}

BAHASA OUTPUT WAJIB: {language_name} untuk seluruh pertanyaan, opsi, dan penjelasan.{extra}

ATURAN OUTPUT WAJIB:
- Output HANYA satu JSON object valid tanpa teks lain, tanpa Markdown, tanpa code fence.
- Buat TEPAT {quiz_count} pertanyaan: {quiz_mc} pilihan ganda ("type":"mc") dan {quiz_essay} esai ("type":"essay"). {count_note}
- WAJIB: SETIAP soal punya field "type" bernilai "mc" atau "essay" — tanpa field ini aplikasi tidak bisa mengenali/menilai soal tersebut.
- Pilihan ganda ("type":"mc"): 4 opsi, tepat satu jawaban benar (index 0-3), plus penjelasan singkat mengapa benar.
- Esai ("type":"essay"): JANGAN sertakan "options"; WAJIB sertakan "model_answer" berisi jawaban contoh yang baik dan lengkap (2-5 kalimat).
- Variasikan kesulitan: ingatan, pemahaman, penerapan, analisis.
ATURAN JSON KETAT (WAJIB DIPATUHI):
- Setiap key WAJIB diikuti titik dua (:) — JANGAN pernah menulis koma setelah nama key (contoh SALAH: "q","teks").
- Key penjelasan WAJIB bernama "explain" (BUKAN "explanation").
- JANGAN tambah koma di akhir objek/array (no trailing comma).
- Semua teks memakai tanda kutip ganda; hindari tanda kutip ganda di dalam teks.
Format persis:
{{"title":"Judul Quiz","questions":[{{"type":"mc","q":"Pertanyaan?","options":["A","B","C","D"],"answer":0,"explain":"Karena..."}},{{"type":"essay","q":"Jelaskan...","model_answer":"Jawaban contoh..."}}]}}""",

        "faq": f"""Buatkan FAQ berisi TEPAT {faq_i} pertanyaan dari konteks.
Bahasa: {language_name}.{faq_style_line}{extra}
Konteks:\n{context}\n\nFormat (mulai dari Q1, tanpa pembuka):
Q1: ...
A1: ...
Q2: ...
A2: ...
Topik: {query or 'Umum'}""",

        "timeline": f"""Buatkan TIMELINE kronologis dari konteks.
Bahasa: {language_name}.{gran_line}{abs_line}{extra}
Konteks:\n{context}\n\nFormat:
- **2024-01-15 / Tahap 1:** Deskripsi
- **Februari 2024:** ...
Jika tidak ada tanggal, buat urutan logis Tahap 1,2,3...
Topik: {query or 'Urutan'}""",

        "flashcards": f"""Buatkan {flash_count} FLASHCARDS interaktif untuk belajar dari konteks berikut.
Bahasa: {language_name}.{card_line}{extra}
Konteks:\n{context}\n\nTopik: {query or 'Materi'}

ATURAN OUTPUT WAJIB:
- Output HANYA JSON array valid. Jangan tulis pembuka, penutup, Markdown, atau code fence.
- Setiap item WAJIB memiliki key "front" dan "back".
- Variasikan kartu: konsep, contoh, perbandingan, benar/salah, penerapan, dan mini problem (sesuai gaya kartu di atas).
- Pertanyaan singkat dan jelas; jawaban padat tetapi cukup menjelaskan.
Format persis:
[{{"front":"Pertanyaan 1","back":"Jawaban 1"}},{{"front":"Pertanyaan 2","back":"Jawaban 2"}}]""",

        "summary": f"""Buatkan RINGKASAN EKSEKUTIF dari konteks berikut.
Bahasa: {language_name}.{sum_len_line}{sum_style_line}{extra}
Konteks:\n{context}\n\nTopik: {query or 'Ringkasan'}"""
    }

    prompt = prompts.get(studio_type, prompts["summary"])
    if studio_type == "audio_overview":
        system = (
            "You are a creative educational podcast producer. Produce only a natural "
            f"two-host dialogue in {language_name}, following the exact HOST_A| / HOST_B| format."
        )
    else:
        system = "Kamu adalah asisten belajar NotebookLM yang membantu membuat materi belajar dari sources. Jawab dalam bahasa Indonesia yang jelas, terstruktur, dan engaging. Selalu gunakan konteks yang diberikan."
    return call_gemini(prompt, api_key, system_instruction=system)

_CITE_RE = re.compile(r"\[S(\d{1,2})\]")


def _citation_snippet(answer: str, marker: str, source_text: str) -> str:
    """Pilih kalimat yang paling mewakili kutipan untuk chip sitasi.

    Algoritma: cari SEMUA kemunculan penanda, ambil kalimat yang memuatnya
    (berdasarkan posisi span, bukan potongan window), lalu pilih kalimat dengan
    kemiripan kata tertinggi terhadap isi sumber. Dengan begitu chip menampilkan
    kalimat yang benar-benar dikutip dari sumber itu.
    """
    text = str(answer or "").replace("\n", " ")
    spans = [(m.start(), m.end()) for m in re.finditer(r"[^.!?]+[.!?]?", text)]
    occurrences = [m.start() for m in re.finditer(re.escape(marker), text)]
    candidates = []
    for idx in occurrences:
        for s_start, s_end in spans:
            if s_start <= idx < s_end:
                sentence = text[s_start:s_end].strip()
                if sentence:
                    candidates.append(sentence)
                break

    def clean(value: str) -> str:
        value = re.sub(r"\[S\d+\]", "", value)
        value = re.sub(r"\*\*|__", "", value)
        # Buang judul/heading di depan bila kalimat dimulai dari satu baris daftar.
        parts = re.split(r"\s[-•]\s", value.strip())
        value = parts[-1] if parts else value
        value = re.sub(r"^[-•]\s*", "", value.strip())
        return re.sub(r"\s+", " ", value).strip()

    if not candidates:
        return clean(source_text)[:240]
    src_words = set(re.findall(r"\w+", str(source_text or "").lower()))
    best, best_score = candidates[0], -1
    for cand in candidates:
        words = set(re.findall(r"\w+", cand.lower()))
        score = len(words & src_words)
        if score > best_score:
            best, best_score = cand, score
    return clean(best)[:240] or clean(source_text)[:240]


def chat_with_citations(question: str, sources: list, chat_history: list, api_key: str,
                        language: str = "auto") -> dict:
    """Jawab pertanyaan HANYA dari `sources` terpilih, lengkap dengan sitasi terstruktur.

    A08: `sources` = [{"id": str, "title": str, "content": str}, ...] — daftar sumber
    yang DICENTANG pengguna di panel Sumber (grounding). Model diminta menulis penanda
    `[S1]`, `[S2]`, … yang lalu dipetakan balik ke `sourceId` asli.

    Return: `{"answer": str, "citations": [{"index","sourceId","title","marker","snippet"}]}`
    Bila model tidak memberi penanda apa pun → `citations: []` (jawaban tetap tampil,
    tidak pernah error — sesuai rencana A08).
    """
    src_list = []
    for i, src in enumerate(sources or [], start=1):
        content = str((src or {}).get("content") or "").strip()
        if not content:
            continue
        src_list.append({
            "index": i,
            "id": str((src or {}).get("id") or ""),
            "title": str((src or {}).get("title") or f"Sumber {i}"),
            "content": content[:6000],
        })
    if not src_list:
        return {"answer": "", "citations": []}

    lang = detect_content_language(question) if language in (None, "", "auto") else language
    lang_name = language_display_name(lang)
    blocks = "\n\n".join(
        f"[S{src['index']}] {src['title']}\n{src['content']}" for src in src_list
    )
    history_text = ""
    for msg in (chat_history or [])[-6:]:
        role = msg.get("role", "user")
        history_text += f"{role}: {msg.get('content', '')}\n"

    is_greeting = len(question.strip()) < 5 or question.strip().lower() in {
        "hai", "halo", "hello", "hi", "pagi", "siang", "sore", "malam",
        "selamat pagi", "selamat siang", "selamat sore", "selamat malam",
    }

    rules = f"""Aturan WAJIB:
- Jawab dalam {lang_name}, jelas, modern, dan rapi (bullet "-" untuk daftar, **bold** untuk judul).
- Setiap klaim yang berasal dari sumber HARUS diikuti penanda sitasi seperti [S1] atau [S2][S3].
- Hanya gunakan nomor sumber yang benar-benar ada di daftar SOURCES di atas — dilarang mengarang nomor.
- Jangan tulis daftar sumber di akhir jawaban; cukup penanda di dalam kalimat."""
    if is_greeting:
        rules += "\n- Ini sapaan: balas ramah tanpa penanda sitasi."

    prompt = f"""SOURCES (sumber terpilih untuk jawaban ini):
{blocks}

CHAT HISTORY:
{history_text}

PERTANYAAN: {question}

{rules}"""

    answer = call_gemini(
        prompt, api_key,
        system_instruction=(
            "Kamu tutor AI seperti NotebookLM: jawab hanya dari SOURCES yang diberikan "
            "dan sertakan penanda sitasi [S1], [S2], ... pada klaim yang memakai sumber."
        ),
        temperature=0.4,
    )

    citations = []
    if not answer.startswith("[MOCK") and not answer.startswith("[Quota") and not answer.startswith("[Error"):
        seen = set()
        for match in _CITE_RE.finditer(answer):
            num = int(match.group(1))
            src = next((x for x in src_list if x["index"] == num), None)
            if not src or num in seen:
                continue
            seen.add(num)
            marker = f"[S{num}]"
            citations.append({
                "index": num,
                "sourceId": src["id"],
                "title": src["title"],
                "marker": marker,
                "snippet": _citation_snippet(answer, marker, src["content"]),
            })
        citations.sort(key=lambda c: c["index"])
    return {"answer": answer, "citations": citations}


def chat_with_sources(question: str, context_chunks: list, chat_history: list, api_key: str) -> str:
    """Chat Q&A dengan citations."""
    context = "\n\n--- Source ---\n\n".join([f"[Source {i+1}]\n{c}" for i,c in enumerate(context_chunks[:4])])
    history_text = ""
    for msg in chat_history[-6:]:  # 3 turns terakhir
        role = msg.get('role','user')
        history_text += f"{role}: {msg.get('content','')}\n"
    
    # Deteksi sapaan sederhana - jangan pakai sources
    is_greeting = question.strip().lower() in ["hai", "halo", "hello", "hi", "selamat pagi", "selamat siang", "selamat sore", "selamat malam", "hai selamat pagi", "pagi", "siang", "sore", "malam"] or len(question.strip()) < 5
    if is_greeting:
        prompt = f"""Kamu adalah asisten AI yang ramah. User menyapa: "{question}"
Jawab dengan sapaan balik yang hangat, singkat, dan tawarkan bantuan untuk materi yang ada di sources.

JANGAN sebut "tidak ada di sources" atau "Pengetahuan Umum" untuk sapaan.
JANGAN pakai citations [Source X] untuk sapaan.
Cukup: "Hai! Selamat pagi juga! Ada yang bisa aku bantu tentang materi Matematika untuk Ilmu Komputer? Misalnya tanya Logika, Himpunan, Graf, dll."

CHAT HISTORY:
{history_text}"""
    else:
        prompt = f"""Jawab pertanyaan user berdasarkan SOURCES di bawah. Jika jawaban memang tidak ada di sources, jawab dengan pengetahuan umum TAPI JANGAN tulis "(tidak ada di sources)" atau "[Pengetahuan Umum]" — langsung jawab saja dengan alami.

SOURCES:
{context}

CHAT HISTORY:
{history_text}

PERTANYAAN: {question}

Aturan:
- Jawab dalam bahasa Indonesia yang jelas, modern, dan rapi
- Berikan citations seperti [Source 1] HANYA jika pakai info spesifik dari source (untuk sapaan/jawaban umum, tidak perlu citations)
- Format jawaban rapi: gunakan bullet list dengan "-" di awal baris untuk daftar, dan **bold** untuk judul
- Jangan pernah tulis "(Informasi tidak ada di sources)" atau kalimat serupa untuk sapaan
- Jika daftar topik, buat 1 baris per topik, jangan jadi 1 paragraf panjang"""
    
    system = "Kamu adalah tutor AI seperti NotebookLM. Jawab berdasarkan sources yang diberikan, berikan citations."
    return call_gemini(prompt, api_key, system_instruction=system)

# ── TTS untuk Audio Overview (pakai edge-tts jika ada, fallback ke gTTS) ─
# gTTS tidak menerima prefix locale panjang ("id-ID") — pakai kode bahasa pendek.
_GTTS_LANG = {
    "id": "id", "en": "en", "es": "es", "fr": "fr", "de": "de",
    "ja": "ja", "ko": "ko", "zh": "zh-CN", "pt": "pt", "ar": "ar", "ru": "ru",
}
# Perkiraan durasi dari ukuran berkas (bitrate default edge-tts ≈ 48 kbps mono).
_EDGE_BYTES_PER_SEC = 6000.0
_GTTS_BYTES_PER_SEC = 4000.0


def _edge_synth_sync(text: str, voice: str, rate: str, pitch: str) -> tuple:
    """Sintesis satu giliran via edge-tts → (bytes_mp3, durasi_detik)."""
    import asyncio
    import edge_tts  # type: ignore

    async def _run():
        comm = edge_tts.Communicate(text, voice, rate=rate, pitch=pitch, volume="+0%")
        chunks = []
        last_end = 0.0
        async for chunk in comm.stream():
            kind = chunk.get("type")
            if kind == "audio":
                chunks.append(chunk["data"])
            elif kind == "WordBoundary":
                # offset & duration dalam satuan 100 ns
                end = (chunk.get("offset", 0) + chunk.get("duration", 0)) / 10_000_000
                last_end = max(last_end, end)
        return b"".join(chunks), last_end

    return asyncio.run(_run())


def _gtts_synth_sync(text: str, language: str) -> tuple:
    """Fallback gTTS dengan bahasa yang BENAR (bukan suara Inggris membaca teks Indonesia)."""
    import io
    from gtts import gTTS  # type: ignore

    buf = io.BytesIO()
    gTTS(text=text, lang=_GTTS_LANG.get(language, "en")).write_to_fp(buf)
    data = buf.getvalue()
    return data, len(data) / _GTTS_BYTES_PER_SEC


def build_podcast_audio(script: str, output_path: str, language: str = "auto",
                        voice_a: str = None, voice_b: str = None,
                        api_key: str = "", progress_cb=None) -> dict:
    """Buat MP3 dua host yang benar-benar bergantian + metadata per giliran (A08).

    Perbedaan penting dari `podcast_to_speech` lama:
      • setiap giliran disintesis terpisah → durasi & offset tiap giliran diketahui,
        sehingga pemutar di UI bisa **klik giliran untuk lompat** dan menyorot
        giliran yang sedang berbunyi (interaktif, bukan sekadar daftar teks);
      • suara selalu mengikuti **bahasa transkrip** (`id` → id-ID-ArdiNeural /
        id-ID-GadisNeural), jadi tidak ada lagi suara Inggris membaca teks Indonesia;
      • fallback gTTS memakai kode bahasa yang benar (lang="id"), bukan default Inggris.

    Return: {path, voiceA, voiceB, language, languageLabel, engine, durationSec,
             sizeBytes, turns:[{index,speaker,text,startSec,endSec}]}
    """
    if not script or not script.strip():
        raise ValueError("Transkrip podcast kosong.")

    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    detected = detect_content_language(script) if language in (None, "", "auto") else language
    supplied_language = (voice_a or "").split("-", 1)[0].lower()
    if not voice_a or not voice_b or supplied_language != detected:
        voice_a, voice_b = podcast_voice_pair(detected, script)

    turns = parse_podcast_dialogue(script)
    speakers = {speaker for speaker, _ in turns}
    if len(speakers) < 2 or len(turns) < 4:
        if api_key and api_key.strip():
            rewritten = _rewrite_as_two_host_dialogue(script, api_key.strip(), detected)
            repaired = parse_podcast_dialogue(rewritten)
            if len({sp for sp, _ in repaired}) >= 2 and len(repaired) >= 4:
                turns = repaired
        if len({sp for sp, _ in turns}) < 2 or len(turns) < 4:
            raise ValueError(
                "Transkrip belum berbentuk dialog dua host. Generate ulang Podcast audio "
                "agar Host A dan Host B dapat berbicara bergantian."
            )

    engine = ""
    parts = []
    meta_turns = []
    cursor = 0.0
    total = len(turns)
    for index, (speaker, utterance) in enumerate(turns):
        voice = voice_a if speaker == "A" else voice_b
        variation = (-1, 1, 0)[index % 3]
        if speaker == "A":
            rate_value = variation
            pitch_value = -2 + variation
        else:
            rate_value = 4 + variation
            pitch_value = 3 + variation
        if utterance.rstrip().endswith("?"):
            rate_value += 1
            pitch_value += 2
        rate, pitch = f"{rate_value:+d}%", f"{pitch_value:+d}Hz"

        data = duration = None
        if not engine or engine == "edge-tts":
            try:
                data, duration = _edge_synth_sync(utterance, voice, rate, pitch)
                engine = "edge-tts"
            except ImportError:
                if not engine:
                    engine = ""
            except Exception as exc:  # jaringan/voice tidak tersedia → fallback
                print(f"[podcast] edge-tts gagal pada giliran {index + 1}: {exc}")
                if engine == "edge-tts":
                    engine = ""
        if not data:
            if engine == "edge-tts":
                raise RuntimeError("edge-tts gagal di tengah proses; audio dibatalkan agar tidak setengah jadi.")
            data, duration = _gtts_synth_sync(utterance, detected)
            if not engine:
                engine = "gTTS"
        if not data:
            raise RuntimeError("Tidak ada mesin TTS yang tersedia (edge-tts / gTTS).")
        if not duration or duration <= 0:
            duration = len(data) / (_EDGE_BYTES_PER_SEC if engine == "edge-tts" else _GTTS_BYTES_PER_SEC)
        parts.append(data)
        meta_turns.append({
            "index": index,
            "speaker": "A" if speaker == "A" else "B",
            "voice": voice,
            "text": utterance,
            "startSec": round(cursor, 2),
            "endSec": round(cursor + duration, 2),
        })
        cursor += duration
        if progress_cb:
            try:
                progress_cb(index + 1, total)
            except Exception:
                pass

    temp_path = output_path + ".part"
    with open(temp_path, "wb") as fh:
        for data in parts:
            fh.write(data)
    if os.path.getsize(temp_path) <= 0:
        try:
            os.remove(temp_path)
        except OSError:
            pass
        raise RuntimeError("Audio hasil sintesis kosong.")
    os.replace(temp_path, output_path)

    return {
        "path": output_path,
        "voiceA": voice_a,
        "voiceB": voice_b,
        "language": detected,
        "languageLabel": language_display_name(detected),
        "engine": engine or "gTTS",
        "durationSec": round(cursor, 2),
        "sizeBytes": os.path.getsize(output_path),
        "turns": meta_turns,
    }


def text_to_speech(text: str, output_path: str, voice: str = "id-ID-ArdiNeural"):
    """Generate audio dari text. Return path jika sukses."""
    try:
        # Coba edge-tts dulu (paling natural, gratis)
        import edge_tts  # type: ignore
        import asyncio
        async def _gen():
            comm = edge_tts.Communicate(text, voice)
            await comm.save(output_path)
        asyncio.run(_gen())
        return output_path
    except ImportError:
        pass
    except Exception as e:
        print(f"edge-tts gagal: {e}")
    try:
        from gtts import gTTS  # type: ignore
        tts = gTTS(text=text, lang='id' if 'id' in voice else 'en')
        tts.save(output_path)
        return output_path
    except Exception as e:
        print(f"gTTS gagal: {e}")
        return None


_PODCAST_STAGE_WORDS = {
    "narator", "narrator", "narasi", "narration", "intro", "outro",
    "judul", "title", "topik", "topic", "musik", "music", "sfx",
    "catatan", "note", "opening", "closing",
}


def _clean_podcast_utterance(text: str) -> str:
    """Remove labels/stage directions so they are never spoken by TTS."""
    clean = str(text or "").strip()
    clean = clean.replace("**", "").replace("__", "")
    clean = re.sub(r"^[-•]\s*", "", clean)
    clean = re.sub(r"^#{1,6}\s*", "", clean)
    clean = re.sub(r"\[(?:musik|music|sfx|intro|outro|jeda|pause)[^\]]*\]", "", clean, flags=re.I)
    clean = re.sub(r"\((?:musik|music|sfx|tertawa|laughs?|jeda|pause)[^)]*\)", "", clean, flags=re.I)
    clean = re.sub(r"\s+", " ", clean)
    return clean.strip(" \t\"'")


def parse_podcast_dialogue(script: str):
    """Return canonical [('A'|'B', utterance), ...] without spoken labels.

    Supports the strict HOST_A| format plus common Gemini variations such as
    **Host A (Raka):**, Host 1:, Speaker B:, or two named speakers.
    Narration before the first recognized turn and stage directions are dropped.
    """
    if not script:
        return []
    lines = [line.strip() for line in str(script).replace("```", "").splitlines()]

    known_pattern = re.compile(
        r"^\s*(?:[-•]\s*)?(?:\*\*)?"
        r"(?:(?:HOST[_\s-]*|Host\s+|Speaker\s+|Pembicara\s+|Pembawa\s+Acara\s+)([AB12]))"
        r"(?:\s*\([^)]*\))?\s*(?:\||:|—|-)\s*(?:\*\*)?\s*(.*)$",
        re.IGNORECASE,
    )

    def speaker_key(raw):
        return "A" if str(raw).upper() in ("A", "1") else "B"

    # First attempt: explicit Host/Speaker labels.
    turns = []
    current_speaker = None
    current_text = []
    for line in lines:
        if not line:
            continue
        match = known_pattern.match(line)
        if match:
            if current_speaker and current_text:
                utterance = _clean_podcast_utterance(" ".join(current_text))
                if utterance:
                    turns.append((current_speaker, utterance))
            current_speaker = speaker_key(match.group(1))
            current_text = [match.group(2)] if match.group(2) else []
            continue
        # Ignore headings/narration before the first actual speaker.
        if current_speaker is None:
            continue
        # A new narration/stage label must not leak into spoken dialogue.
        label_match = re.match(r"^(?:\*\*)?([^:|]{2,30}):(?:\*\*)?\s*(.*)$", line)
        if label_match and label_match.group(1).strip().lower() in _PODCAST_STAGE_WORDS:
            continue
        if re.fullmatch(r"\s*(?:\[[^]]+]|\([^)]*\))\s*", line):
            continue
        current_text.append(line)
    if current_speaker and current_text:
        utterance = _clean_podcast_utterance(" ".join(current_text))
        if utterance:
            turns.append((current_speaker, utterance))

    # Second attempt: two named speakers, e.g. **Raka:** and **Sinta:**.
    if len({speaker for speaker, _ in turns}) < 2:
        generic = re.compile(r"^\s*(?:\*\*)?([^:*|]{2,30})\s*:\s*(?:\*\*)?\s*(.+)$")
        candidates = []
        for line in lines:
            match = generic.match(line)
            if not match:
                continue
            label = match.group(1).strip()
            if label.lower() not in _PODCAST_STAGE_WORDS:
                candidates.append(label)
        unique_names = []
        for name in candidates:
            if name not in unique_names:
                unique_names.append(name)
        if len(unique_names) == 2:
            name_map = {unique_names[0]: "A", unique_names[1]: "B"}
            turns = []
            for line in lines:
                match = generic.match(line)
                if match and match.group(1).strip() in name_map:
                    utterance = _clean_podcast_utterance(match.group(2))
                    if utterance:
                        turns.append((name_map[match.group(1).strip()], utterance))

    # Merge accidental consecutive turns by the same speaker.
    merged = []
    for speaker, utterance in turns:
        if merged and merged[-1][0] == speaker:
            merged[-1] = (speaker, merged[-1][1] + " " + utterance)
        else:
            merged.append((speaker, utterance))
    return merged


def _rewrite_as_two_host_dialogue(script: str, api_key: str, language: str = "id") -> str:
    """Repair an old narrative transcript into strict conversational turns."""
    language_rule = "bahasa Indonesia" if language == "id" else "English"
    prompt = f"""Ubah teks berikut menjadi percakapan podcast dua host yang natural, kreatif, dan hidup dalam {language_rule}.
Host A hangat dan terstruktur; Host B penasaran, spontan, kritis, dan sesekali humoris.
Buat minimal 10 giliran yang bergantian dengan variasi reaksi singkat, pertanyaan, analogi, contoh konkret, mini-kuis, klarifikasi salah paham, dan rangkuman.
Jangan sekadar membagi narasi menjadi dua suara. Kedua host harus benar-benar saling menanggapi.
Hindari frasa berulang dan jangan tulis narator, judul, heading, petunjuk panggung, Markdown, atau teks di luar dialog.
Output HANYA dengan format:
HOST_A|dialog singkat
HOST_B|dialog singkat

TEKS SUMBER:
{script}"""
    return call_gemini(
        prompt, api_key,
        system_instruction="You convert educational narration into a natural two-person podcast conversation.",
        temperature=0.65,
    )


def podcast_to_speech(script: str, output_path: str,
                      voice_a: str = None, voice_b: str = None,
                      api_key: str = "", language: str = "auto"):
    """Kompatibilitas desktop (PyQt): hasilkan audio dua host, kembalikan path.

    A08: seluruh logika dipindah ke `build_podcast_audio` (satu sumber kebenaran untuk
    desktop **dan** web). Signature & nilai balik dipertahankan agar `MainPyQt6.py`
    tidak perlu diubah; metadata tambahan (offset per giliran) tersedia lewat
    `build_podcast_audio` untuk pemutar interaktif di web.
    """
    result = build_podcast_audio(
        script, output_path, language=language,
        voice_a=voice_a, voice_b=voice_b, api_key=api_key,
    )
    return result["path"]


