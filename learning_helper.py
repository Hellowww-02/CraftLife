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

# ── Studio Generators ────────────────────────────────────────────────────
def generate_studio_content(studio_type: str, query: str, context_chunks: list, api_key: str) -> str:
    """Generate konten Studio berdasarkan type."""
    context = "\n\n---\n\n".join(context_chunks[:6])  # batasi 6 chunks biar tidak kepanjangan
    if not context.strip():
        context = "(Tidak ada source, jawab berdasarkan pengetahuan umum)"
    
    prompts = {
        "audio_overview": f"""Buatkan NASKAH PODCAST 2 HOST (Host A & Host B) yang membahas materi berikut secara santai, engaging, seperti NotebookLM Audio Overview.
Durasi: 3-5 menit baca.
Format:
**Host A:** ...
**Host B:** ...
**Host A:** ...

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
        
        "flashcards": f"""Buatkan 10 FLASHCARDS untuk belajar.
Konteks:\n{context}\n\nFormat JSON array:
[{{"front": "Pertanyaan", "back": "Jawaban"}}, ...]
Topik: {query or 'Materi'}""",
        
        "summary": f"""Buatkan RINGKASAN EKSEKUTIF 200 kata dari konteks.
Konteks:\n{context}\n\nTopik: {query or 'Ringkasan'}"""
    }
    
    prompt = prompts.get(studio_type, prompts["summary"])
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
