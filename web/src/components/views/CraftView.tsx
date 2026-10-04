import React, { useState } from 'react';
import { PageSignature } from '../ui/SignatureKit';
import { useGame } from '../../context/GameContext';
import { liveShopItems, liveRecipes } from '../../data/liveCatalog';
import { t } from '../../i18n';

const tr = (key: string, vars?: Record<string, string | number>) => {
  let s = t(key, key);
  if (!vars) return s;
  s = s.replace(/\{(\w+)(:[^}]*)?\}/g, (m, name, spec) => {
    if (!(name in vars)) return m;
    const v: any = (vars as any)[name];
    return String(typeof v === 'number' && spec ? Math.round(v * 10) / 10 : v);
  });
  return s;
};

/**
 * v1.7.4 rev — CraftView bergaya CRAFTING TABLE Minecraft: panel kayu dengan
 * slot bahan ber-bevel, panah animasi ke slot hasil, dan tombol craft yang
 * "ditempa" (shake + pop saat berhasil). Logika can_craft/gold/owned tetap
 * parity CraftingPage lama — hanya presentasi yang berubah.
 */
export const CraftView: React.FC = () => {
  const { user, inventory, craftItem, lang } = useGame();
  const SHOP_ITEMS = liveShopItems() as Record<string, any>;
  const CRAFT_RECIPES = liveRecipes() as any[];
  const [craftingId, setCraftingId] = useState<string | null>(null);

  // Parity CraftingPage.load: owned = item_id output ada di inventory (max 1 per resep)
  const ownedIds = new Set(inventory.map((i) => i.itemId));
  const ownedQty = new Map(inventory.map((i) => [i.itemId, i.quantity || 0]));
  const invIds = new Set(inventory.filter((i) => (i.quantity || 0) >= 1).map((i) => i.itemId));

  const doCraft = (r: any) => {
    const key = String(r.id || r.resultItemId);
    if (craftingId) return; // satu tempaan berjalan pada satu waktu
    setCraftingId(key);
    window.setTimeout(() => {
      craftItem(r.resultItemId);
      setCraftingId(null);
    }, 750);
  };

  return (
    <div className="px-4 md:px-8 pb-24 pt-4 max-w-7xl mx-auto space-y-4 animate-fade-in-up">
      <PageSignature
        icon={<span className="text-xl">🔨</span>}
        title={tr('page_crafting_title')}
        tagline={tr('page_crafting_subtitle')}
        accent="#fb923c"
        pattern="circuit"
      />

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {CRAFT_RECIPES.map((r: any) => {
          const key = String(r.id || r.resultItemId);
          const out = SHOP_ITEMS[r.resultItemId] || {};
          const desc = (lang === 'id'
            ? (r.descId || out.desc || '')
            : (r.descEn || r.descId || out.desc || '')) as string;

          const goldNeed = r.goldCost || r.gold || 0;
          const goldOk = (user.gold || 0) >= goldNeed;
          const missing = (r.requiredItems || []).filter((req: any) => !invIds.has(req.itemId));
          const ok = missing.length === 0 && goldOk;
          const ownedAlready = ownedIds.has(r.resultItemId);
          const isCrafting = craftingId === key;

          return (
            <div key={key} className={`ct-craft-table${isCrafting ? ' ct-craft-table--on' : ''}`}>
              {/* Header: nama hasil + buff + desc */}
              <div className="flex items-start gap-3 mb-3">
                <div className="min-w-0 flex-1">
                  <h4 className="font-black text-sm text-amber-100 truncate">{out.name || r.resultItemId}</h4>
                  {out.buffDesc ? <p className="text-[11px] font-bold text-emerald-300 mt-0.5">{out.buffDesc}</p> : null}
                  {desc ? <p className="text-[11px] text-amber-200/70 mt-0.5 line-clamp-2">{desc}</p> : null}
                </div>
                <span className={`shrink-0 text-[11px] font-black px-2 py-1 rounded-lg ${goldOk ? 'bg-amber-900/60 text-amber-200' : 'bg-rose-950/70 text-rose-300'}`}>
                  {tr('crafting_gold_cost', { gold: goldNeed })}
                </span>
              </div>

              {/* Meja: slot bahan ➜ slot hasil */}
              <div className="flex items-center gap-3">
                <div className="ct-craft-grid">
                  {(r.requiredItems || []).map((req: any) => {
                    const it = SHOP_ITEMS[req.itemId] || {};
                    const have = (ownedQty.get(req.itemId) || 0) >= 1;
                    return (
                      <div key={req.itemId} className={`ct-craft-slot${have ? ' ct-craft-slot--ok' : ' ct-craft-slot--miss'}`}
                           title={it.name || req.itemId}>
                        <span className="text-xl" aria-hidden="true">{it.icon || '❔'}</span>
                        <span className="ct-craft-slot-name">{have ? tr('crafting_have_tag') : tr('crafting_missing_tag')}</span>
                      </div>
                    );
                  })}
                  {(r.requiredItems || []).length === 0 && (
                    <div className="ct-craft-slot"><span className="text-xl" aria-hidden="true">✦</span></div>
                  )}
                </div>

                <div className={`ct-craft-arrow${isCrafting ? ' ct-craft-arrow--on' : ''}`} aria-hidden="true">➜</div>

                <div className={`ct-craft-result${ok && !ownedAlready ? ' ct-craft-result--ready' : ''}${isCrafting ? ' ct-craft-result--pop' : ''}`}
                     title={out.name || r.resultItemId}>
                  <span className="text-3xl" aria-hidden="true">{out.icon || '🔨'}</span>
                </div>
              </div>

              {/* Footer aksi */}
              <div className="flex items-center gap-2 mt-3">
                {!goldOk && (
                  <span className="text-[10px] text-rose-300">
                    {tr('crafting_gold_short', { have: Math.floor(user.gold || 0), need: goldNeed })}
                  </span>
                )}
                <span className="flex-1" />
                {ownedAlready ? (
                  <span className="text-[11px] font-bold text-amber-100">{tr('crafting_owned')}</span>
                ) : (
                  <button type="button" disabled={!ok || !!craftingId}
                    onClick={() => doCraft(r)}
                    className={`ct-craft-btn${ok ? '' : ' opacity-50 cursor-not-allowed'}`}>
                    {isCrafting ? tr('crafting_working') : tr('crafting_btn')}
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
