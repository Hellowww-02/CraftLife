-- M04b — Channel B: row-level 3-way merge for mutable entities.
-- Closes G1 on the server side and G4 (tombstone propagation).
--
-- Why per field and not per row: two devices offline at the same time usually
-- edit DIFFERENT fields of the same row. Replacing the whole row makes one
-- device's edit vanish; comparing each field against the version the client
-- started from (base_rev) keeps both.
--
--   base   = the payload as the client last saw it (looked up by base_rev)
--   ours   = what the server holds now
--   theirs = what the client is pushing
--
--   theirs == base  -> the client did not touch this field; keep ours
--   ours   == base  -> only the client changed it; take theirs
--   both changed    -> LWW by client timestamp, and the losing value is archived
--                      in sync_entity_revisions rather than discarded (K11/P6)
--
-- If the base revision is not on the server (first push from a device, or the
-- revision was garbage-collected) the merge degrades to a two-way per-field LWW
-- between ours and theirs. It never degrades to whole-row replacement.
--
-- Konvensi mengikuti migration sebelumnya.

-- ---------------------------------------------------------------------------
-- Archive of superseded values — the "losing side" K11 requires be recoverable
-- ---------------------------------------------------------------------------
create table if not exists public.sync_entity_revisions (
  id bigserial primary key,
  user_id uuid not null references auth.users(id) on delete cascade,
  table_name text not null,
  entity_uuid uuid not null,
  rev bigint not null,
  payload jsonb not null,
  client_updated_at timestamptz not null,
  origin_device_id uuid,
  superseded_at timestamptz not null default now()
);

create index if not exists sync_entity_revisions_lookup
  on public.sync_entity_revisions(user_id, table_name, entity_uuid, rev);

create index if not exists sync_entity_revisions_gc
  on public.sync_entity_revisions(superseded_at);

comment on table public.sync_entity_revisions is
  'Every superseded entity payload. This is what makes a lost field recoverable instead of silently gone (K11).';

-- ---------------------------------------------------------------------------
-- Tombstones
-- ---------------------------------------------------------------------------
create table if not exists public.sync_tombstones (
  user_id uuid not null references auth.users(id) on delete cascade,
  table_name text not null,
  entity_uuid uuid not null,
  deleted_at timestamptz not null,
  origin_device_id uuid,
  primary key (user_id, table_name, entity_uuid)
);

create index if not exists sync_tombstones_pull
  on public.sync_tombstones(user_id, table_name, deleted_at);

-- ---------------------------------------------------------------------------
-- Allowlist
-- ---------------------------------------------------------------------------
-- Deliberately NOT a hardcoded list of 34 names. The Python side owns
-- CHANNEL_B_TABLES; duplicating it here would be a second source of truth that
-- drifts (P2). What the server can and must enforce is that the label is a safe
-- identifier and is not one of the append-only tables, which have their own
-- union semantics and must go through append_entities().
create or replace function public.assert_mutable_entity_table(p_table_name text)
returns void
language plpgsql immutable set search_path=public as $$
begin
  if p_table_name is null or p_table_name !~ '^[a-z_][a-z0-9_]{0,62}$' then
    raise exception 'unsupported_table';
  end if;
  if p_table_name = any(public.sync_append_only_tables()) then
    raise exception 'append_only_table_use_append_entities';
  end if;
end; $$;

-- ---------------------------------------------------------------------------
-- Upsert (Channel B)
-- ---------------------------------------------------------------------------
create or replace function public.upsert_entities(
  p_table_name text,
  p_rows jsonb,
  p_device_id uuid,
  p_client_updated_at timestamptz default now()
)
returns jsonb
language plpgsql security definer set search_path=public as $$
declare
  v_row jsonb;
  v_uuid uuid;
  v_payload jsonb;
  v_base_rev bigint;
  v_row_time timestamptz;
  v_deleted timestamptz;
  v_client_time timestamptz;
  v_current public.sync_entities;
  v_base jsonb;
  v_key text;
  v_merged jsonb;
  v_ours_value jsonb;
  v_theirs_value jsonb;
  v_base_value jsonb;
  v_inserted integer := 0;
  v_updated integer := 0;
  v_conflicted integer := 0;
  v_deleted_count integer := 0;
  v_unchanged integer := 0;
  v_rows jsonb := '[]'::jsonb;
begin
  if auth.uid() is null or not public.current_profile_active() then
    raise exception 'account_unavailable';
  end if;
  perform public.assert_mutable_entity_table(p_table_name);
  if p_rows is null or jsonb_typeof(p_rows) <> 'array' then
    raise exception 'invalid_rows';
  end if;
  if jsonb_array_length(p_rows) > 5000 then
    raise exception 'too_many_rows';
  end if;
  if octet_length(p_rows::text) > 8388608 then
    raise exception 'payload_too_large';
  end if;
  if not exists(
    select 1 from public.cloud_devices
    where id = p_device_id and user_id = auth.uid() and revoked_at is null
  ) then
    raise exception 'device_not_registered';
  end if;

  v_client_time := least(coalesce(p_client_updated_at, now()), now() + interval '5 minutes');

  for v_row in select * from jsonb_array_elements(p_rows)
  loop
    if jsonb_typeof(v_row) <> 'object' then
      raise exception 'invalid_row';
    end if;
    begin
      v_uuid := (v_row ->> 'uuid')::uuid;
    exception when others then
      raise exception 'invalid_entity_uuid';
    end;

    v_payload := coalesce(v_row -> 'payload', v_row) - 'uuid' - 'payload';
    v_base_rev := coalesce((v_row ->> 'base_rev')::bigint, 0);
    v_row_time := coalesce((v_row ->> 'updated_at')::timestamptz, v_client_time);
    v_deleted := (v_row ->> 'deleted_at')::timestamptz;

    select * into v_current from public.sync_entities
      where user_id = auth.uid() and table_name = p_table_name and entity_uuid = v_uuid
      for update;

    if v_current.user_id is null then
      insert into public.sync_entities(
        user_id, table_name, entity_uuid, payload, rev,
        client_updated_at, server_updated_at, deleted_at, origin_device_id
      ) values (
        auth.uid(), p_table_name, v_uuid, v_payload, 1,
        v_row_time, now(), v_deleted, p_device_id
      );
      if v_deleted is not null then
        insert into public.sync_tombstones(user_id, table_name, entity_uuid, deleted_at, origin_device_id)
        values (auth.uid(), p_table_name, v_uuid, v_deleted, p_device_id)
        on conflict (user_id, table_name, entity_uuid)
        do update set deleted_at = excluded.deleted_at;
        v_deleted_count := v_deleted_count + 1;
      end if;
      v_inserted := v_inserted + 1;
      v_rows := v_rows || jsonb_build_array(jsonb_build_object('uuid', v_uuid, 'rev', 1));
      continue;
    end if;

    -- A replay: the device never received the acknowledgement and resent the
    -- identical row. Nothing here is superseded, so nothing may be archived -
    -- otherwise every redundant send grows the loser archive with another copy
    -- of a payload that was never actually replaced.
    if v_payload = v_current.payload
       and v_row_time = v_current.client_updated_at
       and v_deleted is not distinct from v_current.deleted_at then
      v_unchanged := v_unchanged + 1;
      v_rows := v_rows || jsonb_build_array(
        jsonb_build_object('uuid', v_uuid, 'rev', v_current.rev));
      continue;
    end if;

    -- Archive the version we are about to supersede, so nothing is unrecoverable.
    insert into public.sync_entity_revisions(
      user_id, table_name, entity_uuid, rev, payload, client_updated_at, origin_device_id
    ) values (
      auth.uid(), p_table_name, v_uuid, v_current.rev, v_current.payload,
      v_current.client_updated_at, v_current.origin_device_id
    );

    -- The version the client started from, when we still have it.
    select payload into v_base from public.sync_entity_revisions
      where user_id = auth.uid() and table_name = p_table_name
        and entity_uuid = v_uuid and rev = v_base_rev
      order by superseded_at desc limit 1;

    v_merged := v_current.payload;
    for v_key in select key from jsonb_object_keys(v_payload) as key
    loop
      v_ours_value := v_current.payload -> v_key;
      v_theirs_value := v_payload -> v_key;
      v_base_value := v_base -> v_key;

      if v_base is not null and v_theirs_value = v_base_value then
        -- The client never touched this field; whatever the server has is newer.
        continue;
      end if;
      if v_base is not null and v_ours_value = v_base_value then
        v_merged := jsonb_set(v_merged, array[v_key], v_theirs_value, true);
        continue;
      end if;
      if v_ours_value is distinct from v_theirs_value then
        -- Genuine conflict on this field.
        v_conflicted := v_conflicted + 1;
        if v_row_time > v_current.client_updated_at then
          v_merged := jsonb_set(v_merged, array[v_key], v_theirs_value, true);
        end if;
        -- Either way the pre-merge value is already archived above.
      end if;
    end loop;

    update public.sync_entities set
      payload = v_merged,
      rev = v_current.rev + 1,
      client_updated_at = greatest(v_current.client_updated_at, v_row_time),
      server_updated_at = now(),
      deleted_at = coalesce(v_deleted, v_current.deleted_at),
      origin_device_id = p_device_id
    where user_id = auth.uid() and table_name = p_table_name and entity_uuid = v_uuid;

    if v_deleted is not null then
      insert into public.sync_tombstones(user_id, table_name, entity_uuid, deleted_at, origin_device_id)
      values (auth.uid(), p_table_name, v_uuid, v_deleted, p_device_id)
      on conflict (user_id, table_name, entity_uuid)
      do update set deleted_at = excluded.deleted_at;
      v_deleted_count := v_deleted_count + 1;
    end if;
    v_updated := v_updated + 1;
    v_rows := v_rows || jsonb_build_array(
      jsonb_build_object('uuid', v_uuid, 'rev', v_current.rev + 1));
  end loop;

  update public.cloud_devices set last_seen_at = now() where id = p_device_id;

  return jsonb_build_object(
    'ok', true, 'table', p_table_name,
    'inserted', v_inserted, 'updated', v_updated,
    'field_conflicts', v_conflicted, 'deleted', v_deleted_count,
    'unchanged', v_unchanged,
    -- The client needs these to record base_rev. Without them sync_entity_state
    -- never advances, every later push still claims base_rev 0, and the 3-way
    -- merge silently degrades to 2-way last-writer-wins forever.
    'rows', v_rows
  );
end; $$;

-- ---------------------------------------------------------------------------
-- Tombstone push / pull, and garbage collection
-- ---------------------------------------------------------------------------
create or replace function public.push_tombstones(
  p_table_name text,
  p_tombstones jsonb,
  p_device_id uuid
)
returns jsonb
language plpgsql security definer set search_path=public as $$
declare
  v_item jsonb;
  v_uuid uuid;
  v_count integer := 0;
begin
  if auth.uid() is null or not public.current_profile_active() then
    raise exception 'account_unavailable';
  end if;
  perform public.assert_mutable_entity_table(p_table_name);
  if p_tombstones is null or jsonb_typeof(p_tombstones) <> 'array' then
    raise exception 'invalid_rows';
  end if;
  if not exists(
    select 1 from public.cloud_devices
    where id = p_device_id and user_id = auth.uid() and revoked_at is null
  ) then
    raise exception 'device_not_registered';
  end if;

  for v_item in select * from jsonb_array_elements(p_tombstones)
  loop
    begin
      v_uuid := (v_item ->> 'uuid')::uuid;
    exception when others then
      raise exception 'invalid_entity_uuid';
    end;
    insert into public.sync_tombstones(user_id, table_name, entity_uuid, deleted_at, origin_device_id)
    values (auth.uid(), p_table_name, v_uuid,
            coalesce((v_item ->> 'deleted_at')::timestamptz, now()), p_device_id)
    on conflict (user_id, table_name, entity_uuid)
    do update set deleted_at = greatest(public.sync_tombstones.deleted_at, excluded.deleted_at);
    v_count := v_count + 1;
  end loop;

  return jsonb_build_object('ok', true, 'table', p_table_name, 'recorded', v_count);
end; $$;

create or replace function public.fetch_tombstones(
  p_table_name text,
  p_since timestamptz default null,
  p_limit integer default 5000
)
returns jsonb
language plpgsql security definer set search_path=public as $$
declare
  v_rows jsonb;
begin
  if auth.uid() is null or not public.current_profile_active() then
    raise exception 'account_unavailable';
  end if;
  perform public.assert_mutable_entity_table(p_table_name);
  if p_limit is null or p_limit < 1 or p_limit > 20000 then
    raise exception 'invalid_limit';
  end if;

  select coalesce(jsonb_agg(to_jsonb(t) order by t.deleted_at), '[]'::jsonb) into v_rows
  from (
    select entity_uuid, deleted_at
    from public.sync_tombstones
    where user_id = auth.uid() and table_name = p_table_name
      and (p_since is null or deleted_at > p_since)
    order by deleted_at limit p_limit
  ) t;

  return jsonb_build_object('ok', true, 'table', p_table_name, 'rows', v_rows);
end; $$;

-- Roadmap M04: garbage-collect tombstones after N days. 30 days is long enough
-- for a device that has been offline a month to still learn about a deletion,
-- and short enough that the table does not grow without bound.
create or replace function public.gc_sync_tombstones(p_retention_days integer default 30)
returns integer
language plpgsql security definer set search_path=public as $$
declare
  v_removed integer;
begin
  if auth.uid() is null then
    raise exception 'account_unavailable';
  end if;
  if p_retention_days is null or p_retention_days < 1 then
    raise exception 'invalid_retention';
  end if;
  delete from public.sync_tombstones
    where user_id = auth.uid()
      and deleted_at < now() - make_interval(days => p_retention_days);
  get diagnostics v_removed = row_count;
  return v_removed;
end; $$;

-- Recover a superseded value. This is what makes "the loser is stored, not
-- discarded" something a user can actually act on (K11).
create or replace function public.fetch_entity_revisions(
  p_table_name text,
  p_entity_uuid uuid,
  p_limit integer default 20
)
returns jsonb
language plpgsql security definer set search_path=public as $$
declare
  v_rows jsonb;
begin
  if auth.uid() is null or not public.current_profile_active() then
    raise exception 'account_unavailable';
  end if;
  perform public.assert_mutable_entity_table(p_table_name);
  if p_limit is null or p_limit < 1 or p_limit > 200 then
    raise exception 'invalid_limit';
  end if;

  select coalesce(jsonb_agg(to_jsonb(r) order by r.rev desc), '[]'::jsonb) into v_rows
  from (
    select rev, payload, client_updated_at, superseded_at, origin_device_id
    from public.sync_entity_revisions
    where user_id = auth.uid() and table_name = p_table_name and entity_uuid = p_entity_uuid
    order by rev desc limit p_limit
  ) r;

  return jsonb_build_object('ok', true, 'rows', v_rows);
end; $$;

-- ---------------------------------------------------------------------------
-- RLS: owners can read; writes are RPC-only.
-- ---------------------------------------------------------------------------
alter table public.sync_entity_revisions enable row level security;
alter table public.sync_tombstones enable row level security;

create policy sync_entity_revisions_owner_read on public.sync_entity_revisions
  for select to authenticated using(user_id = auth.uid());
create policy sync_tombstones_owner_read on public.sync_tombstones
  for select to authenticated using(user_id = auth.uid());

revoke all on public.sync_entity_revisions from anon;
revoke all on public.sync_tombstones from anon;
revoke insert, update, delete on public.sync_entity_revisions from authenticated;
revoke insert, update, delete on public.sync_tombstones from authenticated;

revoke execute on function public.assert_mutable_entity_table(text) from public, anon;
revoke execute on function public.upsert_entities(text, jsonb, uuid, timestamptz) from public, anon;
revoke execute on function public.push_tombstones(text, jsonb, uuid) from public, anon;
revoke execute on function public.fetch_tombstones(text, timestamptz, integer) from public, anon;
revoke execute on function public.gc_sync_tombstones(integer) from public, anon;
revoke execute on function public.fetch_entity_revisions(text, uuid, integer) from public, anon;

grant execute on function public.assert_mutable_entity_table(text) to authenticated;
grant execute on function public.upsert_entities(text, jsonb, uuid, timestamptz) to authenticated;
grant execute on function public.push_tombstones(text, jsonb, uuid) to authenticated;
grant execute on function public.fetch_tombstones(text, timestamptz, integer) to authenticated;
grant execute on function public.gc_sync_tombstones(integer) to authenticated;
grant execute on function public.fetch_entity_revisions(text, uuid, integer) to authenticated;
