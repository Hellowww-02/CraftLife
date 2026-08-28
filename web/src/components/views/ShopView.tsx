import React, { useState } from 'react';
import { useGame } from '../../context/GameContext';
import { liveShopItems } from '../../data/liveCatalog';
import { ShopItemType } from '../../types';
import { t } from '../../i18n';
import { ShoppingBag, Coins, PackageOpen } from 'lucide-react';

export const ShopView: React.FC = () => {
  const { user, inventory, buyItem, sellItem, useConsumable, equipItem, unequipItem, enchantItem, lang } = useGame();
  const [activeTab, setActiveTab] = useState<'shop' | 'inventory'>('shop');
  const [shopCategory, setShopCategory] = useState<ShopItemType | 'all'>('all');

  const shopItemsList = Object.values(liveShopItems()).filter((item) => !item.craftOnly);
  const filteredShopItems = shopItemsList.filter((i) => {
    if (shopCategory === 'all') return true;
    return i.type === shopCategory;
  });

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <ShoppingBag className="w-6 h-6 text-yellow-400" />
            <h2 className="text-xl font-black text-slate-100">{t('web_shop_title', lang === 'id' ? 'Toko Perlengkapan & Pandai Besi' : 'Armory Shop & Crafting Forge')}</h2>
          </div>
          <p className="text-xs text-slate-400 mt-1">
            {lang === 'id'
              ? 'Beli senjata perkasa, armor pelindung, ramuan restorasi, atau tempa perlengkapan legendaris di Pandai Besi.'
              : 'Acquire mighty blades, protective armors, recovery elixirs, or forge legendary mythic gear at the Forge.'}
          </p>
          {user.cloudLinked && (
            <p className="text-[11px] text-sky-300 mt-1">
              {t('cloud_shop_wallet', lang === 'id'
                ? `Toko memakai wallet cloud: ${(user.goldCloud ?? user.gold).toLocaleString()} Gold (lokal ${ (user.goldLocal ?? 0).toLocaleString() }).`
                : `Shop uses cloud wallet: ${(user.goldCloud ?? user.gold).toLocaleString()} Gold (local ${ (user.goldLocal ?? 0).toLocaleString() }).`)}
            </p>
          )}
        </div>

        <div className="flex items-center gap-2 bg-slate-900 border border-slate-800 p-1 rounded-xl text-xs">
          <button
            onClick={() => setActiveTab('shop')}
            className={`px-3 py-1.5 rounded-lg font-bold transition-all ${
              activeTab === 'shop' ? 'bg-yellow-500 text-slate-950 shadow' : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            {lang === 'id' ? '🛒 Toko' : '🛒 Shop'}
          </button>
          <button
            onClick={() => setActiveTab('inventory')}
            className={`px-3 py-1.5 rounded-lg font-bold transition-all ${
              activeTab === 'inventory' ? 'bg-yellow-500 text-slate-950 shadow' : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            {lang === 'id' ? '🎒 Tas Inventory' : '🎒 Inventory'} ({inventory.length})
          </button>
        </div>
      </div>

      {/* SHOP VIEW */}
      {activeTab === 'shop' && (
        <div className="space-y-4">
          {/* Categories */}
          <div className="flex items-center gap-2 overflow-x-auto pb-1 text-xs">
            {(['all', 'weapon', 'armor', 'tool', 'consumable', 'legendary'] as const).map((cat) => (
              <button
                key={cat}
                onClick={() => setShopCategory(cat)}
                className={`px-3 py-1.5 rounded-xl font-semibold capitalize shrink-0 transition-colors ${
                  shopCategory === cat
                    ? 'bg-yellow-500/20 text-yellow-300 border border-yellow-500/40'
                    : 'bg-slate-800/80 text-slate-400 hover:text-slate-200'
                }`}
              >
                {cat}
              </button>
            ))}
          </div>

          {/* Shop Item Grid */}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
            {filteredShopItems.map((item) => {
              const inInventory = inventory.find((i) => i.itemId === item.id);
              const canAfford = user.gold >= item.cost;

              return (
                <div
                  key={item.id}
                  className="p-4 rounded-2xl bg-slate-900/80 border border-slate-800 hover:border-slate-700 flex flex-col justify-between gap-4 transition-all shadow-sm"
                >
                  <div className="flex items-start gap-3">
                    <div className="w-12 h-12 rounded-xl bg-slate-800 border border-slate-700 flex items-center justify-center text-2xl shrink-0">
                      {item.icon}
                    </div>
                    <div className="min-w-0">
                      <div className="flex items-center gap-1.5">
                        <h4 className="font-bold text-sm text-slate-100 truncate">{item.name}</h4>
                        <span className="px-1.5 py-0.5 text-[9px] font-bold uppercase rounded-full bg-slate-800 text-slate-400">
                          {item.type}
                        </span>
                      </div>
                      <p className="text-xs text-slate-400 mt-1 line-clamp-2">{item.desc}</p>
                      {item.buffDesc && (
                        <div className="text-[11px] font-bold text-emerald-400 mt-1">
                          ✨ {item.buffDesc}
                        </div>
                      )}
                    </div>
                  </div>

                  <div className="flex items-center justify-between pt-3 border-t border-slate-800">
                    <div className="flex items-center gap-1 font-black text-amber-300 text-xs">
                      <Coins className="w-4 h-4 text-amber-400" />
                      <span>{item.cost} Gold</span>
                    </div>

                    <button
                      onClick={() => buyItem(item.id)}
                      disabled={!canAfford}
                      className={`px-3 py-1.5 rounded-xl font-bold text-xs flex items-center gap-1 transition-all ${
                        canAfford
                          ? 'bg-yellow-500 hover:bg-yellow-400 text-slate-950 shadow-md active:scale-95'
                          : 'bg-slate-800 text-slate-400 cursor-not-allowed'
                      }`}
                    >
                      <ShoppingBag className="w-3.5 h-3.5" />
                      <span>{inInventory ? (lang === 'id' ? 'Beli Lagi' : 'Buy More') : (lang === 'id' ? 'Beli' : 'Purchase')}</span>
                    </button>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* INVENTORY VIEW */}
      {activeTab === 'inventory' && (
        <div className="space-y-4">
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
            {inventory.map((inv) => {
              const item = (liveShopItems() as Record<string, any>)[inv.itemId];
              if (!item) return null;

              const isConsumable = item.type === 'consumable';

              return (
                <div
                  key={inv.itemId}
                  className={`p-4 rounded-2xl border flex flex-col justify-between gap-4 transition-all ${
                    inv.equipped
                      ? 'bg-yellow-950/20 border-yellow-500/50 shadow-md shadow-yellow-500/10'
                      : 'bg-slate-900/80 border-slate-800'
                  }`}
                >
                  <div className="flex items-start gap-3">
                    <div className="w-12 h-12 rounded-xl bg-slate-800 border border-slate-700 flex items-center justify-center text-2xl shrink-0">
                      {item.icon}
                    </div>
                    <div className="min-w-0">
                      <div className="flex items-center gap-1.5">
                        <h4 className="font-bold text-sm text-slate-100 truncate">{item.name}</h4>
                        {inv.quantity > 1 && (
                          <span className="px-1.5 py-0.5 text-[10px] font-bold rounded-full bg-slate-800 text-amber-400">
                            x{inv.quantity}
                          </span>
                        )}
                      </div>
                      <p className="text-xs text-slate-400 mt-1">{item.desc}</p>
                      {(inv.enchantLevel || 0) > 0 && (
                        <div className="text-[11px] font-bold text-fuchsia-300 mt-1">+{inv.enchantLevel} enchant</div>
                      )}
                      {item.buffDesc && (
                        <div className="text-[11px] font-bold text-emerald-400 mt-1">
                          ✨ {item.buffDesc}
                        </div>
                      )}
                    </div>
                  </div>

                  <div className="flex items-center justify-between pt-3 border-t border-slate-800 gap-2">
                    <button
                      onClick={() => sellItem(item.id)}
                      className="px-2.5 py-1 rounded-lg text-slate-400 hover:text-slate-200 text-xs font-semibold hover:bg-slate-800"
                    >
                      {lang === 'id' ? 'Jual (+40%)' : 'Sell (+40%)'}
                    </button>

                    <div className="flex items-center gap-2">
                      {isConsumable ? (
                        <button
                          onClick={() => useConsumable(item.id)}
                          className="px-3 py-1.5 rounded-xl bg-emerald-500 hover:bg-emerald-400 text-slate-950 font-bold text-xs"
                        >
                          {lang === 'id' ? 'Gunakan' : 'Use Item'}
                        </button>
                      ) : (
                        <>
                          <button
                            onClick={() => enchantItem(item.id)}
                            className="px-2 py-1.5 rounded-xl bg-fuchsia-500/20 border border-fuchsia-500/40 text-fuchsia-200 font-bold text-xs"
                          >
                            {t('web_enchant', lang === 'id' ? 'Enchant' : 'Enchant')}
                          </button>
                      {inv.equipped ? (
                        <button
                          onClick={() => unequipItem(item.id)}
                          className="px-3 py-1.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-300 font-bold text-xs"
                        >
                          {lang === 'id' ? 'Lepas' : 'Unequip'}
                        </button>
                      ) : (
                        <button
                          onClick={() => equipItem(item.id)}
                          className="px-3 py-1.5 rounded-xl bg-yellow-500 hover:bg-yellow-400 text-slate-950 font-bold text-xs"
                        >
                          {lang === 'id' ? 'Pakai' : 'Equip'}
                        </button>
                      )}
                        </>
                      )}
                    </div>
                  </div>
                </div>
              );
            })}
          </div>

          {inventory.length === 0 && (
            <div className="text-center py-12 text-slate-400 bg-slate-900/40 rounded-2xl border border-slate-800/80">
              <PackageOpen className="w-8 h-8 text-yellow-500/40 mx-auto mb-2" />
              <p className="text-sm font-semibold">{lang === 'id' ? 'Tas Inventory masih kosong.' : 'Inventory is empty.'}</p>
            </div>
          )}
        </div>
      )}

    </div>
  );
};
