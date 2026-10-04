import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { PageSignature } from '../ui/SignatureKit';
import { useGame } from '../../context/GameContext';
import { livePets } from '../../data/liveCatalog';
import { rpg } from '../../api/rpg';
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

/* L06 (v1.7.4) — Pets "Boss Arena": arena kolektor + mesin spin gacha +
 * ensiklopedia. Warna rank adalah SEMANTIK game (kelangkaan), bukan chrome
 * tema — konsisten lintas 12 tema seperti rarity color game pada umumnya. */
const RANKS = ['common', 'rare', 'epic', 'legendary', 'mythic', 'secret'] as const;
type Rank = (typeof RANKS)[number];
const RANK_COLOR: Record<Rank, string> = {
  common: '#9ca3af',
  rare: '#38bdf8',
  epic: '#a78bfa',
  legendary: '#fbbf24',
  mythic: '#fb7185',
  secret: '#34d399',
};

const FEED_COST = 30; // Parity database.feed_pet (tidak berubah di L05).

type OddsData = {
  cost: number;
  odds: Record<string, number>;
  pity: { epic: number; legendary: number };
  training?: Record<string, [number, number, number, number]>;
  skillRanks?: Record<string, { cooldown: number; mp_cost: number; unlock_level: number; actions: number }>;
  state: { spins_total: number; since_epic: number; since_legendary: number };
};
type DexEntry = {
  id: string; name: string; name_id: string; icon: string; rank: Rank;
  bonus: string; baseBuff: Record<string, number>; owned: boolean;
  level?: number; hasSkill: boolean;
};

const RankBadge: React.FC<{ rank: Rank; small?: boolean }> = ({ rank, small }) => (
  <span
    className={`ct-rank-badge${small ? ' ct-rank-badge--sm' : ''}${rank === 'secret' ? ' ct-rank-badge--secret' : ''}`}
    style={{ ['--ct-rank-c' as any]: RANK_COLOR[rank] }}
  >
    {tr(`pet_rank_${rank}`)}
  </span>
);

export const PetsView: React.FC = () => {
  const { user, userPets, maxActivePets, lang, feedPet, trainPet, equipPet, unequipPet, spinPet, castPetSkill } = useGame();
  const PETS_DATA = livePets() as Record<string, any>;

  const [tab, setTab] = useState<'arena' | 'spin' | 'dex'>('arena');
  const [odds, setOdds] = useState<OddsData | null>(null);
  const [dex, setDex] = useState<DexEntry[]>([]);
  const [spinning, setSpinning] = useState(false);
  const [reveal, setReveal] = useState<any | null>(null);
  const [spinErr, setSpinErr] = useState('');
  const [dexSel, setDexSel] = useState<string | null>(null);
  const [now, setNow] = useState(() => Math.floor(Date.now() / 1000));

  // Tick 20 dtk utk tampilan cooldown skill (murah, tanpa API call).
  useEffect(() => {
    const iv = window.setInterval(() => setNow(Math.floor(Date.now() / 1000)), 20000);
    return () => window.clearInterval(iv);
  }, []);

  useEffect(() => {
    rpg.getPetOdds().then((r) => r?.ok && setOdds(r)).catch(() => {});
    rpg.getPetPokedex().then((r) => r?.ok && setDex(r.pets || [])).catch(() => {});
  }, [userPets.length]);

  const activePets = userPets.filter((p) => p.isEquipped);
  const starPet = activePets[0];
  const gold = user.gold || 0;

  const petName = useCallback(
    (pid: string) => {
      const d = PETS_DATA[pid] || {};
      return lang === 'id' ? d.name_id || d.name || pid : d.name || pid;
    },
    [PETS_DATA, lang],
  );

  const trainCostOf = useCallback(
    (pid: string, level: number) => {
      // Formula backend (K6) — data training dari API, fallback umum.
      const rank = (PETS_DATA[pid]?.rank || 'common') as string;
      const row = odds?.training?.[rank];
      if (row) return Math.round(row[0] + Math.max(0, level - 1) * row[1]);
      return 20 + Math.max(0, level - 1) * 4;
    },
    [PETS_DATA, odds],
  );

  const doSpin = useCallback(async () => {
    if (!odds || spinning) return;
    if (gold < odds.cost) { setSpinErr(tr('pets_spin_gold_low', { cost: odds.cost })); return; }
    setSpinErr(''); setReveal(null); setSpinning(true);
    try {
      const res = await spinPet();
      window.setTimeout(() => {
        setSpinning(false);
        if (res?.ok) setReveal(res);
        else setSpinErr(res?.msg || 'Spin gagal');
      }, 1400);
    } catch (e: any) {
      setSpinning(false);
      setSpinErr(e?.message || 'Spin gagal');
    }
  }, [odds, spinning, gold, spinPet]);

  const skillState = useCallback(
    (p: any): { ok: boolean; label: string } => {
      const meta = odds?.skillRanks?.[p.rank];
      if (!p.skill || !meta) return { ok: false, label: '' };
      if ((p.level || 1) < meta.unlock_level)
        return { ok: false, label: tr('pets_skill_locked', { level: meta.unlock_level }) };
      const left = meta.cooldown - (now - (p.skillUsedAt || 0));
      if (left > 0) return { ok: false, label: tr('pets_skill_cd', { mins: Math.ceil(left / 60) }) };
      return { ok: true, label: tr('pets_skill_use', { mp: meta.mp_cost }) };
    },
    [odds, now],
  );

  const onSkill = useCallback(
    async (petId: string) => {
      const res = await castPetSkill(petId);
      if (res && !res.ok && res.msg) window.dispatchEvent(new CustomEvent('ct-led-pulse'));
      setNow(Math.floor(Date.now() / 1000));
    },
    [castPetSkill],
  );

  const dexOwned = useMemo(() => dex.filter((d) => d.owned).length, [dex]);
  const dexByRank = useMemo(() => {
    const m: Record<string, { total: number; pct: number }> = {};
    for (const r of RANKS) m[r] = { total: dex.filter((d) => d.rank === r).length, pct: odds?.odds?.[r] ?? 0 };
    return m;
  }, [dex, odds]);

  const TabBtn: React.FC<{ id: 'arena' | 'spin' | 'dex'; icon: string; label: string }> = ({ id, icon, label }) => (
    <button
      onClick={() => setTab(id)}
      className={`px-4 py-2 rounded-lg text-sm font-bold transition-colors cursor-pointer ${
        tab === id ? 'ct-btn ct-btn-primary' : 'ct-btn ct-btn-ghost'
      }`}
      aria-pressed={tab === id}
    >
      <span aria-hidden="true">{icon}</span> {label}
    </button>
  );

  return (
    <div className="px-4 md:px-8 pb-24 pt-4 max-w-7xl mx-auto space-y-4 animate-fade-in-up">
      <PageSignature
        icon={<span className="text-xl">🐾</span>}
        title={tr('page_pets_title')}
        tagline={tr('page_pets_subtitle')}
        accent="#a78bfa"
        pattern="dots"
      />

      <div className="flex items-center justify-between flex-wrap gap-2">
        <div className="flex gap-2" role="tablist" aria-label="Pets">
          <TabBtn id="arena" icon="⚔️" label={tr('pets_tab_arena')} />
          <TabBtn id="spin" icon="🎰" label={tr('pets_tab_spin')} />
          <TabBtn id="dex" icon="📖" label={tr('pets_tab_dex')} />
        </div>
        <div className="ct-panel px-3 py-1.5 text-sm font-bold text-amber-200">
          🪙 {Math.floor(gold).toLocaleString()} · {tr('pets_active_info_short', { active: activePets.length, max: maxActivePets })}
        </div>
      </div>

      {tab === 'arena' && (
        <>
          {/* ══ ARENA: panggung pet aktif ala boss-battle ══ */}
          <div className="ct-arena-stage" data-has-pet={starPet ? '1' : '0'}>
            <div className="ct-arena-spot" aria-hidden="true" />
            {starPet ? (
              <div className="ct-arena-pet" style={{ ['--ct-rank-c' as any]: RANK_COLOR[(PETS_DATA[starPet.petId]?.rank || 'common') as Rank] }}>
                <span className="ct-arena-pet-icon" role="img" aria-label={petName(starPet.petId)}>
                  {PETS_DATA[starPet.petId]?.icon || '🐾'}
                </span>
                <div className="text-center space-y-1">
                  <p className="text-lg font-black text-slate-100">{petName(starPet.petId)}</p>
                  <div className="flex items-center justify-center gap-2">
                    <RankBadge rank={(PETS_DATA[starPet.petId]?.rank || 'common') as Rank} small />
                    <span className="text-xs text-slate-300 font-bold">Lv. {starPet.level || 1}</span>
                  </div>
                </div>
              </div>
            ) : (
              <p className="text-sm text-slate-400 text-center py-10">{tr('pets_stage_empty')}</p>
            )}
          </div>

          {userPets.length === 0 ? (
            <div className="ct-panel p-6 text-center space-y-3">
              <p className="text-sm text-slate-400">{tr('pets_empty')}</p>
              <button onClick={() => setTab('spin')} className="ct-btn ct-btn-primary cursor-pointer">
                🎰 {tr('pets_tab_spin')}
              </button>
            </div>
          ) : (
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
              {userPets.map((p) => {
                const pd = PETS_DATA[p.petId] || {};
                const rank = (pd.rank || 'common') as Rank;
                const xpNeed = (p.level || 1) * 100;
                const xpPct = Math.min(100, Math.round(((p.xp || 0) / xpNeed) * 100));
                const tCost = trainCostOf(p.petId, p.level || 1);
                const sk = skillState(p);
                return (
                  <div key={p.petId} className="ct-panel p-4 space-y-2.5" style={{ borderColor: `${RANK_COLOR[rank]}55` }}>
                    <div className="flex items-center gap-3">
                      <span className="text-3xl" role="img" aria-label={petName(p.petId)}>{pd.icon || '🐾'}</span>
                      <div className="min-w-0 flex-1">
                        <p className="font-bold text-slate-100 truncate">{petName(p.petId)}</p>
                        <div className="flex items-center gap-2 mt-0.5">
                          <RankBadge rank={rank} small />
                          <span className="text-[11px] text-slate-400">Lv. {p.level || 1}</span>
                        </div>
                      </div>
                      {p.isEquipped && <span className="text-[10px] font-bold text-emerald-300 bg-emerald-950/60 px-2 py-1 rounded-full">{tr('pets_equipped')}</span>}
                    </div>
                    <div>
                      <div className="flex justify-between text-[10px] text-slate-400 mb-1">
                        <span>EXP</span><span>{p.xp || 0}/{xpNeed}</span>
                      </div>
                      <div className="h-1.5 rounded-full bg-slate-800 overflow-hidden">
                        <div className="h-full rounded-full" style={{ width: `${xpPct}%`, background: RANK_COLOR[rank] }} />
                      </div>
                    </div>
                    <div className="flex gap-1.5 flex-wrap">
                      <button className="ct-btn ct-btn-ghost text-xs cursor-pointer" onClick={() => feedPet(p.petId)} title={tr('pets_feed_cost')}>
                        🍖 {tr('pets_feed')} ({FEED_COST})
                      </button>
                      <button
                        className="ct-btn ct-btn-ghost text-xs cursor-pointer"
                        onClick={() => trainPet(p.petId)}
                        disabled={gold < tCost}
                        title={tr('pets_train_cost', { cost: tCost })}
                      >
                        🏋️ {tr('pets_train')} ({tCost})
                      </button>
                      {p.isEquipped ? (
                        <button className="ct-btn ct-btn-ghost text-xs cursor-pointer" onClick={() => unequipPet(p.petId)}>
                          ⬇️ {tr('pets_unequip')}
                        </button>
                      ) : (
                        <button className="ct-btn ct-btn-secondary text-xs cursor-pointer" onClick={() => equipPet(p.petId)}>
                          ⬆️ {tr('pets_equip')}
                        </button>
                      )}
                    </div>
                    {p.skill && (
                      <button
                        className={`w-full text-xs cursor-pointer ${sk.ok ? 'ct-btn ct-btn-glow' : 'ct-btn ct-btn-ghost opacity-70'}`}
                        disabled={!sk.ok}
                        onClick={() => onSkill(p.petId)}
                      >
                        ✨ {lang === 'id' ? p.skill.name_id || p.skill.name : p.skill.name} — {sk.label}
                      </button>
                    )}
                  </div>
                );
              })}
            </div>
          )}
        </>
      )}

      {tab === 'spin' && odds && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          {/* ══ MESIN SPIN ══ */}
          <div className="ct-panel p-6 space-y-4 text-center">
            <h2 className="text-lg font-black text-slate-100">🎰 {tr('pets_spin_title')}</h2>
            <div className={`ct-spin-orb${spinning ? ' ct-spin-orb--on' : ''}${reveal ? ' ct-spin-orb--reveal' : ''}`}
                 style={reveal ? ({ ['--ct-rank-c' as any]: RANK_COLOR[(reveal.rank || 'common') as Rank] } as any) : undefined}
                 aria-hidden="true"
            >
              <span className="text-4xl">{reveal ? reveal.icon : '🔮'}</span>
            </div>
            {reveal && (
              <div className="ct-reveal-card space-y-1" style={{ ['--ct-rank-c' as any]: RANK_COLOR[(reveal.rank || 'common') as Rank] }}>
                <p className="font-black text-base" style={{ color: RANK_COLOR[(reveal.rank || 'common') as Rank] }}>
                  {reveal.name_id && lang === 'id' ? reveal.name_id : reveal.name}
                </p>
                <RankBadge rank={(reveal.rank || 'common') as Rank} />
                <p className="text-xs text-slate-300">
                  {reveal.is_new ? tr('pets_result_new') : tr('pets_result_dupe', { exp: reveal.dupe_exp || 0 })}
                </p>
              </div>
            )}
            {spinErr && <p className="text-xs text-rose-300" role="alert">{spinErr}</p>}
            <button
              onClick={doSpin}
              disabled={spinning || gold < odds.cost}
              className="ct-btn ct-btn-glow text-base px-8 cursor-pointer"
            >
              {spinning ? tr('pets_spin_spinning') : tr('pets_spin_btn', { cost: odds.cost })}
            </button>
            <div className="text-xs text-slate-400 space-y-1">
              <p>{tr('pets_pity_epic', { n: odds.state.since_epic, max: odds.pity.epic })}</p>
              <p>{tr('pets_pity_legendary', { n: odds.state.since_legendary, max: odds.pity.legendary })}</p>
              <p>{tr('pets_spin_total', { n: odds.state.spins_total })}</p>
            </div>
          </div>

          {/* ══ PELUANG PER RANK ══ */}
          <div className="ct-panel p-6 space-y-3">
            <h2 className="text-lg font-black text-slate-100">📊 {tr('pets_spin_odds_title')}</h2>
            {RANKS.map((r) => (
              <div key={r} className="flex items-center gap-3">
                <RankBadge rank={r} />
                <div className="flex-1 h-2 rounded-full bg-slate-800 overflow-hidden">
                  <div className="h-full rounded-full" style={{ width: `${(dexByRank[r]?.pct || 0)}%`, background: RANK_COLOR[r] }} />
                </div>
                <span className="text-xs font-bold text-slate-200 w-12 text-right">{dexByRank[r]?.pct || 0}%</span>
                <span className="text-[10px] text-slate-500 w-14 text-right">
                  {tr('pets_odds_pool', { n: dexByRank[r]?.total || 0 })}
                </span>
              </div>
            ))}
            <p className="text-[11px] text-slate-500 pt-2">{tr('pets_odds_note')}</p>
          </div>
        </div>
      )}

      {tab === 'dex' && (
        <div className="space-y-3">
          <div className="ct-panel p-4 flex items-center gap-3">
            <span className="text-2xl" aria-hidden="true">📖</span>
            <div className="flex-1">
              <p className="text-sm font-bold text-slate-100">{tr('pets_dex_progress', { owned: dexOwned, total: dex.length })}</p>
              <div className="h-2 mt-1.5 rounded-full bg-slate-800 overflow-hidden">
                <div className="h-full rounded-full bg-emerald-400" style={{ width: `${dex.length ? Math.round((dexOwned / dex.length) * 100) : 0}%` }} />
              </div>
            </div>
          </div>
          <div className="grid grid-cols-3 sm:grid-cols-4 md:grid-cols-6 gap-2.5">
            {dex.map((d) => (
              <button
                key={d.id}
                onClick={() => setDexSel(dexSel === d.id ? null : d.id)}
                className={`ct-panel p-3 text-center space-y-1 cursor-pointer transition-transform hover:scale-[1.04] ${dexSel === d.id ? 'ring-2 ring-violet-400' : ''}`}
                aria-pressed={dexSel === d.id}
              >
                <span className={`text-3xl block ${d.owned ? '' : 'ct-dex-silhouette'}`} aria-hidden="true">{d.icon}</span>
                <span className="text-[11px] font-bold text-slate-200 block truncate">
                  {d.owned ? (lang === 'id' ? d.name_id : d.name) : '???'}
                </span>
                <RankBadge rank={d.rank} small />
              </button>
            ))}
          </div>
          {dexSel && (() => {
            const d = dex.find((x) => x.id === dexSel);
            if (!d) return null;
            return (
              <div className="ct-panel p-4 space-y-1.5" role="region" aria-label="Detail">
                <p className="font-bold text-slate-100">
                  {d.icon} {d.owned ? (lang === 'id' ? d.name_id : d.name) : '???'} <RankBadge rank={d.rank} small />
                </p>
                {d.owned ? (
                  <>
                    <p className="text-xs text-slate-300">{tr('pets_dex_bonus')}: {d.bonus}</p>
                    <p className="text-xs text-slate-400">
                      Buff: {Object.entries(d.baseBuff).map(([k, v]) => `${k} +${v}`).join(', ')}
                    </p>
                    {d.hasSkill && <p className="text-xs text-violet-300">✨ {tr('pets_dex_skill')}</p>}
                  </>
                ) : (
                  <p className="text-xs text-slate-500 italic">{tr('pets_dex_unknown')}</p>
                )}
              </div>
            );
          })()}
        </div>
      )}
    </div>
  );
};
