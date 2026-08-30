"""Studio & social API — learning, music, love, guild. Wraps database.py + learning_helper."""
from __future__ import annotations

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


def handle_get(path: str, uid: int, qs=None):
    qs = qs or {}
    if path == "/api/learning/notebooks":
        return {"ok": True, "notebooks": snapshot(uid)["notebooks"]}
    if path == "/api/music/playlists":
        s = snapshot(uid)
        return {"ok": True, "playlists": s["playlists"], "history": s["musicHistory"]}
    if path == "/api/love":
        return {"ok": True, "loveSpace": snapshot(uid)["loveSpace"]}
    if re.match(r"^/api/friends/[^/]+/chat$", path):
        # Parity ChatDialog._load_messages (lokal): mark read + pesan lengkap.
        fid = path.split("/")[3]
        try:
            fid_i = int(fid)
        except ValueError:
            return {"ok": False, "msg": "not found"}
        try:
            db.mark_messages_read(uid, fid_i)
        except Exception:
            pass
        try:
            limit = int((qs or {}).get("limit", [100])[0] or 100)
        except Exception:
            limit = 100
        limit = max(1, min(500, limit))
        msgs = []
        for m in db.get_messages(uid, fid_i, limit) or []:
            rxn = m.get("reactions") or {}
            msgs.append({
                "id": str(m.get("id")),
                "senderId": str(m.get("sender_id")),
                "text": m.get("message") or "",
                "isSelf": bool(m.get("sender_id") == uid),
                "createdAt": m.get("created_at") or "",
                "editedAt": m.get("edited_at") or "",
                "deletedAt": m.get("deleted_at") or "",
                "replyToId": str(m.get("reply_to_id")) if m.get("reply_to_id") else None,
                # di-agregat di client (_reaction_text): dict uid→emoji mentah dibawa
                "reactions": rxn,
            })
        return {"ok": True, "messages": msgs}
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
        )}
    return None


def _clean_lyrics_query(s: str) -> str:
    """Bersihkan judul/artis untuk query online (sama dengan _LyricsFetcher PyQt)."""
    import re as _re
    s = _re.sub(r"\((official|lyric|lyrics|video|audio|mv|hq|hd)[^)]*\)", " ", s, flags=_re.I)
    s = _re.sub(r"\bfeat(\.|uring)?\b.*$", " ", s, flags=_re.I)
    return _re.sub(r"\s+", " ", s).strip()


def get_lyrics(artist: str, title: str) -> dict:
    """Cari lirik online CEPAT: 3 provider paralel (LRCLIB get, LRCLIB search,
    lyrics.ovh) — meniru _LyricsFetcher PyQt. Return {plain, synced, source}."""
    import concurrent.futures as _cf
    import requests
    from urllib.parse import quote

    plain = ""
    synced = ""
    source = ""
    artist = _clean_lyrics_query(artist)
    title = _clean_lyrics_query(title)
    if artist and title:
        user_agent = {"User-Agent": "CraftLifeDesktop/1.0"}

        def lrclib_get():
            r = requests.get("https://lrclib.net/api/get",
                             params={"artist_name": artist, "track_name": title},
                             headers=user_agent, timeout=6)
            d = r.json() if r.ok else {}
            return (d.get("plainLyrics") or "", d.get("syncedLyrics") or "")

        def lrclib_search():
            r = requests.get("https://lrclib.net/api/search",
                             params={"q": f"{artist} {title}"},
                             headers=user_agent, timeout=6)
            for it in (r.json() if r.ok else []) or []:
                if it.get("syncedLyrics") or it.get("plainLyrics"):
                    return (it.get("plainLyrics") or "", it.get("syncedLyrics") or "")
            return ("", "")

        def ovh():
            r = requests.get(f"https://api.lyrics.ovh/v1/{quote(artist)}/{quote(title)}", timeout=6)
            return (((r.json() or {}).get("lyrics") or ""), "") if r.ok else ("", "")

        try:
            with _cf.ThreadPoolExecutor(max_workers=3) as ex:
                futs = [ex.submit(fn) for fn in (lrclib_get, lrclib_search, ovh)]
                for fut in _cf.as_completed(futs, timeout=8):
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
    if synced or plain:
        source = "lrclib" if (synced or plain) else "lyrics.ovh"
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
        return {"result": db.create_playlist(uid, body.get("name") or "Playlist")}
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
            my_gender=cur.get("my_gender") or "male",
            my_age=int(cur.get("my_age") or 25),
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
                return {"result": {"ok": False, "msg": str(e)}}
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
        # Parity ChatDialog._send_message (dengan reply_to).
        fid = path.split("/")[3]
        try:
            fid_i = int(fid)
        except ValueError:
            return _bad("not found")
        text = (body.get("text") or "").strip()
        if not text:
            return _bad("empty message")
        reply_to = body.get("replyToId")
        try:
            reply_to = int(reply_to) if reply_to else None
        except (TypeError, ValueError):
            reply_to = None
        return db.send_message(uid, fid_i, text, reply_to_id=reply_to)
    if re.match(r"^/api/friends/[^/]+/clear$", path):
        # Parity ChatDialog._clear_chat (non-cloud, konfirmasi di client).
        fid = path.split("/")[3]
        try:
            fid_i = int(fid)
        except ValueError:
            return _bad("not found")
        db.clear_friend_chat(uid, fid_i)
        return {"ok": True}
    if re.match(r"^/api/friends/messages/\d+/edit$", path):
        mid = int(path.split("/")[4])
        return db.edit_local_message(uid, mid, body.get("text") or "")
    if re.match(r"^/api/friends/messages/\d+/delete$", path):
        mid = int(path.split("/")[4])
        return db.delete_local_message(uid, mid)
    if re.match(r"^/api/friends/messages/\d+/reaction$", path):
        mid = int(path.split("/")[4])
        return db.set_local_message_reaction(uid, mid, body.get("reaction"))
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
        ca = _cloud_mod()
        if ca and ca.is_cloud_linked(uid):
            try:
                return {"result": ca.send_guild_message_cloud(body.get("text") or "")}
            except Exception:
                pass
        u = db.get_user(uid) or {}
        gid = u.get("guild_id")
        if not gid:
            return {"result": {"ok": False, "msg": "no_guild"}}
        return {"result": db.send_guild_message(gid, uid, body.get("text") or "")}
    if path == "/api/guild/leave":
        return {"result": db.leave_guild_with_transfer(uid)}
    if path == "/api/guild/invite":
        g = (db.get_user(uid) or {}).get("guild_id")
        if not g:
            return {"result": {"ok": False, "msg": "no_guild"}}
        guild = db.get_guild(g) or {}
        ginfo = guild.get("guild") or guild
        if str(ginfo.get("leader_id")) != str(uid):
            return {"result": {"ok": False, "msg": "not_leader"}}
        username = (body.get("username") or "").strip()
        target = None
        try:
            conn = db.get_conn()
            row = conn.execute("SELECT id FROM users WHERE username=?", (username,)).fetchone()
            if row:
                target = int(row["id"])
            conn.close()
        except Exception:
            target = None
        if not target:
            return {"result": {"ok": False, "msg": "user_not_found"}}
        conn = db.get_conn()
        conn.execute(
            "INSERT INTO guild_invites(guild_id, user_id, status) VALUES(?,?,'pending')",
            (g, target),
        )
        conn.commit()
        conn.close()
        return {"result": {"ok": True}}
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
