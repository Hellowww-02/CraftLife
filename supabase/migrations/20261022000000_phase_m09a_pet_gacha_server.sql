-- Phase M09a — Pet gacha server-authoritative (K13).
--
-- Masalah yang ditutup: spin gacha pet selama ini diundi dan dibukukan oleh
-- client (SQLite lokal `spin_pet` di database.py). Untuk pengguna cloud-linked
-- itu berarti dua device bisa mengundi sendiri-sendiri: koleksi dan saldo
-- gold bisa berbeda antar device, dan client yang dimodifikasi bisa
-- mengarang hasil.
--
-- Migrasi ini memindahkan keputusan spin ke server mengikuti pola Phase 5A/5B
-- yang sudah terbukti (reward_ledger + spend_gold + idempotency key):
--   * `pets_server`          katalog pet versi server (seed dari PETS_DATA desktop).
--   * `cloud_user_pets`      koleksi otoritatif per pengguna cloud.
--   * `cloud_pet_spin_state` penghitung pity otoritatif per pengguna.
--   * `cloud_pet_spins`      log spin; unique(user_id, idempotency_key) membuat
--                            pengiriman ulang aman (hasil pertama diputar ulang).
--   * `spin_pet_cloud`       RPC: peluang + pity dihitung server, gold dipotong
--                            lewat ledger, duplikat -> EXP (aturan K2 yang sama).
--   * `fetch_cloud_pets`     RPC baca koleksi + state sendiri untuk dicerminkan
--                            ke cache lokal client.
--
-- Konstanta disalin PERSIS dari database.py: SPIN_COST=120,
-- SPIN_ODDS common 34 / rare 26 / epic 18 / legendary 12 / mythic 8 / secret 2,
-- PITY_EPIC=10, PITY_LEGENDARY=30, SPIN_DUPE_EXP_RATIO=0.5 (60 EXP),
-- level-up pet: butuh level*100 EXP (add_pet_exp).
-- Satu penyelarasan yang disengaja: pada spin PERTAMA seumur hidup, jalur
-- INSERT lokal lama menulis since_* = 1 walau rank-nya kena pity floor;
-- di sini dipakai semantik jalur UPDATE lokal (0 bila kena), yang juga yang
-- dipakai semua spin berikutnya.
--
-- Pengguna local-only TIDAK tersentuh: tanpa migrasi ini pun aplikasi lokal
-- berjalan seperti sebelumnya (spin lokal di SQLite). Migrasi cloud selalu
-- opsional (UPDATE_RULES §6).

create table if not exists public.pets_server (
  pet_key text primary key,
  name text not null,
  name_id text not null default '',
  icon text not null default '',
  rank text not null,
  cost integer not null default 0
);

create table if not exists public.cloud_user_pets (
  user_id uuid not null references public.profiles(id) on delete cascade,
  pet_key text not null references public.pets_server(pet_key),
  level integer not null default 1,
  exp integer not null default 0,
  hunger integer not null default 100,
  happiness integer not null default 50,
  is_active boolean not null default false,
  obtained_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  primary key (user_id, pet_key)
);

create table if not exists public.cloud_pet_spin_state (
  user_id uuid primary key references public.profiles(id) on delete cascade,
  spins_total integer not null default 0,
  since_epic integer not null default 0,
  since_legendary integer not null default 0,
  updated_at timestamptz not null default now()
);

create table if not exists public.cloud_pet_spins (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references public.profiles(id) on delete cascade,
  idempotency_key text not null,
  pet_key text not null,
  rank text not null,
  is_new boolean not null,
  dupe_exp integer not null default 0,
  cost integer not null,
  created_at timestamptz not null default now(),
  unique (user_id, idempotency_key)
);

-- Seed katalog (39 pet, dihasilkan dari PETS_DATA di database.py).
insert into public.pets_server(pet_key,name,name_id,icon,rank,cost) values ('axolotl','Axolotl','Axolotl','🦎','rare',200) on conflict (pet_key) do nothing;
insert into public.pets_server(pet_key,name,name_id,icon,rank,cost) values ('basilisk','Basilisk','Basilisk','🐍','mythic',850) on conflict (pet_key) do nothing;
insert into public.pets_server(pet_key,name,name_id,icon,rank,cost) values ('bat','Bat','Kelelawar','🦇','rare',160) on conflict (pet_key) do nothing;
insert into public.pets_server(pet_key,name,name_id,icon,rank,cost) values ('bee','Bee','Lebah','🐝','common',110) on conflict (pet_key) do nothing;
insert into public.pets_server(pet_key,name,name_id,icon,rank,cost) values ('capybara','Capybara','Kapibara','🦫','rare',180) on conflict (pet_key) do nothing;
insert into public.pets_server(pet_key,name,name_id,icon,rank,cost) values ('cat','Cat','Kucing','🐱','common',120) on conflict (pet_key) do nothing;
insert into public.pets_server(pet_key,name,name_id,icon,rank,cost) values ('chick','Chick','Anak Ayam','🐤','common',90) on conflict (pet_key) do nothing;
insert into public.pets_server(pet_key,name,name_id,icon,rank,cost) values ('creeper','Creeper','Creeper','💥','common',90) on conflict (pet_key) do nothing;
insert into public.pets_server(pet_key,name,name_id,icon,rank,cost) values ('dolphin','Dolphin','Lumba-lumba','🐬','epic',300) on conflict (pet_key) do nothing;
insert into public.pets_server(pet_key,name,name_id,icon,rank,cost) values ('dragon','Dragon','Naga','🐉','legendary',600) on conflict (pet_key) do nothing;
insert into public.pets_server(pet_key,name,name_id,icon,rank,cost) values ('enderman','Enderman','Enderman','👾','epic',400) on conflict (pet_key) do nothing;
insert into public.pets_server(pet_key,name,name_id,icon,rank,cost) values ('fox','Fox','Rubah','🦊','rare',180) on conflict (pet_key) do nothing;
insert into public.pets_server(pet_key,name,name_id,icon,rank,cost) values ('ghast','Ghast','Ghast','👻','common',150) on conflict (pet_key) do nothing;
insert into public.pets_server(pet_key,name,name_id,icon,rank,cost) values ('griffin','Griffin','Griffin','🦅','legendary',700) on conflict (pet_key) do nothing;
insert into public.pets_server(pet_key,name,name_id,icon,rank,cost) values ('hamster','Hamster','Hamster','🐹','common',95) on conflict (pet_key) do nothing;
insert into public.pets_server(pet_key,name,name_id,icon,rank,cost) values ('hedgehog','Hedgehog','Landak','🦔','rare',190) on conflict (pet_key) do nothing;
insert into public.pets_server(pet_key,name,name_id,icon,rank,cost) values ('kangaroo','Kangaroo','Kanguru','🦘','epic',460) on conflict (pet_key) do nothing;
insert into public.pets_server(pet_key,name,name_id,icon,rank,cost) values ('kirin','Kirin','Kirin','🦌','mythic',900) on conflict (pet_key) do nothing;
insert into public.pets_server(pet_key,name,name_id,icon,rank,cost) values ('lion','Lion','Singa','🦁','epic',550) on conflict (pet_key) do nothing;
insert into public.pets_server(pet_key,name,name_id,icon,rank,cost) values ('luminara','Luminara','Luminara','🦢','secret',1500) on conflict (pet_key) do nothing;
insert into public.pets_server(pet_key,name,name_id,icon,rank,cost) values ('mermaid','Mermaid','Putri Duyung','🧜‍♀️','epic',500) on conflict (pet_key) do nothing;
insert into public.pets_server(pet_key,name,name_id,icon,rank,cost) values ('orca','Orca','Paus Orca','🐋','legendary',680) on conflict (pet_key) do nothing;
insert into public.pets_server(pet_key,name,name_id,icon,rank,cost) values ('otter','Otter','Berang-berang','🦦','epic',380) on conflict (pet_key) do nothing;
insert into public.pets_server(pet_key,name,name_id,icon,rank,cost) values ('owl','Owl','Burung Hantu','🦉','rare',220) on conflict (pet_key) do nothing;
insert into public.pets_server(pet_key,name,name_id,icon,rank,cost) values ('panda','Panda','Panda','🐼','rare',240) on conflict (pet_key) do nothing;
insert into public.pets_server(pet_key,name,name_id,icon,rank,cost) values ('parrot','Parrot','Burung Beo','🦜','common',140) on conflict (pet_key) do nothing;
insert into public.pets_server(pet_key,name,name_id,icon,rank,cost) values ('peacock','Peacock','Merak','🦚','epic',420) on conflict (pet_key) do nothing;
insert into public.pets_server(pet_key,name,name_id,icon,rank,cost) values ('phoenix','Phoenix','Phoenix','🐦‍🔥','mythic',800) on conflict (pet_key) do nothing;
insert into public.pets_server(pet_key,name,name_id,icon,rank,cost) values ('rabbit','Rabbit','Kelinci','🐇','common',100) on conflict (pet_key) do nothing;
insert into public.pets_server(pet_key,name,name_id,icon,rank,cost) values ('raccoon','Raccoon','Rakun','🦝','rare',210) on conflict (pet_key) do nothing;
insert into public.pets_server(pet_key,name,name_id,icon,rank,cost) values ('skeleton','Skeleton','Tengkorak','💀','common',120) on conflict (pet_key) do nothing;
insert into public.pets_server(pet_key,name,name_id,icon,rank,cost) values ('slime','Slime','Slime','🟢','common',80) on conflict (pet_key) do nothing;
insert into public.pets_server(pet_key,name,name_id,icon,rank,cost) values ('snail','Snail','Siput','🐌','common',85) on conflict (pet_key) do nothing;
insert into public.pets_server(pet_key,name,name_id,icon,rank,cost) values ('tiger','Tiger','Harimau','🐅','legendary',720) on conflict (pet_key) do nothing;
insert into public.pets_server(pet_key,name,name_id,icon,rank,cost) values ('turtle','Turtle','Kura-kura','🐢','common',130) on conflict (pet_key) do nothing;
insert into public.pets_server(pet_key,name,name_id,icon,rank,cost) values ('unicorn','Unicorn','Unicorn','🦄','legendary',650) on conflict (pet_key) do nothing;
insert into public.pets_server(pet_key,name,name_id,icon,rank,cost) values ('void_dragon','Void Dragon','Naga Hampa','🐲','secret',1500) on conflict (pet_key) do nothing;
insert into public.pets_server(pet_key,name,name_id,icon,rank,cost) values ('wolf','Wolf','Serigala','🐺','common',150) on conflict (pet_key) do nothing;
insert into public.pets_server(pet_key,name,name_id,icon,rank,cost) values ('zombie','Zombie','Zombi','🧟','common',100) on conflict (pet_key) do nothing;

-- Spin otoritatif. Client hanya mengirim idempotency key; SEMUA angka
-- (biaya, peluang, pity, hasil, EXP duplikat) ditentukan di sini.
create or replace function public.spin_pet_cloud(p_idem text)
returns jsonb language plpgsql security definer set search_path=public as $$
declare
  uid uuid := auth.uid();
  prev public.cloud_pet_spins;
  st public.cloud_pet_spin_state;
  v_ranks text[] := array['common','rare','epic','legendary','mythic','secret'];
  v_odds double precision[] := array[34,26,18,12,8,2];
  v_cost integer := 120;
  v_dupe_exp integer := 60;
  v_floor text := null;
  v_rank text := 'common';
  v_idx integer := 1;
  v_floor_idx integer := 0;
  v_roll double precision;
  v_acc double precision := 0;
  v_total double precision := 0;
  v_pet text;
  owned public.cloud_user_pets;
  v_is_new boolean := false;
  v_level integer;
  v_exp integer;
  v_gold bigint;
  i integer;
begin
  if uid is null then raise exception 'not_authenticated'; end if;
  if not public.current_profile_active() then raise exception 'account_unavailable'; end if;
  if p_idem is null or length(trim(p_idem)) = 0 then raise exception 'missing_idempotency_key'; end if;

  -- Putar ulang: key yang sama tidak pernah mengundi atau memotong dua kali.
  select * into prev from public.cloud_pet_spins
   where user_id = uid and idempotency_key = p_idem;
  if found then
    return jsonb_build_object('ok', true, 'replay', true,
      'pet_id', prev.pet_key, 'rank', prev.rank, 'is_new', prev.is_new,
      'dupe_exp', prev.dupe_exp, 'cost', prev.cost);
  end if;

  -- Kunci baris state per pengguna: dua spin bersamaan dari dua device
  -- terserialisasi di sini, jadi pity tidak bisa diakali paralel.
  insert into public.cloud_pet_spin_state(user_id) values (uid)
  on conflict (user_id) do nothing;
  select * into st from public.cloud_pet_spin_state where user_id = uid for update;

  if st.since_legendary + 1 >= 30 then v_floor := 'legendary';
  elsif st.since_epic + 1 >= 10 then v_floor := 'epic';
  end if;

  v_roll := random() * 100;
  v_acc := 0;
  for i in 1..6 loop
    v_acc := v_acc + v_odds[i];
    if v_roll <= v_acc then v_rank := v_ranks[i]; v_idx := i; exit; end if;
  end loop;

  if v_floor is not null then
    v_floor_idx := array_position(v_ranks, v_floor);
    if v_idx < v_floor_idx then
      -- Paksa acak di antara rank >= lantai dengan bobot relatifnya.
      v_total := 0;
      for i in v_floor_idx..6 loop v_total := v_total + v_odds[i]; end loop;
      v_roll := random() * v_total;
      v_acc := 0;
      for i in v_floor_idx..6 loop
        v_acc := v_acc + v_odds[i];
        if v_roll <= v_acc then v_rank := v_ranks[i]; v_idx := i; exit; end if;
      end loop;
    end if;
  end if;

  select pet_key into v_pet from public.pets_server
   where rank = v_rank order by random() limit 1;
  if v_pet is null then
    -- Pengaman pool kosong: turun ke common seperti jalur lokal.
    v_rank := 'common'; v_idx := 1;
    select pet_key into v_pet from public.pets_server
     where rank = 'common' order by random() limit 1;
  end if;
  if v_pet is null then raise exception 'empty_pet_catalog'; end if;

  -- Potong gold lewat ledger (menaikkan insufficient_balance bila kurang).
  -- Sengaja SEBELUM pemberian pet: exception membatalkan seluruh transaksi.
  perform public.spend_gold(uid, v_cost, 'pet_spin', v_pet, 'petspin:' || p_idem);

  select * into owned from public.cloud_user_pets
   where user_id = uid and pet_key = v_pet;
  if found then
    -- K2: duplikat menjadi EXP latihan untuk pet yang sudah dimiliki.
    v_level := owned.level; v_exp := owned.exp + v_dupe_exp;
    while v_exp >= v_level * 100 loop
      v_exp := v_exp - v_level * 100; v_level := v_level + 1;
    end loop;
    update public.cloud_user_pets
       set exp = v_exp, level = v_level, updated_at = now()
     where user_id = uid and pet_key = v_pet;
  else
    v_is_new := true;
    insert into public.cloud_user_pets(user_id, pet_key) values (uid, v_pet);
  end if;

  update public.cloud_pet_spin_state set
    spins_total = spins_total + 1,
    since_epic = case when v_idx >= 3 then 0 else since_epic + 1 end,
    since_legendary = case when v_idx >= 4 then 0 else since_legendary + 1 end,
    updated_at = now()
  where user_id = uid returning * into st;

  insert into public.cloud_pet_spins(user_id, idempotency_key, pet_key, rank, is_new, dupe_exp, cost)
  values (uid, p_idem, v_pet, v_rank, v_is_new,
          case when v_is_new then 0 else v_dupe_exp end, v_cost);

  select gold into v_gold from public.user_cloud_wallets where user_id = uid;
  return jsonb_build_object('ok', true, 'replay', false,
    'pet_id', v_pet, 'rank', v_rank, 'is_new', v_is_new,
    'dupe_exp', case when v_is_new then 0 else v_dupe_exp end,
    'cost', v_cost, 'gold', coalesce(v_gold, 0),
    'spins_total', st.spins_total, 'since_epic', st.since_epic,
    'since_legendary', st.since_legendary);
end; $$;

-- Baca koleksi + state spin milik sendiri (untuk cermin cache client).
create or replace function public.fetch_cloud_pets()
returns jsonb language plpgsql stable security definer set search_path=public as $$
declare
  uid uuid := auth.uid();
  st public.cloud_pet_spin_state;
  v_pets jsonb;
begin
  if uid is null then raise exception 'not_authenticated'; end if;
  select coalesce(jsonb_agg(jsonb_build_object(
           'pet_key', pet_key, 'level', level, 'exp', exp,
           'hunger', hunger, 'happiness', happiness, 'is_active', is_active
         ) order by pet_key), '[]'::jsonb)
    into v_pets
    from public.cloud_user_pets where user_id = uid;
  select * into st from public.cloud_pet_spin_state where user_id = uid;
  return jsonb_build_object(
    'pets', v_pets,
    'spin_state', jsonb_build_object(
      'spins_total', coalesce(st.spins_total, 0),
      'since_epic', coalesce(st.since_epic, 0),
      'since_legendary', coalesce(st.since_legendary, 0)));
end; $$;

alter table public.pets_server enable row level security;
create policy pets_server_read on public.pets_server
  for select to authenticated using (true);
alter table public.cloud_user_pets enable row level security;
create policy cloud_user_pets_select_own on public.cloud_user_pets
  for select to authenticated using (user_id = auth.uid());
alter table public.cloud_pet_spin_state enable row level security;
create policy cloud_pet_spin_state_select_own on public.cloud_pet_spin_state
  for select to authenticated using (user_id = auth.uid());
alter table public.cloud_pet_spins enable row level security;
create policy cloud_pet_spins_select_own on public.cloud_pet_spins
  for select to authenticated using (user_id = auth.uid());

revoke insert, update, delete on public.pets_server from authenticated, anon, public;
revoke insert, update, delete on public.cloud_user_pets from authenticated, anon, public;
revoke insert, update, delete on public.cloud_pet_spin_state from authenticated, anon, public;
revoke insert, update, delete on public.cloud_pet_spins from authenticated, anon, public;
revoke execute on function public.spin_pet_cloud(text) from public, anon;
revoke execute on function public.fetch_cloud_pets() from public, anon;
grant execute on function public.spin_pet_cloud(text) to authenticated;
grant execute on function public.fetch_cloud_pets() to authenticated;
