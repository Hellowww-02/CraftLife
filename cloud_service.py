"""Supabase client boundary for CraftLife.

The desktop app uses only the publishable key. Authorization remains enforced by
PostgreSQL RLS/RPC and private Storage policies.
"""
from __future__ import annotations

import asyncio
import io
import hashlib
import logging
import mimetypes
import threading
import uuid
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from cloud_config import CloudConfig, load_cloud_config

log = logging.getLogger("craftlife.cloud")

try:
    from supabase import Client, acreate_client, create_client
    from realtime.types import RealtimePostgresChangesListenEvent
    SUPABASE_AVAILABLE = True
except ImportError:
    Client = Any
    acreate_client = None
    create_client = None
    RealtimePostgresChangesListenEvent = None
    SUPABASE_AVAILABLE = False

try:
    import keyring
    KEYRING_AVAILABLE = True
except ImportError:
    keyring = None
    KEYRING_AVAILABLE = False

try:
    from PIL import Image, ImageOps
    PILLOW_AVAILABLE = True
except ImportError:
    Image = None
    PILLOW_AVAILABLE = False

_KEYRING_SERVICE = "CraftLife Supabase"


def _response_data(response):
    if response is None:
        return None
    if isinstance(response, dict):
        return response.get("data", response)
    return getattr(response, "data", None)


def _auth_user(response):
    return getattr(response, "user", None) or (
        response.get("user") if isinstance(response, dict) else None
    )


def _auth_session(response):
    return getattr(response, "session", None) or (
        response.get("session") if isinstance(response, dict) else None
    )


def _value(obj, name, default=None):
    if obj is None:
        return default
    if isinstance(obj, dict):
        return obj.get(name, default)
    return getattr(obj, name, default)


class CloudService:
    def __init__(self, config: Optional[CloudConfig] = None):
        self.config = config or load_cloud_config()
        self.client: Optional[Client] = None
        self.current_cloud_user_id: Optional[str] = None
        self.current_email: str = ""
        self.last_error: str = ""
        self._realtime_channel = None
        self._realtime_thread = None
        self._realtime_stop = threading.Event()
        self._realtime_connected = threading.Event()
        self._realtime_reconnects = 0
        if self.config.configured and SUPABASE_AVAILABLE:
            try:
                self.client = create_client(self.config.url, self.config.publishable_key)
            except Exception as exc:
                self.last_error = str(exc)
                log.warning("Supabase client init failed: %s", exc)

    @property
    def configured(self) -> bool:
        return self.config.configured

    @property
    def available(self) -> bool:
        return bool(self.client)

    @property
    def authenticated(self) -> bool:
        return bool(self.client and self.current_cloud_user_id)

    def status(self) -> dict:
        return {
            "configured": self.configured,
            "sdk_available": SUPABASE_AVAILABLE,
            "keyring_available": KEYRING_AVAILABLE,
            "authenticated": self.authenticated,
            "cloud_user_id": self.current_cloud_user_id,
            "email": self.current_email,
            "last_error": self.last_error,
            "realtime_connected": self._realtime_connected.is_set(),
            "realtime_reconnects": self._realtime_reconnects,
        }

    def _require_client(self):
        if not self.configured:
            raise RuntimeError("Supabase environment is not configured")
        if not SUPABASE_AVAILABLE:
            raise RuntimeError("The supabase Python package is not installed")
        if not self.client:
            raise RuntimeError(self.last_error or "Supabase client is unavailable")
        return self.client

    def _require_auth(self):
        client = self._require_client()
        if not self.authenticated:
            raise RuntimeError("Cloud account is not signed in")
        return client

    def sign_up(self, email: str, password: str):
        client = self._require_client()
        result = client.auth.sign_up({"email": email.strip(), "password": password})
        return {
            "user": _auth_user(result),
            "session": _auth_session(result),
            "verification_required": _auth_session(result) is None,
        }

    def sign_in(self, email: str, password: str):
        client = self._require_client()
        result = client.auth.sign_in_with_password({"email": email.strip(), "password": password})
        user, session = _auth_user(result), _auth_session(result)
        if not user or not session:
            raise RuntimeError("Supabase did not return an authenticated session")
        self.current_cloud_user_id = str(_value(user, "id"))
        self.current_email = str(_value(user, "email", email))
        return {"user": user, "session": session}

    def link_local_account(self, local_user_id: int, auth_result: dict):
        import database as db
        user, session = auth_result.get("user"), auth_result.get("session")
        cloud_id = str(_value(user, "id", ""))
        email = str(_value(user, "email", ""))
        confirmed = _value(user, "email_confirmed_at") or _value(user, "confirmed_at")
        if not cloud_id or not session:
            raise RuntimeError("A verified sign-in session is required before linking")
        if not confirmed:
            raise RuntimeError("Verify the email address before linking this account")
        db.save_cloud_user_link(local_user_id, cloud_id, email, "linked")
        refresh_token = str(_value(session, "refresh_token", ""))
        if refresh_token and KEYRING_AVAILABLE:
            keyring.set_password(_KEYRING_SERVICE, f"local:{local_user_id}", refresh_token)
        self.current_cloud_user_id, self.current_email = cloud_id, email
        self.upsert_profile_from_local(local_user_id)
        return {"ok": True, "cloud_user_id": cloud_id, "email": email}

    def restore_session(self, local_user_id: int) -> bool:
        import database as db
        link = db.get_cloud_user_link(local_user_id)
        if not link or not KEYRING_AVAILABLE:
            return False
        token = keyring.get_password(_KEYRING_SERVICE, f"local:{local_user_id}")
        if not token:
            return False
        try:
            result = self._require_client().auth.refresh_session(token)
            user, session = _auth_user(result), _auth_session(result)
            if not user or not session:
                return False
            self.current_cloud_user_id = str(_value(user, "id"))
            self.current_email = str(_value(user, "email", link.get("email", "")))
            new_token = str(_value(session, "refresh_token", ""))
            if new_token:
                keyring.set_password(_KEYRING_SERVICE, f"local:{local_user_id}", new_token)
            return True
        except Exception as exc:
            self.last_error = str(exc)
            return False

    def sign_out(self, local_user_id: Optional[int] = None):
        self.unsubscribe_realtime()
        if self.client:
            try:
                self.client.auth.sign_out()
            except Exception:
                pass
        if local_user_id is not None and KEYRING_AVAILABLE:
            try:
                keyring.delete_password(_KEYRING_SERVICE, f"local:{local_user_id}")
            except Exception:
                pass
        self.current_cloud_user_id = None
        self.current_email = ""

    def rpc(self, function_name: str, params: Optional[dict] = None):
        response = self._require_auth().rpc(function_name, params or {}).execute()
        return _response_data(response)

    def upsert_profile_from_local(self, local_user_id: int):
        import database as db
        client = self._require_auth()
        user = db.get_user(local_user_id)
        payload = {
            "id": self.current_cloud_user_id,
            "username": user.get("username", ""),
            "display_name": user.get("display_name", ""),
            "bio": user.get("bio", ""),
            "avatar_class": user.get("avatar_class", "warrior"),
            "avatar_color": user.get("avatar_color", "#5a8a2e"),
            "avatar_emoji": user.get("avatar_emoji", ""),
        }
        client.table("profiles").upsert(payload, on_conflict="id").execute()
        return payload

    def _as_webp(self, image_data: bytes, max_dimension=1600, quality=84) -> bytes:
        if not PILLOW_AVAILABLE:
            raise RuntimeError("Pillow is required for WebP cloud uploads")
        with Image.open(io.BytesIO(image_data)) as image:
            image.load()
            image = image.convert("RGB")
            image.thumbnail((max_dimension, max_dimension), Image.Resampling.LANCZOS)
            output = io.BytesIO()
            image.save(output, "WEBP", quality=quality, method=6)
            return output.getvalue()

    def upload_profile_photo(self, local_user_id: int):
        import database as db
        client = self._require_auth()
        photo = db.get_profile_photo(local_user_id)
        if not photo:
            raise RuntimeError("Local profile photo does not exist")
        webp = self._as_webp(photo["image_data"], 1024, 86)
        if len(webp) > 5 * 1024 * 1024:
            raise RuntimeError("Processed profile photo exceeds 5 MB")
        path = f"{self.current_cloud_user_id}/profile.webp"
        bucket = client.storage.from_(self.config.profile_bucket)
        bucket.upload(path, webp, {"content-type": "image/webp", "upsert": "true"})
        client.table("profiles").update({"avatar_path": path}).eq("id", self.current_cloud_user_id).execute()
        return {"storage_path": path, "size_bytes": len(webp)}

    def delete_profile_photo(self):
        client = self._require_auth()
        path = f"{self.current_cloud_user_id}/profile.webp"
        try:
            client.storage.from_(self.config.profile_bucket).remove([path])
        finally:
            client.table("profiles").update({"avatar_path": None}).eq("id", self.current_cloud_user_id).execute()

    def download_storage(self, bucket: str, path: str) -> bytes:
        return bytes(self._require_auth().storage.from_(bucket).download(path))

    # Phase 2A: chat, presence, notifications
    def get_or_create_direct_conversation(self, other_cloud_user_id: str):
        return self.rpc("get_or_create_direct_conversation", {"p_other_user_id": other_cloud_user_id})

    def fetch_direct_messages(self, conversation_id: str, limit=50, before=None):
        query=(self._require_auth().table("messages").select("*")
               .eq("conversation_id",conversation_id))
        if before:query=query.lt("created_at",before)
        response=query.order("created_at",desc=True).limit(max(1,min(200,int(limit)))).execute()
        return list(reversed(_response_data(response) or []))

    def fetch_message_reactions(self,message_ids):
        ids=[str(value) for value in message_ids if value]
        if not ids:return []
        response=self._require_auth().table("message_reactions").select("*").in_("message_id",ids).execute()
        return _response_data(response) or []

    def send_direct_message(self, conversation_id: str, body: str,
                            client_message_id: Optional[str] = None,reply_to_id=None):
        client_id=client_message_id or str(uuid.uuid4())
        try:
            return self.rpc("send_direct_message_v2", {
                "p_conversation_id":conversation_id,"p_body":body,
                "p_client_message_id":client_id,"p_reply_to_id":reply_to_id})
        except Exception as exc:
            text=str(exc)
            if reply_to_id is not None or ("PGRST202" not in text and "Could not find the function" not in text):raise
            # Additive rollout only while the v2 migration is genuinely absent.
            return self.rpc("send_direct_message", {
                "p_conversation_id":conversation_id,"p_body":body,"p_client_message_id":client_id})

    def edit_direct_message(self,message_id: str,body: str):
        return self.rpc("edit_direct_message",{"p_message_id":message_id,"p_body":body})

    def delete_direct_message(self,message_id: str):
        return self.rpc("delete_direct_message",{"p_message_id":message_id})

    def set_direct_message_reaction(self,message_id: str,reaction=None):
        return self.rpc("set_direct_message_reaction",{"p_message_id":message_id,"p_reaction":reaction})

    def get_direct_conversation_summaries(self):
        return self.rpc("get_direct_conversation_summaries") or []

    _CHAT_FILE_MIMES={
        ".pdf":"application/pdf",".txt":"text/plain",
        ".docx":"application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        ".xlsx":"application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        ".pptx":"application/vnd.openxmlformats-officedocument.presentationml.presentation",
    }

    def prepare_chat_attachment(self,local_user_id: int,file_path: str):
        """Validate/re-encode a local file and persist a retryable SQLite BLOB."""
        import database as db
        path=Path(file_path);name=path.name
        if not path.is_file() or not name or len(name)>160:raise RuntimeError("Invalid attachment file")
        raw=path.read_bytes()
        if not raw or len(raw)>10*1024*1024:raise RuntimeError("Attachment must be between 1 byte and 10 MB")
        suffix=path.suffix.lower();width=height=None;thumbnail=None
        if suffix in (".jpg",".jpeg",".png",".webp"):
            if not PILLOW_AVAILABLE:raise RuntimeError("Pillow is required for image attachments")
            with Image.open(io.BytesIO(raw)) as image:
                image.load()
                if image.width*image.height>40_000_000:raise RuntimeError("Image dimensions are too large")
                image=ImageOps.exif_transpose(image).convert("RGB");image.thumbnail((1600,1600),Image.Resampling.LANCZOS)
                thumb=image.copy();thumb.thumbnail((320,320),Image.Resampling.LANCZOS);thumb_out=io.BytesIO();thumb.save(thumb_out,"WEBP",quality=72,method=6);thumbnail=thumb_out.getvalue()
                output=io.BytesIO();image.save(output,"WEBP",quality=84,method=6);raw=output.getvalue();width,height=image.width,image.height
            if len(raw)>5*1024*1024:raise RuntimeError("Processed image exceeds 5 MB")
            mime="image/webp";name=f"{path.stem[:150] or 'image'}.webp"
        else:
            mime=self._CHAT_FILE_MIMES.get(suffix)
            if not mime:raise RuntimeError("Unsupported attachment type")
            if suffix==".pdf" and not raw.startswith(b"%PDF-"):raise RuntimeError("Invalid PDF signature")
            if suffix==".txt":
                try:raw.decode("utf-8")
                except UnicodeDecodeError:raise RuntimeError("Text attachment must be UTF-8")
            if suffix in (".docx",".xlsx",".pptx"):
                try:
                    with zipfile.ZipFile(io.BytesIO(raw)) as archive:
                        names=set(archive.namelist());expected={".docx":"word/",".xlsx":"xl/",".pptx":"ppt/"}[suffix]
                        if "[Content_Types].xml" not in names or not any(item.startswith(expected) for item in names):raise RuntimeError("Invalid Office document")
                except zipfile.BadZipFile:raise RuntimeError("Invalid Office document")
        attachment_uuid=str(uuid.uuid4());digest=hashlib.sha256(raw).hexdigest()
        local_id=db.create_pending_chat_attachment(local_user_id,attachment_uuid,name,mime,raw,digest,width,height,thumbnail)
        return db.get_chat_attachment(local_id)

    def fetch_message_attachments(self,message_ids):
        ids=[str(value) for value in message_ids if value]
        if not ids:return []
        response=self._require_auth().table("message_attachments").select("*").in_("message_id",ids).is_("deleted_at","null").execute()
        return _response_data(response) or []

    def send_direct_message_with_attachments(self,local_user_id: int,conversation_id: str,body: str,
                                             client_message_id: str,reply_to_id,attachment_local_ids):
        import database as db
        client=self._require_auth();metadata=[]
        for local_id in attachment_local_ids:
            item=db.get_chat_attachment(local_id)
            if not item or item.get("local_user_id")!=local_user_id or not item.get("file_data"):raise RuntimeError("Attachment cache is unavailable")
            safe_name=Path(item["original_filename"]).name[:160]
            slot=self.rpc("create_chat_attachment_upload_slot",{
                "p_conversation_id":conversation_id,"p_attachment_id":item["cloud_id"],
                "p_original_filename":safe_name,"p_mime_type":item["mime_type"],
                "p_size_bytes":item["size_bytes"],"p_width":item.get("width"),"p_height":item.get("height"),
                "p_sha256":item["sha256"]}) or {}
            storage_path=slot["storage_path"];safe_name=slot.get("original_filename") or safe_name
            client.storage.from_(self.config.chat_bucket).upload(storage_path,item["file_data"],{
                "content-type":item["mime_type"],"upsert":"true"})
            metadata.append({"id":item["cloud_id"],"storage_path":storage_path,"original_filename":safe_name,
                "mime_type":item["mime_type"],"size_bytes":item["size_bytes"],"width":item.get("width"),
                "height":item.get("height"),"sha256":item["sha256"]})
        result=self.rpc("send_direct_message_with_attachments",{
            "p_conversation_id":conversation_id,"p_body":body,"p_client_message_id":client_message_id,
            "p_reply_to_id":reply_to_id,"p_attachments":metadata}) or {}
        message=result.get("message") or {};attachments=result.get("attachments") or []
        if message:db.cache_cloud_messages([message])
        db.mark_chat_attachments_synced(local_user_id,message.get("id"),conversation_id,attachments)
        return message

    def download_chat_attachment(self,local_user_id: int,attachment: dict):
        import database as db
        raw=self.download_storage(self.config.chat_bucket,attachment["storage_path"])
        if len(raw)!=int(attachment.get("size_bytes") or 0) or hashlib.sha256(raw).hexdigest()!=attachment.get("sha256"):
            raise RuntimeError("Attachment integrity check failed")
        thumbnail=None
        if str(attachment.get("mime_type") or "").startswith("image/") and PILLOW_AVAILABLE:
            with Image.open(io.BytesIO(raw)) as image:
                image.load();image=ImageOps.exif_transpose(image).convert("RGB");image.thumbnail((320,320),Image.Resampling.LANCZOS)
                output=io.BytesIO();image.save(output,"WEBP",quality=72,method=6);thumbnail=output.getvalue()
        db.cache_chat_attachment_data(attachment["cloud_id"],raw,thumbnail);return raw

    def get_chat_attachment_usage(self):
        return self.rpc("get_chat_attachment_usage") or {}

    def mark_conversation_read(self, conversation_id: str):
        return self.rpc("mark_conversation_read", {"p_conversation_id": conversation_id})

    def set_conversation_typing(self, conversation_id: str, is_typing: bool):
        return self.rpc("set_conversation_typing", {"p_conversation_id": conversation_id, "p_is_typing": is_typing})

    def get_conversation_typing(self, conversation_id: str):
        response=(self._require_auth().table("conversation_typing").select("*")
                  .eq("conversation_id",conversation_id).gt("expires_at",datetime.now(timezone.utc).isoformat()).execute())
        return _response_data(response) or []

    def heartbeat_presence(self, status="online", device_name="CraftLife Desktop"): 
        return self.rpc("heartbeat_presence", {"p_status": status, "p_device_name": device_name})

    # Phase 3: private multi-device tracker snapshots.
    def register_cloud_device(self, device: dict):
        return self.rpc("register_cloud_device", {
            "p_device_id": device["device_id"],
            "p_device_name": device.get("device_name") or "CraftLife Desktop",
            "p_platform": device.get("platform") or "desktop",
            "p_app_version": device.get("app_version") or "1.0-phase3",
        })

    def get_cloud_devices(self):
        response=(self._require_auth().table("cloud_devices").select("*")
                  .order("last_seen_at",desc=True).execute())
        return _response_data(response) or []

    def revoke_cloud_device(self, device_id: str):
        return self.rpc("revoke_cloud_device", {"p_device_id": device_id})

    def rename_cloud_device(self,device_id: str,name: str):
        return self.rpc("rename_cloud_device",{"p_device_id":device_id,"p_device_name":name})

    def revoke_other_cloud_devices(self,current_device_id: str):
        return self.rpc("revoke_other_cloud_devices",{"p_current_device_id":current_device_id})

    def get_personal_snapshots(self):
        response=(self._require_auth().table("personal_snapshots").select("*")
                  .order("server_updated_at",desc=True).execute())
        return _response_data(response) or []

    def get_personal_snapshot_versions(self, document_key="tracker_v1", limit=10):
        response=(self._require_auth().table("personal_snapshot_versions").select(
                    "id,document_key,revision,content_hash,source_device_id,server_updated_at,archived_at")
                  .eq("document_key",document_key).order("revision",desc=True)
                  .limit(max(1,min(10,int(limit)))).execute())
        return _response_data(response) or []

    def upsert_personal_snapshot(self, document_key: str, base_revision: int,
                                 content_hash: str, payload: dict, device_id: str):
        return self.rpc("upsert_personal_snapshot", {
            "p_document_key": document_key,
            "p_base_revision": int(base_revision),
            "p_content_hash": content_hash,
            "p_payload": payload,
            "p_device_id": device_id,
            "p_client_updated_at": datetime.now(timezone.utc).isoformat(),
        })

    def run_cloud_maintenance(self):
        return self.rpc("run_cloud_maintenance")

    # Phase 4A: cloud-native shared Love Space records.
    def fetch_love_space_bundle(self, love_space_id: str):
        client=self._require_auth()
        tables={
            "profile":"love_space_shared_profiles","events":"love_space_events",
            "memories":"love_space_memories","checkins":"love_space_checkins",
            "prompt_responses":"love_space_prompt_responses",
            "prompt_favorites":"love_space_prompt_favorites",
            "weekly_reviews":"love_space_weekly_reviews","bucket_items":"love_space_bucket_items",
            "cycle_settings":"love_space_cycle_settings","cycles":"love_space_cycles",
        }
        bundle={}
        for key,table in tables.items():
            response=client.table(table).select("*").eq("love_space_id",love_space_id).execute()
            bundle[key]=_response_data(response) or []
        return bundle

    def save_love_space_shared_profile(self, love_space_id: str, values: dict):
        return self.rpc("save_love_space_shared_profile", {
            "p_love_space_id":love_space_id,"p_partner_name":values.get("partner_name", ""),
            "p_partner_gender":values.get("partner_gender", "female"),
            "p_partner_age":int(values.get("partner_age") or 25),
            "p_relationship_type":values.get("relationship_type", "dating"),
            "p_start_date":values.get("start_date") or None,
        })

    def save_love_space_cycle_settings(self, love_space_id: str, values: dict):
        return self.rpc("save_love_space_cycle_settings", {
            "p_love_space_id":love_space_id,"p_tracked_person":values.get("tracked_person", "partner"),
            "p_last_period_start":values.get("last_period_start") or None,
            "p_cycle_length":int(values.get("cycle_length") or 28),
            "p_period_length":int(values.get("period_length") or 5),
        })

    def upsert_love_space_record(self, love_space_id: str, record_type: str,
                                 payload: dict, record_id=None):
        result=self.rpc("upsert_love_space_record", {
            "p_love_space_id":love_space_id,"p_record_type":record_type,
            "p_record_id":record_id or str(uuid.uuid4()),"p_payload":payload,
        })
        return result or {}

    def delete_love_space_record(self, love_space_id: str, record_type: str, record_id: str):
        return self.rpc("delete_love_space_record", {
            "p_love_space_id":love_space_id,"p_record_type":record_type,"p_record_id":record_id,
        })

    def toggle_love_space_bucket_item(self, love_space_id: str, record_id: str, done: bool):
        return self.rpc("toggle_love_space_bucket_item", {
            "p_love_space_id":love_space_id,"p_record_id":record_id,"p_is_done":bool(done),
        })

    def set_love_space_prompt_favorite(self, love_space_id: str, prompt_key: str, favorite: bool):
        return self.rpc("set_love_space_prompt_favorite", {
            "p_love_space_id":love_space_id,"p_prompt_key":prompt_key,"p_favorite":bool(favorite),
        }) or {}

    def migrate_love_space_from_local(self, local_user_id: int, love_space_id: str):
        import database as db
        bundle=db.build_local_love_migration_bundle(local_user_id);done=0
        profile=bundle.get("profile") or {}
        if profile.get("partner_name"):
            row=self.save_love_space_shared_profile(love_space_id,profile)
            db.mirror_cloud_love_profile(local_user_id,row);done+=1
        settings=bundle.get("cycle_settings") or {}
        if settings.get("last_period_start") or bundle.get("cycles"):
            row=self.save_love_space_cycle_settings(love_space_id,settings)
            db.mirror_cloud_love_cycle_settings(local_user_id,row);done+=1
        specs={
            "events":("event",("title","event_date","category","notes")),
            "memories":("memory",("title","memory_date","notes")),
            "checkins":("checkin",("checkin_date","my_mood","partner_mood","connection_score","note")),
            "prompt_responses":("prompt_response",("prompt_key","category","prompt_text","my_answer","partner_answer","response_date")),
            "weekly_reviews":("weekly_review",("week_start","appreciation","wins","support_needed","shared_intention")),
            "bucket_items":("bucket_item",("title","category","target_date","is_done")),
            "cycles":("cycle",("start_date","end_date","notes")),
        }
        for key,(record_type,fields) in specs.items():
            for local_row in bundle.get(key) or []:
                cloud_id=db.ensure_love_record_cloud_id(record_type,local_row["id"])
                payload={field:local_row.get(field) for field in fields}
                result=self.upsert_love_space_record(love_space_id,record_type,payload,cloud_id)
                db.mirror_cloud_love_record(local_user_id,record_type,result.get("row") or {});done+=1
        for prompt_key in bundle.get("prompt_favorites") or []:
            result=self.set_love_space_prompt_favorite(love_space_id,prompt_key,True)
            db.mirror_cloud_love_favorite(local_user_id,result.get("row") or {},True,prompt_key);done+=1
        return {"ok":True,"migrated":done}

    def get_presence(self, cloud_user_ids):
        if not cloud_user_ids:
            return []
        response = self._require_auth().table("user_presence").select("*").in_("user_id", cloud_user_ids).execute()
        return _response_data(response) or []

    def get_social_notifications(self, unread_only=False, limit=50):
        query = self._require_auth().table("social_notifications").select("*")
        if unread_only:
            query = query.eq("is_read", False)
        return _response_data(query.order("created_at", desc=True).limit(limit).execute()) or []

    def mark_social_notifications_read(self, notification_ids=None):
        return self.rpc("mark_social_notifications_read", {"p_ids": notification_ids})

    def get_social_notifications_page(self,limit=50,before=None,type_filter=None):
        return self.rpc("get_social_notifications_page",{"p_limit":limit,"p_before":before,"p_type":type_filter}) or []

    def mark_social_notification_read(self,notification_id):
        return self.rpc("mark_social_notification_read",{"p_notification_id":notification_id})

    def set_notification_preferences(self,values):
        return self.rpc("set_notification_preferences",{"p_values":values})

    # Phase 2B: server-scored productivity events
    def wallet_balance(self):
        return self.rpc("wallet_balance")

    def buy_shop_item(self, item_key: str, qty: int, idempotency_key: str):
        return self.rpc("buy_shop_item", {"p_item": item_key, "p_qty": qty, "p_idem": idempotency_key})

    def craft_item_cloud(self, recipe_key: str, idempotency_key: str):
        return self.rpc("craft_item_cloud", {"p_recipe": recipe_key, "p_idem": idempotency_key})

    def enchant_item_cloud(self, item_key: str, idempotency_key: str):
        return self.rpc("enchant_item_cloud", {"p_item": item_key, "p_idem": idempotency_key})

    def equip_item_cloud(self, item_key: str, equipped: bool):
        return self.rpc("equip_item_cloud", {"p_item": item_key, "p_on": bool(equipped)})

    def fetch_cloud_inventory(self):
        client = self._require_auth()
        return _response_data(client.table("cloud_inventory").select("*")
                              .eq("user_id", self.current_cloud_user_id).execute()) or []

    def claim_achievement_reward_cloud(self, achievement_key: str, claim_key: str):
        return self.rpc("claim_achievement_reward_cloud",
                        {"achievement_key": achievement_key, "claim_key": claim_key})

    def record_productivity_event(self, payload: dict):
        return self.rpc("record_productivity_event", {
            "p_event_type": payload["event_type"],
            "p_source_local_id": str(payload.get("source_local_id", "")),
            "p_idempotency_key": payload["idempotency_key"],
            "p_completed_at": payload["completed_at"],
            "p_device_id": payload.get("device_id", "CraftLife Desktop"),
            "p_payload": payload.get("payload", {}),
        })

    # Phase 2C: online PvP
    def send_online_pvp_challenge(self, opponent_cloud_id: str, duration_days=7):
        return self.rpc("send_online_pvp_challenge", {"p_opponent_id": opponent_cloud_id, "p_duration_days": duration_days})

    def respond_online_pvp_challenge(self, challenge_id: str, accept: bool):
        return self.rpc("respond_online_pvp_challenge", {"p_challenge_id": challenge_id, "p_accept": accept})

    def cancel_online_pvp_challenge(self, challenge_id: str):
        return self.rpc("cancel_online_pvp_challenge", {"p_challenge_id": challenge_id})

    def get_online_pvp_challenges(self):
        return self.fetch_table("online_pvp_challenges")

    def get_online_pvp_score(self, challenge_id: str, cloud_user_id: str):
        return self.rpc("pvp_score", {"p_challenge_id": challenge_id, "p_user_id": cloud_user_id})

    def finalize_online_pvp(self, challenge_id: str):
        return self.rpc("finalize_online_pvp", {"p_challenge_id": challenge_id})

    def claim_online_pvp_reward(self, challenge_id: str):
        return self.rpc("claim_online_pvp_reward", {"p_challenge_id": challenge_id})

    # Phase 2D: online Guild
    def create_online_guild(self, name: str, description=""):
        return self.rpc("create_online_guild", {"p_name": name, "p_description": description})

    def get_online_guilds(self):
        return [row for row in self.fetch_table("online_guilds") if not row.get("disbanded_at")]

    def get_online_guild_members(self):
        return self.fetch_table("online_guild_members")

    def get_online_guild_requests(self):
        return self.fetch_table("online_guild_requests")

    def request_online_guild_join(self, guild_id: str):
        return self.rpc("request_online_guild_join", {"p_guild_id": guild_id})

    def respond_online_guild_join(self, request_id: str, accept: bool):
        return self.rpc("respond_online_guild_join", {"p_request_id": request_id, "p_accept": accept})

    def get_online_guild_messages(self,guild_id: str,limit=50,before=None):
        query=self._require_auth().table("online_guild_messages").select("*").eq("guild_id",guild_id)
        if before:query=query.lt("created_at",before)
        rows=_response_data(query.order("created_at",desc=True).limit(max(1,min(200,int(limit)))).execute()) or []
        return list(reversed(rows))

    def get_online_guild_message_reactions(self,message_ids):
        ids=[str(value) for value in message_ids if value]
        if not ids:return []
        return _response_data(self._require_auth().table("online_guild_message_reactions").select("*").in_("message_id",ids).execute()) or []

    def send_online_guild_message(self,guild_id: str,body: str,client_message_id=None,reply_to_id=None):
        client_id=client_message_id or str(uuid.uuid4())
        try:return self.rpc("send_online_guild_message_v2",{"p_guild_id":guild_id,"p_body":body,"p_client_message_id":client_id,"p_reply_to_id":reply_to_id})
        except Exception as exc:
            text=str(exc)
            if reply_to_id is not None or ("PGRST202" not in text and "Could not find the function" not in text):raise
            return self.rpc("send_online_guild_message",{"p_guild_id":guild_id,"p_body":body,"p_client_message_id":client_id})

    def edit_online_guild_message(self,message_id,body):
        return self.rpc("edit_online_guild_message",{"p_message_id":message_id,"p_body":body})

    def delete_online_guild_message(self,message_id):
        return self.rpc("delete_online_guild_message",{"p_message_id":message_id})

    def set_online_guild_message_reaction(self,message_id,reaction=None):
        return self.rpc("set_online_guild_message_reaction",{"p_message_id":message_id,"p_reaction":reaction})

    def mark_online_guild_read(self,guild_id):return self.rpc("mark_online_guild_read",{"p_guild_id":guild_id})
    def get_my_online_guild_summary(self):return self.rpc("get_my_online_guild_summary") or {}
    def cancel_online_guild_join(self,request_id):return self.rpc("cancel_online_guild_join",{"p_request_id":request_id})
    def leave_online_guild(self,guild_id):return self.rpc("leave_online_guild",{"p_guild_id":guild_id})
    def kick_online_guild_member(self,guild_id,user_id):return self.rpc("kick_online_guild_member",{"p_guild_id":guild_id,"p_user_id":user_id})
    def ban_online_guild_member(self,guild_id,user_id,reason=""):return self.rpc("ban_online_guild_member",{"p_guild_id":guild_id,"p_user_id":user_id,"p_reason":reason})
    def unban_online_guild_member(self,guild_id,user_id):return self.rpc("unban_online_guild_member",{"p_guild_id":guild_id,"p_user_id":user_id})
    def set_online_guild_role(self,guild_id,user_id,role):return self.rpc("set_online_guild_role",{"p_guild_id":guild_id,"p_user_id":user_id,"p_role":role})
    def transfer_online_guild_leader(self,guild_id,user_id):return self.rpc("transfer_online_guild_leader",{"p_guild_id":guild_id,"p_user_id":user_id})
    def disband_online_guild(self,guild_id):return self.rpc("disband_online_guild",{"p_guild_id":guild_id})
    def update_online_guild_description(self,guild_id,description):return self.rpc("update_online_guild_description",{"p_guild_id":guild_id,"p_description":description})
    def get_online_guild_bans(self):return self.fetch_table("online_guild_bans")

    def start_online_guild_boss(self,guild_id: str,boss_key="cloud_dragon",boss_name=None,max_hp=None):
        return self.rpc("start_online_guild_boss_v2",{"p_guild_id":guild_id,"p_boss_key":boss_key})

    def get_online_guild_contributions(self):return self.fetch_table("online_guild_contributions")
    def get_online_guild_battles(self):return self.fetch_table("online_guild_battles")
    def get_online_guild_boss_rewards(self):return self.fetch_table("online_guild_boss_rewards")
    def claim_online_guild_boss_reward(self,battle_id):return self.rpc("claim_online_guild_boss_reward",{"p_battle_id":battle_id})
    def run_online_guild_maintenance(self):return self.rpc("run_online_guild_maintenance")

    # Phase 2E: leaderboards
    def get_global_productivity_leaderboard(self, days=30, limit=50):
        return self.rpc("get_global_productivity_leaderboard", {"p_days": days, "p_limit": limit}) or []

    def get_online_guild_leaderboard(self, limit=50):
        return self.rpc("get_online_guild_leaderboard", {"p_limit": limit}) or []

    def send_friend_request(self, target_username: str):
        return self.rpc("send_friend_request", {"target_username": target_username.strip().lower()})

    def respond_friend_request(self, friendship_id: str, accept: bool):
        return self.rpc("respond_friend_request", {"friendship_id": friendship_id, "accept_request": accept})

    def remove_friendship(self, friendship_id: str):
        return self.rpc("remove_friendship", {"friendship_id": friendship_id})

    def send_couple_request(self, target_user_id: str):
        return self.rpc("send_couple_request", {"target_user_id": target_user_id})

    def respond_couple_request(self, relationship_id: str, accept: bool):
        return self.rpc("respond_couple_request", {"relationship_id": relationship_id, "accept_request": accept})

    def cancel_couple_request(self, relationship_id: str):
        return self.rpc("cancel_couple_request", {"relationship_id": relationship_id})

    def end_couple_relationship(self, relationship_id: str):
        return self.rpc("end_couple_relationship", {"relationship_id": relationship_id})

    def delete_gallery_photo(self, cloud_photo_id: str, storage_path: str):
        client = self._require_auth()
        client.table("love_space_photos").delete().eq("id", cloud_photo_id).execute()
        if storage_path:
            client.storage.from_(self.config.gallery_bucket).remove([storage_path])
        return {"ok": True}

    def subscribe_social_realtime(self, callback):
        client = self._require_auth()
        if self._realtime_thread and self._realtime_thread.is_alive():
            return self._realtime_thread
        session = client.auth.get_session()
        if not session:
            raise RuntimeError("No Supabase session is available for Realtime")
        access_token = _value(session, "access_token", "")
        refresh_token = _value(session, "refresh_token", "")
        self._realtime_stop.clear()
        self._realtime_connected.clear()

        def dispatch(table_name, payload):
            try:
                callback(table_name, payload)
            except Exception as exc:
                log.warning("Realtime callback failed for %s: %s", table_name, exc)

        async def connect_once():
            async_client = await acreate_client(self.config.url, self.config.publishable_key)
            try:
                try:
                    await async_client.auth.set_session(access_token, refresh_token)
                except Exception:
                    await async_client.auth.refresh_session(refresh_token)
                channel = async_client.channel(f"craftlife-realtime-{self.current_cloud_user_id}")
                tables = (
                    "friendships", "couple_relationships", "love_space_photos",
                    "messages", "message_reactions", "message_attachments", "conversation_typing", "user_presence", "social_notifications",
                    "productivity_events", "online_pvp_challenges", "online_guild_messages",
                    "online_guild_message_reactions", "online_guild_members", "online_guild_requests",
                    "online_guild_contributions", "online_guild_battles", "online_guild_boss_rewards",
                    "personal_snapshots", "love_space_shared_profiles", "love_space_events",
                    "love_space_memories", "love_space_checkins", "love_space_prompt_responses",
                    "love_space_prompt_favorites", "love_space_weekly_reviews",
                    "love_space_bucket_items", "love_space_cycle_settings", "love_space_cycles",
                )
                for table in tables:
                    channel = channel.on_postgres_changes(
                        RealtimePostgresChangesListenEvent.All,
                        lambda payload, table_name=table: dispatch(table_name, payload),
                        table=table, schema="public",
                    )
                self._realtime_channel = await channel.subscribe()
                self._realtime_connected.set()
                while not self._realtime_stop.is_set():
                    await asyncio.sleep(0.5)
            finally:
                self._realtime_connected.clear()
                try:
                    if 'channel' in locals():
                        await async_client.remove_channel(channel)
                except Exception:
                    pass
                self._realtime_channel = None

        async def runner():
            delay = 1
            while not self._realtime_stop.is_set():
                try:
                    await connect_once()
                    delay = 1
                except Exception as exc:
                    if self._realtime_stop.is_set():
                        break
                    self.last_error = f"Realtime: {exc}"
                    self._realtime_reconnects += 1
                    log.warning("Realtime disconnected; retry in %ss: %s", delay, exc)
                    await asyncio.sleep(delay)
                    delay = min(30, delay * 2)

        def thread_main():
            try:
                asyncio.run(runner())
            except Exception as exc:
                self.last_error = f"Realtime: {exc}"
                log.warning("Realtime stopped: %s", exc)
            finally:
                self._realtime_connected.clear()

        self._realtime_thread = threading.Thread(
            target=thread_main, daemon=True, name="CraftLifeRealtime"
        )
        self._realtime_thread.start()
        return self._realtime_thread

    def unsubscribe_realtime(self):
        self._realtime_stop.set()
        self._realtime_connected.clear()
        thread = self._realtime_thread
        if thread and thread.is_alive():
            thread.join(timeout=2)
        self._realtime_thread = None
        self._realtime_channel = None

    def request_account_deletion(self):
        return self.rpc("request_account_deletion")

    def cancel_account_deletion(self):
        return self.rpc("cancel_account_deletion")

    def fetch_table(self, table: str, columns="*"):
        return _response_data(self._require_auth().table(table).select(columns).execute()) or []

    def upload_gallery_photo(self, local_photo_id: int, love_space_cloud_id: str):
        import database as db
        client = self._require_auth()
        photo = db.get_love_space_photo_raw(local_photo_id)
        photo_owner = db.get_love_photo_owner(local_photo_id)
        if not photo or photo_owner != db.get_local_user_id_for_cloud(self.current_cloud_user_id):
            raise RuntimeError("Only the local uploader can sync this gallery photo")
        webp = self._as_webp(photo["image_data"], 1600, 84)
        if len(webp) > 5 * 1024 * 1024:
            raise RuntimeError("Processed gallery photo exceeds 5 MB")
        photo_uuid = str(uuid.uuid4())
        scope_path = love_space_cloud_id or "private"
        path = f"{scope_path}/{self.current_cloud_user_id}/{photo_uuid}.webp"
        client.storage.from_(self.config.gallery_bucket).upload(
            path, webp, {"content-type": "image/webp", "upsert": "false"}
        )
        rpc_payload = {
            "p_photo_id": photo_uuid,
            "p_love_space_id": love_space_cloud_id if photo["visibility"] == "shared" else None,
            "p_visibility": photo["visibility"],
            "p_storage_path": path,
            "p_mime_type": "image/webp",
            "p_width": int(photo["width"]),
            "p_height": int(photo["height"]),
            "p_size_bytes": len(webp),
            "p_caption": photo.get("caption", ""),
            "p_photo_date": photo.get("photo_date"),
        }
        try:
            payload = self.rpc("register_love_photo", rpc_payload)
        except Exception:
            # Avoid orphaned Storage objects if quota/RLS/RPC validation fails.
            try:
                client.storage.from_(self.config.gallery_bucket).remove([path])
            except Exception:
                pass
            raise
        db.mark_love_photo_synced(local_photo_id, photo_uuid, path)
        return payload


_cloud_service: Optional[CloudService] = None


def get_cloud_service() -> CloudService:
    global _cloud_service
    if _cloud_service is None:
        _cloud_service = CloudService()
    return _cloud_service
