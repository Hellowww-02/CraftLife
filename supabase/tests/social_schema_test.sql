begin;
create extension if not exists pgtap with schema extensions;
select plan(20);

select has_table('public','profiles','profiles exists');
select has_table('public','friendships','friendships exists');
select has_table('public','couple_relationships','couple relationships exists');
select has_table('public','love_spaces','love spaces exists');
select has_table('public','love_space_members','love members exists');
select has_table('public','love_space_photos','love photos exists');
select has_table('public','account_deletion_requests','soft delete requests exist');
select has_function('public','send_friend_request',array['text'],'friend request RPC exists');
select has_function('public','respond_friend_request',array['uuid','boolean'],'friend response RPC exists');
select has_function('public','send_couple_request',array['uuid'],'couple request RPC exists');
select has_function('public','respond_couple_request',array['uuid','boolean'],'couple response RPC exists');
select has_function('public','cancel_couple_request',array['uuid'],'couple cancel RPC exists');
select has_function('public','end_couple_relationship',array['uuid'],'relationship end RPC exists');
select has_function('public','register_love_photo',array['uuid','uuid','text','text','text','integer','integer','bigint','text','date'],'quota checked gallery RPC exists');
select has_function('public','request_account_deletion',array[]::text[],'soft delete RPC exists');
select has_function('public','cancel_account_deletion',array[]::text[],'soft delete cancel RPC exists');
select col_is_pk('public','profiles','id','profiles id is primary key');
select col_is_unique('public','love_spaces','couple_relationship_id','one love space per couple');
select col_is_pk('public','love_space_members',array['love_space_id','user_id'],'membership composite key');
select results_eq(
  $$select count(*)::bigint from storage.buckets where id in ('profile-photos','love-space-photos') and public=false$$,
  array[2::bigint],
  'both storage buckets are private'
);

select * from finish();
rollback;
