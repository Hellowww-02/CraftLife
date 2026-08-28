import React from 'react';
import { useGame } from '../../context/GameContext';
import { liveBosses } from '../../data/liveCatalog';
import { BossTier } from '../../types';
import { Swords, Zap, Shield, Heart, Skull, Play, Flame, Sparkles, Award } from 'lucide-react';
import { motion } from 'motion/react';

export const BossView: React.FC = () => {
  const { user, activeBoss, activeBossHp, startBossFight, attackBoss, fleeBoss, useClassSkill, lang } = useGame();

  const BOSSES = liveBosses();
  const bossesList = Object.values(BOSSES);

  const getTierBadge = (tier: BossTier) => {
    switch (tier) {
      case 'beginner':
        return <span className="px-2 py-0.5 text-[10px] font-bold rounded-full bg-emerald-500/20 text-emerald-300 border border-emerald-500/30">Beginner</span>;
      case 'normal':
        return <span className="px-2 py-0.5 text-[10px] font-bold rounded-full bg-blue-500/20 text-blue-300 border border-blue-500/30">Normal</span>;
      case 'hard':
        return <span className="px-2 py-0.5 text-[10px] font-bold rounded-full bg-amber-500/20 text-amber-300 border border-amber-500/30">Hard</span>;
      case 'elite':
        return <span className="px-2 py-0.5 text-[10px] font-bold rounded-full bg-purple-500/20 text-purple-300 border border-purple-500/30">Elite</span>;
      case 'legendary':
        return <span className="px-2 py-0.5 text-[10px] font-bold rounded-full bg-rose-500/20 text-rose-300 border border-rose-500/30">Legendary</span>;
      case 'seasonal':
        return <span className="px-2 py-0.5 text-[10px] font-bold rounded-full bg-orange-500/20 text-orange-300 border border-orange-500/30">Seasonal</span>;
    }
  };

  const bossHpPct = activeBoss ? Math.max(0, Math.min(100, Math.round((activeBossHp / activeBoss.maxHp) * 100))) : 0;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <div className="flex items-center gap-2">
          <Swords className="w-6 h-6 text-red-500" />
          <h2 className="text-xl font-black text-slate-100">{lang === 'id' ? 'Arena Pertarungan Boss' : 'Dungeon Boss Arena'}</h2>
        </div>
        <p className="text-xs text-slate-400 mt-1">
          {lang === 'id'
            ? 'Pilih monster dungeon, selesaikan tugas harianmu untuk melancarkan serangan dahsyat, atau cast mantra sihir di arena!'
            : 'Select dungeon bosses, complete tasks to unleash relentless assault strikes, or cast arcane spells directly in battle!'}
        </p>
      </div>

      {/* Active Boss Arena Stage */}
      {activeBoss ? (
        <div className="relative overflow-hidden rounded-3xl bg-gradient-to-b from-slate-900 via-red-950/20 to-slate-950 border-2 border-red-500/40 p-6 shadow-2xl shadow-red-950/40">
          <div className="flex flex-col md:flex-row items-center justify-between gap-6">
            {/* Boss Display */}
            <div className="flex flex-col items-center text-center space-y-3">
              <motion.div
                animate={{ y: [0, -8, 0] }}
                transition={{ repeat: Infinity, duration: 3, ease: 'easeInOut' }}
                className="w-28 h-28 rounded-3xl bg-red-500/10 border-2 border-red-500/40 flex items-center justify-center text-6xl shadow-2xl shadow-red-500/20"
              >
                {activeBoss.icon}
              </motion.div>

              <div>
                <div className="flex items-center justify-center gap-2">
                  <h3 className="text-xl font-black text-slate-100">{activeBoss.name}</h3>
                  {getTierBadge(activeBoss.tier)}
                </div>
                <div className="text-xs text-slate-400 mt-1">
                  Atk: {activeBoss.atk} DMG · Bounty: +{activeBoss.xpReward} XP / +{activeBoss.goldReward} Gold
                </div>
              </div>

              {/* Boss Health Bar */}
              <div className="w-64 space-y-1">
                <div className="flex items-center justify-between text-xs font-bold text-slate-300">
                  <span className="text-red-400 flex items-center gap-1">
                    <Heart className="w-3.5 h-3.5 fill-red-500 text-red-500" /> Boss HP
                  </span>
                  <span>{activeBossHp} / {activeBoss.maxHp} ({bossHpPct}%)</span>
                </div>
                <div className="w-full h-3 bg-slate-900 rounded-full overflow-hidden border border-red-500/30">
                  <div
                    className="h-full bg-gradient-to-r from-red-600 via-rose-500 to-orange-500 transition-all duration-300"
                    style={{ width: `${bossHpPct}%` }}
                  />
                </div>
              </div>
            </div>

            {/* Combat Actions & Hero Status */}
            <div className="w-full md:w-80 space-y-3 bg-slate-900/90 border border-slate-800 p-4.5 rounded-2xl">
              <h4 className="font-bold text-xs text-slate-300 uppercase tracking-wider">{lang === 'id' ? 'Aksi Pertarungan' : 'Combat Actions'}</h4>

              {/* Physical Strike */}
              <button
                id="btn-attack-boss"
                type="button"
                onClick={() => attackBoss('light')}
                className="w-full py-3 px-4 rounded-xl bg-gradient-to-r from-red-600 to-rose-600 hover:from-red-500 hover:to-rose-500 text-white font-extrabold text-xs shadow-lg shadow-red-600/30 flex items-center justify-between"
              >
                <span className="flex items-center gap-2">
                  <Swords className="w-4 h-4" /> {lang === 'id' ? 'Serangan ringan' : 'Light attack'}
                </span>
                <span className="text-[11px] font-bold text-red-200">0 MP</span>
              </button>

              <button
                id="btn-heavy-boss"
                type="button"
                onClick={() => attackBoss('heavy')}
                disabled={user.mp < 5}
                className={`w-full py-3 px-4 rounded-xl font-extrabold text-xs flex items-center justify-between ${
                  user.mp >= 5 ? 'bg-orange-600 hover:bg-orange-500 text-white' : 'bg-slate-800 text-slate-400 cursor-not-allowed'
                }`}
              >
                <span className="flex items-center gap-2">
                  <Flame className="w-4 h-4" /> {lang === 'id' ? 'Serangan berat' : 'Heavy attack'}
                </span>
                <span className="text-[11px] font-bold">5 MP</span>
              </button>

              <button
                id="btn-ultimate-boss"
                type="button"
                onClick={() => attackBoss('ultimate')}
                disabled={user.mp < 50}
                className={`w-full py-3 px-4 rounded-xl font-extrabold text-xs flex items-center justify-between ${
                  user.mp >= 50 ? 'bg-gradient-to-r from-fuchsia-600 to-purple-600 text-white' : 'bg-slate-800 text-slate-400 cursor-not-allowed'
                }`}
              >
                <span className="flex items-center gap-2">
                  <Sparkles className="w-4 h-4" /> {lang === 'id' ? 'Ultimate' : 'Ultimate'}
                </span>
                <span className="text-[11px] font-bold">50 MP</span>
              </button>

              <button
                id="btn-block-boss"
                type="button"
                onClick={() => attackBoss('block')}
                disabled={user.mp < 5}
                className={`w-full py-3 px-4 rounded-xl font-extrabold text-xs flex items-center justify-between ${
                  user.mp >= 5 ? 'bg-slate-700 hover:bg-slate-600 text-white' : 'bg-slate-800 text-slate-400 cursor-not-allowed'
                }`}
              >
                <span className="flex items-center gap-2">
                  <Shield className="w-4 h-4" /> {lang === 'id' ? 'Blokir' : 'Block'}
                </span>
                <span className="text-[11px] font-bold">5 MP</span>
              </button>

              <button
                id="btn-class-skill"
                type="button"
                onClick={() => useClassSkill()}
                className="w-full py-3 px-4 rounded-xl bg-sky-700 hover:bg-sky-600 text-white font-extrabold text-xs flex items-center justify-between"
              >
                <span className="flex items-center gap-2">
                  <Zap className="w-4 h-4 text-cyan-300" /> {lang === 'id' ? 'Skill kelas (MP)' : 'Class skill (MP)'}
                </span>
                <span className="text-[11px] font-bold capitalize">{user.avatarClass || 'warrior'}</span>
              </button>

              {/* Passive Tip */}
              <div className="p-2.5 rounded-xl bg-slate-800/60 border border-slate-700/60 text-[11px] text-slate-400 space-y-1">
                <div className="text-slate-300 font-semibold flex items-center gap-1">
                  <Zap className="w-3 h-3 text-amber-400" /> {lang === 'id' ? 'Sinergi Tugas Harian:' : 'Task Synergy:'}
                </div>
                <div>
                  {lang === 'id'
                    ? 'Menyelesaikan Habits, Dailies, dan Quests otomatis melancarkan damage ekstra ke Boss ini!'
                    : 'Completing Habits, Dailies, and Quests will automatically strike and damage this active Boss!'}
                </div>
              </div>

              <button
                onClick={fleeBoss}
                className="w-full py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-400 hover:text-slate-200 text-xs font-semibold"
              >
                {lang === 'id' ? 'Kabur dari Pertarungan' : 'Flee Encounter'}
              </button>
            </div>
          </div>
        </div>
      ) : (
        <div className="p-8 rounded-3xl bg-slate-900/60 border border-slate-800 text-center space-y-2">
          <Skull className="w-10 h-10 text-slate-600 mx-auto" />
          <h3 className="font-bold text-base text-slate-200">{lang === 'id' ? 'Tidak Ada Boss yang Sedang Dihadapi' : 'No Active Boss Encounter'}</h3>
          <p className="text-xs text-slate-400 max-w-sm mx-auto">
            {lang === 'id' ? 'Pilih salah satu dungeon boss di bawah ini untuk memulai pertarungan!' : 'Select a monster boss from the dungeon roster below to initiate combat!'}
          </p>
        </div>
      )}

      {/* Boss Roster Selection */}
      <div className="space-y-3">
        <h3 className="font-bold text-sm text-slate-200">{lang === 'id' ? 'Daftar Monster Dungeon' : 'Dungeon Monster Roster'}</h3>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {bossesList.map((boss) => {
            const isCurrentActive = activeBoss?.id === boss.id;
            const meetsLevel = user.level >= boss.minLevel;

            return (
              <div
                key={boss.id}
                className={`p-4.5 rounded-2xl border flex flex-col justify-between gap-4 transition-all ${
                  isCurrentActive
                    ? 'bg-red-950/20 border-red-500/50 shadow-md'
                    : 'bg-slate-900/80 border-slate-800 hover:border-slate-700'
                }`}
              >
                <div>
                  <div className="flex items-start justify-between gap-2 mb-2">
                    <div className="flex items-center gap-3">
                      <div className="w-12 h-12 rounded-2xl bg-slate-800 border border-slate-700 flex items-center justify-center text-3xl shrink-0">
                        {boss.icon}
                      </div>
                      <div>
                        <h4 className="font-extrabold text-sm text-slate-100">{boss.name}</h4>
                        <div className="flex items-center gap-2 mt-0.5">
                          {getTierBadge(boss.tier)}
                          <span className="text-[10px] text-slate-400 font-medium">Min Lv.{boss.minLevel}</span>
                        </div>
                      </div>
                    </div>
                  </div>

                  <div className="grid grid-cols-2 gap-2 text-xs pt-2 border-t border-slate-800 text-slate-400">
                    <div>HP: <span className="font-bold text-red-400">{boss.hp}</span></div>
                    <div>Atk: <span className="font-bold text-amber-400">{boss.atk} DMG</span></div>
                    <div>Reward: <span className="font-bold text-emerald-400">+{boss.xpReward} XP</span></div>
                    <div>Bounty: <span className="font-bold text-yellow-400">+{boss.goldReward}g</span></div>
                  </div>
                </div>

                <div>
                  {isCurrentActive ? (
                    <span className="block w-full text-center py-2 rounded-xl bg-red-500/20 text-red-300 font-bold text-xs border border-red-500/30">
                      {lang === 'id' ? 'Sedang Bertarung' : 'Engaged in Battle'}
                    </span>
                  ) : meetsLevel ? (
                    <button
                      onClick={() => startBossFight(boss.id)}
                      className="w-full py-2 rounded-xl bg-red-600 hover:bg-red-500 text-white font-bold text-xs shadow-md transition-all flex items-center justify-center gap-1.5"
                    >
                      <Play className="w-3.5 h-3.5" /> {lang === 'id' ? 'Tantang Boss' : 'Challenge Boss'}
                    </button>
                  ) : (
                    <button
                      disabled
                      className="w-full py-2 rounded-xl bg-slate-800 text-slate-400 font-bold text-xs cursor-not-allowed"
                    >
                      {lang === 'id' ? `Terkunci (Butuh Lv.${boss.minLevel})` : `Locked (Req Lv.${boss.minLevel})`}
                    </button>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
};
