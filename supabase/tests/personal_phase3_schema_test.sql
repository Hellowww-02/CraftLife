begin;
create extension if not exists pgtap with schema extensions;
select plan(21);

select has_table('public','cloud_devices','Phase 3 device registry exists');
select has_table('public','personal_snapshots','Phase 3 personal snapshots exist');
select has_table('public','personal_snapshot_versions','Phase 3 snapshot history exists');
select has_column('public','personal_snapshots','revision','Snapshot has optimistic revision');
select has_column('public','personal_snapshots','content_hash','Snapshot has content hash');
select has_column('public','personal_snapshots','source_device_id','Snapshot records source device');
select col_is_pk('public','personal_snapshots',array['user_id','document_key'],'Snapshot key is owner plus document');
select has_function('public','register_cloud_device',array['uuid','text','text','text'],'Device registration RPC exists');
select has_function('public','revoke_cloud_device',array['uuid'],'Device revoke RPC exists');
select has_function('public','upsert_personal_snapshot',array['text','bigint','text','jsonb','uuid','timestamp with time zone'],'Snapshot upsert RPC exists');
select has_function('public','get_personal_snapshot_version',array['text','bigint'],'Snapshot history RPC exists');
select has_function('public','run_cloud_maintenance',array[]::text[],'Maintenance RPC exists');
select ok((select c.relrowsecurity from pg_class c join pg_namespace n on n.oid=c.relnamespace where n.nspname='public' and c.relname='cloud_devices'),'Device RLS enabled');
select ok((select c.relrowsecurity from pg_class c join pg_namespace n on n.oid=c.relnamespace where n.nspname='public' and c.relname='personal_snapshots'),'Snapshot RLS enabled');
select ok((select c.relrowsecurity from pg_class c join pg_namespace n on n.oid=c.relnamespace where n.nspname='public' and c.relname='personal_snapshot_versions'),'History RLS enabled');
select table_privs_are('public','personal_snapshots','anon',array[]::text[],'Anon has no snapshot table privileges');
select table_privs_are('public','personal_snapshot_versions','anon',array[]::text[],'Anon has no history table privileges');
select table_privs_are('public','cloud_devices','anon',array[]::text[],'Anon has no device table privileges');
select function_privs_are('public','upsert_personal_snapshot',array['text','bigint','text','jsonb','uuid','timestamp with time zone'],'anon',array[]::text[],'Anon cannot upsert snapshots');
select function_privs_are('public','register_cloud_device',array['uuid','text','text','text'],'anon',array[]::text[],'Anon cannot register devices');
select function_privs_are('public','run_cloud_maintenance',array[]::text[],'anon',array[]::text[],'Anon cannot run maintenance');

select * from finish();
rollback;
