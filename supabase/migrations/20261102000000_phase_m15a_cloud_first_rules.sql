-- M15a — Cloud-first: aturan main tracker di Postgres (port setia dari Python).
--
-- Tujuan (roadmap M15): HP <-> Supabase langsung tanpa PC. Aturan yang selama
-- ini dijalankan `database.py` dipindah ke sini APA ADANYA — angka harus
-- identik, dijaga tests/test_m15_rules_parity.py (rumus dieksekusi di dua
-- sisi) + scripts/m15_parity_live.py (bukti live RPC vs Python).
--
-- Sumber kebenaran perilaku: database.py pada commit M15
--   gain_xp_gold        L3526   lose_hp            L3594
--   penalize_gold       L3638   penalize_xp        L3657
--   complete_habit      L3902   complete_daily     L4060
--   fail_daily          L4098   add_freeze_to_daily L4189
--   complete_todo       L4278   complete_sport_activity L4607 (+gain_sport_points L4644)
--   complete_pomodoro   L13082  apply_late_debt_penalty L9040
--
-- Konvensi mengikuti migrasi M09 (lowercase, security definer, search_path
-- pinned, error code sebagai pesan exception, eksekusi hanya untuk
-- `authenticated`). Tidak ada migrasi lama yang disentuh — semua lewat
-- CREATE OR REPLACE / ALTER TABLE additive.
--
-- Keputusan desain yang tercatat:
--   * S4 (users vs user_cloud_wallets dual authority) DIBAYAR di sini: kurva
--     level dompet disamakan dengan desktop (threshold kumulatif 150*L*(L-1)/2,
--     bukan sqrt(xp/100) placeholder M05). Kolom `xp` dompet memang berperan
--     sebagai TOTAL xp (perilaku lama tetap), progress level dihitung dari
--     threshold — persis model Python (`xp` = sisa di level berjalan).
--   * Multiplier (pet/skill/admin) dibaca dari kolom baru di
--     `user_cloud_wallets` supaya aturan bisa identik; disinkronkan desktop.

-- ---------------------------------------------------------------------------
-- 1. Kolom aturan di dompet (additive)
-- ---------------------------------------------------------------------------
alter table public.user_cloud_wallets
  add column if not exists total_xp_earned bigint not null default 0,
  add column if not exists total_gold_earned bigint not null default 0,
  add column if not exists max_hp integer not null default 50,
  add column if not exists hp integer not null default 50,
  add column if not exists max_mp integer not null default 30,
  add column if not exists mp integer not null default 30,
  add column if not exists mp_bonus integer not null default 0,
  add column if not exists hp_damage_reduction numeric not null default 0,
  add column if not exists has_revive boolean not null default false,
  add column if not exists is_admin boolean not null default false,
  add column if not exists xp_multiplier numeric not null default 1.0,
  add column if not exists gold_multiplier numeric not null default 1.0,
  add column if not exists skill_buffs jsonb not null default '{}'::jsonb,
  add column if not exists sport_xp integer not null default 0,
  add column if not exists sport_level integer not null default 1,
  add column if not exists total_sport_points_earned bigint not null default 0,
  add column if not exists total_habits_done integer not null default 0,
  add column if not exists total_dailies_done integer not null default 0,
  add column if not exists total_todos_done integer not null default 0,
  add column if not exists total_tasks_completed integer not null default 0,
  add column if not exists longest_streak integer not null default 0;

-- ---------------------------------------------------------------------------
-- 2. Kurva level — SAMA dengan Python (needed = level*150 per level up)
--    level = floor((1 + sqrt(1 + 8*total/150)) / 2), progress = total - 150*L*(L-1)/2
--    (pengganti `wallet_level_for_xp` placeholder M05 — lihat catatan S4 di atas.)
-- ---------------------------------------------------------------------------
create or replace function public.wallet_level_for_xp(p_xp bigint)
returns integer language sql immutable set search_path=public as $$
  select greatest(1, floor((1.0 + sqrt(1.0 + 8.0 * greatest(0, p_xp) / 150.0)) / 2.0)::integer);
$$;

-- Progress XP di level berjalan (padanan `u["xp"]` Python).
create or replace function public.m15_xp_progress(p_total bigint)
returns bigint language sql immutable set search_path=public as $$
  select greatest(0, p_total - (150 * public.wallet_level_for_xp(p_total)
                                * (public.wallet_level_for_xp(p_total) - 1)) / 2);
$$;

-- ---------------------------------------------------------------------------
-- 3. gain_xp_gold — mesin reward (port L3526)
-- ---------------------------------------------------------------------------
create or replace function public.m15_gain_xp_gold(p_xp_base integer, p_gold_base integer,
                                                   p_idem text default null)
returns jsonb language plpgsql security definer set search_path=public as $$
declare
  uid uuid := auth.uid();
  w public.user_cloud_wallets%rowtype;
  v_skill_xp numeric := 1.0;
  v_skill_gold numeric := 1.0;
  v_buffs jsonb;
  v_xp integer;
  v_gold integer;
  v_total_xp bigint;
  v_total_gold bigint;
  v_old_level integer;
  v_new_level integer;
  v_needed bigint;
begin
  if uid is null then raise exception 'unauthorized'; end if;
  select * into w from public.user_cloud_wallets where user_id = uid;
  if not found then
    insert into public.user_cloud_wallets(user_id) values (uid)
    returning * into w;
  end if;

  -- buff skill (multiplier + sisa pakai) — padanan get_skill_buffs/set_skill_buffs
  v_buffs := coalesce(w.skill_buffs, '{}'::jsonb);
  if coalesce((v_buffs->>'xp_remaining')::int, 0) > 0 then
    v_skill_xp := coalesce((v_buffs->>'xp_multiplier')::numeric, 1.0);
    v_buffs := v_buffs || jsonb_build_object('xp_remaining',
                 (v_buffs->>'xp_remaining')::int - 1);
    if (v_buffs->>'xp_remaining')::int = 0 then
      v_buffs := v_buffs - 'xp_multiplier' - 'xp_remaining';
    end if;
  end if;
  if coalesce((v_buffs->>'gold_remaining')::int, 0) > 0 then
    v_skill_gold := coalesce((v_buffs->>'gold_multiplier')::numeric, 1.0);
    v_buffs := v_buffs || jsonb_build_object('gold_remaining',
                 (v_buffs->>'gold_remaining')::int - 1);
    if (v_buffs->>'gold_remaining')::int = 0 then
      v_buffs := v_buffs - 'gold_multiplier' - 'gold_remaining';
    end if;
  end if;

  -- multiplier dasar (pet + skill + admin x5) — urutan perkalian sama dengan Python
  v_xp := floor(p_xp_base * w.xp_multiplier * v_skill_xp)::integer;
  v_gold := round(p_gold_base * w.gold_multiplier * v_skill_gold)::integer;
  if w.is_admin then
    v_xp := (v_xp * 5)::integer;
    v_gold := (v_gold * 5)::integer;
  end if;

  v_old_level := public.wallet_level_for_xp(w.xp);
  v_total_xp := greatest(0, w.xp + v_xp);
  v_total_gold := w.gold + v_gold;
  v_new_level := public.wallet_level_for_xp(v_total_xp);

  update public.user_cloud_wallets set
    xp = v_total_xp,
    gold = v_total_gold,
    level = v_new_level,
    total_xp_earned = total_xp_earned + v_xp,
    total_gold_earned = total_gold_earned + v_gold,
    skill_buffs = v_buffs,
    updated_at = now()
  where user_id = uid;

  -- level up: HP/MP penuh sesuai kurva Python (mhp=50+(lvl-1)*10, mmp=30+(lvl-1)*5)
  if v_new_level > v_old_level then
    update public.user_cloud_wallets set
      max_hp = 50 + (v_new_level - 1) * 10,
      hp = 50 + (v_new_level - 1) * 10,
      max_mp = 30 + (v_new_level - 1) * 5 + mp_bonus,
      mp = 30 + (v_new_level - 1) * 5 + mp_bonus
    where user_id = uid;
  end if;

  return jsonb_build_object(
    'ok', true,
    'leveled_up', v_new_level > v_old_level,
    'new_level', v_new_level,
    'new_xp', public.m15_xp_progress(v_total_xp),
    'xp_gained', v_xp,
    'gold_gained', v_gold);
end; $$;

-- ---------------------------------------------------------------------------
-- 4. lose_hp (port L3594) — dipakai jalur fail/down
-- ---------------------------------------------------------------------------
create or replace function public.m15_lose_hp(p_base integer, p_ignore_reduction boolean default false)
returns jsonb language plpgsql security definer set search_path=public as $$
declare
  uid uuid := auth.uid();
  w public.user_cloud_wallets%rowtype;
  v_damage numeric;
  v_actual integer;
  v_new_hp integer;
begin
  if uid is null then raise exception 'unauthorized'; end if;
  select * into w from public.user_cloud_wallets where user_id = uid;
  if not found then return jsonb_build_object('revived', false, 'new_hp', 0); end if;
  v_damage := p_base + least(25, w.level * 0.5);
  v_actual := floor(greatest(0.0, v_damage
               - case when p_ignore_reduction then 0 else w.hp_damage_reduction end))::integer;
  v_new_hp := greatest(0, w.hp - v_actual);

  if v_new_hp = 0 and w.has_revive then
    v_new_hp := floor(w.max_hp * 0.3)::integer;
    update public.user_cloud_wallets set hp = v_new_hp, has_revive = false where user_id = uid;
    return jsonb_build_object('revived', true, 'new_hp', v_new_hp, 'damage_taken', v_actual);
  end if;

  update public.user_cloud_wallets set hp = v_new_hp where user_id = uid;
  return jsonb_build_object('revived', false, 'new_hp', v_new_hp, 'damage_taken', v_actual);
end; $$;

-- ---------------------------------------------------------------------------
-- 5. penalize_gold / penalize_xp (port L3638 / L3657)
-- ---------------------------------------------------------------------------
create or replace function public.m15_penalize_gold(p_base integer default 5)
returns jsonb language plpgsql security definer set search_path=public as $$
declare
  uid uuid := auth.uid();
  w public.user_cloud_wallets%rowtype;
  v_penalty integer;
  v_lost integer;
begin
  if uid is null then raise exception 'unauthorized'; end if;
  select * into w from public.user_cloud_wallets where user_id = uid;
  if not found then return jsonb_build_object('gold_lost', 0, 'remaining_gold', 0); end if;
  v_penalty := floor(p_base + least(25, w.level * 0.5))::integer;
  if w.gold <= 0 then return jsonb_build_object('gold_lost', 0, 'remaining_gold', 0); end if;
  v_lost := least(v_penalty, w.gold);
  update public.user_cloud_wallets set gold = gold - v_lost where user_id = uid;
  return jsonb_build_object('gold_lost', v_lost, 'remaining_gold', w.gold - v_lost);
end; $$;

create or replace function public.m15_penalize_xp()
returns jsonb language plpgsql security definer set search_path=public as $$
declare
  uid uuid := auth.uid();
  w public.user_cloud_wallets%rowtype;
  v_lost integer;
  v_total bigint;
  v_new_level integer;
begin
  if uid is null then raise exception 'unauthorized'; end if;
  select * into w from public.user_cloud_wallets where user_id = uid;
  if not found then return jsonb_build_object('xp_lost', 0, 'new_level', 1); end if;
  -- Python: potong 10% dari XP level berjalan, minimal 1; level turun bila kurang.
  if public.m15_xp_progress(w.xp) <= 0 then
    return jsonb_build_object('xp_lost', 0, 'new_level', public.wallet_level_for_xp(w.xp));
  end if;
  v_lost := greatest(1, floor(public.m15_xp_progress(w.xp) * 0.1)::integer);
  v_total := greatest(0, w.xp - v_lost);
  v_new_level := public.wallet_level_for_xp(v_total);
  update public.user_cloud_wallets set
    xp = v_total,
    level = v_new_level,
    total_xp_earned = total_xp_earned  -- total tetap: ini penalti progress, bukan earned
  where user_id = uid;
  return jsonb_build_object('xp_lost', v_lost, 'new_level', v_new_level);
end; $$;

-- ---------------------------------------------------------------------------
-- 6. Aksi tracker — membaca payload `sync_entities` (baris yang sama dengan
--    sinkronisasi desktop) lalu memanggil mesin reward di atas.
-- ---------------------------------------------------------------------------
create or replace function public.m15_entity_payload(p_table text, p_uuid uuid)
returns jsonb language plpgsql stable security definer set search_path=public as $$
declare
  uid uuid := auth.uid();
  v jsonb;
begin
  if uid is null then raise exception 'unauthorized'; end if;
  select payload into v from public.sync_entities
   where user_id = uid and table_name = p_table and entity_uuid = p_uuid
     and deleted_at is null;
  if not found then raise exception 'entity_not_found'; end if;
  return v;
end; $$;

create or replace function public.m15_entity_update(p_table text, p_uuid uuid, p_patch jsonb)
returns jsonb language plpgsql security definer set search_path=public as $$
declare
  uid uuid := auth.uid();
  v jsonb;
begin
  if uid is null then raise exception 'unauthorized'; end if;
  update public.sync_entities
     set payload = payload || p_patch,
         rev = rev + 1,
         client_updated_at = now(),
         server_updated_at = now()
   where user_id = uid and table_name = p_table and entity_uuid = p_uuid
     and deleted_at is null
  returning payload into v;
  if v is null then raise exception 'entity_not_found'; end if;
  return v;
end; $$;

-- counter tugas di dompet (padanan total_tasks_completed dst.)
create or replace function public.m15_bump_counter(p_key text, p_amount integer default 1)
returns void language plpgsql security definer set search_path=public as $$
begin
  update public.user_cloud_wallets
     set total_tasks_completed = total_tasks_completed + p_amount,
         updated_at = now()
   where user_id = auth.uid();
  if p_key in ('total_habits_done','total_dailies_done','total_todos_done') then
    execute format('update public.user_cloud_wallets set %I = %I + $1 where user_id = $2', p_key, p_key)
      using p_amount, auth.uid();
  end if;
end; $$;

-- complete_habit (port L3902) — arah 'up' = reward+streak, 'down' = fail_streak+HP
create or replace function public.m15_complete_habit(p_uuid uuid, p_direction text default 'up')
returns jsonb language plpgsql security definer set search_path=public as $$
declare
  uid uuid := auth.uid();
  p jsonb;
  v_streak integer;
  v_fail integer;
  v_res jsonb;
begin
  if uid is null then raise exception 'unauthorized'; end if;
  p := public.m15_entity_payload('habits', p_uuid);
  if (p->>'done_today')::boolean then raise exception 'already_done'; end if;
  v_streak := case when p_direction = 'up' then coalesce((p->>'streak')::int, 0) + 1 else 0 end;
  v_fail := case when p_direction = 'up' then 0
                 else coalesce((p->>'fail_streak')::int, 0) + 1 end;
  perform public.m15_entity_update('habits', p_uuid, jsonb_build_object(
    'done_today', true, 'streak', v_streak, 'fail_streak', v_fail,
    'last_done', to_char(now(), 'YYYY-MM-DD'), 'last_action', p_direction,
    'counter_up', coalesce((p->>'counter_up')::int, 0) + case when p_direction = 'up' then 1 else 0 end,
    'counter_down', coalesce((p->>'counter_down')::int, 0) + case when p_direction = 'down' then 1 else 0 end));
  perform public.m15_bump_counter('total_habits_done', 1);

  if p_direction = 'up' then
    -- restore_mp(3): padanan database.py — pulihkan MP 3
    update public.user_cloud_wallets set mp = least(max_mp, mp + 3) where user_id = uid;
    if v_streak > coalesce((p->>'longest_streak')::int, 0) then
      update public.user_cloud_wallets set longest_streak = v_streak where user_id = uid;
    end if;
    v_res := public.m15_gain_xp_gold(coalesce((p->>'xp_reward')::int, 0),
                                     coalesce((p->>'gold_reward')::int, 0));
  else
    v_res := public.m15_lose_hp(5, true);
  end if;
  return v_res || jsonb_build_object('ok', true, 'streak', v_streak, 'fail_streak', v_fail);
end; $$;

-- complete_daily (port L4060) — buff double_streak menggandakan bonus streak
create or replace function public.m15_complete_daily(p_uuid uuid)
returns jsonb language plpgsql security definer set search_path=public as $$
declare
  uid uuid := auth.uid();
  p jsonb;
  w public.user_cloud_wallets%rowtype;
  v_buffs jsonb;
  v_bonus integer := 1;
  v_streak integer;
  v_res jsonb;
begin
  if uid is null then raise exception 'unauthorized'; end if;
  p := public.m15_entity_payload('dailies', p_uuid);
  if (p->>'done_today')::boolean then raise exception 'already_done'; end if;
  select * into w from public.user_cloud_wallets where user_id = uid;
  v_buffs := coalesce(w.skill_buffs, '{}'::jsonb);
  if coalesce((v_buffs->>'double_streak')::boolean, false) then
    v_bonus := 2;
    v_buffs := v_buffs - 'double_streak';
    update public.user_cloud_wallets set skill_buffs = v_buffs where user_id = uid;
  end if;
  v_streak := coalesce((p->>'streak')::int, 0) + v_bonus;
  perform public.m15_entity_update('dailies', p_uuid, jsonb_build_object(
    'done_today', true, 'streak', v_streak, 'fail_streak', 0,
    'last_done', to_char(now(), 'YYYY-MM-DD'), 'last_action', 'up'));
  perform public.m15_bump_counter('total_dailies_done', 1);
  update public.user_cloud_wallets set mp = least(max_mp, mp + 5) where user_id = uid;
  v_res := public.m15_gain_xp_gold(coalesce((p->>'xp_reward')::int, 0),
                                   coalesce((p->>'gold_reward')::int, 0));
  return v_res || jsonb_build_object('ok', true, 'streak', v_streak);
end; $$;

-- fail_daily (port L4098) — freeze slot dulu; kalau habis: HP → gold → XP
create or replace function public.m15_fail_daily(p_uuid uuid)
returns jsonb language plpgsql security definer set search_path=public as $$
declare
  uid uuid := auth.uid();
  p jsonb;
  v_freeze integer;
  v_fail_streak integer;
  v_hp jsonb;
  v_penalty_type text := 'hp';
  v_penalty_amount integer := 0;
  v_g jsonb;
  v_x jsonb;
begin
  if uid is null then raise exception 'unauthorized'; end if;
  p := public.m15_entity_payload('dailies', p_uuid);
  if (p->>'done_today')::boolean then raise exception 'already_done'; end if;

  v_freeze := coalesce((p->>'freeze_slots')::int, 0);
  if v_freeze > 0 then
    perform public.m15_entity_update('dailies', p_uuid, jsonb_build_object(
      'done_today', true, 'freeze_slots', v_freeze - 1,
      'last_done', to_char(now(), 'YYYY-MM-DD'), 'last_action', 'frozen'));
    perform public.m15_bump_counter('total_dailies_done', 1);
    return jsonb_build_object('ok', true, 'freeze_used', true,
                              'remaining_freezes', v_freeze - 1);
  end if;

  v_fail_streak := coalesce((p->>'fail_streak')::int, 0) + 1;
  perform public.m15_entity_update('dailies', p_uuid, jsonb_build_object(
    'done_today', true, 'streak', 0, 'fail_streak', v_fail_streak,
    'last_done', to_char(now(), 'YYYY-MM-DD'), 'last_action', 'down'));
  perform public.m15_bump_counter('total_dailies_done', 1);

  if (select hp from public.user_cloud_wallets where user_id = uid) > 0 then
    v_hp := public.m15_lose_hp(5, true);
  else
    v_hp := jsonb_build_object('damage_taken', 0, 'new_hp', 0);
  end if;
  if (v_hp->>'new_hp')::int > 0 then
    v_penalty_amount := coalesce((v_hp->>'damage_taken')::int, 0);
  else
    v_g := public.m15_penalize_gold(5);
    if (v_g->>'gold_lost')::int > 0 then
      v_penalty_type := 'gold'; v_penalty_amount := (v_g->>'gold_lost')::int;
    else
      v_x := public.m15_penalize_xp();
      if (v_x->>'xp_lost')::int > 0 then
        v_penalty_type := 'xp'; v_penalty_amount := (v_x->>'xp_lost')::int;
      else
        v_penalty_type := 'none'; v_penalty_amount := 0;
      end if;
    end if;
  end if;
  return jsonb_build_object('ok', true, 'lost_hp', coalesce((v_hp->>'damage_taken')::int, 0),
    'fail_streak', v_fail_streak, 'penalty_type', v_penalty_type,
    'penalty_amount', v_penalty_amount);
end; $$;

-- add_freeze_to_daily (port L4189) — 1 ice_block dari cloud_inventory → 1 slot (max 3)
create or replace function public.m15_add_freeze_to_daily(p_uuid uuid)
returns jsonb language plpgsql security definer set search_path=public as $$
declare
  uid uuid := auth.uid();
  p jsonb;
  v_freeze integer;
begin
  if uid is null then raise exception 'unauthorized'; end if;
  p := public.m15_entity_payload('dailies', p_uuid);
  v_freeze := coalesce((p->>'freeze_slots')::int, 0);
  if v_freeze >= 3 then raise exception 'freeze_max_reached'; end if;
  update public.cloud_inventory
     set quantity = quantity - 1
   where user_id = uid and item_id = 'ice_block' and quantity > 0;
  if not found then raise exception 'freeze_no_item'; end if;
  perform public.m15_entity_update('dailies', p_uuid,
    jsonb_build_object('freeze_slots', v_freeze + 1));
  return jsonb_build_object('ok', true, 'remaining', v_freeze + 1);
end; $$;

-- complete_todo (port L4278)
create or replace function public.m15_complete_todo(p_uuid uuid)
returns jsonb language plpgsql security definer set search_path=public as $$
declare
  uid uuid := auth.uid();
  p jsonb;
  v_res jsonb;
begin
  if uid is null then raise exception 'unauthorized'; end if;
  p := public.m15_entity_payload('todos', p_uuid);
  if coalesce((p->>'done')::boolean, false) then raise exception 'already_done'; end if;
  perform public.m15_entity_update('todos', p_uuid, jsonb_build_object('done', true));
  perform public.m15_bump_counter('total_todos_done', 1);
  update public.user_cloud_wallets set mp = least(max_mp, mp + 4) where user_id = uid;
  v_res := public.m15_gain_xp_gold(coalesce((p->>'xp_reward')::int, 0),
                                   coalesce((p->>'gold_reward')::int, 0));
  return v_res || jsonb_build_object('ok', true);
end; $$;

-- complete_sport_activity (port L4607 + gain_sport_points L4644)
create or replace function public.m15_complete_sport_activity(p_uuid uuid)
returns jsonb language plpgsql security definer set search_path=public as $$
declare
  uid uuid := auth.uid();
  p jsonb;
  w public.user_cloud_wallets%rowtype;
  v_points integer;
  v_sport_xp integer;
  v_sport_lvl integer;
  v_needed integer;
  v_leveled boolean := false;
  v_res jsonb;
begin
  if uid is null then raise exception 'unauthorized'; end if;
  p := public.m15_entity_payload('sport_activities', p_uuid);
  if coalesce((p->>'done_today')::boolean, false) then raise exception 'already_done'; end if;
  perform public.m15_entity_update('sport_activities', p_uuid, jsonb_build_object(
    'done_today', true, 'streak', coalesce((p->>'streak')::int, 0) + 1,
    'last_done', to_char(now(), 'YYYY-MM-DD')));

  v_res := public.m15_gain_xp_gold(coalesce((p->>'xp_reward')::int, 0),
                                   coalesce((p->>'gold_reward')::int, 0));

  -- gain_sport_points: kurva level*100 — terpisah dari level utama (port L4644)
  v_points := coalesce((p->>'sport_points_reward')::int, 0);
  select * into w from public.user_cloud_wallets where user_id = uid;
  v_sport_xp := w.sport_xp + v_points;
  v_sport_lvl := w.sport_level;
  v_needed := v_sport_lvl * 100;
  while v_sport_xp >= v_needed loop
    v_sport_xp := v_sport_xp - v_needed;
    v_sport_lvl := v_sport_lvl + 1;
    v_leveled := true;
    v_needed := v_sport_lvl * 100;
  end loop;
  update public.user_cloud_wallets set
    sport_xp = v_sport_xp, sport_level = v_sport_lvl,
    total_sport_points_earned = total_sport_points_earned + v_points
  where user_id = uid;

  return v_res || jsonb_build_object('ok', true,
    'sport_points_gained', v_points, 'sport_leveled_up', v_leveled,
    'new_sport_level', v_sport_lvl, 'new_sport_xp', v_sport_xp);
end; $$;

-- complete_pomodoro (port L13082) — xp = max(1, menit*1), gold = max(2, menit//5)
-- Konstanta POMODORO_XP_PER_MIN=1 & POMODORO_GOLD_DIV=5 (database.py L13078).
create or replace function public.m15_complete_pomodoro(p_minutes integer, p_task_name text default '')
returns jsonb language plpgsql security definer set search_path=public as $$
declare
  uid uuid := auth.uid();
  v_xp integer;
  v_gold integer;
  v_id uuid;
  v_res jsonb;
begin
  if uid is null then raise exception 'unauthorized'; end if;
  if p_minutes is null or p_minutes <= 0 then raise exception 'invalid_duration'; end if;
  v_xp := greatest(1, p_minutes * 1);
  v_gold := greatest(2, p_minutes / 5);
  insert into public.sync_entities(user_id, table_name, entity_uuid, payload,
           client_updated_at, server_updated_at)
  values (uid, 'pomodoro_sessions', gen_random_uuid(),
          jsonb_build_object('task_name', left(coalesce(p_task_name, ''), 120),
                             'duration_minutes', p_minutes,
                             'xp_earned', v_xp, 'gold_earned', v_gold,
                             'completed_at', now()),
          now(), now())
  returning entity_uuid into v_id;
  v_res := public.m15_gain_xp_gold(v_xp, v_gold);
  return v_res || jsonb_build_object('ok', true, 'session_minutes', p_minutes, 'session_uuid', v_id);
end; $$;

-- apply_late_debt_penalty (port L9040) — penalti 10*(level/5), clamp 10..100, sekali per hutang
create or replace function public.m15_apply_late_debt_penalty(p_uuid uuid)
returns jsonb language plpgsql security definer set search_path=public as $$
declare
  uid uuid := auth.uid();
  p jsonb;
  w public.user_cloud_wallets%rowtype;
  v_penalty integer;
begin
  if uid is null then raise exception 'unauthorized'; end if;
  p := public.m15_entity_update('debts', p_uuid, '{}'::jsonb); -- validasi ada
  if coalesce((p->>'is_paid')::boolean, false)
     or coalesce((p->>'penalty_applied')::boolean, false) then
    raise exception 'penalty_already';
  end if;
  select * into w from public.user_cloud_wallets where user_id = uid;
  v_penalty := greatest(10, least(100, floor(10 * (w.level / 5.0))::integer));
  update public.user_cloud_wallets set gold = greatest(0, gold - v_penalty) where user_id = uid;
  perform public.m15_entity_update('debts', p_uuid, jsonb_build_object(
    'penalty_applied', true, 'penalty_amount', v_penalty));
  return jsonb_build_object('ok', true, 'gold_lost', v_penalty);
end; $$;

-- ---------------------------------------------------------------------------
-- 7. Keamanan: hanya `authenticated`, tidak untuk anon (pola M09)
-- ---------------------------------------------------------------------------
revoke all on function public.wallet_level_for_xp(bigint) from public;
revoke all on function public.m15_xp_progress(bigint) from public;
revoke all on function public.m15_gain_xp_gold(integer, integer, text) from public;
revoke all on function public.m15_lose_hp(integer, boolean) from public;
revoke all on function public.m15_penalize_gold(integer) from public;
revoke all on function public.m15_penalize_xp() from public;
revoke all on function public.m15_entity_payload(text, uuid) from public;
revoke all on function public.m15_entity_update(text, uuid, jsonb) from public;
revoke all on function public.m15_bump_counter(text, integer) from public;
revoke all on function public.m15_complete_habit(uuid, text) from public;
revoke all on function public.m15_complete_daily(uuid) from public;
revoke all on function public.m15_fail_daily(uuid) from public;
revoke all on function public.m15_add_freeze_to_daily(uuid) from public;
revoke all on function public.m15_complete_todo(uuid) from public;
revoke all on function public.m15_complete_sport_activity(uuid) from public;
revoke all on function public.m15_complete_pomodoro(integer, text) from public;
revoke all on function public.m15_apply_late_debt_penalty(uuid) from public;

grant execute on function public.wallet_level_for_xp(bigint) to authenticated;
grant execute on function public.m15_xp_progress(bigint) to authenticated;
grant execute on function public.m15_gain_xp_gold(integer, integer, text) to authenticated;
grant execute on function public.m15_lose_hp(integer, boolean) to authenticated;
grant execute on function public.m15_penalize_gold(integer) to authenticated;
grant execute on function public.m15_penalize_xp() to authenticated;
grant execute on function public.m15_entity_payload(text, uuid) to authenticated;
grant execute on function public.m15_entity_update(text, uuid, jsonb) to authenticated;
grant execute on function public.m15_bump_counter(text, integer) to authenticated;
grant execute on function public.m15_complete_habit(uuid, text) to authenticated;
grant execute on function public.m15_complete_daily(uuid) to authenticated;
grant execute on function public.m15_fail_daily(uuid) to authenticated;
grant execute on function public.m15_add_freeze_to_daily(uuid) to authenticated;
grant execute on function public.m15_complete_todo(uuid) to authenticated;
grant execute on function public.m15_complete_sport_activity(uuid) to authenticated;
grant execute on function public.m15_complete_pomodoro(integer, text) to authenticated;
grant execute on function public.m15_apply_late_debt_penalty(uuid) to authenticated;
