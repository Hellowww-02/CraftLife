import React, { useMemo, useState } from 'react';
import { useGame } from '../../context/GameContext';
import { liveShopItems } from '../../data/liveCatalog';
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

/* Parity database.py (L07): konstanta enchant — satu sumber tetap backend. */
const ENCHANT_MAX = 5;
const ENCHANT_BONUS = 0.12; // +12% kekuatan buff per level
const enchantCost = (lvl: number) => (lvl + 1) * 50;

/**
 * L07 (v1.7.4) — EnchantForge: sub-tab ANVIL interaktif untuk enchant.
 * Item dipilih dari inventory → dipajang di atas paron → ditempa dengan
 * animasi palu + percikan api (transform/opacity, sekali per aksi,
 * reduced-motion diguard). Logika tetap di backend (biaya XP, max level).
 */
export const EnchantForge: React.FC = () => {
  const { inventory, user, enchantItem, lang } = useGame();
  const SHOP = liveShopItems() as Record<string, any>;
  const [sel, setSel] = useState<string | null>(null);
  const [forging, setForging] = useState(false);
  const [flash, setFlash] = useState<null | 'ok' | 'fail'>(null);
  const [msg, setMsg] = useState('');

  // Hanya equipment (non-consumable) yang bisa di-enchant — parity backend.
  const equips = useMemo(
    () =>
      inventory.filter((inv: any) => {
        const it = SHOP[inv.itemId] || {};
        return it.type && it.type !== 'consumable';
      }),
    [inventory, SHOP],
  );

  const selected = sel ? equips.find((e: any) => e.itemId === sel) : equips[0];
  const it = selected ? SHOP[selected.itemId] : null;
  const lvl = selected ? Number(selected.enchantLevel || (selected as any).enchant_level || 0) : 0;
  const cost = enchantCost(lvl);
  const canForge = !!it && lvl < ENCHANT_MAX && (user.xp || 0) >= cost && !forging;

  const buffRows = useMemo(() => {
    if (!it?.buff) return [] as { k: string; now: number; next: number }[];
    return Object.entries(it.buff as Record<string, number>).map(([k, v]) => ({
      k,
      now: Math.round((v as number) * (1 + ENCHANT_BONUS * lvl) * 10) / 10,
      next: Math.round((v as number) * (1 + ENCHANT_BONUS * (lvl + 1)) * 10) / 10,
    }));
  }, [it, lvl]);

  const itemName = (iid: string) => {
    const d = SHOP[iid] || {};
    return lang === 'id' ? d.name_id || d.name || iid : d.name || iid;
  };

  const forge = async () => {
    if (!canForge || !selected) return;
    setForging(true);
    setFlash(null);
    setMsg('');
    try {
      const res: any = await enchantItem(selected.itemId);
      window.setTimeout(() => {
        setForging(false);
        if (res?.result?.ok ?? res?.ok) {
          setFlash('ok');
          setMsg(tr('forge_success', { lvl: lvl + 1 }));
          window.dispatchEvent(new CustomEvent('ct-led-pulse'));
        } else {
          setFlash('fail');
          setMsg(res?.result?.msg || res?.msg || 'Enchant gagal');
        }
        window.setTimeout(() => setFlash(null), 1200);
      }, 850);
    } catch (e: any) {
      setForging(false);
      setFlash('fail');
      setMsg(String(e?.message || e));
    }
  };

  return (
    <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
      {/* ── Daftar equipment ── */}
      <div className="ct-panel p-4 space-y-2 max-h-[420px] overflow-y-auto">
        <h3 className="text-sm font-black text-slate-100">⚔️ {tr('forge_pick_title')}</h3>
        {equips.length === 0 && <p className="text-xs text-slate-500">{tr('forge_pick_empty')}</p>}
        {equips.map((inv: any) => {
          const d = SHOP[inv.itemId] || {};
          const l = Number(inv.enchantLevel || (inv as any).enchant_level || 0);
          const isSel = selected?.itemId === inv.itemId;
          return (
            <button
              key={inv.id || inv.itemId}
              onClick={() => setSel(inv.itemId)}
              className={`w-full flex items-center gap-2.5 p-2.5 rounded-xl text-left cursor-pointer transition-colors ${
                isSel ? 'bg-violet-950/60 border border-violet-500/50' : 'bg-slate-900/40 border border-transparent hover:border-slate-600'
              }`}
              aria-pressed={isSel}
            >
              <span className="text-2xl" aria-hidden="true">{d.icon || '📦'}</span>
              <span className="min-w-0 flex-1">
                <span className="block text-xs font-bold text-slate-100 truncate">{itemName(inv.itemId)}</span>
                <span className="block text-[10px] text-violet-300 font-bold" aria-label={`enchant level ${l}`}>
                  {'★'.repeat(l)}{'☆'.repeat(Math.max(0, ENCHANT_MAX - l))}
                </span>
              </span>
            </button>
          );
        })}
      </div>

      {/* ── Panggung paron ── */}
      <div className="ct-panel p-6 flex flex-col items-center justify-center gap-3 relative overflow-hidden">
        <div className={`ct-forge-stage${forging ? ' ct-forge-stage--on' : ''}${flash === 'ok' ? ' ct-forge-stage--ok' : ''}`} aria-hidden="true">
          <span className="ct-forge-hammer">⚒️</span>
          <span className="ct-forge-item">{it?.icon || '❔'}</span>
          <span className="ct-forge-anvil">🪨</span>
          <span className="ct-forge-sparks"><i /> <i /> <i /> <i /></span>
        </div>
        <p className="text-sm font-black text-slate-100">{it && selected ? itemName(selected.itemId) : tr('forge_pick_empty')}</p>
        <p className="text-[11px] text-violet-300 font-bold" aria-hidden="true">
          {'★'.repeat(lvl)}{'☆'.repeat(Math.max(0, ENCHANT_MAX - lvl))}
        </p>
        {msg && (
          <p className={`text-xs font-bold ${flash === 'fail' ? 'text-rose-300' : 'text-emerald-300'}`} role="status">{msg}</p>
        )}
        <button
          onClick={forge}
          disabled={!canForge}
          className="ct-btn ct-btn-glow px-8 cursor-pointer"
        >
          {forging ? tr('forge_working') : lvl >= ENCHANT_MAX ? tr('forge_maxed') : tr('forge_btn', { cost })}
        </button>
        {it && lvl < ENCHANT_MAX && (user.xp || 0) < cost && (
          <p className="text-[11px] text-rose-300">{tr('db_enchant_no_xp', { cost })}</p>
        )}
      </div>

      {/* ── Pratinjau buff ── */}
      <div className="ct-panel p-4 space-y-2">
        <h3 className="text-sm font-black text-slate-100">📈 {tr('forge_preview_title')}</h3>
        {!it ? (
          <p className="text-xs text-slate-500">{tr('forge_pick_empty')}</p>
        ) : lvl >= ENCHANT_MAX ? (
          <p className="text-xs text-violet-300 font-bold">{tr('forge_maxed')}</p>
        ) : buffRows.length === 0 ? (
          <p className="text-xs text-slate-500">{tr('forge_no_buff')}</p>
        ) : (
          <table className="w-full text-xs">
            <thead>
              <tr className="text-slate-500 text-[10px] uppercase">
                <th className="text-left pb-1">Buff</th>
                <th className="text-right pb-1">Lv.{lvl}</th>
                <th className="text-right pb-1">→ Lv.{lvl + 1}</th>
              </tr>
            </thead>
            <tbody>
              {buffRows.map((r) => (
                <tr key={r.k} className="text-slate-200">
                  <td className="py-1 font-bold">{r.k}</td>
                  <td className="py-1 text-right">{r.now}</td>
                  <td className="py-1 text-right font-black text-emerald-300">+{r.next}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
        <p className="text-[10px] text-slate-500 pt-2">{tr('forge_note', { pct: 12 })}</p>
      </div>
    </div>
  );
};
