-- M04a — Channel A: union-merge entity log for append-only tables.
-- Closes the first half of G1 for the tables where conflict is impossible.
--
-- Rationale (roadmap K10): a row in these tables is written once and never
-- edited. Two devices appending concurrently therefore cannot conflict, and the
-- correct merge is a set union keyed by a client-generated UUID — not
-- last-writer-wins, which is what the whole-document snapshot did and is why a
-- device could silently lose the other device's rows.
--
-- The allowlist is deliberately narrow and deliberately a server-side constant:
-- a table only belongs here if no code path ever UPDATEs it. Measured against
-- database.py at M04a, that is these seven. Tables that merely avoid UPDATE by
-- doing delete+insert (recipes, relationship_events) are NOT append-only and go
-- through Channel B in M04b.
--
-- Konvensi mengikuti migration sebelumnya (lowercase, security definer,
-- error code sebagai exception message, idempotency by key).

-- ---------------------------------------------------------------------------
-- Storage
-- ---------------------------------------------------------------------------
create table if not exists public.sync_entities (
  user_id uuid not null references auth.users(id) on delete cascade,
  table_name text not null,
  entity_uuid uuid not null,
  payload jsonb not null,
  rev bigint not null default 1,
  client_updated_at timestamptz not null,
  server_updated_at timestamptz not null default now(),
  deleted_at timestamptz,
  origin_device_id uuid,
  primary key (user_id, table_name, entity_uuid)
);

-- Pull is "everything for me in this table changed since X", so that is the
-- access path and it gets an index.
create index if not exists sync_entities_pull
  on public.sync_entities(user_id, table_name, server_updated_at);

comment on table public.sync_entities is
  'Row-level sync store. Channel A (append-only) writes here from M04a; Channel B (row-level 3-way merge) joins in M04b.';

-- ---------------------------------------------------------------------------
-- Allowlist
-- ---------------------------------------------------------------------------
-- A function rather than a hardcoded IN-list so the client, the RPC and the
-- pgTAP tests all read the same single source of truth (P2).
create or replace function public.sync_append_only_tables()
returns text[]
language sql immutable set search_path=public as $$
  select array[
    'food_logs',
    'water_logs',
    'health_logs',
    'task_history',
    'pomodoro_sessions',
    'sport_rep_logs',
    'supplies_tx'
  ]
$$;

-- ---------------------------------------------------------------------------
-- Append (Channel A) — insert-if-absent, never update
-- ---------------------------------------------------------------------------
create or replace function public.append_entities(
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
  v_client_time timestamptz;
  v_inserted integer := 0;
  v_skipped integer := 0;
begin
  if auth.uid() is null or not public.current_profile_active() then
    raise exception 'account_unavailable';
  end if;
  if p_table_name is null or not (p_table_name = any(public.sync_append_only_tables())) then
    raise exception 'unsupported_table';
  end if;
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

  -- Clamp skewed client clocks the same way upsert_personal_snapshot does, so a
  -- device with a wrong clock cannot write a future timestamp that hides its own
  -- rows from an incremental pull.
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

    -- Union semantics: an entity already present is left exactly as it is.
    -- Replaying the same outbox twice must be a no-op, not a second row and not
    -- an edit.
    insert into public.sync_entities(
      user_id, table_name, entity_uuid, payload, rev,
      client_updated_at, server_updated_at, origin_device_id
    ) values (
      auth.uid(), p_table_name, v_uuid, v_row, 1,
      v_client_time, now(), p_device_id
    )
    on conflict (user_id, table_name, entity_uuid) do nothing;

    if found then
      v_inserted := v_inserted + 1;
    else
      v_skipped := v_skipped + 1;
    end if;
  end loop;

  update public.cloud_devices set last_seen_at = now() where id = p_device_id;

  return jsonb_build_object(
    'ok', true,
    'table', p_table_name,
    'inserted', v_inserted,
    'skipped', v_skipped
  );
end; $$;

-- ---------------------------------------------------------------------------
-- Pull (Channel A)
-- ---------------------------------------------------------------------------
create or replace function public.fetch_entities(
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
  if p_table_name is null or not (p_table_name = any(public.sync_append_only_tables())) then
    raise exception 'unsupported_table';
  end if;
  if p_limit is null or p_limit < 1 or p_limit > 20000 then
    raise exception 'invalid_limit';
  end if;

  select coalesce(jsonb_agg(to_jsonb(e) order by e.server_updated_at), '[]'::jsonb)
    into v_rows
  from (
    select entity_uuid, payload, rev, client_updated_at, server_updated_at, deleted_at
    from public.sync_entities
    where user_id = auth.uid()
      and table_name = p_table_name
      and (p_since is null or server_updated_at > p_since)
    order by server_updated_at
    limit p_limit
  ) e;

  return jsonb_build_object('ok', true, 'table', p_table_name, 'rows', v_rows);
end; $$;

-- ---------------------------------------------------------------------------
-- RLS: owners can read; writes are RPC-only.
-- ---------------------------------------------------------------------------
alter table public.sync_entities enable row level security;

create policy sync_entities_owner_read on public.sync_entities
  for select to authenticated using(user_id = auth.uid());

revoke all on public.sync_entities from anon;
revoke insert, update, delete on public.sync_entities from authenticated;

revoke execute on function public.append_entities(text, jsonb, uuid, timestamptz) from public, anon;
revoke execute on function public.fetch_entities(text, timestamptz, integer) from public, anon;

grant execute on function public.append_entities(text, jsonb, uuid, timestamptz) to authenticated;
grant execute on function public.fetch_entities(text, timestamptz, integer) to authenticated;
