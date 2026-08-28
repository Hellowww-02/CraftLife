import React from 'react';
import { useGame } from '../context/GameContext';
import { CheckCircle, AlertTriangle, Sparkles, Info, Swords, X } from 'lucide-react';
import { AnimatePresence, motion } from 'motion/react';

export const ToastContainer: React.FC = () => {
  const { toasts, removeToast } = useGame();

  const getIcon = (type: string) => {
    switch (type) {
      case 'success':
        return <CheckCircle className="w-5 h-5 text-emerald-400 shrink-0" />;
      case 'damage':
        return <AlertTriangle className="w-5 h-5 text-rose-400 shrink-0" />;
      case 'level_up':
        return <Sparkles className="w-5 h-5 text-amber-400 shrink-0" />;
      case 'boss':
        return <Swords className="w-5 h-5 text-red-400 shrink-0" />;
      default:
        return <Info className="w-5 h-5 text-sky-400 shrink-0" />;
    }
  };

  const getBorderColor = (type: string) => {
    switch (type) {
      case 'success':
        return 'border-emerald-500/40 bg-slate-900/95';
      case 'damage':
        return 'border-rose-500/40 bg-slate-900/95';
      case 'level_up':
        return 'border-amber-500/50 bg-slate-900/95 shadow-amber-500/10';
      case 'boss':
        return 'border-red-500/50 bg-slate-900/95';
      default:
        return 'border-sky-500/40 bg-slate-900/95';
    }
  };

  return (
    <div className="fixed bottom-4 right-4 z-50 flex flex-col gap-2 max-w-sm w-full pointer-events-none px-3">
      <AnimatePresence>
        {toasts.map((toast) => (
          <motion.div
            key={toast.id}
            initial={{ opacity: 0, y: 20, scale: 0.95 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, scale: 0.9, y: 10 }}
            className={`pointer-events-auto flex items-start gap-3 p-3.5 rounded-xl border shadow-xl backdrop-blur-md ${getBorderColor(
              toast.type
            )}`}
          >
            {getIcon(toast.type)}
            <div className="flex-1 min-w-0">
              <div className="text-xs font-bold text-slate-100">{toast.title}</div>
              <div className="text-xs text-slate-300 mt-0.5 break-words">{toast.message}</div>
            </div>
            <button
              onClick={() => removeToast(toast.id)}
              className="text-slate-400 hover:text-slate-200 transition-colors"
            >
              <X className="w-4 h-4" />
            </button>
          </motion.div>
        ))}
      </AnimatePresence>
    </div>
  );
};
