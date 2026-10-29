-- Fix M09a — rapikan variabel loop spin_pet_cloud (peringatan lint).
--
-- `supabase db lint --linked` melaporkan variabel `i` di spin_pet_cloud
-- "shadows a previously defined variable" + "unused variable": `i`
-- dideklarasikan di blok DECLARE sekaligus menjadi variabel loop FOR,
-- padahal variabel loop PL/pgSQL terdeklarasi sendiri. Fungsi di bawah
-- sama persis dengan versi 20261022000000, hanya deklarasi `i integer;`
-- yang dibuang dan variabel loop diganti nama menjadi v_i. Semantik
-- undian (odds, pity, dupe EXP, kunci idempotensi) tidak berubah sama
-- sekali. Migrasi lama sudah terpasang dan tidak disunting.

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
  for v_i in 1..6 loop
    v_acc := v_acc + v_odds[v_i];
    if v_roll <= v_acc then v_rank := v_ranks[v_i]; v_idx := v_i; exit; end if;
  end loop;

  if v_floor is not null then
    v_floor_idx := array_position(v_ranks, v_floor);
    if v_idx < v_floor_idx then
      -- Paksa acak di antara rank >= lantai dengan bobot relatifnya.
      v_total := 0;
      for v_i in v_floor_idx..6 loop v_total := v_total + v_odds[v_i]; end loop;
      v_roll := random() * v_total;
      v_acc := 0;
      for v_i in v_floor_idx..6 loop
        v_acc := v_acc + v_odds[v_i];
        if v_roll <= v_acc then v_rank := v_ranks[v_i]; v_idx := v_i; exit; end if;
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
