import React from 'react';
import { useGame } from '../../context/GameContext';
import { Trophy, CheckCircle, Award, Sparkles, Coins, ArrowRight } from 'lucide-react';

export const AchievementsView: React.FC = () => {
  const { achievements, claimAchievement, lang } = useGame();

  const evaluatedAchievements = achievements.map((ach) => ({
    ...ach,
    currentProgress: Number(ach.currentProgress || 0),
    isUnlocked: Boolean(ach.isUnlocked || ach.isClaimed),
  }));

  const claimedCount = evaluatedAchievements.filter((a) => a.isClaimed).length;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <Trophy className="w-6 h-6 text-amber-400" />
            <h2 className="text-xl font-black text-slate-100">{lang === 'id' ? 'Pencapaian & Medali' : 'Achievements & Medals'}</h2>
          </div>
          <p className="text-xs text-slate-400 mt-1">
            {lang === 'id'
              ? 'Raih tonggak sejarah dalam petualanganmu dan klaim hadiah XP serta Gold berlimpah!'
              : 'Unlock epic adventure milestones and claim rich XP and Gold bounties!'}
          </p>
        </div>

        <div className="flex items-center gap-2 px-3.5 py-2 rounded-xl bg-amber-500/10 border border-amber-500/30 text-amber-300 font-extrabold text-xs">
          <Award className="w-4 h-4 text-amber-400" />
          <span>
            {claimedCount} / {evaluatedAchievements.length} {lang === 'id' ? 'Terklaim' : 'Claimed'}
          </span>
        </div>
      </div>

      {/* Grid of Achievements */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {evaluatedAchievements.map((ach) => {
          const progressPct = Math.min(100, Math.round((ach.currentProgress / ach.targetProgress) * 100));

          return (
            <div
              key={ach.id}
              className={`p-4.5 rounded-2xl border flex flex-col justify-between gap-4 transition-all ${
                ach.isClaimed
                  ? 'bg-slate-900/40 border-slate-800/60 opacity-60'
                  : ach.isUnlocked
                  ? 'bg-amber-950/20 border-amber-500/50 shadow-lg shadow-amber-500/10'
                  : 'bg-slate-900/80 border-slate-800'
              }`}
            >
              <div>
                <div className="flex items-start justify-between gap-3">
                  <div className="flex items-center gap-3">
                    <div className="w-12 h-12 rounded-2xl bg-slate-800 border border-slate-700 flex items-center justify-center text-2xl shrink-0">
                      {ach.icon}
                    </div>
                    <div>
                      <h4 className="font-extrabold text-sm text-slate-100">{ach.title}</h4>
                      <p className="text-xs text-slate-400 mt-0.5">{ach.desc}</p>
                    </div>
                  </div>

                  <div className="text-right shrink-0">
                    <div className="text-xs font-bold text-amber-300">+{ach.goldReward}g</div>
                    <div className="text-[10px] font-bold text-emerald-400">+{ach.xpReward} XP</div>
                  </div>
                </div>

                {/* Progress bar */}
                <div className="space-y-1 mt-3">
                  <div className="flex items-center justify-between text-[10px] text-slate-400">
                    <span>{lang === 'id' ? 'Kemajuan' : 'Progress'}</span>
                    <span>
                      {ach.currentProgress} / {ach.targetProgress} ({progressPct}%)
                    </span>
                  </div>
                  <div className="w-full h-1.5 bg-slate-800 rounded-full overflow-hidden">
                    <div
                      className="h-full bg-gradient-to-r from-amber-500 to-yellow-400 transition-all duration-300"
                      style={{ width: `${progressPct}%` }}
                    />
                  </div>
                </div>
              </div>

              {/* Claim Action */}
              <div className="pt-2">
                {ach.isClaimed ? (
                  <span className="flex items-center justify-center gap-1.5 py-1.5 rounded-xl bg-slate-800 text-slate-400 text-xs font-bold">
                    <CheckCircle className="w-4 h-4 text-emerald-500" /> {lang === 'id' ? 'Hadiah Terklaim' : 'Reward Claimed'}
                  </span>
                ) : ach.isUnlocked ? (
                  <button
                    onClick={() => claimAchievement(ach.id)}
                    className="w-full py-2 rounded-xl bg-gradient-to-r from-amber-500 to-yellow-500 hover:from-amber-400 hover:to-yellow-400 text-slate-950 font-extrabold text-xs shadow-lg shadow-amber-500/20 active:scale-95 transition-all flex items-center justify-center gap-1.5"
                  >
                    <Sparkles className="w-4 h-4" /> {lang === 'id' ? 'Klaim Hadiah!' : 'Claim Bounty!'}
                  </button>
                ) : (
                  <div className="w-full py-1.5 rounded-xl bg-slate-800 text-slate-400 text-center text-xs font-semibold">
                    {lang === 'id' ? 'Terkunci' : 'In Progress'}
                  </div>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};
