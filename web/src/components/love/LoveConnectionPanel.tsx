/**
 * LoveConnectionPanel.tsx — tab `connection` Love Space (fase A11).
 *
 * Isi: statistik check-in (streak), grafik tren mood 30/90 hari, prompt harian,
 * riwayat jawaban dengan pencarian/filter/favorit, panel prompt favorit, dan
 * review mingguan. Seluruh logika tanggal/filter ada di `connectionUtils.ts`
 * supaya bisa diuji tanpa DOM.
 */
import React, { useEffect, useMemo, useState } from 'react';
import { Copy, Flame, Search, Shuffle, Star, Trash2 } from 'lucide-react';
import { DualLineChart, LineChart } from '../charts';
import {
  PROMPT_CATEGORIES,
  buildMoodSeries,
  checkinStats,
  favoritePrompts,
  filterResponses,
  historyCategories,
  historyDate,
  pickPrompt,
  promptByKey,
  promptPool,
  weekStartOf,
  type Prompt,
  type ResponseRow,
} from './connectionUtils';

const inputCls = 'ct-input w-full px-2 py-1.5 rounded-lg text-slate-200 text-xs';
const btnRose = 'ct-btn ct-btn-rose ct-btn-sm';
const btnGhost = 'ct-btn ct-btn-secondary ct-btn-sm';

export interface LoveConnectionPanelProps {
  t: (k: string, fb: string) => string;
  trv: (k: string, vars: Record<string, string | number>, fb: string) => string;
  loveSpace: any;
  today: string;
  onSaveResponse: (payload: { promptKey: string; category: string; prompt: string; answer: string; partnerAnswer: string }) => void;
  onFavorite: (promptKey: string) => void;
  onDeleteResponse: (id: string) => void;
  onSaveWeekly: (payload: { weekStart: string; appreciation: string; wins: string; support: string; intention: string }) => void;
  onDeleteWeekly: (id: string) => void;
  showToast: (kind: any, title: string, msg: string) => void;
}

export const LoveConnectionPanel: React.FC<LoveConnectionPanelProps> = ({
  t, trv, loveSpace, today, onSaveResponse, onFavorite, onDeleteResponse, onSaveWeekly, onDeleteWeekly, showToast,
}) => {
  const checkins = loveSpace.checkins || [];
  const responses: ResponseRow[] = loveSpace.promptResponses || [];
  const favorites: string[] = loveSpace.promptFavorites || [];

  // ── prompt harian ───────────────────────────────────────────────────────
  const [promptCategory, setPromptCategory] = useState<string>('all');
  const [currentPrompt, setCurrentPrompt] = useState<Prompt | null>(null);
  const [myAnswer, setMyAnswer] = useState('');
  const [partnerAnswer, setPartnerAnswer] = useState('');
  const pool = useMemo(() => promptPool(promptCategory, favorites), [promptCategory, favorites]);
  const shuffle = (cat = promptCategory) => {
    const next = pickPrompt(promptPool(cat, favorites), currentPrompt);
    setCurrentPrompt(next);
    setMyAnswer(''); setPartnerAnswer('');
  };
  useEffect(() => { if (!currentPrompt) shuffle(); /* eslint-disable-next-line */ }, [promptCategory]);
  useEffect(() => { if (currentPrompt && promptCategory !== 'favorites' && !promptPool(promptCategory, favorites).some((p) => p[0] === currentPrompt[0])) shuffle(); /* eslint-disable-next-line */ }, [promptCategory]);

  // ── riwayat jawaban ─────────────────────────────────────────────────────
  const [historyQuery, setHistoryQuery] = useState('');
  const [historyCat, setHistoryCat] = useState('all');
  const [historyFavOnly, setHistoryFavOnly] = useState(false);
  const cats = useMemo(() => historyCategories(responses), [responses]);
  const history = useMemo(
    () => filterResponses(responses, { query: historyQuery, category: historyCat, onlyFavorites: historyFavOnly }, favorites),
    [responses, historyQuery, historyCat, historyFavOnly, favorites],
  );

  // ── tren mood ───────────────────────────────────────────────────────────
  const [moodRange, setMoodRange] = useState(30);
  const stats = useMemo(() => checkinStats(checkins, today), [checkins, today]);
  const series = useMemo(() => buildMoodSeries(checkins, today, moodRange), [checkins, today, moodRange]);
  const favList = useMemo(() => favoritePrompts(favorites), [favorites]);

  // ── review mingguan ─────────────────────────────────────────────────────
  const [weekDate, setWeekDate] = useState(() => weekStartOf(today));
  const [revAppr, setRevAppr] = useState('');
  const [revWins, setRevWins] = useState('');
  const [revSupport, setRevSupport] = useState('');
  const [revIntent, setRevIntent] = useState('');

  const askPartner = (prompt: Prompt | null) => {
    if (!prompt) return;
    const text = t(prompt[2], prompt[0]);
    try {
      if (typeof navigator !== 'undefined' && navigator.clipboard?.writeText) {
        navigator.clipboard.writeText(text);
      }
    } catch { /* clipboard tidak tersedia — teks tetap tampil di layar */ }
    showToast('success', t('berhasil_title', 'Berhasil'), trv('love_conn_copied', { prompt: text }, 'Prompt disalin — kirim ke pasanganmu.'));
  };

  return (
    <div className="space-y-4" data-testid="love-conn-panel">
      {/* ── Statistik check-in ── */}
      <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
        {[
          { icon: '🔥', label: t('love_conn_streak', '{n} hari berturut-turut').replace('{n}', String(stats.streak)), sub: t('love_conn_streak_sub', 'Streak check-in'), testid: 'love-conn-streak' },
          { icon: '📅', label: String(stats.total), sub: t('love_conn_stat_total', 'Total check-in'), testid: 'love-conn-total' },
          { icon: '🙂', label: String(stats.avgMy || '—'), sub: t('love_conn_my_mood', 'Mood kamu'), testid: 'love-conn-avg-my' },
          { icon: '💞', label: String(stats.avgPartner || '—'), sub: t('love_conn_partner_mood', 'Mood pasangan'), testid: 'love-conn-avg-partner' },
          { icon: '✨', label: String(stats.avgScore || '—'), sub: t('love_conn_score', 'Skor koneksi'), testid: 'love-conn-avg-score' },
        ].map((c) => (
          <div key={c.testid} data-testid={c.testid} className="p-3 rounded-2xl bg-slate-900/70 border border-slate-800">
            <div className="text-lg leading-none">{c.icon}</div>
            <div className="text-sm font-bold text-slate-100 mt-1 truncate">{c.label}</div>
            <div className="text-[10px] text-slate-500">{c.sub}</div>
          </div>
        ))}
      </div>

      {/* ── Grafik tren mood ── */}
      <div className="p-5 bg-slate-900/70 border border-slate-800 rounded-2xl space-y-3" data-testid="love-conn-mood-card">
        <div className="flex flex-wrap items-center gap-2">
          <h3 className="font-bold text-sm text-slate-200 flex-1">{t('love_conn_mood_trend', 'Tren mood')}</h3>
          {stats.streak > 1 && (
            <span className="text-[10px] px-2 py-0.5 rounded-full bg-amber-500/15 text-amber-300 border border-amber-500/30 inline-flex items-center gap-1">
              <Flame className="w-3 h-3" />{trv('love_conn_streak', { n: stats.streak }, `${stats.streak} hari berturut-turut`)}
            </span>
          )}
          <select value={moodRange} onChange={(e) => setMoodRange(Number(e.target.value))} className={`${inputCls} w-auto`} data-testid="love-conn-range">
            <option value={30}>{t('love_conn_range_30', '30 hari')}</option>
            <option value={90}>{t('love_conn_range_90', '90 hari')}</option>
          </select>
        </div>
        {series.empty ? (
          <p className="text-xs text-slate-500 py-4 text-center">{t('love_conn_trend_empty', 'Belum ada check-in pada rentang ini — grafik muncul setelah check-in pertama.')}</p>
        ) : (
          <>
            <div className="flex flex-wrap items-center gap-3 text-[10px] text-slate-400">
              <span className="inline-flex items-center gap-1"><span className="w-2.5 h-2.5 rounded-full bg-emerald-400 inline-block" />{t('love_conn_my_mood', 'Mood kamu')}</span>
              <span className="inline-flex items-center gap-1"><span className="w-2.5 h-2.5 rounded-full bg-rose-400 inline-block" />{t('love_conn_partner_mood', 'Mood pasangan')}</span>
              <span className="ml-auto">{trv('love_conn_points', { n: series.labels.length }, `${series.labels.length} titik data`)}</span>
            </div>
            <DualLineChart
              labels={series.labels}
              a={series.my.map((p, i) => ({ label: series.labels[i], value: p.value }))}
              b={series.partner.map((p, i) => ({ label: series.labels[i], value: p.value }))}
              height={170}
            />
            <div className="pt-1">
              <p className="text-[11px] text-slate-400 mb-1">{t('love_conn_score_trend', 'Skor koneksi (1–5)')}</p>
              <LineChart data={series.score.map((p, i) => ({ label: series.labels[i], value: p.value }))} height={120} color="#fb7185" />
            </div>
          </>
        )}
      </div>

      {/* ── Prompt koneksi ── */}
      <div className="p-5 bg-slate-900/70 border border-slate-800 rounded-2xl space-y-3">
        <div className="flex flex-wrap items-center gap-2">
          <h3 className="font-bold text-sm text-slate-200 flex-1">{t('love_connection_prompts', 'Prompt Koneksi')}</h3>
          <select value={promptCategory} onChange={(e) => setPromptCategory(e.target.value)} className={`${inputCls} w-auto`} data-testid="love-conn-category">
            {PROMPT_CATEGORIES.map((c) => (
              <option key={c} value={c}>{t(`love_prompt_${c}`, c)}</option>
            ))}
          </select>
          <button type="button" onClick={() => shuffle()} className={btnGhost} data-testid="love-conn-shuffle">
            <Shuffle className="w-3.5 h-3.5 inline mr-1" />{t('love_prompt_shuffle', 'Acak')}
          </button>
          <button
            type="button"
            disabled={!currentPrompt}
            onClick={() => currentPrompt && onFavorite(currentPrompt[0])}
            className={btnGhost}
            data-testid="love-conn-fav-toggle"
          >
            <Star className={`w-3.5 h-3.5 inline mr-1 ${currentPrompt && favorites.includes(currentPrompt[0]) ? 'fill-amber-400 text-amber-400' : ''}`} />
            {currentPrompt && favorites.includes(currentPrompt[0])
              ? t('love_prompt_unfavorite', 'Batal Favorit')
              : t('love_prompt_favorite', 'Favorit')}
          </button>
          <button type="button" disabled={!currentPrompt} onClick={() => askPartner(currentPrompt)} className={btnGhost} data-testid="love-conn-ask">
            <Copy className="w-3.5 h-3.5 inline mr-1" />{t('love_conn_ask_partner', 'Tanya pasangan')}
          </button>
        </div>
        <p className="text-center text-sm text-rose-200 font-semibold py-4" data-testid="love-conn-prompt-text">
          {currentPrompt ? t(currentPrompt[2], currentPrompt[0]) : t('love_prompt_no_favorites', 'Tidak ada prompt pada kategori ini.')}
          <span className="block text-[10px] text-slate-500 mt-1">{trv('love_conn_pool_count', { n: pool.length }, `${pool.length} prompt pada kategori ini`)}</span>
        </p>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          <div>
            <label className="block text-[11px] text-slate-400 mb-1">{t('love_prompt_my_reflection', 'Refleksiku')}</label>
            <textarea value={myAnswer} onChange={(e) => setMyAnswer(e.target.value)} rows={3} className={inputCls} placeholder={t('love_prompt_my_ph', 'Tulis jawabanmu…')} />
          </div>
          <div>
            <label className="block text-[11px] text-slate-400 mb-1">{t('love_prompt_partner_reflection', 'Refleksi Pasangan')}</label>
            <textarea value={partnerAnswer} onChange={(e) => setPartnerAnswer(e.target.value)} rows={3} className={inputCls} placeholder={t('love_prompt_partner_ph', 'Tulis jawaban pasangan…')} />
          </div>
        </div>
        <button
          type="button"
          onClick={() => {
            if (!currentPrompt) return;
            if (!myAnswer.trim() && !partnerAnswer.trim()) {
              showToast('info', t('msg_error', 'Error'), t('love_prompt_answer_required', 'Isi salah satu jawaban dulu.'));
              return;
            }
            onSaveResponse({
              promptKey: currentPrompt[0],
              category: currentPrompt[1],
              prompt: t(currentPrompt[2], currentPrompt[0]),
              answer: myAnswer,
              partnerAnswer,
            });
            setMyAnswer(''); setPartnerAnswer('');
          }}
          className={btnRose}
          data-testid="love-conn-save-response"
        >
          {t('love_prompt_save', 'Simpan Jawaban')}
        </button>
      </div>

      {/* ── Riwayat jawaban ── */}
      <div className="p-5 bg-slate-900/70 border border-slate-800 rounded-2xl space-y-2" data-testid="love-conn-history">
        <div className="flex flex-wrap items-center gap-2">
          <h3 className="font-bold text-sm text-slate-200 flex-1">{t('love_conn_history', 'Riwayat jawaban')}</h3>
          <div className="relative">
            <Search className="w-3.5 h-3.5 absolute left-2 top-1/2 -translate-y-1/2 text-slate-500" />
            <input
              value={historyQuery}
              onChange={(e) => setHistoryQuery(e.target.value)}
              className={`${inputCls} pl-7 w-44`}
              placeholder={t('love_conn_search_ph', 'Cari prompt…')}
              data-testid="love-conn-search"
            />
          </div>
          <select value={historyCat} onChange={(e) => setHistoryCat(e.target.value)} className={`${inputCls} w-auto`} data-testid="love-conn-history-cat">
            <option value="all">{t('love_conn_filter_all', 'Semua kategori')}</option>
            {cats.map((c) => (
              <option key={c.id} value={c.id}>{t(`love_prompt_${c.id}`, c.id)} ({c.count})</option>
            ))}
          </select>
          <button
            type="button"
            onClick={() => setHistoryFavOnly((v) => !v)}
            className={historyFavOnly ? btnRose : btnGhost}
            data-testid="love-conn-history-fav"
          >
            <Star className={`w-3.5 h-3.5 inline mr-1 ${historyFavOnly ? 'fill-current' : ''}`} />
            {t('love_conn_only_favorites', 'Hanya favorit')}
          </button>
          <span className="text-[10px] text-slate-500">{trv('love_conn_showing', { n: history.length, total: responses.length }, `${history.length}/${responses.length}`)}</span>
        </div>
        <div className="max-h-64 overflow-y-auto space-y-1">
          {history.map((r) => (
            <div key={r.id} className="flex items-start gap-2 text-xs text-slate-300 py-1 border-b border-slate-800/50" data-testid="love-conn-history-row">
              <div className="flex-1">
                <span className="text-slate-500">{historyDate(r.createdAt) || r.promptKey}</span> · {r.prompt}
                {r.answer && <div className="text-slate-400">🙋 {r.answer}</div>}
                {r.partnerAnswer && <div className="text-slate-400">💞 {r.partnerAnswer}</div>}
              </div>
              <button
                type="button"
                onClick={() => onFavorite(r.promptKey)}
                className={`p-1 hover:text-amber-300 ${favorites.includes(r.promptKey) ? 'text-amber-400' : 'text-slate-500'}`}
                title={t('love_prompt_favorite', 'Favorit')}
              >
                <Star className={`w-3.5 h-3.5 ${favorites.includes(r.promptKey) ? 'fill-current' : ''}`} />
              </button>
              <button
                type="button"
                onClick={() => {
                  const found = promptByKey(r.promptKey);
                  setCurrentPrompt(found || [r.promptKey, r.category, r.prompt]);
                  setMyAnswer(''); setPartnerAnswer('');
                  showToast('info', t('love_conn_reuse', 'Prompt diulang'), r.prompt);
                }}
                className="p-1 text-slate-500 hover:text-rose-300"
                title={t('love_conn_reuse', 'Jawab ulang')}
                data-testid="love-conn-reuse"
              >
                <Shuffle className="w-3.5 h-3.5" />
              </button>
              <button type="button" onClick={() => r.id && onDeleteResponse(r.id)} className="p-1 text-slate-500 hover:text-rose-400" title={t('love_delete_selected', 'Hapus')}>
                <Trash2 className="w-3.5 h-3.5" />
              </button>
            </div>
          ))}
          {!history.length && (
            <p className="text-xs text-slate-500" data-testid="love-conn-history-empty">
              {responses.length
                ? t('love_conn_no_match', 'Tidak ada jawaban yang cocok dengan filter ini.')
                : t('love_conn_empty_history', 'Belum ada jawaban tersimpan. Mulai dari satu prompt.')}
            </p>
          )}
        </div>
      </div>

      {/* ── Prompt favorit ── */}
      <div className="p-5 bg-slate-900/70 border border-slate-800 rounded-2xl space-y-2" data-testid="love-conn-favorites">
        <h3 className="font-bold text-sm text-slate-200">{t('love_conn_favorites', 'Prompt favorit')}</h3>
        {favList.length ? (
          <div className="flex flex-wrap gap-2">
            {favList.map((p) => (
              <span key={p[0]} className="inline-flex items-center gap-1 text-[11px] px-2 py-1 rounded-full bg-slate-800 border border-slate-700 text-slate-200" data-testid="love-conn-fav-chip">
                <button type="button" className="max-w-[16rem] truncate text-left" onClick={() => { setCurrentPrompt(p); setMyAnswer(''); setPartnerAnswer(''); }} title={t('love_conn_use', 'Pakai prompt ini')}>
                  {t(p[2], p[0])}
                </button>
                <button type="button" onClick={() => askPartner(p)} className="text-slate-400 hover:text-rose-300" title={t('love_conn_ask_partner', 'Tanya pasangan')}>
                  <Copy className="w-3 h-3" />
                </button>
                <button type="button" onClick={() => onFavorite(p[0])} className="text-amber-400 hover:text-amber-200" title={t('love_prompt_unfavorite', 'Batal Favorit')}>
                  <Star className="w-3 h-3 fill-current" />
                </button>
              </span>
            ))}
          </div>
        ) : (
          <p className="text-xs text-slate-500">{t('love_conn_favorites_empty', 'Belum ada prompt favorit — tekan ⭐ pada prompt untuk menyimpannya di sini.')}</p>
        )}
      </div>

      {/* ── Review mingguan ── */}
      <div className="p-5 bg-slate-900/70 border border-slate-800 rounded-2xl space-y-3">
        <div className="flex items-center gap-2">
          <h3 className="font-bold text-sm text-slate-200 flex-1">{t('love_weekly_review', 'Review Mingguan')}</h3>
          <label className="text-[11px] text-slate-400">{t('love_week_of', 'Minggu mulai')}</label>
          <input type="date" value={weekDate} onChange={(e) => setWeekDate(e.target.value)} className={`${inputCls} w-auto`} />
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
          <input value={revAppr} onChange={(e) => setRevAppr(e.target.value)} className={inputCls} placeholder={t('love_review_appreciation_ph', 'Apresiasi minggu ini…')} />
          <input value={revWins} onChange={(e) => setRevWins(e.target.value)} className={inputCls} placeholder={t('love_review_wins_ph', 'Kemenangan kecil…')} />
          <input value={revSupport} onChange={(e) => setRevSupport(e.target.value)} className={inputCls} placeholder={t('love_review_support_ph', 'Butuh dukungan di…')} />
          <input value={revIntent} onChange={(e) => setRevIntent(e.target.value)} className={inputCls} placeholder={t('love_review_intention_ph', 'Niat bersama minggu depan…')} />
        </div>
        <button
          type="button"
          onClick={() => {
            if (!revAppr.trim() || !revWins.trim()) {
              showToast('info', t('msg_error', 'Error'), t('love_review_required', 'Lengkapi apresiasi & kemenangan.'));
              return;
            }
            onSaveWeekly({ weekStart: weekDate, appreciation: revAppr, wins: revWins, support: revSupport, intention: revIntent });
            setRevAppr(''); setRevWins(''); setRevSupport(''); setRevIntent('');
          }}
          className={btnRose}
        >
          {t('love_review_save', 'Simpan Review')}
        </button>
        <div className="max-h-40 overflow-y-auto space-y-1">
          {(loveSpace.weeklyReviews || []).map((w: any) => (
            <div key={w.id} className="flex items-start gap-2 text-xs text-slate-300 py-1 border-b border-slate-800/50">
              <div className="flex-1">
                <span className="text-slate-500">{w.weekStart}</span> — {w.appreciation}
                {w.wins && <div className="text-slate-400">🏆 {w.wins}</div>}
                {w.support && <div className="text-slate-400">🤝 {w.support}</div>}
                {w.intention && <div className="text-slate-400">🎯 {w.intention}</div>}
              </div>
              <button type="button" onClick={() => onDeleteWeekly(w.id)} className="p-1 text-slate-500 hover:text-rose-400" title={t('love_delete_selected', 'Hapus')}><Trash2 className="w-3.5 h-3.5" /></button>
            </div>
          ))}
          {!(loveSpace.weeklyReviews || []).length && <p className="text-xs text-slate-500">{t('love_review_empty_history', 'Belum ada review.')}</p>}
        </div>
      </div>
    </div>
  );
};
