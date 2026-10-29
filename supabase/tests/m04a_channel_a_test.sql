-- M04a — Channel A behaviour.
--
-- Every other file in this directory asserts schema shape (has_table,
-- has_function, RLS, privileges). None of them executes an RPC. Channel A's
-- entire value is behavioural — union not replace, idempotent replay, never
-- update — so this is the first test here that actually calls the functions.

begin;
create extension if not exists pgtap with schema extensions;
select plan(22);

-- ---------------------------------------------------------------------------
-- Fixtures: two verified users with active profiles, each with a device.
-- Created as the table owner, before dropping to the `authenticated` role.
-- ---------------------------------------------------------------------------
insert into auth.users(id, email, email_confirmed_at) values
  ('11111111-1111-1111-1111-111111111111', 'channel_a@example.test', now()),
  ('22222222-2222-2222-2222-222222222222', 'channel_b@example.test', now());

-- The on_auth_user_created trigger already created both profiles, so these are
-- updates, not inserts.
update public.profiles set username = 'channel_a', display_name = 'Channel A'
  where id = '11111111-1111-1111-1111-111111111111';
update public.profiles set username = 'channel_b', display_name = 'Channel B'
  where id = '22222222-2222-2222-2222-222222222222';

set local request.jwt.claim.sub = '11111111-1111-1111-1111-111111111111';
set local role authenticated;

select public.register_cloud_device(
  'aaaaaaaa-0000-0000-0000-000000000001', 'Device A', 'desktop', '1.7.4');

-- ---------------------------------------------------------------------------
-- Schema
-- ---------------------------------------------------------------------------
select has_table('public', 'sync_entities', 'Channel A/B row store exists');
select col_is_pk('public', 'sync_entities',
  array['user_id', 'table_name', 'entity_uuid'],
  'An entity is identified by owner, table and client UUID');
select has_index('public', 'sync_entities', 'sync_entities_pull',
  'Incremental pull has an index');

-- ---------------------------------------------------------------------------
-- Allowlist: the single source of truth for which tables are append-only
-- ---------------------------------------------------------------------------
select is(array_length(public.sync_append_only_tables(), 1), 7,
  'Seven tables measured as append-only at M04a');
select ok('food_logs' = any(public.sync_append_only_tables()),
  'food_logs is append-only');
select ok(not ('habits' = any(public.sync_append_only_tables())),
  'habits is mutable and must not be in Channel A');
select ok(not ('recipes' = any(public.sync_append_only_tables())),
  'recipes only avoids UPDATE via delete+insert, so it is not append-only');

-- ---------------------------------------------------------------------------
-- Append, replay, and union
-- ---------------------------------------------------------------------------
select is(
  (public.append_entities('food_logs',
    '[{"uuid":"eeeeeeee-0000-0000-0000-000000000001","name":"meal 1"},
      {"uuid":"eeeeeeee-0000-0000-0000-000000000002","name":"meal 2"},
      {"uuid":"eeeeeeee-0000-0000-0000-000000000003","name":"meal 3"}]'::jsonb,
    'aaaaaaaa-0000-0000-0000-000000000001') ->> 'inserted')::int,
  3, 'First append inserts all three rows');

select is(
  (public.append_entities('food_logs',
    '[{"uuid":"eeeeeeee-0000-0000-0000-000000000001","name":"meal 1"},
      {"uuid":"eeeeeeee-0000-0000-0000-000000000002","name":"meal 2"},
      {"uuid":"eeeeeeee-0000-0000-0000-000000000003","name":"meal 3"}]'::jsonb,
    'aaaaaaaa-0000-0000-0000-000000000001') ->> 'skipped')::int,
  3, 'Replaying the same outbox is a no-op, not a duplicate');

select is(jsonb_array_length(
    public.fetch_entities('food_logs') -> 'rows'), 3,
  'Replay did not create extra rows');

-- The core Channel A guarantee: an existing entity is never edited, so a stale
-- device replaying an old version of a row cannot overwrite a newer one.
select is(
  (public.append_entities('food_logs',
    '[{"uuid":"eeeeeeee-0000-0000-0000-000000000001","name":"STALE OVERWRITE"}]'::jsonb,
    'aaaaaaaa-0000-0000-0000-000000000001') ->> 'inserted')::int,
  0, 'Re-appending a known UUID inserts nothing');

select is(
  (select elem -> 'payload' ->> 'name'
     from jsonb_array_elements(public.fetch_entities('food_logs') -> 'rows') elem
    where elem ->> 'entity_uuid' = 'eeeeeeee-0000-0000-0000-000000000001'),
  'meal 1', 'Channel A never updates: the original payload survives');

-- Two devices appending disjoint rows is the scenario that lost data under
-- whole-document LWW. Both must survive.
select public.register_cloud_device(
  'aaaaaaaa-0000-0000-0000-000000000002', 'Device B', 'android', '2.0.0');
select is(
  (public.append_entities('food_logs',
    '[{"uuid":"eeeeeeee-0000-0000-0000-000000000004","name":"meal from other device"}]'::jsonb,
    'aaaaaaaa-0000-0000-0000-000000000002') ->> 'inserted')::int,
  1, 'A second device can append');
select is(jsonb_array_length(public.fetch_entities('food_logs') -> 'rows'), 4,
  'Union: rows from both devices are all present');

-- ---------------------------------------------------------------------------
-- Rejections
-- ---------------------------------------------------------------------------
select throws_ok(
  $sql$select public.append_entities('habits', '[]'::jsonb, 'aaaaaaaa-0000-0000-0000-000000000001')$sql$,
  'unsupported_table', 'A mutable table is refused by Channel A');
select throws_ok(
  $sql$select public.append_entities('food_logs', '[{"uuid":"not-a-uuid"}]'::jsonb, 'aaaaaaaa-0000-0000-0000-000000000001')$sql$,
  'invalid_entity_uuid', 'A row without a usable UUID is refused');
select throws_ok(
  $sql$select public.append_entities('food_logs', '[]'::jsonb, 'bbbbbbbb-0000-0000-0000-000000000009')$sql$,
  'device_not_registered', 'An unknown device is refused');

-- ---------------------------------------------------------------------------
-- Pull
-- ---------------------------------------------------------------------------
select is(jsonb_array_length(
    public.fetch_entities('food_logs', now() + interval '1 hour') -> 'rows'), 0,
  'An incremental pull with a future cursor returns nothing');

-- ---------------------------------------------------------------------------
-- Isolation and privileges
-- ---------------------------------------------------------------------------
select is((select count(*) from public.sync_entities
    where user_id = '22222222-2222-2222-2222-222222222222')::int, 0,
  'The other user has no rows yet');

select ok((select c.relrowsecurity from pg_class c
    join pg_namespace n on n.oid = c.relnamespace
    where n.nspname = 'public' and c.relname = 'sync_entities'),
  'RLS is enabled on the row store');
select table_privs_are('public', 'sync_entities', 'anon', array[]::text[],
  'Anon has no privileges on the row store');
select function_privs_are('public', 'append_entities',
  array['text', 'jsonb', 'uuid', 'timestamp with time zone'], 'anon', array[]::text[],
  'Anon cannot append');

select * from finish();
rollback;
