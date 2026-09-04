import React, { useMemo } from 'react';
import { useGame } from '../../context/GameContext';
import { livePets } from '../../data/liveCatalog';
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

// Parity PetsPage: biaya UI (sama dengan database.feed_pet/train_pet)
const FEED_COST = 30;
const trainCost = (lvl: number) => 25 + (lvl - 1) * 5;
// Parity: exp untuk naik level = level * 100
const expNeeded = (lvl: number) => lvl * 100;
// Parity: skala buff per level = 1 + (level - 1) * 0.1
const buffScale = (lvl: number) => 1 + (lvl - 1) * 0.1;

export const PetsView: React.FC = () => {
  const { user, userPets, maxActivePets, adoptPet, feedPet, trainPet, equipPet, unequipPet } = useGame();
  const PETS_DATA = livePets() as Record<string, any>;

  const activeCount = userPets.filter((p) => p.isEquipped).length;
  const userLevel = user.level || 1;
  // P43: slot pet aktif bertingkat — nilai dari backend (db.max_active_pets),
  // BUKAN dihitung ulang di sini (aturan: rule hanya di database.py).
  const maxPets = maxActivePets;
  const statusVars = maxPets >= 2 ? { n: maxPets } : undefined;
  const statusKey = maxPets >= 2 ? 'pets_max_n' : 'pets_max_1';

  const ownedIds = useMemo(() => new Set(userPets.map((p) => p.petId)), [userPets]);

  return (
    <div className="px-4 md:px-8 pb-24 pt-4 max-w-7xl mx-auto space-y-4 animate-fade-in-up">
      {/* Header halaman (parity PageHeader('pets')) */}
      <header>
        <p className="text-[11px] uppercase tracking-[0.2em] text-amber-400/80 font-bold">
          {tr('page_pets_subtitle')}
        </p>
        <h2 className="text-2xl font-black text-slate-100">{tr('page_pets_title')}</h2>
      </header>

      {userPets.length === 0 ? (
        <p className="text-center text-sm text-slate-500 py-12">{tr('pets_empty')}</p>
      ) : (
        <>
          {/* Info aktif/maks (parity info_widget) */}
          <div className="rounded-2xl border border-slate-800 bg-slate-900/70 p-4 text-center">
            <p className="text-sm font-bold text-amber-200">
              {tr('pets_active_info', {
                active: activeCount, max: maxPets, level: userLevel, status: tr(statusKey, statusVars),
              })}
            </p>
          </div>

          {/* Grid kartu pet dimiliki (parity 3 kolom) */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
            {userPets.map((p) => {
              const meta = PETS_DATA[p.petId] || {};
              const need = expNeeded(p.level);
              const scale = buffScale(p.level);
              const base = (meta.baseBuff || meta.base_buff || {}) as Record<string, number>;
              const lines: string[] = [];
              if ('xp_pct' in base) lines.push(tr('pets_buff_xp_format', { val: +(base.xp_pct! * scale).toFixed(1) }));
              if ('gold_pct' in base) lines.push(tr('pets_buff_gold_format', { val: +(base.gold_pct! * scale).toFixed(1) }));
              if ('boss_dmg' in base) lines.push(tr('pets_buff_dmg_format', { val: +(base.boss_dmg! * scale).toFixed(1) }));
              if ('hp_reduc' in base) lines.push(tr('pets_buff_reduc_format', { val: +(base.hp_reduc! * scale).toFixed(1) }));

              return (
                <div key={p.petId}
                  className={`p-3 rounded-2xl border flex flex-col gap-2 ${
                    p.isEquipped ? 'bg-slate-900/90 border-lime-500/50' : 'bg-slate-900/80 border-slate-800'
                  }`}>
                  {/* Header: icon + nama + tag aktif */}
                  <div className="flex items-center gap-2">
                    <span className="text-3xl">{meta.icon || '🐾'}</span>
                    <span className="flex-1 text-sm font-bold text-slate-100">
                      {meta.name || p.petId}
                    </span>
                    {p.isEquipped && (
                      <span className="text-[10px] font-bold text-lime-400">{tr('shop_active')}</span>
                    )}
                  </div>

                  {/* Level & EXP (parity exp_bar format) */}
                  <div className="text-[11px] font-bold text-amber-400">
                    {tr('pets_level_label', { level: p.level })}
                  </div>
                  <div className="relative h-2 rounded-full bg-slate-800 overflow-hidden">
                    <div className="h-full bg-gradient-to-r from-amber-500 to-amber-300"
                      style={{ width: `${Math.min(100, Math.round(((p.xp || 0) / need) * 100))}%` }} />
                  </div>
                  <div className="text-[10px] text-slate-500 font-mono">
                    {tr('pets_exp_format', { exp: p.xp || 0, need })}
                  </div>

                  {/* Hunger (parity hunger_bar chunk #f0a800) */}
                  <div className="relative h-3 rounded-full bg-slate-800 overflow-hidden">
                    <div className="h-full bg-amber-500"
                      style={{ width: `${Math.min(100, Math.max(0, p.hunger ?? 100))}%` }} />
                    <span className="absolute inset-0 flex items-center justify-center text-[9px] font-bold text-slate-100">
                      {tr('pets_hunger', { hunger: p.hunger ?? 100 })}
                    </span>
                  </div>

                  {/* Buff lines terskala level (parity) */}
                  {lines.length > 0 && (
                    <div className="text-[10px] text-cyan-300">{lines.join(' | ')}</div>
                  )}

                  {/* Tombol (parity: unequip/equip + feed + train) */}
                  <div className="flex flex-wrap gap-2 pt-1">
                    {p.isEquipped ? (
                      <button type="button" onClick={() => unequipPet(p.petId)}
                        className="min-w-[80px] px-2 py-1.5 rounded-lg bg-rose-900/40 hover:bg-rose-900/70 text-rose-300 text-[11px] font-bold">
                        {tr('shop_unequip')}
                      </button>
                    ) : (
                      <button type="button" onClick={() => equipPet(p.petId)}
                        className="min-w-[80px] px-2 py-1.5 rounded-lg bg-sky-600 hover:bg-sky-500 text-white text-[11px] font-bold">
                        {tr('shop_equip')}
                      </button>
                    )}
                    <button type="button" onClick={() => feedPet(p.petId)}
                      className="min-w-[70px] px-2 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-amber-300 text-[11px] font-bold">
                      🍖 {tr('pets_feed', { cost: FEED_COST })}
                    </button>
                    <button type="button" onClick={() => trainPet(p.petId)}
                      className="min-w-[70px] px-2 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-sky-300 text-[11px] font-bold">
                      ⚡ {tr('pets_train', { cost: trainCost(p.level) })}
                    </button>
                  </div>
                </div>
              );
            })}
          </div>
        </>
      )}

      {/* ── Adoption market (parity ShopPage tab Pets bagian belum dimiliki) ── */}
      <div className="space-y-3 pt-4 border-t border-slate-800">
        <h3 className="font-bold text-sm text-slate-200">
          {tr('adoption_sanctuary')}
        </h3>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
          {Object.entries(PETS_DATA).map(([pid, pet]: [string, any]) => {
            const isOwned = ownedIds.has(pid);
            const canAfford = (user.gold || 0) >= (pet.cost || 0);
            return (
              <div key={pid}
                className="p-3 rounded-2xl bg-slate-900/60 border border-slate-800 flex items-center justify-between gap-3">
                <div className="flex items-center gap-3">
                  <span className="text-3xl">{pet.icon}</span>
                  <div>
                    <h4 className="font-bold text-sm text-slate-100">{pet.name}</h4>
                    <div className="text-[10px] font-bold text-cyan-300">{pet.bonus}</div>
                    <div className="text-xs font-bold text-amber-300 mt-0.5">💰 {pet.cost} G</div>
                  </div>
                </div>
                {isOwned ? (
                  <span className="px-3 py-1 rounded-xl bg-slate-800 text-emerald-400 text-xs font-bold">
                    {tr('shop_owned')}
                  </span>
                ) : (
                  <button type="button" onClick={() => adoptPet(pid)} disabled={!canAfford}
                    className={`px-3.5 py-2 rounded-xl font-bold text-xs ${
                      canAfford ? 'bg-amber-500 hover:bg-amber-400 text-slate-950'
                                : 'bg-slate-800 text-slate-400 cursor-not-allowed'
                    }`}>
                    {tr('shop_adopt')}
                  </button>
                )}
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
};
