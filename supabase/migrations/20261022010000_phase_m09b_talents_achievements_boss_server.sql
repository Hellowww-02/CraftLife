-- Phase M09b — Talents, achievements, boss rewards server-authoritative.
--
-- Melanjutkan M09a dengan pola yang sama (Kanal C: perintah dikirim sebagai
-- RPC/queue, client hanya menampilkan hasil; angka dari katalog server).
--
-- 1) SUMBER LEDGER: M09a memperkenalkan source 'pet_spin' lewat spend_gold,
--    dan klaim boss lokal di sini memakai 'boss_local'. Keduanya belum ada
--    di constraint reward_ledger_source_check (terakhir diubah Phase 5B),
--    jadi constraint diperluas lebih dulu — tanpa ini spin M09a akan
--    ditolak Postgres pada runtime.
-- 2) TALENTS: katalog talents_server (seed TALENTS desktop) +
--    cloud_user_talents + unlock_talent_cloud yang memvalidasi class
--    (profiles.avatar_class), level dompet, poin (level//5 - terpakai),
--    syarat level tier (tier*5), dan prasyarat tier — aturan yang sama
--    persis dengan can_unlock_talent lokal. Poin tidak disimpan: ia
--    diturunkan dari level + jumlah unlock, jadi dua device selalu sepakat.
-- 3) ACHIEVEMENTS: cloud_user_achievements menjadi buku catatan server.
--    claim_achievement_reward_cloud (Phase 5A) diganti versinya di sini:
--    klaim kini mensyaratkan catatan unlock di server dan menandai
--    claimed_at. Angka reward tetap dari achievement_definitions.
-- 4) BOSS (lokal): bosses_server (seed BOSSES desktop) +
--    claim_boss_reward_cloud. XP/gold dihitung server dari katalog dibagi
--    jumlah member (pembagian yang sama seperti attack_boss lokal);
--    client hanya mengirim boss_key + member_count + idempotency key,
--    dan satu key hanya bisa diklaim sekali. Jumlah member untuk guild
--    LOKAL memang dilaporkan client (guild lokal tidak ada di server) —
--    batas yang dicatat apa adanya; boss guild cloud sudah otoritatif
--    penuh sejak Phase 4C dan tidak diubah.
--
-- Pengguna local-only tidak tersentuh; migrasi cloud selalu opsional
-- (UPDATE_RULES §6).

-- M09b-0: perluaskan sumber ledger (menutup source M09a + klaim boss lokal)
alter table public.reward_ledger drop constraint if exists reward_ledger_source_check;
alter table public.reward_ledger add constraint reward_ledger_source_check
  check (source in ('productivity','pvp','guild_boss','achievement','quest',
                    'shop_refund','shop_purchase','craft_spend','admin_adjustment',
                    'pet_spin','boss_local'));

-- M09b-1: katalog talent & boss (seed dari TALENTS/BOSSES desktop)
create table if not exists public.talents_server (
  talent_key text primary key,
  class text not null,
  tier integer not null check (tier between 1 and 3)
);
create table if not exists public.bosses_server (
  boss_key text primary key,
  name text not null,
  tier text not null,
  xp integer not null default 0,
  gold integer not null default 0
);
insert into public.talents_server(talent_key,class,tier) values ('archer_t1_keen','archer',1) on conflict (talent_key) do nothing;
insert into public.talents_server(talent_key,class,tier) values ('archer_t1_scout','archer',1) on conflict (talent_key) do nothing;
insert into public.talents_server(talent_key,class,tier) values ('archer_t2_quiver','archer',2) on conflict (talent_key) do nothing;
insert into public.talents_server(talent_key,class,tier) values ('archer_t2_tracker','archer',2) on conflict (talent_key) do nothing;
insert into public.talents_server(talent_key,class,tier) values ('archer_t3_deadeye','archer',3) on conflict (talent_key) do nothing;
insert into public.talents_server(talent_key,class,tier) values ('archer_t3_ranger','archer',3) on conflict (talent_key) do nothing;
insert into public.talents_server(talent_key,class,tier) values ('healer_t1_bless','healer',1) on conflict (talent_key) do nothing;
insert into public.talents_server(talent_key,class,tier) values ('healer_t1_medic','healer',1) on conflict (talent_key) do nothing;
insert into public.talents_server(talent_key,class,tier) values ('healer_t2_charity','healer',2) on conflict (talent_key) do nothing;
insert into public.talents_server(talent_key,class,tier) values ('healer_t2_prayer','healer',2) on conflict (talent_key) do nothing;
insert into public.talents_server(talent_key,class,tier) values ('healer_t3_guard','healer',3) on conflict (talent_key) do nothing;
insert into public.talents_server(talent_key,class,tier) values ('healer_t3_holy','healer',3) on conflict (talent_key) do nothing;
insert into public.talents_server(talent_key,class,tier) values ('mage_t1_mana','mage',1) on conflict (talent_key) do nothing;
insert into public.talents_server(talent_key,class,tier) values ('mage_t1_mind','mage',1) on conflict (talent_key) do nothing;
insert into public.talents_server(talent_key,class,tier) values ('mage_t2_alch','mage',2) on conflict (talent_key) do nothing;
insert into public.talents_server(talent_key,class,tier) values ('mage_t2_flow','mage',2) on conflict (talent_key) do nothing;
insert into public.talents_server(talent_key,class,tier) values ('mage_t3_arch','mage',3) on conflict (talent_key) do nothing;
insert into public.talents_server(talent_key,class,tier) values ('mage_t3_hex','mage',3) on conflict (talent_key) do nothing;
insert into public.talents_server(talent_key,class,tier) values ('rogue_t1_nimble','rogue',1) on conflict (talent_key) do nothing;
insert into public.talents_server(talent_key,class,tier) values ('rogue_t1_pick','rogue',1) on conflict (talent_key) do nothing;
insert into public.talents_server(talent_key,class,tier) values ('rogue_t2_loot','rogue',2) on conflict (talent_key) do nothing;
insert into public.talents_server(talent_key,class,tier) values ('rogue_t2_shadow','rogue',2) on conflict (talent_key) do nothing;
insert into public.talents_server(talent_key,class,tier) values ('rogue_t3_assassin','rogue',3) on conflict (talent_key) do nothing;
insert into public.talents_server(talent_key,class,tier) values ('rogue_t3_phantom','rogue',3) on conflict (talent_key) do nothing;
insert into public.talents_server(talent_key,class,tier) values ('warrior_t1_rage','warrior',1) on conflict (talent_key) do nothing;
insert into public.talents_server(talent_key,class,tier) values ('warrior_t1_skin','warrior',1) on conflict (talent_key) do nothing;
insert into public.talents_server(talent_key,class,tier) values ('warrior_t2_chest','warrior',2) on conflict (talent_key) do nothing;
insert into public.talents_server(talent_key,class,tier) values ('warrior_t2_veteran','warrior',2) on conflict (talent_key) do nothing;
insert into public.talents_server(talent_key,class,tier) values ('warrior_t3_jugg','warrior',3) on conflict (talent_key) do nothing;
insert into public.talents_server(talent_key,class,tier) values ('warrior_t3_slayer','warrior',3) on conflict (talent_key) do nothing;
insert into public.bosses_server(boss_key,name,tier,xp,gold) values ('blaze_lord','Blaze Lord','normal',300,70) on conflict (boss_key) do nothing;
insert into public.bosses_server(boss_key,name,tier,xp,gold) values ('creeper','Creeper','beginner',100,25) on conflict (boss_key) do nothing;
insert into public.bosses_server(boss_key,name,tier,xp,gold) values ('creeper_god','Creeper God','hard',700,180) on conflict (boss_key) do nothing;
insert into public.bosses_server(boss_key,name,tier,xp,gold) values ('elder_guardian','Elder Guardian','legendary',3000,800) on conflict (boss_key) do nothing;
insert into public.bosses_server(boss_key,name,tier,xp,gold) values ('ender_dragon','Ender Dragon','elite',1500,400) on conflict (boss_key) do nothing;
insert into public.bosses_server(boss_key,name,tier,xp,gold) values ('herobrine','Herobrine','legendary',5000,1500) on conflict (boss_key) do nothing;
insert into public.bosses_server(boss_key,name,tier,xp,gold) values ('iron_golem','Iron Golem Boss','hard',600,150) on conflict (boss_key) do nothing;
insert into public.bosses_server(boss_key,name,tier,xp,gold) values ('ketupat_golem','Ketupat Golem','seasonal',400,120) on conflict (boss_key) do nothing;
insert into public.bosses_server(boss_key,name,tier,xp,gold) values ('krampus','Krampus','seasonal',900,250) on conflict (boss_key) do nothing;
insert into public.bosses_server(boss_key,name,tier,xp,gold) values ('pumpkin_king','Pumpkin King','seasonal',600,160) on conflict (boss_key) do nothing;
insert into public.bosses_server(boss_key,name,tier,xp,gold) values ('skeleton','Skeleton Archer','beginner',120,30) on conflict (boss_key) do nothing;
insert into public.bosses_server(boss_key,name,tier,xp,gold) values ('skeleton_lord','Skeleton Lord','normal',350,80) on conflict (boss_key) do nothing;
insert into public.bosses_server(boss_key,name,tier,xp,gold) values ('spider_queen','Spider Queen','hard',500,120) on conflict (boss_key) do nothing;
insert into public.bosses_server(boss_key,name,tier,xp,gold) values ('wither','The Wither','elite',1200,300) on conflict (boss_key) do nothing;
insert into public.bosses_server(boss_key,name,tier,xp,gold) values ('zombie','Zombie','beginner',80,20) on conflict (boss_key) do nothing;
insert into public.bosses_server(boss_key,name,tier,xp,gold) values ('zombie_king','Zombie King','normal',250,60) on conflict (boss_key) do nothing;

-- M09b-2: talent yang sudah dibuka per pengguna cloud
create table if not exists public.cloud_user_talents (
  user_id uuid not null references public.profiles(id) on delete cascade,
  talent_key text not null references public.talents_server(talent_key),
  unlocked_at timestamptz not null default now(),
  primary key (user_id, talent_key)
);

-- M09b-3: unlock talent otoritatif. Mengembalikan sisa poin resmi server.
create or replace function public.unlock_talent_cloud(p_talent_key text)
returns jsonb language plpgsql security definer set search_path=public as $$
declare
  uid uuid := auth.uid();
  def public.talents_server;
  v_class text;
  v_level integer := 1;
  v_earned integer;
  v_spent integer;
begin
  if uid is null then raise exception 'not_authenticated'; end if;
  if not public.current_profile_active() then raise exception 'account_unavailable'; end if;
  select * into def from public.talents_server where talent_key = p_talent_key;
  if not found then raise exception 'unknown_talent'; end if;
  select avatar_class into v_class from public.profiles where id = uid;
  if v_class is distinct from def.class then raise exception 'talent_class_mismatch'; end if;
  if exists(select 1 from public.cloud_user_talents
             where user_id = uid and talent_key = p_talent_key) then
    select count(*) into v_spent from public.cloud_user_talents where user_id = uid;
    select coalesce(level,1) into v_level from public.user_cloud_wallets where user_id = uid;
    return jsonb_build_object('ok', true, 'replay', true, 'talent_key', p_talent_key,
      'points_left', greatest(0, (coalesce(v_level,1) // 5) - v_spent));
  end if;
  select coalesce(level,1) into v_level from public.user_cloud_wallets where user_id = uid;
  v_level := coalesce(v_level, 1);
  v_earned := v_level // 5;
  select count(*) into v_spent from public.cloud_user_talents where user_id = uid;
  if v_earned - v_spent <= 0 then raise exception 'talent_no_points'; end if;
  if v_level < def.tier * 5 then raise exception 'talent_level_required'; end if;
  if def.tier > 1 and not exists(
       select 1 from public.cloud_user_talents cut
       join public.talents_server ts on ts.talent_key = cut.talent_key
        where cut.user_id = uid and ts.class = def.class and ts.tier = def.tier - 1)
  then raise exception 'talent_prereq_required'; end if;
  insert into public.cloud_user_talents(user_id, talent_key) values (uid, p_talent_key);
  return jsonb_build_object('ok', true, 'replay', false, 'talent_key', p_talent_key,
    'points_left', v_earned - v_spent - 1);
end; $$;

create or replace function public.fetch_cloud_talents()
returns jsonb language plpgsql stable security definer set search_path=public as $$
declare
  uid uuid := auth.uid();
  v_class text;
  v_level integer := 1;
  v_spent integer := 0;
  v_keys jsonb;
begin
  if uid is null then raise exception 'not_authenticated'; end if;
  select avatar_class into v_class from public.profiles where id = uid;
  select coalesce(level,1) into v_level from public.user_cloud_wallets where user_id = uid;
  select count(*) into v_spent from public.cloud_user_talents where user_id = uid;
  select coalesce(jsonb_agg(talent_key order by talent_key), '[]'::jsonb)
    into v_keys from public.cloud_user_talents where user_id = uid;
  return jsonb_build_object('talents', v_keys, 'class', v_class,
    'level', coalesce(v_level,1),
    'points', greatest(0, (coalesce(v_level,1) // 5) - v_spent), 'spent', v_spent);
end; $$;

-- M09b-4: buku catatan achievement server
create table if not exists public.cloud_user_achievements (
  user_id uuid not null references public.profiles(id) on delete cascade,
  achievement_key text not null references public.achievement_definitions(achievement_key),
  unlocked_at timestamptz not null default now(),
  claimed_at timestamptz,
  primary key (user_id, achievement_key)
);

create or replace function public.record_achievement_unlock_cloud(p_key text)
returns jsonb language plpgsql security definer set search_path=public as $$
declare uid uuid := auth.uid();
begin
  if uid is null then raise exception 'not_authenticated'; end if;
  if not public.current_profile_active() then raise exception 'account_unavailable'; end if;
  if not exists(select 1 from public.achievement_definitions where achievement_key = p_key)
  then raise exception 'unknown_achievement'; end if;
  insert into public.cloud_user_achievements(user_id, achievement_key)
  values (uid, p_key) on conflict (user_id, achievement_key) do nothing;
  return jsonb_build_object('ok', true, 'achievement_key', p_key);
end; $$;

-- M09b-5: klaim achievement kini mensyaratkan catatan unlock server.
-- Badan fungsi sama dengan Phase 5A ditambah dua hal itu (angka reward
-- tetap dari achievement_definitions; idempotency & already-claimed utuh).
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
  if not exists(select 1 from public.cloud_user_achievements
                 where cloud_user_achievements.user_id = auth.uid()
                   and cloud_user_achievements.achievement_key = ak)
  then raise exception 'achievement_not_unlocked'; end if;
  insert into public.reward_ledger(user_id, source, ref_key, delta_xp, delta_gold, delta_gems, idempotency_key)
  values (auth.uid(), 'achievement', ak, def.xp_reward, def.gold_reward, def.gems_reward, ck)
  returning * into res;
  update public.cloud_user_achievements set claimed_at = now()
   where cloud_user_achievements.user_id = auth.uid()
     and cloud_user_achievements.achievement_key = ak;
  return res;
end; $$;

-- M09b-6: klaim reward boss lokal. Angka dari katalog server.
create table if not exists public.cloud_boss_reward_claims (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references public.profiles(id) on delete cascade,
  boss_key text not null,
  member_count integer not null,
  xp_reward integer not null default 0,
  gold_reward integer not null default 0,
  idempotency_key text not null,
  created_at timestamptz not null default now(),
  unique (user_id, idempotency_key)
);

create or replace function public.claim_boss_reward_cloud(p_boss_key text, p_member_count integer, p_idem text)
returns jsonb language plpgsql security definer set search_path=public as $$
declare
  uid uuid := auth.uid();
  def public.bosses_server;
  prev public.cloud_boss_reward_claims;
  v_cnt integer;
  v_xp integer;
  v_gold integer;
begin
  if uid is null then raise exception 'not_authenticated'; end if;
  if not public.current_profile_active() then raise exception 'account_unavailable'; end if;
  if p_idem is null or length(trim(p_idem)) = 0 then raise exception 'missing_idempotency_key'; end if;
  select * into prev from public.cloud_boss_reward_claims
   where user_id = uid and idempotency_key = p_idem;
  if found then
    return jsonb_build_object('ok', true, 'replay', true, 'boss_key', prev.boss_key,
      'xp_reward', prev.xp_reward, 'gold_reward', prev.gold_reward);
  end if;
  select * into def from public.bosses_server where boss_key = p_boss_key;
  if not found then raise exception 'unknown_boss'; end if;
  v_cnt := greatest(1, least(coalesce(p_member_count, 1), 100));
  -- Pembagian integer yang sama seperti attack_boss lokal (// cnt).
  v_xp := def.xp // v_cnt;
  v_gold := def.gold // v_cnt;
  insert into public.cloud_boss_reward_claims(user_id, boss_key, member_count, xp_reward, gold_reward, idempotency_key)
  values (uid, p_boss_key, v_cnt, v_xp, v_gold, p_idem);
  if v_xp <> 0 or v_gold <> 0 then
    insert into public.reward_ledger(user_id, source, ref_key, delta_xp, delta_gold, idempotency_key)
    values (uid, 'boss_local', p_boss_key, v_xp, v_gold, 'boss:' || p_idem);
  end if;
  return jsonb_build_object('ok', true, 'replay', false, 'boss_key', p_boss_key,
    'xp_reward', v_xp, 'gold_reward', v_gold);
end; $$;

alter table public.talents_server enable row level security;
create policy talents_server_read on public.talents_server
  for select to authenticated using (true);
alter table public.bosses_server enable row level security;
create policy bosses_server_read on public.bosses_server
  for select to authenticated using (true);
alter table public.cloud_user_talents enable row level security;
create policy cloud_user_talents_select_own on public.cloud_user_talents
  for select to authenticated using (user_id = auth.uid());
alter table public.cloud_user_achievements enable row level security;
create policy cloud_user_achievements_select_own on public.cloud_user_achievements
  for select to authenticated using (user_id = auth.uid());
alter table public.cloud_boss_reward_claims enable row level security;
create policy cloud_boss_reward_claims_select_own on public.cloud_boss_reward_claims
  for select to authenticated using (user_id = auth.uid());

revoke insert, update, delete on public.talents_server from authenticated, anon, public;
revoke insert, update, delete on public.bosses_server from authenticated, anon, public;
revoke insert, update, delete on public.cloud_user_talents from authenticated, anon, public;
revoke insert, update, delete on public.cloud_user_achievements from authenticated, anon, public;
revoke insert, update, delete on public.cloud_boss_reward_claims from authenticated, anon, public;
revoke execute on function public.unlock_talent_cloud(text) from public, anon;
revoke execute on function public.fetch_cloud_talents() from public, anon;
revoke execute on function public.record_achievement_unlock_cloud(text) from public, anon;
revoke execute on function public.claim_boss_reward_cloud(text, integer, text) from public, anon;
grant execute on function public.unlock_talent_cloud(text) to authenticated;
grant execute on function public.fetch_cloud_talents() to authenticated;
grant execute on function public.record_achievement_unlock_cloud(text) to authenticated;
grant execute on function public.claim_boss_reward_cloud(text, integer, text) to authenticated;
