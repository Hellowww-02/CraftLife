"""CraftLife local HTTP API — wraps database.py for the React UI (Phase 0–1)."""
from __future__ import annotations

import json
import os
import threading
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

import database as db
import life_api
import studio_api
from translations import get_text

_state = {
    "user_id": None,
    "token": None,
}

WEB_I18N_KEYS = [
    "app_logo", "loading", "nav_dashboard", "nav_habits", "nav_dailies",
    "nav_quests", "nav_sport", "nav_economy", "nav_health_food", "nav_shop",
    "nav_pets", "nav_guild", "nav_achievements", "nav_settings", "nav_learning",
    "nav_music", "nav_love", "nav_calendar", "nav_friends",
    "page_home_title", "page_home_subtitle", "dashboard_greeting",
    "dashboard_level", "dashboard_gold", "dashboard_hp", "dashboard_mp",
    "dashboard_streak", "web_shell_title", "web_engine_missing", "web_loading",
    "web_api_offline", "web_live_badge", "nav_adventure_menu", "nav_prestige_level",
    "web_offline_first", "web_connecting", "web_use_game_error",
    "web_legacy_ui", "web_open_web_ui",
    "web_shop_title", "web_shop_subtitle", "web_shop_tab", "web_inv_tab",
    "web_forge_tab", "web_buy", "web_buy_more", "web_sell", "web_use_item",
    "web_equip", "web_unequip", "web_forge_item", "web_inv_empty",
    "web_pet_adopt", "web_pet_feed", "web_pet_train", "web_boss_start",
    "web_boss_attack", "web_boss_skill", "web_ach_claim", "web_level_up",
    "cloud_group", "cloud_account_title", "cloud_account_info", "cloud_email",
    "cloud_password", "cloud_create_account", "cloud_signin_link",
    "cloud_credentials_invalid", "cloud_verification_sent", "cloud_account_created",
    "cloud_error", "cloud_link_account", "cloud_sync_now", "cloud_migrate_local",
    "cloud_sign_out", "cloud_status_not_configured", "cloud_status_ready_unlinked",
    "cloud_status_linked", "cloud_never", "cloud_syncing", "cloud_sync_success",
    "cloud_sync_partial", "cloud_queue_inspect", "cloud_queue_retry",
    "cloud_queue_empty", "cloud_realtime_on", "cloud_realtime_connecting",
    "cloud_personal_revision", "cloud_personal_conflict", "cloud_conflict_title",
    "cloud_conflict_hint", "cloud_conflict_keep_local", "cloud_conflict_use_remote",
    "cloud_conflict_keep_local_confirm", "cloud_conflict_use_remote_confirm",
    "cloud_conflict_resolved", "cloud_devices_title", "cloud_devices_info",
    "cloud_device_revoke", "cloud_device_revoke_others", "cloud_device_active",
    "cloud_device_revoked", "cloud_device_last_seen", "cloud_device_current_block",
    "cloud_device_register_failed", "cloud_off_hint", "cloud_shop_wallet", "web_enchant",
    "love_add_photo", "love_photo_pick_hint", "cloud_friend_username", "cloud_friend_add",
    "cloud_pvp_challenge", "cloud_chat_pick_friend", "love_daily_checkin", "love_save_checkin",
    "web_supplies_title", "web_supplies_sub", "web_supplies_add",
    "web_music_download", "web_music_search", "web_quiz_generate",
    "web_cal_day_note", "web_cal_save_note", "web_health_history",
    "web_local_account", "web_leaderboard", "web_profile", "web_create_guild", "web_join_guild",
    "web_tracker_export", "web_tracker_import", "web_check_update", "web_stay_logged_in", "web_switch_local",
    "web_task_fail", "web_task_duplicate", "web_task_folder_new", "web_supply_adjust",
    "web_sport_complete", "web_water_goal", "web_calorie_goal",
    # ── Phase P1: drag & drop reorder + quick add + undo ──
    "task_reorder_hint", "quick_add_title", "quick_add_habit", "quick_add_daily",
    "quick_add_quest", "quick_add_placeholder", "quick_add_add", "quick_add_cancel",
    "task_undo", "task_deleted", "task_restored", "task_moved_folder",
    # ── Phase P3: economy trend + supplies ──
    "economy_trend_title", "economy_trend_income", "economy_trend_expense",
    "economy_trend_net", "economy_period_7d", "economy_period_30d",
    "economy_period_90d", "economy_expense_split", "economy_trend_empty",
    "supplies_dlg_title_add", "supplies_dlg_title_edit", "supplies_name_ph",
    "supplies_category_ph", "supplies_unit_ph", "supplies_stock_lbl",
    "supplies_min_lbl", "supplies_price_lbl", "supplies_location_ph",
    "supplies_notes_ph", "supplies_economy_lbl", "supplies_stock_now",
    "supplies_tx_title", "supplies_tx_in", "supplies_tx_out",
    "supplies_tx_adjust", "supplies_qty_lbl", "supplies_note_ph",
    "supplies_restock_expense", "supplies_economy_amount",
    "supplies_economy_category_ph", "btn_save",
    "dashwidgets_title", "dashwidgets_hint", "dashwidgets_visible",
    "dashwidgets_hidden", "dashwidgets_compact", "dashwidgets_expanded",
    "dashwidgets_save", "dashwidgets_cancel", "wrapped_title", "wrapped_open",
    "wrapped_empty", "wrapped_hero", "wrapped_total", "wrapped_active_days",
    "wrapped_best", "wrapped_focus", "wrapped_level", "wrapped_streak",
    "wrapped_income", "wrapped_expense", "wrapped_top_habits", "talents_points",
    "talents_unlocked", "talents_unlock", "talents_locked_level",
    "talents_locked_prereq", "talents_no_points", "talents_tier",
]


def configure(user_id: int, token: str | None = None) -> None:
    _state["user_id"] = int(user_id)
    _state["token"] = token


def _json_bytes(obj) -> bytes:
    return json.dumps(obj, ensure_ascii=False, default=str).encode("utf-8")


def _row_user(u: dict) -> dict:
    if not u:
        return {}
    level = int(u.get("level") or 1)
    cls = (u.get("avatar_class") or "warrior").lower()
    if cls == "archer":
        cls = "ranger"
    ice = 0
    try:
        for row in db.get_inventory(u.get("id")):
            if row.get("item_id") == "ice_block":
                ice += int(row.get("quantity") or 0)
    except Exception:
        ice = 0
    active_pet = None
    try:
        for p in db.get_user_pets(u.get("id")):
            if p.get("is_active"):
                active_pet = p.get("pet_id")
                break
    except Exception:
        pass
    return {
        "id": str(u.get("id")),
        "username": u.get("username") or "",
        "displayName": u.get("display_name") or u.get("username") or "",
        "name": u.get("display_name") or "",
        "bio": u.get("bio") or "",
        "avatarClass": cls if cls in ("warrior", "mage", "rogue", "paladin", "ranger", "healer") else "warrior",
        "heroClass": u.get("avatar_class") or "warrior",
        "avatarEmoji": u.get("avatar_emoji") or "⚔️",
        "avatar": u.get("avatar_emoji") or "⚔️",
        "avatarColor": u.get("avatar_color") or "#ef4444",
        "level": level,
        "xp": int(u.get("xp") or 0),
        "xpToNextLevel": level * 150,
        "hp": int(u.get("hp") or 0),
        "maxHp": int(u.get("max_hp") or 50),
        "mp": int(u.get("mp") or 0),
        "maxMp": int(u.get("max_mp") or 30),
        "gold": int(round(float(u.get("gold") or 0))),
        "gems": int(u.get("gems") or 0),
        "rebirthCount": int(u.get("rebirth_count") or 0),
        "sportLevel": int(u.get("sport_level") or 1),
        "sportXp": int(u.get("sport_xp") or 0),
        "activePetId": active_pet,
        "equippedWeapon": None,
        "equippedArmor": None,
        "equippedTool": None,
        "equippedLegendary": None,
        "freezeSlots": ice,
        "createdAt": u.get("created_at") or "",
        "language": u.get("language") or "id",
        "theme": u.get("theme") or "modern_dark",
        "soundEnabled": bool(u.get("sound_enabled", 1)),
        "longestStreak": int(u.get("longest_streak") or 0),
        "guildId": u.get("guild_id"),
        "currency": u.get("currency") or "IDR",
        "fontScale": int(u.get("font_scale") or 100),
        "highContrast": bool(u.get("high_contrast")),
        "isAdmin": bool(u.get("is_admin")),
        "onboardingDone": bool(u.get("onboarding_done")),
    }


def _map_habit(h: dict) -> dict:
    diff = (h.get("difficulty") or "medium").lower()
    if diff not in ("trivial", "easy", "medium", "hard", "epic"):
        diff = "medium"
    return {
        "id": str(h.get("id")),
        "title": h.get("name") or "",
        "notes": h.get("notes") or "",
        "folderId": str(h["folder_id"]) if h.get("folder_id") else None,
        "difficulty": diff,
        "isPositive": bool(h.get("positive", 1)),
        "isNegative": bool(h.get("negative", 0)),
        "positiveStreak": int(h.get("streak") or h.get("counter_up") or 0),
        "negativeStreak": int(h.get("counter_down") or 0),
        "history": [],
        "createdAt": h.get("created_at") or "",
        "icon": h.get("icon") or "⚔️",
        "doneToday": bool(h.get("done_today")),
        "sortOrder": int(h.get("sort_order") or 0),
    }


def _parse_repeat(raw) -> list:
    if not raw:
        return [0, 1, 2, 3, 4, 5, 6]
    s = str(raw)
    days = []
    for part in s.replace(";", ",").split(","):
        part = part.strip()
        if part.isdigit():
            days.append(int(part) % 7)
    return days or [0, 1, 2, 3, 4, 5, 6]


def _map_daily(d: dict) -> dict:
    diff = (d.get("difficulty") or "medium").lower()
    if diff not in ("trivial", "easy", "medium", "hard", "epic"):
        diff = "medium"
    return {
        "id": str(d.get("id")),
        "title": d.get("name") or "",
        "notes": d.get("notes") or "",
        "folderId": str(d["folder_id"]) if d.get("folder_id") else None,
        "difficulty": diff,
        "streak": int(d.get("streak") or 0),
        "isCompletedToday": bool(d.get("done_today")),
        "repeatDays": _parse_repeat(d.get("repeat_days")),
        "lastCompletedDate": d.get("last_done"),
        "isFrozen": int(d.get("freeze_slots") or 0) > 0,
        "createdAt": d.get("created_at") or "",
        "icon": d.get("icon") or "📅",
        "sortOrder": int(d.get("sort_order") or 0),
    }


def _map_todo(t: dict) -> dict:
    prio = (t.get("priority") or "medium").lower()
    if prio not in ("trivial", "easy", "medium", "hard", "epic"):
        prio = "medium"
    return {
        "id": str(t.get("id")),
        "title": t.get("name") or "",
        "notes": t.get("notes") or "",
        "folderId": str(t["folder_id"]) if t.get("folder_id") else None,
        "difficulty": prio,
        "dueDate": t.get("due_date"),
        "isCompleted": bool(t.get("done")),
        "completedAt": None,
        "createdAt": t.get("created_at") or "",
        "icon": t.get("icon") or "📜",
        "sortOrder": int(t.get("sort_order") or 0),
    }


def _map_inv(row: dict) -> dict:
    return {
        "itemId": row.get("item_id"),
        "quantity": int(row.get("quantity") or 1),
        "equipped": bool(row.get("equipped")),
        "rowId": row.get("id"),
        "enchantLevel": int(row.get("enchant_level") or 0),
    }


def _map_pet(row: dict) -> dict:
    return {
        "petId": row.get("pet_id"),
        "nickname": row.get("nickname") or row.get("pet_id"),
        "level": int(row.get("level") or 1),
        "xp": int(row.get("exp") or row.get("xp") or 0),
        "hunger": int(row.get("hunger") or 100),
        "isEquipped": bool(row.get("is_active")),
        "adoptedAt": row.get("adopted_at") or "",
    }


def _map_ach(row: dict) -> dict:
    unlocked = bool(row.get("unlocked_at"))
    return {
        "id": str(row.get("id")),
        "title": row.get("name") or "",
        "desc": row.get("description") or "",
        "category": row.get("category") or "level",
        "icon": row.get("icon") or "🏆",
        "xpReward": int(row.get("xp_reward") or 0),
        "goldReward": int(row.get("gold_reward") or 0),
        "currentProgress": int(row.get("progress") or 0),
        "targetProgress": int(row.get("requirement_value") or 1),
        "isUnlocked": unlocked,
        "isClaimed": bool(row.get("claimed")),
    }


def _shop_catalog() -> list:
    out = []
    for iid, item in getattr(db, "SHOP_ITEMS", {}).items():
        rec = dict(item)
        rec["id"] = iid
        rec["buffDesc"] = rec.pop("buff_desc", rec.get("buffDesc", ""))
        rec["craftOnly"] = bool(rec.get("craftOnly") or rec.get("craft_only"))
        out.append(rec)
    return out


def _pet_catalog() -> list:
    out = []
    for pid, pet in getattr(db, "PETS_DATA", {}).items():
        rec = dict(pet)
        rec["id"] = pid
        rec["baseBuff"] = rec.pop("base_buff", rec.get("baseBuff", {}))
        out.append(rec)
    return out


def _boss_catalog() -> list:
    out = []
    for bid, b in getattr(db, "BOSSES", {}).items():
        rec = dict(b)
        rec["id"] = bid
        rec["maxHp"] = rec.get("hp")
        rec["xpReward"] = rec.get("xp") or rec.get("xpReward")
        rec["goldReward"] = rec.get("gold") or rec.get("goldReward")
        rec["minLevel"] = rec.get("min_level") or rec.get("minLevel") or 1
        out.append(rec)
    return out


def _recipe_catalog() -> list:
    out = []
    for rid, r in getattr(db, "CRAFTING_RECIPES", {}).items():
        inputs = r.get("inputs") or []
        req = [{"itemId": i, "quantity": 1} for i in inputs]
        out.append({
            "id": rid,
            "resultItemId": r.get("output") or rid,
            "requiredItems": req,
            "goldCost": int(r.get("gold") or 0),
        })
    return out


def _snapshot(uid: int) -> dict:
    u = db.get_user(uid) or {}
    try:
        ach = [_map_ach(a) for a in db.get_user_achievements(uid)]
    except Exception:
        ach = []
    try:
        inv = [_map_inv(r) for r in db.get_inventory(uid)]
    except Exception:
        inv = []
    try:
        pets = [_map_pet(r) for r in db.get_user_pets(uid)]
    except Exception:
        pets = []
    payload = {
        "user": _row_user(u),
        "habits": [_map_habit(h) for h in db.get_habits(uid)],
        "dailies": [_map_daily(d) for d in db.get_dailies(uid)],
        "quests": [_map_todo(t) for t in db.get_todos(uid)],
        "inventory": inv,
        "userPets": pets,
        "achievements": ach,
        "lang": u.get("language") or "id",
    }
    payload.update(life_api.snapshot(uid))
    payload.update(studio_api.snapshot(uid))
    try:
        battle = db.get_active_boss_for_user(uid)
    except Exception:
        battle = None
    if battle:
        payload["activeBoss"] = {
            "id": battle.get("boss_id") or "",
            "name": battle.get("boss_name") or "",
            "icon": battle.get("boss_icon") or "🐉",
            "tier": battle.get("boss_tier") or "normal",
            "hp": int(battle.get("boss_max_hp") or battle.get("boss_hp") or 0),
            "maxHp": int(battle.get("boss_max_hp") or battle.get("boss_hp") or 0),
            "atk": int(battle.get("boss_attack") or 0),
            "xpReward": 0,
            "goldReward": 0,
            "minLevel": 1,
        }
        payload["activeBossHp"] = int(battle.get("boss_hp") or 0)
        payload["activeBossId"] = battle.get("boss_id")
    else:
        payload["activeBoss"] = None
        payload["activeBossHp"] = 0
        payload["activeBossId"] = None
    link = None
    try:
        link = db.get_cloud_user_link(uid)
    except Exception:
        link = None
    wallet = None
    if link:
        try:
            wallet = db.get_cloud_wallet(uid)
        except Exception:
            wallet = None
        gold_cloud = int((wallet or {}).get("gold") or 0) if wallet else None
        payload["user"]["cloudLinked"] = True
        payload["user"]["goldLocal"] = payload["user"]["gold"]
        payload["user"]["goldCloud"] = gold_cloud
        payload["goldLocal"] = payload["user"]["gold"]
        payload["goldCloud"] = gold_cloud
        payload["cloudLinked"] = True
        if gold_cloud is not None:
            payload["user"]["gold"] = gold_cloud
            if wallet and wallet.get("gems") is not None:
                payload["user"]["gems"] = int(wallet.get("gems") or 0)
        try:
            cloud_inv = db.get_cloud_inventory_cache(uid)
        except Exception:
            cloud_inv = []
        if cloud_inv:
            payload["inventory"] = [
                _map_inv({
                    "item_id": row.get("item_key"),
                    "quantity": row.get("qty") or 0,
                    "equipped": row.get("equipped"),
                    "id": row.get("item_key"),
                    "enchant_level": row.get("enchant_level") or 0,
                })
                for row in cloud_inv
                if int(row.get("qty") or 0) > 0
            ]
    else:
        payload["goldLocal"] = payload["user"]["gold"]
        payload["goldCloud"] = None
        payload["cloudLinked"] = False
        payload["user"]["goldLocal"] = payload["user"]["gold"]
        payload["user"]["goldCloud"] = None
        payload["user"]["cloudLinked"] = False
    return payload


def _ok_payload(uid: int, result=None, extra=None) -> dict:
    payload = {"ok": True, "result": result or {}}
    payload.update(_snapshot(uid))
    if extra:
        payload.update(extra)
    if isinstance(result, dict) and result.get("leveled_up"):
        payload["levelUp"] = {
            "level": result.get("new_level"),
            "hpGain": 15,
            "mpGain": 10,
            "goldGain": result.get("gold_gained") or 0,
        }
    return payload


def _equip_item(uid: int, item_id: str, equipped: bool) -> dict:
    conn = db.get_conn()
    try:
        row = conn.execute(
            "SELECT * FROM inventory WHERE user_id=? AND item_id=?",
            (uid, item_id),
        ).fetchone()
        if not row:
            return {"ok": False, "msg": "not_found"}
        item = db.SHOP_ITEMS.get(item_id) or {}
        itype = item.get("type")
        if equipped and itype:
            conn.execute(
                """UPDATE inventory SET equipped=0 WHERE user_id=? AND item_id IN
                   (SELECT item_id FROM inventory WHERE user_id=?)""",
                (uid, uid),
            )
            # only unequip same type
            rows = conn.execute("SELECT item_id FROM inventory WHERE user_id=?", (uid,)).fetchall()
            for r in rows:
                meta = db.SHOP_ITEMS.get(r["item_id"]) or {}
                if meta.get("type") == itype:
                    conn.execute(
                        "UPDATE inventory SET equipped=0 WHERE user_id=? AND item_id=?",
                        (uid, r["item_id"]),
                    )
        conn.execute(
            "UPDATE inventory SET equipped=? WHERE user_id=? AND item_id=?",
            (1 if equipped else 0, uid, item_id),
        )
        conn.commit()
    finally:
        conn.close()
    if hasattr(db, "recalculate_all_buffs"):
        db.recalculate_all_buffs(uid)
    return {"ok": True}


def _ensure_user() -> int | None:
    uid = _state.get("user_id")
    if uid:
        return int(uid)
    try:
        conn = db.get_conn()
        row = conn.execute("SELECT id FROM users ORDER BY id LIMIT 1").fetchone()
        conn.close()
        if row:
            _state["user_id"] = int(row["id"])
            return int(row["id"])
    except Exception:
        return None
    return None


def _auth_ok(handler) -> bool:
    uid = _ensure_user()
    if not uid:
        return False
    token = _state.get("token")
    hdr = handler.headers.get("Authorization") or ""
    qtoken = parse_qs(urlparse(handler.path).query).get("token", [None])[0]
    given = None
    if hdr.lower().startswith("bearer "):
        given = hdr[7:].strip()
    elif qtoken:
        given = qtoken
    if token and given and given != token:
        return False
    return True


def _guild_id(uid: int):
    u = db.get_user(uid) or {}
    return u.get("guild_id")


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        return

    def _cors(self):
        origin = self.headers.get("Origin") or "*"
        self.send_header("Access-Control-Allow-Origin", origin)
        self.send_header("Access-Control-Allow-Headers", "Authorization, Content-Type")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Credentials", "true")

    def _send(self, code, payload, content="application/json"):
        body = payload if isinstance(payload, bytes) else _json_bytes(payload)
        self.send_response(code)
        self._cors()
        self.send_header("Content-Type", content + "; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        self.send_response(204)
        self._cors()
        self.end_headers()

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path.rstrip("/") or "/"
        qs = parse_qs(parsed.query)

        if path == "/api/health":
            self._send(200, {"ok": True, "phase": 1})
            return

        if path.startswith("/assets/") or path in ("/", "/index.html"):
            self._serve_static(path)
            return

        # Stream a local library audio file to the browser <audio> element.
        # The path is validated to live inside the CraftLife Music folder, so a
        # web client can "play a local file" (parity with PyQt QMediaPlayer),
        # and stays local — the file is never uploaded anywhere.
        if path == "/music/stream":
            file_path = (qs.get("path") or [""])[0]
            self._serve_audio(file_path)
            return

        if not _auth_ok(self) and path.startswith("/api/") and path != "/api/health":
            if path != "/api/i18n":
                self._send(401, {"ok": False, "error": "unauthorized"})
                return

        uid = _state.get("user_id")
        if path == "/api/i18n":
            lang = (qs.get("lang") or ["id"])[0]
            if lang not in ("id", "en"):
                lang = "id"
            keys = qs.get("keys")
            out = {}
            source_keys = keys[0].split(",") if keys else WEB_I18N_KEYS
            for k in source_keys:
                k = k.strip()
                if k:
                    out[k] = get_text(k, lang)
            self._send(200, {"lang": lang, "messages": out})
            return

        routes = {
            "/api/me": lambda: {"ok": True, "user": _row_user(db.get_user(uid))},
            "/api/habits": lambda: {"ok": True, "habits": [_map_habit(h) for h in db.get_habits(uid)]},
            "/api/dailies": lambda: {"ok": True, "dailies": [_map_daily(d) for d in db.get_dailies(uid)]},
            "/api/todos": lambda: {"ok": True, "quests": [_map_todo(t) for t in db.get_todos(uid)]},
            "/api/inventory": lambda: {"ok": True, "inventory": [_map_inv(r) for r in db.get_inventory(uid)]},
            "/api/pets": lambda: {"ok": True, "userPets": [_map_pet(r) for r in db.get_user_pets(uid)]},
            "/api/achievements": lambda: {"ok": True, "achievements": [_map_ach(a) for a in db.get_user_achievements(uid)]},
            "/api/catalog/shop": lambda: {"ok": True, "items": _shop_catalog()},
            "/api/catalog/pets": lambda: {"ok": True, "pets": _pet_catalog()},
            "/api/catalog/bosses": lambda: {"ok": True, "bosses": _boss_catalog()},
            "/api/catalog/recipes": lambda: {"ok": True, "recipes": _recipe_catalog()},
            "/api/catalog/currency": lambda: {"ok": True, "rates": getattr(db, "CURRENCY_RATES", {"IDR": 1})},
            "/api/profile/talents": lambda: {"ok": True, "talents": db.get_talent_state(uid)},
            "/api/dashboard/widgets": lambda: {"ok": True, "widgets": db.get_dashboard_widgets(uid)},
            "/api/year-wrapped": lambda: {"ok": True, "wrapped": db.get_year_wrapped(uid)},
            "/api/leaderboard": lambda: {
                "ok": True,
                "linked": bool(db.get_cloud_user_link(uid)),
                "leaderboard": [
                    {
                        "id": str(r.get("id")),
                        "username": r.get("username") or "",
                        "displayName": r.get("display_name") or r.get("username") or "",
                        "level": int(r.get("level") or 1),
                        "xp": int(r.get("total_xp_earned") or 0),
                        "gold": int(r.get("gold") or 0),
                        "sportLevel": int(r.get("sport_level") or 1),
                        "pets": int(r.get("pet_count") or 0),
                        "rebirth": int(r.get("rebirth_count") or 0),
                        "title": r.get("selected_title") or "",
                        "cloudUserId": r.get("cloud_user_id") or "",
                        "presence": (
                            (db.get_cached_presence(r.get("cloud_user_id")) or {}).get("status")
                            if r.get("cloud_user_id")
                            else "offline"
                        ),
                    }
                    for r in (db.get_leaderboard_for_user(uid) or db.get_leaderboard(50) or [])
                ],
            },
        }
        if path in routes:
            self._send(200, routes[path]())
            return
        if path == "/api/holidays":
            year = int((qs.get("year") or [0])[0] or 0) or None
            try:
                import holidays as hol
                from datetime import datetime as _dt
                y = year or _dt.now().year
                data = hol.get_holidays_for_year(y) or {}
            except Exception:
                data = {}
                y = year or 0
            items = []
            for ds, names in data.items():
                if isinstance(names, (list, tuple)) and len(names) >= 2:
                    nid, nen = names[0], names[1]
                else:
                    nid = nen = str(names)
                items.append({"date": ds, "nameId": nid, "nameEn": nen, "type": "national"})
            self._send(200, {"ok": True, "year": y, "holidays": items})
            return
        # Serve a Love Space photo image (BLOB) to the browser <img>. Visibility
        # (owner / shared-with-couple) is enforced inside get_love_space_photo.
        if path == "/api/love/photo/image":
            pid = (qs.get("id") or [None])[0]
            if not pid:
                self._send(400, {"ok": False, "error": "id"})
                return
            try:
                ph = db.get_love_space_photo(uid, int(pid))
            except (ValueError, TypeError):
                ph = None
            if not ph:
                self._send(404, {"ok": False, "error": "not_found"})
                return
            blob = ph.get("image_data")
            mime = (ph.get("mime_type") or "image/jpeg").split(";")[0].strip()
            self.send_response(200)
            self._cors()
            self.send_header("Content-Type", mime)
            self.send_header("Content-Length", str(len(blob)))
            self.send_header("Cache-Control", "private, max-age=3600")
            self.end_headers()
            self.wfile.write(blob)
            return

        extra = life_api.handle_get(path, uid)
        if extra is not None:
            self._send(200, extra)
            return
        extra = studio_api.handle_get(path, uid, qs)
        if extra is not None:
            self._send(200, extra)
            return
        if path.startswith("/api/cloud"):
            try:
                import cloud_api
                extra = cloud_api.handle_get(path, uid)
            except Exception as e:
                self._send(400, {"ok": False, "error": str(e)})
                return
            if extra is not None:
                code = 200 if extra.get("ok", True) else 400
                self._send(code, extra)
                return

        if path == "/api/tracker/export":
            try:
                data = db.export_tracker_data(uid)
            except Exception as e:
                self._send(400, {"ok": False, "error": str(e)})
                return
            self._send(200, {"ok": True, "tracker": data})
            return
        if path == "/api/update/check":
            info = {"ok": True, "current": None, "update": None}
            try:
                import updater
                info["current"] = getattr(updater, "APP_VERSION", None)
                info["update"] = updater.check_for_update()
            except Exception as e:
                info["error"] = str(e)
            self._send(200, info)
            return

        if path == "/api/bootstrap":
            snap = _snapshot(uid)
            snap["ok"] = True
            snap["shop"] = _shop_catalog()
            snap["petCatalog"] = _pet_catalog()
            snap["bossCatalog"] = _boss_catalog()
            snap["recipes"] = _recipe_catalog()
            self._send(200, snap)
            return

        self._serve_static(path)

    def do_POST(self):
        parsed = urlparse(self.path)
        path = parsed.path.rstrip("/")
        length = int(self.headers.get("Content-Length") or 0)
        raw = self.rfile.read(length) if length else b"{}"
        try:
            body = json.loads(raw.decode("utf-8") or "{}")
        except json.JSONDecodeError:
            body = {}

        if path == "/api/auth/reset":
            username = (body.get("username") or "").strip()
            code = (body.get("code") or "").strip()
            new_pw = body.get("password") or body.get("newPassword") or ""
            try:
                conn = db.get_conn()
                row = conn.execute("SELECT id FROM users WHERE username=?", (username,)).fetchone()
                conn.close()
                if not row:
                    self._send(400, {"ok": False, "error": "user_not_found"})
                    return
                uid = int(row["id"])
                if not db.verify_backup_code(uid, code):
                    self._send(400, {"ok": False, "error": "invalid_code"})
                    return
                result = db.reset_password_with_backup_code(uid, new_pw)
                self._send(200, {"ok": True, "result": result if isinstance(result, dict) else {"ok": True}})
            except Exception as e:
                self._send(400, {"ok": False, "error": str(e)})
            return
        if path in ("/api/auth/login", "/api/auth/register"):
            try:
                if path.endswith("register"):
                    result = db.register_user(
                        body.get("username") or "",
                        body.get("password") or "",
                        display_name=body.get("displayName") or "",
                    )
                    if result.get("ok"):
                        result = db.login_user(body.get("username") or "", body.get("password") or "")
                else:
                    result = db.login_user(body.get("username") or "", body.get("password") or "")
                if not result.get("ok"):
                    self._send(401, {"ok": False, "error": result.get("msg") or "login_failed", "result": result})
                    return
                user = result.get("user") or {}
                uid = int(user.get("id"))
                token = db.create_session_token(uid)
                configure(uid, token)
                self._send(200, {"ok": True, "token": token, "user": _row_user(db.get_user(uid))})
            except Exception as e:
                self._send(400, {"ok": False, "error": str(e)})
            return

        if path == "/api/profile/rebirth":
            if not _auth_ok(self):
                self._send(401, {"ok": False, "error": "unauthorized"})
                return
            uid = _state.get("user_id")
            try:
                result = db.perform_rebirth(uid)
            except Exception as e:
                self._send(400, {"ok": False, "error": str(e)})
                return
            self._send(200, _ok_payload(uid, result if isinstance(result, dict) else {"ok": True}))
            return
        if path == "/api/profile/redeem":
            if not _auth_ok(self):
                self._send(401, {"ok": False, "error": "unauthorized"})
                return
            uid = _state.get("user_id")
            try:
                result = db.redeem_code(uid, (body.get("code") or "").strip())
            except Exception as e:
                self._send(400, {"ok": False, "error": str(e)})
                return
            self._send(200, _ok_payload(uid, result if isinstance(result, dict) else {"ok": True}))
            return
        if path == "/api/profile/talent":
            if not _auth_ok(self):
                self._send(401, {"ok": False, "error": "unauthorized"})
                return
            uid = _state.get("user_id")
            try:
                result = db.unlock_talent(uid, body.get("key") or body.get("talentKey") or "")
            except Exception as e:
                self._send(400, {"ok": False, "error": str(e)})
                return
            self._send(200, _ok_payload(uid, result if isinstance(result, dict) else {"ok": True}))
            return
        if path == "/api/dashboard/widgets":
            if not _auth_ok(self):
                self._send(401, {"ok": False, "error": "unauthorized"})
                return
            uid = _state.get("user_id")
            widgets = body.get("widgets")
            if not isinstance(widgets, list):
                self._send(400, {"ok": False, "error": "widgets_required"})
                return
            try:
                db.set_dashboard_widgets(uid, widgets)
            except Exception as e:
                self._send(400, {"ok": False, "error": str(e)})
                return
            self._send(200, _ok_payload(uid, {"ok": True}))
            return
        if path == "/api/profile/backup-codes":
            if not _auth_ok(self):
                self._send(401, {"ok": False, "error": "unauthorized"})
                return
            uid = _state.get("user_id")
            try:
                result = db.generate_backup_codes(uid)
            except Exception as e:
                self._send(400, {"ok": False, "error": str(e)})
                return
            self._send(200, {"ok": True, "result": result})
            return
        if path == "/api/profile/security":
            if not _auth_ok(self):
                self._send(401, {"ok": False, "error": "unauthorized"})
                return
            uid = _state.get("user_id")
            try:
                result = db.set_security_question(uid, body.get("question") or "", body.get("answer") or "")
            except Exception as e:
                self._send(400, {"ok": False, "error": str(e)})
                return
            self._send(200, {"ok": True, "result": result})
            return
        if path == "/api/profile/password":
            if not _auth_ok(self):
                self._send(401, {"ok": False, "error": "unauthorized"})
                return
            uid = _state.get("user_id")
            try:
                result = db.change_password(uid, body.get("oldPassword") or "", body.get("newPassword") or body.get("password") or "")
            except Exception as e:
                self._send(400, {"ok": False, "error": str(e)})
                return
            self._send(200, {"ok": True, "result": result})
            return
        if path == "/api/profile/lock":
            if not _auth_ok(self):
                self._send(401, {"ok": False, "error": "unauthorized"})
                return
            uid = _state.get("user_id")
            try:
                if body.get("unlock"):
                    result = db.unlock_account(uid, body.get("password") or "")
                else:
                    result = db.lock_account(uid, body.get("password") or "")
            except Exception as e:
                self._send(400, {"ok": False, "error": str(e)})
                return
            self._send(200, {"ok": True, "result": result})
            return
        if path == "/api/settings":
            if not _auth_ok(self):
                self._send(401, {"ok": False, "error": "unauthorized"})
                return
            uid = _state.get("user_id")
            lang = body.get("language") or body.get("lang")
            if lang in ("id", "en"):
                try:
                    db.set_user_language(uid, lang)
                except Exception:
                    pass
            theme = body.get("theme")
            if theme and hasattr(db, "set_user_theme"):
                try:
                    db.set_user_theme(uid, theme)
                except Exception:
                    pass
            kw = {}
            if body.get("displayName") or body.get("name"):
                kw["display_name"] = body.get("displayName") or body.get("name")
            if "bio" in body:
                kw["bio"] = body.get("bio") or ""
            if body.get("avatar") or body.get("avatarEmoji"):
                kw["avatar_emoji"] = body.get("avatar") or body.get("avatarEmoji")
            cls = body.get("heroClass") or body.get("avatarClass")
            if cls:
                kw["avatar_class"] = str(cls).lower()
            if kw:
                try:
                    db.update_user(uid, **kw)
                except Exception:
                    pass
            if "soundEnabled" in body:
                try:
                    db.set_user_settings(uid, sound_enabled=1 if body.get("soundEnabled") else 0)
                except Exception:
                    pass
            cur = body.get("currency")
            if cur:
                try:
                    db.set_user_currency(uid, str(cur).upper())
                except Exception:
                    pass
            if body.get("fontScale") is not None:
                try:
                    db.set_font_scale(uid, int(body.get("fontScale") or 100))
                except Exception:
                    pass
            if "highContrast" in body:
                try:
                    db.set_high_contrast(uid, bool(body.get("highContrast")))
                except Exception:
                    pass
            if body.get("avatarColor"):
                try:
                    db.update_user(uid, avatar_color=body.get("avatarColor"))
                except Exception:
                    pass
            if "onboardingDone" in body:
                try:
                    if body.get("onboardingDone"):
                        db.mark_onboarding_done(uid)
                except Exception:
                    pass
            self._send(200, _ok_payload(uid, {"ok": True, "user": _row_user(db.get_user(uid))}))
            return

        if path == "/api/tracker/import":
            if not _auth_ok(self):
                self._send(401, {"ok": False, "error": "unauthorized"})
                return
            uid = _state.get("user_id")
            payload = body.get("tracker") or body
            try:
                db.import_tracker_data(uid, payload, preserve_progress=bool(body.get("preserveProgress")))
            except Exception as e:
                self._send(400, {"ok": False, "error": str(e)})
                return
            self._send(200, _ok_payload(uid, {"ok": True}))
            return

        if path == "/api/update/check":
            info = {"ok": True, "current": None, "update": None}
            try:
                import updater
                info["current"] = getattr(updater, "APP_VERSION", None)
                chk = updater.check_for_update()
                info["update"] = chk
            except Exception as e:
                info["error"] = str(e)
            self._send(200, info)
            return

        if not _auth_ok(self):
            self._send(401, {"ok": False, "error": "unauthorized"})
            return
        uid = _state.get("user_id")
        parts = [p for p in path.split("/") if p]

        def fail(e):
            self._send(400, {"ok": False, "error": str(e)})

        try:
            # tasks reorder (drag & drop) — one call handles reorder-in-folder + move across folders
            if path == "/api/tasks/reorder":
                mode = str(body.get("mode") or "habit")
                items = body.get("items")
                if not isinstance(items, list):
                    self._send(400, {"ok": False, "error": "items_required"})
                    return
                result = db.reorder_tasks(uid, mode, items)
                if not result.get("ok"):
                    self._send(400, {"ok": False, "error": result.get("msg") or "reorder_failed", **_snapshot(uid)})
                    return
                self._send(200, _ok_payload(uid, result))
                return
            if path == "/api/trash/restore":
                result = db.restore_task_from_trash(uid, body.get("trashId") or body.get("trash_id"))
                if not result.get("ok"):
                    self._send(400, {"ok": False, "error": result.get("msg") or "restore_failed", **_snapshot(uid)})
                    return
                self._send(200, _ok_payload(uid, result))
                return

            # habits
            if path == "/api/habits":
                name = (body.get("title") or body.get("name") or "").strip()
                if not name:
                    self._send(400, {"ok": False, "error": "empty"})
                    return
                db.add_habit(
                    uid, name,
                    icon=body.get("icon") or "⚔️",
                    difficulty=body.get("difficulty") or "medium",
                    positive=1 if body.get("isPositive", True) else 0,
                    negative=1 if body.get("isNegative") else 0,
                    notes=body.get("notes") or "",
                )
                fid = body.get("folderId") or body.get("folder_id")
                if fid not in (None, "", "null"):
                    try:
                        conn = db.get_conn()
                        row = conn.execute(
                            "SELECT id FROM habits WHERE user_id=? ORDER BY id DESC LIMIT 1", (uid,)
                        ).fetchone()
                        conn.close()
                        if row:
                            db.update_habit(int(row["id"]), uid, folder_id=int(fid))
                    except Exception:
                        pass
                self._send(200, _ok_payload(uid))
                return
            if len(parts) >= 4 and parts[1] == "habits":
                hid = int(parts[2])
                action = parts[3]
                if action == "complete":
                    direction = "up" if body.get("positive", True) else "down"
                    result = db.complete_habit(uid, hid, direction=direction)
                    self._send(200, _ok_payload(uid, result))
                    return
                if action == "delete":
                    result = db.delete_habit(uid, hid)
                    self._send(200, _ok_payload(uid, result if isinstance(result, dict) else {"ok": True, "trash_id": None}))
                    return
                if action == "duplicate":
                    result = db.duplicate_habit(uid, hid)
                    self._send(200, _ok_payload(uid, result if isinstance(result, dict) else {}))
                    return
                if action == "update":
                    kw = {}
                    if body.get("title") or body.get("name"):
                        kw["name"] = body.get("title") or body.get("name")
                    if body.get("difficulty"):
                        kw["difficulty"] = body.get("difficulty")
                    if body.get("icon"):
                        kw["icon"] = body.get("icon")
                    if "notes" in body:
                        kw["notes"] = body.get("notes") or ""
                    if "isPositive" in body:
                        kw["positive"] = 1 if body.get("isPositive") else 0
                    if "isNegative" in body:
                        kw["negative"] = 1 if body.get("isNegative") else 0
                    if "folderId" in body or "folder_id" in body:
                        fid = body.get("folderId") if "folderId" in body else body.get("folder_id")
                        kw["folder_id"] = int(fid) if fid not in (None, "", "null") else None
                    db.update_habit(hid, uid, **kw)
                    self._send(200, _ok_payload(uid))
                    return

            if path == "/api/dailies":
                name = (body.get("title") or body.get("name") or "").strip()
                if not name:
                    self._send(400, {"ok": False, "error": "empty"})
                    return
                days = body.get("repeatDays") or []
                repeat = ",".join(str(int(x)) for x in days) if days else ""
                db.add_daily(
                    uid, name,
                    icon=body.get("icon") or "📅",
                    difficulty=body.get("difficulty") or "medium",
                    notes=body.get("notes") or "",
                    repeat_days=repeat,
                )
                fid = body.get("folderId") or body.get("folder_id")
                if fid not in (None, "", "null"):
                    try:
                        conn = db.get_conn()
                        row = conn.execute(
                            "SELECT id FROM dailies WHERE user_id=? ORDER BY id DESC LIMIT 1", (uid,)
                        ).fetchone()
                        conn.close()
                        if row:
                            db.set_item_folder(uid, "daily", int(row["id"]), int(fid))
                    except Exception:
                        pass
                self._send(200, _ok_payload(uid))
                return
            if len(parts) >= 4 and parts[1] == "dailies":
                did = int(parts[2])
                action = parts[3]
                if action == "complete":
                    result = db.complete_daily(uid, did)
                    self._send(200, _ok_payload(uid, result))
                    return
                if action == "fail":
                    result = db.fail_daily(uid, did)
                    self._send(200, _ok_payload(uid, result))
                    return
                if action == "freeze":
                    result = db.add_freeze_to_daily(uid, did)
                    self._send(200, _ok_payload(uid, result))
                    return
                if action == "delete":
                    result = db.delete_daily(uid, did)
                    self._send(200, _ok_payload(uid, result if isinstance(result, dict) else {"ok": True, "trash_id": None}))
                    return
                if action == "duplicate":
                    result = db.duplicate_daily(uid, did)
                    self._send(200, _ok_payload(uid, result if isinstance(result, dict) else {}))
                    return
                if action == "update":
                    kw = {}
                    if body.get("title") or body.get("name"):
                        kw["name"] = body.get("title") or body.get("name")
                    if body.get("difficulty"):
                        kw["difficulty"] = body.get("difficulty")
                    if "notes" in body:
                        kw["notes"] = body.get("notes") or ""
                    if body.get("repeatDays") is not None:
                        days = body.get("repeatDays") or []
                        kw["repeat_days"] = ",".join(str(int(x)) for x in days)
                    if "folderId" in body or "folder_id" in body:
                        fid = body.get("folderId") if "folderId" in body else body.get("folder_id")
                        kw["folder_id"] = int(fid) if fid not in (None, "", "null") else None
                    db.update_daily(did, uid, **kw)
                    self._send(200, _ok_payload(uid))
                    return

            if path == "/api/todos":
                name = (body.get("title") or body.get("name") or "").strip()
                if not name:
                    self._send(400, {"ok": False, "error": "empty"})
                    return
                db.add_todo(
                    uid, name,
                    priority=body.get("difficulty") or "medium",
                    icon=body.get("icon") or "📜",
                    due_date=body.get("dueDate"),
                    notes=body.get("notes") or "",
                )
                fid = body.get("folderId") or body.get("folder_id")
                if fid not in (None, "", "null"):
                    try:
                        conn = db.get_conn()
                        row = conn.execute(
                            "SELECT id FROM todos WHERE user_id=? ORDER BY id DESC LIMIT 1", (uid,)
                        ).fetchone()
                        conn.close()
                        if row:
                            db.update_todo(int(row["id"]), uid, folder_id=int(fid))
                    except Exception:
                        pass
                self._send(200, _ok_payload(uid))
                return
            if len(parts) >= 4 and parts[1] == "todos":
                tid = int(parts[2])
                action = parts[3]
                if action == "complete":
                    result = db.complete_todo(uid, tid)
                    self._send(200, _ok_payload(uid, result))
                    return
                if action == "delete":
                    result = db.delete_todo(uid, tid)
                    self._send(200, _ok_payload(uid, result if isinstance(result, dict) else {"ok": True, "trash_id": None}))
                    return
                if action == "duplicate":
                    result = db.duplicate_todo(uid, tid)
                    self._send(200, _ok_payload(uid, result if isinstance(result, dict) else {}))
                    return
                if action == "update":
                    kw = {}
                    if body.get("title") or body.get("name"):
                        kw["name"] = body.get("title") or body.get("name")
                    if body.get("difficulty") or body.get("priority"):
                        kw["priority"] = body.get("difficulty") or body.get("priority")
                    if body.get("icon"):
                        kw["icon"] = body.get("icon")
                    if "notes" in body:
                        kw["notes"] = body.get("notes") or ""
                    if "dueDate" in body:
                        kw["due_date"] = body.get("dueDate") or None
                    if "folderId" in body or "folder_id" in body:
                        fid = body.get("folderId") if "folderId" in body else body.get("folder_id")
                        kw["folder_id"] = int(fid) if fid not in (None, "", "null") else None
                    db.update_todo(tid, uid, **kw)
                    self._send(200, _ok_payload(uid))
                    return

            if path == "/api/shop/buy":
                item_id = body.get("itemId") or body.get("item_id")
                idem = str(body.get("idempotencyKey") or body.get("idempotency_key") or uuid.uuid4())
                qty = int(body.get("quantity") or 1)
                import cloud_api
                if cloud_api.is_shop_cloud(uid):
                    try:
                        result = cloud_api.shop_cloud_buy(uid, item_id, qty, idem)
                    except Exception as e:
                        self._send(400, {"ok": False, "error": str(e), **_snapshot(uid)})
                        return
                    self._send(200, _ok_payload(uid, result))
                    return
                result = db.buy_item(uid, item_id)
                if not result.get("ok"):
                    self._send(400, {"ok": False, "error": result.get("msg") or "buy_failed", **_snapshot(uid)})
                    return
                self._send(200, _ok_payload(uid, result))
                return
            if path == "/api/shop/sell":
                item_id = body.get("itemId") or body.get("item_id")
                row_id = body.get("rowId")
                if not row_id:
                    for r in db.get_inventory(uid):
                        if r.get("item_id") == item_id:
                            row_id = r.get("id")
                            break
                result = db.sell_item(uid, row_id, quantity=int(body.get("quantity") or 1))
                self._send(200, _ok_payload(uid, result))
                return
            if path == "/api/shop/use":
                result = db.use_item(uid, body.get("itemId") or body.get("item_id"))
                self._send(200, _ok_payload(uid, result))
                return
            if path == "/api/shop/equip":
                item_id = body.get("itemId") or body.get("item_id")
                equipped = bool(body.get("equipped", True))
                import cloud_api
                if cloud_api.is_shop_cloud(uid):
                    try:
                        result = cloud_api.shop_cloud_equip(uid, item_id, equipped)
                    except Exception as e:
                        self._send(400, {"ok": False, "error": str(e), **_snapshot(uid)})
                        return
                    self._send(200, _ok_payload(uid, result))
                    return
                result = _equip_item(uid, item_id, equipped)
                if not result.get("ok"):
                    self._send(400, {"ok": False, "error": result.get("msg") or "equip_failed", **_snapshot(uid)})
                    return
                self._send(200, _ok_payload(uid, result))
                return
            if path == "/api/shop/craft":
                rid = body.get("recipeId") or body.get("resultItemId")
                idem = str(body.get("idempotencyKey") or body.get("idempotency_key") or uuid.uuid4())
                import cloud_api
                if cloud_api.is_shop_cloud(uid):
                    try:
                        result = cloud_api.shop_cloud_craft(uid, rid, idem)
                    except Exception as e:
                        self._send(400, {"ok": False, "error": str(e), **_snapshot(uid)})
                        return
                    self._send(200, _ok_payload(uid, result))
                    return
                result = db.craft_item(uid, rid)
                if not result.get("ok"):
                    self._send(400, {"ok": False, "error": result.get("msg") or "craft_failed", **_snapshot(uid)})
                    return
                self._send(200, _ok_payload(uid, result))
                return
            if path == "/api/shop/enchant":
                item_id = body.get("itemId") or body.get("item_id")
                idem = str(body.get("idempotencyKey") or body.get("idempotency_key") or uuid.uuid4())
                import cloud_api
                if cloud_api.is_shop_cloud(uid):
                    try:
                        result = cloud_api.shop_cloud_enchant(uid, item_id, idem)
                    except Exception as e:
                        self._send(400, {"ok": False, "error": str(e), **_snapshot(uid)})
                        return
                    self._send(200, _ok_payload(uid, result))
                    return
                result = db.enchant_item(uid, item_id)
                if not result.get("ok"):
                    self._send(400, {"ok": False, "error": result.get("msg") or "enchant_failed", **_snapshot(uid)})
                    return
                self._send(200, _ok_payload(uid, result))
                return

            if path == "/api/pets/adopt":
                result = db.adopt_pet(uid, body.get("petId"))
                self._send(200, _ok_payload(uid, result))
                return
            if path == "/api/pets/feed":
                result = db.feed_pet(uid, body.get("petId"))
                self._send(200, _ok_payload(uid, result))
                return
            if path == "/api/pets/train":
                result = db.train_pet(uid, body.get("petId"))
                self._send(200, _ok_payload(uid, result))
                return
            if path == "/api/pets/equip":
                result = db.equip_pet(uid, body.get("petId"))
                self._send(200, _ok_payload(uid, result))
                return
            if path == "/api/pets/unequip":
                result = db.unequip_pet(uid, body.get("petId"))
                self._send(200, _ok_payload(uid, result))
                return

            if path == "/api/boss/start":
                u = db.get_user(uid)
                gid = u.get("guild_id") or 0
                result = db.start_boss(gid, body.get("bossId"), u)
                self._send(200, _ok_payload(uid, result, extra={"activeBossId": body.get("bossId")}))
                return
            if path == "/api/boss/attack":
                u = db.get_user(uid)
                gid = u.get("guild_id") or 0
                action = body.get("action") or "light"
                result = db.attack_boss(uid, gid, action=action)
                self._send(200, _ok_payload(uid, result))
                return
            if path == "/api/boss/flee":
                self._send(200, _ok_payload(uid, {"ok": True, "fled": True}))
                return
            if path == "/api/skill/use":
                result = db.use_class_skill(uid)
                if not result.get("ok"):
                    self._send(400, {"ok": False, "error": result.get("msg") or "skill_failed", **_snapshot(uid)})
                    return
                self._send(200, _ok_payload(uid, result))
                return

            if len(parts) >= 4 and parts[1] == "achievements" and parts[3] == "claim":
                aid = parts[2]
                try:
                    aid_int = int(aid)
                except ValueError:
                    aid_int = aid
                result = db.claim_achievement_reward(uid, aid_int)
                self._send(200, _ok_payload(uid, result))
                return

            life = life_api.handle_post(path, uid, body, parts)
            if life is not None:
                if life.get("skip_snap"):
                    self._send(200, {"ok": True, "result": life.get("result")})
                    return
                self._send(200, _ok_payload(uid, life.get("result")))
                return
            studio = studio_api.handle_post(path, uid, body, parts)
            if studio is not None:
                if studio.get("skip_snap"):
                    payload = {"ok": True, "result": studio.get("result")}
                    if isinstance(studio.get("result"), dict):
                        payload.update(studio.get("result"))
                    self._send(200, payload)
                    return
                self._send(200, _ok_payload(uid, studio.get("result")))
                return
            if path == "/api/admin/debug":
                u = db.get_user(uid) or {}
                if not u.get("is_admin"):
                    self._send(403, {"ok": False, "error": "forbidden"})
                    return
                action = body.get("action") or ""
                result = {"ok": True}
                if action == "xp":
                    result = db.gain_xp_gold(uid, int(body.get("amount") or 0), 0)
                elif action == "gold":
                    result = db.gain_xp_gold(uid, 0, int(body.get("amount") or 0))
                elif action == "fill":
                    db.update_user(uid, hp=u.get("max_hp"), mp=u.get("max_mp"))
                elif action == "maxLevel":
                    target = 50
                    needed = 0
                    for lvl in range(int(u.get("level") or 1), target):
                        needed += lvl * 150
                    result = db.gain_xp_gold(uid, needed, 0)
                elif action == "completeTasks":
                    for h in db.get_habits(uid):
                        if not h.get("done_today"):
                            db.complete_habit(uid, h["id"], "up")
                    for d in db.get_dailies(uid):
                        if not d.get("done_today"):
                            db.complete_daily(uid, d["id"])
                    for t in db.get_todos(uid):
                        if not t.get("done"):
                            db.complete_todo(uid, t["id"])
                elif action == "petLevel":
                    result = db.admin_level_up_all_pets(uid)
                elif action == "petExp":
                    result = db.admin_add_exp_all_pets(uid, int(body.get("amount") or 100)) if hasattr(db, "admin_add_exp_all_pets") else {"ok": False}
                elif action == "feedPets":
                    result = db.admin_feed_all_pets(uid) if hasattr(db, "admin_feed_all_pets") else {"ok": False}
                self._send(200, _ok_payload(uid, result if isinstance(result, dict) else {"ok": True}))
                return
            if path.startswith("/api/cloud"):
                import cloud_api
                extra = cloud_api.handle_post(path, uid, body)
                if extra is not None:
                    code = 200 if extra.get("ok", True) else 400
                    self._send(code, extra)
                    return
        except Exception as e:
            fail(e)
            return

        self._send(404, {"ok": False, "error": "not_found"})

    def _serve_audio(self, file_path: str):
        """Serve a local audio file with HTTP Range support (for <audio> seek).

        Only files inside the CraftLife Music library dir are reachable; nothing
        is uploaded/streamed over the internet beyond the local loopback.
        """
        import mimetypes
        from http import HTTPStatus
        try:
            import music_downloader as md
            lib_dir = os.path.realpath(md.get_download_dir())
        except Exception:
            self._send(404, {"ok": False, "error": "no_music_dir"})
            return
        if not file_path:
            self._send(404, {"ok": False, "error": "bad_path"})
            return
        real = os.path.realpath(file_path)
        if not real.startswith(lib_dir + os.sep):
            self._send(403, {"ok": False, "error": "forbidden"})
            return
        if not os.path.isfile(real):
            self._send(404, {"ok": False, "error": "not_found"})
            return
        size = os.path.getsize(real)
        ctype = mimetypes.guess_type(real)[0] or "audio/mpeg"
        rng = self.headers.get("Range")
        start = 0
        end = size - 1
        if rng:
            try:
                spec = rng.replace("bytes=", "").strip()
                if "-" in spec:
                    a, b = spec.split("-", 1)
                    start = int(a) if a else 0
                    end = (int(b) if b else end)
                else:
                    start = int(spec)
            except (ValueError, IndexError):
                start = 0
                end = size - 1
            start = max(0, min(start, size - 1))
            end = max(start, min(end, size - 1))
        length = end - start + 1
        self.send_response(206 if rng else 200)
        self._cors()
        self.send_header("Content-Type", ctype)
        self.send_header("Accept-Ranges", "bytes")
        self.send_header("Content-Length", str(length))
        if rng:
            self.send_header("Content-Range", f"bytes {start}-{end}/{size}")
        self.end_headers()
        try:
            with open(real, "rb") as f:
                f.seek(start)
                remaining = length
                while remaining > 0:
                    chunk = f.read(min(65536, remaining))
                    if not chunk:
                        break
                    self.wfile.write(chunk)
                    remaining -= len(chunk)
        except (BrokenPipeError, ConnectionResetError):
            pass

    def _serve_static(self, path: str):
        try:
            from web_shell import web_dist_candidates
            cands = web_dist_candidates()
        except Exception:
            here = os.path.dirname(os.path.abspath(__file__))
            cands = [
                os.path.join(here, "web", "dist"),
                os.path.join(os.path.dirname(here), "web", "dist"),
            ]
            meipass = getattr(__import__("sys"), "_MEIPASS", None)
            if meipass:
                cands.insert(0, os.path.join(meipass, "web", "dist"))
        root = next((c for c in cands if os.path.isdir(c)), cands[-1])
        if not os.path.isdir(root) or not os.path.isfile(os.path.join(root, "index.html")):
            html = (
                "<!DOCTYPE html><html><head><meta charset='utf-8'><title>CraftLife</title></head>"
                "<body style='font-family:Segoe UI,sans-serif;background:#0f172a;color:#e2e8f0;padding:48px'>"
                "<h1>UI React belum di-build</h1>"
                "<p>Folder <code>web/dist</code> kosong. API di port ini hidup, tapi tidak ada index.html.</p>"
                "<ol>"
                "<li>Buka PowerShell di folder <code>web</code></li>"
                "<li><code>npm install</code></li>"
                "<li><code>npm run build</code></li>"
                "<li>Jalankan ulang CraftLife</li>"
                "</ol>"
                "<p>Jangan pakai <code>npm run dev</code> untuk jendela exe — WebEngine memuat "
                "<code>http://127.0.0.1:8765/</code>.</p>"
                "</body></html>"
            ).encode("utf-8")
            self._send(200, html, "text/html")
            return
        if path in ("/", "", "/index.html"):
            rel = "index.html"
        else:
            rel = path.lstrip("/")
        full = os.path.normpath(os.path.join(root, rel))
        if not full.startswith(os.path.normpath(root)):
            self._send(403, {"ok": False})
            return
        if not os.path.isfile(full):
            full = os.path.join(root, "index.html")
        lower = full.lower()
        ctype = "text/html"
        if lower.endswith(".js") or lower.endswith(".mjs"):
            ctype = "application/javascript"
        elif lower.endswith(".css"):
            ctype = "text/css"
        elif lower.endswith(".ico"):
            ctype = "image/x-icon"
        elif lower.endswith(".png"):
            ctype = "image/png"
        elif lower.endswith(".jpg") or lower.endswith(".jpeg"):
            ctype = "image/jpeg"
        elif lower.endswith(".webp"):
            ctype = "image/webp"
        elif lower.endswith(".svg"):
            ctype = "image/svg+xml"
        elif lower.endswith(".woff"):
            ctype = "font/woff"
        elif lower.endswith(".woff2"):
            ctype = "font/woff2"
        elif lower.endswith(".json"):
            ctype = "application/json"
        elif lower.endswith(".map"):
            ctype = "application/json"
        with open(full, "rb") as f:
            data = f.read()
        self._send(200, data, ctype)


_httpd = None


def start_server(host="127.0.0.1", port=8765):
    global _httpd
    if _httpd is not None:
        return _httpd, f"http://{host}:{port}"
    last_err = None
    for candidate in range(int(port), int(port) + 8):
        try:
            httpd = ThreadingHTTPServer((host, candidate), Handler)
            t = threading.Thread(target=httpd.serve_forever, daemon=True)
            t.start()
            _httpd = httpd
            if candidate != int(port):
                os.environ["CRAFTLIFE_API_PORT"] = str(candidate)
            print(f"CraftLife API http://{host}:{candidate}", flush=True)
            return httpd, f"http://{host}:{candidate}"
        except OSError as exc:
            last_err = exc
            continue
    print(f"CraftLife API gagal bind {host}:{port}: {last_err}", flush=True)
    raise last_err or OSError("api_bind_failed")


if __name__ == "__main__":
    db.init_db()
    _ensure_user()
    host = os.environ.get("CRAFTLIFE_API_HOST", "127.0.0.1")
    port = int(os.environ.get("CRAFTLIFE_API_PORT", "8765"))
    start_server(host, port)
    print(f"CraftLife API http://{host}:{port} user_id={_state.get('user_id')}", flush=True)
    try:
        threading.Event().wait()
    except KeyboardInterrupt:
        pass
