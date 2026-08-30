import React from 'react';
import { useGame } from '../../context/GameContext';
import { liveShopItems, liveRecipes } from '../../data/liveCatalog';
import { t } from '../../i18n';

const tr = (key: string, vars?: Record<string, string | number>) => {
  let s = t(key, key);
  if (!vars) return s;
  // Dukung placeholder bentuk {name} dan spec python {name:.0f}/{name:0.1f}
  s = s.replace(/\{(\w+)(:[^}]*)?\}/g, (m, name, spec) => {
    if (!(name in vars)) return m;
    const v: any = (vars as any)[name];
    return String(typeof v === 'number' && spec ? (Math.round(v * 10) / 10) : v);
  });
  return s;
};

export const CraftView: React.FC = () => {
  const { user, inventory, craftItem, lang } = useGame();
  const SHOP_ITEMS = liveShopItems() as Record<string, any>;
  const CRAFT_RECIPES = liveRecipes() as any[];

  // Parity CraftingPage.load: owned = item_id output ada di inventory (max 1 per resep)
  const ownedIds = new Set(inventory.map((i) => i.itemId));
  const ownedQty = new Map(inventory.map((i) => [i.itemId, i.quantity || 0]));

  return (
    <div className="px-4 md:px-8 pb-24 pt-4 max-w-7xl mx-auto space-y-4 animate-fade-in-up">
      {/* Header halaman (parity PageHeader('crafting')) */}
      <header>
        <p className="text-[11px] uppercase tracking-[0.2em] text-amber-400/80 font-bold">
          {tr('page_crafting_subtitle')}
        </p>
        <h2 className="text-2xl font-black text-slate-100">{tr('page_crafting_title')}</h2>
      </header>

      <div className="space-y-3">
        {CRAFT_RECIPES.map((r: any) => {
          const out = SHOP_ITEMS[r.resultItemId] || {};
          // desc per bahasa (parity r["desc"][0/1])
          const desc = (lang === 'id'
            ? (r.descId || out.desc || '')
            : (r.descEn || r.descId || out.desc || '')) as string;

          // can_craft parity: input minimal 1; gold_ok terpisah
          const invIds = new Set(inventory.filter((i) => (i.quantity || 0) >= 1).map((i) => i.itemId));
          const goldNeed = r.goldCost || r.gold || 0;
          const goldOk = (user.gold || 0) >= goldNeed;
          const missing = (r.requiredItems || []).filter((req: any) => !invIds.has(req.itemId));
          const ok = missing.length === 0 && goldOk;
          const ownedAlready = ownedIds.has(r.resultItemId);

          return (
            <div key={String(r.id || r.resultItemId)}
              className="p-4 rounded-2xl bg-slate-900/80 border border-slate-800 space-y-2">
              {/* Header: icon + nama output + buff + desc */}
              <div className="flex items-start gap-3">
                <div className="w-12 h-12 rounded-xl bg-slate-800 border border-amber-500/40 flex items-center justify-center text-3xl shrink-0">
                  {out.icon || '🔨'}
                </div>
                <div>
                  <h4 className="font-extrabold text-sm text-slate-100">
                    {out.name || r.resultItemId}
                  </h4>
                  <div className="text-[11px] font-bold text-emerald-400 mt-0.5">
                    {out.buffDesc || ''}
                  </div>
                  <p className="text-[11px] text-slate-400 mt-0.5">{desc}</p>
                </div>
              </div>

              {/* Materials (parity: [have]/[missing] tag + icon + nama; light/e05050) */}
              <div className="flex flex-wrap items-center gap-2.5 text-[11px]">
                <span className="text-slate-500">{tr('crafting_needs')}</span>
                {(r.requiredItems || []).map((req: any) => {
                  const it = SHOP_ITEMS[req.itemId] || {};
                  const have = (ownedQty.get(req.itemId) || 0) >= 1;
                  return (
                    <span key={req.itemId}
                      className={have ? 'text-amber-100' : 'text-rose-500'}>
                      {have ? tr('crafting_have_tag') : tr('crafting_missing_tag')}{' '}
                      {it.icon || '❔'} {it.name || req.itemId}
                    </span>
                  );
                })}
              </div>

              {/* Gold + aksi (parity foot) */}
              <div className="flex items-center gap-3 pt-1">
                <span className={`text-[11px] font-bold ${goldOk ? 'text-amber-300' : 'text-rose-500'}`}>
                  {tr('crafting_gold_cost', { gold: goldNeed })}
                </span>
                {!goldOk && (
                  <span className="text-[10px] text-slate-500">
                    {tr('crafting_gold_short', { have: Math.floor(user.gold || 0), need: goldNeed })}
                  </span>
                )}
                <span className="flex-1" />
                {ownedAlready ? (
                  <span className="text-[11px] font-bold text-amber-100">{tr('crafting_owned')}</span>
                ) : (
                  <button type="button" disabled={!ok}
                    onClick={() => craftItem(r.resultItemId)}
                    className={`min-w-[130px] px-4 py-2 rounded-lg font-black text-[11px] ${
                      ok ? 'bg-amber-500 hover:bg-amber-400 text-slate-950'
                         : 'bg-slate-800 text-slate-500 cursor-not-allowed'
                    }`}>
                    {tr('crafting_btn')}
                  </button>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};
