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

try:
    import google.generativeai as genai
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False
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
def _get_model(api_key: str, model_name: str = "gemini-2.0-flash"):
    # Coba SDK baru dulu (google.genai) untuk AQ Auth keys, fallback ke SDK lama (google.generativeai)
    # SDK baru handle AQ... lebih baik
    if not api_key or not api_key.strip():
        return None, "API Key Gemini belum diisi. Isi di Settings → Learning AI"
    if not (api_key.startswith("AIza") or api_key.startswith("AQ.")):
        return None, "API Key terlihat tidak valid (harus diawali AIza... atau AQ...)"
    
    # Coba SDK baru (google.genai) - untuk AQ keys
    try:
        from google import genai as new_genai
        from google.genai import types
        # Untuk SDK baru, model name tanpa models/ prefix
        clean_name = model_name.replace("models/", "")
        # Map nama lama ke nama baru jika perlu
        if clean_name == "gemini-pro":
            clean_name = "gemini-1.5-flash"
        try:
            client = new_genai.Client(api_key=api_key.strip())
            # Test dengan list models untuk validasi
            return ("new_sdk", client, clean_name), None
        except Exception as e:
            last_err_new = str(e)
            # Jika bukan 404, lanjut coba SDK lama
            if "404" not in last_err_new and "not found" not in last_err_new.lower():
                pass
    except ImportError:
        pass
    except Exception:
        pass
    
    # Fallback ke SDK lama (google.generativeai)
    if not GEMINI_AVAILABLE:
        return None, "google-generativeai belum terinstall. Jalankan: pip install google-generativeai\nAtau untuk AQ keys: pip install google-genai"
    candidates = [model_name]
    if not model_name.startswith("models/"):
        candidates.append(f"models/{model_name}")
    else:
        candidates.append(model_name.replace("models/", ""))
    # Hapus gemini-pro yang deprecated
    candidates = [c for c in candidates if "gemini-pro" not in c or "1.5-pro" in c]
    last_err = None
    for m in candidates:
        try:
            genai.configure(api_key=api_key.strip())
            model = genai.GenerativeModel(m)
            return model, None
        except Exception as e:
            last_err = str(e)
            if "404" in last_err or "not found" in last_err.lower():
                continue
            return None, f"Gagal init Gemini: {e}"
    return None, f"Gagal init Gemini (404): {last_err}"

def call_gemini(prompt: str, api_key: str, system_instruction: str = None, model_name: str = "gemini-2.5-flash", temperature: float = 0.7) -> str:
    # Auto-detect: jika model_name adalah 2.0/1.5 yang lama dan gagal, akan fallback ke 2.5

    """Panggil Gemini dengan fallback model jika 429 quota. Return text atau pesan user-friendly."""
    # Fallback models - update 2026-08: 2.5 series yang tersedia untuk AQ keys
    # Dari error Models tersedia: gemini-2.5-flash, 2.5-pro, dll. 404 untuk 2.0/1.5 lama
    models_to_try = [
        model_name,
        "gemini-2.5-flash",
        "models/gemini-2.5-flash",
        "gemini-2.5-pro",
        "models/gemini-2.5-pro",
        "gemini-2.5-flash-lite",
        "models/gemini-2.5-flash-lite",
        "gemini-2.0-flash",
        "models/gemini-2.0-flash",
        "gemini-1.5-flash",
        "models/gemini-1.5-flash",
        "gemma-4-26b-a4b-it",
        "models/gemma-4-26b-a4b-it",
    ]
    seen = set()
    unique_models = []
    for m in models_to_try:
        if m not in seen:
            seen.add(m)
            unique_models.append(m)
    
    last_error = None
    for m in unique_models:
        model_info, err = _get_model(api_key, m)
        if err:
            last_error = err
            if "quota" not in err.lower() and "429" not in err:
                return f"[MOCK - {err}]\n\nPrompt preview:\n{prompt[:600]}...\n\n[Isi API Key Gemini di Learning → 🔑 API Key untuk hasil real]"
            continue
        try:
            full_prompt = prompt
            if system_instruction:
                full_prompt = f"System: {system_instruction}\n\nUser: {prompt}"
            # Handle new SDK vs old SDK
            if isinstance(model_info, tuple) and model_info[0] == "new_sdk":
                _, client, clean_name = model_info
                from google.genai import types
                resp = client.models.generate_content(model=clean_name, contents=full_prompt, config=types.GenerateContentConfig(temperature=temperature))
                # New SDK response handling
                try:
                    return resp.text
                except:
                    return str(resp)
            else:
                model = model_info
                resp = model.generate_content(full_prompt, generation_config=genai.GenerationConfig(temperature=temperature))
            if not resp.candidates:
                return "[Gemini blocked response - coba sederhanakan prompt atau ganti topik]"
            try:
                return resp.text
            except:
                parts = resp.candidates[0].content.parts
                return "".join([p.text for p in parts if hasattr(p, 'text')])
        except Exception as e:
            err_str = str(e)
            last_error = err_str
            if "429" in err_str or "quota" in err_str.lower() or "exceeded" in err_str.lower() or "404" in err_str or "not found" in err_str.lower():
                print(f"[Gemini] {m} tidak tersedia/quota, coba model berikutnya...")
                continue
            traceback.print_exc()
            return f"[Error Gemini ({m}): {e}]"
    
    # Jika semua model 404, coba list models dan auto-pilih yang tersedia
    _hint = ""
    _auto_models = []
    try:
        from google import genai as _new_genai
        _client = _new_genai.Client(api_key=api_key.strip())
        _models = [m.name for m in _client.models.list()]
        if _models:
            _hint = f"\nModels tersedia: {', '.join(_models[:5])}"
            # Simpan untuk auto-try di iterasi berikutnya (jika ada)
            _auto_models = _models[:3]
            # Coba langsung satu model dari list jika fallback habis
            for _m in _auto_models:
                clean = _m.replace("models/", "")
                if clean not in [m.replace("models/", "") for m in models_to_try]:
                    try:
                        _c2 = _new_genai.Client(api_key=api_key.strip())
                        _resp = _c2.models.generate_content(model=clean, contents="hai")
                        return _resp.text
                    except:
                        continue
    except Exception as _e:
        _hint = f"\nListModels gagal: {_e}" if "_e" not in locals() else ""
        pass
    
    return (
        "[Quota/Model Error] Gemini menolak semua model.\n\n"
        "Penyebab paling sering untuk key baru `AQ...`:\n"
        "1. **Generative Language API belum di-Enable** (404) → Buka https://console.cloud.google.com/apis/library/generativelanguage.googleapis.com → Pilih project 'gen-lang-client-093...' → Klik **Enable** → Tunggu 1 menit\n"
        "2. Quota 0 → Tunggu 2 menit atau buat key baru di **New Project**\n"
        "3. Model gemini-pro & 1.5-pro sudah deprecated untuk v1beta → sudah di-handle\n\n"
        "Langkah cepat:\n"
        "1. Enable API di link atas\n"
        "2. pip install google-genai (sudah ada di requirements)\n"
        "3. Coba chat lagi dengan topik simpel `hai`\n"
        "4. Cek https://aistudio.google.com/app/apikey → Usage\n\n"
        f"Detail: {last_error[:600] if last_error else 'Unknown'}{_hint}"
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
                            language_hint: str = None) -> str:
    """Generate konten Studio berdasarkan type."""
    context = "\n\n---\n\n".join(context_chunks[:6])  # batasi 6 chunks biar tidak kepanjangan
    if not context.strip():
        context = "(Tidak ada source, jawab berdasarkan pengetahuan umum)"
    detected_language = language_hint or detect_content_language(
        f"{query}\n{' '.join(context_chunks[:3])}"
    )
    language_name = _LANGUAGE_NAMES.get(detected_language, "English")
    
    prompts = {
        "audio_overview": f"""Buat dialog podcast edukasi dengan DUA HOST yang benar-benar saling berbicara, bertanya, menanggapi, dan menyimpulkan materi.

BAHASA OUTPUT WAJIB: {language_name}. Gunakan bahasa ini untuk SETIAP giliran percakapan, terlepas dari bahasa antarmuka aplikasi.

KARAKTER HOST:
- Host A: pembawa acara utama yang hangat, percaya diri, terstruktur, dan pandai menjelaskan konsep rumit dengan analogi.
- Host B: co-host yang penasaran, spontan, kritis, kadang humoris, aktif bertanya, memberi contoh, menantang asumsi, dan merangkum dengan bahasanya sendiri.

ALUR KREATIF:
- Mulai dengan cold open atau pertanyaan pemancing yang langsung menarik perhatian.
- Buat 14-24 giliran bicara yang bergantian secara natural.
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
        
        "mind_map": f"""Buatkan struktur MIND MAP dalam format JSON untuk visualisasi.
Konteks:\n{context}\n\nTopik: {query or 'Topik utama'}

Format JSON WAJIB seperti ini (jangan tambah markdown):
{{"central": "Topik Utama", "branches": [{{"label": "Cabang 1", "children": ["sub 1", "sub 2"]}}, {{"label": "Cabang 2", "children": []}}]}}
Buat 3-6 cabang utama, tiap cabang 2-4 sub.""",
        
        "study_guide": f"""Buatkan STUDY GUIDE lengkap dari konteks berikut.
Konteks:\n{context}\n\nBuat dengan format:
# Study Guide: [Judul]
## 1. Ringkasan Utama
## 2. Konsep Kunci (dengan penjelasan)
## 3. Contoh Penting
## 4. Latihan Soal (3 soal + jawaban)
## 5. Kesimpulan
Topik: {query or 'Semua materi'}""",
        
        "briefing": f"""Buatkan BRIEFING DOC profesional (seperti di NotebookLM).
Konteks:\n{context}\n\nFormat:
# Briefing Doc
## Executive Summary (3 kalimat)
## Key Insights (5 poin)
## Important Quotes
## Action Items
Topik: {query or 'Ringkasan' }""",
        
        "faq": f"""Buatkan FAQ 8-10 pertanyaan dari konteks.
Konteks:\n{context}\n\nFormat:
Q1: ...
A1: ...
Q2: ...
A2: ...
Topik: {query or 'Umum'}""",
        
        "timeline": f"""Buatkan TIMELINE kronologis dari konteks.
Konteks:\n{context}\n\nFormat:
- **YYYY-MM-DD / Tahap 1:** Deskripsi
- **Tahap 2:** ...
Jika tidak ada tanggal, buat urutan logis Tahap 1,2,3...
Topik: {query or 'Urutan'}""",
        
        "flashcards": f"""Buatkan 10 FLASHCARDS interaktif untuk belajar dari konteks berikut.
Konteks:\n{context}\n\nTopik: {query or 'Materi'}

ATURAN OUTPUT WAJIB:
- Output HANYA JSON array valid. Jangan tulis pembuka, penutup, Markdown, atau code fence.
- Setiap item WAJIB memiliki key "front" dan "back".
- Variasikan kartu: konsep, contoh, perbandingan, benar/salah, penerapan, dan mini problem.
- Pertanyaan singkat dan jelas; jawaban padat tetapi cukup menjelaskan.
Format persis:
[{{"front":"Pertanyaan 1","back":"Jawaban 1"}},{{"front":"Pertanyaan 2","back":"Jawaban 2"}}]""",
        
        "summary": f"""Buatkan RINGKASAN EKSEKUTIF 200 kata dari konteks.
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
    """Create real alternating two-host audio; locale follows the transcript itself."""
    if not script or not script.strip():
        return None
    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)

    detected_language = detect_content_language(script) if language in (None, "", "auto") else language
    # Prevent an English voice from reading Indonesian (or the inverse), even if
    # a stale caller passes voices selected from the CraftLife settings language.
    supplied_language = (voice_a or "").split("-", 1)[0].lower()
    if not voice_a or not voice_b or supplied_language != detected_language:
        voice_a, voice_b = podcast_voice_pair(detected_language, script)
    language = detected_language

    turns = parse_podcast_dialogue(script)
    speakers = {speaker for speaker, _ in turns}
    if len(speakers) < 2 or len(turns) < 4:
        if api_key and api_key.strip():
            rewritten = _rewrite_as_two_host_dialogue(script, api_key.strip(), language)
            turns = parse_podcast_dialogue(rewritten)
            speakers = {speaker for speaker, _ in turns}
        if len(speakers) < 2 or len(turns) < 4:
            raise ValueError(
                "Transkrip belum berbentuk dialog dua host. Generate ulang Podcast audio "
                "agar Host A dan Host B dapat berbicara bergantian."
            )

    segments = [
        (speaker, voice_a if speaker == "A" else voice_b, utterance)
        for speaker, utterance in turns if utterance.strip()
    ]

    try:
        import edge_tts  # type: ignore
        import asyncio

        async def _generate():
            temp_path = output_path + ".part"
            try:
                with open(temp_path, "wb") as audio_file:
                    for index, (speaker, voice, utterance) in enumerate(segments):
                        # Separate synthesis calls preserve a distinct voice per host.
                        # Small deterministic prosody changes keep long podcasts lively
                        # without turning them into exaggerated character voices.
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
                        communication = edge_tts.Communicate(
                            utterance, voice,
                            rate=f"{rate_value:+d}%",
                            pitch=f"{pitch_value:+d}Hz",
                            volume="+0%",
                        )
                        async for chunk in communication.stream():
                            if chunk.get("type") == "audio":
                                audio_file.write(chunk["data"])
                if os.path.getsize(temp_path) <= 0:
                    raise RuntimeError("Audio stream kosong")
                os.replace(temp_path, output_path)
            finally:
                if os.path.exists(temp_path):
                    try:
                        os.remove(temp_path)
                    except OSError:
                        pass

        asyncio.run(_generate())
        return output_path
    except ImportError as error:
        raise RuntimeError("edge-tts belum terpasang; audio dua host tidak dapat dibuat") from error
    except Exception as error:
        # Do not fall back to one voice: that would turn the podcast back into narration.
        raise RuntimeError(f"Gagal membuat audio dua host: {error}") from error
