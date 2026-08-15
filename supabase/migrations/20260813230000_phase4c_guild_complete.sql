-- CraftLife Phase 4C.1-4C.4: complete online Guild lifecycle, roles,
-- upgraded chat, server-catalog bosses, contribution totals and one-time rewards.

alter table public.online_guilds add column if not exists disbanded_at timestamptz;
alter table public.online_guild_members add column if not exists last_read_at timestamptz;
alter table public.online_guild_members add column if not exists contribution_points bigint not null default 0;
alter table public.online_guild_messages add column if not exists reply_to_id uuid references public.online_guild_messages(id) on delete set null;
alter table public.online_guild_messages add column if not exists edited_at timestamptz;
alter table public.online_guild_battles add column if not exists end_at timestamptz;
create unique index if not exists online_guild_one_leader on public.online_guild_members(guild_id) where role='leader';
update public.online_guild_battles set end_at=started_at+interval '7 days' where end_at is null;

create table if not exists public.online_guild_bans(
  guild_id uuid not null references public.online_guilds(id) on delete cascade,
  user_id uuid not null references public.profiles(id) on delete cascade,
  banned_by uuid not null references public.profiles(id) on delete restrict,
  reason text not null default '' check(char_length(reason)<=500),
  created_at timestamptz not null default now(),
  primary key(guild_id,user_id)
);

create table if not exists public.online_guild_message_reactions(
  message_id uuid not null references public.online_guild_messages(id) on delete cascade,
  user_id uuid not null references public.profiles(id) on delete cascade,
  reaction text not null check(char_length(reaction) between 1 and 16),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  primary key(message_id,user_id)
);
create trigger guild_message_reactions_updated before update on public.online_guild_message_reactions
for each row execute function public.set_updated_at();

create table if not exists public.online_guild_boss_rewards(
  battle_id uuid not null references public.online_guild_battles(id) on delete cascade,
  user_id uuid not null references public.profiles(id) on delete cascade,
  damage bigint not null default 0,
  xp_reward integer not null check(xp_reward between 0 and 10000),
  gold_reward integer not null check(gold_reward between 0 and 10000),
  created_at timestamptz not null default now(),
  claimed_at timestamptz,
  primary key(battle_id,user_id)
);

create or replace function public.is_online_guild_owner(p_guild_id uuid)
returns boolean language sql stable security definer set search_path=public as $$
 select exists(select 1 from public.online_guild_members where guild_id=p_guild_id and user_id=auth.uid() and role='leader')
$$;
create or replace function public.can_manage_online_guild(p_guild_id uuid)
returns boolean language sql stable security definer set search_path=public as $$
 select exists(select 1 from public.online_guild_members where guild_id=p_guild_id and user_id=auth.uid() and role in('leader','officer'))
$$;

-- Replace the original join RPC so old clients cannot bypass bans/disband state.
create or replace function public.request_online_guild_join(p_guild_id uuid)
returns public.online_guild_requests language plpgsql security definer set search_path=public as $$
declare result public.online_guild_requests;
begin
  if exists(select 1 from public.online_guild_members where user_id=auth.uid()) then raise exception 'already_in_guild'; end if;
  if not exists(select 1 from public.online_guilds where id=p_guild_id and disbanded_at is null) then raise exception 'guild_unavailable'; end if;
  if exists(select 1 from public.online_guild_bans where guild_id=p_guild_id and user_id=auth.uid()) then raise exception 'guild_banned'; end if;
  insert into public.online_guild_requests(guild_id,user_id,status) values(p_guild_id,auth.uid(),'pending')
  on conflict(guild_id,user_id) do update set status='pending',created_at=now(),responded_at=null returning * into result;
  return result;
end; $$;

create or replace function public.respond_online_guild_join(p_request_id uuid,p_accept boolean)
returns public.online_guild_requests language plpgsql security definer set search_path=public as $$
declare result public.online_guild_requests;
begin
 select r.* into result from public.online_guild_requests r where r.id=p_request_id and r.status='pending' for update;
 if result.id is null or not public.can_manage_online_guild(result.guild_id) then raise exception 'forbidden'; end if;
 if p_accept then
   if not exists(select 1 from public.online_guilds where id=result.guild_id and disbanded_at is null) then raise exception 'guild_unavailable'; end if;
   if exists(select 1 from public.online_guild_bans where guild_id=result.guild_id and user_id=result.user_id) then raise exception 'guild_banned'; end if;
   if exists(select 1 from public.online_guild_members where user_id=result.user_id) then raise exception 'already_in_guild'; end if;
   insert into public.online_guild_members(guild_id,user_id) values(result.guild_id,result.user_id);
 end if;
 update public.online_guild_requests set status=case when p_accept then 'accepted' else 'rejected' end,responded_at=now()
 where id=result.id returning * into result;return result;
end; $$;

create or replace function public.cancel_online_guild_join(p_request_id uuid)
returns boolean language plpgsql security definer set search_path=public as $$
begin
 update public.online_guild_requests set status='cancelled',responded_at=now()
 where id=p_request_id and user_id=auth.uid() and status='pending';return found;
end; $$;

create or replace function public.leave_online_guild(p_guild_id uuid)
returns jsonb language plpgsql security definer set search_path=public as $$
declare mine public.online_guild_members;member_count integer;
begin
 select * into mine from public.online_guild_members where guild_id=p_guild_id and user_id=auth.uid() for update;
 if mine.user_id is null then raise exception 'not_a_member'; end if;
 select count(*) into member_count from public.online_guild_members where guild_id=p_guild_id;
 if mine.role='leader' and member_count>1 then raise exception 'transfer_leader_required'; end if;
 if mine.role='leader' then
   update public.online_guilds set disbanded_at=now() where id=p_guild_id;
   update public.online_guild_battles set status='cancelled',ended_at=now() where guild_id=p_guild_id and status='active';
   update public.online_guild_requests set status='cancelled',responded_at=now() where guild_id=p_guild_id and status='pending';
   delete from public.online_guild_members where guild_id=p_guild_id;
 else delete from public.online_guild_members where guild_id=p_guild_id and user_id=auth.uid();
 end if;
 return jsonb_build_object('ok',true,'disbanded',mine.role='leader');
end; $$;

create or replace function public.kick_online_guild_member(p_guild_id uuid,p_user_id uuid)
returns boolean language plpgsql security definer set search_path=public as $$
declare actor_role text;target_role text;
begin
 select role into actor_role from public.online_guild_members where guild_id=p_guild_id and user_id=auth.uid();
 select role into target_role from public.online_guild_members where guild_id=p_guild_id and user_id=p_user_id;
 if actor_role not in('leader','officer') or target_role is null or p_user_id=auth.uid() then raise exception 'forbidden'; end if;
 if actor_role='officer' and target_role<>'member' then raise exception 'forbidden'; end if;
 delete from public.online_guild_members where guild_id=p_guild_id and user_id=p_user_id;
 return found;
end; $$;

create or replace function public.ban_online_guild_member(p_guild_id uuid,p_user_id uuid,p_reason text default '')
returns boolean language plpgsql security definer set search_path=public as $$
declare actor_role text;target_role text;
begin
 select role into actor_role from public.online_guild_members where guild_id=p_guild_id and user_id=auth.uid();
 select role into target_role from public.online_guild_members where guild_id=p_guild_id and user_id=p_user_id;
 if actor_role not in('leader','officer') or p_user_id=auth.uid() then raise exception 'forbidden'; end if;
 if target_role='leader' or (actor_role='officer' and target_role='officer') then raise exception 'forbidden'; end if;
 insert into public.online_guild_bans(guild_id,user_id,banned_by,reason)
 values(p_guild_id,p_user_id,auth.uid(),left(coalesce(p_reason,''),500))
 on conflict(guild_id,user_id) do update set banned_by=auth.uid(),reason=excluded.reason,created_at=now();
 delete from public.online_guild_members where guild_id=p_guild_id and user_id=p_user_id;
 update public.online_guild_requests set status='rejected',responded_at=now() where guild_id=p_guild_id and user_id=p_user_id and status='pending';
 return true;
end; $$;

create or replace function public.unban_online_guild_member(p_guild_id uuid,p_user_id uuid)
returns boolean language plpgsql security definer set search_path=public as $$
begin
 if not public.can_manage_online_guild(p_guild_id) then raise exception 'forbidden'; end if;
 delete from public.online_guild_bans where guild_id=p_guild_id and user_id=p_user_id;return found;
end; $$;

create or replace function public.set_online_guild_role(p_guild_id uuid,p_user_id uuid,p_role text)
returns public.online_guild_members language plpgsql security definer set search_path=public as $$
declare result public.online_guild_members;
begin
 if not public.is_online_guild_owner(p_guild_id) or p_role not in('officer','member') or p_user_id=auth.uid() then raise exception 'forbidden'; end if;
 update public.online_guild_members set role=p_role where guild_id=p_guild_id and user_id=p_user_id and role<>'leader' returning * into result;
 if result.user_id is null then raise exception 'member_not_found'; end if;return result;
end; $$;

create or replace function public.transfer_online_guild_leader(p_guild_id uuid,p_user_id uuid)
returns jsonb language plpgsql security definer set search_path=public as $$
begin
 perform 1 from public.online_guilds where id=p_guild_id and leader_id=auth.uid() for update;
 if not found or p_user_id=auth.uid() then raise exception 'forbidden'; end if;
 if not exists(select 1 from public.online_guild_members where guild_id=p_guild_id and user_id=p_user_id) then raise exception 'member_not_found'; end if;
 update public.online_guild_members set role='officer' where guild_id=p_guild_id and user_id=auth.uid();
 update public.online_guild_members set role='leader' where guild_id=p_guild_id and user_id=p_user_id;
 update public.online_guilds set leader_id=p_user_id where id=p_guild_id;
 return jsonb_build_object('ok',true,'leader_id',p_user_id);
end; $$;

create or replace function public.disband_online_guild(p_guild_id uuid)
returns boolean language plpgsql security definer set search_path=public as $$
begin
 if not public.is_online_guild_owner(p_guild_id) then raise exception 'forbidden'; end if;
 update public.online_guilds set disbanded_at=now() where id=p_guild_id and disbanded_at is null;
 update public.online_guild_battles set status='cancelled',ended_at=now() where guild_id=p_guild_id and status='active';
 update public.online_guild_requests set status='cancelled',responded_at=now() where guild_id=p_guild_id and status='pending';
 delete from public.online_guild_members where guild_id=p_guild_id;return true;
end; $$;

create or replace function public.update_online_guild_description(p_guild_id uuid,p_description text)
returns public.online_guilds language plpgsql security definer set search_path=public as $$
declare result public.online_guilds;
begin
 if not public.can_manage_online_guild(p_guild_id) then raise exception 'forbidden'; end if;
 update public.online_guilds set description=left(coalesce(p_description,''),500) where id=p_guild_id and disbanded_at is null returning * into result;
 return result;
end; $$;

-- Guild chat core.
create or replace function public.send_online_guild_message_v2(p_guild_id uuid,p_body text,p_client_message_id uuid,p_reply_to_id uuid default null)
returns public.online_guild_messages language plpgsql security definer set search_path=public as $$
declare result public.online_guild_messages;
begin
 if not public.is_online_guild_member(p_guild_id) or char_length(trim(coalesce(p_body,'')))<1 then raise exception 'forbidden'; end if;
 if p_reply_to_id is not null and not exists(select 1 from public.online_guild_messages where id=p_reply_to_id and guild_id=p_guild_id) then raise exception 'invalid_reply_target'; end if;
 insert into public.online_guild_messages(guild_id,sender_id,body,client_message_id,reply_to_id)
 values(p_guild_id,auth.uid(),left(trim(p_body),4000),p_client_message_id,p_reply_to_id)
 on conflict(sender_id,client_message_id) do update set body=excluded.body returning * into result;return result;
end; $$;

create or replace function public.edit_online_guild_message(p_message_id uuid,p_body text)
returns public.online_guild_messages language plpgsql security definer set search_path=public as $$
declare result public.online_guild_messages;
begin
 update public.online_guild_messages set body=left(trim(p_body),4000),edited_at=now()
 where id=p_message_id and sender_id=auth.uid() and deleted_at is null and char_length(trim(coalesce(p_body,'')))>0 returning * into result;
 if result.id is null then raise exception 'forbidden'; end if;return result;
end; $$;

create or replace function public.delete_online_guild_message(p_message_id uuid)
returns public.online_guild_messages language plpgsql security definer set search_path=public as $$
declare result public.online_guild_messages;g uuid;
begin
 select guild_id into g from public.online_guild_messages where id=p_message_id;
 if g is null or not public.is_online_guild_member(g) then raise exception 'forbidden'; end if;
 update public.online_guild_messages set body='',deleted_at=coalesce(deleted_at,now()),edited_at=null
 where id=p_message_id and (sender_id=auth.uid() or public.can_manage_online_guild(g)) returning * into result;
 if result.id is null then raise exception 'forbidden'; end if;
 delete from public.online_guild_message_reactions where message_id=p_message_id;return result;
end; $$;

create or replace function public.set_online_guild_message_reaction(p_message_id uuid,p_reaction text default null)
returns jsonb language plpgsql security definer set search_path=public as $$
declare g uuid;result public.online_guild_message_reactions;
begin
 select guild_id into g from public.online_guild_messages where id=p_message_id and deleted_at is null;
 if g is null or not public.is_online_guild_member(g) then raise exception 'forbidden'; end if;
 if p_reaction is null or trim(p_reaction)='' then
   delete from public.online_guild_message_reactions where message_id=p_message_id and user_id=auth.uid();return jsonb_build_object('active',false);
 end if;
 insert into public.online_guild_message_reactions(message_id,user_id,reaction) values(p_message_id,auth.uid(),left(p_reaction,16))
 on conflict(message_id,user_id) do update set reaction=excluded.reaction,updated_at=now() returning * into result;
 return jsonb_build_object('active',true,'row',to_jsonb(result));
end; $$;

create or replace function public.mark_online_guild_read(p_guild_id uuid)
returns boolean language plpgsql security definer set search_path=public as $$
begin
 update public.online_guild_members set last_read_at=now() where guild_id=p_guild_id and user_id=auth.uid();return found;
end; $$;

create or replace function public.get_my_online_guild_summary()
returns jsonb language sql stable security definer set search_path=public as $$
 select coalesce(jsonb_build_object('guild_id',m.guild_id,'role',m.role,'contribution_points',m.contribution_points,
   'unread_count',(select count(*) from public.online_guild_messages msg where msg.guild_id=m.guild_id and msg.sender_id<>auth.uid()
      and msg.deleted_at is null and msg.created_at>coalesce(m.last_read_at,'epoch'::timestamptz))), '{}'::jsonb)
 from public.online_guild_members m where m.user_id=auth.uid()
$$;

-- Server catalog boss start: desktop never chooses HP or duration.
create or replace function public.start_online_guild_boss_v2(p_guild_id uuid,p_boss_key text)
returns public.online_guild_battles language plpgsql security definer set search_path=public as $$
declare result public.online_guild_battles;boss_name text;hp bigint;duration interval;
begin
 if not public.can_manage_online_guild(p_guild_id) then raise exception 'forbidden'; end if;
 case p_boss_key
   when 'cloud_dragon' then boss_name='Cloud Ender Dragon';hp=5000;duration=interval '7 days';
   when 'storm_titan' then boss_name='Storm Titan';hp=12000;duration=interval '7 days';
   when 'void_guardian' then boss_name='Void Guardian';hp=25000;duration=interval '10 days';
   else raise exception 'unknown_boss';
 end case;
 insert into public.online_guild_battles(guild_id,boss_key,boss_name,max_hp,current_hp,end_at)
 values(p_guild_id,p_boss_key,boss_name,hp,hp,now()+duration) returning * into result;return result;
end; $$;

create or replace function public.create_online_guild_boss_rewards()
returns trigger language plpgsql security definer set search_path=public as $$
begin
 if old.status='active' and new.status='defeated' then
   insert into public.online_guild_boss_rewards(battle_id,user_id,damage,xp_reward,gold_reward)
   select new.id,a.user_id,sum(a.damage)::bigint,
     least(10000,100+(sum(a.damage)/10)::integer),least(10000,50+(sum(a.damage)/25)::integer)
   from public.online_guild_boss_actions a where a.battle_id=new.id group by a.user_id
   on conflict do nothing;
 end if;return new;
end; $$;
drop trigger if exists online_guild_boss_reward_trigger on public.online_guild_battles;
create trigger online_guild_boss_reward_trigger after update of status on public.online_guild_battles
for each row execute function public.create_online_guild_boss_rewards();

create or replace function public.claim_online_guild_boss_reward(p_battle_id uuid)
returns public.online_guild_boss_rewards language plpgsql security definer set search_path=public as $$
declare result public.online_guild_boss_rewards;
begin
 update public.online_guild_boss_rewards set claimed_at=now()
 where battle_id=p_battle_id and user_id=auth.uid() and claimed_at is null returning * into result;
 if result.user_id is null then raise exception 'nothing_to_claim'; end if;return result;
end; $$;

-- Add contribution totals while retaining event-idempotent damage.
create or replace function public.apply_productivity_to_guild()
returns trigger language plpgsql security definer set search_path=public as $$
declare g uuid;b public.online_guild_battles;damage integer;
begin
 select guild_id into g from public.online_guild_members where user_id=new.user_id;
 if g is null then return new; end if;
 insert into public.online_guild_contributions(guild_id,event_id,user_id,points) values(g,new.id,new.user_id,new.points) on conflict do nothing;
 if found then
   update public.online_guild_members set contribution_points=contribution_points+new.points where guild_id=g and user_id=new.user_id;
   update public.online_guilds set exp=exp+new.points,level=greatest(level,1+((exp+new.points)/1000)::integer) where id=g;
   select * into b from public.online_guild_battles where guild_id=g and status='active' and end_at>now() for update;
   if b.id is not null then
     damage=greatest(1,new.points);
     insert into public.online_guild_boss_actions(battle_id,event_id,user_id,damage) values(b.id,new.id,new.user_id,damage) on conflict do nothing;
     if found then update public.online_guild_battles set current_hp=greatest(0,current_hp-damage),
       status=case when current_hp-damage<=0 then 'defeated' else status end,
       ended_at=case when current_hp-damage<=0 then now() else ended_at end where id=b.id;end if;
   end if;
 end if;return new;
end; $$;

create or replace function public.run_online_guild_maintenance()
returns jsonb language plpgsql security definer set search_path=public as $$
declare expired_count integer;
begin
 update public.online_guild_battles set status='expired',ended_at=now() where status='active' and end_at<=now();
 get diagnostics expired_count=row_count;return jsonb_build_object('ok',true,'guild_boss_expired',expired_count);
end; $$;

alter table public.online_guild_bans enable row level security;
alter table public.online_guild_message_reactions enable row level security;
alter table public.online_guild_boss_rewards enable row level security;
create policy guild_bans_manager_read on public.online_guild_bans for select to authenticated using(public.can_manage_online_guild(guild_id));
create policy guild_message_reactions_member_read on public.online_guild_message_reactions for select to authenticated
using(exists(select 1 from public.online_guild_messages m where m.id=message_id and public.is_online_guild_member(m.guild_id)));
create policy guild_boss_rewards_owner_read on public.online_guild_boss_rewards for select to authenticated using(user_id=auth.uid());
revoke all on public.online_guild_bans,public.online_guild_message_reactions,public.online_guild_boss_rewards from anon;
revoke insert,update,delete on public.online_guild_bans,public.online_guild_message_reactions,public.online_guild_boss_rewards from authenticated;
grant select on public.online_guild_bans,public.online_guild_message_reactions,public.online_guild_boss_rewards to authenticated;

revoke execute on function public.cancel_online_guild_join(uuid) from public,anon;
revoke execute on function public.leave_online_guild(uuid) from public,anon;
revoke execute on function public.kick_online_guild_member(uuid,uuid) from public,anon;
revoke execute on function public.ban_online_guild_member(uuid,uuid,text) from public,anon;
revoke execute on function public.unban_online_guild_member(uuid,uuid) from public,anon;
revoke execute on function public.set_online_guild_role(uuid,uuid,text) from public,anon;
revoke execute on function public.transfer_online_guild_leader(uuid,uuid) from public,anon;
revoke execute on function public.disband_online_guild(uuid) from public,anon;
revoke execute on function public.update_online_guild_description(uuid,text) from public,anon;
revoke execute on function public.send_online_guild_message_v2(uuid,text,uuid,uuid) from public,anon;
revoke execute on function public.edit_online_guild_message(uuid,text) from public,anon;
revoke execute on function public.delete_online_guild_message(uuid) from public,anon;
revoke execute on function public.set_online_guild_message_reaction(uuid,text) from public,anon;
revoke execute on function public.mark_online_guild_read(uuid) from public,anon;
revoke execute on function public.get_my_online_guild_summary() from public,anon;
-- Disable the Phase 2 client-supplied-HP RPC; only the server catalog v2 may start bosses.
revoke execute on function public.start_online_guild_boss(uuid,text,text,bigint) from authenticated;
revoke execute on function public.start_online_guild_boss_v2(uuid,text) from public,anon;
revoke execute on function public.claim_online_guild_boss_reward(uuid) from public,anon;
revoke execute on function public.run_online_guild_maintenance() from public,anon;
grant execute on function public.cancel_online_guild_join(uuid),public.leave_online_guild(uuid),
 public.kick_online_guild_member(uuid,uuid),public.ban_online_guild_member(uuid,uuid,text),
 public.unban_online_guild_member(uuid,uuid),public.set_online_guild_role(uuid,uuid,text),
 public.transfer_online_guild_leader(uuid,uuid),public.disband_online_guild(uuid),
 public.update_online_guild_description(uuid,text),public.send_online_guild_message_v2(uuid,text,uuid,uuid),
 public.edit_online_guild_message(uuid,text),public.delete_online_guild_message(uuid),
 public.set_online_guild_message_reaction(uuid,text),public.mark_online_guild_read(uuid),
 public.get_my_online_guild_summary(),public.start_online_guild_boss_v2(uuid,text),
 public.claim_online_guild_boss_reward(uuid),public.run_online_guild_maintenance() to authenticated;

do $$ begin alter publication supabase_realtime add table public.online_guild_members; exception when duplicate_object then null; end $$;
do $$ begin alter publication supabase_realtime add table public.online_guild_requests; exception when duplicate_object then null; end $$;
do $$ begin alter publication supabase_realtime add table public.online_guild_message_reactions; exception when duplicate_object then null; end $$;
do $$ begin alter publication supabase_realtime add table public.online_guild_boss_rewards; exception when duplicate_object then null; end $$;
do $$ begin alter publication supabase_realtime add table public.online_guild_contributions; exception when duplicate_object then null; end $$;
notify pgrst,'reload schema';
