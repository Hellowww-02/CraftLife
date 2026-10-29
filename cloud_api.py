"""HTTP boundary for CraftLife Cloud (I1). React never talks to Supabase directly."""
from __future__ import annotations

import threading
from typing import Optional

import gzip
import json

from cloud_service import get_cloud_service
from storage import get_store
from sync_service import get_sync_service

_bg_stop = threading.Event()
_bg_thread: Optional[threading.Thread] = None
_bg_user_id: Optional[int] = None


def _public_link(link):
    if not link:
        return None
    return {
        "email": link.get("email") or "",
        "status": link.get("status") or "",
        "cloud_user_id": link.get("cloud_user_id") or "",
        "last_sync_at": link.get("last_sync_at"),
        "linked_at": link.get("linked_at") or link.get("created_at"),
    }


def _public_device(device):
    if not device:
        return None
    return {
        "device_id": device.get("device_id"),
        "device_name": device.get("device_name"),
        "platform": device.get("platform"),
        "app_version": device.get("app_version"),
        "last_seen_at": device.get("last_seen_at"),
    }


def _public_personal(personal):
    personal = personal or {}
    return {
        "conflict_status": personal.get("conflict_status") or "none",
        "remote_revision": personal.get("remote_revision") or 0,
        "last_pushed_at": personal.get("last_pushed_at"),
        "last_pulled_at": personal.get("last_pulled_at"),
    }


def classify_cloud_error(exc: Exception) -> dict:
    """H06 (v1.7.0): terjemahkan exception Supabase/jaringan menjadi KODE
    terstruktur supaya web tidak pernah menampilkan "HTTP 400" mentah.

    Frontend memetakan `code` → pesan bilingual (cloud_err_<code>); `error`
    tetap diisi agar klien lama (PyQt6/desktop) tidak berubah perilakunya.
    """
    msg = str(exc or "")
    low = msg.lower()
    if "invalid login credentials" in low or "invalid_credentials" in low:
        code = "auth_invalid_credentials"
    elif "email not confirmed" in low or "email_not_confirmed" in low:
        code = "auth_email_not_confirmed"
    elif "already registered" in low or "already been registered" in low or "user already" in low:
        code = "auth_email_exists"
    elif "rate limit" in low or "too many requests" in low or " 429" in low:
        code = "cloud_rate_limited"
    elif "migration" in low and ("not applied" in low or "not_applied" in low):
        code = "cloud_migration_not_applied"
    elif any(k in low for k in ("network", "connection", "connect", "timeout", "timed out",
                                "resolve", "dns", "getaddrinfo", "unreachable", "refused",
                                "name or service not known", "temporarily unavailable")):
        code = "cloud_network_error"
    elif "supabase" in low and any(k in low for k in ("url", "key", "missing", "unset", "not configured", "not_configured", "env")):
        code = "cloud_not_configured"
    elif any(k in low for k in ("no module named", "importerror", "modulenotfounderror", "pip install")):
        code = "cloud_sdk_missing"
    elif "jwt" in low or "token" in low or "session" in low or "auth_required" in low:
        code = "auth_session_expired"
    else:
        code = "cloud_unknown_error"
    return {"ok": False, "code": code, "error": code, "detail": msg[:300]}


def _sync_out(result: dict) -> dict:
    """H06: hasil sync `ok:false` WAJIB membawa `error` — tanpa itu client web
    melempar fallback "HTTP 400" dan user mengira sinkronisasi rusak total."""
    # Salin, jangan rekursi. Baris ini dulu tertulis `out = _sync_out(result)`,
    # yang memanggil dirinya sendiri tanpa dasar: setiap panggilan berakhir
    # RecursionError, sehingga /api/cloud/sync-now, /migrate-local dan /conflict
    # tidak pernah bisa mengembalikan apa pun. Ada sejak commit pertama.
    out = dict(result or {})
    if not out.get("ok", True) and not out.get("error"):
        code = out.get("code") or "cloud_sync_failed"
        out["error"] = code
        out.setdefault("code", code)
    return out


def public_status(uid: int) -> dict:
    service = get_sync_service()
    try:
        if get_store().get_cloud_user_link(uid) and not service.cloud.authenticated:
            service.ensure_session(uid)
    except Exception:
        pass
    raw = service.cloud_status(uid)
    link = _public_link(raw.get("link"))
    # Lewat store, bukan `database` langsung: cloud_api.py dikunci oleh tes AST
    # M05d agar tidak punya satu pun referensi `db`.
    _state_row = get_store().get_cloud_service_state(uid)
    _reason = str(_state_row.get("suspended_reason") or "")
    _suspended_at = str(_state_row.get("suspended_at") or "")
    _suspended, _ = get_store().cloud_suspension_active(uid)
    _retry_after = 0
    if _suspended:
        from datetime import datetime, timezone
        try:
            _parsed = datetime.fromisoformat(_suspended_at.replace("Z", "+00:00"))
            # Penanda waktu SQLite adalah UTC tanpa zona; lihat catatan yang
            # sama di database.cloud_suspension_active.
            if _parsed.tzinfo is None:
                _parsed = _parsed.replace(tzinfo=timezone.utc)
            _elapsed = (datetime.now(timezone.utc) - _parsed).total_seconds()
            _retry_after = max(0, int(CLOUD_SUSPEND_PROBE_SECONDS - _elapsed))
        except Exception:
            _retry_after = CLOUD_SUSPEND_PROBE_SECONDS
    queue = raw.get("queue") or {}
    failed = []
    for row in (raw.get("queue_failed_samples") or [])[:3]:
        failed.append({
            "entity_type": row.get("entity_type"),
            "operation": row.get("operation"),
            "status": row.get("status"),
            "retry_count": row.get("retry_count"),
            "last_error": (row.get("last_error") or row.get("err") or "")[:200],
            "next_retry_at": row.get("next_retry_at"),
        })
    return {
        "ok": True,
        "configured": bool(raw.get("configured")),
        "sdk_available": bool(raw.get("sdk_available")),
        "keyring_available": bool(raw.get("keyring_available")),
        "authenticated": bool(raw.get("authenticated")),
        # P26: `linked` hanya true bila sesi benar2 aktif (authenticated). Setelah
        # sign_out, baris cloud_user_links lama tetap ada di DB, jadi tanpa gate ini
        # `linked` tetap true dan tombol Sign-In/Buat Akun ter-disable permanen.
        "linked": bool(link) and bool(raw.get("authenticated")),
        "email": (link or {}).get("email") or raw.get("email") or "",
        # Kuota/penangguhan. Saat Supabase menjawab 402 (egress free tier habis,
        # project dibatasi) sync berhenti sendiri dan keadaan ini yang memberi
        # tahu pengguna apa yang terjadi. Tanpa ini yang terlihat hanya "sync
        # tidak jalan" tanpa alasan.
        # snake_case dipakai karena seluruh objek ini sudah snake_case;
        # mencampur camelCase di satu respons justru tidak konsisten.
        "suspended": bool(_suspended),
        "suspended_reason": _reason,
        "suspended_at": _suspended_at,
        "retry_after_seconds": _retry_after,
        "link": link,
        "queue": {
            "pending": int(queue.get("pending") or 0),
            "retry": int(queue.get("retry") or 0),
            "done": int(queue.get("done") or 0),
            "failed": int(queue.get("failed") or 0),
        },
        "queue_failed_samples": failed,
        "device": _public_device(raw.get("device")),
        "personal": _public_personal(raw.get("personal")),
        "realtime_connected": bool(raw.get("realtime_connected")),
        "last_error": (raw.get("last_error") or "")[:300],
    }


def _slim_sync_result(result: dict) -> dict:
    out = dict(result or {})
    out.pop("status", None)
    personal = out.get("personal")
    if isinstance(personal, dict):
        out["personal"] = {
            k: personal.get(k)
            for k in ("available", "remote", "conflict", "revision", "applied", "matched", "unchanged", "reason")
            if k in personal
        }
    return out


def handle_get(path: str, uid: int):
    if path == "/api/cloud/status":
        return public_status(uid)
    if path == "/api/cloud/devices":
        cloud = get_cloud_service()
        sync = get_sync_service()
        if not sync.ensure_session(uid):
            return {"ok": False, "error": "auth_required", "devices": []}
        local = get_store().get_or_create_cloud_device(uid)
        register_error = None
        try:
            row = cloud.register_cloud_device(local)
            if isinstance(row, list):
                row = row[0] if row else {}
            if isinstance(row, dict) and row:
                get_store().mark_cloud_device_registered(uid, row.get("first_seen_at"), row.get("last_seen_at"))
        except Exception as exc:
            register_error = str(exc)
        devices = cloud.get_cloud_devices()
        local_id = str(local.get("device_id") or "").lower()
        pub = []
        for device in devices:
            did = str(device.get("id") or device.get("device_id") or "")
            pub.append({
                "id": did,
                "device_name": device.get("device_name"),
                "platform": device.get("platform"),
                "revoked_at": device.get("revoked_at"),
                "last_seen_at": device.get("last_seen_at"),
                "current": did.lower() == local_id,
            })
        return {
            "ok": True,
            "devices": pub,
            "local": _public_device(local),
            "register_error": register_error,
        }
    if path == "/api/cloud/queue":
        info = get_sync_service().inspect_queue(uid)
        jobs = []
        for job in (info.get("jobs") or [])[:40]:
            jobs.append({
                "id": job.get("id"),
                "entity_type": job.get("entity_type"),
                "operation": job.get("operation"),
                "status": job.get("status"),
                "retry_count": job.get("retry_count"),
                "last_error": (job.get("last_error") or "")[:180],
                "next_retry_at": job.get("next_retry_at"),
            })
        return {"ok": True, "summary": info.get("summary") or {}, "jobs": jobs}
    if path == "/api/cloud/sync-status":
        # M04c: pending count · failed count · last-synced untuk panel status sync.
        return {"ok": True, **get_store().sync_status_summary(uid)}
    if path == "/api/cloud/conflicts":
        # M04c: "baru saja tertimpa" yang bisa dipulihkan (K11) — bukan dialog biner.
        return {"ok": True, "conflicts": get_store().list_sync_conflicts(uid, 50)}
    if path == "/api/cloud/migrate-preview":
        preview = get_sync_service().initial_migration_preview(uid)
        return {"ok": True, "preview": preview}
    if path == "/api/cloud/backups":
        return backup_list(uid)
    if path.startswith("/api/cloud/leaderboard"):
        # Parity LeaderboardPage.load cloud mode:
        # bila linked → get_online_guild_leaderboard(50) / get_global_productivity_leaderboard(30,50)
        from urllib.parse import urlparse, parse_qs
        q = parse_qs(urlparse(path).query)
        mode = (q.get("mode") or ["cloud_productivity"])[0]
        if not get_store().get_cloud_user_link(uid):
            return {"ok": True, "linked": False, "rows": []}
        cloud = get_cloud_service()
        sync = get_sync_service()
        if not sync.ensure_session(uid):
            return {"ok": False, "error": "auth_required", "linked": True, "rows": []}
        try:
            if mode == "cloud_guild":
                rows = cloud.get_online_guild_leaderboard(50)
            else:
                rows = cloud.get_global_productivity_leaderboard(30, 50)
        except Exception as exc:
            return {"ok": False, "error": str(exc), "linked": True, "rows": []}
        return {"ok": True, "linked": True, "mode": mode, "rows": rows or []}
    if path == "/api/cloud/guild-online":
        # M10: guild ONLINE (cloud) — role/transfer/ban/chat/boss hidup di
        # RPC Supabase; route ini jembatan Android (pola yang sama dengan
        # /api/cloud/leaderboard di atas). Guild LOKAL tetap di
        # studio_api /api/guild dan tidak dicampur ke sini.
        cloud, err = _social_cloud(uid)
        if err is not None:
            return {**err, "guilds": [], "summary": {}, "members": [],
                    "requests": [], "messages": [], "battles": [], "rewards": []}
        try:
            summary = cloud.get_my_online_guild_summary() or {}
            gid = summary.get("guild_id") or summary.get("id")
            out = {"ok": True, "linked": True, "summary": summary,
                   "guilds": cloud.get_online_guilds() or [],
                   "members": [], "requests": [], "messages": [],
                   "messageReactions": {}, "battles": [], "rewards": [],
                   "contributions": []}
            if gid:
                out["members"] = cloud.get_online_guild_members() or []
                out["requests"] = cloud.get_online_guild_requests() or []
                msgs = cloud.get_online_guild_messages(str(gid), 50) or []
                out["messages"] = msgs
                ids = [m.get("id") for m in msgs if isinstance(m, dict) and m.get("id")]
                if ids:
                    out["messageReactions"] = cloud.get_online_guild_message_reactions(ids) or {}
                out["battles"] = cloud.get_online_guild_battles() or []
                out["rewards"] = cloud.get_online_guild_boss_rewards() or []
                out["contributions"] = cloud.get_online_guild_contributions() or []
            return out
        except Exception as exc:
            return {"ok": False, "error": str(exc), "linked": True}
    if path == "/api/cloud/notifications":
        # M10: notifikasi sosial cloud (teman/guild/PvP/Love). Berbeda dari
        # /api/notifications (pusat notifikasi lokal studio_api).
        cloud, err = _social_cloud(uid)
        if err is not None:
            return {**err, "notifications": [], "unread": 0}
        try:
            rows = cloud.get_social_notifications(False, 50) or []
        except Exception as exc:
            return {"ok": False, "error": str(exc), "linked": True}
        unread = sum(1 for r in rows if isinstance(r, dict) and not r.get("is_read"))
        return {"ok": True, "linked": True, "notifications": rows, "unread": unread}
    return None


def handle_post(path: str, uid: int, body: dict):
    body = body or {}
    cloud = get_cloud_service()
    sync = get_sync_service()

    if path == "/api/cloud/register":
        email = str(body.get("email") or "").strip()
        password = str(body.get("password") or "")
        if "@" not in email or len(password) < 8:
            return {"ok": False, "code": "credentials_invalid", "error": "credentials_invalid"}
        try:
            result = cloud.sign_up(email, password)
        except Exception as exc:  # H06: AuthApiError → kode terstruktur
            return classify_cloud_error(exc)
        return {
            "ok": True,
            "verification_required": bool(result.get("verification_required")),
        }

    if path == "/api/cloud/login":
        email = str(body.get("email") or "").strip()
        password = str(body.get("password") or "")
        if "@" not in email or len(password) < 8:
            return {"ok": False, "code": "credentials_invalid", "error": "credentials_invalid"}
        try:
            auth = cloud.sign_in(email, password)
            linked = cloud.link_local_account(uid, auth)
        except Exception as exc:  # H06: kredensial salah / email belum dikonfirmasi
            return classify_cloud_error(exc)
        try:
            sync.start_realtime(uid)
        except Exception:
            pass
        start_desktop_cloud_loop(uid)
        return {"ok": True, "link": linked, "status": public_status(uid)}

    if path == "/api/cloud/logout":
        cloud.sign_out(uid)
        return {"ok": True, "status": public_status(uid)}

    if path == "/api/cloud/sync-now":
        result = sync.sync_now(uid, force_retry=True)
        try:
            sync.start_realtime(uid)
        except Exception:
            pass
        out = _sync_out(result)  # H06: ok:false selalu membawa error/code
        out["status"] = public_status(uid)
        return out

    if path == "/api/cloud/migrate-local":
        preview = sync.initial_migration_preview(uid)
        sync.enqueue_initial_migration(uid)
        result = sync.sync_now(uid, force_retry=True)
        out = _sync_out(result)  # H06: ok:false selalu membawa error/code
        out["preview"] = preview
        out["status"] = public_status(uid)
        return out

    if path == "/api/cloud/conflict":
        choice = str(body.get("choice") or "").lower()
        if choice in ("local", "keep_local"):
            result = sync.resolve_personal_conflict_keep_local(uid)
        elif choice in ("cloud", "use_cloud", "remote"):
            result = sync.resolve_personal_conflict_use_cloud(uid)
        else:
            return {"ok": False, "error": "invalid_choice"}
        out = _sync_out(result)  # H06: ok:false selalu membawa error/code
        out["status"] = public_status(uid)
        return out

    if path == "/api/cloud/queue/retry":
        result = sync.retry_failed_now(uid)
        out = _sync_out(result)  # H06: ok:false selalu membawa error/code
        out["status"] = public_status(uid)
        return out

    if path == "/api/cloud/conflicts/restore":
        conflict_id = body.get("conflict_id")
        if not conflict_id:
            return {"ok": False, "error": "conflict_id_required"}
        result = get_store().restore_sync_conflict(uid, conflict_id)
        out = _sync_out(result)
        out["status"] = public_status(uid)
        return out

    if path == "/api/cloud/devices/revoke":
        if not sync.ensure_session(uid):
            return {"ok": False, "error": "auth_required"}
        device_id = str(body.get("device_id") or body.get("id") or "")
        if not device_id:
            return {"ok": False, "error": "device_id_required"}
        local = get_store().get_or_create_cloud_device(uid)
        if str(local.get("device_id")) == device_id:
            return {"ok": False, "error": "current_device"}
        cloud.revoke_cloud_device(device_id)
        return {"ok": True}

    if path == "/api/cloud/devices/rename":
        if not sync.ensure_session(uid):
            return {"ok": False, "error": "auth_required"}
        device_id = str(body.get("device_id") or body.get("id") or "")
        name = str(body.get("name") or "").strip()
        if not device_id or not name:
            return {"ok": False, "error": "invalid"}
        cloud.rename_cloud_device(device_id, name)
        local = get_store().get_or_create_cloud_device(uid)
        if str(local.get("device_id")) == device_id:
            get_store().rename_local_cloud_device(uid, name)
        return {"ok": True}

    if path == "/api/cloud/backup":
        action = str(body.get("action") or "create").strip().lower()
        if action == "set-auto":
            return backup_set_auto(uid, bool(body.get("enabled")))
        if action == "restore":
            return backup_restore(uid, str(body.get("path") or ""))
        if action == "create":
            return backup_create(uid)
        return {"ok": False, "error": "action_invalid"}

    if path == "/api/cloud/devices/revoke-others":
        if not sync.ensure_session(uid):
            return {"ok": False, "error": "auth_required"}
        local = get_store().get_or_create_cloud_device(uid)
        cloud.revoke_other_cloud_devices(local["device_id"])
        return {"ok": True}

    # ── M10: jembatan sosial cloud (guild online, notifikasi, presence, push)
    if path == "/api/cloud/presence":
        cloud, err = _social_cloud(uid)
        if err is not None:
            return err
        try:
            cloud.heartbeat_presence(str(body.get("status") or "online"),
                                     str(body.get("deviceName") or "CraftLife Android"))
        except Exception as exc:
            return {"ok": False, "error": str(exc), "linked": True}
        return {"ok": True, "linked": True}

    if path == "/api/cloud/push-token":
        # Token dicatat apa adanya; Supabase (Edge Function send-push) yang
        # memanggil FCM. Tanpa sesi cloud token tidak diterima — token atas
        # nama orang lain tidak boleh bisa didaftarkan (RPC memakai uid).
        cloud, err = _social_cloud(uid)
        if err is not None:
            return err
        token = str(body.get("token") or "").strip()
        if not token:
            return {"ok": False, "error": "token_required", "linked": True}
        try:
            row = cloud.register_push_token(
                token,
                str(body.get("platform") or "android"),
                str(body.get("deviceName") or "CraftLife Android"))
        except Exception as exc:
            return {"ok": False, "error": str(exc), "linked": True}
        return {"ok": True, "linked": True, "row": row or {}}

    if path == "/api/cloud/notifications/read":
        cloud, err = _social_cloud(uid)
        if err is not None:
            return err
        try:
            nid = body.get("id")
            if nid:
                cloud.mark_social_notification_read(str(nid))
            else:
                cloud.mark_social_notifications_read(None)
        except Exception as exc:
            return {"ok": False, "error": str(exc), "linked": True}
        return {"ok": True, "linked": True}

    if path.startswith("/api/cloud/guild-online/"):
        cloud, err = _social_cloud(uid)
        if err is not None:
            return err
        action = path.rsplit("/", 1)[-1]
        gid = str(body.get("guildId") or body.get("guild_id") or "")
        target = str(body.get("userId") or body.get("user_id") or "")
        try:
            if action == "create":
                name = str(body.get("name") or "").strip()
                if not name:
                    return {"ok": False, "error": "name_required", "linked": True}
                row = cloud.create_online_guild(name, str(body.get("description") or ""))
            elif action == "join":
                row = cloud.request_online_guild_join(gid)
            elif action == "respond":
                row = cloud.respond_online_guild_join(str(body.get("requestId") or ""), bool(body.get("accept", True)))
            elif action == "cancel":
                row = cloud.cancel_online_guild_join(str(body.get("requestId") or ""))
            elif action == "leave":
                row = cloud.leave_online_guild(gid)
            elif action == "kick":
                row = cloud.kick_online_guild_member(gid, target)
            elif action == "ban":
                row = cloud.ban_online_guild_member(gid, target, str(body.get("reason") or ""))
            elif action == "unban":
                row = cloud.unban_online_guild_member(gid, target)
            elif action == "role":
                row = cloud.set_online_guild_role(gid, target, str(body.get("role") or "member"))
            elif action == "transfer":
                row = cloud.transfer_online_guild_leader(gid, target)
            elif action == "disband":
                row = cloud.disband_online_guild(gid)
            elif action == "description":
                row = cloud.update_online_guild_description(gid, str(body.get("description") or ""))
            elif action == "message":
                text = str(body.get("text") or "").strip()
                if not text:
                    return {"ok": False, "error": "empty", "linked": True}
                row = cloud.send_online_guild_message(gid, text, None, body.get("replyToId") or None)
            elif action == "message-reaction":
                row = cloud.set_online_guild_message_reaction(str(body.get("messageId") or ""), body.get("reaction"))
            elif action == "boss-start":
                row = cloud.start_online_guild_boss(gid, str(body.get("bossKey") or "cloud_dragon"))
            elif action == "boss-claim":
                row = cloud.claim_online_guild_boss_reward(str(body.get("battleId") or ""))
            else:
                return {"ok": False, "error": "unknown_action", "linked": True}
        except Exception as exc:
            return {"ok": False, "error": str(exc), "linked": True}
        return {"ok": True, "linked": True, "row": row or {}}

    return None


# ---------------------------------------------------------------------------
# Backup tracker ke cloud (P6: jangan pernah kehilangan data)
#
# Paket gratis Supabase tidak punya backup otomatis. Backup lokal yang sudah
# ada hanya menyelamatkan SQLite di satu perangkat; ia tidak menolong kalau
# perangkat itu hilang. Ini menutup lubang itu.
# ---------------------------------------------------------------------------

BACKUP_KEEP = 14

#: Jeda antar percobaan ulang saat layanan ditangguhkan (harus sama dengan
#: database.CLOUD_SUSPEND_PROBE_SECONDS; diuji oleh test_m05_cloud_quota).
CLOUD_SUSPEND_PROBE_SECONDS = 3600          # berapa backup terbaru yang disimpan di cloud
BACKUP_INTERVAL_HOURS = 24


def _gzip_snapshot(uid: int) -> bytes:
    # allow_admin=True: backup itu baca-saja dan tidak menulis apa pun, jadi ia
    # bukan vektor curang yang dijaga oleh larangan ekspor admin. Tanpa ini,
    # akun admin tidak punya cadangan data sama sekali.
    snapshot = get_store().build_backup_snapshot(uid)
    raw = json.dumps(snapshot, ensure_ascii=False, default=str).encode("utf-8")
    return gzip.compress(raw, 6)


def backup_list(uid: int) -> dict:
    """Daftar backup + status auto. Tidak butuh sesi cloud untuk statusnya,
    jadi UI tetap bisa menampilkan 'mati' walaupun belum login."""
    st = get_store().get_maintenance_state(uid)
    out = {"ok": True, "backupAuto": bool(st.get("backup_auto")),
           "lastBackupAt": st.get("last_backup_at") or "", "backups": []}
    if not is_cloud_linked(uid):
        return {**out, "linked": False}
    sync = get_sync_service()
    if not sync.ensure_session(uid):
        return {**out, "linked": True, "error": "auth_required"}
    try:
        # C06: respons camelCase konsisten. Klien tidak boleh dibiasakan
        # membaca snake_case dari sebagian rute dan camelCase dari yang lain.
        out["backups"] = [{
            "name": b.get("name"), "path": b.get("path"),
            "sizeBytes": int(b.get("size_bytes") or 0),
            "createdAt": b.get("created_at") or "",
        } for b in get_cloud_service().list_tracker_backups()]
    except Exception as exc:
        return {**out, "linked": True, "error": str(exc)[:200]}
    return out


def backup_create(uid: int) -> dict:
    """Buat satu backup sekarang, lalu rotasi yang lama."""
    if not is_cloud_linked(uid):
        return {"ok": False, "error": "not_linked"}
    sync = get_sync_service()
    if not sync.ensure_session(uid):
        return {"ok": False, "error": "auth_required"}
    cloud = get_cloud_service()
    try:
        payload = _gzip_snapshot(uid)
    except PermissionError as exc:
        return {"ok": False, "error": "export_forbidden", "detail": str(exc)}
    except Exception as exc:
        return {"ok": False, "error": "export_failed", "detail": str(exc)[:200]}
    try:
        info = cloud.upload_tracker_backup(payload)
        pruned = cloud.prune_tracker_backups(BACKUP_KEEP)
    except Exception as exc:
        return {"ok": False, "error": "upload_failed", "detail": str(exc)[:200]}
    get_store().mark_backup_done(uid)
    return {"ok": True, "path": info["path"], "sizeBytes": info["size_bytes"],
            "pruned": pruned}


def backup_set_auto(uid: int, enabled: bool) -> dict:
    get_store().set_maintenance_state(uid, backup_auto=enabled)
    st = get_store().get_maintenance_state(uid)
    return {"ok": True, "backupAuto": bool(st.get("backup_auto"))}


def backup_restore(uid: int, path: str) -> dict:
    """Pulihkan dari satu backup cloud.

    Dua pagar pengaman, dan keduanya disengaja:

    1. **Backup lokal dibuat lebih dulu.** Restore menimpa data sekarang. Kalau
       hasilnya ternyata bukan yang diinginkan, harus masih ada jalan kembali
       (P6). Tanpa ini, restore yang salah jadi kehilangan data permanen.
    2. **Path harus di folder pengguna ini.** Nama file datang dari request;
       tanpa pemeriksaan, seseorang bisa memulihkan dari path milik orang lain.
    """
    if not is_cloud_linked(uid):
        return {"ok": False, "error": "not_linked"}
    sync = get_sync_service()
    if not sync.ensure_session(uid):
        return {"ok": False, "error": "auth_required"}
    cloud = get_cloud_service()
    prefix = f"{cloud.current_cloud_user_id}/"
    if not path.startswith(prefix) or ".." in path:
        return {"ok": False, "error": "path_forbidden"}
    try:
        raw = cloud.download_storage(cloud.config.backup_bucket, path)
    except Exception as exc:
        return {"ok": False, "error": "download_failed", "detail": str(exc)[:200]}
    # Dipisahkan dari unduhan dengan sengaja: "gagal mengunduh" dan "isinya
    # rusak" adalah dua masalah berbeda, dan mencampurnya membuat pengguna
    # mengira jaringannya putus padahal cadangannya yang korup.
    try:
        data = json.loads(gzip.decompress(raw).decode("utf-8"))
    except Exception as exc:
        return {"ok": False, "error": "backup_malformed", "detail": str(exc)[:200]}
    if not isinstance(data, dict) or "tables" not in data:
        return {"ok": False, "error": "backup_malformed"}
    try:
        get_store().local_backup_before_restore()
    except Exception:
        # Kegagalan backup lokal tidak boleh membatalkan restore yang diminta
        # pengguna, tapi harus dilaporkan supaya keputusannya sadar.
        local_backup_ok = False
    else:
        local_backup_ok = True
    try:
        get_store().import_backup_snapshot(uid, data)
    except PermissionError as exc:
        return {"ok": False, "error": "import_forbidden", "detail": str(exc),
                "localBackupOk": local_backup_ok}
    except Exception as exc:
        return {"ok": False, "error": "import_failed", "detail": str(exc)[:200],
                "localBackupOk": local_backup_ok}
    return {"ok": True, "localBackupOk": local_backup_ok,
            "tables": len(data.get("tables") or {})}


def maybe_auto_backup(uid: int) -> dict:
    """Backup harian, dipicu saat login. Best-effort: tidak pernah raise."""
    try:
        st = get_store().get_maintenance_state(uid)
        if not st.get("backup_auto"):
            return {"ok": False, "code": "disabled"}
        if not is_cloud_linked(uid):
            return {"ok": False, "code": "not_linked"}
        last = st.get("last_backup_at") or ""
        if last:
            import sqlite3
            try:
                elapsed_h = (sqlite3.connect(":memory:")
                             .execute("SELECT (julianday('now') - julianday(?)) * 24", (last,))
                             .fetchone()[0])
            except Exception:
                elapsed_h = None
            if elapsed_h is not None and float(elapsed_h) < BACKUP_INTERVAL_HOURS:
                return {"ok": False, "code": "not_due"}
        result = backup_create(uid)
        if result.get("ok"):
            return {"ok": True, "path": result.get("path")}
        return {"ok": False, "code": result.get("error") or "failed"}
    except Exception as exc:
        return {"ok": False, "code": "error", "error": str(exc)[:200]}


def is_cloud_linked(uid: int) -> bool:
    return is_shop_cloud(uid)


def _social_cloud(uid: int):
    """(cloud, error_dict): cloud sosial hanya untuk user yang tertaut DAN
    sesinya hidup. error_dict siap dikembalikan apa adanya oleh handler."""
    if not get_store().get_cloud_user_link(uid):
        return None, {"ok": True, "linked": False}
    if not get_sync_service().ensure_session(uid):
        return None, {"ok": False, "error": "auth_required", "linked": True}
    return get_cloud_service(), None


def friend_request_cloud(uid: int, username: str) -> dict:
    cloud = get_cloud_service()
    row = cloud.send_friend_request(username)
    try:
        get_sync_service().sync_now(uid)
    except Exception:
        pass
    return {"ok": True, "cloud": True, "row": row or {}}


def send_direct_cloud(uid: int, other_local_id, text: str) -> dict:
    cloud = get_cloud_service()
    other = get_store().get_user(int(other_local_id)) or {}
    cid = other.get("cloud_user_id")
    if not cid:
        raise RuntimeError("friend_not_linked")
    conv = cloud.get_or_create_direct_conversation(str(cid))
    if isinstance(conv, list):
        conv = conv[0] if conv else {}
    conv_id = (conv or {}).get("id") or (conv or {}).get("conversation_id")
    if not conv_id:
        raise RuntimeError("conversation_missing")
    msg = cloud.send_direct_message(str(conv_id), text)
    return {"ok": True, "cloud": True, "message": msg or {}}


def send_pvp_cloud(uid: int, friend_local_id) -> dict:
    cloud = get_cloud_service()
    other = get_store().get_user(int(friend_local_id)) or {}
    cid = other.get("cloud_user_id")
    if not cid:
        raise RuntimeError("friend_not_linked")
    row = cloud.send_online_pvp_challenge(str(cid))
    return {"ok": True, "cloud": True, "row": row or {}}


def respond_pvp_cloud(challenge_id: str, accept: bool) -> dict:
    cloud = get_cloud_service()
    row = cloud.respond_online_pvp_challenge(str(challenge_id), bool(accept))
    return {"ok": True, "cloud": True, "row": row or {}}


def send_guild_message_cloud(text: str) -> dict:
    cloud = get_cloud_service()
    summary = cloud.get_my_online_guild_summary() or {}
    gid = summary.get("guild_id") or summary.get("id")
    if not gid:
        raise RuntimeError("no_online_guild")
    row = cloud.send_online_guild_message(str(gid), text)
    return {"ok": True, "cloud": True, "row": row or {}}


def love_upsert_cloud(uid: int, record_type: str, payload: dict, record_id=None) -> dict:
    cloud = get_cloud_service()
    space = None
    try:
        space = cloud.resolve_love_space_id(uid)
    except Exception:
        space = get_store().get_cloud_love_space_id(uid)
    if not space:
        raise RuntimeError("cloud_relationship_not_synced")
    row = cloud.upsert_love_space_record(space, record_type, payload, record_id)
    try:
        get_store().mirror_cloud_love_record(uid, record_type, (row or {}).get("row") or row or {})
    except Exception:
        pass
    return {"ok": True, "cloud": True, "row": row or {}}


def love_profile_cloud(uid: int, values: dict) -> dict:
    cloud = get_cloud_service()
    space = cloud.resolve_love_space_id(uid) or get_store().get_cloud_love_space_id(uid)
    if not space:
        raise RuntimeError("cloud_relationship_not_synced")
    row = cloud.save_love_space_shared_profile(space, values)
    try:
        get_store().mirror_cloud_love_profile(uid, row)
    except Exception:
        pass
    return {"ok": True, "cloud": True, "row": row or {}}


def love_photo_from_path(uid: int, file_path: str) -> dict:
    import io
    from pathlib import Path
    path = Path(file_path)
    if not path.is_file():
        raise RuntimeError("file_not_found")
    raw = path.read_bytes()
    return love_photo_from_bytes(uid, raw)


def love_photo_from_bytes(uid: int, raw: bytes, mime_hint: str = "image/jpeg",
                          caption=None, photo_date=None, visibility=None) -> dict:
    """Simpan foto Love Space dari bytes (upload web) — parity dengan love_photo_from_path
    yang dipakai dialog QFileDialog PyQt. Bekerja offline (BLOB SQLite) dan tetap
    antre-kan sync cloud bila akun ter-link."""
    import io
    mime = mime_hint or "image/jpeg"
    width, height = 800, 800
    try:
        from PIL import Image
        with Image.open(io.BytesIO(raw)) as image:
            image.load()
            width, height = image.size
            fmt = (image.format or "JPEG").upper()
            mime = {"PNG": "image/png", "WEBP": "image/webp", "JPEG": "image/jpeg"}.get(fmt, "image/jpeg")
    except Exception:
        pass
    result = get_store().add_love_space_photo(uid, raw, mime, width, height,
                                     caption=caption, photo_date=photo_date,
                                     visibility=visibility or "private")
    if not result.get("ok"):
        return result
    local_id = result.get("photo_id")
    if local_id:
        try:
            get_sync_service().queue_gallery_photo(uid, int(local_id))
        except Exception:
            pass
    return {"ok": True, "queued": True, "photo_id": local_id}


def is_shop_cloud(uid: int) -> bool:
    if not get_store().get_cloud_user_link(uid):
        return False
    try:
        return bool(get_sync_service().ensure_session(uid))
    except Exception:
        return False


def refresh_wallet_inventory(uid: int) -> tuple:
    cloud = get_cloud_service()
    wallet = {}
    inv = []
    try:
        wallet = cloud.wallet_balance() or {}
        get_store().save_cloud_wallet(uid, wallet)
    except Exception:
        wallet = get_store().get_cloud_wallet(uid) or {}
    try:
        inv = cloud.fetch_cloud_inventory() or []
        get_store().save_cloud_inventory(uid, inv)
    except Exception:
        inv = get_store().get_cloud_inventory_cache(uid) or []
    return wallet, inv


def shop_cloud_buy(uid: int, item_key: str, qty: int, idem: str) -> dict:
    cloud = get_cloud_service()
    rpc = cloud.buy_shop_item(item_key, int(qty or 1), idem)
    wallet, inv = refresh_wallet_inventory(uid)
    return {"ok": True, "cloud": True, "rpc": rpc or {}, "wallet": wallet, "inventory_cloud": inv}


def shop_cloud_craft(uid: int, recipe_key: str, idem: str) -> dict:
    cloud = get_cloud_service()
    rpc = cloud.craft_item_cloud(recipe_key, idem)
    wallet, inv = refresh_wallet_inventory(uid)
    return {"ok": True, "cloud": True, "rpc": rpc or {}, "wallet": wallet, "inventory_cloud": inv}


def shop_cloud_enchant(uid: int, item_key: str, idem: str) -> dict:
    cloud = get_cloud_service()
    rpc = cloud.enchant_item_cloud(item_key, idem)
    wallet, inv = refresh_wallet_inventory(uid)
    return {"ok": True, "cloud": True, "rpc": rpc or {}, "wallet": wallet, "inventory_cloud": inv}


def shop_cloud_equip(uid: int, item_key: str, equipped: bool) -> dict:
    cloud = get_cloud_service()
    rpc = cloud.equip_item_cloud(item_key, bool(equipped))
    wallet, inv = refresh_wallet_inventory(uid)
    return {"ok": True, "cloud": True, "rpc": rpc or {}, "wallet": wallet, "inventory_cloud": inv}


def pets_cloud_spin(uid: int, idem: str) -> dict:
    """M09a: spin gacha yang diputuskan server (Kanal C).

    Berbeda dari spin lokal: fungsi ini TIDAK memanggil `db.spin_pet`.
    RPC `spin_pet_cloud` mengundi, memotong gold lewat ledger, dan
    membukukan pet; di sini hasilnya hanya dicerminkan ke tabel lokal
    yang dibaca UI (lewat `apply_cloud_spin_result`) dan cache pet
    disegarkan dari `fetch_cloud_pets`. Error RPC (mis.
    insufficient_balance) diteruskan ke pemanggil apa adanya.
    """
    cloud = get_cloud_service()
    result = cloud.spin_pet_cloud(idem) or {}
    payload = {}
    try:
        payload = cloud.fetch_cloud_pets() or {}
    except Exception:
        payload = {}
    if payload:
        get_store().save_cloud_pets(uid, payload)
    get_store().apply_cloud_spin_result(uid, result, payload)
    return {"ok": True, "cloud": True, **result,
            "pets": payload.get("pets") or [],
            "spin_state": payload.get("spin_state") or {}}


def refresh_cloud_talents(uid: int) -> dict:
    """M09b: segarkan talent dari server lalu cerminkan ke lokal.

    Server adalah buku catatan unlock; device lain yang membuka talent
    lewat device ini menerima unlock dari device pertamanya di sini.
    Kegagalan cloud tidak menggagalkan baca lokal (pemanggil memakai
    state lokal apa adanya).
    """
    cloud = get_cloud_service()
    payload = cloud.fetch_cloud_talents() or {}
    if payload:
        get_store().save_cloud_talents(uid, payload)
        get_store().apply_cloud_talents(uid, payload)
    return payload


def start_desktop_cloud_loop(local_user_id: int) -> None:
    """Background sync + realtime even when the UI is WebEngine, not MainWindow."""
    global _bg_thread, _bg_user_id
    from cloud_config import load_cloud_config

    _bg_user_id = int(local_user_id)
    if _bg_thread and _bg_thread.is_alive() and _bg_user_id == int(local_user_id):
        return

    interval = max(15, int(load_cloud_config().sync_interval_seconds or 60))
    _bg_stop.set()
    _bg_stop.clear()

    def run():
        uid = int(local_user_id)
        svc = get_sync_service()
        try:
            if get_store().get_cloud_user_link(uid):
                svc.ensure_session(uid)
                svc.start_realtime(uid)
                svc.sync_now(uid)
        except Exception:
            pass
        while not _bg_stop.wait(interval):
            try:
                if get_store().get_cloud_user_link(uid):
                    svc.sync_now(uid)
            except Exception:
                pass

    _bg_thread = threading.Thread(target=run, daemon=True, name="CraftLifeCloudLoop")
    _bg_thread.start()
