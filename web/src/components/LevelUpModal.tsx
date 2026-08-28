import React from 'react';
import { useGame } from '../context/GameContext';
import { Sparkles, Heart, Zap, Coins, Check } from 'lucide-react';
import { motion, AnimatePresence } from 'motion/react';

export const LevelUpModal: React.FC = () => {
  const { levelUpInfo, closeLevelUpModal, lang, user } = useGame();

  if (!levelUpInfo) return null;

  return (
    <AnimatePresence>
      <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-sm">
        <motion.div
          initial={{ scale: 0.8, opacity: 0, y: 20 }}
          animate={{ scale: 1, opacity: 1, y: 0 }}
          exit={{ scale: 0.8, opacity: 0 }}
          className="relative max-w-md w-full bg-gradient-to-b from-slate-900 via-slate-900 to-slate-950 border-2 border-amber-500/60 rounded-3xl p-6 shadow-2xl shadow-amber-500/20 text-center overflow-hidden"
        >
          {/* Ambient Glow */}
          <div className="absolute -top-24 left-1/2 -translate-x-1/2 w-48 h-48 bg-amber-500/20 rounded-full blur-3xl pointer-events-none" />

          <div className="w-16 h-16 mx-auto mb-3 rounded-2xl bg-amber-500/20 border border-amber-400 flex items-center justify-center text-3xl shadow-lg animate-bounce">
            🎉
          </div>

          <h2 className="text-2xl font-black text-transparent bg-clip-text bg-gradient-to-r from-amber-300 via-yellow-400 to-amber-200">
            {lang === 'id' ? 'SELAMAT LEVEL UP!' : 'LEVEL UP! CONGRATULATIONS!'}
          </h2>
          <p className="text-xs text-slate-300 mt-1 font-medium">
            {lang === 'id'
              ? `Karaktermu kini mencapai Level ${levelUpInfo.level}!`
              : `Your character has reached Level ${levelUpInfo.level}!`}
          </p>

          <div className="my-5 p-4 rounded-2xl bg-slate-800/80 border border-slate-700/60 space-y-2.5 text-xs text-left">
            <div className="flex items-center justify-between text-red-300">
              <span className="flex items-center gap-2">
                <Heart className="w-4 h-4 text-red-400 fill-red-400" /> {lang === 'id' ? 'Maksimal HP Meningkat' : 'Max HP Increased'}
              </span>
              <span className="font-bold">+{levelUpInfo.hpGain} HP (Full Restored)</span>
            </div>

            <div className="flex items-center justify-between text-sky-300">
              <span className="flex items-center gap-2">
                <Zap className="w-4 h-4 text-sky-400 fill-sky-400" /> {lang === 'id' ? 'Maksimal MP Meningkat' : 'Max MP Increased'}
              </span>
              <span className="font-bold">+{levelUpInfo.mpGain} MP (Full Restored)</span>
            </div>

            <div className="flex items-center justify-between text-amber-300">
              <span className="flex items-center gap-2">
                <Coins className="w-4 h-4 text-amber-400" /> {lang === 'id' ? 'Bonus Hadiah Gold' : 'Gold Bounty Reward'}
              </span>
              <span className="font-bold">+{levelUpInfo.goldGain} Gold</span>
            </div>
          </div>

          <button
            onClick={closeLevelUpModal}
            className="w-full py-3 px-4 rounded-xl bg-gradient-to-r from-amber-500 to-yellow-500 hover:from-amber-400 hover:to-yellow-400 text-slate-950 font-extrabold text-sm shadow-lg shadow-amber-500/30 transition-all flex items-center justify-center gap-2"
          >
            <Check className="w-4 h-4" /> {lang === 'id' ? 'Lanjutkan Petualangan!' : 'Continue Adventure!'}
          </button>
        </motion.div>
      </div>
    </AnimatePresence>
  );
};
