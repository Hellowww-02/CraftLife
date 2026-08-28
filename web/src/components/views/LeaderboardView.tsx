import React, { useEffect, useState } from 'react';
import { useGame } from '../../context/GameContext';
import { Trophy } from 'lucide-react';

type Row = {
  id: string;
  username: string;
  displayName: string;
  level: number;
  xp: number;
  gold: number;
  sportLevel: number;
  pets: number;
  rebirth: number;
  title: string;
  presence?: string;
  cloudUserId?: string;
};

export const LeaderboardView: React.FC = () => {
  const { lang, user } = useGame();
  const [rows, setRows] = useState<Row[]>([]);

  useEffect(() => {
    fetch('/api/leaderboard')
      .then((r) => r.json())
      .then((d) => setRows(d.leaderboard || []))
      .catch(() => setRows([]));
  }, []);

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-2">
        <Trophy className="w-6 h-6 text-amber-400" />
        <h2 className="text-xl font-black text-slate-100">
          {lang === 'id' ? 'Papan peringkat' : 'Leaderboard'}
        </h2>
      </div>
      <p className="text-xs text-slate-400">
        {lang === 'id'
          ? 'Kamu, teman, dan anggota guild — data SQLite lokal (cloud jika ter-link).'
          : 'You, friends, and guild — local SQLite (cloud when linked).'}
      </p>
      <div className="rounded-2xl border border-slate-800 overflow-hidden">
        <table className="w-full text-xs">
          <thead className="bg-slate-900 text-slate-400">
            <tr>
              <th className="p-2 text-left">#</th>
              <th className="p-2 text-left">{lang === 'id' ? 'Pemain' : 'Player'}</th>
              <th className="p-2">Lv</th>
              <th className="p-2">XP</th>
              <th className="p-2">Gold</th>
              <th className="p-2">{lang === 'id' ? 'Olahraga' : 'Sport'}</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((r, i) => (
              <tr
                key={r.id}
                className={`border-t border-slate-800 ${String(user.id) === r.id ? 'bg-emerald-950/40 text-emerald-200' : 'text-slate-200'}`}
              >
                <td className="p-2">{i + 1}</td>
                <td className="p-2 font-semibold">
                  {r.displayName || r.username}
                  {r.title ? <span className="text-slate-500 font-normal"> · {r.title}</span> : null}
                  {r.presence && r.presence !== 'offline' ? (
                    <span className="ml-1 text-[10px] text-emerald-400">{r.presence}</span>
                  ) : null}
                </td>
                <td className="p-2 text-center">{r.level}</td>
                <td className="p-2 text-center">{r.xp}</td>
                <td className="p-2 text-center">{r.gold}</td>
                <td className="p-2 text-center">{r.sportLevel}</td>
              </tr>
            ))}
            {rows.length === 0 && (
              <tr>
                <td colSpan={6} className="p-4 text-slate-500">
                  {lang === 'id' ? 'Belum ada data.' : 'No rows yet.'}
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
};
