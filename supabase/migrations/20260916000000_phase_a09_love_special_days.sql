-- CraftLife v1.6.3 · fase A09 — Love Space: Special Days & pengingat acara
--
-- OPSIONAL: hanya perlu dijalankan bila akun ini memakai Love Space cloud (Supabase).
-- Tanpa migrasi ini aplikasi tetap normal — kolom baru hanya tersimpan lokal dan
-- payload cloud lama tetap valid (RPC lama mengabaikan kunci yang tak dikenalnya).
--
-- Isi:
--   1. Kolom baru pada public.love_space_events (icon, location, is_special, recurring,
--      remind_days_before, updated_at) + indeks bantu untuk query acara istimewa.
--   2. Definisi ulang public.upsert_love_space_record(...) dengan cabang 'event' yang
--      menulis kolom-kolom baru tersebut (sisa cabang lain disalin apa adanya).

-- ── 1) Kolom baru ─────────────────────────────────────────────────────────────
alter table public.love_space_events
  add column if not exists icon text not null default '',
  add column if not exists location text not null default '',
  add column if not exists is_special boolean not null default false,
  add column if not exists recurring text not null default 'none',
  add column if not exists remind_days_before integer not null default 0,
  add column if not exists updated_at timestamptz not null default now();

do $$
begin
  if not exists (
    select 1 from pg_constraint where conname = 'love_space_events_recurring_check'
  ) then
    alter table public.love_space_events
      add constraint love_space_events_recurring_check check (recurring in ('none','yearly'));
  end if;
  if not exists (
    select 1 from pg_constraint where conname = 'love_space_events_remind_check'
  ) then
    alter table public.love_space_events
      add constraint love_space_events_remind_check check (remind_days_before between 0 and 365);
  end if;
end $$;

create index if not exists idx_love_space_events_special
  on public.love_space_events(love_space_id, is_special, event_date);

-- ── 2) RPC diperluas (event) ─────────────────────────────────────────────────
create or replace function public.upsert_love_space_record(
  p_love_space_id uuid,p_record_type text,p_record_id uuid,p_payload jsonb
)
returns jsonb language plpgsql security definer set search_path=public as $$
declare result jsonb;
begin
  if not public.can_write_love_space(p_love_space_id) then raise exception 'love_space_write_forbidden'; end if;
  if p_record_id is null then raise exception 'record_id_required'; end if;
  if p_payload is null or jsonb_typeof(p_payload)<>'object' then raise exception 'invalid_payload'; end if;
  if octet_length(p_payload::text)>32768 then raise exception 'payload_too_large'; end if;

  case p_record_type
    when 'event' then
      -- A09: + catatan panjang, ikon, lokasi, Special Day, pengulangan tahunan & pengingat.
      insert into public.love_space_events as e(
        id,love_space_id,created_by,title,event_date,category,notes,icon,location,
        is_special,recurring,remind_days_before
      ) values(
        p_record_id,p_love_space_id,auth.uid(),left(trim(p_payload->>'title'),160),
        (p_payload->>'event_date')::date,left(coalesce(p_payload->>'category','date'),60),
        left(coalesce(p_payload->>'notes',''),4000),left(coalesce(p_payload->>'icon',''),16),
        left(coalesce(p_payload->>'location',''),160),
        case when coalesce(p_payload->>'is_special','0') in ('1','true','t') then true else false end,
        case when p_payload->>'recurring' = 'yearly' then 'yearly' else 'none' end,
        greatest(0,least(365,coalesce((p_payload->>'remind_days_before')::integer,0)))
      )
      on conflict(id) do update set title=excluded.title,event_date=excluded.event_date,
        category=excluded.category,notes=excluded.notes,icon=excluded.icon,
        location=excluded.location,is_special=excluded.is_special,
        recurring=excluded.recurring,remind_days_before=excluded.remind_days_before
      where e.love_space_id=p_love_space_id returning to_jsonb(e) into result;
    when 'memory' then
      insert into public.love_space_memories as m(id,love_space_id,created_by,title,memory_date,notes)
      values(p_record_id,p_love_space_id,auth.uid(),left(trim(p_payload->>'title'),160),
             (p_payload->>'memory_date')::date,left(coalesce(p_payload->>'notes',''),4000))
      on conflict(id) do update set title=excluded.title,memory_date=excluded.memory_date,notes=excluded.notes
      where m.love_space_id=p_love_space_id returning to_jsonb(m) into result;
    when 'checkin' then
      insert into public.love_space_checkins as c(
        id,love_space_id,created_by,checkin_date,my_mood,partner_mood,connection_score,note
      ) values(
        p_record_id,p_love_space_id,auth.uid(),(p_payload->>'checkin_date')::date,
        (p_payload->>'my_mood')::integer,(p_payload->>'partner_mood')::integer,
        (p_payload->>'connection_score')::integer,left(coalesce(p_payload->>'note',''),2000)
      ) on conflict(love_space_id,created_by,checkin_date) do update set
        my_mood=excluded.my_mood,partner_mood=excluded.partner_mood,
        connection_score=excluded.connection_score,note=excluded.note
      returning to_jsonb(c) into result;
    when 'prompt_response' then
      insert into public.love_space_prompt_responses as r(
        id,love_space_id,created_by,prompt_key,category,prompt_text,my_answer,partner_answer,response_date
      ) values(
        p_record_id,p_love_space_id,auth.uid(),left(p_payload->>'prompt_key',120),
        left(coalesce(p_payload->>'category','connection'),60),left(p_payload->>'prompt_text',1000),
        left(coalesce(p_payload->>'my_answer',''),4000),left(coalesce(p_payload->>'partner_answer',''),4000),
        coalesce(nullif(p_payload->>'response_date','')::date,current_date)
      ) on conflict(id) do update set prompt_key=excluded.prompt_key,category=excluded.category,
        prompt_text=excluded.prompt_text,my_answer=excluded.my_answer,
        partner_answer=excluded.partner_answer,response_date=excluded.response_date
      where r.love_space_id=p_love_space_id returning to_jsonb(r) into result;
    when 'weekly_review' then
      insert into public.love_space_weekly_reviews as w(
        id,love_space_id,created_by,week_start,appreciation,wins,support_needed,shared_intention
      ) values(
        p_record_id,p_love_space_id,auth.uid(),(p_payload->>'week_start')::date,
        left(coalesce(p_payload->>'appreciation',''),4000),left(coalesce(p_payload->>'wins',''),4000),
        left(coalesce(p_payload->>'support_needed',''),4000),left(coalesce(p_payload->>'shared_intention',''),4000)
      ) on conflict(love_space_id,created_by,week_start) do update set
        appreciation=excluded.appreciation,wins=excluded.wins,support_needed=excluded.support_needed,
        shared_intention=excluded.shared_intention returning to_jsonb(w) into result;
    when 'bucket_item' then
      insert into public.love_space_bucket_items as b(
        id,love_space_id,created_by,title,category,target_date,is_done,completed_at
      ) values(
        p_record_id,p_love_space_id,auth.uid(),left(trim(p_payload->>'title'),200),
        left(coalesce(p_payload->>'category','dream'),60),nullif(p_payload->>'target_date','')::date,
        coalesce((p_payload->>'is_done')::boolean,false),
        case when coalesce((p_payload->>'is_done')::boolean,false) then now() else null end
      ) on conflict(id) do update set title=excluded.title,category=excluded.category,
        target_date=excluded.target_date,is_done=excluded.is_done,
        completed_at=case when excluded.is_done then coalesce(b.completed_at,now()) else null end
      where b.love_space_id=p_love_space_id returning to_jsonb(b) into result;
    when 'cycle' then
      insert into public.love_space_cycles as y(id,love_space_id,created_by,start_date,end_date,notes)
      values(p_record_id,p_love_space_id,auth.uid(),(p_payload->>'start_date')::date,
             nullif(p_payload->>'end_date','')::date,left(coalesce(p_payload->>'notes',''),2000))
      on conflict(id) do update set start_date=excluded.start_date,end_date=excluded.end_date,notes=excluded.notes
      where y.love_space_id=p_love_space_id returning to_jsonb(y) into result;
    else raise exception 'unsupported_love_record_type';
  end case;
  if result is null then raise exception 'love_record_conflict'; end if;
  return jsonb_build_object('record_type',p_record_type,'row',result);
end; $$;

-- ── 3) Hak akses (fungsi ditulis ulang dengan tanda tangan yang sama) ────────
revoke execute on function public.upsert_love_space_record(uuid,text,uuid,jsonb) from public,anon;
grant execute on function public.upsert_love_space_record(uuid,text,uuid,jsonb) to authenticated;
