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
}


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
    out = {
        "id": str(nid),
        "title": row.get("title") or "",
        "description": row.get("description") or "",
        "icon": row.get("icon") or "📚",
        "sources": [
            {
                "id": str(s.get("id")),
                "title": s.get("title") or "",
                "type": s.get("type") or "text",
                "content": (s.get("content") or "")[:4000],
                "wordCount": len((s.get("content") or "").split()),
                "createdAt": s.get("created_at") or "",
            }
            for s in sources
        ],
        "chatHistory": [
            {
                "sender": "ai" if (c.get("role") == "assistant" or c.get("role") == "model") else "user",
                "text": c.get("content") or c.get("text") or "",
                "timestamp": c.get("created_at") or "",
            }
            for c in chats
        ],
        "flashcards": [],
        "quizzes": [],
        "podcast": [],
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
            try:
                data = json.loads(raw) if isinstance(raw, str) else raw
                qs = data.get("questions") if isinstance(data, dict) else data
                out["quizzes"] = [
                    {
                        "id": str(i),
                        "question": q.get("q") or q.get("question") or "",
                        "options": q.get("options") or [],
                        "correctAnswerIndex": int(q.get("answer") or q.get("correctAnswerIndex") or 0),
                        "explanation": q.get("explain") or q.get("explanation") or "",
                    }
                    for i, q in enumerate(qs or [])
                ]
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
    # Parity LearningPage: riwayat generasi Studio (tipe/topic/waktu) untuk combo
    # history + aksi hapus (_delete_generation). Slot tipe di atas = generasi terbaru.
    try:
        out["generations"] = [
            {
                "id": str(g.get("id") or ""),
                "gtype": _LEGACY_STUDIO_TYPE.get((g.get("type") or "").lower(), (g.get("type") or "").lower()),
                "topic": g.get("title") or "",
                "fileName": g.get("title") or "",
                "createdAt": g.get("created_at") or "",
                "content": g.get("content") or "",
            }
            for g in gens
        ]
    except Exception:
        out["generations"] = []
    return out


def _love_map(uid: int) -> dict:
    prof = {}
    try:
        prof = db.get_relationship_profile(uid) or {}
    except Exception:
        prof = {}
    memories = []
    try:
        memories = [
            {
                "id": str(m.get("id")),
                "title": m.get("title") or "",
                "date": m.get("memory_date") or m.get("date") or "",
                "description": m.get("notes") or "",
                "emoji": "💖",
            }
            for m in (db.get_relationship_memories(uid) or [])
        ]
    except Exception:
        pass
    bucket = []
    try:
        bucket = [
            {
                "id": str(b.get("id")),
                "title": b.get("title") or "",
                "isCompleted": bool(b.get("done") or b.get("is_done")),
                "completedDate": b.get("completed_at"),
            }
            for b in (db.get_relationship_bucket_items(uid) or [])
        ]
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
    try:
        data["events"] = [
            {
                "id": str(ev.get("id")),
                "title": ev.get("title") or "",
                "date": ev.get("event_date") or "",
                "category": ev.get("category") or "date",
                "notes": ev.get("notes") or "",
            }
            for ev in (db.get_relationship_events(uid) or [])
        ]
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
        data["cycles"] = [
            {
                "id": str(c.get("id")),
                "startDate": c.get("start_date") or "",
                "endDate": c.get("end_date") or "",
                "notes": c.get("notes") or "",
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
        data["albums"] = [
            {
                "id": str(a.get("id")),
                "name": a.get("name") or "",
                "scope": a.get("scope") or "personal",
                "photoIds": [str(x) for x in (db.get_love_album_photo_ids(uid, a.get("id")) or [])],
            }
            for a in (db.get_love_albums(uid) or [])
        ]
    except Exception:
        data["albums"] = []
    try:
        data["coupleActive"] = bool((db.get_couple_context(uid) or {}).get("active"))
    except Exception:
        data["coupleActive"] = False
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
                try:
                    lang = (db.get_user(uid2) or {}).get("language") or "id"
                except Exception:
                    lang = "id"
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


def handle_get(path: str, uid: int, qs=None):
    qs = qs or {}
    if path == "/api/learning/notebooks":
        return {"ok": True, "notebooks": snapshot(uid)["notebooks"]}
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
        return {"ok": True, "loveSpace": snapshot(uid)["loveSpace"]}
    if path == "/api/love/couple-tracking":
        return _couple_tracking_map(uid)
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
        return {"ok": True, "lyrics": get_lyrics(
            (qs.get("artist") or [""])[0].strip(),
            (qs.get("title") or [""])[0].strip(),
            (qs.get("path") or [""])[0].strip(),
        )}
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


def get_lyrics(artist: str, title: str, file_path: str = "") -> dict:
    """Cari lirik online CEPAT & LUAS: LRCLIB get + LRCLIB search (beberapa varian
    query) + lyrics.ovh, paralel — meniru _LyricsFetcher PyQt namun dengan
    fallback query makin longgar (artis+judul → judul saja → artis saja).
    Fallback terakhir: lirik tertanam file audio. Return {plain, synced, source}."""
    import concurrent.futures as _cf
    import os
    import requests
    from urllib.parse import quote

    plain = ""
    synced = ""
    source = ""
    artist = _clean_lyrics_query(artist)
    title = _clean_lyrics_query(title)
    if artist or title:
        user_agent = {"User-Agent": "CraftLifeDesktop/1.0"}

        def lrclib_get():
            r = requests.get("https://lrclib.net/api/get",
                             params={"artist_name": artist, "track_name": title},
                             headers=user_agent, timeout=5)
            d = r.json() if r.ok else {}
            return (d.get("plainLyrics") or "", d.get("syncedLyrics") or "")

        def lrclib_search(q):
            r = requests.get("https://lrclib.net/api/search",
                             params={"q": q},
                             headers=user_agent, timeout=5)
            for it in (r.json() if r.ok else []) or []:
                if it.get("syncedLyrics") or it.get("plainLyrics"):
                    return (it.get("plainLyrics") or "", it.get("syncedLyrics") or "")
            return ("", "")

        def ovh():
            if not (artist and title):
                return ("", "")
            r = requests.get(f"https://api.lyrics.ovh/v1/{quote(artist)}/{quote(title)}", timeout=5)
            return (((r.json() or {}).get("lyrics") or ""), "") if r.ok else ("", "")

        # Varian query progresif (paling akurat → paling longgar) utk coverage luas.
        queries = []
        if artist and title:
            queries.append(f"{artist} {title}")
        if title and title not in queries:
            queries.append(title)
        if artist and artist not in queries:
            queries.append(artist)

        def _jobs():
            if artist and title:
                yield lrclib_get
            yield ovh
            for q in queries:
                yield lambda q=q: lrclib_search(q)

        try:
            with _cf.ThreadPoolExecutor(max_workers=5) as ex:
                futs = [ex.submit(fn) for fn in _jobs()]
                for fut in _cf.as_completed(futs, timeout=9):
                    try:
                        p, s = fut.result()
                    except Exception:
                        continue
                    if s and not synced:
                        synced = s
                    if p and not plain:
                        plain = p
                    if synced and plain:
                        break
        except Exception:
            pass

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
        source = "lrclib"
    elif plain:
        source = source or "lrclib"
    return {"plain": plain, "synced": synced, "source": source}


def _chat_ai(uid: int, notebook_id: int, question: str) -> str:
    db.add_learning_chat(notebook_id, "user", question)
    key = ""
    try:
        key = db.get_gemini_api_key(uid) or os.environ.get("GEMINI_API_KEY") or ""
    except Exception:
        key = os.environ.get("GEMINI_API_KEY") or ""
    chunks = []
    try:
        rows = db.get_learning_chunks(notebook_id, uid) or []
        chunks = [r.get("chunk_text") or r.get("content") or "" for r in rows]
        chunks = [c for c in chunks if c]
    except Exception:
        chunks = []
    if not chunks:
        try:
            for s in db.get_learning_sources(notebook_id, uid) or []:
                if s.get("content"):
                    chunks.append(s["content"][:2000])
        except Exception:
            pass
    history = []
    try:
        for c in db.get_learning_chats(notebook_id) or []:
            history.append({"role": c.get("role") or "user", "content": c.get("content") or ""})
    except Exception:
        pass
    answer = ""
    if key and chunks:
        try:
            import learning_helper as lh
            ctx = chunks[:8]
            if hasattr(lh, "find_relevant_chunks"):
                try:
                    ctx = lh.find_relevant_chunks(question, chunks) or ctx
                except Exception:
                    pass
            answer = lh.chat_with_sources(question, ctx, history, key)
        except Exception as e:
            answer = str(e)
    if not answer:
        if not chunks:
            answer = "Tambahkan sumber ke notebook ini dulu, baru tanya AI."
        elif not key:
            answer = "Setel Gemini API key di pengaturan (tersimpan di Python, bukan di web)."
        else:
            answer = "Tidak ada jawaban."
    db.add_learning_chat(notebook_id, "assistant", answer)
    return answer


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


def _strip_json_fence(text: str) -> str:
    text = (text or "").strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[-1]
        if text.endswith("```"):
            text = text.rsplit("```", 1)[0]
    return text.strip()


def _studio_generate(uid: int, body: dict, studio_type: str):
    key = _gemini_key(uid)
    content = body.get("content") or ""
    topic = (body.get("topic") or "").strip()
    nid = body.get("notebookId")
    chunks = [content[:8000]] if content else []
    if nid and not chunks:
        try:
            for s in db.get_learning_sources(int(nid), uid) or []:
                if s.get("content"):
                    chunks.append(s["content"][:4000])
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
        if studio_type == "quiz":
            kwargs["count"] = int(body.get("questionCount") or 10)
        raw = lh.generate_studio_content(studio_type, topic or "Materi", chunks, key, **kwargs)
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
    if nid:
        try:
            db.add_learning_generation(int(nid), persist_type, topic or studio_type, text[:200000])
        except Exception:
            pass
    return {"result": payload, "skip_snap": True}

def _add_source_from_upload(nid: int, uid: int, path: str) -> dict:
    """Ekstraksi file upload Learning (parity LearningPage._add_source_files)."""
    if not path or not os.path.isfile(path):
        return {"ok": False, "msg": "learning_not_found"}
    ext = os.path.splitext(path)[1].lower()
    ftype = "docx" if ext == ".docx" else "pdf" if ext == ".pdf" else "txt"
    try:
        import learning_helper as lh
        if ftype == "pdf":
            content = lh.extract_from_pdf(path)
        elif ftype == "docx":
            content = lh.extract_from_docx(path)
        else:
            content = lh.extract_from_txt(path)
    except Exception:
        try:
            if ftype == "txt":
                content = open(path, "r", encoding="utf-8", errors="ignore").read()[:50000]
            else:
                content = open(path, "rb").read().decode(errors="ignore")[:50000]
        except Exception as e:
            return {"ok": False, "msg": str(e)}
    content = str(content or "").strip()
    if not content or content.startswith("[Gagal"):
        return {"ok": False, "msg": content or "learning_source_empty_file"}
    return db.add_learning_source(
        nid, uid, ftype, os.path.basename(path), path, content[:80000],
    )


def handle_post(path: str, uid: int, body: dict, parts: list):
    if path == "/api/learning/notebooks":
        title = (body.get("title") or "Notebook").strip()
        return {"result": db.create_learning_notebook(uid, title)}

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
            title = (body.get("title") or "").strip()
            if not title:
                return {"result": {"ok": False, "msg": "learning_no_title"}}
            db.update_learning_notebook(nid, uid, title)
            return {"result": {"ok": True}}
        if len(parts) >= 5 and parts[4] == "upload-source":
            # Parity LearningPage._add_source_files: ekstrak per ekstensi →
            # db.add_learning_source(type, basename, path, content[:80000]).
            path = body.get("path") or ""
            res = _add_source_from_upload(nid, uid, path)
            try:
                if res.get("ok"):
                    os.remove(path)
            except Exception:
                pass
            return {"result": res}
        if len(parts) >= 5 and parts[4] == "sources":
            if len(parts) >= 7 and parts[6] == "delete":
                try:
                    db.delete_learning_source(int(parts[5]), uid)
                except Exception:
                    pass
                return {"result": {"ok": True}}
            result = db.add_learning_source(
                nid, uid,
                body.get("type") or "text",
                body.get("title") or "Source",
                body.get("path") or "",
                body.get("content") or "",
            )
            return {"result": result}
        if len(parts) >= 5 and parts[4] == "chat":
            text = (body.get("text") or "").strip()
            if not text:
                return {"result": {"ok": False, "msg": "empty"}}
            answer = _chat_ai(uid, nid, text)
            return {"result": {"ok": True, "answer": answer}}

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
    if path == "/api/ai/chat":
        nid = int(body.get("notebookId") or 0)
        text = (body.get("text") or body.get("question") or "").strip()
        if not nid or not text:
            return {"result": {"ok": False, "msg": "notebook_and_text"}, "skip_snap": True}
        answer = _chat_ai(uid, nid, text)
        return {"result": {"ok": True, "answer": answer}, "skip_snap": True}
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
        ca = _cloud_mod()
        payload = {
            "title": body.get("title") or "",
            "memory_date": body.get("date") or "",
            "notes": body.get("description") or "",
        }
        if ca and ca.is_cloud_linked(uid):
            try:
                return {"result": ca.love_upsert_cloud(uid, "memory", payload)}
            except Exception:
                pass
        return {"result": db.add_relationship_memory(uid, payload["title"], payload["memory_date"], payload["notes"])}
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
        return {"result": db.add_relationship_event(
            uid,
            body.get("title") or "Event",
            body.get("date") or body.get("eventDate") or "",
            body.get("category") or "date",
            body.get("notes") or "",
        )}
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
        return {"result": db.add_relationship_bucket_item(uid, body.get("title") or "Goal")}
    if len(parts) >= 5 and parts[1] == "love" and parts[2] == "bucket" and parts[4] == "toggle":
        bid = int(parts[3])
        items = db.get_relationship_bucket_items(uid) or []
        done = True
        for it in items:
            if int(it.get("id")) == bid:
                done = not bool(it.get("done") or it.get("is_done"))
                break
        return {"result": db.toggle_relationship_bucket_item(uid, bid, done)}

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
        return {"result": db.send_couple_request(uid, int(body.get("friendId") or 0))}
    if path == "/api/couple/end":
        rel = db.get_active_couple_relationship(uid)
        if not rel:
            return {"result": {"ok": False, "msg": "no_couple"}}
        return {"result": db.end_local_couple_relationship(uid, rel.get("id"))}
    if len(parts) >= 4 and parts[1] == "couple" and parts[3] == "respond":
        return {"result": db.respond_couple_request(uid, int(parts[2]), bool(body.get("accept", True)))}
    if len(parts) >= 4 and parts[1] == "couple" and parts[3] == "cancel":
        return {"result": db.cancel_couple_request(uid, int(parts[2]))}
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

    return None
