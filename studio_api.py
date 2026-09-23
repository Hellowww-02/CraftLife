"""Studio & social API — learning, music, love, guild. Wraps database.py + learning_helper."""
from __future__ import annotations

import base64
import json
import os
import re

import database as db

# Konversi tipe generasi tersimpan (nama channel Gemini) ke gaya PyQt/web
# LearningPage._studio_generators: audio_overview→audio-overview, mind_map→mindmap, …
_LEGACY_STUDIO_TYPE = {
    "audio_overview": "audio-overview",
    "mind_map": "mindmap",
    "study_guide": "study-guide",
    # C05: 4 tipe baru (snake → kebab utk gtype kartu artefak).
    "briefing_doc": "briefing-doc",
    "data_table": "data-table",
    "infographic": "infographic",
    "slide_deck": "slide-deck",
}


# ── A06: metadata artefak Studio untuk daftar artefak (list ke bawah) ────────
_TEXT_STUDIO_TYPES = ("summary", "faq", "timeline", "study_guide", "briefing_doc")


def _artifact_meta(gen_type: str, content: str) -> dict:
    """Hitung jumlah item / jumlah kata / ukuran byte dari isi generasi.

    Dipakai kartu artefak di UI: quiz → "15 soal", flashcards → "20 kartu",
    audio-overview → "18 giliran", tipe teks → "340 kata". Semua defensif:
    isi yang rusak / bukan JSON tetap menghasilkan kartu yang tampil wajar.
    """
    raw = content or ""
    size = len(raw.encode("utf-8", "ignore"))
    gtype = (gen_type or "").lower()
    item_count = 0
    words = 0
    try:
        if gtype == "quiz":
            data = json.loads(_strip_json_fence(raw))
            qs = data.get("questions") if isinstance(data, dict) else data
            item_count = len(qs or []) if isinstance(qs, list) else 0
        elif gtype == "flashcards":
            data = json.loads(_strip_json_fence(raw))
            arr = data if isinstance(data, list) else (data.get("cards") or data.get("flashcards") or [])
            item_count = len(arr or [])
        elif gtype == "audio_overview":
            item_count = len([ln for ln in raw.splitlines() if ln.strip()])
        elif gtype == "data_table":
            data = json.loads(_strip_json_fence(raw))
            rows = data.get("rows") if isinstance(data, dict) else []
            item_count = len(rows or []) if isinstance(rows, list) else 0
        elif gtype == "slide_deck":
            data = json.loads(_strip_json_fence(raw))
            slides = data.get("slides") if isinstance(data, dict) else []
            item_count = len(slides or []) if isinstance(slides, list) else 0
        elif gtype == "infographic":
            data = json.loads(_strip_json_fence(raw))
            pts = data.get("points") if isinstance(data, dict) else []
            item_count = len(pts or []) if isinstance(pts, list) else 0
        else:
            words = len(raw.split())
    except Exception:
        # Bukan JSON yang valid → tetap laporkan ukuran teksnya.
        words = len(raw.split())
        item_count = 0
    if gtype in _TEXT_STUDIO_TYPES:
        item_count = 0
    return {"itemCount": item_count, "words": words, "sizeBytes": size}


def _map_sources(uid: int, sources: list) -> list:
    """C03: petakan baris sumber + ringkasan panduan (backfill malas ≤2/panggil)."""
    try:
        key = _gemini_key(uid)
    except Exception:
        key = ""
    budget = 2
    out = []
    for s in sources or []:
        content = s.get("content") or ""
        summary = s.get("summary") or ""
        snippet = ""
        if content.strip():
            try:
                import learning_helper as lh
                snippet = lh.source_snippet(content)
            except Exception:
                snippet = ""
        if not summary and snippet and key and budget > 0:
            # Backfill malas: hanya hasil AI yang disimpan (potongan dihitung ulang
            # tiap baca; gagal AI → "" → pakai potongan sementara, coba lagi nanti).
            try:
                import learning_helper as lh
                gen = lh.make_source_guide(content, key, s.get("title") or "") or ""
                if gen and gen != snippet:
                    try:
                        db.update_learning_source_summary(s.get("id"), uid, gen)
                    except Exception:
                        pass
                    summary = gen
                    budget -= 1
            except Exception:
                pass
        out.append({
            "id": str(s.get("id")),
            "title": s.get("title") or "",
            "type": s.get("type") or "text",
            "content": (s.get("content") or "")[:4000],
            "wordCount": len((s.get("content") or "").split()),
            "createdAt": s.get("created_at") or "",
            # C02: metadata berkas asli (kosong bila sumber teks/URL).
            "fileName": s.get("file_name") or "",
            "mimeType": s.get("mime_type") or "",
            "fileSize": s.get("file_size") or 0,
            "hasFile": bool(s.get("file_path")),
            "extractedAt": s.get("extracted_at") or s.get("created_at") or "",
            # C03: ringkasan panduan (AI tersimpan, else potongan).
            "summary": summary or snippet,
        })
    return out


def _nb_map(row: dict, uid: int) -> dict:
    nid = row.get("id")
    try:
        sources = db.get_learning_sources(nid, uid) or []
    except Exception:
        sources = []
    try:
        chats = db.get_learning_chats(nid) or []
    except Exception:
        chats = []
    try:
        _notes = db.get_learning_notes(nid, uid) or []
    except Exception:
        _notes = []
    out = {
        "id": str(nid),
        "title": row.get("title") or "",
        "description": row.get("description") or "",
        "icon": row.get("icon") or "📚",
        "sources": _map_sources(uid, sources),
        "chatHistory": [
            {
                "sender": "ai" if (c.get("role") == "assistant" or c.get("role") == "model") else "user",
                "text": c.get("content") or c.get("text") or "",
                "timestamp": c.get("created_at") or "",
                # A08: sitasi tersimpan ikut dikirim supaya chip sitasi tetap ada
                # setelah reload/restart (bukan hanya saat balasan baru datang).
                "citations": _parse_citations(c.get("citations")),
            }
            for c in chats
        ],
        "savedNotes": [
            {
                "id": str(n.get("id")),
                "title": n.get("title") or "",
                "content": n.get("content") or "",
                "createdAt": n.get("created_at") or "",
            }
            for n in _notes
        ],
        "flashcards": [],
        "quizzes": [],
        "podcast": [],
        # C05: slot 4 tipe baru (terbaru per tipe).
        "briefingDoc": "",
        "dataTable": None,
        "infographic": None,
        "slideDeck": None,
        "studyGuide": "",
        "mindMap": None,
        "faq": "",
        "timeline": "",
        "summary": "",
        "notes": row.get("notes") or "",
        "createdAt": row.get("created_at") or "",
    }
    try:
        gens = db.get_learning_generations(nid) or []
    except Exception:
        gens = []
    for g in gens:
        typ = (g.get("type") or "").lower()
        raw = g.get("content") or ""
        if typ == "flashcards" and not out["flashcards"]:
            try:
                arr = json.loads(raw) if isinstance(raw, str) else raw
                out["flashcards"] = [
                    {
                        "id": str(i),
                        "question": x.get("front") or x.get("question") or "",
                        "answer": x.get("back") or x.get("answer") or "",
                    }
                    for i, x in enumerate(arr or [])
                ]
            except Exception:
                pass
        elif typ == "quiz" and not out["quizzes"]:
            # A04: JANGAN buang `type`/`modelAnswer`. Dulu keduanya dibuang sehingga
            # soal esai — setelah refresh dari server — datang sebagai {options: [],
            # correctAnswerIndex: 0} tanpa penanda = tidak ada textarea untuk mengetik
            # (bug fatal "soal essay tidak bisa dijawab"). Kini lengkap + tahan banting:
            # bila field `type` tidak ada, soal dengan `model_answer`/tanpa opsi
            # tetap dikenali sebagai esai.
            try:
                data = json.loads(raw) if isinstance(raw, str) else raw
                qs = data.get("questions") if isinstance(data, dict) else data
                mapped = []
                for i, q in enumerate(qs or []):
                    if not isinstance(q, dict):
                        continue
                    options = q.get("options")
                    options = options if isinstance(options, list) else []
                    model_answer = q.get("model_answer") or q.get("modelAnswer") or ""
                    qtype = str(q.get("type") or "").strip().lower()
                    if qtype not in ("mc", "essay"):
                        qtype = "essay" if (model_answer and not options) else "mc"
                    try:
                        answer_idx = int(q.get("answer") if q.get("answer") is not None
                                         else (q.get("correctAnswerIndex") or 0))
                    except (TypeError, ValueError):
                        answer_idx = 0
                    mapped.append({
                        "id": f"g{g.get('id')}_{i}",
                        "type": qtype,
                        "question": q.get("q") or q.get("question") or "",
                        "options": options,
                        "correctAnswerIndex": answer_idx,
                        "explanation": q.get("explain") or q.get("explanation") or "",
                        "modelAnswer": model_answer,
                    })
                out["quizzes"] = mapped
            except Exception:
                pass
        elif typ in ("audio_overview", "podcast") and not out["podcast"]:
            lines = []
            for line in str(raw).splitlines():
                if "|" in line:
                    sp, txt = line.split("|", 1)
                    sp = sp.strip().replace("HOST_A", "Alex").replace("HOST_B", "Sam")
                    lines.append({"speaker": sp or "Alex", "line": txt.strip()})
            out["podcast"] = lines
        elif typ == "study_guide" and not out["studyGuide"]:
            out["studyGuide"] = raw
        elif typ == "mind_map" and not out["mindMap"]:
            try:
                out["mindMap"] = json.loads(raw)
            except Exception:
                out["mindMap"] = {"raw": raw}
        elif typ == "faq" and not out["faq"]:
            out["faq"] = raw
        elif typ == "timeline" and not out["timeline"]:
            out["timeline"] = raw
        elif typ == "summary" and not out["summary"]:
            out["summary"] = raw
        elif typ == "briefing_doc" and not out["briefingDoc"]:
            out["briefingDoc"] = raw
        elif typ == "data_table" and not out["dataTable"]:
            try:
                out["dataTable"] = _parse_data_table(raw)
            except Exception:
                out["dataTable"] = {"raw": raw}
        elif typ == "infographic" and not out["infographic"]:
            try:
                out["infographic"] = _parse_infographic(raw)
            except Exception:
                out["infographic"] = {"raw": raw}
        elif typ == "slide_deck" and not out["slideDeck"]:
            try:
                out["slideDeck"] = _parse_slide_deck(raw)
            except Exception:
                out["slideDeck"] = {"raw": raw}
    # Parity LearningPage: riwayat generasi Studio (tipe/topic/waktu) untuk combo
    # history + aksi hapus (_delete_generation). Slot tipe di atas = generasi terbaru.
    try:
        out["generations"] = [
            {
                "id": str(g.get("id") or ""),
                "gtype": _LEGACY_STUDIO_TYPE.get((g.get("type") or "").lower(), (g.get("type") or "").lower()),
                # A06: `title` & `topic` sama-sama dikirim — UI kartu artefak memakai
                # `title` (bisa diganti user), `topic` dipertahankan untuk kompatibilitas
                # riwayat lama (LearningView sebelumnya membaca `topic`).
                "title": g.get("title") or "",
                "topic": g.get("title") or "",
                "fileName": g.get("title") or "",
                "createdAt": g.get("created_at") or "",
                "updatedAt": g.get("updated_at") or g.get("created_at") or "",
                "content": g.get("content") or "",
                **_artifact_meta(g.get("type") or "", g.get("content") or ""),
                # A08: pemutar podcast tahu audio sudah siap (tanpa perlu POST ulang).
                "audio": podcast_audio_info(nid, g.get("id"))
                if (g.get("type") or "").lower() in ("audio_overview", "podcast") else None,
            }
            for g in gens
        ]
    except Exception:
        out["generations"] = []
    return out


def _love_days_to(iso):
    """Selisih hari `iso` − hari ini (negatif = sudah lewat); None bila tak lengkap."""
    try:
        from datetime import date as _d
        y, m, d = (int(x) for x in str(iso)[:10].split("-"))
        return (_d(y, m, d) - _d.today()).days
    except Exception:
        return None


def _love_memory_cloud_payload(row: dict) -> dict:
    """Field kenangan yang dikenal server cloud (dipakai add/update/favorit)."""
    return {
        "title": row.get("title") or "",
        "memory_date": row.get("memory_date") or "",
        "notes": row.get("notes") or "",
        "emoji": row.get("emoji") or "",
        "tags": row.get("tags") or "",
        "is_favorite": int(row.get("is_favorite") or 0),
    }


def _love_bucket_cloud_payload(row: dict) -> dict:
    """Field item bucket list yang dikenal server cloud."""
    return {
        "title": row.get("title") or "",
        "category": row.get("category") or "dream",
        "target_date": row.get("target_date") or "",
        "notes": row.get("notes") or "",
        "priority": int(row.get("priority") or 0),
        "is_done": 1 if row.get("is_done") else 0,
        "completed_at": row.get("completed_at") or "",
    }


def _love_map(uid: int) -> dict:
    prof = {}
    try:
        prof = db.get_relationship_profile(uid) or {}
    except Exception:
        prof = {}
    memories = []
    try:
        # A10: emoji, tag, favorit, tautan foto & jejak ubah ikut dikirim (dulu emoji
        # selalu "💖" dan sisa field tidak ada di payload sama sekali).
        memories = [
            {
                "id": str(m.get("id")),
                "title": m.get("title") or "",
                "date": m.get("memory_date") or m.get("date") or "",
                "description": m.get("notes") or "",
                "emoji": m.get("emoji") or "💖",
                "tags": db.love_memory_tags(m.get("tags")),
                "isFavorite": bool(m.get("is_favorite")),
                "photoId": str(m.get("photo_id")) if m.get("photo_id") else "",
                "updatedAt": m.get("updated_at") or "",
            }
            for m in (db.get_relationship_memories(uid) or [])
        ]
    except Exception:
        pass
    bucket = []
    try:
        # A10: kategori, target tanggal (dengan hitung mundur & penanda terlewat),
        # catatan, prioritas, dan penanda "sudah jadi kenangan".
        for _b in (db.get_relationship_bucket_items(uid) or []):
            _done = bool(_b.get("done") or _b.get("is_done"))
            _days = _love_days_to(_b.get("target_date"))
            bucket.append({
                "id": str(_b.get("id")),
                "title": _b.get("title") or "",
                "isCompleted": _done,
                "completedDate": _b.get("completed_at"),
                "category": _b.get("category") or "dream",
                "targetDate": _b.get("target_date") or "",
                "daysToTarget": _days,
                "isOverdue": bool(_days is not None and _days < 0 and not _done),
                "notes": _b.get("notes") or "",
                "priority": int(_b.get("priority") or 0),
                "promotedMemoryId": str(_b.get("promoted_memory_id")) if _b.get("promoted_memory_id") else "",
                "updatedAt": _b.get("updated_at") or "",
            })
    except Exception:
        pass
    data = {
        "partnerName": prof.get("partner_name") or "",
        "myName": prof.get("my_name") or "",
        "startDate": prof.get("start_date") or "",
        "relationshipType": prof.get("relationship_type") or "",
        "myGender": prof.get("my_gender") or "male",
        "myAge": int(prof.get("my_age") or 25),
        "myBirthdate": prof.get("my_birthdate") or "",
        "partnerGender": prof.get("partner_gender") or "female",
        "partnerAge": int(prof.get("partner_age") or 25),
        "partnerBirthdate": prof.get("partner_birthdate") or "",
        "memories": memories,
        "bucketList": bucket,
        "connectionScore": int(prof.get("connection_score") or 0),
        "prompts": [],
        "events": [],
        "weeklyReviews": [],
        "cycles": [],
        "photos": [
            {
                "id": str(ph.get("id")),
                "caption": ph.get("caption") or "",
                "photoDate": ph.get("photo_date") or "",
                "visibility": ph.get("visibility") or "private",
                "ownerUserId": str(ph.get("owner_user_id") or ""),
                "uploaderName": ph.get("uploader_name") or "",
                "createdAt": ph.get("created_at") or "",
            }
            for ph in (db.get_love_space_photo_meta(uid) or [])
        ],
    }
    # A10: faset untuk toolbar tab memories (filter tahun & tag) + statistik bucket.
    try:
        _years = sorted({str(m.get("date") or "")[:4] for m in memories if str(m.get("date") or "")[:4].isdigit()},
                        reverse=True)
        _tag_counts = {}
        for _m in memories:
            for _tag in (_m.get("tags") or []):
                _tag_counts[_tag] = _tag_counts.get(_tag, 0) + 1
        data["memoryYears"] = _years
        data["memoryTags"] = [{"tag": k, "count": v}
                              for k, v in sorted(_tag_counts.items(), key=lambda kv: (-kv[1], kv[0]))]
        data["memoryStats"] = {
            "total": len(memories),
            "favorites": sum(1 for _m in memories if _m.get("isFavorite")),
            "tagged": sum(1 for _m in memories if _m.get("tags")),
            "withPhoto": sum(1 for _m in memories if _m.get("photoId")),
        }
    except Exception:
        data["memoryYears"] = []
        data["memoryTags"] = []
        data["memoryStats"] = {"total": len(memories), "favorites": 0, "tagged": 0, "withPhoto": 0}
    try:
        data["bucketStats"] = db.get_relationship_bucket_stats(uid)
    except Exception:
        data["bucketStats"] = {"total": len(bucket), "done": 0, "open": len(bucket),
                               "overdue": 0, "dueSoon": 0, "percent": 0, "targeted": 0}
    try:
        data["events"] = [
            {
                "id": str(ev.get("id")),
                "title": ev.get("title") or "",
                "date": ev.get("event_date") or "",
                "category": ev.get("category") or "date",
                "notes": ev.get("notes") or "",
                # A09: ikon, lokasi, Special Day, pengulangan tahunan & pengingat.
                "icon": ev.get("icon") or "",
                "location": ev.get("location") or "",
                "isSpecial": bool(ev.get("is_special")),
                "recurring": ev.get("recurring") or "none",
                "remindDaysBefore": int(ev.get("remind_days_before") or 0),
                "updatedAt": ev.get("updated_at") or "",
            }
            for ev in (db.get_relationship_events(uid) or [])
        ]
        # A09: hitung mundur + hari istimewa dari profil (ulang tahun/anniversary)
        # dihitung di server supaya klien tidak perlu tahu soal tanggal 29 Feb dll.
        data["upcomingEvents"] = db.upcoming_relationship_events(uid, 90) or []
        data["specialDays"] = [it for it in data["upcomingEvents"] if it.get("isSpecial")]
        data["weeklyReviews"] = [
            {
                "id": str(w.get("id")),
                "weekStart": w.get("week_start") or "",
                "appreciation": w.get("appreciation") or "",
                "wins": w.get("wins") or "",
                "support": w.get("support_needed") or "",
                "intention": w.get("shared_intention") or "",
            }
            for w in (db.get_relationship_weekly_reviews(uid) or [])
        ]
        # A11: panjang hari tiap siklus (dihitung server supaya UI bisa
        # menampilkan tabel riwayat + rata-rata tanpa logika tanggal di klien).
        data["cycles"] = [
            {
                "id": str(c.get("id")),
                "startDate": c.get("start_date") or "",
                "endDate": c.get("end_date") or "",
                "notes": c.get("notes") or "",
                "lengthDays": c.get("length_days"),
                "updatedAt": c.get("updated_at") or "",
            }
            for c in (db.get_menstrual_cycles(uid) or [])
        ]
    except Exception:
        pass
    # Parity LovePage: riwayat check-in, respons prompt + favorit, album galeri,
    # dan status couple aktif (mengendalikan visibilitas shared & tombol end-couple).
    try:
        data["checkins"] = [
            {
                "id": str(c.get("id")),
                "date": c.get("checkin_date") or "",
                "myMood": int(c.get("my_mood") or 3),
                "partnerMood": int(c.get("partner_mood") or 3),
                "connectionScore": int(c.get("connection_score") or 3),
                "note": c.get("note") or "",
            }
            for c in (db.get_relationship_checkins(uid) or [])
        ]
    except Exception:
        data["checkins"] = []
    try:
        data["promptResponses"] = [
            {
                "id": str(p.get("id")),
                "promptKey": p.get("prompt_key") or "",
                "category": p.get("category") or "daily",
                "prompt": p.get("prompt_text") or p.get("prompt") or "",
                "answer": p.get("my_answer") or p.get("answer") or "",
                "partnerAnswer": p.get("partner_answer") or "",
                "createdAt": p.get("created_at") or p.get("response_date") or "",
            }
            for p in (db.get_relationship_prompt_responses(uid) or [])
        ]
    except Exception:
        data["promptResponses"] = []
    try:
        data["promptFavorites"] = sorted(db.get_relationship_prompt_favorites(uid) or set())
    except Exception:
        data["promptFavorites"] = []
    try:
        # A11: album membawa sampul (cover_photo_id), jumlah foto & tanggal buat
        # supaya toolbar galeri bisa menampilkan chip album yang benar-benar
        # informatif (dulu hanya nama + scope).
        _albums = []
        for a in (db.get_love_albums(uid) or []):
            _ids = [str(x) for x in (db.get_love_album_photo_ids(uid, a.get("id")) or [])]
            _cover = str(a.get("cover_photo_id") or "")
            if _cover and _cover not in _ids:
                # Sampul menunjuk foto yang sudah dihapus → jangan tampilkan hantu.
                _cover = ""
            _albums.append({
                "id": str(a.get("id")),
                "name": a.get("name") or "",
                "scope": a.get("scope") or "personal",
                "photoIds": _ids,
                "photoCount": len(_ids),
                "coverPhotoId": _cover or (_ids[0] if _ids else ""),
                "hasCover": bool(a.get("cover_photo_id")),
                "createdAt": a.get("created_at") or "",
            })
        data["albums"] = _albums
    except Exception:
        data["albums"] = []
    try:
        data["coupleActive"] = bool((db.get_couple_context(uid) or {}).get("active"))
    except Exception:
        data["coupleActive"] = False
    # P61: akun pasangan couple (untuk kartu partner Love Space) + jumlah
    # permintaan couple pending (badge "menunggu konfirmasi").
    try:
        cc = db.get_couple_context(uid) or {}
        partner_u = cc.get("partner") or {}
        data["couplePartner"] = {
            "displayName": partner_u.get("display_name") or partner_u.get("username") or "",
            "username": partner_u.get("username") or "",
            "avatarEmoji": partner_u.get("avatar_emoji") or "",
            "avatarColor": partner_u.get("avatar_color") or "",
            "level": int(partner_u.get("level") or 0),
        } if cc.get("active") else None
    except Exception:
        data["couplePartner"] = None
    try:
        data["couplePending"] = len(db.get_pending_couple_requests(uid) or [])
    except Exception:
        data["couplePending"] = 0
    # Parity LovePage.load(): status shared (linked username) + realtime cloud
    # + profil kesehatan tersinkron (gender/usia dari BMI settings).
    try:
        cc = db.get_couple_context(uid) or {}
        partner_u = cc.get("partner")
        data["linkedPartnerUsername"] = (partner_u or {}).get("username") or ""
        try:
            data["cloudLoveActive"] = bool(db.get_cloud_love_space_id(uid))
        except Exception:
            data["cloudLoveActive"] = False
    except Exception:
        data["linkedPartnerUsername"] = ""
        data["cloudLoveActive"] = False
    try:
        hp = db.get_user_bmi_settings(uid) or {}
        data["healthProfile"] = {
            "gender": str(hp.get("gender") or "male").lower(),
            "age": int(hp.get("age") or 25),
        }
    except Exception:
        data["healthProfile"] = {"gender": "male", "age": 25}
    # Parity tab Cycle: settings + prediksi periode (db.get_menstrual_prediction).
    try:
        s = db.get_menstrual_settings(uid) or {}
        data["cycleSettings"] = {
            "trackedPerson": s.get("tracked_person") or "partner",
            "lastPeriodStart": s.get("last_period_start") or "",
            "cycleLength": int(s.get("cycle_length") or 28),
            "periodLength": int(s.get("period_length") or 5),
        }
    except Exception:
        data["cycleSettings"] = {"trackedPerson": "partner", "lastPeriodStart": "", "cycleLength": 28, "periodLength": 5}
    try:
        p = db.get_menstrual_prediction(uid)
        data["cyclePrediction"] = {
            "predictedStart": p.get("predicted_start") or "",
            "predictedEnd": p.get("predicted_end") or "",
            "daysUntil": int(p.get("days_until") or 0),
        } if p else None
    except Exception:
        data["cyclePrediction"] = None
    return data


def _refresh_couple_mirror(uid: int) -> None:
    """P61: best-effort mirror couple cloud → lokal sebelum membaca Love Space.
    Aman offline / tanpa cloud (diam)."""
    try:
        if db.get_cloud_user_link(uid):
            from sync_service import get_sync_service
            get_sync_service().pull_social_now(uid)
    except Exception:
        pass


def _couple_cloud_push(uid: int, action: str, friend_id=None, rel_id=None, accept=None):
    """P61: best-effort naikkan aksi couple web → cloud RPC (bila session cloud
    aktif & pasangan cloud-linked). Gagal = diam — relasi lokal tetap sah;
    desktop dapat menyusul via sync queue couple_end."""
    try:
        if not db.get_cloud_user_link(uid):
            return None
        from sync_service import get_sync_service
        svc = get_sync_service()
        if not svc.ensure_session(uid):
            return None
        cloud = svc.cloud
        if action == "request" and friend_id:
            target = (db.get_user(friend_id) or {}).get("cloud_user_id")
            if not target:
                return None
            rel = cloud.rpc("send_couple_request", {"target_user_id": target})
            if isinstance(rel, list):
                rel = rel[0] if rel else None
            if isinstance(rel, dict) and rel.get("id"):
                db.attach_cloud_id_to_couple(uid, friend_id, str(rel["id"]))
                return str(rel["id"])
        elif action == "respond" and rel_id:
            rel = db.get_couple_relationship_record(rel_id, uid) or {}
            if not rel.get("cloud_id"):
                return None
            cloud.rpc("respond_couple_request", {"relationship_id": rel["cloud_id"], "accept_request": bool(accept)})
            return rel["cloud_id"]
        elif action == "cancel" and rel_id:
            rel = db.get_couple_relationship_record(rel_id, uid) or {}
            if not rel.get("cloud_id"):
                return None
            cloud.rpc("cancel_couple_request", {"relationship_id": rel["cloud_id"]})
            return rel["cloud_id"]
        elif action == "end" and rel_id:
            rel = db.get_couple_relationship_record(rel_id, uid) or {}
            if not rel.get("cloud_id"):
                return None
            try:
                cloud.rpc("end_couple_relationship", {"relationship_id": rel["cloud_id"]})
            except Exception as exc:
                low = str(exc).lower()
                if not any(c in low for c in ("invalid_relationship", "p0001", "not found", "does not exist")):
                    try:
                        db.enqueue_sync(uid, "couple_end", rel.get("id") or 0, "end", {"cloud_id": rel["cloud_id"]})
                    except Exception:
                        pass
            return rel["cloud_id"]
    except Exception:
        return None
    return None


def _couple_tracking_map(uid: int) -> dict:
    """Ringkasan tracking couple 1:1 `CoupleTrackingDialog` PyQt: 11 sub-tab
    data per orang (saya + pasangan). Line di-render server-side via tr_db()
    supaya frontend tidak perlu menduplikasi game rule / string."""
    rel = db.get_active_couple_relationship(uid)
    if not rel:
        return {"ok": False, "code": "no_couple"}
    try:
        lang = (db.get_user(uid) or {}).get("language") or "id"
    except Exception:
        lang = "id"
    partner_id = rel["user_b_id"] if rel["user_a_id"] == uid else rel["user_a_id"]
    me = db.get_user(uid) or {}
    pn = db.get_user(partner_id) or {}
    pair = [(uid, (me.get("display_name") or me.get("username") or "A")),
            (partner_id, (pn.get("display_name") or pn.get("username") or "B"))]

    def _lines(uid2: int, key: str) -> list:
        try:
            if key == "ct_tab_tasks":
                hs = db.get_habits(uid2) or []
                ds = db.get_dailies(uid2) or []
                ts = db.get_todos(uid2) or []
                up = sum(int(h.get("counter_up") or 0) for h in hs)
                stk = max([int(h.get("streak") or 0) for h in hs] or [0])
                dd = sum(1 for d in ds if d.get("done_today"))
                td = sum(1 for t in ts if t.get("done"))
                return [db.tr_db(lang=lang, key="ct_habits_line", n=len(hs), up=up, s=stk),
                        db.tr_db(lang=lang, key="ct_dailies_line", n=len(ds), d=dd),
                        db.tr_db(lang=lang, key="ct_todos_line", n=len(ts), d=td)]
            if key == "ct_tab_sport":
                st = db.get_sport_stats(uid2) or {}
                return [db.tr_db(lang=lang, key="ct_sport_line",
                                 act=st.get("total_sport", st.get("total_activities", 0)),
                                 done=st.get("done_today", st.get("done_sport_today", 0)),
                                 s=st.get("s", st.get("max_sport_streak", 0)),
                                 lv=st.get("sport_level", 1))]
            if key == "ct_tab_economy":
                es = db.get_economy_summary(uid2) or {}
                return [db.tr_db(lang=lang, key="ct_economy_line",
                                 inc=es.get("total_income", 0),
                                 exp=es.get("total_expense", 0),
                                 bal=es.get("balance", 0))]
            if key == "ct_tab_supplies":
                sp = db.supplies_stats(uid2) or {}
                return [db.tr_db(lang=lang, key="ct_supplies_line", n=sp.get("items", 0),
                                 low=sp.get("low", 0), val=sp.get("value", 0))]
            if key == "ct_tab_health":
                h = db.get_health_summary(uid2) or {}
                return [db.tr_db(lang=lang, key="ct_health_line",
                                 steps=h.get("avg_steps") or "—",
                                 logs=h.get("log_count", h.get("days_recorded") or "—"))]
            if key == "ct_tab_love":
                ck = db.get_relationship_checkins(uid2, 100) or []
                avg = sum(int(x["connection_score"] or 0) for x in ck) / len(ck) if ck else 0
                ev = db.get_relationship_events(uid2, False, 100) or []
                try:
                    ph = db.get_love_space_photo_meta(uid2, 100) or []
                except Exception:
                    ph = []
                mem = db.get_relationship_memories(uid2, 100) or []
                return [db.tr_db(lang=lang, key="ct_love_line", ck=len(ck), avg=f"{avg:.1f}",
                                 ev=len(ev), ph=len(ph), mem=len(mem))]
            if key == "ct_tab_learning":
                nbs = db.get_learning_notebooks(uid2) or []
                lines = []
                for nb in nbs[:5]:
                    src = len(db.get_learning_sources(nb["id"], uid2) or [])
                    cht = len(db.get_learning_chats(nb["id"]) or [])
                    lines.append(db.tr_db(lang=lang, key="ct_learning_line",
                                          name=(nb.get("title") or nb.get("name") or "?"),
                                          s=src, c=cht))
                return lines or [db.tr_db(lang=lang, key="ct_none")]
            if key == "ct_tab_pomodoro":
                rows = db.get_recent_pomodoros(uid2, 5) or []
                out = []
                for r in rows:
                    out.append(db.tr_db(lang=lang, key="ct_pomodoro_line",
                                        m=r.get("minutes") or r.get("duration_minutes") or 0,
                                        d=str(r.get("created_at") or "")[:16]))
                return out or [db.tr_db(lang=lang, key="ct_none")]
            if key == "ct_tab_music":
                hist = db.get_music_play_history(uid2, 5) or []
                pls = db.get_all_playlists(uid2) or []
                blend = db.get_blend_playlist_for_user(uid2)
                if blend and not any(p["id"] == blend["id"] for p in pls):
                    pls.append(blend)
                lines = [db.tr_db(lang=lang, key="ct_music_recent")]
                lines += [f"🎵 {h.get('title') or (h.get('path') or '').split('/')[-1]} — {h.get('artist') or ''}" for h in hist] or [db.tr_db(lang=lang, key="ct_none")]
                lines.append(db.tr_db(lang=lang, key="ct_music_playlists"))
                import json as _json
                lines += [f"🎧 {p.get('name') or '?'} ({len(_json.loads(p.get('tracks') or '[]'))})" for p in pls] or [db.tr_db(lang=lang, key="ct_none")]
                return lines
            if key == "ct_tab_reminders":
                rs = [r for r in (db.get_reminders(uid2) or []) if r.get("is_active")]
                return [f"⏰ {r.get('title')} · {str(r.get('reminder_datetime') or '')[:16]}" for r in rs[:8]] or [db.tr_db(lang=lang, key="ct_none")]
            if key == "ct_tab_achievements":
                # P61 fix: JANGAN re-assign `lang` di dalam closure — itu membuat
                # `lang` lokal di seluruh _lines sehingga cabang lain crash
                # UnboundLocalError (akar couple tracking 500 / item #9).
                ua = db.get_user_achievements(uid2) or []
                unlocked = [a for a in ua if a.get("unlocked_at")]
                out = []
                for a in unlocked[:8]:
                    name_text, _ = db.tr_achievement(a, lang)
                    out.append(f"🏆 {name_text} · {str(a.get('unlocked_at') or '')[:10]}")
                return out or [db.tr_db(lang=lang, key="ct_none")]
        except Exception:
            pass
        return [db.tr_db(lang=lang, key="ct_none")]

    tab_keys = ["ct_tab_tasks", "ct_tab_sport", "ct_tab_economy", "ct_tab_supplies",
                "ct_tab_health", "ct_tab_love", "ct_tab_learning", "ct_tab_pomodoro",
                "ct_tab_music", "ct_tab_reminders", "ct_tab_achievements"]
    out_pair = []
    for uid2, name in pair:
        sections = [{"key": k, "label": db.tr_db(lang=lang, key=k), "lines": _lines(uid2, k)} for k in tab_keys]
        out_pair.append({"id": str(uid2), "name": name, "sections": sections})
    return {"ok": True, "pair": out_pair}


def _guild_map(uid: int) -> dict:
    u = db.get_user(uid) or {}
    gid = u.get("guild_id")
    empty = {
        "id": "",
        "name": "",
        "level": 1,
        "exp": 0,
        "maxExp": 100,
        "bossHp": 0,
        "bossMaxHp": 0,
        "members": [],
        "messages": [],
    }
    if not gid:
        return empty
    try:
        raw = db.get_guild(gid) or {}
    except Exception:
        return empty
    g = raw.get("guild") or raw
    members = raw.get("members") or []
    boss = raw.get("boss") or {}
    msgs = []
    try:
        msgs = [
            {
                "id": str(m.get("id")),
                "senderId": str(m.get("sender_id")),
                "senderName": m.get("display_name") or m.get("username") or "",
                "senderAvatar": m.get("avatar_emoji") or "⚔️",
                "text": m.get("message") or m.get("content") or "",
                "timestamp": m.get("created_at") or "",
                "isSelf": str(m.get("sender_id")) == str(uid),
            }
            for m in (db.get_guild_messages(gid) or [])
        ]
    except Exception:
        pass
    transfers = []
    try:
        conn = db.get_conn()
        rows = conn.execute(
            "SELECT * FROM guild_leader_transfers WHERE guild_id=? AND status='pending'",
            (gid,),
        ).fetchall()
        conn.close()
        transfers = [{"id": str(r["id"]), "oldLeaderId": str(r["old_leader_id"])} for r in rows]
    except Exception:
        transfers = []
    return {
        "id": str(g.get("id") or gid),
        "name": g.get("name") or "",
        "level": int(g.get("level") or 1),
        "exp": int(g.get("exp") or g.get("xp") or 0),
        "maxExp": int(g.get("max_exp") or 100),
        "bossHp": int((boss or {}).get("boss_hp") or g.get("boss_hp") or 0),
        "bossMaxHp": int((boss or {}).get("boss_max_hp") or g.get("boss_max_hp") or 0),
        "bossName": (boss or {}).get("boss_name") or g.get("boss_name") or "",
        "bossIcon": (boss or {}).get("boss_icon") or "🐉",
        "bossTier": (boss or {}).get("boss_tier") or "normal",
        "bossAttack": int((boss or {}).get("boss_attack") or 0),
        "bossParticipants": (boss or {}).get("participants") or "[]",
        "leaderId": str(g.get("leader_id") or ""),
        # Parity GuildPage._make_stats.
        "buffXp": int(g.get("buff_xp") or 0),
        "buffGold": int(g.get("buff_gold") or 0),
        "buffDamage": int(g.get("buff_damage") or 0),
        "critChance": float(g.get("crit_chance") or 0),
        "members": [
            {
                "id": str(m.get("id")),
                "displayName": m.get("display_name") or "",
                "name": m.get("display_name") or "",
                "level": int(m.get("level") or 1),
                "role": "leader" if str(m.get("id")) == str(g.get("leader_id")) else "member",
                "avatarEmoji": m.get("avatar_emoji") or "⚔️",
                "avatarColor": m.get("avatar_color") or "",
                "hp": int(m.get("hp") or 0),
                "maxHp": int(m.get("max_hp") or 1),
            }
            for m in members
        ],
        "messages": msgs,
        "requests": [
            {
                "id": str(r.get("id")),
                "userId": str(r.get("user_id")),
                "name": r.get("display_name") or r.get("username") or "",
                "username": r.get("username") or "",
            }
            for r in (db.get_guild_requests(gid) or [])
        ],
        "description": g.get("description") or "",
        "leaderTransfers": transfers,
    }


def _friends_map(uid: int) -> list:
    # Parity FriendsPage.load: tiap baris teman membawa status couple, presence
    # (online/offline dari cache) & unread count untuk label tombol chat.
    out = []
    try:
        linked = bool(db.get_cloud_user_link(uid))
    except Exception:
        linked = False
    try:
        for f in db.get_friends(uid) or []:
            fid = f.get("id")
            try:
                status = (db.get_couple_status_between(uid, fid) or {}).get("status", "friend")
            except Exception:
                status = "friend"
            presence = ""
            try:
                if f.get("cloud_user_id"):
                    presence = (db.get_cached_presence(f.get("cloud_user_id")) or {}).get("status", "")
            except Exception:
                presence = ""
            try:
                if linked and f.get("cloud_user_id"):
                    unread = db.get_cloud_unread_count(uid, fid)
                else:
                    unread = db.get_unread_count_between(uid, fid)
            except Exception:
                unread = 0
            out.append({
                "id": str(fid),
                "displayName": f.get("display_name") or f.get("username") or "",
                "username": f.get("username") or "",
                "avatarEmoji": f.get("avatar_emoji") or "⚔️",
                "avatarColor": f.get("avatar_color") or "",
                "level": int(f.get("level") or 1),
                "coupleStatus": status if status in ("accepted", "pending") else "friend",
                "presence": presence or "offline",
                "unreadCount": int(unread or 0),
            })
    except Exception:
        pass
    return out


def _pvp_map(uid: int) -> list:
    out = []
    try:
        for c in db.get_pvp_challenges(uid) or []:
            raw = (c.get("status") or "pending").lower()
            if raw in ("finished", "completed", "declined"):
                st = "completed"
            elif raw == "active":
                st = "active"
            else:
                st = "pending"
            out.append({
                "id": str(c.get("id")),
                "opponentName": c.get("opponent_name") or "",
                "opponentId": str(c.get("opponent_id") or ""),
                "opponentAvatar": "⚔️",
                "opponentLevel": 1,
                "status": st,
                "rawStatus": raw,
                "isChallenger": bool(c.get("is_challenger")),
                "playerScore": int(c.get("my_score") or 0),
                "opponentScore": int(c.get("opponent_score") or 0),
                "daysLeft": int(c.get("days_left") or 0),
                "winnerId": (str(c.get("winner_id")) if c.get("winner_id") is not None else None),
                "rewardXp": int(c.get("xp_reward") or 100),
                "rewardGold": int(c.get("gold_reward") or 50),
            })
    except Exception:
        pass
    return out


def _couple_requests_map(uid: int) -> list:
    out = []
    try:
        for r in db.get_pending_couple_requests(uid) or []:
            out.append({
                "id": str(r.get("id")),
                "name": r.get("other_display_name") or r.get("other_username") or "",
                "username": r.get("other_username") or "",
                "otherUserId": str(r.get("other_user_id") or ""),
                "direction": r.get("direction") or "incoming",
            })
    except Exception:
        pass
    return out


def _friend_requests_map(uid: int) -> list:
    out = []
    try:
        for r in db.get_pending_friend_requests(uid) or []:
            out.append({
                "id": str(r.get("id")),
                "senderId": str(r.get("sender_id")),
                "name": r.get("display_name") or r.get("username") or "",
                "username": r.get("username") or "",
            })
    except Exception:
        pass
    return out



def _guild_invites_map(uid: int) -> list:
    out = []
    try:
        for r in db.get_guild_invites(uid) or []:
            out.append({
                "id": str(r.get("id")),
                "guildId": str(r.get("guild_id")),
                "guildName": r.get("guild_name") or "",
            })
    except Exception:
        pass
    return out

def snapshot(uid: int) -> dict:
    nbs = []
    try:
        nbs = [_nb_map(r, uid) for r in db.get_learning_notebooks(uid)]
    except Exception:
        nbs = []
    playlists = []
    history = []
    try:
        playlists = db.get_all_playlists(uid) or []
        for p in playlists:
            if isinstance(p.get("tracks"), str):
                try:
                    p["tracks"] = json.loads(p["tracks"])
                except Exception:
                    p["tracks"] = []
        history = db.get_music_play_history(uid, limit=20) or []
    except Exception:
        pass
    chats = []
    friends = _friends_map(uid)
    if friends:
        try:
            chats = [
                {
                    "id": str(m.get("id")),
                    "senderId": str(m.get("sender_id")),
                    "senderName": "",
                    "senderAvatar": "⚔️",
                    "text": m.get("message") or "",
                    "timestamp": m.get("created_at") or "",
                    "isSelf": str(m.get("sender_id")) == str(uid),
                }
                for m in (db.get_messages(uid, int(friends[0]["id"])) or [])
            ]
        except Exception:
            chats = []
    return {
        "notebooks": nbs,
        "loveSpace": _love_map(uid),
        "friends": friends,
        "friendRequests": _friend_requests_map(uid),
        "coupleRequests": _couple_requests_map(uid),
        "chatMessages": chats,
        "guild": _guild_map(uid),
        "guildInvites": _guild_invites_map(uid),
        "pvpChallenges": _pvp_map(uid),
        "playlists": playlists,
        "musicHistory": history,
    }


# ──────────────────────────────────────────────────────────────────────────────
# P44 — Friends chat parity (ChatDialog hybrid: cloud Supabase bila linked,
#       else local SQLite). Semua aturan bisnis tetap di database.py/cloud_service.py.
# ──────────────────────────────────────────────────────────────────────────────
def _chat_attachment_payload(a: dict) -> dict:
    thumb = a.get("thumbnail_data")
    return {
        "id": str(a.get("id")),
        "originalFilename": a.get("original_filename") or "attachment",
        "mimeType": a.get("mime_type") or "",
        "sizeBytes": int(a.get("size_bytes") or 0),
        "width": a.get("width"),
        "height": a.get("height"),
        "thumbnailData": base64.b64encode(bytes(thumb)).decode("ascii") if thumb else None,
    }


def _ts_epoch(v, naive_is_utc=False):
    """Ubah timestamp chat (datetime/str, aware/naive) → unix detik (int) atau None.

    Frontend memakai `epoch` ini untuk merender jam pesan di ZONA LOKASI USER
    (browser), sama persis dengan jam app — jadi chat selalu sinkron dengan jam
    user berapa pun zona server-nya.
      - aware    → .timestamp() (instan absolut, benar).
      - naive    → dianggap UTC bila `naive_is_utc` (timestamp cloud Supabase),
                   selain itu dianggap waktu lokal sistem (datetime.now() penulis
                   pesan lokal) — konsisten karena dibaca di proses yang sama.
    """
    import datetime as _dt
    if v in (None, ""):
        return None
    if isinstance(v, bool):
        return None
    if isinstance(v, (int, float)):
        return int(v)
    if isinstance(v, _dt.datetime):
        dt = v
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=_dt.timezone.utc) if naive_is_utc else dt.astimezone()
    elif isinstance(v, str):
        s = v.strip()
        if not s:
            return None
        if s.endswith("Z"):
            s = s[:-1] + "+00:00"
        try:
            dt = _dt.datetime.fromisoformat(s)
        except Exception:
            try:
                dt = _dt.datetime.strptime(s, "%Y-%m-%d %H:%M:%S")
            except Exception:
                return None
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=_dt.timezone.utc) if naive_is_utc else dt.astimezone()
    else:
        return None
    try:
        return int(dt.timestamp())
    except Exception:
        return None


def _local_message_payload(m: dict, uid: int) -> dict:
    return {
        "id": str(m.get("id")),
        "senderId": str(m.get("sender_id")),
        "text": m.get("message") or "",
        "isSelf": bool(m.get("sender_id") == uid),
        "createdAt": m.get("created_at") or "",
        "epoch": _ts_epoch(m.get("created_at"), naive_is_utc=False),
        "editedAt": m.get("edited_at") or "",
        "deletedAt": m.get("deleted_at") or "",
        "replyToId": str(m.get("reply_to_id")) if m.get("reply_to_id") else None,
        "syncStatus": "synced",
        "reactions": m.get("reactions") or {},
        "attachments": [_chat_attachment_payload(a) for a in (m.get("attachments") or [])],
    }


def _cloud_message_payload(m: dict, current_cid) -> dict:
    return {
        "id": str(m.get("cloud_id")),
        "senderId": str(m.get("sender_cloud_id")),
        "text": m.get("body") or "",
        "isSelf": bool(str(m.get("sender_cloud_id")) == str(current_cid or "")),
        "createdAt": m.get("created_at") or "",
        "epoch": _ts_epoch(m.get("created_at"), naive_is_utc=True),
        "editedAt": m.get("edited_at") or "",
        "deletedAt": m.get("deleted_at") or "",
        "replyToId": m.get("reply_to_cloud_id"),
        "syncStatus": m.get("sync_status") or "synced",
        "reactions": m.get("reactions") or {},
        "attachments": [_chat_attachment_payload(a) for a in (m.get("attachments") or [])],
    }


def _cloud_service_for_user(uid: int):
    """Return CloudService bila user cloud-linked DAN session terautentikasi, else None."""
    try:
        if not db.get_cloud_user_link(uid):
            return None
        from sync_service import get_sync_service
        if not get_sync_service().ensure_session(uid):
            return None
        from cloud_service import get_cloud_service
        return get_cloud_service()
    except Exception:
        return None


def _cloud_chat_context(uid: int, fid: int):
    """Return (cloud, conversation_id) bila chat cloud aktif (parity ChatDialog.__init__),
    else (None, None). Cloud aktif hanya bila user linked + friend punya cloud_user_id
    + session terautentikasi. conversation_id di-cache di cloud_conversations agar
    tidak RPC setiap request."""
    try:
        friend = db.get_user(fid) or {}
        friend_cid = friend.get("cloud_user_id")
        if not friend_cid:
            return None, None
        cloud = _cloud_service_for_user(uid)
        if cloud is None:
            return None, None
        cached = db.get_cloud_conversation(uid, fid) or {}
        conv_id = cached.get("cloud_id")
        if not conv_id:
            conv = cloud.get_or_create_direct_conversation(str(friend_cid))
            if isinstance(conv, list):
                conv = conv[0] if conv else {}
            if isinstance(conv, dict):
                conv_id = conv.get("id") or conv.get("conversation_id")
            else:
                conv_id = conv
            if not conv_id:
                return None, None
            conv_id = str(conv_id)
            db.save_cloud_conversation(uid, fid, conv_id)
        return cloud, str(conv_id)
    except Exception:
        return None, None


def _refresh_cloud_chat(cloud, conv_id: str, uid: int) -> int:
    """Parity ChatDialog._refresh_cloud_page: tarik 50 pesan + reactions + attachments."""
    remote = cloud.fetch_direct_messages(conv_id, 50) or []
    db.cache_cloud_messages(remote)
    ids = [row.get("id") for row in remote if row.get("id")]
    if ids:
        db.cache_cloud_message_reactions(cloud.fetch_message_reactions(ids) or [], ids)
        try:
            db.cache_cloud_chat_attachments(uid, cloud.fetch_message_attachments(ids) or [])
        except Exception:
            pass
    return len(remote)


def _load_chat_payload(uid: int, fid: int, limit: int) -> dict:
    """Parity ChatDialog._load_messages: hybrid cloud/local + mark-read + typing."""
    ctx = _cloud_chat_context(uid, fid)
    if ctx[0] is not None:
        cloud, conv_id = ctx
        try:
            _refresh_cloud_chat(cloud, conv_id, uid)
        except Exception:
            pass
        try:
            cloud.mark_conversation_read(conv_id)
        except Exception:
            pass
        db.mark_cloud_conversation_read_local(conv_id)
        rows = db.get_cached_cloud_messages(conv_id, limit) or []
        current = (db.get_cloud_user_link(uid) or {}).get("cloud_user_id")
        friend_typing = False
        try:
            typing = cloud.get_conversation_typing(conv_id) or []
            friend_typing = any(str(row.get("user_id") or "") != str(current or "") for row in typing)
        except Exception:
            pass
        return {
            "ok": True,
            "cloudMode": True,
            "friendTyping": friend_typing,
            "messages": [_cloud_message_payload(m, current) for m in rows],
        }
    msgs = [_local_message_payload(m, uid) for m in (db.get_messages(uid, fid, limit) or [])]
    return {"ok": True, "cloudMode": False, "messages": msgs}


# ── A06: ekspor artefak Studio (.md / .txt) ─────────────────────────────────
_STUDIO_TITLES = {
    "quiz": "Quiz", "flashcards": "Flashcards", "audio_overview": "Audio Overview",
    "mind_map": "Mind Map", "study_guide": "Study Guide", "faq": "FAQ",
    "timeline": "Timeline", "summary": "Summary",
    # C05.
    "briefing_doc": "Briefing Doc", "data_table": "Data Table",
    "infographic": "Infographic", "slide_deck": "Slide Deck",
}


def _artifact_csv(gtype: str, title: str, content: str) -> str:
    """C05: ekspor Data Table sebagai CSV (delimiter `;` + BOM agar Excel ID langsung benar)."""
    import csv as _csv
    import io as _io
    gtype = (gtype or "").lower()
    raw = (content or "").strip()
    buf = _io.StringIO()
    w = _csv.writer(buf, delimiter=";", lineterminator="\r\n")
    try:
        data = json.loads(_strip_json_fence(raw)) if gtype == "data_table" else None
        cols = [str(c) for c in ((data or {}).get("columns") or [])][:8]
        rows = (data or {}).get("rows") or []
        if cols:
            if title:
                w.writerow([title])
            w.writerow(cols)
            for r in rows:
                cells = [str(c) for c in (r if isinstance(r, list) else [r])]
                w.writerow((cells + [""] * len(cols))[:len(cols)])
            return "\ufeff" + buf.getvalue()
    except Exception:
        pass
    w.writerow([title or "Data"])
    w.writerow([raw[:200000]])
    return "\ufeff" + buf.getvalue()


def _artifact_html_slides(gtype: str, title: str, content: str) -> str:
    """C05: ekspor Slide Deck sebagai SATU berkas HTML mandiri (CSS+JS inline, tombol+keyboard)."""
    import html as _html
    raw = (content or "").strip()
    slides = []
    try:
        data = json.loads(_strip_json_fence(raw))
        arr = data.get("slides") if isinstance(data, dict) else []
        for s in arr or []:
            if isinstance(s, dict):
                slides.append({"title": str(s.get("title") or ""),
                               "bullets": [str(b) for b in (s.get("bullets") or [])]})
    except Exception:
        slides = []
    if not slides:
        slides = [{"title": title or "Slide", "bullets": [raw[:5000] or "(kosong)"]}]
    deck_title = _html.escape(title or "Slide Deck")
    cards = []
    for i, s in enumerate(slides, 1):
        lis = "".join(f"<li>{_html.escape(b)}</li>" for b in s["bullets"][:8])
        cards.append(
            f'<section class="slide" id="s{i}" style="display:{"block" if i == 1 else "none"}">'
            f'<div class="num">{i} / {len(slides)}</div>'
            f"<h1>{_html.escape(s['title'])}</h1>"
            f"<ul>{lis}</ul></section>")
    return ("<!DOCTYPE html><html lang=\"id\"><head><meta charset=\"utf-8\">"
            f"<title>{deck_title}</title><style>"
            "body{font-family:system-ui,sans-serif;background:#0f172a;color:#e2e8f0;margin:0;padding:32px}"
            ".slide{max-width:760px;margin:0 auto;background:#1e293b;border:1px solid #334155;"
            "border-radius:16px;padding:40px;min-height:320px}"
            "h1{font-size:28px;margin:0 0 20px}.num{float:right;color:#64748b;font-size:13px}"
            "li{margin:10px 0;font-size:17px;line-height:1.5}.nav{text-align:center;margin-top:24px}"
            "button{background:#7c3aed;color:#fff;border:0;border-radius:10px;"
            "padding:10px 22px;font-size:15px;margin:0 6px;cursor:pointer}"
            "@media print{.nav{display:none}.slide{display:block!important;page-break-after:always;border:0}}"
            "</style></head><body>" + "".join(cards) +
            "<div class=\"nav\"><button onclick=\"go(-1)\">\u2039</button>"
            "<button onclick=\"go(1)\">\u203a</button></div>"
            "<script>let i=1;const n=" + str(len(slides)) + ";"
            "function go(d){document.getElementById(\u0027s\u0027+i).style.display=\u0027none\u0027;"
            "i=(i-1+d+n)%n+1;document.getElementById(\u0027s\u0027+i).style.display=\u0027block\u0027;}"
            "document.addEventListener(\u0027keydown\u0027,e=>{"
            "if(e.key===\u0027ArrowRight\u0027||e.key===\u0027 \u0027)go(1);"
            "if(e.key===\u0027ArrowLeft\u0027)go(-1);});</script></body></html>")


def _artifact_plain(gtype: str, title: str, content: str) -> str:
    """Versi teks polos (tanpa Markdown) untuk ekspor .txt."""
    gtype = (gtype or "").lower()
    raw = (content or "").strip()
    lines = [f"{title or _STUDIO_TITLES.get(gtype, 'Studio')}",
             f"({_STUDIO_TITLES.get(gtype, gtype)} · CraftLife v1.6.3)", ""]
    if gtype in ("quiz", "flashcards"):
        try:
            data = json.loads(_strip_json_fence(raw))
            if gtype == "quiz":
                qs = (data.get("questions") if isinstance(data, dict) else data) or []
                for i, q in enumerate(qs, 1):
                    if not isinstance(q, dict):
                        continue
                    qtype = str(q.get("type") or ("essay" if (q.get("model_answer") or q.get("modelAnswer")) and not q.get("options") else "mc")).lower()
                    lines.append(f"{i}. {q.get('q') or q.get('question') or ''}")
                    if qtype == "essay":
                        lines.append(f"   [Esai] Jawaban contoh: {q.get('model_answer') or q.get('modelAnswer') or '-'}")
                    else:
                        answer = q.get("answer")
                        if answer is None:
                            answer = q.get("correctAnswerIndex")
                        for oi, opt in enumerate(q.get("options") or []):
                            lines.append(f"   {'*' if int(oi) == int(answer or 0) else '-'} {opt}")
                        exp = q.get("explain") or q.get("explanation") or ""
                        if exp:
                            lines.append(f"   Penjelasan: {exp}")
                    lines.append("")
            else:
                arr = data if isinstance(data, list) else (data.get("cards") or data.get("flashcards") or [])
                for i, card in enumerate(arr, 1):
                    lines.append(f"{i}. {card.get('front') or card.get('question') or ''}")
                    lines.append(f"   {card.get('back') or card.get('answer') or ''}")
                    lines.append("")
            return "\n".join(lines)
        except Exception:
            pass
    if gtype == "data_table":
        try:
            data = json.loads(_strip_json_fence(raw))
            cols = [str(c) for c in (data.get("columns") or [])][:8]
            rows = data.get("rows") or []
            if cols:
                lines.append(" | ".join(cols))
                for r in rows:
                    cells = [str(c) for c in (r if isinstance(r, list) else [r])]
                    lines.append(" | ".join((cells + [""] * len(cols))[:len(cols)]))
                lines.append("")
                return "\n".join(lines)
        except Exception:
            pass
    if gtype == "slide_deck":
        try:
            data = json.loads(_strip_json_fence(raw))
            slides = data.get("slides") if isinstance(data, dict) else []
            if slides:
                for i, s in enumerate(slides, 1):
                    if not isinstance(s, dict):
                        continue
                    lines.append(f"Slide {i}: {s.get('title') or ''}")
                    for b in s.get("bullets") or []:
                        lines.append(f"  - {b}")
                    lines.append("")
                return "\n".join(lines)
        except Exception:
            pass
    if gtype == "infographic":
        try:
            data = json.loads(_strip_json_fence(raw))
            if isinstance(data, dict) and "points" in data:
                if data.get("subtitle"):
                    lines.append(str(data["subtitle"]))
                    lines.append("")
                for st in data.get("stats") or []:
                    if isinstance(st, dict):
                        lines.append(f"[{st.get('value') or ''}] {st.get('label') or ''}")
                lines.append("")
                for p in data.get("points") or []:
                    if isinstance(p, dict):
                        lines.append(f"* {p.get('heading') or ''}: {p.get('text') or ''}")
                lines.append("")
                return "\n".join(lines)
        except Exception:
            pass
    lines.append(raw)
    return "\n".join(lines)


def _artifact_markdown(gtype: str, title: str, content: str, meta: dict) -> str:
    """Ubah isi generasi (JSON atau teks) menjadi Markdown rapi untuk diekspor."""
    gtype = (gtype or "").lower()
    head = f"# {title or _STUDIO_TITLES.get(gtype, 'Studio')}\n\n"
    head += f"> {_STUDIO_TITLES.get(gtype, gtype)} · CraftLife v1.6.3"
    if meta.get("itemCount"):
        head += f" · {meta['itemCount']} item"
    elif meta.get("words"):
        head += f" · {meta['words']} kata"
    head += "\n\n---\n\n"
    raw = (content or "").strip()
    if gtype == "quiz":
        try:
            data = json.loads(_strip_json_fence(raw))
            qs = (data.get("questions") if isinstance(data, dict) else data) or []
            quiz_title = data.get("title") if isinstance(data, dict) else ""
            body = [f"**Judul quiz:** {quiz_title}\n"] if quiz_title else []
            for i, q in enumerate(qs, 1):
                if not isinstance(q, dict):
                    continue
                qtype = str(q.get("type") or ("essay" if (q.get("model_answer") or q.get("modelAnswer")) and not q.get("options") else "mc")).lower()
                body.append(f"### {i}. {q.get('q') or q.get('question') or ''}")
                if qtype == "essay":
                    body.append(f"*Tipe: esai*\n")
                    body.append(f"**Jawaban contoh:** {q.get('model_answer') or q.get('modelAnswer') or '-'}\n")
                else:
                    opts = q.get("options") or []
                    answer = q.get("answer")
                    if answer is None:
                        answer = q.get("correctAnswerIndex")
                    for oi, opt in enumerate(opts):
                        marker = " ✅" if int(oi) == int(answer or 0) else ""
                        body.append(f"- [{'x' if marker else ' '}] {opt}{marker}")
                    exp = q.get("explain") or q.get("explanation") or ""
                    if exp:
                        body.append(f"\n*Penjelasan:* {exp}")
                    body.append("")
            return head + "\n".join(body)
        except Exception:
            return head + raw
    if gtype == "flashcards":
        try:
            data = json.loads(_strip_json_fence(raw))
            arr = data if isinstance(data, list) else (data.get("cards") or data.get("flashcards") or [])
            body = []
            for i, card in enumerate(arr, 1):
                front = card.get("front") or card.get("question") or ""
                back = card.get("back") or card.get("answer") or ""
                body.append(f"**{i}. {front}**\n\n{back}\n")
            return head + "\n".join(body)
        except Exception:
            return head + raw
    if gtype == "audio_overview":
        lines = []
        for line in raw.splitlines():
            if "|" in line:
                speaker, text = line.split("|", 1)
                speaker = speaker.strip().replace("HOST_A", "Alex").replace("HOST_B", "Sam")
                lines.append(f"**{speaker or 'Host'}:** {text.strip()}\n")
        return head + ("\n".join(lines) or raw)
    if gtype == "mind_map":
        try:
            return head + "```json\n" + json.dumps(json.loads(_strip_json_fence(raw)), indent=2, ensure_ascii=False) + "\n```"
        except Exception:
            return head + raw
    if gtype == "data_table":
        try:
            data = json.loads(_strip_json_fence(raw))
            cols = [str(c) for c in (data.get("columns") or [])][:8]
            rows = data.get("rows") or []
            if not cols:
                return head + raw
            body = ["| " + " | ".join(cols) + " |",
                    "|" + "|".join(["---"] * len(cols)) + "|"]
            for r in rows:
                cells = [str(c) for c in (r if isinstance(r, list) else [r])]
                cells = (cells + [""] * len(cols))[:len(cols)]
                body.append("| " + " | ".join(cells) + " |")
            return head + "\n".join(body) + "\n"
        except Exception:
            return head + raw
    if gtype == "slide_deck":
        try:
            data = json.loads(_strip_json_fence(raw))
            slides = data.get("slides") if isinstance(data, dict) else []
            if not slides:
                return head + raw
            body = []
            for i, s in enumerate(slides, 1):
                if not isinstance(s, dict):
                    continue
                body.append(f"## Slide {i}: {s.get('title') or ''}\n")
                for b in s.get("bullets") or []:
                    body.append(f"- {b}")
                body.append("")
            return head + "\n".join(body)
        except Exception:
            return head + raw
    if gtype == "infographic":
        try:
            data = json.loads(_strip_json_fence(raw))
            if not isinstance(data, dict) or "points" not in data:
                return head + raw
            body = []
            if data.get("subtitle"):
                body.append(f"*{data.get('subtitle')}*\n")
            for st in data.get("stats") or []:
                if isinstance(st, dict):
                    body.append(f"- **{st.get('value') or ''}** \u2014 {st.get('label') or ''}")
            body.append("")
            for p in data.get("points") or []:
                if isinstance(p, dict):
                    body.append(f"### {p.get('heading') or ''}\n\n{p.get('text') or ''}\n")
            return head + "\n".join(body)
        except Exception:
            return head + raw
    return head + raw


def handle_get(path: str, uid: int, qs=None):
    qs = qs or {}
    if path == "/api/learning/notebooks":
        return {"ok": True, "notebooks": snapshot(uid)["notebooks"]}
    if path == "/api/learning/generations/export":
        # A06: ekspor satu artefak Studio sebagai berkas .md / .txt.
        # Berkas "dititipkan" (staged) ke server lalu diunduh lewat jalur unduhan
        # terverifikasi A03.5 (`/api/system/download-file?id=…`) — jadi di shell Qt
        # maupun browser berkas benar-benar sampai ke komputer user.
        try:
            gid = int((qs.get("generationId") or ["0"])[0] or 0)
            nid = int((qs.get("notebookId") or ["0"])[0] or 0)
        except (TypeError, ValueError):
            gid = nid = 0
        fmt = ((qs.get("format") or ["md"])[0] or "md").strip().lower()
        if fmt not in ("md", "txt", "csv", "html"):
            fmt = "md"
        if not gid or not nid:
            return {"ok": False, "msg": "learning_not_found"}
        row = db.get_learning_generation(gid, nid)
        if not row:
            return {"ok": False, "msg": "learning_not_found"}
        title = " ".join(str(row.get("title") or "").split()) or "studio"
        gtype = (row.get("type") or "summary").lower()
        content = row.get("content") or ""
        meta = _artifact_meta(gtype, content)
        # C05: csv hanya untuk data_table, html hanya untuk slide_deck (else fallback md).
        if fmt == "csv" and gtype != "data_table":
            fmt = "md"
        if fmt == "html" and gtype != "slide_deck":
            fmt = "md"
        if fmt == "md":
            data = _artifact_markdown(gtype, title, content, meta)
        elif fmt == "csv":
            data = _artifact_csv(gtype, title, content)
        elif fmt == "html":
            data = _artifact_html_slides(gtype, title, content)
        else:
            data = _artifact_plain(gtype, title, content)
        safe = "".join(ch for ch in title if ch not in '<>:"/\\|?*' and ord(ch) >= 32).strip(" .") or "studio"
        safe = safe[:60]
        try:
            import api_server as _api  # lazy: hindari impor melingkar saat modul dimuat
            staged = _api._dl_stage_file(uid, {
                "name": f"{safe}.{fmt}",
                "mime": {"md": "text/markdown", "txt": "text/plain",
                         "csv": "text/csv", "html": "text/html"}.get(fmt, "text/plain"),
                "text": data,
            })
        except Exception as e:
            return {"ok": False, "msg": str(e)}
        if not isinstance(staged, dict) or not staged.get("ok"):
            return staged if isinstance(staged, dict) else {"ok": False, "msg": "stage_failed"}
        staged["format"] = fmt
        staged["gtype"] = gtype
        staged["title"] = title
        staged["itemCount"] = meta.get("itemCount") or 0
        return staged
    if path == "/api/music/playlists":
        # Parity MusicPage._ensure_favorite_playlist: jamin playlist "Favorite"
        # (is_favorite=1) selalu ada, supaya tombol "Tambah ke favorit" valid.
        try:
            if not any(row.get("is_favorite") for row in db.get_all_playlists(uid)):
                db.create_playlist(uid, "Favorite", 1)
        except Exception:
            pass
        s = snapshot(uid)
        return {"ok": True, "playlists": s["playlists"], "history": s["musicHistory"]}
    if path == "/api/love":
        # P61: segarkan mirror couple cloud → lokal supaya relasi couple yang
        # terjadi di device lain langsung terdeteksi (best-effort, aman offline).
        _refresh_couple_mirror(uid)
        return {"ok": True, "loveSpace": snapshot(uid)["loveSpace"]}
    if path == "/api/love/couple-tracking":
        _refresh_couple_mirror(uid)
        return _couple_tracking_map(uid)
    if path == "/api/love/events/upcoming":
        # A09: acara & hari istimewa dalam rentang `days` (default 90).
        try:
            days = int((qs.get("days") or ["90"])[0] or 90)
        except (TypeError, ValueError):
            days = 90
        days = max(1, min(730, days))
        items = db.upcoming_relationship_events(uid, days)
        return {"ok": True, "days": days, "count": len(items),
                "events": items, "specialDays": [it for it in items if it.get("isSpecial")]}
    if path == "/api/settings/cleanup":
        # C06: respons camelCase konsisten (dulu snake_case → UI tampil 0 B) +
        # rincian ukuran per tabel.
        st = db.get_maintenance_state(uid)
        rd = int(st.get("retention_days") or 0)
        if rd > 0:
            est = db.estimate_tracker_purge(uid, rd)
        else:
            est = {"cutoff": "", "tables": {}, "total_rows": 0, "db_size_bytes": db.db_file_size_bytes()}
        try:
            sizes = db.db_table_sizes()
        except Exception:
            sizes = {"tables": [], "total_bytes": est.get("db_size_bytes", 0)}
        return {"ok": True, "cleanup": {
            "retentionDays": rd, "auto": bool(st.get("auto")),
            "lastPurgeAt": st.get("last_purge_at") or "",
            "schedule": st.get("schedule") or "monthly",
            "cutoff": est.get("cutoff") or "", "tables": est.get("tables") or {},
            "totalRows": int(est.get("total_rows") or 0),
            "dbSizeBytes": int(est.get("db_size_bytes") or 0),
            "tableSizes": sizes.get("tables") or [],
            "dbTotalBytes": int(sizes.get("total_bytes") or 0),
        }}
    if re.match(r"^/api/friends/[^/]+/chat$", path):
        # Parity ChatDialog._load_messages (hybrid cloud/local).
        fid = path.split("/")[3]
        try:
            fid_i = int(fid)
        except ValueError:
            return {"ok": False, "msg": "not found"}
        try:
            limit = int((qs or {}).get("limit", [50])[0] or 50)
        except Exception:
            limit = 50
        limit = max(1, min(2000, limit))
        try:
            db.mark_messages_read(uid, fid_i)
        except Exception:
            pass
        return _load_chat_payload(uid, fid_i, limit)
    if path == "/api/friends":
        s = snapshot(uid)
        return {"ok": True, "friends": s["friends"], "friendRequests": s.get("friendRequests") or [], "coupleRequests": s.get("coupleRequests") or []}
    if path == "/api/pvp":
        s = snapshot(uid)
        return {"ok": True, "pvpChallenges": s.get("pvpChallenges") or []}
    if path.startswith("/api/friends/") and path.endswith("/profile"):
        try:
            fid = int(path.split("/")[3])
        except (ValueError, IndexError):
            return {"ok": False, "error": "id"}
        d = db.get_friend_profile_details(fid)
        if not d:
            return {"ok": False, "error": "not_found"}
        u = d.get("user") or {}
        return {
            "ok": True,
            "profile": {
                "id": str(u.get("id") or fid),
                "displayName": u.get("display_name") or "",
                "username": u.get("username") or "",
                "bio": u.get("bio") or "",
                "avatarEmoji": u.get("avatar_emoji") or "⚔️",
                "avatarColor": u.get("avatar_color") or "",
                "level": d.get("level"),
                "xp": d.get("xp"),
                "xpNeeded": d.get("xp_needed"),
                "totalXp": d.get("total_xp_earned"),
                "sportLevel": d.get("sport_level"),
                "rebirthCount": d.get("rebirth_count"),
                "title": d.get("selected_title") or "",
                "avatarClass": d.get("avatar_class") or "",
                "guildName": d.get("guild_name") or "",
                "joinDate": d.get("join_date") or "",
                "achievementsDone": d.get("achievements_done"),
                "achievementsTotal": d.get("achievements_total"),
                "latestAchievements": d.get("latest_achievements") or [],
                "tasksDone": d.get("tasks_done"),
                "pomodoroMinutes": d.get("pomodoro_minutes"),
                # P26: sertakan statistik detail utk FriendProfileDialog 1:1 PyQt.
                "stats": d.get("stats") or {},
                # P26: relasi couple antara user & teman (friend/couple/pending).
                "relation": (db.get_couple_status_between(uid, fid) or {}).get("status", "friend"),
            },
        }
    if path == "/api/notifications":
        rows = db.get_notification_center(uid, limit=50) if hasattr(db, "get_notification_center") else db.get_notifications(uid, unread_only=False)
        items = []
        for r in rows or []:
            items.append({
                "id": str(r.get("id")),
                "message": r.get("message") or "",
                "type": r.get("notification_type") or r.get("type") or "info",
                "isRead": bool(r.get("is_read")),
                "createdAt": r.get("created_at") or "",
            })
        unread = sum(1 for i in items if not i["isRead"])
        return {"ok": True, "notifications": items, "unread": unread}
    if path == "/api/guild":
        s = snapshot(uid)
        return {"ok": True, "guild": s["guild"], "guildInvites": s.get("guildInvites") or []}
    if path == "/api/guild/messages":
        # Parity GuildChatDialog._load_messages: daftar pesan guild LOKAL (page
        # guild lokal di PyQt selalu pakai DB lokal; chat cloud hanya ada di
        # halaman online guild yang terpisah). Kembalikan pesan + isLeader +
        # timestamp agar render [HH:MM] name: message konsisten.
        u = db.get_user(uid) or {}
        gid = u.get("guild_id")
        if not gid:
            return {"ok": True, "messages": [], "isLeader": False}
        try:
            limit = int((qs or {}).get("limit", [100])[0] or 100)
        except Exception:
            limit = 100
        limit = max(1, min(2000, limit))
        g = db.get_guild(gid) or {}
        gcore = g.get("guild") or g
        is_leader = str(gcore.get("leader_id") or "") == str(uid)
        msgs = []
        try:
            msgs = [
                {
                    "id": str(m.get("id")),
                    "senderId": str(m.get("sender_id")),
                    "senderName": m.get("display_name") or m.get("username") or "",
                    "text": m.get("message") or "",
                    "createdAt": m.get("created_at") or "",
                    "epoch": _ts_epoch(m.get("created_at"), naive_is_utc=False),
                    "isSelf": str(m.get("sender_id")) == str(uid),
                }
                for m in (db.get_guild_messages(gid, limit) or [])
            ]
        except Exception:
            pass
        return {"ok": True, "messages": msgs, "isLeader": is_leader}
    if path == "/api/guild/rewards":
        # Parity GuildPage._show_unclaimed_rewards (dialog check saat load page).
        return {"ok": True, "rewards": db.get_unclaimed_boss_rewards(uid)}
    if path == "/api/guild/bosses":
        # Parity _fill_boss_cb: semua boss utk guild (default + custom), filter
        # tier & ketersediaan seasonal diterapkan di client; server kirim flag.
        u = db.get_user(uid) or {}
        gid = u.get("guild_id")
        items = []
        try:
            for bid, bd in (db.get_all_bosses_for_guild(gid) or {}).items():
                try:
                    avail = bool(db.is_boss_available(bid))
                except Exception:
                    avail = True
                items.append({
                    "id": bid,
                    "name": bd.get("name") or bid,
                    "icon": bd.get("icon") or "🐉",
                    "tier": bd.get("tier") or "normal",
                    "hp": int(bd.get("hp") or 0),
                    "atk": int(bd.get("boss_attack") or bd.get("atk") or 0),
                    "xp": int(bd.get("xp") or 0),
                    "gold": int(bd.get("gold") or 0),
                    "minLevel": int(bd.get("min_level") or 1),
                    "maxLevel": int(bd["max_level"]) if bd.get("max_level") is not None else None,
                    "available": avail,
                })
        except Exception:
            items = []
        return {"ok": True, "bosses": items}
        return {"ok": True, "pvpChallenges": snapshot(uid)["pvpChallenges"]}
    if path == "/api/music/library":
        try:
            import music_downloader as md
            return {"ok": True, "library": md.list_library(), "ytAvailable": bool(md.YT_AVAILABLE)}
        except Exception as e:
            return {"ok": True, "library": [], "ytAvailable": False, "error": str(e)}
    if path.startswith("/api/music/jobs/"):
        jid = path.split("/api/music/jobs/", 1)[-1]
        try:
            import music_downloader as md
            return {"ok": True, "job": md.get_download_job(jid)}
        except Exception as e:
            return {"ok": False, "error": str(e)}
    if path == "/api/music/lyrics":
        # P58: (1) cek lirik TERSIMPAN dulu (source apapun) — kecuali refresh=1;
        # (2) cari web dengan DURASI + ALBUM lagu agar tidak salah versi (live/remix).
        # A02: + prefer=<indeks kandidat> & cache negatif (trek kosong tak diulang terus).
        qs = qs or {}
        key = (qs.get("key") or [""])[0].strip()
        artist = (qs.get("artist") or [""])[0].strip()
        title = (qs.get("title") or [""])[0].strip()
        album = (qs.get("album") or [""])[0].strip()
        fpath = (qs.get("path") or [""])[0].strip()
        refresh = (qs.get("refresh") or [""])[0] == "1"
        prefer = (qs.get("prefer") or [""])[0].strip() or None
        try:
            dur = float((qs.get("duration") or ["0"])[0]) or None
        except (TypeError, ValueError):
            dur = None
        if key and not refresh:
            try:
                row = db.get_song_lyrics(uid, key)
            except Exception:
                row = None
            if row and (row.get("plain") or row.get("synced")):
                return {"ok": True, "lyrics": {
                    "plain": row.get("plain") or "", "synced": row.get("synced") or "",
                    "source": row.get("source") or "saved", "saved": True,
                    "offsetMs": int(row.get("offset_ms") or 0)}}
        ly = get_lyrics(artist, title, fpath, dur, album=album, prefer=prefer, refresh=refresh)
        ly.update({"saved": False, "offsetMs": 0})
        return {"ok": True, "lyrics": ly}
    if path == "/api/music/lyrics-candidates":
        # A02: daftar kandidat lirik (maks 12) dari LRCLIB get/search + lyrics.ovh +
        # lirik tertanam, sudah diberi skor album/durasi/versi → user pilih yang benar.
        qs = qs or {}
        artist = (qs.get("artist") or [""])[0].strip()
        title = (qs.get("title") or [""])[0].strip()
        album = (qs.get("album") or [""])[0].strip()
        fpath = (qs.get("path") or [""])[0].strip()
        try:
            dur = float((qs.get("duration") or ["0"])[0]) or None
        except (TypeError, ValueError):
            dur = None
        try:
            limit = max(1, min(int((qs.get("limit") or ["12"])[0]), 24))
        except (TypeError, ValueError):
            limit = 12
        try:
            cands = collect_lyrics_candidates(artist, title, album=album, duration=dur,
                                              file_path=fpath, limit=limit)
        except Exception as e:
            return {"ok": True, "candidates": [], "error": str(e)}
        return {"ok": True, "candidates": cands, "count": len(cands),
                "query": {"artist": artist, "title": title, "album": album, "duration": dur}}
    if path == "/api/music/track-meta":
        # A02: metadata batch untuk trek yang melewati batas listing library
        # (title/artist/album/duration) → lirik tetap dicocokkan dengan durasi.
        qs = qs or {}
        raw_paths = (qs.get("paths") or [""])[0]
        paths = [p for p in (raw_paths.split("|") if raw_paths else []) if p.strip()]
        if not paths:
            paths = [p for p in qs.get("path", []) if p.strip()]
        try:
            import music_downloader as md
            rows = md.get_track_meta_many(paths)
        except Exception as e:
            return {"ok": True, "tracks": [], "error": str(e)}
        return {"ok": True, "tracks": rows, "count": len(rows)}
    if path == "/api/music/lyrics-template":
        # A03: template .lrc siap unduh (komentar cara pakai + tag + 6 baris contoh).
        return {"__file_bytes__": lyrics_template_bytes(),
                "name": "craftlife-lyrics-template.lrc", "mime": "text/plain"}
    if path == "/api/music/lyrics-export":
        # A03: ekspor lirik tersimpan ke .lrc (bertimestamp + header [ti:][ar:][al:][offset:])
        # atau .txt (teks polos). Marker __file_bytes__ → api_server mengirim sebagai unduhan.
        qs = qs or {}
        key = (qs.get("key") or [""])[0].strip()
        fmt = ((qs.get("format") or ["lrc"])[0] or "lrc").strip().lower()
        if fmt not in ("lrc", "txt"):
            fmt = "lrc"
        row = None
        if key:
            try:
                row = db.get_song_lyrics(uid, key)
            except Exception:
                row = None
        if not row or not (row.get("plain") or row.get("synced")):
            return {"ok": False, "error": "no_saved_lyrics"}
        title = row.get("track_title") or (qs.get("title") or [""])[0] or "lyrics"
        artist = row.get("artist") or (qs.get("artist") or [""])[0] or ""
        album = (qs.get("album") or [""])[0].strip()
        offset_ms = int(row.get("offset_ms") or 0)
        if fmt == "txt":
            text = (row.get("plain") or "").strip()
            if not text:
                text = _lrc_strip_timestamps(row.get("synced") or "").strip()
            data = text + "\n"
            mime = "text/plain"
        else:
            data = build_lrc_export(title, artist, album, offset_ms,
                                    synced=row.get("synced") or "", plain=row.get("plain") or "")
            mime = "text/plain"
        safe = "".join(ch for ch in f"{artist} - {title}".strip(" -") if ch.isalnum() or ch in " -_().,")[:80].strip() or "lyrics"
        return {"__file_bytes__": data.encode("utf-8"), "name": f"{safe}.{fmt}", "mime": mime}
    return None


def _clean_lyrics_query(s: str) -> str:
    """Bersihkan judul/artis untuk query online (sama dengan _LyricsFetcher PyQt,
    diperluas: live/remaster/radio-edit/bracket/feat/ft.)."""
    import re as _re
    s = _re.sub(r"\((official|lyric|lyrics|video|audio|mv|hq|hd|live|remaster(?:ed)?|radio[ -]?edit|explicit|clean|deluxe|bonus)[^)]*\)", " ", s, flags=_re.I)
    s = _re.sub(r"\[(official|lyric|lyrics|video|audio|mv|hq|hd|live|remaster(?:ed)?|radio[ -]?edit|explicit|clean)[^\]]*\]", " ", s, flags=_re.I)
    s = _re.sub(r"\bfeat(\.|uring)?\b.*$", " ", s, flags=_re.I)
    s = _re.sub(r"\bft\.?\s+.*$", " ", s, flags=_re.I)
    s = s.replace("_", " ").replace("/", " ")
    return _re.sub(r"\s+", " ", s).strip()


def _read_embedded_lyrics(file_path: str) -> str:
    """Baca lirik tertanam dari file audio (parity MusicPage._embedded_lyrics):
    ID3 USLT/TXXX, Vorbis/FLAC LYRICS, MP4 ©lyr. Import mutagen defensif."""
    try:
        from mutagen.mp3 import MP3
        from mutagen.flac import FLAC
        from mutagen.mp4 import MP4
        from mutagen.oggvorbis import OggVorbis
    except Exception:
        return ""
    try:
        low = file_path.lower()
        if low.endswith(".mp3"):
            audio = MP3(file_path)
            for key in list(audio.keys()):
                if key.startswith("USLT"):
                    text = str(audio[key]).strip()
                    if text:
                        return text
            if audio.tags is not None:
                for key in list(audio.tags.keys()):
                    if key.startswith("TXXX"):
                        frame = audio.tags[key]
                        if "lyric" in (getattr(frame, "desc", "") or "").lower():
                            text = str(frame).strip()
                            if text:
                                return text
        elif low.endswith(".flac"):
            audio = FLAC(file_path)
            for k in ("lyrics", "unsyncedlyrics"):
                value = audio.get(k) or []
                if value and str(value[0]).strip():
                    return str(value[0]).strip()
        elif low.endswith((".m4a", ".mp4")):
            audio = MP4(file_path)
            if audio.tags:
                value = audio.tags.get("\xa9lyr") or []
                if value and str(value[0]).strip():
                    return str(value[0]).strip()
        elif low.endswith((".ogg", ".opus")):
            audio = OggVorbis(file_path)
            for k in ("lyrics", "unsyncedlyrics"):
                value = audio.get(k) or []
                if value and str(value[0]).strip():
                    return str(value[0]).strip()
    except Exception:
        return ""
    return ""


def _norm_lyrics_text(s: str) -> str:
    """Normalisasi ringan utk pencocokan nama (lower, & → and, buang non-alfanumerik)."""
    import re as _re
    s = (s or "").lower().replace("&", " and ")
    return _re.sub(r"[^a-z0-9]+", " ", s).strip()


def _version_markers(text: str) -> list:
    """A02: penanda versi lagu yang sering membuat lirik TIDAK cocok
    (live/remix/karaoke/cover/instrumental/sped up/slowed/acoustic)."""
    t = (text or "").lower()
    return sorted({m for m in (
        "live", "remix", "karaoke", "cover", "instrumental", "sped up", "slowed",
        "acoustic", "re-recorded", "demo", "extended",
    ) if m in t})


def _score_lyrics_candidate(cand: dict, artist: str, title: str, duration=None, album: str = "") -> float:
    """Skor kandidat lirik (P58 + A02).

    P58: kecocokan judul+artis, kedekatan DURASI (≤3 dtk = versi studio yang sama),
    bonus bila synced (lirik live per detik).
    A02: + bonus ALBUM (+1.5) supaya versi album benar, + PENALTI penanda versi
    (live/remix/karaoke/cover/…) yang tidak diminta user, dan toleransi durasi
    bertingkat (≤2 dtk: +3 · ≤5 dtk: +1.5 · >15 dtk: −2).
    """
    score = 0.0
    ca = _norm_lyrics_text(cand.get("artist") or "")
    ct = _norm_lyrics_text(cand.get("title") or "")
    ta = _norm_lyrics_text(artist)
    tt = _norm_lyrics_text(title)
    if tt and ct and (tt in ct or ct in tt):
        score += 2.0
    if ta and ca and (ta in ca or ca in ta):
        score += 2.0
    # A02: album — hanya menambah bila user memang punya info album.
    cal = _norm_lyrics_text(cand.get("album") or "")
    tal = _norm_lyrics_text(album or "")
    if tal and cal and (tal in cal or cal in tal):
        score += 1.5
    # A02: penalti penanda versi yang tidak diminta (sumber "lirik lagu lain" paling umum).
    asked = _version_markers(f"{title} {album or ''}")
    bad = [m for m in _version_markers(f"{cand.get('title') or ''} {cand.get('album') or ''}") if m not in asked]
    if bad:
        score -= 1.5 * len(bad)
    if cand.get("synced"):
        score += 1.5
    try:
        dur = float(duration) if duration else None
    except (TypeError, ValueError):
        dur = None
    if dur:
        try:
            cd = float(cand["duration"]) if cand.get("duration") is not None else None
        except (TypeError, ValueError):
            cd = None
        if cd:
            diff = abs(cd - dur)
            if diff <= 2:
                score += 3.0
            elif diff <= 5:
                score += 1.5
            elif diff > 15:
                score -= 2.0
    return score


def _lyrics_preview(text: str, lines: int = 5) -> str:
    """5 baris pertama untuk pratinjau kandidat (timestamp LRC dibuang)."""
    import re as _re
    clean = _re.sub(r"\[\d{1,2}:\d{1,2}(?:[.:]\d{1,3})?\]", "", text or "")
    rows = [ln.strip() for ln in clean.splitlines()]
    return "\n".join([r for r in rows if r][:lines])


# A02: cache NEGATIF in-memory (trek tanpa lirik tidak memicu 4–6 request berulang).
_NEG_CACHE: dict = {}
_NEG_TTL = 600.0  # detik


def _neg_key(artist: str, title: str, duration=None, album: str = "") -> str:
    try:
        dur = int(float(duration)) if duration else 0
    except (TypeError, ValueError):
        dur = 0
    return f"{_norm_lyrics_text(artist)}|{_norm_lyrics_text(title)}|{_norm_lyrics_text(album)}|{dur}"


def _neg_get(key: str) -> bool:
    import time as _time
    ts = _NEG_CACHE.get(key)
    if not ts:
        return False
    if (_time.time() - ts) > _NEG_TTL:
        _NEG_CACHE.pop(key, None)
        return False
    return True


def _neg_put(key: str) -> None:
    import time as _time
    if len(_NEG_CACHE) > 2000:
        _NEG_CACHE.clear()
    _NEG_CACHE[key] = _time.time()


def _mk_cand(plain: str, synced: str, artist: str, title: str, album: str = "",
             duration=None, source: str = "", cid=None) -> dict:
    """Satu kandidat lirik dalam bentuk seragam (dipakai semua sumber)."""
    return {
        "id": cid, "plain": plain or "", "synced": synced or "",
        "artist": artist or "", "title": title or "", "album": album or "",
        "duration": duration, "source": source or "",
    }


def _lrc_strip_timestamps(text: str) -> str:
    """A03: buang tag metadata + timestamp LRC → teks polos (untuk ekspor .txt)."""
    import re as _re
    body = _re.sub(r"^\s*\[(ar|ti|al|by|re|ve|length|offset)\s*:[^\]]*\]\s*$", "", text or "", flags=_re.I | _re.M)
    body = _re.sub(r"\[\d{1,3}:\d{1,2}(?:[.:]\d{1,3})?\]", "", body)
    rows = [ln.strip() for ln in body.splitlines()]
    return "\n".join([r for r in rows if r])


def _lyrics_report_payload(parsed: dict) -> dict:
    """A03: bentuk laporan validasi yang dikirim ke UI (semua angka + kode peringatan).

    Peringatan dikirim sebagai KODE (mis. ``untimed_lines:3``) agar UI bisa menerjemahkan
    ke id/en lewat i18n — bukan string bahasa yang dikunci di backend.
    """
    return {
        "format": parsed.get("format") or "plain",
        "timedLines": int(parsed.get("timedLines") or 0),
        "breakLines": int(parsed.get("breakLines") or 0),
        "firstMs": int(parsed.get("firstMs") or 0),
        "lastMs": int(parsed.get("lastMs") or 0),
        "lineCount": int(parsed.get("lineCount") or 0),
        "offsetMs": int(parsed.get("offsetMs") or 0),
        "metadata": parsed.get("metadata") or {},
        "warnings": parsed.get("warnings") or [],
        "preview": parsed.get("preview") or [],
    }


def _parse_lrc_like(content: str, duration=None) -> dict:
    """A03 — Parser LRC/plain yang menghasilkan LAPORAN VALIDASI.

    Mendukung:
      • tag metadata standar yang BUKAN baris lirik: ``[ar:]`` ``[ti:]`` ``[al:]``
        ``[by:]`` ``[re:]`` ``[ve:]`` ``[length:]`` ``[offset:±ms]``;
      • timestamp ``[mm:ss]`` / ``[mm:ss.x]`` / ``[mm:ss.xx]`` / ``[mm:ss.xxx]``,
        termasuk ``[m:ss]`` dan **multi-timestamp dalam satu baris**;
      • baris ber-timestamp **tanpa teks** = jeda/instrumen (bukan baris kosong yang error);
      • campuran baris tanpa timestamp → dilaporkan sebagai peringatan.

    Return: ``{format, plain, synced, offsetMs, timedLines, breakLines, firstMs, lastMs,
    metadata, warnings, preview, lineCount}``.
    """
    import re as _re

    meta_re = _re.compile(r"^\s*\[(ar|ti|al|by|re|ve|length|offset)\s*:\s*(.*?)\]\s*$", _re.I)
    ts_re = _re.compile(r"\[(\d{1,3}):(\d{1,2})(?:[.:](\d{1,3}))?\]")

    lines = (content or "").replace("\r\n", "\n").replace("\r", "\n").split("\n")
    metadata = {}
    warnings = []
    out_lines = []           # baris synced yang dibangun ulang (kanonik)
    timed = 0                # baris dengan teks + timestamp
    breaks = 0               # timestamp tanpa teks (jeda)
    plain_lines = []         # teks tanpa timestamp (untuk mode plain)
    offset_ms = 0
    untimed_within_lrc = 0
    bad_brackets = 0

    def _ts_to_ms(m, s, frac):
        ms = int(m) * 60000 + int(s) * 1000
        if frac:
            ms += int((frac + "00")[:3])
        return ms

    for raw in lines:
        line = raw.strip()
        if not line:
            continue
        mmeta = meta_re.match(line)
        if mmeta:
            k = mmeta.group(1).lower()
            v = (mmeta.group(2) or "").strip()
            metadata[k] = v
            if k == "offset":
                try:
                    offset_ms += int(float(v))
                except (TypeError, ValueError):
                    warnings.append("offset_bad_value")
            continue
        stamps = list(ts_re.finditer(line))
        text = ts_re.sub("", line).strip()
        # Sisa bracket aneh (mis. "[xx:yy]") → laporan, bukan crash
        if _re.search(r"\[[^\]]*\]", text):
            bad_brackets += 1
            text = _re.sub(r"\[[^\]]*\]", "", text).strip()
        if stamps:
            if not text:
                breaks += 1
            else:
                timed += 1
            for st in stamps:
                ms = _ts_to_ms(st.group(1), st.group(2), st.group(3))
                out_lines.append((ms, text))
        else:
            if text:
                plain_lines.append(text)
                untimed_within_lrc += 1

    out_lines.sort(key=lambda x: x[0])
    is_lrc = timed > 0
    if is_lrc:
        # Deteksi duplikat & urutan timestamp yang mundur (setelah sort: harus naik).
        seen_ms = set()
        dup = 0
        for ms, _t in out_lines:
            if ms in seen_ms:
                dup += 1
            seen_ms.add(ms)
        if dup:
            warnings.append(f"duplicate_timestamps:{dup}")
    if not is_lrc and plain_lines:
        warnings.append("no_timestamps")
    if is_lrc and untimed_within_lrc:
        warnings.append(f"untimed_lines:{untimed_within_lrc}")
    if bad_brackets:
        warnings.append(f"unknown_tags:{bad_brackets}")
    if is_lrc and timed < 3:
        warnings.append("too_few_lines")
    first_ms = out_lines[0][0] if out_lines else 0
    last_ms = out_lines[-1][0] if out_lines else 0
    if is_lrc and first_ms > 20000:
        warnings.append("first_line_late")
    if duration:
        try:
            dur_ms = float(duration) * 1000
            if is_lrc and last_ms > dur_ms + 5000:
                warnings.append("beyond_track_duration")
        except (TypeError, ValueError):
            pass

    synced = "\n".join(f"[{ms // 60000:02d}:{(ms % 60000) / 1000:05.2f}]{t}" for ms, t in out_lines)
    plain = "" if is_lrc else "\n".join(plain_lines)
    preview = [f"[{ms // 60000:02d}:{(ms % 60000) / 1000:05.2f}]{t}" for ms, t in out_lines[:5]] or plain_lines[:5]
    return {
        "format": "lrc" if is_lrc else "plain",
        "plain": plain,
        "synced": synced,
        "offsetMs": offset_ms,
        "timedLines": timed,
        "breakLines": breaks,
        "firstMs": first_ms,
        "lastMs": last_ms,
        "lineCount": len([ln for ln in lines if ln.strip()]),
        "metadata": metadata,
        "warnings": warnings,
        "preview": preview,
    }


def _fmt_lrc_ms(ms: int) -> str:
    ms = max(0, int(ms))
    return f"[{ms // 60000:02d}:{(ms % 60000) / 1000:05.2f}]"


def lyrics_template_bytes() -> bytes:
    """A03: template .lrc siap pakai (komentar + 6 baris contoh + tag metadata)."""
    text = (
        "# CraftLife — template lirik .lrc\n"
        "# Cara pakai:\n"
        "#   1. Tag di bawah boleh diubah/dihapus. [ar:] artis, [ti:] judul, [al:] album,\n"
        "#      [offset:+500] menggeser lirik (ms; + = lirik lebih lambat, - = lebih cepat).\n"
        "#   2. Tulis satu baris lirik per baris, diawali timestamp [mm:ss.xx].\n"
        "#   3. Baris boleh punya beberapa timestamp sekaligus, mis. [00:12.00][01:20.00]Reff\n"
        "#   4. Timestamp tanpa teks = jeda/instrumen (boleh ditulis [00:30.00] saja).\n"
        "#   5. Simpan sebagai .lrc (UTF-8), lalu unggah lewat tombol Import di panel lirik.\n"
        "[ar:Nama Artis]\n"
        "[ti:Judul Lagu]\n"
        "[al:Nama Album]\n"
        "[by:CraftLife]\n"
        "[offset:0]\n"
        "\n"
        "[00:00.00]Contoh baris pembuka\n"
        "[00:05.35]Baris kedua mulai di detik 5,35\n"
        "[00:11.00]Baris ketiga\n"
        "[00:16.20][00:48.00]Reff — satu teks, dua timestamp\n"
        "[00:24.00]\n"
        "[00:26.50]Baris terakhir contoh\n"
    )
    return text.encode("utf-8")


def build_lrc_export(title: str, artist: str, album: str = "", offset_ms: int = 0,
                     synced: str = "", plain: str = "") -> str:
    """A03: rangkai lirik menjadi berkas .lrc (header tag + baris bertimestamp)."""
    head = [
        f"[ti:{title or ''}]",
        f"[ar:{artist or ''}]",
    ]
    if album:
        head.append(f"[al:{album}]")
    head += [f"[offset:{int(offset_ms or 0)}]", "[re:CraftLife]"]
    if synced:
        # Normalkan timestamp agar file ekspor selalu format kanonik [mm:ss.xx].
        parsed = _parse_lrc_like(synced)
        body = parsed["synced"] or synced
        return "\n".join(head) + "\n\n" + body + "\n"
    body = plain or ""
    return "\n".join(head) + "\n\n" + body + "\n"


def collect_lyrics_candidates(artist: str, title: str, album: str = "", duration=None,
                              file_path: str = "", limit: int = 12, timeout: int = 9) -> list:
    """A02: kumpulkan kandidat lirik dari BANYAK sumber sekaligus lalu beri skor.

    Sumber: LRCLIB ``get`` (durasi eksak + toleransi ±2 dtk) · LRCLIB ``search`` dengan
    varian query (``artist title``, ``title album``, ``artist album title``, ``title``) ·
    lyrics.ovh · lirik tertanam di file. Hasil: daftar terurut skor menurun (maks ``limit``),
    tiap item memuat album/durasi/badge/preview supaya user bisa memilih sendiri.
    """
    import concurrent.futures as _cf
    import requests
    from urllib.parse import quote

    artist_c = _clean_lyrics_query(artist)
    title_c = _clean_lyrics_query(title)
    album_c = _clean_lyrics_query(album or "")
    try:
        dur = float(duration) if duration else None
    except (TypeError, ValueError):
        dur = None
    if not (artist_c or title_c):
        return []

    ua = {"User-Agent": "CraftLifeDesktop/1.0"}
    raw = []

    def _lrclib_row(d, src="lrclib"):
        return _mk_cand(d.get("plainLyrics") or "", d.get("syncedLyrics") or "",
                        d.get("artistName") or "", d.get("trackName") or "",
                        d.get("albumName") or "", d.get("duration"), src, d.get("id"))

    def lrclib_get():
        """get (durasi eksak) → bila kosong, coba get dengan durasi ±2 dtk."""
        tries = [int(dur)] if dur else []
        if dur:
            tries += [int(dur) - 2, int(dur) + 2]
        if not tries:
            tries = [None]
        for t in tries:
            params = {"artist_name": artist_c, "track_name": title_c}
            if t:
                params["duration"] = t
            try:
                r = requests.get("https://lrclib.net/api/get", params=params, headers=ua, timeout=5)
                d = r.json() if r.ok else {}
            except Exception:
                continue
            if isinstance(d, dict) and (d.get("syncedLyrics") or d.get("plainLyrics")):
                return [_lrclib_row(d)]
        return []

    def lrclib_search(q):
        if not (q or "").strip():
            return []
        try:
            r = requests.get("https://lrclib.net/api/search", params={"q": q}, headers=ua, timeout=5)
            rows = (r.json() if r.ok else []) or []
        except Exception:
            return []
        out = []
        for it in rows:
            if not isinstance(it, dict):
                continue
            if it.get("syncedLyrics") or it.get("plainLyrics"):
                out.append(_lrclib_row(it))
            if len(out) >= 12:
                break
        return out

    def ovh():
        if not (artist_c and title_c):
            return []
        try:
            r = requests.get(f"https://api.lyrics.ovh/v1/{quote(artist_c)}/{quote(title_c)}", timeout=5)
            ly = ((r.json() or {}).get("lyrics") or "") if r.ok else ""
        except Exception:
            ly = ""
        return [_mk_cand(ly, "", artist_c, title_c, "", None, "ovh")] if ly else []

    def embedded():
        if not file_path:
            return []
        import os as _os
        try:
            import music_downloader as _md
            real = _os.path.realpath(file_path)
            lib = _os.path.realpath(_md.get_download_dir())
            if not (real.startswith(lib + _os.sep) and _os.path.isfile(real)):
                return []
            text = _read_embedded_lyrics(real)
        except Exception:
            text = ""
        import re as _re
        if not text:
            return []
        is_lrc = bool(_re.search(r"\[\d{1,2}:\d{1,2}(?:[.:]\d{1,3})?\]", text))
        return [_mk_cand("" if is_lrc else text, text if is_lrc else "", artist_c, title_c,
                         album_c, dur, "embedded")]

    def _jobs():
        yield lrclib_get
        yield ovh
        yield embedded
        seen_q = set()
        for q in (f"{artist_c} {title_c}".strip(), f"{title_c} {album_c}".strip(),
                  f"{artist_c} {album_c} {title_c}".strip(), title_c):
            q = q.strip()
            if q and q not in seen_q:
                seen_q.add(q)
                yield lambda q=q: lrclib_search(q)

    try:
        with _cf.ThreadPoolExecutor(max_workers=6) as ex:
            futs = [ex.submit(fn) for fn in _jobs()]
            for fut in _cf.as_completed(futs, timeout=timeout):
                try:
                    raw.extend(fut.result() or [])
                except Exception:
                    continue
    except Exception:
        pass

    # Gabung kandidat "sama" (artis+judul+album) → satu baris, isi field yang bolong.
    merged: dict = {}
    order = []
    for c in raw:
        if not (c.get("plain") or c.get("synced")):
            continue
        mkey = (_norm_lyrics_text(c.get("artist")), _norm_lyrics_text(c.get("title")),
                _norm_lyrics_text(c.get("album")))
        cur = merged.get(mkey)
        if cur is None:
            merged[mkey] = dict(c)
            order.append(mkey)
            continue
        if c.get("synced") and not cur.get("synced"):
            cur["synced"] = c["synced"]
            cur["source"] = c.get("source") or cur.get("source")
        if c.get("plain") and not cur.get("plain"):
            cur["plain"] = c["plain"]
        if c.get("album") and not cur.get("album"):
            cur["album"] = c["album"]
        if c.get("duration") and not cur.get("duration"):
            cur["duration"] = c["duration"]

    out = []
    for mkey in order:
        c = merged[mkey]
        if not (c.get("plain") or c.get("synced")):
            continue
        score = _score_lyrics_candidate(c, artist_c, title_c, dur, album_c)
        badges = []
        if c.get("synced"):
            badges.append("SYNCED")
        if c.get("plain"):
            badges.append("PLAIN")
        if c.get("source") == "embedded":
            badges.append("EMBEDDED")
        delta = None
        try:
            if dur and c.get("duration") is not None:
                delta = int(round(float(c["duration"]) - float(dur)))
        except (TypeError, ValueError):
            delta = None
        out.append({
            "artist": c.get("artist") or artist_c, "title": c.get("title") or title_c,
            "album": c.get("album") or "", "duration": c.get("duration"),
            "durationDelta": delta, "synced": bool(c.get("synced")), "plain": bool(c.get("plain")),
            "source": c.get("source") or "lrclib", "score": round(float(score), 2),
            "badges": badges, "versionMarkers": _version_markers(f"{c.get('title')} {c.get('album')}"),
            "preview": _lyrics_preview(c.get("synced") or c.get("plain") or ""),
            "syncedText": c.get("synced") or "", "plainText": c.get("plain") or "",
        })
    out.sort(key=lambda x: (x["score"], 1 if x["synced"] else 0), reverse=True)
    return out[: int(limit)]


def get_lyrics(artist: str, title: str, file_path: str = "", duration=None,
               album: str = "", prefer=None, refresh: bool = False) -> dict:
    """Cari lirik online CEPAT, LUAS, dan AKURAT (P58 + A02).

    Kandidat dikumpulkan dari LRCLIB get/search + lyrics.ovh (+ lirik tertanam file),
    diberi skor (judul, artis, ALBUM, durasi bertingkat, penalti versi live/remix,
    bonus synced), lalu diambil yang terbaik. ``prefer`` = indeks kandidat pilihan
    user (dari /api/music/lyrics-candidates). Trek tanpa hasil di-cache negatif 10 menit
    supaya tidak memicu request berulang. Return {plain, synced, source} (+ cachedEmpty).
    """
    import os

    neg = _neg_key(artist, title, duration, album)
    if not refresh and _neg_get(neg):
        return {"plain": "", "synced": "", "source": "", "cachedEmpty": True}

    plain = ""
    synced = ""
    source = ""
    cands = []
    try:
        cands = collect_lyrics_candidates(artist, title, album=album, duration=duration,
                                         file_path=file_path, limit=12)
    except Exception:
        cands = []
    if cands:
        chosen = None
        try:
            idx = int(prefer) if prefer is not None and str(prefer) != "" else None
        except (TypeError, ValueError):
            idx = None
        if idx is not None and 0 <= idx < len(cands):
            chosen = cands[idx]
        else:
            # pilih kandidat terbaik yang punya synced (lirik live per detik) — fallback terbaik.
            chosen = next((c for c in cands if c.get("synced")), cands[0])
        if chosen:
            synced = chosen.get("syncedText") or ""
            plain = chosen.get("plainText") or ""
            source = chosen.get("source") or "lrclib"
            # Bila kandidat terbaik hanya synced, ambil plain dari kandidat dengan
            # judul+artis SAMA (jangan campur versi berbeda).
            if not plain:
                for c in cands:
                    if c.get("plainText") and c.get("title") == chosen.get("title"):
                        plain = c["plainText"]
                        break

    # Fallback: lirik tertanam di file (parity _embedded_lyrics), hanya path valid.
    if not synced and not plain and file_path:
        embedded = ""
        try:
            import music_downloader as _md
            lib_dir = os.path.realpath(_md.get_download_dir())
            real = os.path.realpath(file_path)
            if real.startswith(lib_dir + os.sep) and os.path.isfile(real):
                embedded = _read_embedded_lyrics(real)
        except Exception:
            embedded = ""
        if embedded:
            plain = embedded
            source = "embedded"

    if synced:
        source = "lrclib" if source in ("", "embedded") else source
    elif plain:
        source = source or "lrclib"
    if not synced and not plain:
        _neg_put(neg)
    return {"plain": plain, "synced": synced, "source": source}


def _parse_citations(raw) -> list:
    """Ubah kolom `citations` (JSON TEXT) menjadi list aman untuk UI."""
    if not raw:
        return []
    if isinstance(raw, list):
        return raw
    try:
        data = json.loads(raw)
        return data if isinstance(data, list) else []
    except Exception:
        return []


def _normalize_ids(values) -> list:
    """Bersihkan daftar id dari UI (string / int / dipisah koma)."""
    out = []
    if values in (None, "", []):
        return out
    if isinstance(values, str):
        values = [v for v in values.split(",")]
    if not isinstance(values, (list, tuple, set)):
        values = [values]
    for v in values:
        token = str(v).strip()
        if token and token not in out:
            out.append(token)
    return out


def _selected_sources(notebook_id: int, uid: int, source_ids=None) -> list:
    """Sumber yang DIPILIH untuk grounding (A08).

    `source_ids` kosong → semua sumber notebook (perilaku lama). Bila diisi, hanya
    sumber dengan id tersebut yang masuk konteks — inilah "checkbox sumber" NotebookLM.
    """
    try:
        rows = db.get_learning_source_rows(notebook_id, uid)
    except Exception:
        rows = []
    out = []
    for row in rows or []:
        content = (row.get("content") or "").strip()
        fp = row.get("file_path") or ""
        if not content and not (fp and db.is_managed_source_file(fp)):
            continue
        out.append({
            "id": str(row.get("id")),
            "title": row.get("title") or "Sumber",
            "type": row.get("type") or "text",
            "content": content,
            "file_path": fp,
            "mime_type": row.get("mime_type") or "",
            "file_size": row.get("file_size") or 0,
        })
    wanted = _normalize_ids(source_ids)
    if wanted:
        picked = [x for x in out if str(x["id"]) in wanted]
        if picked:
            return picked
    return out


def _vision_files_for_sources(sources, max_files=3, max_bytes=20 * 1024 * 1024):
    """C02-revisi: berkas asli (pdf/gambar) untuk dilampirkan ke Gemini.

    Hanya path kelolaan app + ada + <=max_bytes; dibaca sebagai bytes di sini
    (learning_helper tidak menyentuh disk). Audio tidak dilampirkan (transkrip
    impor sudah menjadi teks grounding); Office tidak didukung Gemini langsung.
    """
    _MIME = {".pdf": "application/pdf", ".png": "image/png", ".jpg": "image/jpeg",
             ".jpeg": "image/jpeg", ".webp": "image/webp", ".gif": "image/gif"}
    out = []
    for s in sources or []:
        if len(out) >= max_files:
            break
        fp = (s or {}).get("file_path") or ""
        if not fp or not db.is_managed_source_file(fp):
            continue
        ext = os.path.splitext(fp)[1].lower()
        if ext not in _MIME:
            continue
        try:
            if os.path.getsize(fp) > max_bytes or os.path.getsize(fp) == 0:
                continue
            with open(fp, "rb") as f:
                data = f.read()
        except Exception:
            continue
        if not data:
            continue
        mime = (s.get("mime_type") or "").split(";")[0].strip() or _MIME[ext]
        out.append({"data": data, "mime": mime,
                    "name": s.get("title") or os.path.basename(fp)})
    return out


def _chat_ai(uid: int, notebook_id: int, question: str, source_ids=None) -> dict:
    """Jawab pertanyaan user dari sumber notebook — kini dengan SITASI (A08).

    Return `{"answer": str, "citations": [...], "grounded": bool, "sourcesUsed": n}`.
    Pemanggil lama yang mengharapkan string dapat memakai `["answer"]`; respons HTTP
    tetap membawa `answer` sehingga kontrak lama tidak putus.
    """
    key = _gemini_key(uid)
    sources = _selected_sources(notebook_id, uid, source_ids)
    history = []
    try:
        for c in db.get_learning_chats(notebook_id) or []:
            history.append({"role": c.get("role") or "user", "content": c.get("content") or ""})
    except Exception:
        pass

    result = {"answer": "", "citations": [], "grounded": False, "sourcesUsed": len(sources)}

    if key and sources:
        try:
            import learning_helper as lh
            files = _vision_files_for_sources(sources)
            payload = lh.chat_with_citations(question, sources, history, key, files=files)
            answer = (payload or {}).get("answer") or ""
            citations = (payload or {}).get("citations") or []
            if answer:
                result = {
                    "answer": answer,
                    "citations": citations,
                    "grounded": bool(citations),
                    "sourcesUsed": len(sources),
                }
        except Exception as e:
            result["answer"] = str(e)

    # Jalur lama (chunks RAG tanpa baris sumber) tetap dipertahankan sebagai fallback.
    if not result["answer"]:
        try:
            rows = db.get_learning_chunks(notebook_id, uid) or []
            chunks = [r.get("chunk_text") or r.get("content") or "" for r in rows]
            chunks = [c for c in chunks if c]
            if chunks and key:
                import learning_helper as lh
                ctx = chunks[:8]
                if hasattr(lh, "find_relevant_chunks"):
                    try:
                        ctx = lh.find_relevant_chunks(question, chunks) or ctx
                    except Exception:
                        pass
                result["answer"] = lh.chat_with_sources(question, ctx, history, key)
        except Exception:
            pass

    if not result["answer"]:
        if not sources:
            result["answer"] = "Tambahkan sumber ke notebook ini dulu, baru tanya AI."
        elif not key:
            result["answer"] = "Setel Gemini API key di pengaturan (tersimpan di Python, bukan di web)."
        else:
            result["answer"] = "Tidak ada jawaban."

    try:
        db.add_learning_chat(notebook_id, "assistant", result["answer"], result["citations"] or None)
    except Exception:
        pass
    return result


def podcast_audio_dir() -> str:
    """Folder audio podcast — SAMA dengan jalur desktop (`learning_audio/`)."""
    try:
        base = os.path.dirname(os.path.abspath(db.DB_PATH))
    except Exception:
        base = os.getcwd()
    path = os.path.join(base, "learning_audio")
    os.makedirs(path, exist_ok=True)
    return path


def podcast_audio_path(generation_id) -> str:
    return os.path.join(podcast_audio_dir(), f"podcast_{int(generation_id)}.mp3")


def podcast_audio_info(notebook_id, generation_id) -> dict | None:
    """Metadata audio tersimpan (untuk daftar artefak & pemutar web)."""
    try:
        row = db.get_learning_audio(notebook_id, generation_id)
    except Exception:
        row = None
    if not row:
        return None
    path = row.get("path") or ""
    if not path or not os.path.exists(path):
        return None
    return {
        "url": f"/api/learning/podcast/audio?notebook={int(notebook_id)}&id={int(generation_id)}",
        "durationSec": float(row.get("duration_sec") or 0),
        "sizeBytes": int(row.get("size_bytes") or 0),
        "language": row.get("language") or "id",
        "engine": row.get("engine") or "",
        "voiceA": row.get("voice_a") or "",
        "voiceB": row.get("voice_b") or "",
        "turns": row.get("turns") or [],
        "createdAt": row.get("created_at") or "",
    }


def _latest_audio_generation(notebook_id: int):
    """Generasi `audio_overview` terbaru notebook (sumber transkrip podcast)."""
    try:
        gens = db.get_learning_generations(notebook_id) or []
    except Exception:
        gens = []
    picks = [g for g in gens if (g.get("type") or "").lower() in ("audio_overview", "podcast")]
    return picks[-1] if picks else None


def _bad(msg: str) -> dict:
    """Respons error standar untuk studio_api.handle_post.

    Parity pola error yang sudah ada di handler ini (mis. ``{"result": {"ok": False,
    "msg": "no_friend"}}``). api_server membungkus hasil handle_post melalui
    ``_ok_payload(uid, studio.get("result"))``, jadi hasil harus dibungkus ``result``.
    """
    return {"result": {"ok": False, "msg": msg}}


def _cloud_mod():
    try:
        import cloud_api
        return cloud_api
    except Exception:
        return None



def _gemini_key(uid: int) -> str:
    try:
        return db.get_gemini_api_key(uid) or os.environ.get("GEMINI_API_KEY") or ""
    except Exception:
        return os.environ.get("GEMINI_API_KEY") or ""


def _parse_data_table(raw: str) -> dict:
    """C05: normalisasi JSON Data Table → {title, columns, rows} (semua sel string)."""
    data = json.loads(_strip_json_fence(raw))
    if not isinstance(data, dict):
        raise ValueError("bad_shape")
    cols = [str(c) for c in (data.get("columns") or [])][:8]
    if not cols:
        raise ValueError("no_columns")
    rows = []
    for r in (data.get("rows") or [])[:30]:
        cells = [str(c) for c in (r if isinstance(r, list) else [r])]
        rows.append((cells + [""] * len(cols))[:len(cols)])
    return {"title": str(data.get("title") or ""), "columns": cols, "rows": rows}


def _parse_infographic(raw: str) -> dict:
    """C05: normalisasi JSON Infografik → {title, subtitle, stats, points}."""
    data = json.loads(_strip_json_fence(raw))
    if not isinstance(data, dict) or not isinstance(data.get("points"), list):
        raise ValueError("bad_shape")
    stats = [{"value": str((s or {}).get("value") or "")[:40],
              "label": str((s or {}).get("label") or "")[:120]}
             for s in (data.get("stats") or [])[:6] if isinstance(s, dict)]
    points = [{"heading": str((p or {}).get("heading") or "")[:120],
               "text": str((p or {}).get("text") or "")[:2000]}
              for p in data["points"][:15] if isinstance(p, dict)]
    if not points:
        raise ValueError("no_points")
    return {"title": str(data.get("title") or ""),
            "subtitle": str(data.get("subtitle") or ""),
            "stats": stats, "points": points}


def _parse_slide_deck(raw: str) -> dict:
    """C05: normalisasi JSON Slide Deck → {title, slides[{title, bullets}]}."""
    data = json.loads(_strip_json_fence(raw))
    if not isinstance(data, dict) or not isinstance(data.get("slides"), list):
        raise ValueError("bad_shape")
    slides = [{"title": str((s or {}).get("title") or "")[:200],
               "bullets": [str(b)[:500] for b in ((s or {}).get("bullets") or [])][:8]}
              for s in data["slides"][:25] if isinstance(s, dict)]
    if not slides:
        raise ValueError("no_slides")
    return {"title": str(data.get("title") or ""), "slides": slides}


def _strip_json_fence(text: str) -> str:
    text = (text or "").strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[-1]
        if text.endswith("```"):
            text = text.rsplit("```", 1)[0]
    return text.strip()


# ══════════════════════════════════════════════════════════════════════════════
#  A05 — whitelist & validasi opsi konfigurasi per tipe Studio
# ══════════════════════════════════════════════════════════════════════════════
#  Dialog tiap tipe (StudioGenerateDialog) mengirim opsi seperti `difficulty`,
#  `length`, `faqCount`, `absoluteDates`, dst. Semua divalidasi DI SINI (server),
#  bukan hanya di UI: nilai di luar rentang/whitelist dibuang, angka di-clamp,
#  dan teks dipangkas panjangnya. Ini mencegah penyalahgunaan payload (mis. prompt
#  injection lewat nilai pilihan yang tidak dikenal).
_STUDIO_CHOICES = {
    "difficulty": ("easy", "mixed", "hard"),
    "language": ("auto", "id", "en"),
    "length": ("short", "standard", "deep"),
    "granularity": ("day", "week", "month", "year"),
    "style": ("term", "qa", "formula", "casual", "formal", "debate",
              "brief", "detail", "bullets", "narrative"),
}
_STUDIO_INTS = {"depth": (1, 3), "branches": (3, 8), "subs": (2, 6),
                "exercises": (3, 10), "faq_count": (5, 15),
                # C05: counter 3 tipe JSON baru.
                "table_rows": (3, 15), "info_points": (3, 10),
                "slide_count": (4, 15), "slide_bullets": (2, 6)}
_STUDIO_TEXTS = {"focus": 200, "instructions": 600}
_STUDIO_SECTIONS = ("summary", "concepts", "examples", "practice", "conclusion")
# Alias dari UI (gaya per tipe) → satu kunci `style` yang dipakai learning_helper.
_STUDIO_ALIASES = {
    "cardStyle": "style", "hostStyle": "style", "answerStyle": "style",
    "summaryStyle": "style", "card_style": "style", "host_style": "style",
    "answer_style": "style", "summary_style": "style",
    "faqCount": "faq_count", "faq_count": "faq_count", "faqQuestions": "faq_count",
    "absoluteDates": "absolute_dates", "absolute_dates": "absolute_dates",
    # C05: alias camelCase counter baru.
    "tableRows": "table_rows", "infoPoints": "info_points",
    "slideCount": "slide_count", "slideBullets": "slide_bullets",
    "focusTopic": "focus", "customInstructions": "instructions",
    "extraInstructions": "instructions",
}


def _studio_opts(body: dict) -> dict:
    """Ambil opsi A05 yang valid dari body request (sisanya diabaikan)."""
    src = {}
    for raw_key, value in (body or {}).items():
        if value in (None, ""):
            continue
        src[_STUDIO_ALIASES.get(raw_key, raw_key)] = value
    out = {}
    for key, allowed in _STUDIO_CHOICES.items():
        val = src.get(key)
        if isinstance(val, str) and val.strip().lower() in allowed:
            val = val.strip().lower()
            if not (key == "language" and val == "auto"):
                out[key] = val
    for key, (lo, hi) in _STUDIO_INTS.items():
        val = src.get(key)
        if val is None or val == "":
            continue
        try:
            out[key] = max(lo, min(hi, int(val)))
        except (TypeError, ValueError):
            continue
    for key, limit in _STUDIO_TEXTS.items():
        val = src.get(key)
        if isinstance(val, str) and val.strip():
            # Buang karakter kontrol (bisa merusak prompt/log).
            clean = "".join(ch for ch in val if ch.isprintable() or ch in "\n\t").strip()
            if clean:
                out[key] = clean[:limit]
    if "sections" in src:
        val = src["sections"]
        if isinstance(val, str):
            val = [x.strip() for x in val.split(",")]
        if isinstance(val, (list, tuple)):
            picked = [x for x in _STUDIO_SECTIONS if x in [str(v).strip().lower() for v in val]]
            if picked:
                out["sections"] = picked
    if "absolute_dates" in src:
        val = src["absolute_dates"]
        if isinstance(val, bool):
            out["absolute_dates"] = val
        elif isinstance(val, (int, float)):
            out["absolute_dates"] = bool(val)
        elif isinstance(val, str) and val.strip().lower() in ("true", "false", "1", "0", "yes", "no"):
            out["absolute_dates"] = val.strip().lower() in ("true", "1", "yes")
    return out


def _studio_generate(uid: int, body: dict, studio_type: str):
    key = _gemini_key(uid)
    content = body.get("content") or ""
    topic = (body.get("topic") or "").strip()
    nid = body.get("notebookId")
    chunks = [content[:8000]] if content else []
    if nid and not chunks:
        try:
            # A08: hanya sumber terpilih (`sourceIds`) yang dijadikan konteks.
            for src in _selected_sources(int(nid), uid, body.get("sourceIds") or body.get("source_ids")):
                chunks.append((src.get("content") or "")[:4000])
        except Exception:
            pass
        if not topic:
            try:
                nb = db.get_learning_notebook(int(nid), uid) or {}
                topic = nb.get("title") or ""
            except Exception:
                pass
    if not key:
        return {"result": {"ok": False, "msg": "no_gemini_key"}, "skip_snap": True}
    try:
        import learning_helper as lh
        kwargs = {}
        if studio_type in ("quiz", "flashcards"):
            # P56: jumlah soal/kartu dari counter Studio. Terima beberapa nama key
            # (frontend memakai `count`; `questionCount`/`numQuestions` nama lama) —
            # dulu hanya quiz + key `questionCount` sehingga counter 30 soal
            # diabaikan dan selalu jatuh ke default 10.
            for _ck in ("count", "questionCount", "numQuestions"):
                _cv = body.get(_ck)
                if _cv not in (None, ""):
                    try:
                        kwargs["count"] = int(_cv)
                        break
                    except (TypeError, ValueError):
                        pass
            # A04: DUA counter terpisah untuk quiz — Pilihan Ganda & Essay
            # (default 10 + 5, total gabungan maks 30; guard juga ada di learning_helper).
            for _mk in ("mcCount", "mc_count", "mcQuestions"):
                _mv = body.get(_mk)
                if _mv not in (None, ""):
                    try:
                        kwargs["mc_count"] = int(_mv)
                        break
                    except (TypeError, ValueError):
                        pass
            for _ek in ("essayCount", "essay_count", "essayQuestions"):
                _ev = body.get(_ek)
                if _ev not in (None, ""):
                    try:
                        kwargs["essay_count"] = int(_ev)
                        break
                    except (TypeError, ValueError):
                        pass
        # A05: opsi konfigurasi per tipe (difficulty/language/style/length/depth/branches/
        # subs/sections/exercises/faqCount/granularity/absoluteDates/focus/instructions).
        # Divalidasi & di-clamp di `_studio_opts` → tidak ada nilai liar yang masuk prompt.
        kwargs.update(_studio_opts(body))
        files = []
        try:
            if nid:
                files = _vision_files_for_sources(_selected_sources(int(nid), uid))
        except Exception:
            files = []
        raw = lh.generate_studio_content(studio_type, topic or "Materi", chunks, key,
                                         files=files, **kwargs)
    except Exception as e:
        return {"result": {"ok": False, "msg": str(e)}, "skip_snap": True}
    text = raw if isinstance(raw, str) else json.dumps(raw)
    persist_type = studio_type
    payload = {"ok": True, "type": studio_type, "raw": text}
    if studio_type == "quiz":
        quiz = []
        try:
            data = json.loads(_strip_json_fence(text))
            qs = data.get("questions") or data.get("quiz") or []
            for q in qs:
                quiz.append({
                    "question": q.get("q") or q.get("question") or "",
                    "options": q.get("options") or [],
                    "correctAnswerIndex": int(q.get("answer") or q.get("correctAnswerIndex") or 0),
                    "explanation": q.get("explain") or q.get("explanation") or "",
                    "type": q.get("type") or "mc",
                    # P56: jawaban contoh untuk soal essay (dulu dibuang).
                    "modelAnswer": q.get("model_answer") or q.get("modelAnswer") or "",
                })
        except Exception as e:
            return {"result": {"ok": False, "msg": str(e), "quiz": []}, "skip_snap": True}
        payload["quiz"] = quiz
    elif studio_type == "flashcards":
        cards = []
        try:
            data = json.loads(_strip_json_fence(text))
            arr = data if isinstance(data, list) else data.get("cards") or data.get("flashcards") or []
            for x in arr:
                cards.append({
                    "question": x.get("front") or x.get("question") or "",
                    "answer": x.get("back") or x.get("answer") or "",
                })
        except Exception:
            cards = []
        payload["flashcards"] = cards
    elif studio_type == "audio_overview":
        lines = []
        for line in text.splitlines():
            if "|" in line:
                sp, txt = line.split("|", 1)
                sp = sp.strip().replace("HOST_A", "Alex").replace("HOST_B", "Sam")
                lines.append({"speaker": sp or "Alex", "line": txt.strip()})
        payload["podcast"] = lines
        persist_type = "audio_overview"
    elif studio_type == "mind_map":
        try:
            payload["mindMap"] = json.loads(_strip_json_fence(text))
        except Exception:
            payload["mindMap"] = {"raw": text}
    elif studio_type == "study_guide":
        payload["studyGuide"] = text
    elif studio_type == "faq":
        payload["faq"] = text
    elif studio_type == "timeline":
        payload["timeline"] = text
    elif studio_type == "summary":
        payload["summary"] = text
    elif studio_type == "briefing_doc":
        payload["briefingDoc"] = text
    elif studio_type == "data_table":
        try:
            payload["dataTable"] = _parse_data_table(text)
        except Exception:
            payload["dataTable"] = {"raw": text}
    elif studio_type == "infographic":
        try:
            payload["infographic"] = _parse_infographic(text)
        except Exception:
            payload["infographic"] = {"raw": text}
    elif studio_type == "slide_deck":
        try:
            payload["slideDeck"] = _parse_slide_deck(text)
        except Exception:
            payload["slideDeck"] = {"raw": text}
    if nid:
        try:
            # A04: untuk QUIZ, simpan JSON yang SUDAH dinormalkan (field `type` +
            # `modelAnswer` ikut tersimpan). Dulu `text` mentah dari model tersimpan
            # apa adanya, lalu `_nb_map` membuang `type`/`model_answer` → setelah
            # refresh, soal esai kehilangan identitasnya dan muncul sebagai PG tanpa
            # opsi (inilah inti bug "tidak bisa mengetik jawaban essay").
            persist_text = text
            if studio_type == "quiz" and payload.get("quiz"):
                persist_text = json.dumps({"title": topic or "Quiz", "questions": payload["quiz"]},
                                          ensure_ascii=False)
            saved = db.add_learning_generation(int(nid), persist_type, topic or studio_type,
                                               persist_text[:200000])
            # A08: kembalikan id generasi yang baru dibuat → UI bisa langsung
            # menawarkan "Buat voice" untuk podcast tanpa perlu fetch ulang daftar.
            if isinstance(saved, dict) and saved.get("generation_id"):
                payload["generationId"] = str(saved["generation_id"])
        except Exception:
            pass
    return {"result": payload, "skip_snap": True}

def _add_source_from_upload(nid: int, uid: int, path: str, orig_name: str = "",
                             mime: str = "") -> dict:
    """C02: impor berkas sumber Learning — berkas asli DISIMPAN (tidak dihapus),
    teks terekstrak terstruktur, metadata berkas ikut dicatat di DB."""
    if not path or not os.path.isfile(path):
        return {"ok": False, "msg": "learning_not_found"}
    try:
        import learning_helper as lh
        res = lh.extract_source_file(path, _gemini_key(uid))
    except Exception as e:
        return {"ok": False, "msg": f"[Gagal ekstrak: {e}]"}
    if not res.get("ok"):
        return {"ok": False, "msg": res.get("msg") or "learning_source_empty_file"}
    content = str(res.get("text") or "").strip()
    if not content:
        return {"ok": False, "msg": "learning_source_empty_file"}
    title = (orig_name or "").strip() or os.path.basename(path)
    try:
        size = os.path.getsize(path)
    except Exception:
        size = 0
    if not mime:
        import mimetypes as _mt
        mime = _mt.guess_type(path)[0] or "application/octet-stream"
    # Hanya path kelolaan app yang dicatat (aman dihapus saat sumber dihapus).
    managed = path if db.is_managed_source_file(path) else ""
    out = db.add_learning_source(
        nid, uid, res.get("kind") or "txt", title, managed or path,
        content[:80000], file_name=os.path.basename(title) or os.path.basename(path),
        mime_type=mime, file_size=size, file_path=managed,
    )
    if isinstance(out, dict):
        out["warnings"] = res.get("warnings") or []
        out["kind"] = res.get("kind") or "txt"
    return out


def _add_source_from_url(nid: int, uid: int, url: str, title: str = "") -> dict:
    """C03: impor sumber URL — deteksi YouTube vs website, fetch server-side."""
    u = (url or "").strip()
    if not u.lower().startswith(("http://", "https://")) or len(u) < 12 or " " in u:
        return {"ok": False, "msg": "learning_url_invalid"}
    try:
        import learning_helper as lh
        if lh.is_youtube_url(u):
            kind = "youtube"
            res = lh.fetch_youtube(u)
        else:
            kind = "website"
            res = lh.fetch_website(u)
    except Exception:
        return {"ok": False, "msg": "learning_source_fetch_failed"}
    text = str((res or {}).get("text") or "").strip()
    if not (res or {}).get("ok") or len(text) < 20:
        return {"ok": False, "msg": "learning_source_fetch_failed"}
    name = (title or "").strip() or (res.get("title") or "").strip() or u[:60]
    return db.add_learning_source(nid, uid, kind, name, u, text[:80000])


def _op_report_camel(rep: dict) -> dict:
    # C06: laporan checkpoint/VACUUM snake → camel (error ikut terlihat).
    rep = rep or {}
    return {"ok": bool(rep.get("ok")),
            "beforeBytes": int(rep.get("before_bytes") or 0),
            "afterBytes": int(rep.get("after_bytes") or 0),
            "freedBytes": int(rep.get("freed_bytes") or 0),
            "error": rep.get("error") or ""}


def _purge_report_camel(rep: dict) -> dict:
    rep = rep or {}
    out = {"beforeBytes": int(rep.get("before_bytes") or 0),
           "afterBytes": int(rep.get("after_bytes") or 0),
           "freedBytes": int(rep.get("freed_bytes") or 0),
           "deleted": rep.get("deleted") or {},
           "totalDeleted": int(rep.get("total_deleted") or 0),
           "backupPath": rep.get("backup_path") or ""}
    if rep.get("checkpoint") is not None:
        out["checkpoint"] = _op_report_camel(rep.get("checkpoint"))
    if rep.get("vacuum") is not None:
        out["vacuum"] = _op_report_camel(rep.get("vacuum"))
    return out


def handle_post(path: str, uid: int, body: dict, parts: list):
    if path == "/api/learning/notebooks":
        # A15: ikon & deskripsi dari dialog "Notebook Baru" ikut disimpan — sebelumnya
        # hanya `title` yang diteruskan sehingga ikon pilihan user hilang dan rail kiri
        # Learning selalu menampilkan 📚.
        title = (body.get("title") or "Notebook").strip()
        icon = body.get("icon") or "📚"
        description = body.get("description") or body.get("desc") or ""
        return {"result": db.create_learning_notebook(uid, title, icon, description)}

    if path == "/api/learning/source-content":
        # Parity LearningPage._view_source: tampilkan isi penuh source (lookup
        # lewat notebook pemilik; tabel sources terikat notebook_id).
        try:
            sid = int(body.get("sourceId") or body.get("id") or 0)
            nid = int(body.get("notebookId") or 0)
        except (TypeError, ValueError):
            sid = nid = 0
        if not sid or not nid:
            return {"result": {"ok": False, "msg": "learning_not_found"}, "skip_snap": True}
        src_row = None
        try:
            for s in db.get_learning_sources(nid, uid) or []:
                if int(s.get("id") or 0) == sid:
                    src_row = s
                    break
        except Exception:
            src_row = None
        if not src_row:
            return {"result": {"ok": False, "msg": "learning_not_found"}, "skip_snap": True}
        return {"result": {"ok": True, "source": src_row}, "skip_snap": True}


    if len(parts) >= 4 and parts[1] == "learning" and parts[2] == "notebooks":
        nid = int(parts[3])
        if len(parts) >= 5 and parts[4] == "delete":
            db.delete_learning_notebook(nid, uid)
            return {"result": {"ok": True}}
        if len(parts) >= 5 and parts[4] == "rename":
            # Parity LearningPage._rename_notebook (QInputDialog judul baru).
            # A15: `icon`/`description` boleh ikut dikirim (update parsial) — jalur ini
            # dipakai rail kiri untuk mengganti ikon notebook tanpa menyentuh judul.
            title = body.get("title")
            title = title.strip() if isinstance(title, str) else None
            if title is not None and not title:
                return {"result": {"ok": False, "msg": "learning_no_title"}}
            icon = body.get("icon")
            description = body.get("description") if "description" in body else None
            if title is None and icon is None and description is None:
                return {"result": {"ok": False, "msg": "learning_no_fields"}, "skip_snap": True}
            return {"result": db.update_learning_notebook(
                nid, uid, title=title, icon=icon, description=description)}
        if len(parts) >= 5 and parts[4] == "upload-source":
            # C02: berkas asli DISIMPAN (tidak dihapus); nama+mime asli dicatat.
            path = body.get("path") or ""
            res = _add_source_from_upload(nid, uid, path,
                                           body.get("orig_name") or "",
                                           body.get("mime") or "")
            if not res.get("ok") and path and db.is_managed_source_file(path):
                # C02-revisi: impor gagal → hapus mentahan yatim agar tak menumpuk.
                try:
                    os.remove(path)
                except Exception:
                    pass
            return {"result": res}
        if len(parts) >= 7 and parts[4] == "sources" and parts[6] == "re-extract":
            # C02: ekstrak ulang dari berkas asli (mis. setelah isi API key).
            try:
                sid = int(parts[5])
            except (TypeError, ValueError):
                sid = 0
            src = db.get_learning_source(sid, uid) if sid else None
            fp = (src.get("file_path") or "") if src else ""
            if not src or int(src.get("notebook_id") or 0) != nid:
                return {"result": {"ok": False, "msg": "learning_not_found"}}
            if not fp or not os.path.isfile(fp):
                return {"result": {"ok": False, "msg": "learning_nofile"}}
            try:
                import learning_helper as lh
                res = lh.extract_source_file(fp, _gemini_key(uid))
            except Exception as e:
                return {"result": {"ok": False, "msg": f"[Gagal ekstrak: {e}]"}}
            if not res.get("ok"):
                return {"result": {"ok": False,
                                   "msg": res.get("msg") or "learning_source_empty_file"}}
            content = str(res.get("text") or "").strip()
            if not content:
                return {"result": {"ok": False, "msg": "learning_source_empty_file"}}
            db.update_learning_source_content(sid, uid, content[:80000])
            return {"result": {"ok": True, "source_id": sid,
                               "warnings": res.get("warnings") or [],
                               "kind": res.get("kind") or "txt"}}
        if len(parts) >= 5 and parts[4] == "sources":
            if len(parts) >= 7 and parts[6] == "delete":
                try:
                    db.delete_learning_source(int(parts[5]), uid)
                except Exception:
                    pass
                return {"result": {"ok": True}}
            url = (body.get("url") or "").strip()
            if url:
                # C03: sumber URL — server yang fetch (website/YouTube otomatis).
                return {"result": _add_source_from_url(nid, uid, url, body.get("title") or "")}
            result = db.add_learning_source(
                nid, uid,
                body.get("type") or "text",
                body.get("title") or "Source",
                body.get("path") or "",
                body.get("content") or "",
            )
            return {"result": result}
        if len(parts) >= 6 and parts[4] == "chat" and parts[5] == "clear":
            # P48: bersihkan history chat notebook (parity tombol "Bersihkan chat"
            # — dulu hanya membersihkan state React sehingga history kembali
            # setelah reload/restart). Wajib dicek SEBELUM route chat generik.
            db.clear_learning_chats(nid)
            return {"result": {"ok": True}}
        if len(parts) >= 5 and parts[4] == "chat":
            text = (body.get("text") or "").strip()
            if not text:
                return {"result": {"ok": False, "msg": "empty"}}
            # A08: pesan USER ikut disimpan (dulu hanya jawaban AI yang tersimpan di
            # `learning_chats`, sehingga pertanyaan hilang setelah reload/restart).
            try:
                db.add_learning_chat(nid, "user", text)
            except Exception:
                pass
            # A08: `sourceIds` = sumber yang dicentang user (grounding).
            reply = _chat_ai(uid, nid, text, body.get("sourceIds") or body.get("source_ids"))
            return {"result": {"ok": True, **reply}}
        if len(parts) >= 5 and parts[4] == "notes":
            # C04: catatan tersimpan per notebook (simpan/hapus; daftar via _nb_map).
            if len(parts) >= 7 and parts[6] == "delete":
                try:
                    db.delete_learning_note(int(parts[5]), uid)
                except Exception:
                    pass
                return {"result": {"ok": True}}
            title = (body.get("title") or "").strip()
            content = (body.get("content") or "").strip()
            if not content:
                return {"result": {"ok": False, "msg": "learning_note_empty"}}
            if not title:
                title = content[:60]
            return {"result": db.add_learning_note(nid, uid, title, content[:80000])}

    if path == "/api/music/play":
        return {"result": db.log_music_play(uid, body.get("path") or "", body.get("title") or "", body.get("artist") or "")}
    if path == "/api/music/playlists":
        fav = 1 if (body.get("isFavorite") or body.get("is_favorite")) else 0
        return {"result": db.create_playlist(uid, body.get("name") or "Playlist", fav)}
    if path == "/api/music/search":
        try:
            import music_downloader as md
            q = (body.get("query") or "").strip()
            return {"result": {"ok": True, "results": md.search_music(q), "ytAvailable": bool(md.YT_AVAILABLE)}, "skip_snap": True}
        except Exception as e:
            return {"result": {"ok": False, "msg": str(e), "results": []}, "skip_snap": True}
    if path == "/api/music/download":
        url = (body.get("url") or "").strip()
        if not url:
            return {"result": {"ok": False, "msg": "url_required"}, "skip_snap": True}
        try:
            import music_downloader as md
            jid = md.start_download_job(url)
            return {"result": {"ok": True, "jobId": jid}, "skip_snap": True}
        except Exception as e:
            return {"result": {"ok": False, "msg": str(e)}, "skip_snap": True}
    if path == "/api/learning/podcast/audio":
        # A08: buat audio DUA HOST yang nyata (MP3) dari transkrip podcast sebuah
        # generasi, lengkap dengan offset tiap giliran agar pemutar web interaktif:
        # klik giliran = lompat ke detiknya, giliran aktif disorot otomatis.
        # Suara selalu mengikuti bahasa transkrip (id → id-ID-ArdiNeural/GadisNeural),
        # jadi tidak ada lagi suara Inggris yang membaca teks Indonesia.
        try:
            gid = int(body.get("generationId") or body.get("id") or 0)
            nid = int(body.get("notebookId") or 0)
        except (TypeError, ValueError):
            gid = nid = 0
        if not nid:
            return _bad("notebook_required")
        if not gid:
            latest = _latest_audio_generation(nid)
            gid = int(latest.get("id")) if latest else 0
        if not gid:
            return _bad("learning_no_podcast")
        row = None
        try:
            row = db.get_learning_generation_row(gid, nid)
        except Exception:
            row = None
        if not row:
            return _bad("learning_not_found")
        script = row.get("content") or ""
        output_path = podcast_audio_path(gid)
        force = bool(body.get("force") or body.get("regenerate"))
        cached = podcast_audio_info(nid, gid)
        if cached and not force:
            return {"result": {"ok": True, "generationId": gid, "cached": True, **cached}, "skip_snap": True}
        try:
            import learning_helper as lh
        except Exception as e:
            return _bad(f"learning_helper_error: {e}")
        key = _gemini_key(uid)
        try:
            meta = lh.build_podcast_audio(
                script, output_path, language=body.get("language") or "auto",
                api_key=key,
            )
        except Exception as e:
            return {"result": {"ok": False, "msg": str(e)}, "skip_snap": True}
        try:
            db.save_learning_audio(
                nid, gid, meta["path"], language=meta.get("language") or "id",
                engine=meta.get("engine") or "", voice_a=meta.get("voiceA") or "",
                voice_b=meta.get("voiceB") or "", duration_sec=meta.get("durationSec") or 0,
                size_bytes=meta.get("sizeBytes") or 0, turns=meta.get("turns") or [],
            )
        except Exception:
            pass
        info = podcast_audio_info(nid, gid) or {}
        return {
            "result": {
                "ok": True, "generationId": gid, "cached": False,
                "languageLabel": meta.get("languageLabel") or "",
                **info,
            },
            "skip_snap": True,
        }

    if path == "/api/learning/generations/rename":
        # A06: ganti nama artefak Studio dari daftar artefak (list ke bawah).
        try:
            gid = int(body.get("generationId") or 0)
            nid = int(body.get("notebookId") or 0)
        except (TypeError, ValueError):
            gid = nid = 0
        if not gid or not nid:
            return {"result": {"ok": False, "msg": "learning_not_found"}, "skip_snap": True}
        res = db.rename_learning_generation(gid, nid, body.get("title"))
        return {"result": res, "skip_snap": True}
    if path == "/api/learning/generations/duplicate":
        # A06: duplikat artefak (isi sama, judul + " (copy)").
        try:
            gid = int(body.get("generationId") or 0)
            nid = int(body.get("notebookId") or 0)
        except (TypeError, ValueError):
            gid = nid = 0
        if not gid or not nid:
            return {"result": {"ok": False, "msg": "learning_not_found"}, "skip_snap": True}
        res = db.duplicate_learning_generation(gid, nid)
        return {"result": res, "skip_snap": True}
    if path == "/api/learning/generations/delete":
        # Parity LearningPage._delete_generation (hapus entri history Studio).
        try:
            gid = int(body.get("generationId") or 0)
            nid = int(body.get("notebookId") or 0)
        except (TypeError, ValueError):
            gid = nid = 0
        if not gid or not nid:
            return {"result": {"ok": False, "msg": "learning_not_found"}}
        return {"result": db.delete_learning_generation(gid, nid)}
    if path == "/api/learning/generate":
        # Parity LearningPage._generate_studio / _start_learning_job via REST ringkas.
        gtype = (body.get("type") or body.get("gtype") or "").strip()
        mapping = {
            "study-guide": "study_guide", "mindmap": "mind_map", "podcast": "audio_overview",
            "audio-overview": "audio_overview", "quiz": "quiz", "flashcards": "flashcards",
            "faq": "faq", "timeline": "timeline", "summary": "summary",
        }
        st = mapping.get(gtype, gtype)
        if st not in ("quiz", "flashcards", "mind_map", "audio_overview", "study_guide", "faq", "timeline", "summary"):
            return {"result": {"ok": False, "msg": "learning_type_invalid"}, "skip_snap": True}
        body = {**body, "notebookId": body.get("notebookId")}
        return _studio_generate(uid, body, st)
    if path == "/api/ai/quiz":
        return _studio_generate(uid, body, "quiz")
    if path == "/api/ai/flashcards":
        return _studio_generate(uid, body, "flashcards")
    if path in ("/api/ai/podcast", "/api/ai/audio-overview"):
        return _studio_generate(uid, body, "audio_overview")
    if path in ("/api/ai/mindmap", "/api/ai/mind-map"):
        return _studio_generate(uid, body, "mind_map")
    if path in ("/api/ai/study-guide", "/api/ai/study_guide"):
        return _studio_generate(uid, body, "study_guide")
    if path == "/api/ai/faq":
        return _studio_generate(uid, body, "faq")
    if path == "/api/ai/timeline":
        return _studio_generate(uid, body, "timeline")
    if path == "/api/ai/summary":
        return _studio_generate(uid, body, "summary")
    # C05: 4 generator baru.
    if path in ("/api/ai/briefing-doc", "/api/ai/briefing_doc"):
        return _studio_generate(uid, body, "briefing_doc")
    if path in ("/api/ai/data-table", "/api/ai/data_table"):
        return _studio_generate(uid, body, "data_table")
    if path == "/api/ai/infographic":
        return _studio_generate(uid, body, "infographic")
    if path in ("/api/ai/slide-deck", "/api/ai/slide_deck"):
        return _studio_generate(uid, body, "slide_deck")
    if path == "/api/ai/chat":
        nid = int(body.get("notebookId") or 0)
        text = (body.get("text") or body.get("question") or "").strip()
        if not nid or not text:
            return {"result": {"ok": False, "msg": "notebook_and_text"}, "skip_snap": True}
        reply = _chat_ai(uid, nid, text, body.get("sourceIds") or body.get("source_ids"))
        return {"result": {"ok": True, **reply}, "skip_snap": True}
    if path == "/api/ai/solve-math":
        expr = (body.get("expression") or body.get("latex") or body.get("content") or "").strip()
        try:
            import mathtools as mt
            preview = mt.latex_to_unicode(expr) if expr else ""
        except Exception:
            preview = expr
        return {"result": {"ok": True, "preview": preview, "expression": expr}, "skip_snap": True}
    if path == "/api/music/playlist-track":
        try:
            pid = int(body.get("playlistId") or 0)
        except (TypeError, ValueError):
            pid = 0
        fp = body.get("path") or body.get("filePath") or ""
        if not pid or not fp:
            return {"result": {"ok": False, "msg": "playlist_and_path"}, "skip_snap": True}
        return {"result": db.add_song_to_playlist(uid, pid, fp), "skip_snap": True}

    if path == "/api/music/playlist-rename":
        pid = int(body.get("playlistId") or 0)
        name = (body.get("name") or "").strip()
        if not pid or not name:
            return {"result": {"ok": False, "msg": "playlist_and_name"}, "skip_snap": True}
        db.rename_playlist(uid, pid, name)
        return {"result": {"ok": True}}
    if path == "/api/music/playlist-delete":
        pid = int(body.get("playlistId") or 0)
        return {"result": {"ok": db.delete_playlist(uid, pid)}, "skip_snap": True}
    if path == "/api/music/playlist-track-remove":
        pid = int(body.get("playlistId") or 0)
        idx = int(body.get("index")) if body.get("index") is not None else -1
        return {"result": db.remove_song_from_playlist(uid, pid, idx), "skip_snap": True}
    if path == "/api/music/playlist-track-move":
        fpid = int(body.get("fromPlaylistId") or 0)
        tpid = int(body.get("toPlaylistId") or 0)
        idx = int(body.get("index")) if body.get("index") is not None else -1
        return {"result": db.move_song_to_playlist(uid, fpid, tpid, idx), "skip_snap": True}
    if path == "/api/music/playlist-track-copy":
        fpid = int(body.get("fromPlaylistId") or 0)
        tpid = int(body.get("toPlaylistId") or 0)
        idx = int(body.get("index")) if body.get("index") is not None else -1
        return {"result": db.copy_song_to_playlist(uid, fpid, tpid, idx), "skip_snap": True}

    # ── P58: lirik — simpan / hapus / import manual / offset live-sync ──────
    if path == "/api/music/lyrics-save":
        key = (body.get("key") or "").strip()
        if not key:
            return {"result": {"ok": False, "msg": "key_required"}, "skip_snap": True}
        db.save_song_lyrics(uid, key, body.get("title") or "", body.get("artist") or "",
                            body.get("source") or "web", body.get("plain") or "",
                            body.get("synced") or "",
                            body.get("offsetMs") if body.get("offsetMs") is not None else None)
        return {"result": {"ok": True}, "skip_snap": True}
    if path == "/api/music/lyrics-delete":
        key = (body.get("key") or "").strip()
        return {"result": {"ok": bool(db.delete_song_lyrics(uid, key))}, "skip_snap": True}
    if path == "/api/music/lyrics-import":
        # A03: import manual .lrc/.txt — parser penuh (tag [ar:][ti:][al:][offset:],
        # multi-timestamp, jeda) + LAPORAN VALIDASI (bukan lagi toast buta).
        key = (body.get("key") or "").strip()
        content = (body.get("content") or "").strip()
        if not key or not content:
            return {"result": {"ok": False, "msg": "key_and_content"}, "skip_snap": True}
        try:
            dur = float(body.get("duration")) if body.get("duration") else None
        except (TypeError, ValueError):
            dur = None
        parsed = _parse_lrc_like(content, duration=dur)
        if not (parsed["plain"] or parsed["synced"]):
            return {"result": {"ok": False, "msg": "empty_content",
                               "report": _lyrics_report_payload(parsed)}, "skip_snap": True}
        # Metadata dari tag .lrc dipakai bila user tidak mengirim judul/artis.
        meta = parsed.get("metadata") or {}
        title = body.get("title") or meta.get("ti") or ""
        artist = body.get("artist") or meta.get("ar") or ""
        offset_ms = int(body.get("offsetMs") or 0) or int(parsed.get("offsetMs") or 0)
        db.save_song_lyrics(uid, key, title, artist, "user",
                            parsed["plain"], parsed["synced"], offset_ms)
        return {"result": {"ok": True,
                           "lyrics": {"plain": parsed["plain"], "synced": parsed["synced"],
                                      "source": "user", "saved": True, "offsetMs": offset_ms},
                           "report": _lyrics_report_payload(parsed)},
                "skip_snap": True}
    if path == "/api/music/lyrics-validate":
        # A03: cek file SEBELUM disimpan — UI menampilkan jumlah baris bertimestamp,
        # rentang waktu, peringatan (tag aneh, baris tanpa timestamp, timestamps ganda,
        # melewati durasi lagu), dan metadata yang terbaca.
        key = (body.get("key") or "").strip()
        content = (body.get("content") or "").strip()
        if not content:
            return {"result": {"ok": False, "msg": "empty_content"}, "skip_snap": True}
        try:
            dur = float(body.get("duration")) if body.get("duration") else None
        except (TypeError, ValueError):
            dur = None
        parsed = _parse_lrc_like(content, duration=dur)
        return {"result": {"ok": True, "report": _lyrics_report_payload(parsed),
                           "key": key}, "skip_snap": True}
    if path == "/api/music/lyrics-apply":
        # A02: simpan KANDIDAT pilihan user sebagai lirik tersimpan (source "user-pick")
        # → pilihan user tidak pernah tertimpa pencarian web berikutnya.
        key = (body.get("key") or "").strip()
        plain = body.get("plain") or ""
        synced = body.get("synced") or ""
        if not key or not (plain or synced):
            return {"result": {"ok": False, "msg": "key_and_lyrics"}, "skip_snap": True}
        db.save_song_lyrics(uid, key, body.get("title") or "", body.get("artist") or "",
                            "user-pick", plain, synced, 0)
        return {"result": {"ok": True, "lyrics": {"plain": plain, "synced": synced,
                                                  "source": "user-pick", "saved": True,
                                                  "offsetMs": 0}}, "skip_snap": True}
    if path == "/api/music/lyrics-offset":
        key = (body.get("key") or "").strip()
        if not key:
            return {"result": {"ok": False, "msg": "key_required"}, "skip_snap": True}
        try:
            off = int(body.get("offsetMs") or 0)
        except (TypeError, ValueError):
            off = 0
        db.set_song_lyrics_offset(uid, key, off)
        return {"result": {"ok": True, "offsetMs": off}, "skip_snap": True}
    if path == "/api/music/playlist-icon":
        # P59: ganti/reset icon playlist (emoji). Foto via /api/upload/file
        # target=playlist_icon (hasilkan playlists.icon='photo:<id>').
        try:
            pid = int(body.get("playlistId") or 0)
        except (TypeError, ValueError):
            pid = 0
        icon = (body.get("icon") or "").strip()
        if not pid or not icon or len(icon) > 32:
            return {"result": {"ok": False, "msg": "playlist_and_icon"}, "skip_snap": True}
        return {"result": {"ok": db.set_playlist_icon(uid, pid, icon)}, "skip_snap": True}

    if path == "/api/settings/cleanup":
        # P62: aksi pembersihan DB — 'set' (retensi/auto) | 'run' (purge sekarang).
        action = (body.get("action") or "").strip()
        if action == "set":
            rd = body.get("retentionDays")
            if rd is not None:
                try:
                    rd = int(rd)
                except (TypeError, ValueError):
                    rd = -1
                if rd not in (0, 1, 7, 30, 90):
                    return {"result": {"ok": False, "msg": "retention_invalid"}, "skip_snap": True}
                db.set_maintenance_state(uid, retention_days=rd)
            if body.get("auto") is not None:
                db.set_maintenance_state(uid, auto=bool(body.get("auto")))
            if body.get("schedule") is not None:
                sch = str(body.get("schedule")).strip().lower()
                if sch not in ("daily", "weekly", "monthly"):
                    return {"result": {"ok": False, "msg": "schedule_invalid"}, "skip_snap": True}
                db.set_maintenance_state(uid, schedule=sch)
            st = db.get_maintenance_state(uid)
            return {"result": {"ok": True, "state": {
                "retentionDays": int(st.get("retention_days") or 0),
                "auto": bool(st.get("auto")),
                "lastPurgeAt": st.get("last_purge_at") or "",
                "schedule": st.get("schedule") or "monthly"}}, "skip_snap": True}
        if action == "run":
            st = db.get_maintenance_state(uid)
            rd = int(st.get("retention_days") or 0)
            if rd <= 0:
                return {"result": {"ok": False, "msg": "cleanup_disabled"}, "skip_snap": True}
            report = db.purge_tracker_history(uid, rd, do_backup=True)
            return {"result": {"ok": True, "report": _purge_report_camel(report)}, "skip_snap": True}
        if action == "checkpoint":
            # C06: checkpoint WAL manual + laporan.
            return {"result": {"ok": True, "report": _op_report_camel(db.run_checkpoint())},
                    "skip_snap": True}
        if action == "vacuum":
            # C06: VACUUM manual (koneksi khusus) + laporan.
            return {"result": {"ok": True, "report": _op_report_camel(db.run_vacuum())},
                    "skip_snap": True}
        return {"result": {"ok": False, "msg": "action_invalid"}, "skip_snap": True}

    if path == "/api/love/profile":
        cur = db.get_relationship_profile(uid) or {}
        values = {
            "partner_name": body.get("partnerName") or cur.get("partner_name") or "",
            "partner_gender": body.get("partnerGender") or cur.get("partner_gender") or "female",
            "partner_age": body.get("partnerAge") or cur.get("partner_age") or 25,
            "relationship_type": body.get("relationshipType") or cur.get("relationship_type") or "dating",
            "start_date": body.get("startDate") or cur.get("start_date") or "",
            "my_name": body.get("myName") or cur.get("my_name") or "",
            "my_gender": body.get("myGender") or cur.get("my_gender") or "male",
            "my_age": body.get("myAge") if body.get("myAge") is not None else (cur.get("my_age") or 25),
            "my_birthdate": body.get("myBirthdate") or cur.get("my_birthdate") or "",
            "partner_birthdate": body.get("partnerBirthdate") or cur.get("partner_birthdate") or "",
        }
        ca = _cloud_mod()
        if ca and ca.is_cloud_linked(uid):
            try:
                return {"result": ca.love_profile_cloud(uid, values)}
            except Exception as e:
                pass
        result = db.save_relationship_profile(
            uid,
            values["partner_name"],
            values["partner_gender"],
            values["partner_age"],
            values["relationship_type"],
            values["start_date"],
            my_name=values["my_name"],
            my_gender=values["my_gender"],
            my_age=int(values["my_age"] or 25),
            my_birthdate=values["my_birthdate"] or None,
            partner_birthdate=values["partner_birthdate"] or None,
        )
        return {"result": result}
    if path == "/api/love/memories":
        # A10: payload lengkap (emoji, tag, favorit, tautan foto) + validasi nyata.
        ca = _cloud_mod()
        payload = {
            "title": (body.get("title") or "").strip(),
            "memory_date": body.get("date") or body.get("memoryDate") or "",
            "notes": body.get("description") or body.get("notes") or "",
            "emoji": body.get("emoji") or "",
            "tags": body.get("tags") or "",
            "is_favorite": 1 if (body.get("isFavorite") or body.get("is_favorite")) else 0,
        }
        photo_id = body.get("photoId") or body.get("photo_id") or None
        if not payload["title"]:
            return {"result": {"ok": False, "msg": "love_memory_title_required"}, "skip_snap": True}
        if not payload["memory_date"]:
            return {"result": {"ok": False, "msg": "love_memory_date_required"}, "skip_snap": True}
        if ca and ca.is_cloud_linked(uid):
            try:
                return {"result": ca.love_upsert_cloud(uid, "memory", payload)}
            except Exception:
                pass
        return {"result": db.add_relationship_memory(
            uid, payload["title"], payload["memory_date"], payload["notes"],
            emoji=payload["emoji"], tags=payload["tags"],
            is_favorite=payload["is_favorite"], photo_id=photo_id)}
    if path == "/api/love/checkin":
        from datetime import date as _date
        payload = {
            "checkin_date": body.get("date") or _date.today().isoformat(),
            "my_mood": int(body.get("myMood") or 3),
            "partner_mood": int(body.get("partnerMood") or 3),
            "connection_score": int(body.get("connectionScore") or 3),
            "note": body.get("note") or "",
        }
        ca = _cloud_mod()
        if ca and ca.is_cloud_linked(uid):
            try:
                return {"result": ca.love_upsert_cloud(uid, "checkin", payload)}
            except Exception:
                pass
        return {"result": db.save_relationship_checkin(
            uid, payload["checkin_date"], payload["my_mood"], payload["partner_mood"],
            payload["connection_score"], payload["note"])}
    if path == "/api/love/events":
        # A09: payload lengkap (ikon, lokasi, Special Day, pengulangan, pengingat).
        # Server cloud lama mengabaikan kunci yang tak dikenalnya, jadi aman dikirim.
        payload = {
            "title": body.get("title") or "Event",
            "event_date": body.get("date") or body.get("eventDate") or "",
            "category": body.get("category") or "date",
            "notes": body.get("notes") or "",
            "icon": body.get("icon") or "",
            "location": body.get("location") or "",
            "is_special": 1 if (body.get("isSpecial") or body.get("is_special")) else 0,
            "recurring": body.get("recurring") or "none",
            "remind_days_before": body.get("remindDaysBefore") or body.get("remind_days_before") or 0,
        }
        if not payload["event_date"]:
            return {"result": {"ok": False, "msg": "love_event_date_required"}}
        ca = _cloud_mod()
        if ca and ca.is_cloud_linked(uid):
            try:
                return {"result": ca.love_upsert_cloud(uid, "event", dict(payload, notes=payload["notes"]))}
            except Exception:
                pass
        return {"result": db.add_relationship_event(
            uid, payload["title"], payload["event_date"], payload["category"], payload["notes"],
            icon=payload["icon"], location=payload["location"], is_special=payload["is_special"],
            recurring=payload["recurring"], remind_days_before=payload["remind_days_before"])}
    if path == "/api/love/weekly":
        return {"result": db.save_relationship_weekly_review(
            uid,
            body.get("weekStart") or body.get("week_start") or "",
            body.get("appreciation") or "",
            body.get("wins") or "",
            body.get("support") or body.get("supportNeeded") or body.get("challenges") or "",
            body.get("intention") or body.get("nextWeek") or body.get("next_week") or "",
        )}
    if path == "/api/love/cycle":
        if body.get("settings"):
            s = body.get("settings") or body
            return {"result": db.save_menstrual_settings(
                uid,
                s.get("trackedPerson") or s.get("tracked_person") or "partner",
                s.get("lastPeriodStart") or s.get("last_period_start") or "",
                int(s.get("cycleLength") or s.get("cycle_length") or 28),
                int(s.get("periodLength") or s.get("period_length") or 5),
            )}
        return {"result": db.add_menstrual_cycle(
            uid,
            body.get("startDate") or body.get("start_date") or "",
            body.get("endDate") or body.get("end_date"),
            body.get("notes") or "",
        )}
    if path == "/api/love/prompt":
        return {"result": db.add_relationship_prompt_response(
            uid,
            body.get("promptKey") or body.get("id") or "daily",
            body.get("category") or "daily",
            body.get("prompt") or body.get("promptText") or "",
            body.get("answer") or "",
            body.get("partnerAnswer") or "",
        )}
    if path == "/api/learning/gemini-key":
        key = (body.get("apiKey") or body.get("key") or "").strip()
        db.set_gemini_api_key(uid, key)
        return {"result": {"ok": True, "hasKey": bool(key)}, "skip_snap": True}
    if path == "/api/love/photo":
        ca = _cloud_mod()
        file_path = body.get("path") or body.get("filePath") or ""
        if ca and file_path:
            try:
                return {"result": ca.love_photo_from_path(uid, file_path)}
            except Exception as e:
                return {"result": {"ok": False, "msg": str(e)}, "skip_snap": True}
        return {"result": {"ok": False, "msg": "path_required"}}
    if path == "/api/love/bucket":
        # A10: kategori, target tanggal, catatan & prioritas (dulu hanya judul).
        title = (body.get("title") or "").strip()
        if not title:
            return {"result": {"ok": False, "msg": "love_bucket_title_required"}, "skip_snap": True}
        payload = {
            "category": body.get("category") or "dream",
            "target_date": body.get("targetDate") or body.get("target_date") or None,
            "notes": body.get("notes") or "",
            "priority": int(body.get("priority") or 0),
        }
        ca = _cloud_mod()
        if ca and ca.is_cloud_linked(uid):
            try:
                return {"result": ca.love_upsert_cloud(uid, "bucket_item", dict(payload, title=title))}
            except Exception:
                pass
        return {"result": db.add_relationship_bucket_item(
            uid, title, payload["category"], payload["target_date"],
            notes=payload["notes"], priority=payload["priority"])}
    if len(parts) >= 5 and parts[1] == "love" and parts[2] == "bucket" and parts[4] == "toggle":
        bid = int(parts[3])
        items = db.get_relationship_bucket_items(uid) or []
        done = True
        for it in items:
            if int(it.get("id")) == bid:
                done = not bool(it.get("done") or it.get("is_done"))
                break
        return {"result": db.toggle_relationship_bucket_item(uid, bid, done)}

    # --- A09: Love Space → tab plans (edit acara) ---
    if len(parts) >= 5 and parts[1] == "love" and parts[2] == "events" and parts[4] == "update":
        try:
            eid = int(parts[3])
        except (TypeError, ValueError):
            return {"result": {"ok": False, "msg": "learning_not_found"}, "skip_snap": True}
        fields = {}
        for src_key, dst_key in (("title", "title"), ("date", "date"), ("eventDate", "date"),
                                 ("category", "category"), ("notes", "notes"), ("icon", "icon"),
                                 ("location", "location"), ("isSpecial", "isSpecial"),
                                 ("is_special", "isSpecial"), ("recurring", "recurring"),
                                 ("remindDaysBefore", "remindDaysBefore"),
                                 ("remind_days_before", "remindDaysBefore")):
            if src_key in body:
                fields[dst_key] = body.get(src_key)
        if "title" in fields and not str(fields["title"] or "").strip():
            return {"result": {"ok": False, "msg": "love_event_title_required"}, "skip_snap": True}
        res = db.update_relationship_event(uid, eid, **fields)
        if not res.get("ok"):
            return {"result": res, "skip_snap": True}
        ca = _cloud_mod()
        if ca and ca.is_cloud_linked(uid):
            try:
                row = res.get("event") or {}
                ca.love_upsert_cloud(uid, "event", {
                    "title": row.get("title") or "",
                    "event_date": row.get("event_date") or "",
                    "category": row.get("category") or "date",
                    "notes": row.get("notes") or "",
                    "icon": row.get("icon") or "",
                    "location": row.get("location") or "",
                    "is_special": int(row.get("is_special") or 0),
                    "recurring": row.get("recurring") or "none",
                    "remind_days_before": int(row.get("remind_days_before") or 0),
                }, record_id=row.get("cloud_id") or None)
            except Exception:
                pass
        return {"result": {"ok": True, "eventId": str(eid)}}

    # --- A10: Love Space → tab memories & bucket list ---
    # 1) edit kenangan (dulu: hanya tambah + hapus) + tautkan foto/tag/emoji
    if len(parts) >= 5 and parts[1] == "love" and parts[2] == "events" and parts[4] == "create-reminder":
        # A12: "Buat pengingat" dari hari istimewa Love Space.
        # `<id>` boleh id acara (angka) ATAU kunci profil: my_birthdate,
        # partner_birthdate, start_date (ulang tahun & hari jadi dari profil).
        # Idempoten lewat `reminders.source_ref`, dan otomatis `repeat_type='yearly'`
        # untuk acara yang berulang tahunan → mesin Reminder kini mengenal Tahunan.
        try:
            days_before = int(body.get("daysBefore") or body.get("days_before") or 0) or None
        except (TypeError, ValueError):
            days_before = None
        res = db.create_reminder_from_special_day(
            uid, parts[3], days_before=days_before,
            time_str=(body.get("time") or "09:00"))
        if not res.get("ok"):
            msg = {"not_found": "learning_not_found",
                   "no_date": "love_reminder_no_date",
                   "bad_event": "love_reminder_bad_event"}.get(res.get("code") or "", "msg_error")
            return {"result": {"ok": False, "msg": msg}, "skip_snap": True}
        return {"result": res, "skip_snap": True}

    if len(parts) >= 5 and parts[1] == "love" and parts[2] == "memories" and parts[4] == "update":
        try:
            mid = int(parts[3])
        except (TypeError, ValueError):
            return {"result": {"ok": False, "msg": "learning_not_found"}, "skip_snap": True}
        fields = {}
        for key in ("title", "date", "memoryDate", "memory_date", "notes", "description",
                    "emoji", "tags", "isFavorite", "is_favorite", "photoId", "photo_id"):
            if key in body:
                fields[key] = body.get(key)
        if "title" in fields and not str(fields["title"] or "").strip():
            return {"result": {"ok": False, "msg": "love_memory_title_required"}, "skip_snap": True}
        if "memoryDate" in fields or "memory_date" in fields:
            stamp = fields.get("memoryDate") or fields.get("memory_date")
            if not str(stamp or "").strip():
                return {"result": {"ok": False, "msg": "love_memory_date_required"}, "skip_snap": True}
        res = db.update_relationship_memory(uid, mid, **fields)
        if not res.get("ok"):
            return {"result": res, "skip_snap": True}
        ca = _cloud_mod()
        if ca and ca.is_cloud_linked(uid):
            try:
                row = res.get("memory") or {}
                ca.love_upsert_cloud(uid, "memory", _love_memory_cloud_payload(row),
                                     record_id=row.get("cloud_id") or None)
            except Exception:
                pass
        return {"result": {"ok": True, "memoryId": str(mid)}}

    # 2) bintang favorit kenangan (toggle)
    if len(parts) >= 5 and parts[1] == "love" and parts[2] == "memories" and parts[4] == "favorite":
        try:
            mid = int(parts[3])
        except (TypeError, ValueError):
            return {"result": {"ok": False, "msg": "learning_not_found"}, "skip_snap": True}
        res = db.toggle_relationship_memory_favorite(uid, mid)
        if not res.get("ok"):
            return {"result": res, "skip_snap": True}
        ca = _cloud_mod()
        if ca and ca.is_cloud_linked(uid):
            try:
                row = db.get_relationship_memory(uid, mid) or {}
                ca.love_upsert_cloud(uid, "memory", _love_memory_cloud_payload(row),
                                     record_id=row.get("cloud_id") or None)
            except Exception:
                pass
        return {"result": {"ok": True, "favorite": bool(res.get("favorite")), "memoryId": str(mid)}}

    # 3) edit item bucket list (judul/kategori/target/catatan/prioritas/selesai)
    if len(parts) >= 5 and parts[1] == "love" and parts[2] == "bucket" and parts[4] == "update":
        try:
            bid = int(parts[3])
        except (TypeError, ValueError):
            return {"result": {"ok": False, "msg": "learning_not_found"}, "skip_snap": True}
        fields = {}
        for key in ("title", "category", "targetDate", "target_date", "date", "notes",
                    "priority", "isDone", "is_done", "done"):
            if key in body:
                fields[key] = body.get(key)
        if "title" in fields and not str(fields["title"] or "").strip():
            return {"result": {"ok": False, "msg": "love_bucket_title_required"}, "skip_snap": True}
        res = db.update_relationship_bucket_item(uid, bid, **fields)
        if not res.get("ok"):
            return {"result": res, "skip_snap": True}
        ca = _cloud_mod()
        if ca and ca.is_cloud_linked(uid):
            try:
                row = res.get("item") or {}
                ca.love_upsert_cloud(uid, "bucket_item", _love_bucket_cloud_payload(row),
                                     record_id=row.get("cloud_id") or None)
            except Exception:
                pass
        return {"result": {"ok": True, "itemId": str(bid)}}

    # 4) item selesai → kenangan (satu klik, idempoten)
    if len(parts) >= 5 and parts[1] == "love" and parts[2] == "bucket" and parts[4] == "promote-to-memory":
        try:
            bid = int(parts[3])
        except (TypeError, ValueError):
            return {"result": {"ok": False, "msg": "learning_not_found"}, "skip_snap": True}
        res = db.promote_relationship_bucket_item(uid, bid)
        if not res.get("ok"):
            return {"result": res, "skip_snap": True}
        ca = _cloud_mod()
        if ca and ca.is_cloud_linked(uid):
            try:
                mem = db.get_relationship_memory(uid, res["memory_id"]) or {}
                ca.love_upsert_cloud(uid, "memory", _love_memory_cloud_payload(mem),
                                     record_id=mem.get("cloud_id") or None)
            except Exception:
                pass
            try:
                item = db.get_relationship_bucket_item(uid, bid) or {}
                ca.love_upsert_cloud(uid, "bucket_item", _love_bucket_cloud_payload(item),
                                     record_id=item.get("cloud_id") or None)
            except Exception:
                pass
        return {"result": {"ok": True, "memoryId": str(res.get("memory_id") or ""),
                           "itemId": str(bid), "already": bool(res.get("already"))}}

    # --- Love parity: delete handlers per tab (parity tombol "love_delete_selected") ---
    if len(parts) >= 5 and parts[1] == "love" and parts[2] == "memories" and parts[4] == "delete":
        return {"result": db.delete_relationship_memory(uid, int(parts[3]))}
    if len(parts) >= 5 and parts[1] == "love" and parts[2] == "prompts" and parts[4] == "delete":
        return {"result": db.delete_relationship_prompt_response(uid, int(parts[3]))}
    if len(parts) >= 5 and parts[1] == "love" and parts[2] == "weekly" and parts[4] == "delete":
        return {"result": db.delete_relationship_weekly_review(uid, int(parts[3]))}
    if len(parts) >= 5 and parts[1] == "love" and parts[2] == "cycles" and parts[4] == "delete":
        return {"result": db.delete_menstrual_cycle(uid, int(parts[3]))}
    if len(parts) >= 5 and parts[1] == "love" and parts[2] == "events" and parts[4] == "delete":
        return {"result": db.delete_relationship_event(uid, int(parts[3]))}
    if len(parts) >= 5 and parts[1] == "love" and parts[2] == "bucket" and parts[4] == "delete":
        return {"result": db.delete_relationship_bucket_item(uid, int(parts[3]))}
    if path == "/api/love/prompt-favorite":
        return {"result": db.toggle_relationship_prompt_favorite(uid, body.get("promptKey") or body.get("prompt_key") or "")}

    # --- Love gallery parity: hapus foto + CRUD album + keanggotaan foto ---
    if len(parts) >= 5 and parts[1] == "love" and parts[2] == "photos" and parts[4] == "delete":
        ph = db.get_love_space_photo(uid, int(parts[3]))
        if ph and db.get_cloud_user_link(uid):
            try:
                db.enqueue_sync(uid, "gallery_photo", ph["id"], "delete",
                                {"cloud_photo_id": ph.get("cloud_photo_id")})
            except Exception:
                pass
        return {"result": db.delete_love_space_photo(uid, int(parts[3]))}
    if path == "/api/love/albums":
        # Parity _create_album: scope 'shared' hanya bila couple aktif.
        try:
            couple_active = bool((db.get_couple_context(uid) or {}).get("active"))
        except Exception:
            couple_active = False
        scope = "shared" if ((body.get("scope") or "personal") == "shared" and couple_active) else "personal"
        return {"result": db.create_love_album(uid, body.get("name") or "Album", scope)}
    if len(parts) >= 5 and parts[1] == "love" and parts[2] == "albums" and parts[4] == "rename":
        return {"result": db.rename_love_album(uid, int(parts[3]), body.get("name") or "")}
    if len(parts) >= 5 and parts[1] == "love" and parts[2] == "albums" and parts[4] == "delete":
        return {"result": db.delete_love_album(uid, int(parts[3]))}
    if len(parts) >= 5 and parts[1] == "love" and parts[2] == "albums" and parts[4] == "photo":
        # Parity "love_album_copy_to" (add_photo_to_love_album).
        return {"result": db.add_photo_to_love_album(uid, int(parts[3]), int(body.get("photoId") or 0))}
    if len(parts) >= 5 and parts[1] == "love" and parts[2] == "albums" and parts[4] == "photo-move":
        src_raw = body.get("sourceAlbumId")
        src = int(src_raw) if src_raw not in (None, "", 0, "0") else None
        return {"result": db.move_photo_to_love_album(uid, src, int(parts[3]), int(body.get("photoId") or 0))}
    if len(parts) >= 5 and parts[1] == "love" and parts[2] == "albums" and parts[4] == "photo-remove":
        return {"result": db.remove_photo_from_love_album(uid, int(parts[3]), int(body.get("photoId") or 0))}

    if path == "/api/social/messages":
        other = body.get("otherId")
        friends = _friends_map(uid)
        oid = int(other) if other else (int(friends[0]["id"]) if friends else None)
        if oid is None:
            return {"result": {"ok": False, "msg": "no_friend"}}
        ca = _cloud_mod()
        if ca and ca.is_cloud_linked(uid):
            try:
                return {"result": ca.send_direct_cloud(uid, oid, body.get("text") or "")}
            except Exception:
                pass
        return {"result": db.send_message(uid, oid, body.get("text") or "")}
    if re.match(r"^/api/friends/[^/]+/chat$", path):
        # Parity ChatDialog._send_message (hybrid cloud/local + attachments + reply_to).
        fid = path.split("/")[3]
        try:
            fid_i = int(fid)
        except ValueError:
            return _bad("not found")
        text = (body.get("text") or "").strip()
        attachment_ids = [int(x) for x in (body.get("attachmentIds") or []) if str(x).lstrip("-").isdigit()]
        if not text and not attachment_ids:
            return _bad("empty message")
        ctx = _cloud_chat_context(uid, fid_i)
        if ctx[0] is not None:
            cloud, conv_id = ctx
            reply_to = body.get("replyToId") or None
            client_id = str(__import__("uuid").uuid4())
            display_body = text or db.tr_db(user_id=uid, key="chat_attachment_message")
            try:
                if attachment_ids:
                    cloud.send_direct_message_with_attachments(
                        uid, conv_id, text, client_id, reply_to, attachment_ids)
                else:
                    row = cloud.send_direct_message(conv_id, text, client_id, reply_to)
                    db.cache_cloud_messages([row])
            except Exception:
                # Parity ChatDialog._send_message fallback: cache pending + enqueue sync.
                current = (db.get_cloud_user_link(uid) or {}).get("cloud_user_id")
                db.cache_pending_cloud_message(conv_id, current, client_id, display_body, reply_to)
                entity = "direct_message_attachment" if attachment_ids else "direct_message"
                payload = {"conversation_id": conv_id, "body": text,
                           "client_message_id": client_id, "reply_to_id": reply_to}
                if attachment_ids:
                    payload["attachment_local_ids"] = attachment_ids
                db.enqueue_sync(uid, entity, client_id, "send", payload)
            return {"result": {"ok": True, "cloud": True}, "skip_snap": True}
        reply_to = body.get("replyToId")
        try:
            reply_to = int(reply_to) if reply_to else None
        except (TypeError, ValueError):
            reply_to = None
        display_body = text or db.tr_db(user_id=uid, key="chat_attachment_message")
        result = db.send_message(uid, fid_i, display_body, reply_to_id=reply_to)
        if attachment_ids and result.get("message_id"):
            db.link_local_chat_attachments(uid, result.get("message_id"), attachment_ids)
        return {"result": result, "skip_snap": True}
    if path == "/api/friends/chat/attachment":
        # Parity ChatDialog._choose_attachments: prepare → pending BLOB (dipakai cloud & local).
        name = (body.get("name") or "attachment").strip() or "attachment"
        raw_b64 = body.get("dataBase64") or ""
        try:
            raw = base64.b64decode(raw_b64, validate=True)
        except Exception:
            return _bad("web_upload_bad_type")
        if not raw:
            return _bad("empty_file")
        import tempfile
        safe_name = os.path.basename(name).replace("\\", "_").replace("/", "_")[:160] or "attachment"
        tmpdir = tempfile.mkdtemp(prefix="cl_chat_")
        tmp_path = os.path.join(tmpdir, safe_name)
        try:
            with open(tmp_path, "wb") as f:
                f.write(raw)
            try:
                from cloud_service import get_cloud_service
                attachment = get_cloud_service().prepare_chat_attachment(uid, tmp_path)
            except Exception as e:
                return _bad(str(e))
        finally:
            try:
                os.remove(tmp_path)
            except Exception:
                pass
            try:
                os.rmdir(tmpdir)
            except Exception:
                pass
        return {"result": {"ok": True, "attachment": _chat_attachment_payload(attachment)}, "skip_snap": True}
    if path == "/api/friends/chat/attachments/discard":
        # Parity ChatDialog._clear_pending_attachments(delete=True).
        ids = [int(x) for x in (body.get("ids") or []) if str(x).lstrip("-").isdigit()]
        if ids:
            db.delete_pending_chat_attachments(uid, ids)
        return {"result": {"ok": True}, "skip_snap": True}
    if re.match(r"^/api/friends/[^/]+/typing$", path):
        # Parity ChatDialog._set_typing (cloud only; lokal = no-op).
        fid = path.split("/")[3]
        try:
            fid_i = int(fid)
        except ValueError:
            return _bad("not found")
        ctx = _cloud_chat_context(uid, fid_i)
        if ctx[0] is None:
            return {"result": {"ok": True}, "skip_snap": True}
        cloud, conv_id = ctx
        try:
            cloud.set_conversation_typing(conv_id, bool(body.get("isTyping")))
        except Exception:
            pass
        return {"result": {"ok": True}, "skip_snap": True}
    if re.match(r"^/api/friends/[^/]+/clear$", path):
        # Parity ChatDialog._clear_chat (cloud → blokir; lokal → soft delete self).
        fid = path.split("/")[3]
        try:
            fid_i = int(fid)
        except ValueError:
            return _bad("not found")
        if _cloud_chat_context(uid, fid_i)[0] is not None:
            return {"result": {"ok": False, "msg": "cloud_chat_clear_local_only"}, "skip_snap": True}
        db.clear_friend_chat(uid, fid_i)
        return {"result": {"ok": True}, "skip_snap": True}
    edit_m = re.match(r"^/api/friends/messages/([^/]+)/edit$", path)
    if edit_m:
        mid = edit_m.group(1)
        if body.get("cloud"):
            if mid.startswith("pending:"):
                return {"result": {"ok": False, "msg": "chat_pending_action_blocked"}, "skip_snap": True}
            cloud = _cloud_service_for_user(uid)
            if cloud is None:
                return {"result": {"ok": False, "msg": "cloud_auth_required"}, "skip_snap": True}
            try:
                row = cloud.edit_direct_message(mid, body.get("text") or "")
                db.cache_cloud_messages([row])
            except Exception as e:
                return {"result": {"ok": False, "msg": str(e)}}
            return {"result": {"ok": True}, "skip_snap": True}
        try:
            mid_i = int(mid)
        except (TypeError, ValueError):
            return _bad("not found")
        return {"result": db.edit_local_message(uid, mid_i, body.get("text") or ""), "skip_snap": True}
    del_m = re.match(r"^/api/friends/messages/([^/]+)/delete$", path)
    if del_m:
        mid = del_m.group(1)
        if body.get("cloud"):
            if mid.startswith("pending:"):
                return {"result": {"ok": False, "msg": "chat_pending_action_blocked"}}
            cloud = _cloud_service_for_user(uid)
            if cloud is None:
                return {"result": {"ok": False, "msg": "cloud_auth_required"}}
            try:
                row = cloud.delete_direct_message(mid)
                db.cache_cloud_messages([row])
                db.cache_cloud_message_reactions([], [mid])
            except Exception as e:
                return {"result": {"ok": False, "msg": str(e)}}
            return {"result": {"ok": True}, "skip_snap": True}
        try:
            mid_i = int(mid)
        except (TypeError, ValueError):
            return _bad("not found")
        return {"result": db.delete_local_message(uid, mid_i), "skip_snap": True}
    rxn_m = re.match(r"^/api/friends/messages/([^/]+)/reaction$", path)
    if rxn_m:
        mid = rxn_m.group(1)
        if body.get("cloud"):
            if mid.startswith("pending:"):
                return {"result": {"ok": False, "msg": "chat_pending_action_blocked"}}
            cloud = _cloud_service_for_user(uid)
            if cloud is None:
                return {"result": {"ok": False, "msg": "cloud_auth_required"}}
            try:
                cloud.set_direct_message_reaction(mid, body.get("reaction"))
                db.cache_cloud_message_reactions(cloud.fetch_message_reactions([mid]) or [], [mid])
            except Exception as e:
                return {"result": {"ok": False, "msg": str(e)}}
            return {"result": {"ok": True}, "skip_snap": True}
        try:
            mid_i = int(mid)
        except (TypeError, ValueError):
            return _bad("not found")
        return {"result": db.set_local_message_reaction(uid, mid_i, body.get("reaction")), "skip_snap": True}
    if path == "/api/friends/request":
        username = body.get("username") or ""
        ca = _cloud_mod()
        if ca and ca.is_cloud_linked(uid):
            try:
                return {"result": ca.friend_request_cloud(uid, username)}
            except Exception as e:
                return {"result": {"ok": False, "msg": str(e)}}
        return {"result": db.send_friend_request(uid, username)}

    if path == "/api/guild/create":
        name = (body.get("name") or "").strip()
        if not name:
            return {"result": {"ok": False, "msg": "empty"}}
        return {"result": db.create_guild(uid, name, body.get("description") or "")}
    if path == "/api/guild/join":
        try:
            gid = int(body.get("guildId") or body.get("id") or 0)
        except (TypeError, ValueError):
            gid = 0
        if not gid:
            return {"result": {"ok": False, "msg": "guild_id"}}
        return {"result": db.send_guild_request(uid, gid)}
    if path == "/api/guild/messages":
        # Parity GuildChatDialog._send_message: chat guild di halaman guild LOKAL
        # selalu disimpan ke DB lokal. Sebelumnya dikirim ke guild online (cloud)
        # padahal halaman ini menampilkan guild lokal → pesan tampak tidak terkirim.
        u = db.get_user(uid) or {}
        gid = u.get("guild_id")
        if not gid:
            return {"result": {"ok": False, "msg": "no_guild"}}
        text = (body.get("text") or "").strip()
        if not text:
            return {"result": {"ok": False, "msg": "empty"}}
        return {"result": db.send_guild_message(gid, uid, text), "skip_snap": True}
    if path == "/api/guild/leave":
        return {"result": db.leave_guild_with_transfer(uid)}
    if path == "/api/guild/invite":
        # P26: pemimpin guild mengundang TEMAN. Server-enforced via db.send_guild_invite
        # (leader sah + target harus teman accepted + belum di guild + kapasitas).
        # Bisa lewat friendId (dari UI daftar teman) atau username (parity lama).
        fid = int(body.get("friendId") or body.get("userId") or 0)
        if not fid:
            username = (body.get("username") or "").strip()
            if username:
                try:
                    conn = db.get_conn()
                    row = conn.execute("SELECT id FROM users WHERE username=?", (username,)).fetchone()
                    conn.close()
                    fid = int(row["id"]) if row else 0
                except Exception:
                    fid = 0
            if not fid:
                return {"result": {"ok": False, "msg": "user_not_found"}}
        return {"result": db.send_guild_invite(uid, fid)}
    if len(parts) >= 4 and parts[1] == "guild" and parts[2] == "invites" and parts[3].isdigit():
        iid = int(parts[3])
        if len(parts) >= 5 and parts[4] == "accept":
            return {"result": db.accept_invite(uid, iid)}
        if len(parts) >= 5 and parts[4] == "reject":
            return {"result": db.reject_invite(uid, iid)}
    if path == "/api/friends/remove":
        return {"result": db.remove_friend(uid, int(body.get("friendId") or 0))}
    if path == "/api/notifications/read":
        nid = body.get("id")
        if nid in (None, "", "all"):
            db.mark_read(uid)
            return {"result": {"ok": True}}
        db.mark_notification_read(uid, int(nid))
        return {"result": {"ok": True}}
    if path == "/api/guild/kick":
        g = (db.get_user(uid) or {}).get("guild_id")
        tid = int(body.get("userId") or body.get("targetId") or 0)
        if not g or not tid:
            return {"result": {"ok": False, "msg": "kick_args"}}
        return {"result": db.kick_guild_member(g, uid, tid)}
    if path == "/api/guild/transfer":
        g = (db.get_user(uid) or {}).get("guild_id")
        nid = int(body.get("userId") or body.get("newLeaderId") or 0)
        if not g or not nid:
            return {"result": {"ok": False, "msg": "transfer_args"}}
        return {"result": db.transfer_guild_leadership(g, uid, nid)}
    if path == "/api/guild/accept-transfer":
        return {"result": db.accept_leader_transfer(uid, int(body.get("transferId") or 0))}
    if path == "/api/guild/description":
        g = (db.get_user(uid) or {}).get("guild_id")
        if not g:
            return {"result": {"ok": False, "msg": "no_guild"}}
        db.update_guild(g, description=body.get("description") or "")
        return {"result": {"ok": True}}
    if path == "/api/guild/clear-chat":
        g = (db.get_user(uid) or {}).get("guild_id")
        if not g:
            return {"result": {"ok": False, "msg": "no_guild"}}
        db.clear_guild_chat(g)
        return {"result": {"ok": True}}
    if path == "/api/guild/custom-boss":
        u = db.get_user(uid) or {}
        gid = u.get("guild_id")
        return {"result": db.create_custom_boss(
            uid, gid, body.get("name") or "Boss", body.get("icon") or "👾",
            int(body.get("hp") or 1000), int(body.get("atk") or 20), int(body.get("minLevel") or 1))}
    if path == "/api/couple/request":
        friend_id = int(body.get("friendId") or 0)
        result = db.send_couple_request(uid, friend_id)
        if result.get("ok"):
            # P61: bila kedua pihak cloud-linked, relasi juga dibuat di cloud
            # supaya pasangan di device lain dapat mirror (best-effort).
            _couple_cloud_push(uid, "request", friend_id=friend_id)
        return {"result": result}
    if path == "/api/couple/end":
        rel = db.get_active_couple_relationship(uid)
        if not rel:
            return {"result": {"ok": False, "msg": "no_couple"}}
        result = db.end_local_couple_relationship(uid, rel.get("id"))
        _couple_cloud_push(uid, "end", rel_id=rel.get("id"))
        return {"result": result}
    if len(parts) >= 4 and parts[1] == "couple" and parts[3] == "respond":
        result = db.respond_couple_request(uid, int(parts[2]), bool(body.get("accept", True)))
        if result.get("ok"):
            _couple_cloud_push(uid, "respond", rel_id=int(parts[2]), accept=bool(body.get("accept", True)))
        return {"result": result}
    if len(parts) >= 4 and parts[1] == "couple" and parts[3] == "cancel":
        result = db.cancel_couple_request(uid, int(parts[2]))
        if result.get("ok"):
            _couple_cloud_push(uid, "cancel", rel_id=int(parts[2]))
        return {"result": result}
    if path == "/api/guild/boss/attack":
        # Parity GuildPage._perform_action: aksi "light"|"heavy"|"block"|"ultimate".
        u = db.get_user(uid) or {}
        gid = u.get("guild_id") or 0
        action = (body.get("action") or "light").strip().lower()
        if action not in ("light", "heavy", "block", "ultimate"):
            action = "light"
        result = db.attack_boss(uid, gid, action=action)
        return {"result": result}

    if path == "/api/guild/boss/start":
        # Parity GuildPage._start_boss / _start_boss_with_team (raid team maks
        # 4 anggota + leader, filter level boss diterapkan di UI; server tetap
        # menerima participant_ids eksplisit).
        u = db.get_user(uid) or {}
        gid = u.get("guild_id") or 0
        if not gid:
            return {"result": {"ok": False, "msg": "no_guild"}}
        bid = body.get("bossId") or body.get("boss_id")
        team = body.get("teamIds") or body.get("participant_ids") or None
        if isinstance(team, list):
            try:
                team = [int(x) for x in team]
            except Exception:
                team = None
        if team and uid not in team:
            team.insert(0, uid)
        result = db.start_boss(gid, bid, u, team)
        return {"result": result}

    if path == "/api/guild/skill":
        # Parity GuildPage._skill → db.use_class_skill.
        return {"result": db.use_class_skill(uid)}

    if path == "/api/guild/quick-heal":
        # Parity GuildPage._quick_heal → db.use_item('golden_apple').
        return {"result": db.use_item(uid, "golden_apple")}

    if len(parts) >= 5 and parts[1] == "guild" and parts[2] == "rewards" and parts[4] == "claim":
        # Parity GuildPage._claim_reward.
        return {"result": db.claim_boss_reward(int(parts[3]), uid)}

    if path == "/api/pvp":
        return {"result": db.send_pvp_challenge(uid, int(body.get("friendId") or 0))}
    if len(parts) >= 4 and parts[1] == "pvp" and parts[3] == "claim":
        cid = int(parts[2])
        try:
            result = db.respond_pvp_challenge(cid, uid, accept=True)
        except Exception as e:
            result = {"ok": False, "msg": str(e)}
        return {"result": result}
    if len(parts) >= 4 and parts[1] == "pvp" and parts[3] == "respond":
        cid = int(parts[2])
        accept = bool(body.get("accept", True))
        try:
            result = db.respond_pvp_challenge(cid, uid, accept=accept)
        except Exception as e:
            result = {"ok": False, "msg": str(e)}
        return {"result": result}
    if len(parts) >= 4 and parts[1] == "friends" and parts[3] == "accept":
        return {"result": db.accept_friend_request(uid, int(parts[2]))}
    if len(parts) >= 4 and parts[1] == "friends" and parts[3] == "reject":
        return {"result": db.reject_friend_request(uid, int(parts[2]))}
    if len(parts) >= 5 and parts[1] == "guild" and parts[2] == "requests" and parts[4] == "approve":
        g = (db.get_user(uid) or {}).get("guild_id")
        result = db.accept_guild_request(g, uid, int(parts[3])) if g else {"ok": False, "msg": "no guild"}
        return {"result": result}
    if len(parts) >= 5 and parts[1] == "guild" and parts[2] == "requests" and parts[4] == "reject":
        g = (db.get_user(uid) or {}).get("guild_id")
        result = db.reject_guild_request(g, uid, int(parts[3])) if g else {"ok": False, "msg": "no guild"}
        return {"result": result}
    if len(parts) >= 5 and parts[1] == "love" and parts[2] == "photos" and parts[4] == "meta":
        # Parity db.update_love_space_photo_visibility: toggle shared boleh kapan pun
        # (foto di-bind otomatis ke space saat couple terbentuk).
        result = db.update_love_space_photo_meta(
            uid,
            int(parts[3]),
            caption=body.get("caption"),
            photo_date=body.get("photoDate") or body.get("photo_date"),
            visibility=body.get("visibility"),
        )
        return {"result": result}


    # ── A11: connection · cycle · gallery diprofesionalkan ──────────────
    if len(parts) >= 5 and parts[1] == "love" and parts[2] == "cycles" and parts[4] == "update":
        # Edit riwayat siklus (dulu hanya tambah + hapus).
        try:
            cyc_id = int(parts[3])
        except (TypeError, ValueError):
            return {"result": {"ok": False, "msg": "learning_not_found"}, "skip_snap": True}
        kwargs = {}
        for key, arg in (("startDate", "start_date"), ("start_date", "start_date"),
                         ("endDate", "end_date"), ("end_date", "end_date"),
                         ("notes", "notes")):
            if key in body and arg not in kwargs:
                kwargs[arg] = body.get(key)
        res = db.update_menstrual_cycle(uid, cyc_id, **kwargs)
        if not res.get("ok"):
            code = res.get("code") or ""
            msg = {"start_date": "love_cycle_date_required",
                   "range": "love_cycle_range_invalid",
                   "not_found": "learning_not_found",
                   "forbidden": "learning_not_found"}.get(code, "love_cycle_no_fields")
            return {"result": {"ok": False, "msg": msg}, "skip_snap": True}
        ca = _cloud_mod()
        if ca and ca.is_cloud_linked(uid):
            try:
                row = res.get("cycle") or {}
                ca.love_upsert_cloud(uid, "cycle", {
                    "start_date": row.get("start_date") or "",
                    "end_date": row.get("end_date") or "",
                    "notes": row.get("notes") or "",
                }, record_id=row.get("cloud_id") or None)
            except Exception:
                pass
        return {"result": {"ok": True, "cycleId": str(cyc_id)}}

    if path == "/api/love/cycles/create-reminder":
        # Tombol "Jadikan pengingat" di tab Cycle: buat pengingat H-n dari
        # prediksi siklus berikutnya. Idempoten — pengingat dengan judul &
        # waktu sama tidak digandakan (klik dua kali = aman).
        pred = db.get_menstrual_prediction(uid) or {}
        if not pred.get("predicted_start"):
            return {"result": {"ok": False, "msg": "love_cycle_no_data"}, "skip_snap": True}
        try:
            days_before = int(body.get("daysBefore") or body.get("days_before") or 3)
        except (TypeError, ValueError):
            days_before = 3
        days_before = max(0, min(30, days_before))
        from datetime import date as _d, timedelta as _td
        try:
            start = _d.fromisoformat(str(pred["predicted_start"])[:10])
        except (ValueError, TypeError):
            return {"result": {"ok": False, "msg": "love_cycle_no_data"}, "skip_snap": True}
        when = start - _td(days=days_before)
        title = (body.get("title") or "").strip() or "Love Space · cycle reminder"
        time_str = (body.get("time") or "09:00").strip()
        if len(time_str) == 5:
            time_str += ":00"
        stamp = f"{when.isoformat()} {time_str}"
        description = (body.get("description") or "").strip()
        existing = None
        try:
            for rem in (db.get_reminders(uid) or []):
                if (rem.get("title") or "") == title and                         str(rem.get("reminder_datetime") or "").startswith(when.isoformat()):
                    existing = rem
                    break
        except Exception:
            existing = None
        if existing:
            return {"result": {"ok": True, "already": True, "reminderId": str(existing.get("id")),
                               "reminderDate": when.isoformat(), "daysBefore": days_before},
                    "skip_snap": True}
        res = db.add_reminder(uid, title, description, stamp, repeat_type="none")
        # A11 (temuan uji): `add_reminder` mengembalikan key `reminder_id`, bukan `id`
        # → dulu `reminderId` selalu kosong walau pengingatnya benar-benar dibuat.
        return {"result": {"ok": bool(res.get("ok")), "already": False,
                           "reminderId": str(res.get("reminder_id") or res.get("id") or ""),
                           "reminderDate": when.isoformat(), "daysBefore": days_before},
                "skip_snap": True}

    if len(parts) >= 5 and parts[1] == "love" and parts[2] == "albums" and parts[4] == "cover":
        # Sampul album (foto otomatis dimasukkan bila belum jadi anggota album).
        try:
            alb_id = int(parts[3])
        except (TypeError, ValueError):
            return {"result": {"ok": False, "msg": "learning_not_found"}, "skip_snap": True}
        res = db.set_love_album_cover(uid, alb_id, body.get("photoId") or body.get("photo_id"))
        if not res.get("ok"):
            return {"result": {"ok": False, "msg": "love_album_invalid"}, "skip_snap": True}
        return {"result": {"ok": True, "albumId": str(alb_id),
                           "photoId": str(res.get("photo_id") or ""),
                           "added": bool(res.get("added"))}}

    if path == "/api/love/photos/bulk":
        # Aksi massal galeri: hapus / ubah visibilitas / pindah album sekaligus.
        ids = body.get("ids") or body.get("photoIds") or []
        if isinstance(ids, str):
            ids = [x for x in ids.split(",") if x.strip()]
        action = (body.get("action") or "").strip()
        # A11 (perbaikan audit): `cloud_id` WAJIB dibaca sebelum baris dihapus.
        # Versi sebelumnya membacanya setelah `bulk_love_photos`, jadi foto sudah
        # tidak ada → penghapusan massal tidak pernah masuk antrean sinkron cloud
        # (foto tetap tertinggal di Supabase & storage).
        cloud_deletes = []
        if action == "delete":
            for pid in (ids or []):
                try:
                    ph = db.get_love_space_photo_raw(int(pid))
                except (TypeError, ValueError):
                    continue
                except Exception:
                    continue
                # Hanya foto milik pengirim yang benar-benar terhapus oleh bulk.
                if ph and ph.get("cloud_id") and int(ph.get("owner_user_id") or 0) == int(uid):
                    cloud_deletes.append((int(pid), str(ph.get("cloud_id"))))
        res = db.bulk_love_photos(uid, ids, action,
                                  album_id=body.get("albumId") or body.get("album_id"),
                                  visibility=body.get("visibility"))
        if res.get("ok") and action == "delete" and cloud_deletes:
            # Sinkronkan penghapusan ke cloud (pola sama dengan hapus satu foto).
            ca = _cloud_mod()
            if ca and ca.is_cloud_linked(uid):
                for pid, cid in cloud_deletes:
                    try:
                        db.enqueue_sync(uid, "gallery_photo", pid, "delete",
                                        {"cloud_photo_id": cid})
                    except Exception:
                        pass
        if not res.get("ok"):
            msg = {"no_photos": "love_gallery_none_selected",
                   "bad_action": "love_gallery_invalid_action",
                   "album": "love_album_invalid",
                   "invalid": "love_gallery_invalid_visibility"}.get(res.get("code") or "", "msg_error")
            return {"result": {"ok": False, "msg": msg}, "skip_snap": True}
        return {"result": res, "skip_snap": True}

    return None
