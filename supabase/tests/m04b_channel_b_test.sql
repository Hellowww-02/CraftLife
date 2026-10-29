-- M04b — Channel B behaviour: row-level 3-way merge, tombstones, garbage collection.
--
-- The case that matters most is assertion 9: two devices offline at the same
-- time, editing DIFFERENT fields of the SAME row. Whole-row replacement loses
-- one of them. Per-field merge against the base revision keeps both.

begin;
create extension if not exists pgtap with schema extensions;
select plan(27);

insert into auth.users(id, email, email_confirmed_at) values
  ('11111111-1111-1111-1111-111111111111', 'chan_b@example.test', now()),
  ('22222222-2222-2222-2222-222222222222', 'chan_b2@example.test', now());

update public.profiles set username = 'chan_b', display_name = 'Channel B'
  where id = '11111111-1111-1111-1111-111111111111';
update public.profiles set username = 'chan_b2', display_name = 'Channel B2'
  where id = '22222222-2222-2222-2222-222222222222';

set local request.jwt.claim.sub = '11111111-1111-1111-1111-111111111111';
set local role authenticated;

select public.register_cloud_device(
  'bbbbbbbb-0000-0000-0000-000000000001', 'Device A', 'desktop', '1.7.4');
select public.register_cloud_device(
  'bbbbbbbb-0000-0000-0000-000000000002', 'Device B', 'android', '2.0.0');

-- ---------------------------------------------------------------------------
-- Schema and allowlist
-- ---------------------------------------------------------------------------
select has_table('public', 'sync_entity_revisions', 'Superseded values are archived');
select has_table('public', 'sync_tombstones', 'Deletions are recorded server-side');
select throws_ok(
  $sql$select public.assert_mutable_entity_table('food_logs')$sql$,
  'append_only_table_use_append_entities',
  'An append-only table is refused by Channel B');
select throws_ok(
  $sql$select public.assert_mutable_entity_table('habits; DROP TABLE profiles')$sql$,
  'unsupported_table', 'A table label that is not a safe identifier is refused');

-- ---------------------------------------------------------------------------
-- First write
-- ---------------------------------------------------------------------------
select is(
  (public.upsert_entities('habits',
    '[{"uuid":"cccccccc-0000-0000-0000-000000000001","base_rev":0,
       "updated_at":"2026-10-06T10:00:00Z",
       "payload":{"name":"Meditasi","notes":"","streak":0}}]'::jsonb,
    'bbbbbbbb-0000-0000-0000-000000000001') ->> 'inserted')::int,
  1, 'First push inserts the entity');

-- ---------------------------------------------------------------------------
-- The core case: two devices edit DIFFERENT fields of the SAME row
-- ---------------------------------------------------------------------------
-- Device A edits the name. It started from rev 1.
select is(
  (public.upsert_entities('habits',
    '[{"uuid":"cccccccc-0000-0000-0000-000000000001","base_rev":1,
       "updated_at":"2026-10-06T11:00:00Z",
       "payload":{"name":"Meditasi Pagi","notes":"","streak":0}}]'::jsonb,
    'bbbbbbbb-0000-0000-0000-000000000001') ->> 'updated')::int,
  1, 'Device A edits the name');

-- Device B was offline from rev 1 and edits the notes only.
select is(
  (public.upsert_entities('habits',
    '[{"uuid":"cccccccc-0000-0000-0000-000000000001","base_rev":1,
       "updated_at":"2026-10-06T11:30:00Z",
       "payload":{"name":"Meditasi","notes":"Catatan dari perangkat B","streak":0}}]'::jsonb,
    'bbbbbbbb-0000-0000-0000-000000000002') ->> 'updated')::int,
  1, 'Device B edits the notes');

select is(
  (select payload ->> 'name' from public.sync_entities
    where entity_uuid = 'cccccccc-0000-0000-0000-000000000001'
      and user_id = '11111111-1111-1111-1111-111111111111'),
  'Meditasi Pagi', 'Device A''s name edit survives');

select is(
  (select payload ->> 'notes' from public.sync_entities
    where entity_uuid = 'cccccccc-0000-0000-0000-000000000001'
      and user_id = '11111111-1111-1111-1111-111111111111'),
  'Catatan dari perangkat B', 'Device B''s notes edit survives too');

select is(
  (select rev::int from public.sync_entities
    where entity_uuid = 'cccccccc-0000-0000-0000-000000000001'
      and user_id = '11111111-1111-1111-1111-111111111111'),
  3, 'Each accepted write bumps rev');

-- ---------------------------------------------------------------------------
-- A genuine same-field conflict: newer wins, the loser is archived
-- ---------------------------------------------------------------------------
select is(
  (public.upsert_entities('habits',
    '[{"uuid":"cccccccc-0000-0000-0000-000000000001","base_rev":3,
       "updated_at":"2026-10-06T12:00:00Z",
       "payload":{"name":"Nama terbaru","notes":"Catatan dari perangkat B","streak":5}}]'::jsonb,
    'bbbbbbbb-0000-0000-0000-000000000001') ->> 'field_conflicts')::int,
  0, 'No conflict when the client started from the current revision');

-- A stale device now pushes an older edit to the same field.
-- This client really did change `name` relative to its base, while the server
-- changed it too. That is a genuine same-field conflict and must be reported --
-- but because its timestamp is older, it must not win. `notes` and `streak` are
-- untouched relative to the base, so they must not be counted or clobbered.
select is(
  (public.upsert_entities('habits',
    '[{"uuid":"cccccccc-0000-0000-0000-000000000001","base_rev":1,
       "updated_at":"2026-10-06T09:00:00Z",
       "payload":{"name":"Nama basi","notes":"","streak":0}}]'::jsonb,
    'bbbbbbbb-0000-0000-0000-000000000002') ->> 'field_conflicts')::int,
  1, 'A stale edit to a field the server also changed is reported as a conflict');

select is(
  (select payload ->> 'name' from public.sync_entities
    where entity_uuid = 'cccccccc-0000-0000-0000-000000000001'
      and user_id = '11111111-1111-1111-1111-111111111111'),
  'Nama terbaru', 'The newer value wins a real conflict');

select ok(
  (select count(*) from public.sync_entity_revisions
    where user_id = '11111111-1111-1111-1111-111111111111'
      and entity_uuid = 'cccccccc-0000-0000-0000-000000000001') > 0,
  'Superseded versions are archived, not discarded (K11)');

select is(
  jsonb_array_length(
    public.fetch_entity_revisions('habits', 'cccccccc-0000-0000-0000-000000000001') -> 'rows') > 0,
  true, 'The losing side is recoverable through the RPC');

-- ---------------------------------------------------------------------------
-- Tombstones
-- ---------------------------------------------------------------------------
select is(
  (public.upsert_entities('todos',
    '[{"uuid":"cccccccc-0000-0000-0000-000000000002","base_rev":0,
       "updated_at":"2026-10-06T10:00:00Z","deleted_at":"2026-10-06T14:00:00Z",
       "payload":{"title":"Sudah dihapus"}}]'::jsonb,
    'bbbbbbbb-0000-0000-0000-000000000001') ->> 'deleted')::int,
  1, 'A deleted row records a tombstone');

select is(
  (select deleted_at is not null from public.sync_entities
    where entity_uuid = 'cccccccc-0000-0000-0000-000000000002'
      and user_id = '11111111-1111-1111-1111-111111111111'),
  true, 'The entity itself carries the tombstone');

select is(
  jsonb_array_length(public.fetch_tombstones('todos') -> 'rows'), 1,
  'The tombstone is pullable by another device');

select is(
  (public.push_tombstones('todos',
    '[{"uuid":"cccccccc-0000-0000-0000-000000000003","deleted_at":"2026-10-06T15:00:00Z"}]'::jsonb,
    'bbbbbbbb-0000-0000-0000-000000000002') ->> 'recorded')::int,
  1, 'A device can push a bare tombstone');

-- ---------------------------------------------------------------------------
-- Garbage collection keeps recent deletions and drops old ones
-- ---------------------------------------------------------------------------
-- Seeded through the RPC, not a direct INSERT: writes are RPC-only by design.
select public.push_tombstones('todos',
  jsonb_build_array(jsonb_build_object(
    'uuid', 'cccccccc-0000-0000-0000-000000000099',
    'deleted_at', to_char(now() - interval '400 days', 'YYYY-MM-DD"T"HH24:MI:SS"Z"'))),
  'bbbbbbbb-0000-0000-0000-000000000001');

select is(public.gc_sync_tombstones(30), 1,
  'GC removes a tombstone older than the retention window');

select is(
  (select count(*)::int from public.sync_tombstones
    where user_id = '11111111-1111-1111-1111-111111111111' and table_name = 'todos'),
  2, 'GC leaves recent tombstones alone');

-- ---------------------------------------------------------------------------
-- Replaying the same batch twice creates no duplicates
-- ---------------------------------------------------------------------------
-- M04 acceptance criterion: "Replay outbox 2x -> tidak ada duplikasi". A device
-- that never received the acknowledgement will resend the identical batch, so
-- the second send must be a no-op rather than a second row or a second revision.
select is(
  (public.upsert_entities('habits',
    '[{"uuid":"cccccccc-0000-0000-0000-0000000000aa","base_rev":0,
       "updated_at":"2026-10-07T10:00:00Z",
       "payload":{"name":"Jalan Pagi","notes":"","streak":0}}]'::jsonb,
    'bbbbbbbb-0000-0000-0000-000000000001') ->> 'inserted')::int,
  1, 'Replay fixture: first push inserts');

select is(
  (public.upsert_entities('habits',
    '[{"uuid":"cccccccc-0000-0000-0000-0000000000aa","base_rev":0,
       "updated_at":"2026-10-07T10:00:00Z",
       "payload":{"name":"Jalan Pagi","notes":"","streak":0}}]'::jsonb,
    'bbbbbbbb-0000-0000-0000-000000000001') ->> 'inserted')::int,
  0, 'Replaying the identical batch inserts nothing');

select is(
  (public.upsert_entities('habits',
    '[{"uuid":"cccccccc-0000-0000-0000-0000000000aa","base_rev":0,
       "updated_at":"2026-10-07T10:00:00Z",
       "payload":{"name":"Jalan Pagi","notes":"","streak":0}}]'::jsonb,
    'bbbbbbbb-0000-0000-0000-000000000001') ->> 'unchanged')::int,
  1, 'A replay is reported as unchanged, not as an update');

select is(
  (select count(*)::int from public.sync_entities
    where user_id = '11111111-1111-1111-1111-111111111111'
      and table_name = 'habits'
      and entity_uuid = 'cccccccc-0000-0000-0000-0000000000aa'),
  1, 'Replay leaves exactly one entity row');

select is(
  (select count(*)::int from public.sync_entity_revisions
    where user_id = '11111111-1111-1111-1111-111111111111'
      and table_name = 'habits'
      and entity_uuid = 'cccccccc-0000-0000-0000-0000000000aa'),
  0, 'Replay archives no superseded revision');

-- ---------------------------------------------------------------------------
-- Isolation and privileges
-- ---------------------------------------------------------------------------
select is((select count(*)::int from public.sync_entities
    where user_id = '22222222-2222-2222-2222-222222222222'), 0,
  'The other user sees none of this');

select * from finish();
rollback;
