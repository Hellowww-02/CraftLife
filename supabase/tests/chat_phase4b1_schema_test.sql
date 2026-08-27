begin;
create extension if not exists pgtap with schema extensions;
select plan(20);

select has_column('public','messages','reply_to_id','messages support replies');
select has_column('public','messages','edited_at','messages expose edit timestamp');
select has_column('public','messages','deleted_at','messages expose soft-delete timestamp');
select has_table('public','message_reactions','message reactions exist');
select col_is_pk('public','message_reactions',array['message_id','user_id'],'one reaction per user/message');
select has_function('public','send_direct_message_v2',array['uuid','text','uuid','uuid'],'reply-aware send RPC exists');
select has_function('public','edit_direct_message',array['uuid','text'],'edit RPC exists');
select has_function('public','delete_direct_message',array['uuid'],'delete RPC exists');
select has_function('public','set_direct_message_reaction',array['uuid','text'],'reaction RPC exists');
select has_function('public','get_direct_conversation_summaries',array[]::text[],'unread summary RPC exists');
select ok((select c.relrowsecurity from pg_class c join pg_namespace n on n.oid=c.relnamespace where n.nspname='public' and c.relname='message_reactions'),'reaction RLS enabled');
select table_privs_are('public','message_reactions','anon',array[]::text[],'anon has no reaction privileges');
select function_privs_are('public','send_direct_message_v2',array['uuid','text','uuid','uuid'],'anon',array[]::text[],'anon cannot send v2 messages');
select function_privs_are('public','edit_direct_message',array['uuid','text'],'anon',array[]::text[],'anon cannot edit messages');
select function_privs_are('public','delete_direct_message',array['uuid'],'anon',array[]::text[],'anon cannot delete messages');
select function_privs_are('public','set_direct_message_reaction',array['uuid','text'],'anon',array[]::text[],'anon cannot react');
select function_privs_are('public','get_direct_conversation_summaries',array[]::text[],'anon',array[]::text[],'anon cannot list conversation summaries');
select col_is_fk('public','messages','reply_to_id','reply target is a foreign key');
select col_is_fk('public','message_reactions','message_id','reaction message is a foreign key');
select col_is_fk('public','message_reactions','user_id','reaction user is a foreign key');

select * from finish();
rollback;
