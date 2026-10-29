-- Fix M09b — pembagian integer SQL memakai div(), bukan operator Python.
--
-- Tiga fungsi dari migrasi 20261022010000 memakai `//` (operator floor
-- division Python) yang tidak dikenal Postgres ("operator does not exist:
-- integer // integer", terlihat lewat `supabase db lint --linked`).
-- Migrasi lama sudah terpasang dan tidak disunting (UPDATE_RULES section
-- 6); fungsi-fungsi di bawah diganti utuh dengan isi yang sama persis,
-- hanya operator pembagiannya yang dibetulkan. Semantiknya identik:
-- div(a, b) untuk integer positif adalah floor division yang sama, dan
-- v_cnt sudah dijepit greatest(1, ...) sehingga tidak ada bagi-nol.
--
-- Fungsi yang diganti: unlock_talent_cloud, fetch_cloud_talents,
-- claim_boss_reward_cloud. Peringatan lint lain (variabel loop "i" di
-- spin_pet_cloud) hanya warning kosmetik dan tidak diubah.

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
      'points_left', greatest(0, div(coalesce(v_level,1), 5) - v_spent));
  end if;
  select coalesce(level,1) into v_level from public.user_cloud_wallets where user_id = uid;
  v_level := coalesce(v_level, 1);
  v_earned := div(v_level, 5);
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
    'points', greatest(0, div(coalesce(v_level,1), 5) - v_spent), 'spent', v_spent);
end; $$;

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
  -- Pembagian integer yang sama seperti attack_boss lokal (div cnt).
  v_xp := div(def.xp, v_cnt);
  v_gold := div(def.gold, v_cnt);
  insert into public.cloud_boss_reward_claims(user_id, boss_key, member_count, xp_reward, gold_reward, idempotency_key)
  values (uid, p_boss_key, v_cnt, v_xp, v_gold, p_idem);
  if v_xp <> 0 or v_gold <> 0 then
    insert into public.reward_ledger(user_id, source, ref_key, delta_xp, delta_gold, idempotency_key)
    values (uid, 'boss_local', p_boss_key, v_xp, v_gold, 'boss:' || p_idem);
  end if;
  return jsonb_build_object('ok', true, 'replay', false, 'boss_key', p_boss_key,
    'xp_reward', v_xp, 'gold_reward', v_gold);
end; $$;
