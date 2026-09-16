/**
 * LoveOverviewPanel.tsx — tab `overview` Love Space (fase A12).
 *
 * Dashboard pasangan: hero hitungan hari bersama, hari istimewa berikutnya
 * (dengan tombol "Buat pengingat" → Reminder tahunan), cincin skor kedekatan,
 * statistik perjalanan, aksi cepat, plus check-in harian & riwayatnya yang
 * sudah ada sejak awal (tidak ada fitur lama yang dihapus).
 *
 * Semua turunan angka datang dari `overviewUtils.ts` (murni, bisa diuji tanpa
 * DOM). Data hari istimewa berasal dari `GET /api/love/events/upcoming`
 * (server: acara `yearly` + ulang tahun & hari jadi dari profil, 29 Feb aman).
 */
import React, { useMemo, useRef, useState } from 'react';
import { NumberInput } from '../NumberInput';
import { ConnectionScoreRing } from './ConnectionScoreRing';
import {
  countdownBadge,
  daysTogether,
  durationText,
  isProfileSpecial,
  lastCheckinText,
  nextAgenda,
  nextSpecialDay,
  overviewStats,
  quickActions,
  relationshipLabel,
  scoreBreakdown,
  specialIcon,
  todayIso,
  type UpcomingItem,
} from './overviewUtils';

const inputCls = 'ct-input px-2 py-1.5 rounded-lg text-slate-200 text-xs';
const btnRose = 'ct-btn ct-btn-rose ct-btn-sm';
const btnGhost = 'ct-btn ct-btn-secondary ct-btn-sm';

const MOODS: Array<[number, string]> = [[1, '😞'], [2, '😕'], [3, '😐'], [4, '🙂'], [5, '🥰']];

export interface LoveOverviewPanelProps {
  t: (k: string, fb: string) => string;
  trv: (k: string, vars: Record<string, string | number>, fb: string) => string;
  loveSpace: any;
  today: string;
  upcoming: UpcomingItem[];
  loadingUpcoming?: boolean;
  onRefreshUpcoming?: () => void;
  onCheckin: (payload: { myMood: number; partnerMood: number; connectionScore: number; note: string }) => void;
  onQuickAction: (action: 'memory' | 'event' | 'bucket' | 'reminders') => void;
  /** A12: aksi "check-in" digulirkan ke kartu check-in di panel ini (tanpa pindah tab). */
  onEditProfile: () => void;
  onOpenTracking: () => void;
  onCreateReminder: (item: UpcomingItem) => void;
  showToast: (kind: any, title: string, msg: string) => void;
}

export const LoveOverviewPanel: React.FC<LoveOverviewPanelProps> = ({
  t, trv, loveSpace, today, upcoming, loadingUpcoming, onRefreshUpcoming,
  onCheckin, onQuickAction, onEditProfile, onOpenTracking, onCreateReminder, showToast,
}) => {
  const checkins = loveSpace.checkins || [];
  const todayCheckin = checkins.find((c: any) => String(c?.date || '').slice(0, 10) === todayIso(today));

  const checkinRef = useRef<HTMLDivElement | null>(null);
  const [myMood, setMyMood] = useState<number>(Number(todayCheckin?.myMood) || 3);
  const [partnerMood, setPartnerMood] = useState<number>(Number(todayCheckin?.partnerMood) || 3);
  const [connScore, setConnScore] = useState<number>(Number(todayCheckin?.connectionScore) || 4);
  const [checkNote, setCheckNote] = useState('');

  const startDate = String(loveSpace.startDate || loveSpace.anniversaryDate || '');
  const days = useMemo(() => daysTogether(startDate, today), [startDate, today]);
  const stats = useMemo(() => overviewStats(loveSpace, today), [loveSpace, today]);
  const breakdown = useMemo(() => scoreBreakdown(loveSpace, today), [loveSpace, today]);
  const special = useMemo(() => nextSpecialDay(upcoming || []), [upcoming]);
  const agenda = useMemo(() => nextAgenda(upcoming || [], special?.id || ''), [upcoming, special]);
  const relLabel = relationshipLabel(loveSpace.relationshipType, t);
  const coupleActive = !!loveSpace.coupleActive;
  const partnerName = loveSpace.partnerName || t('love_partner_not_set', 'Pasangan belum diatur');
  const myName = loveSpace.myName || t('love_me', 'Aku');
  const initials = (name: string) => (String(name || '?').trim().slice(0, 1) || '?').toUpperCase();

  return (
    <div className="space-y-4" data-testid="love-overview-panel">
      {/* ── Hero: hitungan hari bersama ── */}
      <div className="p-5 bg-gradient-to-br from-rose-500/10 via-slate-900/70 to-slate-900/70 border border-rose-500/20 rounded-2xl space-y-4"
        data-testid="love-hero">
        <div className="flex flex-wrap items-center gap-4">
          <div className="flex items-center gap-2">
            <span className="w-11 h-11 rounded-full bg-slate-800 border border-rose-500/30 flex items-center justify-center text-lg font-black text-rose-200">
              {initials(myName)}
            </span>
            <span className="text-slate-500 text-lg">💞</span>
            <span className="w-11 h-11 rounded-full bg-slate-800 border border-rose-500/30 flex items-center justify-center text-lg font-black text-rose-200">
              {loveSpace.partnerAvatar && String(loveSpace.partnerAvatar).length <= 2 ? loveSpace.partnerAvatar : initials(partnerName)}
            </span>
          </div>
          <div className="flex-1 min-w-[180px]">
            <h3 className="font-bold text-sm text-slate-100 truncate" data-testid="love-hero-names">
              {myName} &amp; {partnerName}
            </h3>
            <p className="text-[11px] text-slate-400">
              {relLabel || t('love_overview_sub', 'Ringkasan perjalanan kalian berdua')}
              {startDate ? ` · ${trv('love_hero_since', { date: startDate }, `Sejak ${startDate}`)}` : ''}
            </p>
          </div>
          <div className="flex flex-wrap items-center gap-1.5">
            {coupleActive ? (
              <span className="px-2 py-0.5 rounded-full text-[9px] font-black tracking-wider bg-emerald-500/15 text-emerald-300 border border-emerald-500/30">
                ✅ {t('love_couple_status_active', 'Couple aktif')}
              </span>
            ) : (
              <span className="px-2 py-0.5 rounded-full text-[9px] font-black tracking-wider bg-slate-700/40 text-slate-400 border border-slate-600/40">
                🔒 {t('love_couple_status_none', 'Belum terhubung couple')}
              </span>
            )}
          </div>
        </div>

        {startDate ? (
          <div className="flex items-center gap-4 bg-slate-950/60 p-4 rounded-xl border border-slate-800">
            <div className="text-center">
              <span className="text-3xl font-extrabold text-rose-400 font-mono" data-testid="love-hero-days">{days}</span>
              <span className="block text-[10px] uppercase tracking-wider text-slate-500 font-bold">
                {t('love_days_together', 'Hari bersama')}
              </span>
            </div>
            <div className="h-9 w-px bg-slate-800" />
            <p className="text-xs text-rose-200 font-semibold" data-testid="love-hero-duration">
              {durationText(days, trv)}
            </p>
          </div>
        ) : (
          <div className="bg-slate-950/60 p-4 rounded-xl border border-slate-800 space-y-2" data-testid="love-hero-empty-cta">
            <p className="text-xs text-slate-300">{t('love_empty_cta', 'Isi tanggal jadian untuk membuka hitungan hari bersama.')}</p>
            <div className="flex flex-wrap gap-2">
              <button type="button" onClick={onEditProfile} className={btnRose} data-testid="love-hero-edit-profile">
                {t('love_edit_profile', 'Edit Profil')}
              </button>
            </div>
          </div>
        )}

        {/* ── Hari istimewa berikutnya + agenda terdekat ── */}
        <div className="grid md:grid-cols-2 gap-3">
          <div className="p-4 bg-slate-950/60 rounded-xl border border-slate-800 space-y-2" data-testid="love-special-card">
            <div className="flex items-center gap-2">
              <h4 className="font-bold text-xs text-slate-200 flex-1">{t('love_next_special', 'Hari istimewa berikutnya')}</h4>
              {onRefreshUpcoming && (
                <button type="button" onClick={onRefreshUpcoming} className="text-[10px] text-slate-400 hover:text-rose-300">
                  {t('reminders_refresh', 'Muat ulang')}
                </button>
              )}
            </div>
            {special ? (
              <>
                <p className="text-sm text-slate-100 font-bold truncate" data-testid="love-special-title">
                  {specialIcon(special)} {special.title}
                  {isProfileSpecial(special) && (
                    <span className="ml-2 text-[9px] px-1.5 py-0.5 rounded-full bg-slate-800 border border-slate-700 text-slate-400">
                      {t('love_special_source_profile', 'dari profil')}
                    </span>
                  )}
                </p>
                <p className="text-[11px] text-slate-400">
                  {special.nextDate}
                  {Number(special.yearsCount) > 0 ? ` · ${trv('love_years_count', { n: Number(special.yearsCount) }, `yang ke-${special.yearsCount}`)}` : ''}
                </p>
                <p className="text-xs text-rose-300 font-bold" data-testid="love-special-countdown">{countdownBadge(special.daysUntil, t)}</p>
                <button type="button" onClick={() => onCreateReminder(special)} className={btnGhost} data-testid="love-special-create-reminder">
                  🔔 {t('love_create_reminder', 'Buat pengingat')}
                </button>
              </>
            ) : (
              <p className="text-xs text-slate-500" data-testid="love-special-empty">
                {loadingUpcoming ? t('loading', 'Memproses…') : t('love_special_none', 'Belum ada hari istimewa dalam 1 tahun ke depan.')}
              </p>
            )}
          </div>

          <div className="p-4 bg-slate-950/60 rounded-xl border border-slate-800 space-y-2" data-testid="love-upcoming-card">
            <h4 className="font-bold text-xs text-slate-200">{t('love_upcoming', 'Agenda Terdekat')}</h4>
            {agenda ? (
              <p className="text-xs text-slate-300" data-testid="love-upcoming-next">
                {specialIcon(agenda)} {agenda.title} · {countdownBadge(agenda.daysUntil, t)}
              </p>
            ) : (
              <p className="text-xs text-slate-500">{t('love_no_upcoming', 'Belum ada agenda bersama.')}</p>
            )}
            {(upcoming || []).length > 1 && (
              <div className="space-y-1 pt-1" data-testid="love-upcoming-list">
                {(upcoming || []).slice(0, 4).map((it) => (
                  <div key={it.id} className="flex items-center gap-2 text-[11px] text-slate-400" data-testid="love-upcoming-row">
                    <span>{specialIcon(it)}</span>
                    <span className="flex-1 truncate">{it.title}</span>
                    <span className="font-mono text-slate-300">{it.nextDate?.slice(5)}</span>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>

      {/* ── Skor kedekatan ── */}
      <ConnectionScoreRing t={t} trv={trv} breakdown={breakdown} lastCheckinText={lastCheckinText(breakdown, today, t)} />

      {/* ── Statistik perjalanan ── */}
      <div className="p-5 bg-slate-900/70 border border-slate-800 rounded-2xl space-y-3" data-testid="love-stats-card">
        <h3 className="font-bold text-sm text-slate-200">{t('love_stat_title', 'Statistik perjalanan')}</h3>
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-2">
          {[
            { id: 'memories', icon: '📸', value: String(stats.memories), label: t('love_stat_memories', 'Kenangan') },
            { id: 'bucket', icon: '🎯', value: trv('love_stat_bucket_of', { done: stats.bucketDone, total: stats.bucketTotal }, `${stats.bucketDone} dari ${stats.bucketTotal}`), label: t('love_stat_bucket_done', 'Bucket tercapai') },
            { id: 'photos', icon: '🖼️', value: String(stats.photos), label: t('love_stat_photos', 'Foto') },
            { id: 'albums', icon: '📚', value: String(stats.albums), label: t('love_stat_albums', 'Album') },
            { id: 'prompts', icon: '💬', value: String(stats.prompts), label: t('love_stat_prompts', 'Prompt terjawab') },
            { id: 'checkins', icon: '💗', value: String(stats.checkinsMonth), label: t('love_stat_checkins_month', 'Check-in bulan ini') },
          ].map((c) => (
            <div key={c.id} className="p-3 rounded-xl bg-slate-950/60 border border-slate-800" data-testid={`love-stat-${c.id}`}>
              <div className="text-base leading-none">{c.icon}</div>
              <div className="text-sm font-bold text-slate-100 mt-1 truncate">{c.value}</div>
              <div className="text-[10px] text-slate-500 truncate">{c.label}</div>
            </div>
          ))}
        </div>
      </div>

      {/* ── Aksi cepat ── */}
      <div className="p-5 bg-slate-900/70 border border-slate-800 rounded-2xl space-y-3" data-testid="love-quick-card">
        <h3 className="font-bold text-sm text-slate-200">{t('love_quick_title', 'Aksi cepat')}</h3>
        <div className="flex flex-wrap gap-2">
          {quickActions().map((a) => (
            <button
              key={a.id}
              type="button"
              onClick={() => {
                // "Check-in" cukup menggulir ke kartu check-in di bawah; sisanya
                // membuka dialog/tab yang sesuai lewat `onQuickAction`.
                if (a.action === 'checkin') checkinRef.current?.scrollIntoView({ behavior: 'smooth', block: 'center' });
                else onQuickAction(a.action);
              }}
              className={a.action === 'checkin' && breakdown.hasToday ? btnGhost : btnRose}
              data-testid={`love-quick-${a.id}`}
            >
              {a.icon} {a.action === 'checkin' && breakdown.hasToday
                ? t('love_quick_checkin_done', 'Sudah check-in hari ini')
                : t(a.labelKey, a.fallback)}
            </button>
          ))}
        </div>
      </div>

      {/* ── Check-in harian (parity lama: form + riwayat) ── */}
      <div ref={checkinRef} className="p-5 bg-slate-900/70 border border-slate-800 rounded-2xl space-y-3" data-testid="love-overview-checkin">
        <h3 className="font-bold text-sm text-slate-200">{t('love_daily_checkin', 'Check-in Harian')}</h3>
        <p className="text-xs text-slate-400" data-testid="love-overview-checkin-status">
          {todayCheckin
            ? trv('love_checkin_today_done', { my: todayCheckin.myMood, partner: todayCheckin.partnerMood, score: todayCheckin.connectionScore, note: todayCheckin.note || '—' }, '✅ Sudah check-in hari ini')
            : t('love_checkin_today_none', 'Belum check-in hari ini.')}
        </p>
        <div className="flex flex-wrap gap-3 items-end text-xs">
          <label className="space-y-1">
            <span className="block text-slate-400">{t('love_my_mood', 'Mood-ku')}</span>
            <select value={myMood} onChange={(e) => setMyMood(Number(e.target.value))} className={`${inputCls} w-auto`} data-testid="love-overview-my-mood">
              {MOODS.map(([v, ic]) => (<option key={v} value={v}>{ic} {v}/5</option>))}
            </select>
          </label>
          <label className="space-y-1">
            <span className="block text-slate-400">{t('love_partner_mood', 'Mood Pasangan')}</span>
            <select value={partnerMood} onChange={(e) => setPartnerMood(Number(e.target.value))} className={`${inputCls} w-auto`} data-testid="love-overview-partner-mood">
              {MOODS.map(([v, ic]) => (<option key={v} value={v}>{ic} {v}/5</option>))}
            </select>
          </label>
          <label className="space-y-1">
            <span className="block text-slate-400">{t('love_connection_score', 'Skor Koneksi')}</span>
            <NumberInput value={connScore} onValueChange={setConnScore} min={1} max={5} integer emptyValue={1} inputClassName={`${inputCls} w-20`} />
          </label>
        </div>
        <input
          value={checkNote}
          onChange={(e) => setCheckNote(e.target.value)}
          className={`${inputCls} w-full`}
          placeholder={t('love_checkin_note_ph', 'Catatan singkat hari ini…')}
          data-testid="love-overview-checkin-note"
        />
        <button
          type="button"
          onClick={() => {
            onCheckin({ myMood, partnerMood, connectionScore: connScore, note: checkNote });
            showToast('success', t('berhasil_title', 'Berhasil'), t('love_checkin_saved', 'Check-in tersimpan.'));
            setCheckNote('');
          }}
          className={btnRose}
          data-testid="love-overview-checkin-save"
        >
          {t('love_save_checkin', 'Simpan Check-in')}
        </button>
      </div>

      <div className="p-5 bg-slate-900/70 border border-slate-800 rounded-2xl space-y-2" data-testid="love-overview-checkin-history">
        <div className="flex items-center gap-2">
          <h3 className="font-bold text-sm text-slate-200 flex-1">{t('love_checkin_history', 'Riwayat Check-in')}</h3>
          <button type="button" onClick={onOpenTracking} className="text-[11px] text-slate-400 hover:text-rose-300" data-testid="love-overview-tracking">
            {t('love_open_tracking', 'Tracking Couple')}
          </button>
        </div>
        <div className="max-h-52 overflow-y-auto space-y-1">
          {checkins.map((c: any) => (
            <div key={c.id} className="text-xs text-slate-300 py-1 border-b border-slate-800/50" data-testid="love-overview-checkin-row">
              {trv('love_checkin_row', { date: c.date, my: c.myMood, partner: c.partnerMood, score: c.connectionScore, note: c.note || '—' }, `${c.date} · 🙂 ${c.myMood} · 💞 ${c.partnerMood}`)}
            </div>
          ))}
          {!checkins.length && <p className="text-xs text-slate-500">—</p>}
        </div>
      </div>
    </div>
  );
};

export default LoveOverviewPanel;
