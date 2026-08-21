-- CraftLife Phase 5A: server-authoritative reward ledger + cloud wallet.
-- Ledger append-only; balance materialized; client TIDAK pernah mengirim jumlah reward.
-- Konvensi mengikuti migration Phase 1-4 (lowercase, security definer, idempotency key).

-- 5A-1: definisi achievement (sumber angka resmi untuk claim achievement cloud)
create table if not exists public.achievement_definitions (
  achievement_key text primary key,
  xp_reward integer not null check (xp_reward between 0 and 100000),
  gold_reward integer not null check (gold_reward between 0 and 100000),
  gems_reward integer not null default 0 check (gems_reward between 0 and 100000),
  created_at timestamptz not null default now()
);

-- 5A-2: ledger append-only
create table if not exists public.reward_ledger (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references public.profiles(id) on delete cascade,
  source text not null check (source in ('productivity','pvp','guild_boss','achievement','quest','shop_refund','admin_adjustment')),
  ref_id uuid,
  ref_key text not null default '',
  delta_xp integer not null default 0,
  delta_gold integer not null default 0,
  delta_gems integer not null default 0,
  reversal_of uuid references public.reward_ledger(id),
  idempotency_key text not null,
  created_at timestamptz not null default now(),
  unique(user_id, idempotency_key),
  check (delta_xp <> 0 or delta_gold <> 0 or delta_gems <> 0)
);
create index if not exists reward_ledger_user_time on public.reward_ledger(user_id, created_at desc);

-- 5A-3: wallet materialized (cache server-side; dihitung dari ledger via trigger)
create table if not exists public.user_cloud_wallets (
  user_id uuid primary key references public.profiles(id) on delete cascade,
  xp bigint not null default 0,
  gold bigint not null default 0,
  gems bigint not null default 0,
  level integer not null default 1,
  updated_at timestamptz not null default now()
);
create trigger user_cloud_wallets_updated_at before update on public.user_cloud_wallets
for each row execute function public.set_updated_at();

create or replace function public.wallet_level_for_xp(p_xp bigint)
returns integer language sql immutable as $$
  select greatest(1, floor(sqrt(greatest(0, p_xp) / 100.0))::integer + 1);
$$;

create or replace function public.apply_ledger_to_wallet()
returns trigger language plpgsql security definer set search_path=public as $$
begin
  insert into public.user_cloud_wallets(user_id, xp, gold, gems)
  values (new.user_id, greatest(0,new.delta_xp), greatest(0,new.delta_gold), greatest(0,new.delta_gems))
  on conflict (user_id) do update set
    xp   = greatest(0, user_cloud_wallets.xp   + new.delta_xp),
    gold = greatest(0, user_cloud_wallets.gold + new.delta_gold),
    gems = greatest(0, user_cloud_wallets.gems + new.delta_gems);
  update public.user_cloud_wallets set level = public.wallet_level_for_xp(xp) where user_id = new.user_id;
  return new;
end; $$;
create trigger reward_ledger_apply after insert on public.reward_ledger
for each row execute function public.apply_ledger_to_wallet();

-- 5A-4: sumber reward -> ledger (trigger, tanpa mengubah signature RPC lama)
create or replace function public.ledger_from_productivity()
returns trigger language plpgsql security definer set search_path=public as $$
begin
  insert into public.reward_ledger(user_id, source, ref_id, ref_key, delta_xp, delta_gold, idempotency_key)
  values (new.user_id, 'productivity', new.id, coalesce(new.source_local_id,''),
          new.points * 2, new.points, 'prod:' || new.id::text)
  on conflict (user_id, idempotency_key) do nothing;
  return new;
end; $$;
create trigger productivity_to_ledger after insert on public.productivity_events
for each row execute function public.ledger_from_productivity();

create or replace function public.ledger_from_pvp_reward()
returns trigger language plpgsql security definer set search_path=public as $$
begin
  insert into public.reward_ledger(user_id, source, ref_id, delta_xp, delta_gold, idempotency_key)
  values (new.user_id, 'pvp', new.challenge_id, new.xp_reward, new.gold_reward,
          'pvp:' || new.challenge_id::text || ':' || new.user_id::text)
  on conflict (user_id, idempotency_key) do nothing;
  return new;
end; $$;
create trigger pvp_reward_to_ledger after insert on public.online_pvp_rewards
for each row execute function public.ledger_from_pvp_reward();

create or replace function public.ledger_from_boss_reward()
returns trigger language plpgsql security definer set search_path=public as $$
begin
  insert into public.reward_ledger(user_id, source, ref_id, delta_xp, delta_gold, idempotency_key)
  values (new.user_id, 'guild_boss', new.battle_id, new.xp_reward, new.gold_reward,
          'boss:' || new.battle_id::text || ':' || new.user_id::text)
  on conflict (user_id, idempotency_key) do nothing;
  return new;
end; $$;
create trigger boss_reward_to_ledger after insert on public.online_guild_boss_rewards
for each row execute function public.ledger_from_boss_reward();

-- 5A-5: RPC claim achievement (angka dari tabel definisi, bukan dari client)
create or replace function public.claim_achievement_reward_cloud(achievement_key text, claim_key text)
returns public.reward_ledger language plpgsql security definer set search_path=public as $$
declare def public.achievement_definitions; res public.reward_ledger;
        ak text := achievement_key; ck text := claim_key;
begin
  if not public.current_profile_active() then raise exception 'account_unavailable'; end if;
  select * into def from public.achievement_definitions where achievement_definitions.achievement_key = ak;
  if not found then raise exception 'unknown_achievement'; end if;
  select * into res from public.reward_ledger where reward_ledger.user_id = auth.uid() and reward_ledger.idempotency_key = ck;
  if res.id is not null then return res; end if;
  if exists(select 1 from public.reward_ledger
            where reward_ledger.user_id = auth.uid() and reward_ledger.source = 'achievement' and reward_ledger.ref_key = ak)
  then raise exception 'achievement_already_claimed'; end if;
  insert into public.reward_ledger(user_id, source, ref_key, delta_xp, delta_gold, delta_gems, idempotency_key)
  values (auth.uid(), 'achievement', ak, def.xp_reward, def.gold_reward, def.gems_reward, ck)
  returning * into res;
  return res;
end; $$;

-- 5A-6: baca wallet sendiri
create or replace function public.wallet_balance()
returns public.user_cloud_wallets language sql stable security definer set search_path=public as $$
  select coalesce(
    (select w from public.user_cloud_wallets w where w.user_id = auth.uid()),
    row(auth.uid(), 0, 0, 0, 1, now())::public.user_cloud_wallets);
$$;

-- 5A-7: koreksi = entry reversal, service role saja
create or replace function public.admin_reverse_ledger(p_entry_id uuid, p_reason text)
returns public.reward_ledger language plpgsql security definer set search_path=public as $$
declare orig public.reward_ledger; res public.reward_ledger;
begin
  if current_setting('role', true) is distinct from 'service_role' then raise exception 'admin_only'; end if;
  select * into orig from public.reward_ledger where id = p_entry_id and reversal_of is null;
  if not found then raise exception 'entry_not_found'; end if;
  if exists(select 1 from public.reward_ledger where reversal_of = p_entry_id) then raise exception 'already_reversed'; end if;
  insert into public.reward_ledger(user_id, source, ref_id, ref_key, delta_xp, delta_gold, delta_gems, reversal_of, idempotency_key)
  values (orig.user_id, 'admin_adjustment', orig.ref_id, orig.ref_key || ' reason:' || coalesce(p_reason,''),
          -orig.delta_xp, -orig.delta_gold, -orig.delta_gems, orig.id, 'rev:' || orig.id::text)
  returning * into res;
  return res;
end; $$;

-- 5A-8: RLS + grants (ledger/wallet/definitions tidak bisa ditulis langsung oleh client)
alter table public.reward_ledger enable row level security;
create policy reward_ledger_select_own on public.reward_ledger
for select to authenticated using (user_id = auth.uid());
alter table public.user_cloud_wallets enable row level security;
create policy user_cloud_wallets_select_own on public.user_cloud_wallets
for select to authenticated using (user_id = auth.uid());
alter table public.achievement_definitions enable row level security;
create policy achievement_definitions_read on public.achievement_definitions
for select to authenticated using (true);

revoke insert, update, delete on public.reward_ledger from authenticated, anon, public;
revoke insert, update, delete on public.user_cloud_wallets from authenticated, anon, public;
revoke insert, update, delete on public.achievement_definitions from authenticated, anon, public;
revoke execute on function public.claim_achievement_reward_cloud(text, text) from public, anon;
revoke execute on function public.wallet_balance() from public, anon;
revoke execute on function public.admin_reverse_ledger(uuid, text) from public, anon, authenticated;
grant execute on function public.admin_reverse_ledger(uuid, text) to service_role;
revoke execute on function public.wallet_level_for_xp(bigint) from public, anon;

-- 5A-10: compat fix — client mengirim parameter TANPA prefix p_, tetapi RPC lama
-- mendefinisikan p_event_type dsb. (PostgREST mencocokkan nama parameter), sehingga
-- record_productivity_event tidak pernah cocok dari desktop. Buat ulang dengan nama
-- parameter tanpa prefix (signature tipe sama; revoke diulang agar tetap aman).
drop function if exists public.record_productivity_event(text, text, text, timestamptz, text, jsonb);
create function public.record_productivity_event(
  event_type text, source_local_id text, idempotency_key text, completed_at timestamptz,
  device_id text default '', payload jsonb default '{}'::jsonb)
returns public.productivity_events language plpgsql security definer set search_path=public as $$
declare result public.productivity_events; p_points integer;
        et text := event_type; sli text := source_local_id; ik text := idempotency_key;
        ca timestamptz := completed_at; dv text := device_id; pl jsonb := payload;
begin
  if not public.current_profile_active() then raise exception 'account_unavailable'; end if;
  select * into result from public.productivity_events where productivity_events.user_id=auth.uid() and productivity_events.idempotency_key=ik;
  if result.id is not null then return result; end if;
  if ca>now()+interval '5 minutes' or ca<now()-interval '14 days' then raise exception 'invalid_event_time'; end if;
  if et in ('habit','daily','sport') and exists(
      select 1 from public.productivity_events where productivity_events.user_id=auth.uid() and productivity_events.event_type=et
      and productivity_events.source_local_id=sli and productivity_events.completed_at::date=ca::date)
    then raise exception 'daily_event_exists'; end if;
  if et='quest' and exists(
      select 1 from public.productivity_events where productivity_events.user_id=auth.uid() and productivity_events.event_type='quest'
      and productivity_events.source_local_id=sli)
    then raise exception 'quest_event_exists'; end if;
  if et='pomodoro' and (
      (select count(*) from public.productivity_events where productivity_events.user_id=auth.uid() and productivity_events.event_type='pomodoro' and productivity_events.completed_at::date=ca::date)>=48
      or coalesce((select sum(coalesce((productivity_events.payload->>'duration_minutes')::integer,0)) from public.productivity_events
                   where productivity_events.user_id=auth.uid() and productivity_events.event_type='pomodoro' and productivity_events.completed_at::date=ca::date),0)
         + coalesce((pl->>'duration_minutes')::integer,0)>720)
    then raise exception 'pomodoro_daily_limit'; end if;
  p_points=public.calculate_productivity_points(et,pl);
  insert into public.productivity_events(user_id,event_type,source_local_id,idempotency_key,points,completed_at,device_id,payload)
  values (auth.uid(),et,sli,ik,p_points,ca,dv,pl)
  returning * into result;
  return result;
end; $$;
revoke execute on function public.record_productivity_event(text, text, text, timestamptz, text, jsonb) from public, anon;

-- 5A-9: seed definisi achievement (digenerate dari ACHIEVEMENTS_REBALANCED desktop)
insert into public.achievement_definitions(achievement_key,xp_reward,gold_reward) values ('Pemula',150,75) on conflict (achievement_key) do nothing;
insert into public.achievement_definitions(achievement_key,xp_reward,gold_reward) values ('Prajurit',300,150) on conflict (achievement_key) do nothing;
insert into public.achievement_definitions(achievement_key,xp_reward,gold_reward) values ('Ksatria',600,300) on conflict (achievement_key) do nothing;
insert into public.achievement_definitions(achievement_key,xp_reward,gold_reward) values ('Legenda',2000,800) on conflict (achievement_key) do nothing;
insert into public.achievement_definitions(achievement_key,xp_reward,gold_reward) values ('Habit Starter',80,30) on conflict (achievement_key) do nothing;
insert into public.achievement_definitions(achievement_key,xp_reward,gold_reward) values ('Habit Enthusiast',250,100) on conflict (achievement_key) do nothing;
insert into public.achievement_definitions(achievement_key,xp_reward,gold_reward) values ('Habit Master',600,250) on conflict (achievement_key) do nothing;
insert into public.achievement_definitions(achievement_key,xp_reward,gold_reward) values ('Streak Warrior',150,50) on conflict (achievement_key) do nothing;
insert into public.achievement_definitions(achievement_key,xp_reward,gold_reward) values ('Streak Legend',600,200) on conflict (achievement_key) do nothing;
insert into public.achievement_definitions(achievement_key,xp_reward,gold_reward) values ('Daily Doer',100,40) on conflict (achievement_key) do nothing;
insert into public.achievement_definitions(achievement_key,xp_reward,gold_reward) values ('Daily Devotee',400,150) on conflict (achievement_key) do nothing;
insert into public.achievement_definitions(achievement_key,xp_reward,gold_reward) values ('Quest Beginner',80,30) on conflict (achievement_key) do nothing;
insert into public.achievement_definitions(achievement_key,xp_reward,gold_reward) values ('Quest Champion',300,100) on conflict (achievement_key) do nothing;
insert into public.achievement_definitions(achievement_key,xp_reward,gold_reward) values ('Sport Rookie',150,50) on conflict (achievement_key) do nothing;
insert into public.achievement_definitions(achievement_key,xp_reward,gold_reward) values ('Sport Athlete',400,150) on conflict (achievement_key) do nothing;
insert into public.achievement_definitions(achievement_key,xp_reward,gold_reward) values ('Sport Legend',1000,400) on conflict (achievement_key) do nothing;
insert into public.achievement_definitions(achievement_key,xp_reward,gold_reward) values ('Sport Streak 7',150,60) on conflict (achievement_key) do nothing;
insert into public.achievement_definitions(achievement_key,xp_reward,gold_reward) values ('Saver',150,75) on conflict (achievement_key) do nothing;
insert into public.achievement_definitions(achievement_key,xp_reward,gold_reward) values ('Rich Player',600,300) on conflict (achievement_key) do nothing;
insert into public.achievement_definitions(achievement_key,xp_reward,gold_reward) values ('Big Spender',300,100) on conflict (achievement_key) do nothing;
insert into public.achievement_definitions(achievement_key,xp_reward,gold_reward) values ('Pet Lover',80,30) on conflict (achievement_key) do nothing;
insert into public.achievement_definitions(achievement_key,xp_reward,gold_reward) values ('Pet Collector',200,80) on conflict (achievement_key) do nothing;
insert into public.achievement_definitions(achievement_key,xp_reward,gold_reward) values ('Pet Master',400,150) on conflict (achievement_key) do nothing;
insert into public.achievement_definitions(achievement_key,xp_reward,gold_reward) values ('Guild Member',150,75) on conflict (achievement_key) do nothing;
insert into public.achievement_definitions(achievement_key,xp_reward,gold_reward) values ('Boss Slayer',300,100) on conflict (achievement_key) do nothing;
insert into public.achievement_definitions(achievement_key,xp_reward,gold_reward) values ('Boss Hunter',600,250) on conflict (achievement_key) do nothing;
insert into public.achievement_definitions(achievement_key,xp_reward,gold_reward) values ('Friendly',80,30) on conflict (achievement_key) do nothing;
insert into public.achievement_definitions(achievement_key,xp_reward,gold_reward) values ('Popular',200,80) on conflict (achievement_key) do nothing;
insert into public.achievement_definitions(achievement_key,xp_reward,gold_reward) values ('Health Tracker',150,60) on conflict (achievement_key) do nothing;
insert into public.achievement_definitions(achievement_key,xp_reward,gold_reward) values ('Calorie Master',200,80) on conflict (achievement_key) do nothing;
insert into public.achievement_definitions(achievement_key,xp_reward,gold_reward) values ('Hydration Hero',250,100) on conflict (achievement_key) do nothing;
insert into public.achievement_definitions(achievement_key,xp_reward,gold_reward) values ('Completionist',2500,1000) on conflict (achievement_key) do nothing;
insert into public.achievement_definitions(achievement_key,xp_reward,gold_reward) values ('All-Rounder',1500,600) on conflict (achievement_key) do nothing;
insert into public.achievement_definitions(achievement_key,xp_reward,gold_reward) values ('Explorer',300,100) on conflict (achievement_key) do nothing;
insert into public.achievement_definitions(achievement_key,xp_reward,gold_reward) values ('Gym Rat',400,150) on conflict (achievement_key) do nothing;
insert into public.achievement_definitions(achievement_key,xp_reward,gold_reward) values ('Millionaire',1000,500) on conflict (achievement_key) do nothing;
insert into public.achievement_definitions(achievement_key,xp_reward,gold_reward) values ('Shopaholic',500,200) on conflict (achievement_key) do nothing;
insert into public.achievement_definitions(achievement_key,xp_reward,gold_reward) values ('Pet Breeder',500,250) on conflict (achievement_key) do nothing;
insert into public.achievement_definitions(achievement_key,xp_reward,gold_reward) values ('Boss Slayer Elite',1000,400) on conflict (achievement_key) do nothing;
insert into public.achievement_definitions(achievement_key,xp_reward,gold_reward) values ('Social Butterfly',300,150) on conflict (achievement_key) do nothing;
insert into public.achievement_definitions(achievement_key,xp_reward,gold_reward) values ('Health Nut',500,200) on conflict (achievement_key) do nothing;
insert into public.achievement_definitions(achievement_key,xp_reward,gold_reward) values ('Calorie Crusher',600,250) on conflict (achievement_key) do nothing;
insert into public.achievement_definitions(achievement_key,xp_reward,gold_reward) values ('Hydration Champion',600,250) on conflict (achievement_key) do nothing;
insert into public.achievement_definitions(achievement_key,xp_reward,gold_reward) values ('Focus Sprout',80,30) on conflict (achievement_key) do nothing;
insert into public.achievement_definitions(achievement_key,xp_reward,gold_reward) values ('Focus Warrior',300,120) on conflict (achievement_key) do nothing;
insert into public.achievement_definitions(achievement_key,xp_reward,gold_reward) values ('Time Bender',500,200) on conflict (achievement_key) do nothing;
insert into public.achievement_definitions(achievement_key,xp_reward,gold_reward) values ('Smith Apprentice',150,60) on conflict (achievement_key) do nothing;
insert into public.achievement_definitions(achievement_key,xp_reward,gold_reward) values ('Master Forger',400,180) on conflict (achievement_key) do nothing;
insert into public.achievement_definitions(achievement_key,xp_reward,gold_reward) values ('Demigod',3000,1200) on conflict (achievement_key) do nothing;
insert into public.achievement_definitions(achievement_key,xp_reward,gold_reward) values ('Streak Immortal',1500,500) on conflict (achievement_key) do nothing;
insert into public.achievement_definitions(achievement_key,xp_reward,gold_reward) values ('Daily Legend',600,250) on conflict (achievement_key) do nothing;
insert into public.achievement_definitions(achievement_key,xp_reward,gold_reward) values ('Quest Overlord',500,200) on conflict (achievement_key) do nothing;
insert into public.achievement_definitions(achievement_key,xp_reward,gold_reward) values ('Boss Terminator',1800,700) on conflict (achievement_key) do nothing;
insert into public.achievement_definitions(achievement_key,xp_reward,gold_reward) values ('Gold Emperor',2000,800) on conflict (achievement_key) do nothing;
insert into public.achievement_definitions(achievement_key,xp_reward,gold_reward) values ('Task Machine',3000,1500) on conflict (achievement_key) do nothing;
insert into public.achievement_definitions(achievement_key,xp_reward,gold_reward) values ('Habit God',1200,500) on conflict (achievement_key) do nothing;
insert into public.achievement_definitions(achievement_key,xp_reward,gold_reward) values ('Daily God',1200,500) on conflict (achievement_key) do nothing;
insert into public.achievement_definitions(achievement_key,xp_reward,gold_reward) values ('Sport God',1500,600) on conflict (achievement_key) do nothing;
insert into public.achievement_definitions(achievement_key,xp_reward,gold_reward) values ('Gold Titan',3000,1200) on conflict (achievement_key) do nothing;
insert into public.achievement_definitions(achievement_key,xp_reward,gold_reward) values ('Pet God',800,400) on conflict (achievement_key) do nothing;
insert into public.achievement_definitions(achievement_key,xp_reward,gold_reward) values ('Boss Emperor',2500,1000) on conflict (achievement_key) do nothing;
insert into public.achievement_definitions(achievement_key,xp_reward,gold_reward) values ('Social King',600,300) on conflict (achievement_key) do nothing;
insert into public.achievement_definitions(achievement_key,xp_reward,gold_reward) values ('Focus Overlord',800,400) on conflict (achievement_key) do nothing;
insert into public.achievement_definitions(achievement_key,xp_reward,gold_reward) values ('Craft Legend',800,350) on conflict (achievement_key) do nothing;
