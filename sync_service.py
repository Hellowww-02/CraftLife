"""Offline-first Supabase sync orchestration for CraftLife Desktop.

SQLite remains the source used by the UI. Supabase adds server-authoritative social
features and Phase 3 conflict-safe personal tracker replication.
"""
from __future__ import annotations

from typing import Optional

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
        status["queue_failed_samples"] = db.get_sync_failed_samples(local_user_id, 3)
        status["queue_all"] = db.get_all_sync_jobs(local_user_id, 8)
        status["device"] = db.get_or_create_cloud_device(local_user_id)
        status["personal"] = db.get_cloud_personal_sync_state(local_user_id)
        return status

    def inspect_queue(self, local_user_id: int) -> dict:
        jobs = db.get_all_sync_jobs(local_user_id, 50)
        summary = db.sync_queue_summary(local_user_id)
        failed = db.get_sync_failed_samples(local_user_id, 10)
        return {"summary": summary, "jobs": jobs, "failed_samples": failed}

    def retry_failed_now(self, local_user_id: int) -> dict:
        reset = db.reset_sync_backoff(local_user_id)
        result = self.sync_now(local_user_id, force_retry=True)
        result["reset"] = reset
        return result

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

    @staticmethod
    def _quota_seen(node) -> Optional[str]:
        """Cari jejak kuota/402 di dalam struktur hasil sync yang bersarang.

        Error per-kanal disimpan sebagai STRING, bukan exception, jadi
        classify_cloud_error() tidak bisa dipakai langsung pada hasilnya.
        Fungsi ini menelusuri dict/list dan mengklasifikasi setiap string.
        """
        if isinstance(node, str):
            from cloud_service import classify_cloud_error
            kind = classify_cloud_error(Exception(node))
            return kind if kind in ("quota", "rate_limited") else None
        # Rujukan lewat nama kelas, bukan `self`: ini staticmethod, jadi `self`
        # tidak ada di dalamnya.
        if isinstance(node, dict):
            for value in node.values():
                found = CloudSyncService._quota_seen(value)
                if found:
                    return found
        elif isinstance(node, (list, tuple)):
            for value in node:
                found = CloudSyncService._quota_seen(value)
                if found:
                    return found
        return None

    def sync_now(self, local_user_id: int, force_retry: bool = False) -> dict:
        if not self._lock.acquire(blocking=False):
            return {"ok": False, "code": "already_running"}
        # Berhenti menembak project yang sedang dibatasi. Selama masa tunggu,
        # satu permintaan pun tidak dikirim — itu inti dari penanganan 402.
        # force_retry tetap diizinkan: pengguna yang sengaja menekan tombol
        # sync berarti ingin mencoba lagi sekarang.
        if not force_retry:
            suspended, reason = db.cloud_suspension_active(local_user_id)
            if suspended:
                self._lock.release()
                return {"ok": False, "code": "cloud_suspended", "reason": reason,
                        "retry_after_seconds": db.CLOUD_SUSPEND_PROBE_SECONDS}
        try:
            if force_retry:
                try: db.reset_sync_backoff(local_user_id)
                except Exception: pass
            if not self.ensure_session(local_user_id):
                return {"ok": False, "code": "auth_required", "status": self.cloud_status(local_user_id)}

            # Phase 3 is intentionally backward-compatible: if its migration has
            # not been pushed yet, Phase 1/2 sync still works and reports the reason.
            phase3 = self._register_phase3_device(local_user_id)
            personal = {"available": False, "reason": phase3.get("error", "migration_not_applied")}
            channel_a = {"available": False, "reason": phase3.get("error", "migration_not_applied")}
            channel_b = {"available": False, "reason": phase3.get("error", "migration_not_applied")}
            if phase3.get("available"):
                personal = self._pull_personal(local_user_id)
                self._queue_personal_if_changed(local_user_id)
                channel_a = self._sync_channel_a(local_user_id)
                channel_b = self._sync_channel_b(local_user_id)

            pushed = self._process_queue(local_user_id, force=force_retry)
            pulled = self._pull_social(local_user_id)
            try:
                wallet = self.cloud.wallet_balance() or {}
                db.save_cloud_wallet(local_user_id, wallet)
                pulled = {**pulled, "wallet": True}
            except Exception:
                pulled = {**pulled, "wallet": False}
            try:
                db.save_cloud_inventory(local_user_id, self.cloud.fetch_cloud_inventory())
                pulled = {**pulled, "inventory": True}
            except Exception:
                pulled = {**pulled, "inventory": False}
            maintenance = {}
            if phase3.get("available"):
                try:
                    maintenance = self.cloud.run_cloud_maintenance() or {}
                    try:maintenance["guild"]=self.cloud.run_online_guild_maintenance() or {}
                    except Exception as guild_exc:maintenance["guild"]={"ok":False,"error":str(guild_exc)}
                except Exception as exc:
                    maintenance = {"ok": False, "error": str(exc)}
            # Error per-kanal datang sebagai string, bukan exception, jadi
            # 402 bisa lolos dari handler di bawah kalau tidak dipindai di sini.
            quota = self._quota_seen({
                "personal": personal, "channel_a": channel_a,
                "channel_b": channel_b, "phase3": phase3,
                "maintenance": maintenance,
            })
            if quota:
                db.set_cloud_suspended(local_user_id, quota)
                self.last_result = {"ok": False, "code": "cloud_suspended",
                                    "reason": quota}
                return self.last_result
            db.clear_cloud_suspended(local_user_id)
            db.mark_cloud_sync_complete(local_user_id)
            self.last_result = {
                "ok": True, "pushed": pushed, "pulled": pulled,
                "personal": personal, "phase3": phase3,
                "channel_a": channel_a,
                "channel_b": channel_b,
                "maintenance": maintenance,
                "synced_at": datetime.now().isoformat(),
            }
            return self.last_result
        except Exception as exc:
            from cloud_service import classify_cloud_error
            kind = classify_cloud_error(exc)
            if kind in ("quota", "rate_limited"):
                db.set_cloud_suspended(local_user_id, kind)
                self.last_result = {"ok": False, "code": "cloud_suspended",
                                    "reason": kind, "error": str(exc)}
            else:
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
        parts = db.split_cloud_personal_snapshot(snapshot)
        if len(parts) <= 1:
            db.enqueue_sync(local_user_id, "personal_snapshot", "tracker_v1", "upsert", payload)
            return {"queued": True, "hash": local_hash}
        # M11 (G5): dokumen besar diantrekan sebagai part. Manifest (part 0)
        # PALING TERAKHIR supaya drain FIFO menyelesaikan part data lebih
        # dulu; penerima tetap memvalidasi kelengkapan satu generasi, jadi
        # urutan ini optimasi, bukan syarat kebenaran.
        for part in reversed(parts):
            meta = part["part"]
            part_payload = {
                "document_key": db.snapshot_part_key(meta["index"]),
                "base_revision": 0,
                "content_hash": local_hash,
                "payload": part,
                "device_id": device["device_id"],
                "part": meta,
            }
            db.enqueue_sync(local_user_id, "personal_snapshot",
                            part_payload["document_key"], "upsert", part_payload)
        return {"queued": True, "hash": local_hash, "parts": len(parts)}

    def _pull_personal(self, local_user_id: int) -> dict:
        # CEK VERSI DULU, baru unduh.
        #
        # get_personal_snapshots() memakai .select("*") sehingga payload penuh
        # ikut terkirim. Padahal get_personal_snapshot_versions() hanya meminta
        # kolom metadata (id, document_key, revision, content_hash, ...) tanpa
        # payload. Dulu dokumen tracker diunduh penuh setiap 60 detik hanya
        # untuk sampai ke cabang "unchanged" di bawah.
        #
        # Aman karena revision dinaikkan server setiap tulis
        # (`revision=revision+1`), jadi revision yang tidak naik berarti
        # benar-benar tidak ada yang berubah. Dua keadaan sengaja TIDAK
        # mengambil jalan pintas: belum pernah sync sama sekali (`not state`),
        # dan konflik yang menunggu penyelesaian — keduanya tetap butuh payload.
        state = db.get_cloud_personal_sync_state(local_user_id)
        if state and state.get("conflict_status") != "needs_resolution":
            known_revision = int(state.get("remote_revision") or 0)
            try:
                # M11: generasi part memakai revisi manifest (part/000)
                # sebagai penanda versi; dokumen tunggal lama tetap dibaca.
                versions = self.cloud.get_personal_snapshot_versions(
                    db.snapshot_part_key(0), limit=1)
                if not versions:
                    versions = self.cloud.get_personal_snapshot_versions("tracker_v1", limit=1)
            except Exception:
                versions = None
            latest = (versions or [None])[0]
            if latest is not None:
                remote_revision = int(latest.get("revision") or 0)
                if remote_revision <= known_revision:
                    return {"available": True, "remote": True, "unchanged": True,
                            "revision": remote_revision, "skippedDownload": True}
        rows = self.cloud.get_personal_snapshots()
        # M11 (G5): utamakan dokumen part bila ada. Set part yang belum
        # lengkap (perangkat lain sedang mengunggah) berarti "belum ada
        # yang bisa diterapkan siklus ini" — bukan error dan bukan konflik.
        part_rows = [r for r in (rows or [])
                     if str(r.get("document_key") or "").startswith(db.SNAPSHOT_PART_KEY_PREFIX)]
        if part_rows:
            merged = db.merge_cloud_personal_parts([r.get("payload") or {} for r in part_rows])
            if merged is None:
                return {"available": True, "remote": True, "partsIncomplete": True}
            manifest = next((r for r in part_rows
                             if r.get("document_key") == db.snapshot_part_key(0)), part_rows[0])
            remote = {"document_key": "tracker_v1", "payload": merged,
                      "revision": int(manifest.get("revision") or 0),
                      "content_hash": manifest.get("content_hash"),
                      "server_updated_at": manifest.get("server_updated_at")}
        else:
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

    def _sync_channel_a(self, local_user_id: int) -> dict:
        """M04a Kanal A: union-merge tabel append-only.

        Sengaja aditif dan tahan gagal, mengikuti pola fallback Phase 3 di atas:
        kalau migrasi M04a belum diterapkan ke proyek Supabase, fungsi ini
        melaporkan alasannya dan sisa sync tetap jalan.

        Urutannya push lalu pull per tabel. Push dulu supaya baris lokal sudah
        ada di server sebelum pull, sehingga satu putaran sync langsung
        menyatukan kedua arah.
        """
        device = db.get_or_create_cloud_device(local_user_id)
        device_id = device["device_id"]
        pushed, pulled, errors = {}, {}, {}
        for table in db.APPEND_ONLY_TABLES:
            try:
                batch = db.build_entity_append_batch(local_user_id, table, limit=5000)
                if batch:
                    result = self.cloud.append_entities(table, batch, device_id)
                    if isinstance(result, list):
                        result = result[0] if result else {}
                    pushed[table] = int((result or {}).get("inserted") or 0)
                # INKREMENTAL, bukan tarikan penuh. Tabel append-only tidak
                # pernah berubah setelah ditulis, jadi meminta yang lebih baru
                # dari watermark saja sudah lengkap — dan itu yang membedakan
                # beberapa baris per menit dari seluruh riwayat tiap 60 detik.
                remote = self.cloud.fetch_entities(
                    table, since=db.channel_a_since(local_user_id, table))
                if isinstance(remote, list):
                    remote = remote[0] if remote else {}
                rows = (remote or {}).get("rows") or []
                applied = db.apply_entity_append_rows(local_user_id, table, rows)
                pulled[table] = int(applied.get("inserted") or 0)
                # Watermark maju ke server_updated_at tertinggi yang diterima.
                # channel_a_since() mengurangi overlap 1 detik, dan baris yang
                # terambil ulang dilewati berdasarkan uuid, jadi batas limit
                # tidak bisa menghilangkan baris.
                marks = [r.get("server_updated_at") for r in rows
                         if isinstance(r, dict) and r.get("server_updated_at")]
                if marks:
                    db.set_channel_a_watermark(local_user_id, table, max(marks))
            except Exception as exc:
                errors[table] = str(exc)[:200]
        if errors and len(errors) == len(db.APPEND_ONLY_TABLES):
            return {"available": False, "reason": next(iter(errors.values()))}
        return {"available": True, "pushed": pushed, "pulled": pulled, "errors": errors}

    def _sync_channel_b(self, local_user_id: int) -> dict:
        """M04b Kanal B: merge 3-way untuk tabel mutable.

        Urutan per tabel: kirim tombstone dulu (supaya penghapusan tidak kalah
        oleh baris yang baru saja di-push), lalu upsert baris, lalu tarik
        tombstone perangkat lain. Sama seperti Kanal A, gagal di satu tabel tidak
        membatalkan tabel lain.
        """
        device = db.get_or_create_cloud_device(local_user_id)
        device_id = device["device_id"]
        pushed, deleted_remote, errors = {}, {}, {}
        for table in db.CHANNEL_B_TABLES:
            try:
                pending = db.pending_sync_tombstones(table)
                if pending:
                    self.cloud.push_tombstones(table, pending, device_id)
                    db.mark_tombstones_pushed(table, [t["uuid"] for t in pending])

                batch = db.build_entity_change_batch(local_user_id, table, limit=5000)
                if batch:
                    result = self.cloud.upsert_entities(table, batch, device_id)
                    if isinstance(result, list):
                        result = result[0] if result else {}
                    pushed[table] = {
                        "sent": len(batch),
                        "inserted": int((result or {}).get("inserted") or 0),
                        "updated": int((result or {}).get("updated") or 0),
                        "field_conflicts": int((result or {}).get("field_conflicts") or 0),
                    }
                    # Catat rev yang diakui server sebagai base_rev berikutnya.
                    # Tanpa langkah ini sync_entity_state tidak pernah maju:
                    # setiap push berikutnya tetap mengaku base_rev 0, server
                    # tidak menemukan sisi "base", dan merge 3-way diam-diam
                    # turun kelas menjadi LWW 2-way selamanya.
                    acked = (result or {}).get("rows") or []
                    if acked:
                        db.record_entity_revisions_synced(local_user_id, table, acked)

                remote = self.cloud.fetch_tombstones(table)
                if isinstance(remote, list):
                    remote = remote[0] if remote else {}
                rows = (remote or {}).get("rows") or []
                if rows:
                    applied = db.apply_entity_tombstones(local_user_id, table, rows)
                    if applied["deleted"]:
                        deleted_remote[table] = applied["deleted"]
            except Exception as exc:
                errors[table] = str(exc)[:200]
        if errors and len(errors) == len(db.CHANNEL_B_TABLES):
            return {"available": False, "reason": next(iter(errors.values()))}
        return {"available": True, "pushed": pushed,
                "deleted_remotely": deleted_remote, "errors": errors}

    def _process_queue(self, local_user_id: int, force: bool = False) -> dict:
        done = failed = conflicts = 0        # Untuk manual Sync Sekarang kita paksa retry walau masih dalam backoff,
        # agar error langsung terlihat (queue 33 tidak lagi \"nyangkut diam\").
        jobs = db.get_all_sync_jobs(local_user_id, 30) if force else db.get_pending_sync_jobs(local_user_id, 30)
        # Filter hanya pending/retry yang siap diproses; jika force, abaikan next_retry_at
        if force:
            jobs = [j for j in jobs if j.get("status") in ("pending","retry")]
        for job in jobs[:30]:
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
                    if payload.get("part"):
                        # M11: part punya revisi sendiri-sendiri. Konflik di
                        # sini berarti basis kita basi (part sudah pernah
                        # terunggah) — ambil revisi terbaru lalu coba sekali
                        # lagi. Ini BUKAN konflik data pengguna.
                        if isinstance(response, dict) and response.get("conflict"):
                            versions = self.cloud.get_personal_snapshot_versions(
                                payload["document_key"], limit=1) or []
                            base = int((versions[0] if versions else {}).get("revision") or 0)
                            # get_personal_snapshot_versions membaca tabel
                            # versi; revisi berjalan ada di baris snapshot.
                            rows = self.cloud.get_personal_snapshots() or []
                            for row in rows:
                                if row.get("document_key") == payload["document_key"]:
                                    base = int(row.get("revision") or base)
                            response = self.cloud.upsert_personal_snapshot(
                                payload["document_key"], base,
                                payload["content_hash"], payload["payload"], payload["device_id"])
                        if isinstance(response, dict) and response.get("conflict"):
                            raise RuntimeError("snapshot_part_conflict")
                        remaining = [j for j in db.get_pending_sync_jobs(local_user_id, 50)
                                     if j.get("entity_type") == "personal_snapshot"
                                     and int(j.get("id") or 0) != int(job.get("id") or 0)]
                        if not remaining:
                            manifest = response.get("snapshot") if isinstance(response, dict) else {}
                            if payload["part"].get("index") != 0:
                                rows = self.cloud.get_personal_snapshots() or []
                                manifest = next((r for r in rows
                                                 if r.get("document_key") == db.snapshot_part_key(0)), manifest)
                            db.record_cloud_personal_synced(local_user_id, manifest or {},
                                                            payload["content_hash"], "push")
                        db.mark_sync_job_done(job["id"]); done += 1
                        continue
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
                elif entity == "event_append" and operation == "append":
                    # M04a Kanal A. Idempoten di server (insert-if-absent by
                    # uuid), jadi memproses job ini dua kali aman.
                    payload = json.loads(job.get("payload") or "{}")
                    table = payload.get("table")
                    rows = db.build_entity_append_batch(
                        local_user_id, table, only_uuid=payload.get("uuid"))
                    if rows:
                        device = db.get_or_create_cloud_device(local_user_id)
                        self.cloud.append_entities(table, rows, device["device_id"])
                    # Baris yang sudah tidak ada secara lokal bukan error: Kanal A
                    # tidak pernah menghapus, jadi tidak ada yang perlu dirambatkan.
                elif entity == "achievement_claim" and operation == "claim":
                    payload = json.loads(job.get("payload") or "{}")
                    try:
                        # M09b: klaim server kini mensyaratkan catatan unlock
                        # di cloud_user_achievements — catat dulu (idempoten),
                        # baru klaim. Kunci tak dikenal di server = selesai
                        # (achievement lokal lama tanpa definisi server).
                        try:
                            self.cloud.record_achievement_unlock_cloud(payload["achievement_key"])
                        except Exception as exc:
                            if "unknown_achievement" not in str(exc).lower():
                                raise
                        self.cloud.claim_achievement_reward_cloud(payload["achievement_key"], payload["claim_key"])
                    except Exception as exc:
                        # Klaim ganda (sudah diklaim device lain) = sukses idempoten.
                        if "achievement_already_claimed" not in str(exc).lower():
                            raise
                elif entity == "shop_buy" and operation == "buy":
                    payload = json.loads(job.get("payload") or "{}")
                    try:
                        self.cloud.buy_shop_item(payload["item_key"], int(payload.get("qty") or 1), payload["idempotency_key"])
                    except Exception as exc:
                        if not any(c in str(exc).lower() for c in ("insufficient_balance", "unknown_item", "limit_reached")):
                            raise
                elif entity == "craft" and operation == "craft":
                    payload = json.loads(job.get("payload") or "{}")
                    try:
                        self.cloud.craft_item_cloud(payload["recipe_key"], payload["idempotency_key"])
                    except Exception as exc:
                        if not any(c in str(exc).lower() for c in ("missing_materials", "unknown_recipe", "insufficient_balance")):
                            raise
                elif entity == "enchant" and operation == "enchant":
                    payload = json.loads(job.get("payload") or "{}")
                    try:
                        self.cloud.enchant_item_cloud(payload["item_key"], payload["idempotency_key"])
                    except Exception as exc:
                        if not any(c in str(exc).lower() for c in ("item_not_owned", "max_enchant", "insufficient_balance")):
                            raise
                elif entity == "talent_unlock" and operation == "unlock":
                    payload = json.loads(job.get("payload") or "{}")
                    try:
                        self.cloud.unlock_talent_cloud(payload["talent_key"])
                    except Exception as exc:
                        # Penolakan bisnis server (class/poin/level/prasyarat/
                        # kunci asing) adalah keputusan otoritatif: job
                        # selesai, state lokal tidak diubah paksa.
                        if not any(c in str(exc).lower() for c in ("unknown_talent", "talent_class_mismatch", "talent_no_points", "talent_level_required", "talent_prereq_required")):
                            raise
                elif entity == "boss_reward" and operation == "claim":
                    payload = json.loads(job.get("payload") or "{}")
                    try:
                        self.cloud.claim_boss_reward_cloud(payload["boss_key"], int(payload.get("member_count") or 1), payload["idempotency_key"])
                    except Exception as exc:
                        if "unknown_boss" not in str(exc).lower():
                            raise
                elif entity == "couple_end" and operation == "end":
                    payload = json.loads(job.get("payload") or "{}")
                    try:
                        self.cloud.end_couple_relationship(payload["cloud_id"])
                    except Exception as exc:
                        # Relasi sudah tidak ada di server (DB reset/akun dihapus) = sukses.
                        low = str(exc).lower()
                        if not ("invalid_relationship" in low or "p0001" in low
                                or "not found" in low or "does not exist" in low):
                            raise
                elif entity == "gallery_photo" and operation == "delete":
                    payload = json.loads(job.get("payload") or "{}")
                    self.cloud.delete_gallery_photo(payload.get("cloud_id"), payload.get("storage_path"))
                elif entity == "gallery_photo" and operation == "upload":
                    context = db.get_couple_context(local_user_id)
                    # Gunakan raw agar foto shared yang belum terlihat di get_love_space_photos tetap bisa di-sync
                    raw_photo = db.get_love_space_photo_raw(int(job["entity_local_id"]))
                    if not raw_photo:
                        raise RuntimeError("Local gallery photo no longer exists (id tidak ditemukan)")
                    if int(raw_photo.get("owner_user_id") or 0) != int(local_user_id):
                        raise RuntimeError("Hanya pemilik foto yang bisa sync foto ini")
                    if raw_photo.get("visibility") == "shared" and not context.get("active"):
                        raise RuntimeError("Foto shared butuh Couple aktif di cloud — ubah ke Private atau buat Couple dulu")
                    cloud_space = db.get_cloud_id("love_space", context.get("love_space_id")) if context.get("love_space_id") else None
                    if raw_photo.get("visibility") == "shared" and not cloud_space:
                        raise RuntimeError("Cloud Love Space belum tersinkron — lakukan Sync dulu sampai couple terbaca")
                    self.cloud.upload_gallery_photo(int(job["entity_local_id"]), cloud_space)
                else:
                    raise RuntimeError(f"Unsupported sync job: {entity}/{operation}")
                db.mark_sync_job_done(job["id"]); done += 1
            except Exception as exc:
                retry = int(job.get("retry_count") or 0) + 1
                db.mark_sync_job_failed(job["id"], str(exc), retry); failed += 1
        return {"done": done, "failed": failed, "conflicts": conflicts}

    def pull_social_now(self, local_user_id: int) -> dict:
        """P61: mirror ringan social/couple cloud → lokal TANPA maintenance/wallet.
        Best-effort — dipanggil jalur Love Space (GET /api/love) supaya relasi couple
        yang terjadi di device lain langsung terdeteksi, bukan hanya saat sync penuh."""
        if not self._lock.acquire(blocking=False):
            return {"ok": False, "code": "busy"}
        try:
            if not self.ensure_session(local_user_id):
                return {"ok": False, "code": "auth_required"}
            pulled = self._pull_social(local_user_id)
            return {"ok": True, **(pulled if isinstance(pulled, dict) else {})}
        except Exception as exc:
            return {"ok": False, "code": "error", "error": str(exc)}
        finally:
            self._lock.release()

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
            if row["user_a_id"] not in profile_map or row["user_b_id"] not in profile_map:
                # Akun pasangan sudah tidak ada di cloud (dihapus) → akhiri relasi lokal.
                db.end_cloud_orphan_couple(local_user_id, str(row["id"]))
                continue
            local_couples[str(row["id"])] = db.mirror_cloud_couple(row, profile_map)
        db.prune_cloud_couples(local_user_id, [str(row["id"]) for row in couples])

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
