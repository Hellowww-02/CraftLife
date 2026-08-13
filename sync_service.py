"""Offline-first Supabase sync orchestration for CraftLife Desktop.

SQLite remains the source used by the UI. Supabase adds server-authoritative social
features and Phase 3 conflict-safe personal tracker replication.
"""
from __future__ import annotations

import io
import json
import threading
import time
from datetime import datetime

import database as db
from cloud_service import get_cloud_service, _response_data

try:
    from PIL import Image
except ImportError:
    Image = None


class CloudSyncService:
    def __init__(self):
        self.cloud = get_cloud_service()
        self._lock = threading.Lock()
        self._realtime_sync_pending = threading.Event()
        self.last_result = {}

    def cloud_status(self, local_user_id: int) -> dict:
        status = self.cloud.status()
        status["link"] = db.get_cloud_user_link(local_user_id)
        status["queue"] = db.sync_queue_summary(local_user_id)
        status["device"] = db.get_or_create_cloud_device(local_user_id)
        status["personal"] = db.get_cloud_personal_sync_state(local_user_id)
        return status

    def ensure_session(self, local_user_id: int) -> bool:
        if self.cloud.authenticated:
            linked = db.get_cloud_user_link(local_user_id)
            return bool(linked and linked.get("cloud_user_id") == self.cloud.current_cloud_user_id)
        return self.cloud.restore_session(local_user_id)

    def start_realtime(self, local_user_id: int) -> bool:
        if not self.ensure_session(local_user_id):
            return False

        def changed(_table, _payload):
            # Ignore our own heartbeat/snapshot echo. Updates from another device
            # have the same user_id but a different source_device_id.
            payload_dict=_payload if isinstance(_payload,dict) else {}
            data=payload_dict.get("data") if isinstance(payload_dict.get("data"),dict) else {}
            record=data.get("record") or payload_dict.get("record") or payload_dict.get("new") or {}
            if _table=="user_presence" and str(record.get("user_id") or "")==str(self.cloud.current_cloud_user_id or ""):
                return
            if _table=="personal_snapshots":
                device=db.get_or_create_cloud_device(local_user_id)
                if str(record.get("source_device_id") or "")==str(device.get("device_id") or ""):
                    return
            # A single SQL transaction can emit several rows. Debounce them so a
            # realtime burst creates one pull instead of dozens of Python threads.
            if self._realtime_sync_pending.is_set():
                return
            self._realtime_sync_pending.set()

            def delayed_sync():
                try:
                    time.sleep(0.35)
                    self.sync_now(local_user_id)
                finally:
                    self._realtime_sync_pending.clear()

            threading.Thread(target=delayed_sync, daemon=True,
                             name="CraftLifeRealtimePull").start()
        try:
            self.cloud.subscribe_social_realtime(changed)
            return True
        except Exception:
            return False

    def queue_profile(self, local_user_id: int):
        db.enqueue_sync(local_user_id, "profile", local_user_id, "upsert")

    def queue_profile_photo(self, local_user_id: int):
        db.enqueue_sync(local_user_id, "profile_photo", local_user_id, "upload")

    def queue_profile_photo_delete(self, local_user_id: int):
        db.enqueue_sync(local_user_id, "profile_photo", local_user_id, "delete")

    def queue_gallery_photo(self, local_user_id: int, local_photo_id: int):
        db.enqueue_sync(local_user_id, "gallery_photo", local_photo_id, "upload")

    def initial_migration_preview(self, local_user_id: int) -> dict:
        personal = db.build_cloud_personal_snapshot(local_user_id)
        tracker_rows = sum(len(rows) for rows in personal.get("tables", {}).values())
        love_bundle=db.build_local_love_migration_bundle(local_user_id)
        love_rows=sum(len(value) if isinstance(value,(list,set,tuple)) else (1 if value else 0) for value in love_bundle.values())
        return {
            "profile": bool(db.get_user(local_user_id)),
            "profile_photo": db.get_profile_photo(local_user_id) is not None,
            "gallery_photos": len([p for p in db.get_love_space_photos(local_user_id)
                                   if p.get("owner_user_id") == local_user_id]),
            "friends": len(db.get_friends(local_user_id)),
            "couple_active": bool(db.get_active_couple_relationship(local_user_id)),
            "tracker_rows": tracker_rows,"love_rows":love_rows,
            "note": "Social relationships require server confirmation and are not silently auto-accepted.",
        }

    def enqueue_initial_migration(self, local_user_id: int):
        self.queue_profile(local_user_id)
        if db.get_profile_photo(local_user_id):
            self.queue_profile_photo(local_user_id)
        for photo in db.get_love_space_photos(local_user_id):
            if photo.get("owner_user_id") == local_user_id and not photo.get("cloud_id"):
                self.queue_gallery_photo(local_user_id, photo["id"])
        cloud_love_space=db.get_cloud_love_space_id(local_user_id)
        relationship=(db.get_couple_context(local_user_id).get("relationship") or {})
        if cloud_love_space or relationship.get("cloud_id"):
            db.enqueue_sync(local_user_id,"love_space_bundle",cloud_love_space or "pending","migrate",{"love_space_id":cloud_love_space})
        # The personal document is queued only after the remote revision is read
        # during sync_now, preventing a first device from overwriting another.
        return db.sync_queue_summary(local_user_id)

    def sync_now(self, local_user_id: int) -> dict:
        if not self._lock.acquire(blocking=False):
            return {"ok": False, "code": "already_running"}
        try:
            if not self.ensure_session(local_user_id):
                return {"ok": False, "code": "auth_required", "status": self.cloud_status(local_user_id)}

            # Phase 3 is intentionally backward-compatible: if its migration has
            # not been pushed yet, Phase 1/2 sync still works and reports the reason.
            phase3 = self._register_phase3_device(local_user_id)
            personal = {"available": False, "reason": phase3.get("error", "migration_not_applied")}
            if phase3.get("available"):
                personal = self._pull_personal(local_user_id)
                self._queue_personal_if_changed(local_user_id)

            pushed = self._process_queue(local_user_id)
            pulled = self._pull_social(local_user_id)
            maintenance = {}
            if phase3.get("available"):
                try:
                    maintenance = self.cloud.run_cloud_maintenance() or {}
                    try:maintenance["guild"]=self.cloud.run_online_guild_maintenance() or {}
                    except Exception as guild_exc:maintenance["guild"]={"ok":False,"error":str(guild_exc)}
                except Exception as exc:
                    maintenance = {"ok": False, "error": str(exc)}
            db.mark_cloud_sync_complete(local_user_id)
            self.last_result = {
                "ok": True, "pushed": pushed, "pulled": pulled,
                "personal": personal, "phase3": phase3,
                "maintenance": maintenance,
                "synced_at": datetime.now().isoformat(),
            }
            return self.last_result
        except Exception as exc:
            self.last_result = {"ok": False, "code": "sync_error", "error": str(exc)}
            return self.last_result
        finally:
            self._lock.release()

    def _register_phase3_device(self, local_user_id: int) -> dict:
        device = db.get_or_create_cloud_device(local_user_id)
        try:
            row = self.cloud.register_cloud_device(device)
            if isinstance(row, list):
                row = row[0] if row else {}
            row = row or {}
            db.mark_cloud_device_registered(local_user_id, row.get("first_seen_at"), row.get("last_seen_at"))
            return {"available": True, "device": device}
        except Exception as exc:
            return {"available": False, "device": device, "error": str(exc)}

    def _queue_personal_if_changed(self, local_user_id: int, force=False):
        state = db.get_cloud_personal_sync_state(local_user_id)
        if state.get("conflict_status") == "needs_resolution" and not force:
            return {"queued": False, "conflict": True}
        snapshot = db.build_cloud_personal_snapshot(local_user_id)
        local_hash = db.cloud_personal_snapshot_hash(snapshot)
        if not force and state.get("last_local_hash") == local_hash:
            return {"queued": False, "unchanged": True}
        if not state and db.cloud_personal_snapshot_is_empty(snapshot):
            return {"queued": False, "empty": True}
        device = db.get_or_create_cloud_device(local_user_id)
        payload = {
            "document_key": "tracker_v1",
            "base_revision": int(state.get("remote_revision") or 0),
            "content_hash": local_hash,
            "payload": snapshot,
            "device_id": device["device_id"],
        }
        db.enqueue_sync(local_user_id, "personal_snapshot", "tracker_v1", "upsert", payload)
        return {"queued": True, "hash": local_hash}

    def _pull_personal(self, local_user_id: int) -> dict:
        rows = self.cloud.get_personal_snapshots()
        remote = next((row for row in rows if row.get("document_key") == "tracker_v1"), None)
        if not remote:
            return {"available": True, "remote": False}

        remote_payload = remote.get("payload") or {}
        remote_hash = db.cloud_personal_snapshot_hash(remote_payload)
        # Compare semantic JSON rather than trusting client-supplied hash metadata.
        remote = dict(remote)
        remote["content_hash"] = remote_hash
        remote_revision = int(remote.get("revision") or 0)
        state = db.get_cloud_personal_sync_state(local_user_id)
        local_snapshot = db.build_cloud_personal_snapshot(local_user_id)
        local_hash = db.cloud_personal_snapshot_hash(local_snapshot)

        if state.get("conflict_status") == "needs_resolution":
            if remote_revision > int(state.get("remote_revision") or 0):
                db.record_cloud_personal_conflict(local_user_id, remote, local_snapshot)
            return {"available": True, "remote": True, "conflict": True,
                    "revision": remote_revision}

        if not state:
            if local_hash == remote_hash:
                db.record_cloud_personal_synced(local_user_id, remote, local_hash, "pull")
                return {"available": True, "remote": True, "matched": True,
                        "revision": remote_revision}
            if db.cloud_personal_snapshot_is_empty(local_snapshot):
                applied = db.apply_cloud_personal_snapshot(local_user_id, remote_payload)
                db.record_cloud_personal_synced(local_user_id, remote, applied["local_hash"],
                                                "pull", applied["local_backup"])
                return {"available": True, "remote": True, "applied": True,
                        "revision": remote_revision}
            db.record_cloud_personal_conflict(local_user_id, remote, local_snapshot)
            return {"available": True, "remote": True, "conflict": True,
                    "revision": remote_revision}

        known_revision = int(state.get("remote_revision") or 0)
        if remote_revision > known_revision:
            if local_hash == state.get("last_local_hash"):
                applied = db.apply_cloud_personal_snapshot(local_user_id, remote_payload)
                db.record_cloud_personal_synced(local_user_id, remote, applied["local_hash"],
                                                "pull", applied["local_backup"])
                return {"available": True, "remote": True, "applied": True,
                        "revision": remote_revision}
            if local_hash == remote_hash:
                db.record_cloud_personal_synced(local_user_id, remote, local_hash, "pull")
                return {"available": True, "remote": True, "matched": True,
                        "revision": remote_revision}
            db.record_cloud_personal_conflict(local_user_id, remote, local_snapshot)
            return {"available": True, "remote": True, "conflict": True,
                    "revision": remote_revision}
        return {"available": True, "remote": True, "unchanged": True,
                "revision": remote_revision}

    def resolve_personal_conflict_keep_local(self, local_user_id: int) -> dict:
        if not self.ensure_session(local_user_id):
            return {"ok": False, "code": "auth_required"}
        state = db.get_cloud_personal_sync_state(local_user_id)
        if state.get("conflict_status") != "needs_resolution":
            return {"ok": False, "code": "no_conflict"}
        phase3 = self._register_phase3_device(local_user_id)
        if not phase3.get("available"):
            return {"ok": False, "code": "phase3_unavailable", "error": phase3.get("error")}
        db.mark_cloud_personal_resolution_pending(local_user_id)
        self._queue_personal_if_changed(local_user_id, force=True)
        return self.sync_now(local_user_id)

    def resolve_personal_conflict_use_cloud(self, local_user_id: int) -> dict:
        if not self.ensure_session(local_user_id):
            return {"ok": False, "code": "auth_required"}
        state = db.get_cloud_personal_sync_state(local_user_id)
        payload = state.get("remote_payload")
        if state.get("conflict_status") != "needs_resolution" or not payload:
            return {"ok": False, "code": "no_conflict"}
        applied = db.apply_cloud_personal_snapshot(local_user_id, payload)
        remote = {
            "revision": int(state.get("remote_revision") or 0),
            "content_hash": db.cloud_personal_snapshot_hash(payload),
            "server_updated_at": state.get("remote_updated_at"),
        }
        db.record_cloud_personal_synced(local_user_id, remote, applied["local_hash"],
                                        "pull", applied["local_backup"])
        return {"ok": True, "applied": True, "revision": remote["revision"]}

    def _process_queue(self, local_user_id: int) -> dict:
        done = failed = conflicts = 0
        for job in db.get_pending_sync_jobs(local_user_id, 30):
            try:
                entity, operation = job["entity_type"], job["operation"]
                if entity == "profile" and operation == "upsert":
                    self.cloud.upsert_profile_from_local(local_user_id)
                elif entity == "profile_photo" and operation == "upload":
                    self.cloud.upload_profile_photo(local_user_id)
                elif entity == "profile_photo" and operation == "delete":
                    self.cloud.delete_profile_photo()
                elif entity == "direct_message" and operation == "send":
                    payload = json.loads(job.get("payload") or "{}")
                    self.cloud.send_direct_message(payload["conversation_id"],payload["body"],payload["client_message_id"],payload.get("reply_to_id"))
                elif entity == "direct_message_attachment" and operation == "send":
                    payload=json.loads(job.get("payload") or "{}")
                    self.cloud.send_direct_message_with_attachments(local_user_id,payload["conversation_id"],payload.get("body") or "",
                        payload["client_message_id"],payload.get("reply_to_id"),payload.get("attachment_local_ids") or [])
                elif entity == "productivity_event" and operation == "record":
                    payload = json.loads(job.get("payload") or "{}")
                    self.cloud.record_productivity_event(payload)
                elif entity == "love_space_bundle" and operation == "migrate":
                    payload=json.loads(job.get("payload") or "{}")
                    love_space_id=payload.get("love_space_id") or db.get_cloud_love_space_id(local_user_id)
                    if not love_space_id:raise RuntimeError("Cloud Love Space has not been synchronized yet")
                    self.cloud.migrate_love_space_from_local(local_user_id,love_space_id)
                elif entity == "personal_snapshot" and operation == "upsert":
                    payload = json.loads(job.get("payload") or "{}")
                    response = self.cloud.upsert_personal_snapshot(
                        payload["document_key"], payload["base_revision"],
                        payload["content_hash"], payload["payload"], payload["device_id"])
                    if isinstance(response, list):
                        response = response[0] if response else {}
                    response = response or {}
                    if response.get("conflict"):
                        remote = response.get("snapshot") or {}
                        if remote:
                            db.record_cloud_personal_conflict(local_user_id, remote, payload["payload"])
                        db.mark_sync_job_done(job["id"])
                        done += 1; conflicts += 1
                        continue
                    remote = response.get("snapshot") or {}
                    db.record_cloud_personal_synced(local_user_id, remote,
                                                    payload["content_hash"], "push")
                elif entity == "gallery_photo" and operation == "delete":
                    payload = json.loads(job.get("payload") or "{}")
                    self.cloud.delete_gallery_photo(payload.get("cloud_id"), payload.get("storage_path"))
                elif entity == "gallery_photo" and operation == "upload":
                    context = db.get_couple_context(local_user_id)
                    photo = db.get_love_space_photo(local_user_id, int(job["entity_local_id"]))
                    if not photo:
                        raise RuntimeError("Local gallery photo no longer exists")
                    if photo.get("visibility") == "shared" and not context.get("active"):
                        raise RuntimeError("A shared gallery upload requires an active cloud couple")
                    cloud_space = db.get_cloud_id("love_space", context.get("love_space_id")) if context.get("love_space_id") else None
                    if photo.get("visibility") == "shared" and not cloud_space:
                        raise RuntimeError("Cloud Love Space has not been synchronized yet")
                    self.cloud.upload_gallery_photo(int(job["entity_local_id"]), cloud_space)
                else:
                    raise RuntimeError(f"Unsupported sync job: {entity}/{operation}")
                db.mark_sync_job_done(job["id"]); done += 1
            except Exception as exc:
                retry = int(job.get("retry_count") or 0) + 1
                db.mark_sync_job_failed(job["id"], str(exc), retry); failed += 1
        return {"done": done, "failed": failed, "conflicts": conflicts}

    def _pull_social(self, local_user_id: int) -> dict:
        client = self.cloud._require_auth()
        cloud_uid = self.cloud.current_cloud_user_id
        friendships = _response_data(client.table("friendships").select("*").or_(
            f"requester_id.eq.{cloud_uid},addressee_id.eq.{cloud_uid}").execute()) or []
        couples = _response_data(client.table("couple_relationships").select("*").or_(
            f"user_a_id.eq.{cloud_uid},user_b_id.eq.{cloud_uid}").execute()) or []
        user_ids = {cloud_uid}
        for row in friendships:
            user_ids.update((row["requester_id"], row["addressee_id"]))
        for row in couples:
            user_ids.update((row["user_a_id"], row["user_b_id"], row["requested_by"]))
        profiles = _response_data(client.table("profiles").select("*").in_("id", list(user_ids)).execute()) or []
        profile_map = {str(row["id"]): row for row in profiles}
        for cloud_id in user_ids:
            if cloud_id in profile_map:
                db.upsert_cloud_profile(cloud_id, profile_map[cloud_id])
        for row in friendships:
            db.mirror_cloud_friendship(row, profile_map)
        db.prune_cloud_friendships(local_user_id, [str(row["id"]) for row in friendships])
        local_couples = {}
        for row in couples:
            local_couples[str(row["id"])] = db.mirror_cloud_couple(row, profile_map)

        spaces = _response_data(client.table("love_spaces").select("*").execute()) or []
        members = _response_data(client.table("love_space_members").select("*").execute()) or []
        shared_love={"available":False,"records":0}
        for space in spaces:
            cloud_rel = str(space["couple_relationship_id"])
            local_rel = local_couples.get(cloud_rel)
            if not local_rel:
                continue
            cloud_member_ids = [m["user_id"] for m in members if str(m["love_space_id"]) == str(space["id"])]
            local_members = [db.get_local_user_id_for_cloud(cid) for cid in cloud_member_ids]
            local_members = [uid for uid in local_members if uid]
            local_space = db.mirror_cloud_love_space(space, local_rel, local_members)
            db.save_cloud_entity_map(local_user_id, "love_space", local_space, str(space["id"]))
            try:
                bundle=self.cloud.fetch_love_space_bundle(str(space["id"]))
                mirrored=db.mirror_cloud_love_bundle(local_user_id,bundle)
                shared_love={"available":True,**mirrored}
            except Exception as exc:
                # Phase 1-3 continue to work before the additive Phase 4A migration is pushed.
                shared_love={"available":False,"records":0,"error":str(exc)}

        photos = _response_data(client.table("love_space_photos").select("*").execute()) or []
        cached = 0
        for photo in photos:
            try:
                raw = self.cloud.download_storage(self.cloud.config.gallery_bucket, photo["storage_path"])
                jpeg, width, height = self._webp_to_jpeg(raw)
                if db.cache_cloud_gallery_photo(photo, jpeg, "image/jpeg", width, height).get("ok"):
                    cached += 1
            except Exception:
                continue
        presence = self.cloud.get_presence(list(user_ids)); db.cache_cloud_presence(presence)
        notifications = self.cloud.get_social_notifications(False,100); db.cache_cloud_notifications(local_user_id,notifications)
        try:
            conversation_summaries=self.cloud.get_direct_conversation_summaries()
            db.cache_cloud_conversation_summaries(local_user_id,conversation_summaries)
        except Exception:
            conversation_summaries=[]
        device = db.get_or_create_cloud_device(local_user_id)
        self.cloud.heartbeat_presence("online",device.get("device_name") or "CraftLife Desktop")
        self._pull_profile_photos(profile_map)
        return {"friendships": len(friendships), "couples": len(couples),
                "love_spaces": len(spaces), "shared_love": shared_love,
                "gallery_cached":cached,"presence":len(presence),"notifications":len(notifications),
                "conversation_summaries":len(conversation_summaries)}

    def _pull_profile_photos(self, profile_map):
        for cloud_id, profile in profile_map.items():
            path = profile.get("avatar_path")
            local_id = db.get_local_user_id_for_cloud(cloud_id)
            if not path or not local_id:
                continue
            try:
                raw = self.cloud.download_storage(self.cloud.config.profile_bucket, path)
                jpeg, width, height = self._webp_to_jpeg(raw)
                db.cache_cloud_profile_photo(local_id, jpeg, "image/jpeg", width, height)
            except Exception:
                continue

    @staticmethod
    def _webp_to_jpeg(raw: bytes):
        if Image is None:
            raise RuntimeError("Pillow is required for cloud photo cache")
        with Image.open(io.BytesIO(raw)) as image:
            image.load(); image = image.convert("RGB")
            image.thumbnail((1600, 1600), Image.Resampling.LANCZOS)
            output = io.BytesIO(); image.save(output, "JPEG", quality=88)
            return output.getvalue(), image.width, image.height


_sync_service = None


def get_sync_service() -> CloudSyncService:
    global _sync_service
    if _sync_service is None:
        _sync_service = CloudSyncService()
    return _sync_service
