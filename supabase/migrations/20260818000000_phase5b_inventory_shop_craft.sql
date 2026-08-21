-- CraftLife Phase 5B: server-authoritative inventory, shop, crafting.
-- Harga & resep dibaca server; transaksi wallet+inventori atomik; idempoten.

-- 5B-0: perluaskan sumber ledger untuk transaksi ekonomi
alter table public.reward_ledger drop constraint if exists reward_ledger_source_check;
alter table public.reward_ledger add constraint reward_ledger_source_check
  check (source in ('productivity','pvp','guild_boss','achievement','quest',
                    'shop_refund','shop_purchase','craft_spend','admin_adjustment'));

-- 5B-1: katalog server (seed dari desktop, harga otoritatif)
create table if not exists public.shop_items_server (
  item_key text primary key,
  name text not null,
  price_gold integer not null check (price_gold >= 0),
  per_user_limit integer,
  active boolean not null default true,
  created_at timestamptz not null default now()
);
create table if not exists public.recipes_server (
  recipe_key text primary key,
  result_key text not null,
  ingredients jsonb not null,           -- [{"item":key,"qty":n}, ...]
  gold_cost integer not null default 0 check (gold_cost >= 0),
  created_at timestamptz not null default now()
);

-- 5B-2: inventori cloud + audit tx
create table if not exists public.cloud_inventory (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references public.profiles(id) on delete cascade,
  item_key text not null,
  qty integer not null check (qty >= 0),
  equipped boolean not null default false,
  enchant_level integer not null default 0,
  acquired_source text not null default '',
  updated_at timestamptz not null default now(),
  unique (user_id, item_key)
);
create table if not exists public.cloud_inventory_tx (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references public.profiles(id) on delete cascade,
  item_key text not null,
  kind text not null check (kind in ('grant','spend','shop_buy','craft_consume','craft_result','enchant','admin')),
  delta integer not null,
  idempotency_key text,
  created_at timestamptz not null default now(),
  unique (user_id, idempotency_key)
);
create table if not exists public.cloud_shop_purchases (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references public.profiles(id) on delete cascade,
  item_key text not null,
  qty integer not null default 1,
  gold_spent integer not null default 0,
  tx_key text not null unique,
  created_at timestamptz not null default now()
);
create table if not exists public.cloud_crafts (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references public.profiles(id) on delete cascade,
  recipe_key text not null,
  tx_key text not null unique,
  created_at timestamptz not null default now()
);

-- 5B-3: helper pengurang gold via ledger (trigger 5A memperbarui wallet)
create or replace function public.spend_gold(p_user uuid, p_amount integer, p_source text, p_ref_key text, p_idem text)
returns void language plpgsql security definer set search_path=public as $$
declare bal bigint;
begin
  select coalesce(gold,0) into bal from public.user_cloud_wallets where user_id=p_user;
  if coalesce(bal,0) < p_amount then raise exception 'insufficient_balance'; end if;
  insert into public.reward_ledger(user_id,source,ref_key,delta_gold,idempotency_key)
  values (p_user,p_source,p_ref_key,-p_amount,p_idem);
end; $$;

-- 5B-3b: seed katalog & resep (generated dari SHOP_ITEMS/CRAFTING_RECIPES desktop)
insert into public.shop_items_server(item_key,name,price_gold) values ('wooden_sword','Wooden Sword',50) on conflict (item_key) do nothing;
insert into public.shop_items_server(item_key,name,price_gold) values ('enchanted_bow','Enchanted Bow',180) on conflict (item_key) do nothing;
insert into public.shop_items_server(item_key,name,price_gold) values ('trident','Trident',350) on conflict (item_key) do nothing;
insert into public.shop_items_server(item_key,name,price_gold) values ('iron_sword','Iron Sword',100) on conflict (item_key) do nothing;
insert into public.shop_items_server(item_key,name,price_gold) values ('diamond_sword','Diamond Sword',320) on conflict (item_key) do nothing;
insert into public.shop_items_server(item_key,name,price_gold) values ('netherite_sword','Netherite Sword',650) on conflict (item_key) do nothing;
insert into public.shop_items_server(item_key,name,price_gold) values ('shield','Shield',120) on conflict (item_key) do nothing;
insert into public.shop_items_server(item_key,name,price_gold) values ('golden_boots','Golden Boots',140) on conflict (item_key) do nothing;
insert into public.shop_items_server(item_key,name,price_gold) values ('diamond_armor','Diamond Armor',300) on conflict (item_key) do nothing;
insert into public.shop_items_server(item_key,name,price_gold) values ('elytra','Elytra Wings',500) on conflict (item_key) do nothing;
insert into public.shop_items_server(item_key,name,price_gold) values ('tower_shield','Tower Shield',200) on conflict (item_key) do nothing;
insert into public.shop_items_server(item_key,name,price_gold) values ('guardian_chestplate','Guardian Chestplate',400) on conflict (item_key) do nothing;
insert into public.shop_items_server(item_key,name,price_gold) values ('diamond_chestplate','Diamond Chestplate',600) on conflict (item_key) do nothing;
insert into public.shop_items_server(item_key,name,price_gold) values ('iron_pickaxe','Iron Pickaxe',100) on conflict (item_key) do nothing;
insert into public.shop_items_server(item_key,name,price_gold) values ('compass','Compass',80) on conflict (item_key) do nothing;
insert into public.shop_items_server(item_key,name,price_gold) values ('spyglass','Spyglass',90) on conflict (item_key) do nothing;
insert into public.shop_items_server(item_key,name,price_gold) values ('ice_block','Ice Block',25) on conflict (item_key) do nothing;
insert into public.shop_items_server(item_key,name,price_gold) values ('blaze_rod','Blaze Rod',160) on conflict (item_key) do nothing;
insert into public.shop_items_server(item_key,name,price_gold) values ('totem','Totem of Life',400) on conflict (item_key) do nothing;
insert into public.shop_items_server(item_key,name,price_gold) values ('golden_apple','Golden Apple',50) on conflict (item_key) do nothing;
insert into public.shop_items_server(item_key,name,price_gold) values ('enchanted_apple','Enchanted Apple',200) on conflict (item_key) do nothing;
insert into public.shop_items_server(item_key,name,price_gold) values ('health_potion','Health Potion',100) on conflict (item_key) do nothing;
insert into public.shop_items_server(item_key,name,price_gold) values ('greater_health_potion','Greater Health Potion',150) on conflict (item_key) do nothing;
insert into public.shop_items_server(item_key,name,price_gold) values ('mana_potion','Mana Potion',80) on conflict (item_key) do nothing;
insert into public.shop_items_server(item_key,name,price_gold) values ('greater_mana_potion','Greater Mana Potion',200) on conflict (item_key) do nothing;
insert into public.shop_items_server(item_key,name,price_gold) values ('super_mana_potion','Super Mana Potion',500) on conflict (item_key) do nothing;
insert into public.shop_items_server(item_key,name,price_gold) values ('elixir','Elixir of Life',1000) on conflict (item_key) do nothing;
insert into public.shop_items_server(item_key,name,price_gold) values ('ender_pearl','Ender Pearl',300) on conflict (item_key) do nothing;
insert into public.shop_items_server(item_key,name,price_gold) values ('nether_star','Nether Star',700) on conflict (item_key) do nothing;
insert into public.shop_items_server(item_key,name,price_gold) values ('beacon','Beacon',1200) on conflict (item_key) do nothing;
insert into public.shop_items_server(item_key,name,price_gold) values ('bedrock_sword','Bedrock Sword',2500) on conflict (item_key) do nothing;
insert into public.shop_items_server(item_key,name,price_gold) values ('phantom_wings','Phantom Wings',1800) on conflict (item_key) do nothing;
insert into public.shop_items_server(item_key,name,price_gold) values ('aegis_of_void','Aegis of the Void',2400) on conflict (item_key) do nothing;
insert into public.shop_items_server(item_key,name,price_gold) values ('ketupat_feast','Ketupat Feast',75) on conflict (item_key) do nothing;
insert into public.shop_items_server(item_key,name,price_gold) values ('candy_bag','Candy Bag',40) on conflict (item_key) do nothing;
insert into public.shop_items_server(item_key,name,price_gold) values ('snowball_fight','Snowball Fight',50) on conflict (item_key) do nothing;
insert into public.shop_items_server(item_key,name,price_gold) values ('storm_blade','Storm Blade',950) on conflict (item_key) do nothing;
insert into public.shop_items_server(item_key,name,price_gold) values ('obsidian_dagger','Obsidian Dagger',420) on conflict (item_key) do nothing;
insert into public.shop_items_server(item_key,name,price_gold) values ('turtle_shell','Turtle Shell Helm',460) on conflict (item_key) do nothing;
insert into public.shop_items_server(item_key,name,price_gold) values ('wind_cloak','Wind Cloak',380) on conflict (item_key) do nothing;
insert into public.shop_items_server(item_key,name,price_gold) values ('lucky_charm','Lucky Charm',260) on conflict (item_key) do nothing;
insert into public.shop_items_server(item_key,name,price_gold) values ('scholar_tome','Scholar''s Tome',320) on conflict (item_key) do nothing;
insert into public.shop_items_server(item_key,name,price_gold) values ('honey_bottle','Honey Bottle',60) on conflict (item_key) do nothing;
insert into public.shop_items_server(item_key,name,price_gold) values ('sturdy_stew','Sturdy Stew',90) on conflict (item_key) do nothing;
insert into public.shop_items_server(item_key,name,price_gold) values ('dragon_breath','Dragon''s Breath',240) on conflict (item_key) do nothing;
insert into public.shop_items_server(item_key,name,price_gold) values ('dragon_egg','Dragon Egg',1600) on conflict (item_key) do nothing;
insert into public.shop_items_server(item_key,name,price_gold) values ('inferno_blade','Inferno Blade',2800) on conflict (item_key) do nothing;
insert into public.shop_items_server(item_key,name,price_gold) values ('healers_blessing','Healer''s Blessing',2200) on conflict (item_key) do nothing;
insert into public.shop_items_server(item_key,name,price_gold) values ('gilded_compass','Gilded Compass',2000) on conflict (item_key) do nothing;
insert into public.shop_items_server(item_key,name,price_gold) values ('bronze_sword','Bronze Sword',70) on conflict (item_key) do nothing;
insert into public.shop_items_server(item_key,name,price_gold) values ('steel_helm','Steel Helm',250) on conflict (item_key) do nothing;
insert into public.shop_items_server(item_key,name,price_gold) values ('travelers_boots','Traveler''s Boots',190) on conflict (item_key) do nothing;
insert into public.shop_items_server(item_key,name,price_gold) values ('arcane_ring','Arcane Ring',450) on conflict (item_key) do nothing;
insert into public.shop_items_server(item_key,name,price_gold) values ('berry_pie','Berry Pie',45) on conflict (item_key) do nothing;
insert into public.shop_items_server(item_key,name,price_gold) values ('mana_cookie','Mana Cookie',110) on conflict (item_key) do nothing;
insert into public.shop_items_server(item_key,name,price_gold) values ('frost_guard','Frost Guard',2600) on conflict (item_key) do nothing;
insert into public.shop_items_server(item_key,name,price_gold) values ('scholar_crown','Scholar Crown',2400) on conflict (item_key) do nothing;
insert into public.shop_items_server(item_key,name,price_gold) values ('void_core','Void Core',3000) on conflict (item_key) do nothing;
insert into public.shop_items_server(item_key,name,price_gold) values ('ember_charm','Ember Charm',2200) on conflict (item_key) do nothing;
insert into public.recipes_server(recipe_key,result_key,ingredients,gold_cost) values ('bedrock_sword','bedrock_sword','[{"item": "netherite_sword", "qty": 1}, {"item": "diamond_sword", "qty": 1}]'::jsonb,500) on conflict (recipe_key) do nothing;
insert into public.recipes_server(recipe_key,result_key,ingredients,gold_cost) values ('phantom_wings','phantom_wings','[{"item": "elytra", "qty": 1}, {"item": "golden_boots", "qty": 1}]'::jsonb,400) on conflict (recipe_key) do nothing;
insert into public.recipes_server(recipe_key,result_key,ingredients,gold_cost) values ('aegis_of_void','aegis_of_void','[{"item": "tower_shield", "qty": 1}, {"item": "diamond_chestplate", "qty": 1}]'::jsonb,600) on conflict (recipe_key) do nothing;
insert into public.recipes_server(recipe_key,result_key,ingredients,gold_cost) values ('inferno_blade','inferno_blade','[{"item": "netherite_sword", "qty": 1}, {"item": "blaze_rod", "qty": 1}]'::jsonb,700) on conflict (recipe_key) do nothing;
insert into public.recipes_server(recipe_key,result_key,ingredients,gold_cost) values ('healers_blessing','healers_blessing','[{"item": "golden_apple", "qty": 1}, {"item": "greater_health_potion", "qty": 1}, {"item": "elixir", "qty": 1}]'::jsonb,300) on conflict (recipe_key) do nothing;
insert into public.recipes_server(recipe_key,result_key,ingredients,gold_cost) values ('gilded_compass','gilded_compass','[{"item": "compass", "qty": 1}, {"item": "golden_apple", "qty": 1}]'::jsonb,450) on conflict (recipe_key) do nothing;
insert into public.recipes_server(recipe_key,result_key,ingredients,gold_cost) values ('frost_guard','frost_guard','[{"item": "turtle_shell", "qty": 1}, {"item": "ice_block", "qty": 1}, {"item": "wind_cloak", "qty": 1}]'::jsonb,550) on conflict (recipe_key) do nothing;
insert into public.recipes_server(recipe_key,result_key,ingredients,gold_cost) values ('scholar_crown','scholar_crown','[{"item": "scholar_tome", "qty": 1}, {"item": "golden_boots", "qty": 1}, {"item": "compass", "qty": 1}]'::jsonb,500) on conflict (recipe_key) do nothing;
insert into public.recipes_server(recipe_key,result_key,ingredients,gold_cost) values ('void_core','void_core','[{"item": "ender_pearl", "qty": 1}, {"item": "nether_star", "qty": 1}, {"item": "blaze_rod", "qty": 1}]'::jsonb,800) on conflict (recipe_key) do nothing;
insert into public.recipes_server(recipe_key,result_key,ingredients,gold_cost) values ('ember_charm','ember_charm','[{"item": "blaze_rod", "qty": 1}, {"item": "honey_bottle", "qty": 1}, {"item": "lucky_charm", "qty": 1}]'::jsonb,400) on conflict (recipe_key) do nothing;

-- 5B-4: beli item shop (atomik + idempoten + harga server)
create or replace function public.buy_shop_item(p_item text, p_qty integer, p_idem text)
returns jsonb language plpgsql security definer set search_path=public as $$
declare item public.shop_items_server; total integer; uid uuid := auth.uid();
        prior public.cloud_shop_purchases; owned integer;
begin
  if uid is null then raise exception 'account_unavailable'; end if;
  if p_qty is null or p_qty < 1 or p_qty > 99 then raise exception 'invalid_qty'; end if;
  select * into prior from public.cloud_shop_purchases where user_id=uid and tx_key=p_idem;
  if prior.id is not null then return jsonb_build_object('idempotent', true, 'purchase', prior.id); end if;
  select * into item from public.shop_items_server where item_key=p_item and active;
  if not found then raise exception 'unknown_item'; end if;
  if item.per_user_limit is not null then
    select coalesce(sum(qty),0) into owned from public.cloud_shop_purchases where user_id=uid and item_key=p_item;
    if owned + p_qty > item.per_user_limit then raise exception 'limit_reached'; end if;
  end if;
  total := item.price_gold * p_qty;
  perform public.spend_gold(uid, total, 'shop_purchase', p_item, 'buy:'||p_idem);
  insert into public.cloud_shop_purchases(user_id,item_key,qty,gold_spent,tx_key)
  values (uid,p_item,p_qty,total,p_idem);
  insert into public.cloud_inventory(user_id,item_key,qty,acquired_source)
  values (uid,p_item,p_qty,'shop')
  on conflict (user_id,item_key) do update set qty = cloud_inventory.qty + excluded.qty, updated_at = now();
  insert into public.cloud_inventory_tx(user_id,item_key,kind,delta,idempotency_key)
  values (uid,p_item,'shop_buy',p_qty,'buytx:'||p_idem);
  return jsonb_build_object('idempotent', false, 'gold_spent', total);
end; $$;

-- 5B-5: craft (bahan+gold+hasil satu transaksi, idempoten)
create or replace function public.craft_item_cloud(p_recipe text, p_idem text)
returns jsonb language plpgsql security definer set search_path=public as $$
declare rec public.recipes_server; uid uuid := auth.uid(); ing jsonb; need integer; rows integer;
        prior public.cloud_crafts;
begin
  if uid is null then raise exception 'account_unavailable'; end if;
  select * into prior from public.cloud_crafts where user_id=uid and tx_key=p_idem;
  if prior.id is not null then return jsonb_build_object('idempotent', true); end if;
  select * into rec from public.recipes_server where recipe_key=p_recipe;
  if not found then raise exception 'unknown_recipe'; end if;
  if rec.gold_cost > 0 then
    perform public.spend_gold(uid, rec.gold_cost, 'craft_spend', p_recipe, 'craftgold:'||p_idem);
  end if;
  for ing in select * from jsonb_array_elements(rec.ingredients)
  loop
    need := coalesce((ing->>'qty')::integer, 1);
    update public.cloud_inventory set qty = qty - need, updated_at = now()
      where user_id=uid and item_key = ing->>'item' and qty >= need;
    get diagnostics rows = row_count;
    if rows = 0 then raise exception 'missing_materials'; end if;
    insert into public.cloud_inventory_tx(user_id,item_key,kind,delta,idempotency_key)
    values (uid, ing->>'item','craft_consume',-need,'cc:'||p_idem||':'||(ing->>'item'));
  end loop;
  insert into public.cloud_inventory(user_id,item_key,qty,acquired_source)
  values (uid,rec.result_key,1,'craft')
  on conflict (user_id,item_key) do update set qty = cloud_inventory.qty + 1, updated_at = now();
  insert into public.cloud_inventory_tx(user_id,item_key,kind,delta,idempotency_key)
  values (uid,rec.result_key,'craft_result',1,'cr:'||p_idem);
  insert into public.cloud_crafts(user_id,recipe_key,tx_key) values (uid,p_recipe,p_idem);
  return jsonb_build_object('idempotent', false);
end; $$;

-- 5B-6: equip & enchant
create or replace function public.equip_item_cloud(p_item text, p_on boolean)
returns jsonb language plpgsql security definer set search_path=public as $$
declare rows integer; uid uuid := auth.uid();
begin
  update public.cloud_inventory set equipped = p_on, updated_at = now()
    where user_id=uid and item_key=p_item and qty > 0;
  get diagnostics rows = row_count;
  if rows = 0 then raise exception 'item_not_owned'; end if;
  return jsonb_build_object('ok', true);
end; $$;

create or replace function public.enchant_item_cloud(p_item text, p_idem text)
returns jsonb language plpgsql security definer set search_path=public as $$
declare inv public.cloud_inventory; cost integer; uid uuid := auth.uid();
begin
  select * into inv from public.cloud_inventory where user_id=uid and item_key=p_item and qty > 0;
  if not found then raise exception 'item_not_owned'; end if;
  if inv.enchant_level >= 10 then raise exception 'max_enchant'; end if;
  cost := 150 * (inv.enchant_level + 1);
  perform public.spend_gold(uid, cost, 'craft_spend', p_item, 'ench:'||p_idem);
  update public.cloud_inventory set enchant_level = enchant_level + 1, updated_at = now() where id = inv.id;
  insert into public.cloud_inventory_tx(user_id,item_key,kind,delta,idempotency_key)
  values (uid,p_item,'enchant',0,'en:'||p_idem)
  on conflict (user_id,idempotency_key) do nothing;
  return jsonb_build_object('level', inv.enchant_level + 1, 'gold_spent', cost);
end; $$;

-- 5B-7: RLS + grants (client hanya baca sendiri; mutasi lewat RPC)
alter table public.cloud_inventory enable row level security;
create policy cloud_inventory_select_own on public.cloud_inventory
  for select to authenticated using (user_id = auth.uid());
alter table public.cloud_inventory_tx enable row level security;
create policy cloud_inventory_tx_select_own on public.cloud_inventory_tx
  for select to authenticated using (user_id = auth.uid());
alter table public.cloud_shop_purchases enable row level security;
create policy cloud_shop_purchases_select_own on public.cloud_shop_purchases
  for select to authenticated using (user_id = auth.uid());
alter table public.cloud_crafts enable row level security;
create policy cloud_crafts_select_own on public.cloud_crafts
  for select to authenticated using (user_id = auth.uid());
alter table public.shop_items_server enable row level security;
create policy shop_items_read on public.shop_items_server for select to authenticated using (true);
alter table public.recipes_server enable row level security;
create policy recipes_read on public.recipes_server for select to authenticated using (true);

revoke insert, update, delete on public.cloud_inventory from authenticated, anon, public;
revoke insert, update, delete on public.cloud_inventory_tx from authenticated, anon, public;
revoke insert, update, delete on public.cloud_shop_purchases from authenticated, anon, public;
revoke insert, update, delete on public.cloud_crafts from authenticated, anon, public;
revoke insert, update, delete on public.shop_items_server from authenticated, anon, public;
revoke insert, update, delete on public.recipes_server from authenticated, anon, public;
revoke execute on function public.buy_shop_item(text, integer, text) from public, anon;
revoke execute on function public.craft_item_cloud(text, text) from public, anon;
revoke execute on function public.equip_item_cloud(text, boolean) from public, anon;
revoke execute on function public.enchant_item_cloud(text, text) from public, anon;
revoke execute on function public.spend_gold(uuid, integer, text, text, text) from public, anon, authenticated;
grant execute on function public.buy_shop_item(text, integer, text) to authenticated;
grant execute on function public.craft_item_cloud(text, text) to authenticated;
grant execute on function public.equip_item_cloud(text, boolean) to authenticated;
grant execute on function public.enchant_item_cloud(text, text) to authenticated;
