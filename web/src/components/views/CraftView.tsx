import React from 'react';
import { useGame } from '../../context/GameContext';
import { liveShopItems, liveRecipes } from '../../data/liveCatalog';
import { t } from '../../i18n';
import { Hammer, Coins } from 'lucide-react';

export const CraftView: React.FC = () => {
  const { user, inventory, craftItem, lang } = useGame();
  const SHOP_ITEMS = liveShopItems();
  const CRAFT_RECIPES = liveRecipes();

  return (
    <div className="space-y-4">
      <div className="p-4 rounded-2xl bg-gradient-to-r from-amber-950/30 to-slate-900 border border-amber-500/30">
        <h2 className="text-xl font-black text-amber-300 flex items-center gap-2">
          <Hammer className="w-5 h-5" /> {t('web_craft_title', lang === 'id' ? 'Tempa & Resep' : 'Craft & Recipes')}
        </h2>
        <p className="text-xs text-slate-400 mt-1">
          {lang === 'id'
            ? 'Tempa di Python/SQLite (cloud jika ter-link). Tidak ada kalkulasi RPG di browser.'
            : 'Forging runs in Python/SQLite (cloud when linked). No RPG math in the browser.'}
        </p>
        {user.cloudLinked && (
          <p className="text-[11px] text-sky-300 mt-1">
            {t('cloud_shop_wallet', lang === 'id'
              ? `Craft memakai wallet cloud: ${(user.goldCloud ?? user.gold).toLocaleString()} Gold.`
              : `Craft uses cloud wallet: ${(user.goldCloud ?? user.gold).toLocaleString()} Gold.`)}
          </p>
        )}
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {CRAFT_RECIPES.map((recipe) => {
          const resultItem = SHOP_ITEMS[recipe.resultItemId];
          if (!resultItem) return null;
          const hasMaterials = recipe.requiredItems.every((req) => {
            const inv = inventory.find((i) => i.itemId === req.itemId && i.quantity >= req.quantity);
            return !!inv;
          });
          const canAffordForge = hasMaterials && user.gold >= recipe.goldCost;

          return (
            <div
              key={recipe.resultItemId}
              className="p-4.5 rounded-2xl bg-slate-900/80 border border-slate-800 flex flex-col justify-between gap-4"
            >
              <div>
                <div className="flex items-start gap-3 mb-3">
                  <div className="w-12 h-12 rounded-xl bg-slate-800 border border-amber-500/40 flex items-center justify-center text-3xl shrink-0">
                    {resultItem.icon}
                  </div>
                  <div>
                    <h4 className="font-extrabold text-sm text-amber-300">{resultItem.name}</h4>
                    <p className="text-xs text-slate-400 mt-0.5">{resultItem.desc}</p>
                    {resultItem.buffDesc && (
                      <div className="text-[11px] font-bold text-emerald-400 mt-1">✨ {resultItem.buffDesc}</div>
                    )}
                  </div>
                </div>
                <div className="space-y-1.5 pt-2 border-t border-slate-800">
                  <div className="text-[11px] font-bold text-slate-400 uppercase">
                    {lang === 'id' ? 'Bahan:' : 'Materials:'}
                  </div>
                  {recipe.requiredItems.map((req) => {
                    const neededItem = SHOP_ITEMS[req.itemId];
                    const inv = inventory.find((i) => i.itemId === req.itemId);
                    const currentQty = inv ? inv.quantity : 0;
                    const isMet = currentQty >= req.quantity;
                    return (
                      <div
                        key={req.itemId}
                        className={`flex items-center justify-between text-xs p-1.5 rounded-lg ${
                          isMet ? 'bg-emerald-950/30 text-emerald-300' : 'bg-slate-800/60 text-slate-400'
                        }`}
                      >
                        <span>{neededItem?.icon} {neededItem?.name || req.itemId}</span>
                        <span className="font-bold">{currentQty} / {req.quantity}</span>
                      </div>
                    );
                  })}
                </div>
              </div>
              <div className="flex items-center justify-between pt-3 border-t border-slate-800">
                <div className="flex items-center gap-1 font-bold text-xs text-amber-300">
                  <Coins className="w-4 h-4 text-amber-400" />
                  <span>{recipe.goldCost} Gold</span>
                </div>
                <button
                  type="button"
                  onClick={() => craftItem(recipe.resultItemId)}
                  disabled={!canAffordForge}
                  className={`px-4 py-2 rounded-xl font-bold text-xs flex items-center gap-1.5 ${
                    canAffordForge
                      ? 'bg-amber-500 hover:bg-amber-400 text-slate-950'
                      : 'bg-slate-800 text-slate-400 cursor-not-allowed'
                  }`}
                >
                  <Hammer className="w-3.5 h-3.5" />
                  {t('web_forge_item', lang === 'id' ? 'Tempa Senjata' : 'Forge Item')}
                </button>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};
