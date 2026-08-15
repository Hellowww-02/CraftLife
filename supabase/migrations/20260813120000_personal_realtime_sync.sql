-- CraftLife Cloud Phase 3A-3E
-- Multi-device registry, conflict-safe personal tracker snapshots, history,
-- Realtime publication, and opportunistic server maintenance.

-- 3A: A public device identifier is not a credential. Refresh/access tokens remain
-- in the OS credential store and are never written to this table.
create table if not exists public.cloud_devices (
  id uuid primary key,
  user_id uuid not null references public.profiles(id) on delete cascade,
  device_name text not null default 'CraftLife Desktop'
    check (char_length(device_name) between 1 and 120),
  platform text not null default 'desktop'
    check (char_length(platform) between 1 and 80),
  app_version text not null default '' check (char_length(app_version) <= 40),
  first_seen_at timestamptz not null default now(),
  last_seen_at timestamptz not null default now(),
  revoked_at timestamptz,
  unique(user_id,id)
);
create index if not exists cloud_devices_user_seen
  on public.cloud_devices(user_id,last_seen_at desc);

-- 3B: Personal tracker data is private to its owner. A document-level snapshot
-- keeps the existing SQLite relational model intact and makes migration reversible.
create table if not exists public.personal_snapshots (
  user_id uuid not null references public.profiles(id) on delete cascade,
  document_key text not null check (document_key in ('tracker_v1')),
  revision bigint not null default 1 check (revision > 0),
  content_hash text not null check (content_hash ~ '^[0-9a-f]{64}$'),
  payload jsonb not null check (jsonb_typeof(payload) = 'object'),
  source_device_id uuid not null references public.cloud_devices(id) on delete restrict,
  client_updated_at timestamptz not null default now(),
  server_updated_at timestamptz not null default now(),
  primary key(user_id,document_key)
);
create index if not exists personal_snapshots_server_time
  on public.personal_snapshots(user_id,server_updated_at desc);

-- 3C: Keep the ten previous server versions for recovery. Clients cannot mutate
-- history directly.
create table if not exists public.personal_snapshot_versions (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references public.profiles(id) on delete cascade,
  document_key text not null,
  revision bigint not null,
  content_hash text not null,
  payload jsonb not null,
  source_device_id uuid references public.cloud_devices(id) on delete set null,
  client_updated_at timestamptz,
  server_updated_at timestamptz not null,
  archived_at timestamptz not null default now(),
  unique(user_id,document_key,revision)
);
create index if not exists personal_snapshot_versions_owner
  on public.personal_snapshot_versions(user_id,document_key,revision desc);

create or replace function public.archive_personal_snapshot_version()
returns trigger language plpgsql security definer set search_path=public as $$
begin
  if old.content_hash is distinct from new.content_hash then
    insert into public.personal_snapshot_versions(
      user_id,document_key,revision,content_hash,payload,source_device_id,
      client_updated_at,server_updated_at
    ) values(
      old.user_id,old.document_key,old.revision,old.content_hash,old.payload,
      old.source_device_id,old.client_updated_at,old.server_updated_at
    ) on conflict(user_id,document_key,revision) do nothing;

    delete from public.personal_snapshot_versions v
    where v.id in (
      select old_v.id
      from public.personal_snapshot_versions old_v
      where old_v.user_id=old.user_id and old_v.document_key=old.document_key
      order by old_v.revision desc
      offset 10
    );
  end if;
  return new;
end; $$;

drop trigger if exists personal_snapshot_archive on public.personal_snapshots;
create trigger personal_snapshot_archive
before update on public.personal_snapshots
for each row execute function public.archive_personal_snapshot_version();

-- Register/heartbeat a device. A revoked identifier cannot silently reactivate;
-- the desktop must create a fresh local device UUID after an explicit revoke.
create or replace function public.register_cloud_device(
  p_device_id uuid,
  p_device_name text default 'CraftLife Desktop',
  p_platform text default 'desktop',
  p_app_version text default ''
)
returns public.cloud_devices
language plpgsql security definer set search_path=public as $$
declare result public.cloud_devices;
begin
  if auth.uid() is null or not public.current_profile_active() then
    raise exception 'account_unavailable';
  end if;
  if p_device_id is null then raise exception 'device_id_required'; end if;

  select * into result from public.cloud_devices where id=p_device_id for update;
  if result.id is not null and result.user_id<>auth.uid() then
    raise exception 'device_owned_by_another_account';
  end if;
  if result.revoked_at is not null then raise exception 'device_revoked'; end if;

  insert into public.cloud_devices(id,user_id,device_name,platform,app_version,last_seen_at)
  values(
    p_device_id,auth.uid(),left(coalesce(nullif(trim(p_device_name),''),'CraftLife Desktop'),120),
    left(coalesce(nullif(trim(p_platform),''),'desktop'),80),left(coalesce(p_app_version,''),40),now()
  )
  on conflict(id) do update set
    device_name=excluded.device_name,
    platform=excluded.platform,
    app_version=excluded.app_version,
    last_seen_at=now()
  returning * into result;
  return result;
end; $$;

create or replace function public.revoke_cloud_device(p_device_id uuid)
returns boolean
language plpgsql security definer set search_path=public as $$
begin
  update public.cloud_devices set revoked_at=coalesce(revoked_at,now())
  where id=p_device_id and user_id=auth.uid();
  return found;
end; $$;

-- 3D: Optimistic concurrency. A stale client receives the authoritative row and
-- must ask the user to keep local data or restore cloud data; nothing is silently
-- overwritten.
create or replace function public.upsert_personal_snapshot(
  p_document_key text,
  p_base_revision bigint,
  p_content_hash text,
  p_payload jsonb,
  p_device_id uuid,
  p_client_updated_at timestamptz default now()
)
returns jsonb
language plpgsql security definer set search_path=public as $$
declare
  current_row public.personal_snapshots;
  result public.personal_snapshots;
  safe_client_time timestamptz;
begin
  if auth.uid() is null or not public.current_profile_active() then
    raise exception 'account_unavailable';
  end if;
  if p_document_key not in ('tracker_v1') then raise exception 'unsupported_document'; end if;
  if p_base_revision is null or p_base_revision<0 then raise exception 'invalid_base_revision'; end if;
  if p_content_hash is null or p_content_hash !~ '^[0-9a-f]{64}$' then raise exception 'invalid_content_hash'; end if;
  if p_payload is null or jsonb_typeof(p_payload)<>'object' then raise exception 'invalid_payload'; end if;
  if octet_length(p_payload::text)>8388608 then raise exception 'payload_too_large'; end if;
  if not exists(
    select 1 from public.cloud_devices
    where id=p_device_id and user_id=auth.uid() and revoked_at is null
  ) then raise exception 'device_not_registered'; end if;

  safe_client_time=least(coalesce(p_client_updated_at,now()),now()+interval '5 minutes');
  select * into current_row from public.personal_snapshots
    where user_id=auth.uid() and document_key=p_document_key for update;

  if current_row.user_id is null then
    if p_base_revision<>0 then
      return jsonb_build_object('ok',false,'conflict',true,'reason','missing_remote_base');
    end if;
    insert into public.personal_snapshots(
      user_id,document_key,revision,content_hash,payload,source_device_id,
      client_updated_at,server_updated_at
    ) values(
      auth.uid(),p_document_key,1,p_content_hash,p_payload,p_device_id,
      safe_client_time,now()
    ) returning * into result;
    return jsonb_build_object('ok',true,'conflict',false,'snapshot',to_jsonb(result));
  end if;

  if current_row.revision<>p_base_revision then
    return jsonb_build_object(
      'ok',false,'conflict',true,'reason','revision_mismatch',
      'snapshot',to_jsonb(current_row)
    );
  end if;

  if current_row.content_hash=p_content_hash then
    update public.cloud_devices set last_seen_at=now() where id=p_device_id;
    return jsonb_build_object('ok',true,'conflict',false,'unchanged',true,
                              'snapshot',to_jsonb(current_row));
  end if;

  update public.personal_snapshots set
    revision=revision+1,
    content_hash=p_content_hash,
    payload=p_payload,
    source_device_id=p_device_id,
    client_updated_at=safe_client_time,
    server_updated_at=now()
  where user_id=auth.uid() and document_key=p_document_key
  returning * into result;
  update public.cloud_devices set last_seen_at=now() where id=p_device_id;
  return jsonb_build_object('ok',true,'conflict',false,'snapshot',to_jsonb(result));
end; $$;

-- Return a selected historical revision without exposing another user's data.
create or replace function public.get_personal_snapshot_version(
  p_document_key text,
  p_revision bigint
)
returns jsonb
language sql stable security definer set search_path=public as $$
  select to_jsonb(v) from public.personal_snapshot_versions v
  where v.user_id=auth.uid() and v.document_key=p_document_key and v.revision=p_revision
$$;

-- 3E: Safe, bounded maintenance. It runs opportunistically when a linked desktop
-- syncs. A later production phase may schedule the same function with pg_cron.
create or replace function public.run_cloud_maintenance()
returns jsonb
language plpgsql security definer set search_path=public as $$
declare
  typing_count integer:=0;
  presence_count integer:=0;
  expired_count integer:=0;
  finalized_count integer:=0;
  c record;
  challenger_score bigint;
  opponent_score bigint;
  winner uuid;
begin
  -- EXECUTE is granted only to authenticated clients (plus the database owner),
  -- so the same bounded function can later be scheduled safely by pg_cron.
  -- Prevent concurrent clients from doing the same bounded maintenance work.
  if not pg_try_advisory_xact_lock(20260813,3) then
    return jsonb_build_object('ok',true,'skipped',true);
  end if;

  delete from public.conversation_typing where expires_at<now();
  get diagnostics typing_count=row_count;

  update public.user_presence set status='offline',updated_at=now()
  where status<>'offline' and last_seen_at<now()-interval '2 minutes';
  get diagnostics presence_count=row_count;

  update public.online_pvp_challenges set status='expired',resolved_at=now()
  where status='pending' and created_at<now()-interval '14 days';
  get diagnostics expired_count=row_count;

  for c in
    select * from public.online_pvp_challenges
    where status='active' and end_at<=now()
    order by end_at for update skip locked limit 100
  loop
    select coalesce(sum(points),0)::bigint into challenger_score
      from public.productivity_events
      where user_id=c.challenger_id and completed_at>=c.start_at and completed_at<=c.end_at;
    select coalesce(sum(points),0)::bigint into opponent_score
      from public.productivity_events
      where user_id=c.opponent_id and completed_at>=c.start_at and completed_at<=c.end_at;
    winner=case when challenger_score>opponent_score then c.challenger_id
                when opponent_score>challenger_score then c.opponent_id else null end;

    update public.online_pvp_challenges
      set status='completed',winner_id=winner,resolved_at=now() where id=c.id;
    insert into public.online_pvp_rewards(challenge_id,user_id,xp_reward,gold_reward) values
      (c.id,c.challenger_id,case when winner=c.challenger_id then 100 else 25 end,
       case when winner=c.challenger_id then 50 else 10 end),
      (c.id,c.opponent_id,case when winner=c.opponent_id then 100 else 25 end,
       case when winner=c.opponent_id then 50 else 10 end)
    on conflict do nothing;
    insert into public.social_notifications(user_id,notification_type,entity_type,entity_id,payload)
    values
      (c.challenger_id,'pvp_completed','online_pvp',c.id,
       jsonb_build_object('winner_id',winner,'my_score',challenger_score,'opponent_score',opponent_score)),
      (c.opponent_id,'pvp_completed','online_pvp',c.id,
       jsonb_build_object('winner_id',winner,'my_score',opponent_score,'opponent_score',challenger_score));
    finalized_count=finalized_count+1;
  end loop;

  return jsonb_build_object(
    'ok',true,'typing_removed',typing_count,'presence_offline',presence_count,
    'pvp_expired',expired_count,'pvp_finalized',finalized_count
  );
end; $$;

-- RLS: owners can read; writes are intentionally RPC-only.
alter table public.cloud_devices enable row level security;
alter table public.personal_snapshots enable row level security;
alter table public.personal_snapshot_versions enable row level security;

create policy cloud_devices_owner_read on public.cloud_devices
  for select to authenticated using(user_id=auth.uid());
create policy personal_snapshots_owner_read on public.personal_snapshots
  for select to authenticated using(user_id=auth.uid());
create policy personal_snapshot_versions_owner_read on public.personal_snapshot_versions
  for select to authenticated using(user_id=auth.uid());

revoke all on public.cloud_devices from anon;
revoke all on public.personal_snapshots from anon;
revoke all on public.personal_snapshot_versions from anon;
revoke insert,update,delete on public.cloud_devices from authenticated;
revoke insert,update,delete on public.personal_snapshots from authenticated;
revoke insert,update,delete on public.personal_snapshot_versions from authenticated;

revoke execute on function public.register_cloud_device(uuid,text,text,text) from public,anon;
revoke execute on function public.revoke_cloud_device(uuid) from public,anon;
revoke execute on function public.upsert_personal_snapshot(text,bigint,text,jsonb,uuid,timestamptz) from public,anon;
revoke execute on function public.get_personal_snapshot_version(text,bigint) from public,anon;
revoke execute on function public.run_cloud_maintenance() from public,anon;

grant select on public.cloud_devices,public.personal_snapshots,
  public.personal_snapshot_versions to authenticated;
grant execute on function public.register_cloud_device(uuid,text,text,text) to authenticated;
grant execute on function public.revoke_cloud_device(uuid) to authenticated;
grant execute on function public.upsert_personal_snapshot(text,bigint,text,jsonb,uuid,timestamptz) to authenticated;
grant execute on function public.get_personal_snapshot_version(text,bigint) to authenticated;
grant execute on function public.run_cloud_maintenance() to authenticated;

-- REPLICA IDENTITY FULL gives Realtime enough old/new data for deterministic pulls.
alter table public.personal_snapshots replica identity full;
do $$ begin
  alter publication supabase_realtime add table public.personal_snapshots;
exception when duplicate_object then null; end $$;
do $$ begin
  alter publication supabase_realtime add table public.cloud_devices;
exception when duplicate_object then null; end $$;

notify pgrst,'reload schema';
