"""HTTP boundary for CraftLife Cloud (I1). React never talks to Supabase directly."""
from __future__ import annotations

import threading
from typing import Optional

import database as db
from cloud_service import get_cloud_service
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


def public_status(uid: int) -> dict:
    service = get_sync_service()
    try:
        if db.get_cloud_user_link(uid) and not service.cloud.authenticated:
            service.ensure_session(uid)
    except Exception:
        pass
    raw = service.cloud_status(uid)
    link = _public_link(raw.get("link"))
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
        "linked": bool(link),
        "email": (link or {}).get("email") or raw.get("email") or "",
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
        local = db.get_or_create_cloud_device(uid)
        register_error = None
        try:
            row = cloud.register_cloud_device(local)
            if isinstance(row, list):
                row = row[0] if row else {}
            if isinstance(row, dict) and row:
                db.mark_cloud_device_registered(uid, row.get("first_seen_at"), row.get("last_seen_at"))
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
    if path == "/api/cloud/migrate-preview":
        preview = get_sync_service().initial_migration_preview(uid)
        return {"ok": True, "preview": preview}
    return None


def handle_post(path: str, uid: int, body: dict):
    body = body or {}
    cloud = get_cloud_service()
    sync = get_sync_service()

    if path == "/api/cloud/register":
        email = str(body.get("email") or "").strip()
        password = str(body.get("password") or "")
        if "@" not in email or len(password) < 8:
            return {"ok": False, "error": "credentials_invalid"}
        result = cloud.sign_up(email, password)
        return {
            "ok": True,
            "verification_required": bool(result.get("verification_required")),
        }

    if path == "/api/cloud/login":
        email = str(body.get("email") or "").strip()
        password = str(body.get("password") or "")
        if "@" not in email or len(password) < 8:
            return {"ok": False, "error": "credentials_invalid"}
        auth = cloud.sign_in(email, password)
        linked = cloud.link_local_account(uid, auth)
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
        out = _slim_sync_result(result)
        out["status"] = public_status(uid)
        return out

    if path == "/api/cloud/migrate-local":
        preview = sync.initial_migration_preview(uid)
        sync.enqueue_initial_migration(uid)
        result = sync.sync_now(uid, force_retry=True)
        out = _slim_sync_result(result)
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
        out = _slim_sync_result(result)
        out["status"] = public_status(uid)
        return out

    if path == "/api/cloud/queue/retry":
        result = sync.retry_failed_now(uid)
        out = _slim_sync_result(result)
        out["status"] = public_status(uid)
        return out

    if path == "/api/cloud/devices/revoke":
        if not sync.ensure_session(uid):
            return {"ok": False, "error": "auth_required"}
        device_id = str(body.get("device_id") or body.get("id") or "")
        if not device_id:
            return {"ok": False, "error": "device_id_required"}
        local = db.get_or_create_cloud_device(uid)
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
        local = db.get_or_create_cloud_device(uid)
        if str(local.get("device_id")) == device_id:
            db.rename_local_cloud_device(uid, name)
        return {"ok": True}

    if path == "/api/cloud/devices/revoke-others":
        if not sync.ensure_session(uid):
            return {"ok": False, "error": "auth_required"}
        local = db.get_or_create_cloud_device(uid)
        cloud.revoke_other_cloud_devices(local["device_id"])
        return {"ok": True}

    return None


def is_cloud_linked(uid: int) -> bool:
    return is_shop_cloud(uid)


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
    other = db.get_user(int(other_local_id)) or {}
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
    other = db.get_user(int(friend_local_id)) or {}
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
        space = db.get_cloud_love_space_id(uid)
    if not space:
        raise RuntimeError("cloud_relationship_not_synced")
    row = cloud.upsert_love_space_record(space, record_type, payload, record_id)
    try:
        db.mirror_cloud_love_record(uid, record_type, (row or {}).get("row") or row or {})
    except Exception:
        pass
    return {"ok": True, "cloud": True, "row": row or {}}


def love_profile_cloud(uid: int, values: dict) -> dict:
    cloud = get_cloud_service()
    space = cloud.resolve_love_space_id(uid) or db.get_cloud_love_space_id(uid)
    if not space:
        raise RuntimeError("cloud_relationship_not_synced")
    row = cloud.save_love_space_shared_profile(space, values)
    try:
        db.mirror_cloud_love_profile(uid, row)
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
    mime = "image/jpeg"
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
    result = db.add_love_space_photo(uid, raw, mime, width, height, visibility="private")
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
    if not db.get_cloud_user_link(uid):
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
        db.save_cloud_wallet(uid, wallet)
    except Exception:
        wallet = db.get_cloud_wallet(uid) or {}
    try:
        inv = cloud.fetch_cloud_inventory() or []
        db.save_cloud_inventory(uid, inv)
    except Exception:
        inv = db.get_cloud_inventory_cache(uid) or []
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
            if db.get_cloud_user_link(uid):
                svc.ensure_session(uid)
                svc.start_realtime(uid)
                svc.sync_now(uid)
        except Exception:
            pass
        while not _bg_stop.wait(interval):
            try:
                if db.get_cloud_user_link(uid):
                    svc.sync_now(uid)
            except Exception:
                pass

    _bg_thread = threading.Thread(target=run, daemon=True, name="CraftLifeCloudLoop")
    _bg_thread.start()
