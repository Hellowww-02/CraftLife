-- CraftLife Cloud Phase 2A-2E: Chat, Presence, Notifications, Productivity, PvP, Guild, Leaderboard

-- 2A: Direct conversations, messages, reads, presence, notifications
create table if not exists public.conversations (
  id uuid primary key default gen_random_uuid(),
  kind text not null default 'direct' check (kind in ('direct','guild')),
  direct_key text unique,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);
create trigger conversations_updated_at before update on public.conversations
for each row execute function public.set_updated_at();

create table if not exists public.conversation_members (
  conversation_id uuid not null references public.conversations(id) on delete cascade,
  user_id uuid not null references public.profiles(id) on delete cascade,
  last_read_at timestamptz,
  joined_at timestamptz not null default now(),
  primary key(conversation_id,user_id)
);
create index if not exists conversation_members_user on public.conversation_members(user_id,conversation_id);

create table if not exists public.messages (
  id uuid primary key default gen_random_uuid(),
  conversation_id uuid not null references public.conversations(id) on delete cascade,
  sender_id uuid not null references public.profiles(id) on delete cascade,
  client_message_id uuid not null,
  body text not null check (char_length(body) between 1 and 4000),
  created_at timestamptz not null default now(),
  edited_at timestamptz,
  deleted_at timestamptz,
  unique(sender_id,client_message_id)
);
create index if not exists messages_conversation_time on public.messages(conversation_id,created_at);

create table if not exists public.conversation_typing (
  conversation_id uuid not null references public.conversations(id) on delete cascade,
  user_id uuid not null references public.profiles(id) on delete cascade,
  expires_at timestamptz not null,
  primary key(conversation_id,user_id)
);

create table if not exists public.user_presence (
  user_id uuid primary key references public.profiles(id) on delete cascade,
  status text not null default 'offline' check (status in ('online','away','offline')),
  device_name text not null default '',
  last_seen_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists public.social_notifications (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references public.profiles(id) on delete cascade,
  actor_id uuid references public.profiles(id) on delete set null,
  notification_type text not null,
  entity_type text,
  entity_id uuid,
  payload jsonb not null default '{}'::jsonb,
  is_read boolean not null default false,
  created_at timestamptz not null default now()
);
create index if not exists social_notifications_user_unread on public.social_notifications(user_id,is_read,created_at desc);

-- 2B: immutable, idempotent productivity completion events
create table if not exists public.productivity_events (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references public.profiles(id) on delete cascade,
  event_type text not null check (event_type in ('habit','daily','quest','pomodoro','sport')),
  source_local_id text,
  idempotency_key text not null,
  points integer not null check (points between 1 and 500),
  completed_at timestamptz not null,
  device_id text not null default '',
  payload jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  unique(user_id,idempotency_key)
);
create index if not exists productivity_user_time on public.productivity_events(user_id,completed_at desc);

-- 2C: online PvP. Scores are derived from server-created productivity events.
create table if not exists public.online_pvp_challenges (
  id uuid primary key default gen_random_uuid(),
  challenger_id uuid not null references public.profiles(id) on delete cascade,
  opponent_id uuid not null references public.profiles(id) on delete cascade,
  status text not null default 'pending' check (status in ('pending','accepted','rejected','cancelled','active','completed','expired')),
  duration_days integer not null default 7 check (duration_days between 1 and 30),
  start_at timestamptz,
  end_at timestamptz,
  winner_id uuid references public.profiles(id) on delete set null,
  created_at timestamptz not null default now(),
  responded_at timestamptz,
  resolved_at timestamptz,
  check(challenger_id<>opponent_id)
);
create unique index if not exists pvp_one_open_pair on public.online_pvp_challenges
  (least(challenger_id,opponent_id),greatest(challenger_id,opponent_id))
  where status in ('pending','accepted','active');
create index if not exists pvp_challenger_status on public.online_pvp_challenges(challenger_id,status);
create index if not exists pvp_opponent_status on public.online_pvp_challenges(opponent_id,status);

create table if not exists public.online_pvp_rewards (
  challenge_id uuid not null references public.online_pvp_challenges(id) on delete cascade,
  user_id uuid not null references public.profiles(id) on delete cascade,
  xp_reward integer not null default 0,
  gold_reward integer not null default 0,
  claimed_at timestamptz,
  primary key(challenge_id,user_id)
);

-- 2D: cloud guilds, realtime chat, contribution and server-computed boss damage
create table if not exists public.online_guilds (
  id uuid primary key default gen_random_uuid(),
  name citext not null unique check (char_length(name) between 3 and 40),
  description text not null default '' check (char_length(description)<=500),
  leader_id uuid not null references public.profiles(id) on delete restrict,
  level integer not null default 1,
  exp bigint not null default 0,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);
create trigger online_guilds_updated_at before update on public.online_guilds
for each row execute function public.set_updated_at();

create table if not exists public.online_guild_members (
  guild_id uuid not null references public.online_guilds(id) on delete cascade,
  user_id uuid not null unique references public.profiles(id) on delete cascade,
  role text not null default 'member' check (role in ('leader','officer','member')),
  joined_at timestamptz not null default now(),
  primary key(guild_id,user_id)
);
create index if not exists online_guild_members_user on public.online_guild_members(user_id,guild_id);

create table if not exists public.online_guild_requests (
  id uuid primary key default gen_random_uuid(),
  guild_id uuid not null references public.online_guilds(id) on delete cascade,
  user_id uuid not null references public.profiles(id) on delete cascade,
  status text not null default 'pending' check (status in ('pending','accepted','rejected','cancelled')),
  created_at timestamptz not null default now(),
  responded_at timestamptz,
  unique(guild_id,user_id)
);

create table if not exists public.online_guild_messages (
  id uuid primary key default gen_random_uuid(),
  guild_id uuid not null references public.online_guilds(id) on delete cascade,
  sender_id uuid not null references public.profiles(id) on delete cascade,
  client_message_id uuid not null,
  body text not null check (char_length(body) between 1 and 4000),
  created_at timestamptz not null default now(),
  deleted_at timestamptz,
  unique(sender_id,client_message_id)
);
create index if not exists online_guild_messages_time on public.online_guild_messages(guild_id,created_at);

create table if not exists public.online_guild_contributions (
  guild_id uuid not null references public.online_guilds(id) on delete cascade,
  event_id uuid not null unique references public.productivity_events(id) on delete cascade,
  user_id uuid not null references public.profiles(id) on delete cascade,
  points integer not null,
  created_at timestamptz not null default now(),
  primary key(guild_id,event_id)
);

create table if not exists public.online_guild_battles (
  id uuid primary key default gen_random_uuid(),
  guild_id uuid not null references public.online_guilds(id) on delete cascade,
  boss_key text not null,
  boss_name text not null,
  max_hp bigint not null check(max_hp>0),
  current_hp bigint not null check(current_hp>=0),
  status text not null default 'active' check(status in ('active','defeated','expired','cancelled')),
  started_at timestamptz not null default now(),
  ended_at timestamptz
);
create unique index if not exists one_active_guild_battle on public.online_guild_battles(guild_id) where status='active';

create table if not exists public.online_guild_boss_actions (
  battle_id uuid not null references public.online_guild_battles(id) on delete cascade,
  event_id uuid not null unique references public.productivity_events(id) on delete cascade,
  user_id uuid not null references public.profiles(id) on delete cascade,
  damage integer not null,
  created_at timestamptz not null default now(),
  primary key(battle_id,event_id)
);

-- Membership helpers used by RLS.
create or replace function public.is_conversation_member(p_conversation_id uuid)
returns boolean language sql stable security definer set search_path=public as $$
  select exists(select 1 from public.conversation_members where conversation_id=p_conversation_id and user_id=auth.uid())
$$;
create or replace function public.is_online_guild_member(p_guild_id uuid)
returns boolean language sql stable security definer set search_path=public as $$
  select exists(select 1 from public.online_guild_members where guild_id=p_guild_id and user_id=auth.uid())
$$;
create or replace function public.is_online_guild_leader(p_guild_id uuid)
returns boolean language sql stable security definer set search_path=public as $$
  select exists(select 1 from public.online_guild_members where guild_id=p_guild_id and user_id=auth.uid() and role in ('leader','officer'))
$$;

-- 2A RPCs
create or replace function public.get_or_create_direct_conversation(p_other_user_id uuid)
returns uuid language plpgsql security definer set search_path=public as $$
declare p_key text; p_id uuid;
begin
  if not public.current_profile_active() then raise exception 'account_unavailable'; end if;
  if not public.is_accepted_friend(p_other_user_id) then raise exception 'not_friends'; end if;
  p_key=least(auth.uid(),p_other_user_id)::text||':'||greatest(auth.uid(),p_other_user_id)::text;
  insert into public.conversations(kind,direct_key) values('direct',p_key)
    on conflict(direct_key) do update set updated_at=now() returning id into p_id;
  insert into public.conversation_members(conversation_id,user_id) values
    (p_id,auth.uid()),(p_id,p_other_user_id) on conflict do nothing;
  return p_id;
end; $$;

create or replace function public.send_direct_message(p_conversation_id uuid,p_body text,p_client_message_id uuid)
returns public.messages language plpgsql security definer set search_path=public as $$
declare result public.messages;
begin
  if not public.current_profile_active() or not public.is_conversation_member(p_conversation_id) then raise exception 'forbidden'; end if;
  insert into public.messages(conversation_id,sender_id,body,client_message_id)
  values(p_conversation_id,auth.uid(),left(trim(p_body),4000),p_client_message_id)
  on conflict(sender_id,client_message_id) do update set body=excluded.body
  returning * into result;
  update public.conversations set updated_at=now() where id=p_conversation_id;
  return result;
end; $$;

create or replace function public.mark_conversation_read(p_conversation_id uuid)
returns boolean language plpgsql security definer set search_path=public as $$
begin
  update public.conversation_members set last_read_at=now()
    where conversation_id=p_conversation_id and user_id=auth.uid();
  return found;
end; $$;

create or replace function public.set_conversation_typing(p_conversation_id uuid,p_is_typing boolean)
returns boolean language plpgsql security definer set search_path=public as $$
begin
  if not public.is_conversation_member(p_conversation_id) then raise exception 'forbidden'; end if;
  if p_is_typing then
    insert into public.conversation_typing(conversation_id,user_id,expires_at)
    values(p_conversation_id,auth.uid(),now()+interval '6 seconds')
    on conflict(conversation_id,user_id) do update set expires_at=excluded.expires_at;
  else
    delete from public.conversation_typing where conversation_id=p_conversation_id and user_id=auth.uid();
  end if;
  return true;
end; $$;

create or replace function public.heartbeat_presence(p_status text default 'online',p_device_name text default '')
returns public.user_presence language plpgsql security definer set search_path=public as $$
declare result public.user_presence;
begin
  insert into public.user_presence(user_id,status,device_name,last_seen_at,updated_at)
  values(auth.uid(),case when p_status in ('online','away','offline') then p_status else 'online' end,left(p_device_name,100),now(),now())
  on conflict(user_id) do update set status=excluded.status,device_name=excluded.device_name,last_seen_at=now(),updated_at=now()
  returning * into result; return result;
end; $$;

create or replace function public.mark_social_notifications_read(p_ids uuid[] default null)
returns integer language plpgsql security definer set search_path=public as $$
declare affected integer;
begin
  update public.social_notifications set is_read=true where user_id=auth.uid() and (p_ids is null or id=any(p_ids));
  get diagnostics affected=row_count;return affected;
end; $$;

-- 2B: point calculation and immutable event insert.
create or replace function public.calculate_productivity_points(p_event_type text,p_payload jsonb)
returns integer language plpgsql immutable as $$
declare minutes integer;
begin
  case p_event_type
    when 'habit' then return 10;
    when 'daily' then return 15;
    when 'quest' then return 30;
    when 'sport' then return 20;
    when 'pomodoro' then
      minutes=greatest(1,least(240,coalesce((p_payload->>'duration_minutes')::integer,1)));
      return greatest(5,least(120,minutes));
    else raise exception 'invalid_event_type';
  end case;
end; $$;

create or replace function public.record_productivity_event(
  p_event_type text,p_source_local_id text,p_idempotency_key text,p_completed_at timestamptz,
  p_device_id text default '',p_payload jsonb default '{}'::jsonb)
returns public.productivity_events language plpgsql security definer set search_path=public as $$
declare result public.productivity_events;p_points integer;
begin
  if not public.current_profile_active() then raise exception 'account_unavailable'; end if;
  select * into result from public.productivity_events where user_id=auth.uid() and idempotency_key=p_idempotency_key;
  if result.id is not null then return result; end if;
  if p_completed_at>now()+interval '5 minutes' or p_completed_at<now()-interval '14 days' then raise exception 'invalid_event_time'; end if;
  if p_event_type in ('habit','daily','sport') and exists(
      select 1 from public.productivity_events where user_id=auth.uid() and event_type=p_event_type
      and source_local_id=p_source_local_id and completed_at::date=p_completed_at::date)
    then raise exception 'daily_event_exists'; end if;
  if p_event_type='quest' and exists(
      select 1 from public.productivity_events where user_id=auth.uid() and event_type='quest'
      and source_local_id=p_source_local_id)
    then raise exception 'quest_event_exists'; end if;
  if p_event_type='pomodoro' and (
      (select count(*) from public.productivity_events where user_id=auth.uid() and event_type='pomodoro' and completed_at::date=p_completed_at::date)>=48
      or coalesce((select sum(coalesce((payload->>'duration_minutes')::integer,0)) from public.productivity_events
                   where user_id=auth.uid() and event_type='pomodoro' and completed_at::date=p_completed_at::date),0)
         + coalesce((p_payload->>'duration_minutes')::integer,0)>720)
    then raise exception 'pomodoro_daily_limit'; end if;
  p_points=public.calculate_productivity_points(p_event_type,p_payload);
  insert into public.productivity_events(user_id,event_type,source_local_id,idempotency_key,points,completed_at,device_id,payload)
  values(auth.uid(),p_event_type,left(p_source_local_id,200),left(p_idempotency_key,200),p_points,p_completed_at,left(p_device_id,120),p_payload)
  on conflict(user_id,idempotency_key) do update set idempotency_key=excluded.idempotency_key
  returning * into result;return result;
end; $$;

-- 2C: PvP RPCs and server-derived score.
create or replace function public.send_online_pvp_challenge(p_opponent_id uuid,p_duration_days integer default 7)
returns public.online_pvp_challenges language plpgsql security definer set search_path=public as $$
declare result public.online_pvp_challenges;
begin
  if not public.current_profile_active() or not public.is_accepted_friend(p_opponent_id) then raise exception 'not_friends'; end if;
  insert into public.online_pvp_challenges(challenger_id,opponent_id,duration_days)
  values(auth.uid(),p_opponent_id,greatest(1,least(30,p_duration_days))) returning * into result;
  insert into public.social_notifications(user_id,actor_id,notification_type,entity_type,entity_id)
  values(p_opponent_id,auth.uid(),'pvp_request','pvp',result.id);
  return result;
exception when unique_violation then raise exception 'pvp_exists';
end; $$;

create or replace function public.respond_online_pvp_challenge(p_challenge_id uuid,p_accept boolean)
returns public.online_pvp_challenges language plpgsql security definer set search_path=public as $$
declare result public.online_pvp_challenges;
begin
  update public.online_pvp_challenges set status=case when p_accept then 'active' else 'rejected' end,
    responded_at=now(),start_at=case when p_accept then now() else null end,
    end_at=case when p_accept then now()+make_interval(days=>duration_days) else null end
  where id=p_challenge_id and opponent_id=auth.uid() and status='pending' returning * into result;
  if result.id is null then raise exception 'invalid_request'; end if;return result;
end; $$;

create or replace function public.cancel_online_pvp_challenge(p_challenge_id uuid)
returns boolean language plpgsql security definer set search_path=public as $$
begin
  update public.online_pvp_challenges set status='cancelled' where id=p_challenge_id and challenger_id=auth.uid() and status='pending';return found;
end; $$;

create or replace function public.pvp_score(p_challenge_id uuid,p_user_id uuid)
returns bigint language sql stable security definer set search_path=public as $$
  select coalesce(sum(e.points),0)::bigint from public.online_pvp_challenges c
  left join public.productivity_events e on e.user_id=p_user_id and e.completed_at>=c.start_at and e.completed_at<=c.end_at
  where c.id=p_challenge_id and auth.uid() in (c.challenger_id,c.opponent_id)
    and p_user_id in (c.challenger_id,c.opponent_id)
$$;

create or replace function public.finalize_online_pvp(p_challenge_id uuid)
returns jsonb language plpgsql security definer set search_path=public as $$
declare c public.online_pvp_challenges;a bigint;b bigint;winner uuid;
begin
  select * into c from public.online_pvp_challenges where id=p_challenge_id for update;
  if c.id is null or auth.uid() not in(c.challenger_id,c.opponent_id) then raise exception 'forbidden'; end if;
  if c.status='completed' then return jsonb_build_object('status','completed','winner_id',c.winner_id); end if;
  if c.status<>'active' or c.end_at>now() then raise exception 'not_due'; end if;
  a=public.pvp_score(c.id,c.challenger_id);b=public.pvp_score(c.id,c.opponent_id);
  winner=case when a>b then c.challenger_id when b>a then c.opponent_id else null end;
  update public.online_pvp_challenges set status='completed',winner_id=winner,resolved_at=now() where id=c.id;
  insert into public.online_pvp_rewards(challenge_id,user_id,xp_reward,gold_reward) values
    (c.id,c.challenger_id,case when winner=c.challenger_id then 100 else 25 end,case when winner=c.challenger_id then 50 else 10 end),
    (c.id,c.opponent_id,case when winner=c.opponent_id then 100 else 25 end,case when winner=c.opponent_id then 50 else 10 end)
    on conflict do nothing;
  return jsonb_build_object('status','completed','challenger_score',a,'opponent_score',b,'winner_id',winner);
end; $$;

create or replace function public.claim_online_pvp_reward(p_challenge_id uuid)
returns public.online_pvp_rewards language plpgsql security definer set search_path=public as $$
declare result public.online_pvp_rewards;
begin
  update public.online_pvp_rewards set claimed_at=now() where challenge_id=p_challenge_id and user_id=auth.uid() and claimed_at is null returning * into result;
  if result.challenge_id is null then raise exception 'nothing_to_claim'; end if;return result;
end; $$;

-- 2D: Guild RPCs.
create or replace function public.create_online_guild(p_name text,p_description text default '')
returns public.online_guilds language plpgsql security definer set search_path=public as $$
declare result public.online_guilds;
begin
  if not public.current_profile_active() then raise exception 'account_unavailable'; end if;
  if exists(select 1 from public.online_guild_members where user_id=auth.uid()) then raise exception 'already_in_guild'; end if;
  insert into public.online_guilds(name,description,leader_id) values(trim(p_name),left(coalesce(p_description,''),500),auth.uid()) returning * into result;
  insert into public.online_guild_members(guild_id,user_id,role) values(result.id,auth.uid(),'leader');return result;
end; $$;

create or replace function public.request_online_guild_join(p_guild_id uuid)
returns public.online_guild_requests language plpgsql security definer set search_path=public as $$
declare result public.online_guild_requests;
begin
  if exists(select 1 from public.online_guild_members where user_id=auth.uid()) then raise exception 'already_in_guild'; end if;
  insert into public.online_guild_requests(guild_id,user_id,status) values(p_guild_id,auth.uid(),'pending')
    on conflict(guild_id,user_id) do update set status='pending',created_at=now(),responded_at=null returning * into result;
  return result;
end; $$;

create or replace function public.respond_online_guild_join(p_request_id uuid,p_accept boolean)
returns public.online_guild_requests language plpgsql security definer set search_path=public as $$
declare result public.online_guild_requests;
begin
  select r.* into result from public.online_guild_requests r where r.id=p_request_id and r.status='pending' for update;
  if result.id is null or not public.is_online_guild_leader(result.guild_id) then raise exception 'forbidden'; end if;
  if p_accept then
    if exists(select 1 from public.online_guild_members where user_id=result.user_id) then raise exception 'already_in_guild'; end if;
    insert into public.online_guild_members(guild_id,user_id) values(result.guild_id,result.user_id);
  end if;
  update public.online_guild_requests set status=case when p_accept then 'accepted' else 'rejected' end,responded_at=now() where id=result.id returning * into result;
  return result;
end; $$;

create or replace function public.send_online_guild_message(p_guild_id uuid,p_body text,p_client_message_id uuid)
returns public.online_guild_messages language plpgsql security definer set search_path=public as $$
declare result public.online_guild_messages;
begin
  if not public.is_online_guild_member(p_guild_id) then raise exception 'forbidden'; end if;
  insert into public.online_guild_messages(guild_id,sender_id,body,client_message_id)
  values(p_guild_id,auth.uid(),left(trim(p_body),4000),p_client_message_id)
  on conflict(sender_id,client_message_id) do update set body=excluded.body returning * into result;return result;
end; $$;

create or replace function public.start_online_guild_boss(p_guild_id uuid,p_boss_key text,p_boss_name text,p_max_hp bigint)
returns public.online_guild_battles language plpgsql security definer set search_path=public as $$
declare result public.online_guild_battles;
begin
  if not public.is_online_guild_leader(p_guild_id) then raise exception 'forbidden'; end if;
  insert into public.online_guild_battles(guild_id,boss_key,boss_name,max_hp,current_hp)
  values(p_guild_id,left(p_boss_key,80),left(p_boss_name,120),p_max_hp,p_max_hp) returning * into result;return result;
end; $$;

-- Every accepted productivity event contributes once to guild and active guild boss.
create or replace function public.apply_productivity_to_guild()
returns trigger language plpgsql security definer set search_path=public as $$
declare g uuid;b public.online_guild_battles;damage integer;
begin
  select guild_id into g from public.online_guild_members where user_id=new.user_id;
  if g is null then return new; end if;
  insert into public.online_guild_contributions(guild_id,event_id,user_id,points) values(g,new.id,new.user_id,new.points) on conflict do nothing;
  update public.online_guilds set exp=exp+new.points,level=greatest(level,1+((exp+new.points)/1000)::integer) where id=g;
  select * into b from public.online_guild_battles where guild_id=g and status='active' for update;
  if b.id is not null then
    damage=greatest(1,new.points);
    insert into public.online_guild_boss_actions(battle_id,event_id,user_id,damage) values(b.id,new.id,new.user_id,damage) on conflict do nothing;
    update public.online_guild_battles set current_hp=greatest(0,current_hp-damage),
      status=case when current_hp-damage<=0 then 'defeated' else status end,
      ended_at=case when current_hp-damage<=0 then now() else ended_at end where id=b.id;
  end if;
  return new;
end; $$;
drop trigger if exists productivity_to_guild on public.productivity_events;
create trigger productivity_to_guild after insert on public.productivity_events
for each row execute function public.apply_productivity_to_guild();

-- 2E: authenticated leaderboard RPCs expose public profile fields only.
create or replace function public.get_global_productivity_leaderboard(p_days integer default 30,p_limit integer default 50)
returns table(user_id uuid,username citext,display_name text,avatar_path text,total_points bigint,event_count bigint)
language sql stable security definer set search_path=public as $$
  select p.id,p.username,p.display_name,p.avatar_path,coalesce(sum(e.points),0)::bigint,count(e.id)::bigint
  from public.profiles p left join public.productivity_events e on e.user_id=p.id
    and e.completed_at>=now()-make_interval(days=>greatest(1,least(365,p_days)))
  where p.deleted_at is null group by p.id,p.username,p.display_name,p.avatar_path
  order by coalesce(sum(e.points),0) desc,count(e.id) desc limit greatest(1,least(100,p_limit))
$$;
create or replace function public.get_online_guild_leaderboard(p_limit integer default 50)
returns table(guild_id uuid,name citext,level integer,exp bigint,member_count bigint)
language sql stable security definer set search_path=public as $$
  select g.id,g.name,g.level,g.exp,count(m.user_id)::bigint from public.online_guilds g
  left join public.online_guild_members m on m.guild_id=g.id group by g.id,g.name,g.level,g.exp
  order by g.exp desc,g.level desc limit greatest(1,least(100,p_limit))
$$;

-- Message/notification triggers.
create or replace function public.notify_direct_message()
returns trigger language plpgsql security definer set search_path=public as $$
begin
  insert into public.social_notifications(user_id,actor_id,notification_type,entity_type,entity_id,payload)
  select m.user_id,new.sender_id,'direct_message','conversation',new.conversation_id,
    jsonb_build_object('preview',left(new.body,120)) from public.conversation_members m
  where m.conversation_id=new.conversation_id and m.user_id<>new.sender_id;
  return new;
end; $$;
drop trigger if exists notify_direct_message on public.messages;
create trigger notify_direct_message after insert on public.messages for each row execute function public.notify_direct_message();

create or replace function public.notify_social_request_changes()
returns trigger language plpgsql security definer set search_path=public as $$
begin
  if tg_table_name='friendships' then
    if tg_op='INSERT' then
      insert into public.social_notifications(user_id,actor_id,notification_type,entity_type,entity_id)
      values(new.addressee_id,new.requester_id,'friend_request','friendship',new.id);
    elsif old.status='pending' and new.status<>old.status then
      insert into public.social_notifications(user_id,actor_id,notification_type,entity_type,entity_id,payload)
      values(new.requester_id,new.addressee_id,'friend_'||new.status,'friendship',new.id,jsonb_build_object('status',new.status));
    end if;
  elsif tg_table_name='couple_relationships' then
    if tg_op='INSERT' or (old.status is distinct from new.status and new.status='pending') then
      insert into public.social_notifications(user_id,actor_id,notification_type,entity_type,entity_id)
      values(case when new.requested_by=new.user_a_id then new.user_b_id else new.user_a_id end,new.requested_by,'couple_request','couple',new.id);
    elsif old.status='pending' and new.status<>old.status then
      insert into public.social_notifications(user_id,actor_id,notification_type,entity_type,entity_id,payload)
      values(new.requested_by,case when new.requested_by=new.user_a_id then new.user_b_id else new.user_a_id end,
        'couple_'||new.status,'couple',new.id,jsonb_build_object('status',new.status));
    end if;
  end if;
  return new;
end; $$;
drop trigger if exists notify_friendship_changes on public.friendships;
create trigger notify_friendship_changes after insert or update on public.friendships for each row execute function public.notify_social_request_changes();
drop trigger if exists notify_couple_changes on public.couple_relationships;
create trigger notify_couple_changes after insert or update on public.couple_relationships for each row execute function public.notify_social_request_changes();

-- RLS
alter table public.conversations enable row level security;
alter table public.conversation_members enable row level security;
alter table public.messages enable row level security;
alter table public.conversation_typing enable row level security;
alter table public.user_presence enable row level security;
alter table public.social_notifications enable row level security;
alter table public.productivity_events enable row level security;
alter table public.online_pvp_challenges enable row level security;
alter table public.online_pvp_rewards enable row level security;
alter table public.online_guilds enable row level security;
alter table public.online_guild_members enable row level security;
alter table public.online_guild_requests enable row level security;
alter table public.online_guild_messages enable row level security;
alter table public.online_guild_contributions enable row level security;
alter table public.online_guild_battles enable row level security;
alter table public.online_guild_boss_actions enable row level security;

create policy conversations_member_read on public.conversations for select to authenticated using(public.is_conversation_member(id));
create policy conversation_members_read on public.conversation_members for select to authenticated using(public.is_conversation_member(conversation_id));
create policy messages_member_read on public.messages for select to authenticated using(public.is_conversation_member(conversation_id));
create policy typing_member_read on public.conversation_typing for select to authenticated using(public.is_conversation_member(conversation_id));
create policy presence_authenticated_read on public.user_presence for select to authenticated using(true);
create policy notifications_owner_read on public.social_notifications for select to authenticated using(user_id=auth.uid());
create policy productivity_owner_read on public.productivity_events for select to authenticated using(user_id=auth.uid());
create policy pvp_participant_read on public.online_pvp_challenges for select to authenticated using(auth.uid() in(challenger_id,opponent_id));
create policy pvp_rewards_owner_read on public.online_pvp_rewards for select to authenticated using(user_id=auth.uid());
create policy guilds_authenticated_read on public.online_guilds for select to authenticated using(true);
create policy guild_members_authenticated_read on public.online_guild_members for select to authenticated using(true);
create policy guild_requests_participant_read on public.online_guild_requests for select to authenticated
  using(user_id=auth.uid() or public.is_online_guild_leader(guild_id));
create policy guild_messages_member_read on public.online_guild_messages for select to authenticated using(public.is_online_guild_member(guild_id));
create policy guild_contrib_member_read on public.online_guild_contributions for select to authenticated using(public.is_online_guild_member(guild_id));
create policy guild_battles_member_read on public.online_guild_battles for select to authenticated using(public.is_online_guild_member(guild_id));
create policy guild_actions_member_read on public.online_guild_boss_actions for select to authenticated
  using(exists(select 1 from public.online_guild_battles b where b.id=battle_id and public.is_online_guild_member(b.guild_id)));

-- Mutation RPCs are authenticated only.
revoke execute on function public.get_or_create_direct_conversation(uuid) from public,anon;
revoke execute on function public.send_direct_message(uuid,text,uuid) from public,anon;
revoke execute on function public.mark_conversation_read(uuid) from public,anon;
revoke execute on function public.set_conversation_typing(uuid,boolean) from public,anon;
revoke execute on function public.heartbeat_presence(text,text) from public,anon;
revoke execute on function public.mark_social_notifications_read(uuid[]) from public,anon;
revoke execute on function public.record_productivity_event(text,text,text,timestamptz,text,jsonb) from public,anon;
revoke execute on function public.send_online_pvp_challenge(uuid,integer) from public,anon;
revoke execute on function public.respond_online_pvp_challenge(uuid,boolean) from public,anon;
revoke execute on function public.cancel_online_pvp_challenge(uuid) from public,anon;
revoke execute on function public.pvp_score(uuid,uuid) from public,anon;
revoke execute on function public.finalize_online_pvp(uuid) from public,anon;
revoke execute on function public.claim_online_pvp_reward(uuid) from public,anon;
revoke execute on function public.create_online_guild(text,text) from public,anon;
revoke execute on function public.request_online_guild_join(uuid) from public,anon;
revoke execute on function public.respond_online_guild_join(uuid,boolean) from public,anon;
revoke execute on function public.send_online_guild_message(uuid,text,uuid) from public,anon;
revoke execute on function public.start_online_guild_boss(uuid,text,text,bigint) from public,anon;
revoke execute on function public.get_global_productivity_leaderboard(integer,integer) from public,anon;
revoke execute on function public.get_online_guild_leaderboard(integer) from public,anon;

grant select on public.conversations,public.conversation_members,public.messages,public.conversation_typing,public.user_presence,
  public.social_notifications,public.productivity_events,public.online_pvp_challenges,public.online_pvp_rewards,
  public.online_guilds,public.online_guild_members,public.online_guild_requests,public.online_guild_messages,
  public.online_guild_contributions,public.online_guild_battles,public.online_guild_boss_actions to authenticated;
grant execute on function public.get_or_create_direct_conversation(uuid) to authenticated;
grant execute on function public.send_direct_message(uuid,text,uuid) to authenticated;
grant execute on function public.mark_conversation_read(uuid) to authenticated;
grant execute on function public.set_conversation_typing(uuid,boolean) to authenticated;
grant execute on function public.heartbeat_presence(text,text) to authenticated;
grant execute on function public.mark_social_notifications_read(uuid[]) to authenticated;
grant execute on function public.record_productivity_event(text,text,text,timestamptz,text,jsonb) to authenticated;
grant execute on function public.send_online_pvp_challenge(uuid,integer) to authenticated;
grant execute on function public.respond_online_pvp_challenge(uuid,boolean) to authenticated;
grant execute on function public.cancel_online_pvp_challenge(uuid) to authenticated;
grant execute on function public.pvp_score(uuid,uuid) to authenticated;
grant execute on function public.finalize_online_pvp(uuid) to authenticated;
grant execute on function public.claim_online_pvp_reward(uuid) to authenticated;
grant execute on function public.create_online_guild(text,text) to authenticated;
grant execute on function public.request_online_guild_join(uuid) to authenticated;
grant execute on function public.respond_online_guild_join(uuid,boolean) to authenticated;
grant execute on function public.send_online_guild_message(uuid,text,uuid) to authenticated;
grant execute on function public.start_online_guild_boss(uuid,text,text,bigint) to authenticated;
grant execute on function public.get_global_productivity_leaderboard(integer,integer) to authenticated;
grant execute on function public.get_online_guild_leaderboard(integer) to authenticated;

-- Realtime publication.
do $$ begin alter publication supabase_realtime add table public.messages; exception when duplicate_object then null; end $$;
do $$ begin alter publication supabase_realtime add table public.conversation_typing; exception when duplicate_object then null; end $$;
do $$ begin alter publication supabase_realtime add table public.user_presence; exception when duplicate_object then null; end $$;
do $$ begin alter publication supabase_realtime add table public.social_notifications; exception when duplicate_object then null; end $$;
do $$ begin alter publication supabase_realtime add table public.productivity_events; exception when duplicate_object then null; end $$;
do $$ begin alter publication supabase_realtime add table public.online_pvp_challenges; exception when duplicate_object then null; end $$;
do $$ begin alter publication supabase_realtime add table public.online_guild_messages; exception when duplicate_object then null; end $$;
do $$ begin alter publication supabase_realtime add table public.online_guild_battles; exception when duplicate_object then null; end $$;

notify pgrst,'reload schema';
