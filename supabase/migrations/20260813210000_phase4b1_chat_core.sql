-- CraftLife Cloud Phase 4B.1: direct-chat core upgrades.
-- Adds reply, edit, sender soft-delete, reactions, unread summaries, pagination support.

alter table public.messages
  add column if not exists reply_to_id uuid references public.messages(id) on delete set null;
create index if not exists messages_reply_to on public.messages(reply_to_id) where reply_to_id is not null;

create table if not exists public.message_reactions (
  message_id uuid not null references public.messages(id) on delete cascade,
  user_id uuid not null references public.profiles(id) on delete cascade,
  reaction text not null check(char_length(reaction) between 1 and 16),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  primary key(message_id,user_id)
);
create index if not exists message_reactions_message on public.message_reactions(message_id,updated_at);
create trigger message_reactions_updated before update on public.message_reactions
for each row execute function public.set_updated_at();

create or replace function public.send_direct_message_v2(
  p_conversation_id uuid,p_body text,p_client_message_id uuid,p_reply_to_id uuid default null
)
returns public.messages language plpgsql security definer set search_path=public as $$
declare result public.messages;
begin
  if not public.current_profile_active() or not public.is_conversation_member(p_conversation_id) then
    raise exception 'forbidden';
  end if;
  if char_length(trim(coalesce(p_body,'')))<1 then raise exception 'message_empty'; end if;
  if p_reply_to_id is not null and not exists(
    select 1 from public.messages where id=p_reply_to_id and conversation_id=p_conversation_id
  ) then raise exception 'invalid_reply_target'; end if;

  insert into public.messages(conversation_id,sender_id,body,client_message_id,reply_to_id)
  values(p_conversation_id,auth.uid(),left(trim(p_body),4000),p_client_message_id,p_reply_to_id)
  on conflict(sender_id,client_message_id) do update set body=excluded.body
  returning * into result;
  update public.conversations set updated_at=now() where id=p_conversation_id;
  return result;
end; $$;

create or replace function public.edit_direct_message(p_message_id uuid,p_body text)
returns public.messages language plpgsql security definer set search_path=public as $$
declare result public.messages;
begin
  if char_length(trim(coalesce(p_body,'')))<1 then raise exception 'message_empty'; end if;
  update public.messages set body=left(trim(p_body),4000),edited_at=now()
  where id=p_message_id and sender_id=auth.uid() and deleted_at is null
  returning * into result;
  if result.id is null then raise exception 'message_edit_forbidden'; end if;
  update public.conversations set updated_at=now() where id=result.conversation_id;
  return result;
end; $$;

create or replace function public.delete_direct_message(p_message_id uuid)
returns public.messages language plpgsql security definer set search_path=public as $$
declare result public.messages;
begin
  update public.messages set body='',deleted_at=coalesce(deleted_at,now()),edited_at=null
  where id=p_message_id and sender_id=auth.uid()
  returning * into result;
  if result.id is null then raise exception 'message_delete_forbidden'; end if;
  delete from public.message_reactions where message_id=p_message_id;
  update public.conversations set updated_at=now() where id=result.conversation_id;
  return result;
end; $$;

create or replace function public.set_direct_message_reaction(
  p_message_id uuid,p_reaction text default null
)
returns jsonb language plpgsql security definer set search_path=public as $$
declare
  conversation_uuid uuid;
  result public.message_reactions;
begin
  select conversation_id into conversation_uuid from public.messages
  where id=p_message_id and deleted_at is null;
  if conversation_uuid is null or not public.is_conversation_member(conversation_uuid) then raise exception 'forbidden'; end if;

  if p_reaction is null or trim(p_reaction)='' then
    delete from public.message_reactions where message_id=p_message_id and user_id=auth.uid();
    return jsonb_build_object('active',false,'message_id',p_message_id);
  end if;
  if char_length(p_reaction)>16 then raise exception 'reaction_too_long'; end if;
  insert into public.message_reactions(message_id,user_id,reaction)
  values(p_message_id,auth.uid(),p_reaction)
  on conflict(message_id,user_id) do update set reaction=excluded.reaction,updated_at=now()
  returning * into result;
  return jsonb_build_object('active',true,'row',to_jsonb(result));
end; $$;

create or replace function public.get_direct_conversation_summaries()
returns table(
  conversation_id uuid,other_user_id uuid,other_username citext,other_display_name text,
  other_avatar_path text,conversation_updated_at timestamptz,last_read_at timestamptz,
  unread_count bigint,last_message_at timestamptz,last_message_preview text
)
language sql stable security definer set search_path=public as $$
  select c.id,other_member.user_id,p.username,p.display_name,p.avatar_path,c.updated_at,mine.last_read_at,
    (select count(*) from public.messages unread
      where unread.conversation_id=c.id and unread.sender_id<>auth.uid()
        and unread.deleted_at is null and unread.created_at>coalesce(mine.last_read_at,'epoch'::timestamptz))::bigint,
    latest.created_at,
    case when latest.deleted_at is not null then '[deleted]'
         else left(coalesce(latest.body,''),160) end
  from public.conversation_members mine
  join public.conversations c on c.id=mine.conversation_id and c.kind='direct'
  join public.conversation_members other_member on other_member.conversation_id=c.id and other_member.user_id<>auth.uid()
  join public.profiles p on p.id=other_member.user_id
  left join lateral(
    select msg.body,msg.created_at,msg.deleted_at from public.messages msg
    where msg.conversation_id=c.id order by msg.created_at desc,msg.id desc limit 1
  ) latest on true
  where mine.user_id=auth.uid()
  order by coalesce(latest.created_at,c.created_at) desc
$$;

alter table public.message_reactions enable row level security;
create policy message_reactions_member_read on public.message_reactions for select to authenticated
using(exists(select 1 from public.messages m where m.id=message_id and public.is_conversation_member(m.conversation_id)));

revoke all on public.message_reactions from anon;
revoke insert,update,delete on public.message_reactions from authenticated;
grant select on public.message_reactions to authenticated;

revoke execute on function public.send_direct_message_v2(uuid,text,uuid,uuid) from public,anon;
revoke execute on function public.edit_direct_message(uuid,text) from public,anon;
revoke execute on function public.delete_direct_message(uuid) from public,anon;
revoke execute on function public.set_direct_message_reaction(uuid,text) from public,anon;
revoke execute on function public.get_direct_conversation_summaries() from public,anon;
grant execute on function public.send_direct_message_v2(uuid,text,uuid,uuid) to authenticated;
grant execute on function public.edit_direct_message(uuid,text) to authenticated;
grant execute on function public.delete_direct_message(uuid) to authenticated;
grant execute on function public.set_direct_message_reaction(uuid,text) to authenticated;
grant execute on function public.get_direct_conversation_summaries() to authenticated;

do $$ begin alter publication supabase_realtime add table public.message_reactions; exception when duplicate_object then null; end $$;

notify pgrst,'reload schema';
