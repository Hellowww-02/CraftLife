-- CraftLife Phase 4B.2-4B.3: private direct-chat attachments and hardening.
-- Upload is staged in Storage, then atomically registered with a message by RPC.

insert into storage.buckets(id,name,public,file_size_limit,allowed_mime_types)
values('chat-attachments','chat-attachments',false,10485760,array[
  'image/webp','image/jpeg','image/png','application/pdf','text/plain',
  'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
  'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
  'application/vnd.openxmlformats-officedocument.presentationml.presentation'
]) on conflict(id) do update set public=false,file_size_limit=excluded.file_size_limit,
  allowed_mime_types=excluded.allowed_mime_types;

create table if not exists public.chat_attachment_upload_slots(
  id uuid primary key,
  conversation_id uuid not null references public.conversations(id) on delete cascade,
  uploader_id uuid not null references public.profiles(id) on delete cascade,
  storage_path text not null unique,
  original_filename text not null check(char_length(original_filename) between 1 and 160),
  mime_type text not null,
  size_bytes bigint not null check(size_bytes between 1 and 10485760),
  width integer,
  height integer,
  sha256 text not null check(sha256 ~ '^[0-9a-f]{64}$'),
  created_at timestamptz not null default now(),
  expires_at timestamptz not null default(now()+interval '24 hours'),
  consumed_at timestamptz
);
create index if not exists chat_upload_slots_expiry on public.chat_attachment_upload_slots(expires_at) where consumed_at is null;

create table if not exists public.message_attachments(
  id uuid primary key,
  message_id uuid not null references public.messages(id) on delete cascade,
  conversation_id uuid not null references public.conversations(id) on delete cascade,
  uploader_id uuid not null references public.profiles(id) on delete restrict,
  storage_path text not null unique check(char_length(storage_path)<=500),
  original_filename text not null check(char_length(original_filename) between 1 and 160),
  mime_type text not null check(mime_type in(
    'image/webp','image/jpeg','image/png','application/pdf','text/plain',
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    'application/vnd.openxmlformats-officedocument.presentationml.presentation'
  )),
  size_bytes bigint not null check(size_bytes between 1 and 10485760),
  width integer check(width is null or width between 1 and 4096),
  height integer check(height is null or height between 1 and 4096),
  sha256 text not null check(sha256 ~ '^[0-9a-f]{64}$'),
  created_at timestamptz not null default now(),
  deleted_at timestamptz,
  check((mime_type like 'image/%' and width is not null and height is not null and size_bytes<=5242880)
     or (mime_type not like 'image/%' and width is null and height is null))
);
create index if not exists message_attachments_message on public.message_attachments(message_id,created_at);
create index if not exists message_attachments_uploader on public.message_attachments(uploader_id,created_at desc);
create index if not exists message_attachments_cleanup on public.message_attachments(deleted_at) where deleted_at is not null;

create or replace function public.create_chat_attachment_upload_slot(
  p_conversation_id uuid,p_attachment_id uuid,p_original_filename text,p_mime_type text,
  p_size_bytes bigint,p_width integer,p_height integer,p_sha256 text
)
returns jsonb language plpgsql security definer set search_path=public as $$
declare result public.chat_attachment_upload_slots;safe_name text;path text;used bigint;pending bigint;recent integer;
begin
  if not public.current_profile_active() or not public.is_conversation_member(p_conversation_id) then raise exception 'forbidden'; end if;
  if p_mime_type not in(
    'image/webp','image/jpeg','image/png','application/pdf','text/plain',
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    'application/vnd.openxmlformats-officedocument.presentationml.presentation'
  ) then raise exception 'unsupported_attachment_mime'; end if;
  if p_size_bytes < 1 or p_size_bytes > (case when p_mime_type like 'image/%' then 5242880 else 10485760 end) then
    raise exception 'attachment_too_large';
  end if;
  if p_mime_type like 'image/%' and (p_width is null or p_height is null or p_width not between 1 and 4096 or p_height not between 1 and 4096) then raise exception 'invalid_image_dimensions'; end if;
  if p_mime_type not like 'image/%' then p_width=null;p_height=null;end if;
  if coalesce(p_sha256,'')!~'^[0-9a-f]{64}$' then raise exception 'invalid_sha256'; end if;
  safe_name=regexp_replace(left(coalesce(nullif(trim(p_original_filename),''),'attachment'),160),'[/\\]','_','g');
  path=p_conversation_id::text||'/'||auth.uid()::text||'/'||p_attachment_id::text||'/'||safe_name;
  select * into result from public.chat_attachment_upload_slots where id=p_attachment_id for update;
  if result.id is not null then
    if result.uploader_id<>auth.uid() or result.conversation_id<>p_conversation_id or result.sha256<>p_sha256 then raise exception 'upload_slot_conflict'; end if;
    return to_jsonb(result);
  end if;
  select count(*) into recent from public.chat_attachment_upload_slots where uploader_id=auth.uid() and created_at>now()-interval '1 hour';
  if recent>=50 then raise exception 'attachment_rate_limit'; end if;
  select coalesce(sum(size_bytes),0) into used from public.message_attachments where uploader_id=auth.uid() and deleted_at is null;
  select coalesce(sum(size_bytes),0) into pending from public.chat_attachment_upload_slots where uploader_id=auth.uid() and consumed_at is null and expires_at>now();
  if used+pending+p_size_bytes>262144000 then raise exception 'chat_attachment_quota_exceeded'; end if;
  insert into public.chat_attachment_upload_slots(id,conversation_id,uploader_id,storage_path,original_filename,mime_type,size_bytes,width,height,sha256)
  values(p_attachment_id,p_conversation_id,auth.uid(),path,safe_name,p_mime_type,p_size_bytes,p_width,p_height,p_sha256) returning * into result;
  return to_jsonb(result);
end; $$;

create or replace function public.send_direct_message_with_attachments(
  p_conversation_id uuid,p_body text,p_client_message_id uuid,p_reply_to_id uuid,p_attachments jsonb
)
returns jsonb language plpgsql security definer set search_path=public,storage as $$
declare
  msg public.messages;
  item jsonb;
  attachment_count integer;
  object_row storage.objects;
  slot_row public.chat_attachment_upload_slots;
  total_new bigint:=0;
  attachment_rows jsonb;
begin
  if not public.current_profile_active() or not public.is_conversation_member(p_conversation_id) then raise exception 'forbidden'; end if;
  if p_attachments is null or jsonb_typeof(p_attachments)<>'array' then raise exception 'invalid_attachments'; end if;
  attachment_count=jsonb_array_length(p_attachments);
  if attachment_count<1 or attachment_count>5 then raise exception 'attachment_count_invalid'; end if;
  if char_length(coalesce(p_body,''))>4000 then raise exception 'message_too_long'; end if;
  if p_reply_to_id is not null and not exists(select 1 from public.messages where id=p_reply_to_id and conversation_id=p_conversation_id) then
    raise exception 'invalid_reply_target';
  end if;
  if (select count(*) from public.messages where sender_id=auth.uid() and created_at>now()-interval '1 minute')>=30 then
    raise exception 'message_rate_limit';
  end if;
  for item in select value from jsonb_array_elements(p_attachments)
  loop
    if (item->>'id') is null or (item->>'id')::uuid is null then raise exception 'attachment_id_required'; end if;
    if split_part(item->>'storage_path','/',1)<>p_conversation_id::text
      or split_part(item->>'storage_path','/',2)<>auth.uid()::text
      or split_part(item->>'storage_path','/',3)<>(item->>'id') then raise exception 'invalid_storage_path'; end if;
    if coalesce(item->>'sha256','')!~'^[0-9a-f]{64}$' then raise exception 'invalid_sha256'; end if;
    select * into slot_row from public.chat_attachment_upload_slots where id=(item->>'id')::uuid for update;
    if slot_row.id is null or slot_row.uploader_id<>auth.uid() or slot_row.conversation_id<>p_conversation_id
      or (slot_row.expires_at<now() and slot_row.consumed_at is null) or slot_row.storage_path<>(item->>'storage_path')
      or slot_row.mime_type<>(item->>'mime_type') or slot_row.size_bytes<>(item->>'size_bytes')::bigint
      or slot_row.sha256<>(item->>'sha256') then raise exception 'invalid_upload_slot'; end if;
    select * into object_row from storage.objects where bucket_id='chat-attachments' and name=item->>'storage_path';
    if object_row.id is null or object_row.owner_id<>auth.uid()::text then raise exception 'attachment_object_missing'; end if;
    if coalesce(object_row.metadata->>'mimetype','')<>(item->>'mime_type') then raise exception 'attachment_mime_mismatch'; end if;
    if coalesce(nullif(object_row.metadata->>'size','')::bigint,
                nullif(object_row.metadata->>'contentLength','')::bigint,0)<>(item->>'size_bytes')::bigint then
      raise exception 'attachment_size_mismatch'; end if;
    if (item->>'size_bytes')::bigint > (case when (item->>'mime_type') like 'image/%' then 5242880 else 10485760 end) then
      raise exception 'attachment_too_large';
    end if;
    if not exists(select 1 from public.message_attachments where id=(item->>'id')::uuid) then
      total_new=total_new+(item->>'size_bytes')::bigint;
    end if;
  end loop;
  if coalesce((select sum(size_bytes) from public.message_attachments where uploader_id=auth.uid() and deleted_at is null),0)+total_new>262144000 then
    raise exception 'chat_attachment_quota_exceeded'; end if;

  select * into msg from public.messages where sender_id=auth.uid() and client_message_id=p_client_message_id for update;
  if msg.id is null then
    insert into public.messages(conversation_id,sender_id,body,client_message_id,reply_to_id)
    values(p_conversation_id,auth.uid(),left(coalesce(nullif(trim(coalesce(p_body,'')),''),'📎 Attachment'),4000),p_client_message_id,p_reply_to_id)
    returning * into msg;
  elsif msg.conversation_id<>p_conversation_id then raise exception 'idempotency_conflict'; end if;

  for item in select value from jsonb_array_elements(p_attachments)
  loop
    insert into public.message_attachments(
      id,message_id,conversation_id,uploader_id,storage_path,original_filename,mime_type,
      size_bytes,width,height,sha256
    ) values(
      (item->>'id')::uuid,msg.id,p_conversation_id,auth.uid(),item->>'storage_path',
      left(item->>'original_filename',160),item->>'mime_type',(item->>'size_bytes')::bigint,
      nullif(item->>'width','')::integer,nullif(item->>'height','')::integer,item->>'sha256'
    ) on conflict(id) do update set message_id=excluded.message_id
      where message_attachments.uploader_id=auth.uid() and message_attachments.conversation_id=p_conversation_id;
    update public.chat_attachment_upload_slots set consumed_at=coalesce(consumed_at,now()) where id=(item->>'id')::uuid;
  end loop;
  update public.conversations set updated_at=now() where id=p_conversation_id;
  select coalesce(jsonb_agg(to_jsonb(a) order by a.created_at),'[]'::jsonb) into attachment_rows
    from public.message_attachments a where a.message_id=msg.id and a.deleted_at is null;
  return jsonb_build_object('message',to_jsonb(msg),'attachments',attachment_rows);
end; $$;

create or replace function public.get_chat_attachment_usage()
returns jsonb language sql stable security definer set search_path=public as $$
  select jsonb_build_object('used_bytes',coalesce(sum(size_bytes),0),'quota_bytes',262144000,'file_count',count(*))
  from public.message_attachments where uploader_id=auth.uid() and deleted_at is null
$$;

create or replace function public.mark_message_attachments_deleted()
returns trigger language plpgsql security definer set search_path=public as $$
begin
  if old.deleted_at is null and new.deleted_at is not null then
    update public.message_attachments set deleted_at=coalesce(deleted_at,now()) where message_id=new.id;
  end if;
  return new;
end; $$;
drop trigger if exists messages_soft_delete_attachments on public.messages;
create trigger messages_soft_delete_attachments after update of deleted_at on public.messages
for each row execute function public.mark_message_attachments_deleted();

-- Service-role-only cleanup candidates for the deployed maintenance Edge Function.
create or replace function public.chat_attachment_cleanup_candidates()
returns table(storage_path text) language sql security definer set search_path=public as $$
  select a.storage_path from public.message_attachments a where a.deleted_at<now()-interval '7 days'
  union
  select s.storage_path from public.chat_attachment_upload_slots s where s.consumed_at is null and s.expires_at<now()
$$;
revoke execute on function public.chat_attachment_cleanup_candidates() from public,anon,authenticated;
grant execute on function public.chat_attachment_cleanup_candidates() to service_role;

alter table public.chat_attachment_upload_slots enable row level security;
alter table public.message_attachments enable row level security;
create policy chat_upload_slots_owner_read on public.chat_attachment_upload_slots for select to authenticated
using(uploader_id=auth.uid());
create policy message_attachments_member_read on public.message_attachments for select to authenticated
using(deleted_at is null and public.is_conversation_member(conversation_id));

revoke all on public.chat_attachment_upload_slots,public.message_attachments from anon;
revoke insert,update,delete on public.chat_attachment_upload_slots,public.message_attachments from authenticated;
grant select on public.chat_attachment_upload_slots,public.message_attachments to authenticated;
revoke execute on function public.create_chat_attachment_upload_slot(uuid,uuid,text,text,bigint,integer,integer,text) from public,anon;
revoke execute on function public.send_direct_message_with_attachments(uuid,text,uuid,uuid,jsonb) from public,anon;
revoke execute on function public.get_chat_attachment_usage() from public,anon;
grant execute on function public.create_chat_attachment_upload_slot(uuid,uuid,text,text,bigint,integer,integer,text) to authenticated;
grant execute on function public.send_direct_message_with_attachments(uuid,text,uuid,uuid,jsonb) to authenticated;
grant execute on function public.get_chat_attachment_usage() to authenticated;

create policy chat_attachments_member_read on storage.objects for select to authenticated
using(bucket_id='chat-attachments' and (
  exists(select 1 from public.message_attachments a where a.storage_path=name and a.deleted_at is null
    and public.is_conversation_member(a.conversation_id))
  or exists(select 1 from public.chat_attachment_upload_slots s where s.storage_path=name
    and s.uploader_id=auth.uid() and s.consumed_at is null and s.expires_at>now())
));
create policy chat_attachments_owner_insert on storage.objects for insert to authenticated
with check(bucket_id='chat-attachments' and (storage.foldername(name))[2]=auth.uid()::text and exists(
  select 1 from public.chat_attachment_upload_slots s where s.storage_path=name and s.uploader_id=auth.uid()
    and s.consumed_at is null and s.expires_at>now()
));
create policy chat_attachments_owner_update on storage.objects for update to authenticated
using(bucket_id='chat-attachments' and owner_id=auth.uid()::text)
with check(bucket_id='chat-attachments' and owner_id=auth.uid()::text);
create policy chat_attachments_owner_delete on storage.objects for delete to authenticated
using(bucket_id='chat-attachments' and owner_id=auth.uid()::text);

do $$ begin alter publication supabase_realtime add table public.message_attachments; exception when duplicate_object then null; end $$;
notify pgrst,'reload schema';
