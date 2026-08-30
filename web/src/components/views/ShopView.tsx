import React, { useMemo, useState } from 'react';
import { useGame } from '../../context/GameContext';
import { liveShopItems, livePets } from '../../data/liveCatalog';
import { t } from '../../i18n';

const tr = (key: string, vars?: Record<string, string | number>) => {
  let s = t(key, key);
  if (!vars) return s;
  s = s.replace(/\{(\w+)(:[^}]*)?\}/g, (m, name, spec) => {
    if (!(name in vars)) return m;
    const v: any = (vars as any)[name];
    return String(typeof v === 'number' && spec ? (Math.round(v * 10) / 10) : v);
  });
  return s;
};

const EQUIP_TYPES = ['weapon', 'armor', 'shoes', 'accessory'] as const;
const enchantCost = (lvl: number) => (lvl + 1) * 50; // parity ENCHANT_COST_FORMULA client-side display
const sellPriceOf = (cost: number) => Math.max(1, Math.floor(cost * 0.1));

/** Parity ShopPage (MainPyQt6.py): buff bar + tab Items/Pets + kartu dengan
 * owned/use/buy again/sell/enchant/adopt/equip/unequip + SellDialog qty. */
export const ShopView: React.FC = () => {
  const {
    user, inventory, userPets, activeBuffs,
    buyItem, sellItem, useConsumable, equipItem, unequipItem,
    adoptPet, equipPet, unequipPet, enchantItem, lang,
  } = useGame();
  const SHOP_ITEMS = liveShopItems() as Record<string, any>;
  const PETS_DATA = livePets() as Record<string, any>;

  const [tab, setTab] = useState<'items' | 'pets'>('items');
  const [sellDlg, setSellDlg] = useState<{ inv: any; it: any } | null>(null);

  const invMap = useMemo(() => new Map(inventory.map((i: any) => [i.itemId, i])), [inventory]);
  const ownedPetIds = useMemo(() => new Set(userPets.map((p) => p.petId)), [userPets]);
  const activePetIds = useMemo(() => new Set(userPets.filter((p) => p.isEquipped).map((p) => p.petId)), [userPets]);

  // ── Buff bar (parity db.get_all_active_buffs) ──
  const buffText = activeBuffs && activeBuffs.length
    ? `⚡ Buff Aktif :  ${activeBuffs.join('  ·  ')}`
    : '⚡ Buff Aktif :  Tidak ada buff aktif.';

  const visibleItems = useMemo(
    () => Object.entries(SHOP_ITEMS)
      .map(([id, it]: [string, any]) => ({ id, ...it }))
      .filter((it: any) => it.visible !== false)
      .filter((it: any) => !(it.seasonal && it.available === false)),
    [SHOP_ITEMS],
  );

  const gold = user.gold || 0;

  return (
    <div className="px-4 md:px-8 pb-24 pt-4 max-w-7xl mx-auto space-y-4 animate-fade-in-up">
      {/* Header (parity _page_header('shop')) */}
      <header>
        <p className="text-[11px] uppercase tracking-[0.2em] text-amber-400/80 font-bold">
          {tr('page_shop_subtitle')}
        </p>
        <h2 className="text-2xl font-black text-slate-100">{tr('page_shop_title')}</h2>
      </header>

      {/* Buff bar */}
      <div className="rounded-lg border border-slate-800 bg-slate-900/70 px-3.5 py-2.5 text-xs text-amber-300">
        {buffText}
      </div>

      {/* Tabs (parity _tabs items/pets) */}
      <div className="inline-flex rounded-2xl bg-slate-900 border border-slate-800 p-1 gap-1">
        {(['items', 'pets'] as const).map((tb) => (
          <button key={tb} type="button" onClick={() => setTab(tb)}
            className={`px-4 py-2 rounded-xl text-xs font-bold tracking-wider transition-all ${tab === tb
              ? 'bg-amber-500 text-slate-950 shadow-[0_2px_12px_rgba(251,191,36,0.35)]'
              : 'text-slate-400 hover:text-slate-200'}`}>
            {tb === 'items' ? tr('shop_tab_items') : tr('shop_tab_pets')}
          </button>
        ))}
      </div>

      {/* ── TAB ITEMS (4 kolom) ── */}
      {tab === 'items' && (
        <section className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-3">
          {visibleItems.map((it: any) => {
            const inv: any = invMap.get(it.id);
            const qty = inv?.qty || 0;
            const owned = qty > 0;
            const elvl = Number(inv?.enchantLevel || inv?.enchant_level || 0);
            const cost = Number(it.cost || 0);
            return (
              <div key={it.id}
                className="p-3 rounded-2xl bg-slate-900/80 border border-slate-800 flex flex-col gap-1.5 text-center">
                <span className="text-3xl">{it.icon}</span>
                <span className="text-xs font-bold text-slate-100">{it.name}</span>
                {it.seasonal && (
                  <span className="text-[9px] font-bold text-teal-400">{tr('shop_seasonal_badge')}</span>
                )}
                <p className="text-[10px] text-amber-300 leading-relaxed">{it.buffDesc || it.buff_desc || ''}</p>
                <p className="text-[10px] text-slate-500">{tr(`shop_type_${it.type}`)}</p>

                {owned ? (
                  <>
                    <span className="text-[11px] font-bold text-sky-300">{tr('shop_owned')}</span>
                    {it.type === 'consumable' ? (
                      <>
                        <button type="button" onClick={() => useConsumable(it.id)}
                          className="h-[30px] rounded-xl bg-sky-600 hover:bg-sky-500 text-white text-[11px] font-bold">
                          {tr('shop_use', { qty })}
                        </button>
                        <button type="button" onClick={() => buyItem(it.id)}
                          className="h-[30px] rounded-xl bg-amber-500 hover:bg-amber-400 text-slate-950 text-[11px] font-black">
                          {tr('shop_buy_again')}
                        </button>
                        <button type="button"
                          onClick={() => setSellDlg({ inv, it })}
                          className="h-[30px] rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-200 text-[11px] font-bold">
                          {tr('shop_sell')}
                        </button>
                        <span className="text-[10px] text-slate-500">{tr('shop_sell_price', { gold: sellPriceOf(cost) })}</span>
                      </>
                    ) : (
                      <>
                        {/* equip/unequip untuk tipe equipment (parity toggle via _stats/_equipped) */}
                        {EQUIP_TYPES.includes(it.type as any) && (
                          inv?.equipped ? (
                            <button type="button" onClick={() => unequipItem(it.id)}
                              className="h-[30px] rounded-xl bg-rose-900/50 hover:bg-rose-900/80 text-rose-200 text-[11px] font-bold">
                              {tr('shop_unequip')}
                            </button>
                          ) : (
                            <button type="button" onClick={() => equipItem(it.id)}
                              className="h-[30px] rounded-xl bg-emerald-700 hover:bg-emerald-600 text-white text-[11px] font-bold">
                              {tr('shop_equip')}
                            </button>
                          )
                        )}
                        <button type="button"
                          onClick={() => setSellDlg({ inv, it })}
                          className="h-[30px] rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-200 text-[11px] font-bold">
                          {tr('shop_sell')}
                        </button>
                        <span className="text-[10px] text-slate-500">{tr('shop_sell_price', { gold: sellPriceOf(cost) })}</span>
                        {/* Enchanting (parity _enchant, equipment saja) */}
                        {equipTypesWithEnchant(it.type) && (
                          <>
                            {elvl > 0 && (
                              <span className="text-[11px] font-bold text-violet-400">{tr('enchant_level_tag', { lvl: elvl })}</span>
                            )}
                            {elvl >= 5 ? (
                              <span className="text-[10px] font-bold text-violet-400">{tr('enchant_max_tag')}</span>
                            ) : (
                              <button type="button" onClick={() => {
                                const c = enchantCost(elvl);
                                if ((user.xp || 0) < c) return;
                                enchantItem(it.id);
                              }}
                                className="h-[30px] rounded-xl bg-violet-700 hover:bg-violet-600 text-white text-[11px] font-bold disabled:opacity-40"
                                disabled={(user.xp || 0) < enchantCost(elvl)}
                                title={(user.xp || 0) < enchantCost(elvl) ? tr('db_enchant_no_xp', { cost: enchantCost(elvl) }) : undefined}>
                                {tr(elvl > 0 ? 'enchant_btn' : 'enchant_first_btn', { lvl: elvl + 1, cost: enchantCost(elvl) })}
                              </button>
                            )}
                          </>
                        )}
                      </>
                    )}
                  </>
                ) : (
                  <>
                    <span className="text-xs font-black text-amber-400">💰 {cost} G</span>
                    <button type="button" onClick={() => buyItem(it.id)} disabled={gold < cost}
                      className="h-[30px] rounded-xl bg-amber-500 hover:bg-amber-400 text-slate-950 text-[11px] font-black disabled:opacity-40 disabled:cursor-not-allowed">
                      {tr('shop_buy')}
                    </button>
                  </>
                )}
              </div>
            );
          })}
        </section>
      )}

      {/* ── TAB PETS (3 kolom) ── */}
      {tab === 'pets' && (
        <section className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
          {Object.entries(PETS_DATA).map(([pid, pet]: [string, any]) => {
            const owned = ownedPetIds.has(pid);
            const active = activePetIds.has(pid);
            return (
              <div key={pid} className="p-3 rounded-2xl bg-slate-900/80 border border-slate-800 flex flex-col gap-1.5 text-center">
                <span className="text-3xl">{pet.icon}</span>
                <span className="text-xs font-bold text-slate-100">{pet.name}</span>
                <p className="text-[10px] font-bold text-cyan-300 leading-relaxed">{pet.bonus}</p>
                {owned ? (
                  active ? (
                    <>
                      <span className="text-[11px] font-bold text-cyan-300">{tr('shop_active')}</span>
                      <button type="button" onClick={() => unequipPet(pid)}
                        className="h-[30px] rounded-xl bg-rose-900/50 hover:bg-rose-900/80 text-rose-200 text-[11px] font-bold">
                        {tr('shop_unequip')}
                      </button>
                    </>
                  ) : (
                    <button type="button" onClick={() => equipPet(pid)}
                      className="h-[30px] rounded-xl bg-sky-600 hover:bg-sky-500 text-white text-[11px] font-bold">
                      {tr('shop_equip')}
                    </button>
                  )
                ) : (
                  <>
                    <span className="text-xs font-black text-amber-400">💰 {pet.cost} G</span>
                    <button type="button" onClick={() => adoptPet(pid)} disabled={gold < (pet.cost || 0)}
                      className="h-[30px] rounded-xl bg-amber-500 hover:bg-amber-400 text-slate-950 text-[11px] font-black disabled:opacity-40 disabled:cursor-not-allowed">
                      {tr('shop_adopt')}
                    </button>
                  </>
                )}
              </div>
            );
          })}
        </section>
      )}

      {/* SellDialog (parity _sell_item) */}
      {sellDlg && (
        <SellDialog inv={sellDlg.inv} it={sellDlg.it}
          onClose={() => setSellDlg(null)}
          onSell={(qty) => {
            sellItem(sellDlg.it.id, qty);
            setSellDlg(null);
          }} />
      )}
    </div>
  );
};

function equipTypesWithEnchant(tp: string): boolean {
  // Parity ShopPage: enchant hanya untuk equipment (weapon/armor/shoes/accessory)
  return (EQUIP_TYPES as readonly string[]).includes(tp);
}

function SellDialog({ inv, it, onClose, onSell }: {
  inv: any; it: any; onClose: () => void; onSell: (qty: number) => void;
}) {
  const pricePer = sellPriceOf(Number(it.cost || 0));
  const maxQty = Math.max(1, inv?.qty || 1);
  const [qty, setQty] = useState(1);

  return (
    <div className="fixed inset-0 z-[70] flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-sm" onClick={onClose}>
      <div className="max-w-sm w-full bg-slate-900 border border-slate-700 rounded-2xl p-6 shadow-2xl space-y-4"
        style={{ minWidth: 300 }}
        onClick={(e) => e.stopPropagation()}>
        <h3 className="text-lg font-black text-slate-100">{tr('shop_sell_title')}</h3>
        <p className="text-sm text-slate-300">
          {tr('shop_sell_confirm', { name: it.name, qty: 1, gold: pricePer })}
        </p>
        <div className="flex items-center gap-3">
          <input type="number" min={1} max={maxQty} value={qty}
            onChange={(e) => setQty(Math.min(Math.max(1, Number(e.target.value) || 1), maxQty))}
            className="w-24 px-3 py-2 rounded-xl bg-slate-950 border border-slate-800 text-sm text-slate-100" />
          <span className="text-xs text-slate-500">(max {maxQty})</span>
          <span className="text-xs font-bold text-amber-400">= 💰 {pricePer * qty} G</span>
        </div>
        <div className="flex items-center justify-end gap-2 pt-1">
          <button type="button" onClick={onClose}
            className="px-4 py-2 rounded-xl bg-slate-800 text-slate-300 text-xs font-semibold">{tr('btn_cancel')}</button>
          <button type="button" onClick={() => onSell(qty)}
            className="px-4 py-2 rounded-xl bg-amber-500 hover:bg-amber-400 text-slate-950 font-bold text-xs">
            {tr('shop_sell')}
          </button>
        </div>
      </div>
    </div>
  );
}
