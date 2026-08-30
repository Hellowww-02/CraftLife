import React, { useState, useEffect, useMemo, useRef } from 'react';
import { useGame } from '../../context/GameContext';
import { t } from '../../i18n';
import { studio } from '../../api/studio';
import { apiUploadFile } from '../../api/client';
import { X } from 'lucide-react';
import {
  Heart,
  MessageSquareHeart,
  Camera,
  Plus,
  Trash2,
  Pencil,
  FolderOpen,
  Images,
  CheckSquare,
  Square,
  Shuffle,
  Star,
  Eye,
  EyeOff,
  Calendar,
} from 'lucide-react';

/** Thumbnail for a Love Space photo; fetches the authed image URL once. */
const PhotoThumb: React.FC<{ photo: any; onClick?: () => void; selected?: boolean; selectMode?: boolean }> = ({ photo, onClick, selected, selectMode }) => {
  const [url, setUrl] = useState('');
  useEffect(() => {
    let alive = true;
    studio.lovePhotoImage(photo.id).then((u) => { if (alive) setUrl(u); }).catch(() => setUrl(''));
    return () => { alive = false; };
  }, [photo.id]);
  return (
    <div
      onClick={onClick}
      className={`cursor-pointer group relative overflow-hidden rounded-lg border aspect-video bg-slate-950 transition-colors ${
        selected ? 'border-rose-500 ring-2 ring-rose-500/50' : 'border-slate-800 hover:border-rose-500/40'
      }`}
    >
      {url ? (
        <img src={url} alt="" className="w-full h-full object-cover group-hover:scale-105 transition-transform" />
      ) : (
        <div className="w-full h-full flex items-center justify-center text-slate-600 text-3xl">🖼️</div>
      )}
      {photo.caption && (
        <span className="absolute bottom-0 inset-x-0 px-2 py-1 text-[10px] text-white bg-black/60 truncate">{photo.caption}</span>
      )}
      {selectMode && (
        <span className="absolute top-1 left-1 p-1 rounded bg-black/60 text-rose-300">
          {selected ? <CheckSquare className="w-4 h-4" /> : <Square className="w-4 h-4" />}
        </span>
      )}
    </div>
  );
};

/** Full-size viewer image (lightbox). */
const ViewerImage: React.FC<{ photo: any }> = ({ photo }) => {
  const [url, setUrl] = useState('');
  useEffect(() => {
    let alive = true;
    if (photo?.id) studio.lovePhotoImage(photo.id).then((u) => { if (alive) setUrl(u); }).catch(() => setUrl(''));
    return () => { alive = false; };
  }, [photo?.id]);
  if (!url) return <div className="w-full h-full flex items-center justify-center text-slate-600 text-4xl">🖼️</div>;
  return <img src={url} alt="" className="w-full h-full object-contain" />;
};

const Modal: React.FC<{ title: string; onClose: () => void; children: React.ReactNode; wide?: boolean }> = ({ title, onClose, children, wide }) => (
  <div className="fixed inset-0 z-[120] flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm" onClick={onClose}>
    <div
      className={`w-full ${wide ? 'max-w-3xl' : 'max-w-md'} bg-slate-900 border border-slate-700 rounded-2xl shadow-2xl p-5 space-y-3 max-h-[90vh] overflow-y-auto`}
      onClick={(e) => e.stopPropagation()}
    >
      <div className="flex items-center justify-between">
        <h3 className="font-bold text-sm text-slate-200">{title}</h3>
        <button onClick={onClose} className="p-1 rounded-lg hover:bg-slate-800 text-slate-400"><X className="w-4 h-4" /></button>
      </div>
      {children}
    </div>
  </div>
);

/** Interpolasi {var} — parity tr(key, **vars) PyQt. */
const trv = (key: string, vars: Record<string, string | number>, fb: string): string =>
  Object.entries(vars).reduce((acc, [k, v]) => acc.split(`{${k}}`).join(String(v)), t(key, fb));

const MOODS: Array<[number, string]> = [[1, '😞'], [2, '😕'], [3, '😐'], [4, '🙂'], [5, '🥰']];
/** Bank prompt Connection — parity LovePage.PROMPTS (key, category, trKey). */
const PROMPTS: Array<[string, string, string]> = [
  ['connection_seen', 'connection', 'love_prompt_connection_seen'],
  ['connection_safe', 'connection', 'love_prompt_connection_safe'],
  ['connection_listen', 'connection', 'love_prompt_connection_listen'],
  ['connection_closer', 'connection', 'love_prompt_connection_closer'],
  ['appreciation_small', 'appreciation', 'love_prompt_appreciation_small'],
  ['appreciation_quality', 'appreciation', 'love_prompt_appreciation_quality'],
  ['appreciation_memory', 'appreciation', 'love_prompt_appreciation_memory'],
  ['appreciation_growth', 'appreciation', 'love_prompt_appreciation_growth'],
  ['support_stress', 'support', 'love_prompt_support_stress'],
  ['support_request', 'support', 'love_prompt_support_request'],
  ['support_energy', 'support', 'love_prompt_support_energy'],
  ['support_team', 'support', 'love_prompt_support_team'],
  ['future_year', 'future', 'love_prompt_future_year'],
  ['future_home', 'future', 'love_prompt_future_home'],
  ['future_skill', 'future', 'love_prompt_future_skill'],
  ['future_priority', 'future', 'love_prompt_future_priority'],
  ['fun_date', 'fun', 'love_prompt_fun_date'],
  ['fun_laugh', 'fun', 'love_prompt_fun_laugh'],
  ['fun_adventure', 'fun', 'love_prompt_fun_adventure'],
  ['fun_switch', 'fun', 'love_prompt_fun_switch'],
];

type TabId = 'overview' | 'connection' | 'cycle' | 'memories' | 'gallery' | 'plans';

const inputCls = 'w-full px-2 py-1.5 rounded-lg bg-slate-950 border border-slate-800 text-slate-200 text-xs';
const btnRose = 'px-3 py-1.5 rounded-lg bg-rose-600 hover:bg-rose-500 text-white text-xs font-bold';
const btnGhost = 'px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-semibold';
const btnDanger = 'px-3 py-1.5 rounded-lg bg-rose-900/60 hover:bg-rose-900 text-rose-200 text-xs font-bold';

export const LoveSpaceView: React.FC = () => {
  const {
    user,
    loveSpace,
    updateLoveSpace,
    loveCheckin,
    loveEvent,
    loveWeekly,
    loveCycle,
    updateLovePhotoMeta,
    addLoveMemory,
    refreshLoveSpace,
    deleteLoveMemory,
    deleteLovePrompt,
    deleteLoveWeekly,
    deleteLoveCycle,
    deleteLoveEvent,
    deleteLoveBucket,
    deleteLovePhoto,
    toggleLoveBucketItem,
    lovePromptFavorite,
    createLoveAlbum,
    renameLoveAlbum,
    deleteLoveAlbum,
    loveAlbumAddPhoto,
    loveAlbumMovePhoto,
    loveAlbumRemovePhoto,
    lang,
    showToast,
  } = useGame();

  const [tab, setTab] = useState<TabId>('overview');

  // ── Overview / check-in ─────────────────────────────────────────────
  const today = new Date().toISOString().split('T')[0];
  const todayCheckin = (loveSpace.checkins || []).find((c) => c.date === today);
  const [myMood, setMyMood] = useState(todayCheckin?.myMood || 3);
  const [partnerMood, setPartnerMood] = useState(todayCheckin?.partnerMood || 3);
  const [connScore, setConnScore] = useState(todayCheckin?.connectionScore || 4);
  const [checkNote, setCheckNote] = useState('');

  // ── Connection / prompts ────────────────────────────────────────────
  const [promptCategory, setPromptCategory] = useState('all');
  const [currentPrompt, setCurrentPrompt] = useState<[string, string, string] | null>(null);
  const [myAnswer, setMyAnswer] = useState('');
  const [partnerAnswer, setPartnerAnswer] = useState('');

  const promptPool = useMemo(() => {
    if (promptCategory === 'all') return PROMPTS;
    if (promptCategory === 'favorites') return PROMPTS.filter((p) => (loveSpace.promptFavorites || []).includes(p[0]));
    return PROMPTS.filter((p) => p[1] === promptCategory);
  }, [promptCategory, loveSpace.promptFavorites]);

  const nextPrompt = () => {
    if (!promptPool.length) { setCurrentPrompt(null); return; }
    const alternatives = promptPool.filter((p) => !currentPrompt || p[0] !== currentPrompt[0]);
    const pick = (alternatives.length ? alternatives : promptPool)[Math.floor(Math.random() * (alternatives.length ? alternatives.length : promptPool.length))];
    setCurrentPrompt(pick);
    setMyAnswer(''); setPartnerAnswer('');
  };
  useEffect(() => { if (!currentPrompt && tab === 'connection') nextPrompt(); /* eslint-disable-next-line */ }, [tab, promptCategory]);

  // ── Weekly review ───────────────────────────────────────────────────
  const weekStartInit = () => {
    const d = new Date(); const dow = (d.getDay() + 6) % 7; d.setDate(d.getDate() - dow);
    return d.toISOString().split('T')[0];
  };
  const [weekDate, setWeekDate] = useState(weekStartInit());
  const [revAppr, setRevAppr] = useState('');
  const [revWins, setRevWins] = useState('');
  const [revSupport, setRevSupport] = useState('');
  const [revIntent, setRevIntent] = useState('');

  // ── Cycle ───────────────────────────────────────────────────────────
  const cs = loveSpace.cycleSettings || { trackedPerson: 'partner', lastPeriodStart: '', cycleLength: 28, periodLength: 5 };
  const [cycPerson, setCycPerson] = useState<'self' | 'partner'>(cs.trackedPerson);
  const [cycStart, setCycStart] = useState(cs.lastPeriodStart || today);
  const [cycLen, setCycLen] = useState(cs.cycleLength);
  const [perLen, setPerLen] = useState(cs.periodLength);
  useEffect(() => {
    setCycPerson(cs.trackedPerson); setCycStart(cs.lastPeriodStart || today);
    setCycLen(cs.cycleLength); setPerLen(cs.periodLength);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [loveSpace.cycleSettings?.lastPeriodStart, loveSpace.cycleSettings?.cycleLength]);

  // ── Memories ────────────────────────────────────────────────────────
  const [showAddMemModal, setShowAddMemModal] = useState(false);
  const [newMemTitle, setNewMemTitle] = useState('');
  const [newMemDate, setNewMemDate] = useState(today);
  const [newMemDesc, setNewMemDesc] = useState('');

  // ── Plans ───────────────────────────────────────────────────────────
  const [evTitle, setEvTitle] = useState('');
  const [evDate, setEvDate] = useState(today);
  const [evCategory, setEvCategory] = useState('date');
  const [evNotes, setEvNotes] = useState('');
  const [bucketTitle, setBucketTitle] = useState('');

  // ── Gallery ─────────────────────────────────────────────────────────
  const [gFilter, setGFilter] = useState<'all' | 'shared' | 'private'>('all');
  const [gAlbum, setGAlbum] = useState<string>('');
  const [selectMode, setSelectMode] = useState(false);
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [viewer, setViewer] = useState<any>(null);
  const [albumFor, setAlbumFor] = useState<any>(null); // photo being assigned
  const [albumTarget, setAlbumTarget] = useState('');
  const fileRef = useRef<HTMLInputElement>(null);
  const [uploadQueue, setUploadQueue] = useState<File[]>([]);
  const [uploadIdx, setUploadIdx] = useState(-1);
  const [upCaption, setUpCaption] = useState('');
  const [upDate, setUpDate] = useState(today);
  const [upVis, setUpVis] = useState<'private' | 'shared'>('private');
  const upStats = useRef({ ok: 0, fail: 0 });

  // ── Profile edit ────────────────────────────────────────────────────
  const [showProfile, setShowProfile] = useState(false);
  const [profPartner, setProfPartner] = useState(loveSpace.partnerName || '');
  const [profMy, setProfMy] = useState((loveSpace as any).myName || '');
  const [profStart, setProfStart] = useState((loveSpace as any).startDate || loveSpace.anniversaryDate || today);

  const coupleActive = !!loveSpace.coupleActive;

  const daysTogether = useMemo(() => {
    try {
      const start = new Date((loveSpace as any).startDate || loveSpace.anniversaryDate);
      return Math.max(1, Math.ceil(Math.abs(Date.now() - start.getTime()) / 86400000));
    } catch { return 1; }
  }, [loveSpace]);

  const futureEvents = useMemo(() =>
    (loveSpace.events || [])
      .filter((e) => e.date >= today)
      .sort((a, b) => a.date.localeCompare(b.date)),
  [loveSpace.events, today]);

  const nextEvent = futureEvents[0];

  const albums = loveSpace.albums || [];
  const myPhotosOwn = (ph: any) => !ph.ownerUserId || ph.ownerUserId === String((user as any)?.id || '');

  const filteredPhotos = useMemo(() => {
    const all = loveSpace.photos || [];
    let out = all;
    if (gFilter !== 'all') out = out.filter((p) => (p.visibility || 'private') === gFilter);
    if (gAlbum) {
      const alb = albums.find((a) => a.id === gAlbum);
      if (alb) out = out.filter((p) => alb.photoIds.includes(String(p.id)));
    }
    return out;
  }, [loveSpace.photos, gFilter, gAlbum, albums]);

  const albumOf = (pid: string) => albums.find((a) => a.photoIds.includes(String(pid)));

  // ── Upload flow (parity _upload_gallery_photo + _GalleryPhotoDialog) ──
  const UPLOAD_MAX = 8 * 1024 * 1024;
  const onPickFiles = (files: FileList | null) => {
    if (!files || !files.length) return;
    upStats.current = { ok: 0, fail: 0 };
    setUploadQueue(Array.from(files));
    setUpCaption(''); setUpDate(today); setUpVis('private');
    setUploadIdx(0);
  };

  const processUpload = async (applyMeta: boolean) => {
    const f = uploadQueue[uploadIdx];
    if (!f) return;
    if (f.size > UPLOAD_MAX) {
      upStats.current.fail++;
    } else {
      try {
        const res: any = await apiUploadFile('love_photo', f, applyMeta
          ? { caption: upCaption, photoDate: upDate, visibility: upVis }
          : { visibility: 'private' });
        if (res?.result?.ok || res?.ok) upStats.current.ok++;
        else upStats.current.fail++;
      } catch { upStats.current.fail++; }
    }
    const next = uploadIdx + 1;
    if (next < uploadQueue.length) {
      setUpCaption(''); setUpDate(today); setUpVis('private');
      setUploadIdx(next);
    } else {
      setUploadIdx(-1); setUploadQueue([]);
      const { ok, fail } = upStats.current;
      showToast(fail ? 'info' : 'success',
        fail ? t('gagal_title', 'Gagal') : t('berhasil_title', 'Berhasil'),
        trv('love_gallery_multi_result', { ok, fail }, '{ok} foto berhasil, {fail} gagal.'));
      refreshLoveSpace();
    }
  };

  const bulkDelete = () => {
    if (!selected.size) return;
    if (!window.confirm(t('love_gallery_delete_confirm', 'Hapus foto terpilih?'))) return;
    selected.forEach((pid) => deleteLovePhoto(pid));
    setSelected(new Set()); setSelectMode(false);
  };
  const bulkVis = (vis: 'private' | 'shared') => {
    selected.forEach((pid) => {
      const ph = (loveSpace.photos || []).find((p) => String(p.id) === String(pid));
      if (ph && myPhotosOwn(ph)) updateLovePhotoMeta(pid, { caption: ph.caption, photoDate: ph.photoDate, visibility: vis });
    });
    setSelected(new Set());
  };

  const TABS: Array<{ id: TabId; icon: React.ReactNode }> = [
    { id: 'overview', icon: <Heart className="w-4 h-4" /> },
    { id: 'connection', icon: <MessageSquareHeart className="w-4 h-4" /> },
    { id: 'cycle', icon: <Calendar className="w-4 h-4" /> },
    { id: 'memories', icon: <Heart className="w-4 h-4" /> },
    { id: 'gallery', icon: <Camera className="w-4 h-4" /> },
    { id: 'plans', icon: <Plus className="w-4 h-4" /> },
  ];

  const miniStat = (label: string, value: React.ReactNode) => (
    <div className="flex-1 min-w-[120px] p-4 bg-slate-900/70 border border-slate-800 rounded-2xl text-center">
      <div className="text-xl font-extrabold text-rose-400 font-mono">{value}</div>
      <div className="text-[10px] uppercase tracking-wider text-slate-500 font-bold mt-1">{label}</div>
    </div>
  );

  return (
    <div id="love-space-view" className="space-y-6">
      {/* Header Hero Banner (parity header LovePage: title + edit profile + end couple) */}
      <div className="p-6 bg-gradient-to-r from-rose-950/60 via-slate-900 to-pink-950/40 border border-rose-500/20 rounded-2xl flex flex-col md:flex-row items-center justify-between gap-6 shadow-xl">
        <div className="flex items-center gap-4 text-center md:text-left">
          <div className="w-16 h-16 rounded-2xl bg-rose-500/10 border border-rose-500/30 flex items-center justify-center text-3xl shadow-lg shrink-0">
            {loveSpace.partnerAvatar || '🌸'}
          </div>
          <div>
            <div className="flex items-center gap-2 justify-center md:justify-start">
              <h1 className="text-xl font-bold text-slate-100">{lang === 'id' ? 'Ruang Cinta (Love Space)' : 'Love Space'}</h1>
              <span className="text-xs px-2.5 py-0.5 rounded-full bg-rose-500/20 text-rose-300 font-semibold flex items-center gap-1">
                <Heart className="w-3 h-3 fill-rose-400 text-rose-400" />
                <span>Together with {loveSpace.partnerName || 'Partner'}</span>
              </span>
            </div>
            <p className="text-xs text-slate-400 mt-1">
              {lang === 'id'
                ? 'Abadikan kenangan bersama, jawab pertanyaan harian, dan pantau bucket list berdua.'
                : 'Cherish shared memories, daily connection prompts, and mutual bucket list dreams.'}
            </p>
          </div>
        </div>
        <div className="flex flex-col items-center gap-2">
          <div className="flex items-center gap-4 bg-slate-950/70 p-4 rounded-xl border border-slate-800">
            <div className="text-center">
              <span className="text-2xl font-extrabold text-rose-400 font-mono">{daysTogether}</span>
              <span className="block text-[10px] uppercase tracking-wider text-slate-500 font-bold">{t('love_days_together', 'Hari Bersama')}</span>
            </div>
            <div className="h-8 w-px bg-slate-800" />
            <div className="text-center">
              <span className="text-2xl font-extrabold text-emerald-400 font-mono">{loveSpace.connectionScore}%</span>
              <span className="block text-[10px] uppercase tracking-wider text-slate-500 font-bold">{t('love_connection', 'Harmoni')}</span>
            </div>
          </div>
          <div className="flex gap-2">
            <button type="button" onClick={() => setShowProfile(true)} className={btnRose}>
              {t('love_edit_profile', 'Edit Profil')}
            </button>
            {coupleActive && (
              <button
                type="button"
                onClick={() => {
                  if (!window.confirm(t('couple_end_confirm', 'Akhiri hubungan couple?'))) return;
                  studio.endCouple().then((r) => showToast(r.ok ? 'success' : 'info', r.result?.msg || r.result?.code || 'couple', ''));
                }}
                className={btnDanger}
              >
                {t('couple_end', 'Akhiri Couple')}
              </button>
            )}
          </div>
        </div>
      </div>

      {/* Tab bar (parity QTabWidget LovePage: 6 tab) */}
      <div className="flex flex-wrap gap-1.5 p-1.5 bg-slate-900/70 border border-slate-800 rounded-2xl">
        {TABS.map((tb) => (
          <button
            key={tb.id}
            onClick={() => setTab(tb.id)}
            className={`flex items-center gap-1.5 px-3 py-2 rounded-xl text-xs font-bold transition-colors ${
              tab === tb.id ? 'bg-rose-600 text-white shadow-lg' : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800'
            }`}
          >
            {tb.icon}
            {t(`love_tab_${tb.id}`, tb.id)}
          </button>
        ))}
      </div>

      {/* ═══ TAB: OVERVIEW ═══ */}
      {tab === 'overview' && (
        <div className="space-y-4">
          <div className="flex flex-wrap gap-3">
            {miniStat(t('love_days_together', 'Hari Bersama'), daysTogether)}
            {miniStat(t('love_next_moment', 'Momen Berikutnya'), nextEvent ? `${nextEvent.title} · ${nextEvent.date}` : t('love_no_upcoming', '—'))}
            {miniStat(t('love_connection', 'Koneksi'), `${loveSpace.connectionScore}%`)}
          </div>

          <div className="p-5 bg-slate-900/70 border border-slate-800 rounded-2xl space-y-3">
            <h3 className="font-bold text-sm text-slate-200">{t('love_daily_checkin', 'Check-in Harian')}</h3>
            <p className="text-xs text-slate-400">
              {todayCheckin
                ? trv('love_checkin_today_done', { my: todayCheckin.myMood, partner: todayCheckin.partnerMood, score: todayCheckin.connectionScore, note: todayCheckin.note || '—' }, '✅ Sudah check-in hari ini')
                : t('love_checkin_today_none', 'Belum check-in hari ini.')}
            </p>
            <div className="flex flex-wrap gap-3 items-end text-xs">
              <label className="space-y-1">
                <span className="block text-slate-400">{t('love_my_mood', 'Mood-ku')}</span>
                <select value={myMood} onChange={(e) => setMyMood(Number(e.target.value))} className={inputCls}>
                  {MOODS.map(([v, ic]) => (<option key={v} value={v}>{ic} {v}/5</option>))}
                </select>
              </label>
              <label className="space-y-1">
                <span className="block text-slate-400">{t('love_partner_mood', 'Mood Pasangan')}</span>
                <select value={partnerMood} onChange={(e) => setPartnerMood(Number(e.target.value))} className={inputCls}>
                  {MOODS.map(([v, ic]) => (<option key={v} value={v}>{ic} {v}/5</option>))}
                </select>
              </label>
              <label className="space-y-1">
                <span className="block text-slate-400">{t('love_connection_score', 'Skor Koneksi')}</span>
                <input type="number" min={1} max={5} value={connScore} onChange={(e) => setConnScore(Math.max(1, Math.min(5, Number(e.target.value) || 1)))} className={`${inputCls} w-20`} />
              </label>
            </div>
            <input value={checkNote} onChange={(e) => setCheckNote(e.target.value)} className={inputCls} placeholder={t('love_checkin_note_ph', 'Catatan singkat hari ini…')} />
            <button
              type="button"
              onClick={() => {
                loveCheckin({ myMood, partnerMood, connectionScore: connScore, note: checkNote });
                showToast('success', t('berhasil_title', 'Berhasil'), t('love_checkin_saved', 'Check-in tersimpan.'));
                setCheckNote('');
              }}
              className={btnRose}
            >
              {t('love_save_checkin', 'Simpan Check-in')}
            </button>
          </div>

          <div className="p-5 bg-slate-900/70 border border-slate-800 rounded-2xl space-y-2">
            <h3 className="font-bold text-sm text-slate-200">{t('love_checkin_history', 'Riwayat Check-in')}</h3>
            <div className="max-h-52 overflow-y-auto space-y-1">
              {(loveSpace.checkins || []).map((c) => (
                <div key={c.id} className="text-xs text-slate-300 py-1 border-b border-slate-800/50">
                  {trv('love_checkin_row', { date: c.date, my: c.myMood, partner: c.partnerMood, score: c.connectionScore, note: c.note || '—' }, `${c.date} · 🙂 ${c.myMood} · 💞 ${c.partnerMood}`)}
                </div>
              ))}
              {!(loveSpace.checkins || []).length && <p className="text-xs text-slate-500">—</p>}
            </div>
          </div>

          <div className="p-5 bg-slate-900/70 border border-slate-800 rounded-2xl space-y-2">
            <h3 className="font-bold text-sm text-slate-200">{t('love_upcoming', 'Akan Datang')}</h3>
            {futureEvents.length ? futureEvents.slice(0, 5).map((ev) => (
              <div key={ev.id} className="text-xs text-slate-300 py-1 border-b border-slate-800/50">{ev.date} · {ev.title}</div>
            )) : <p className="text-xs text-slate-500">{t('love_no_upcoming', 'Belum ada momen terjadwal.')}</p>}
          </div>
        </div>
      )}

      {/* ═══ TAB: CONNECTION ═══ */}
      {tab === 'connection' && (
        <div className="space-y-4">
          <div className="p-5 bg-slate-900/70 border border-slate-800 rounded-2xl space-y-3">
            <div className="flex flex-wrap items-center gap-2">
              <h3 className="font-bold text-sm text-slate-200 flex-1">{t('love_connection_prompts', 'Prompt Koneksi')}</h3>
              <select value={promptCategory} onChange={(e) => setPromptCategory(e.target.value)} className={`${inputCls} w-auto`}>
                {(['all', 'connection', 'appreciation', 'support', 'future', 'fun', 'favorites'] as const).map((c) => (
                  <option key={c} value={c}>{t(`love_prompt_${c}`, c)}</option>
                ))}
              </select>
              <button type="button" onClick={nextPrompt} className={btnGhost}><Shuffle className="w-3.5 h-3.5 inline mr-1" />{t('love_prompt_shuffle', 'Acak')}</button>
              <button
                type="button"
                disabled={!currentPrompt}
                onClick={() => currentPrompt && lovePromptFavorite(currentPrompt[0])}
                className={btnGhost}
              >
                <Star className={`w-3.5 h-3.5 inline mr-1 ${currentPrompt && (loveSpace.promptFavorites || []).includes(currentPrompt[0]) ? 'fill-amber-400 text-amber-400' : ''}`} />
                {currentPrompt && (loveSpace.promptFavorites || []).includes(currentPrompt[0])
                  ? t('love_prompt_unfavorite', 'Batal Favorit')
                  : t('love_prompt_favorite', 'Favorit')}
              </button>
            </div>
            <p className="text-center text-sm text-rose-200 font-semibold py-4">
              {currentPrompt ? t(currentPrompt[2], currentPrompt[0]) : t('love_prompt_no_favorites', 'Tidak ada prompt pada kategori ini.')}
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
                // Parity _save_prompt_response: simpan answer + partner_answer sekaligus.
                studio.lovePrompt({
                  promptKey: currentPrompt[0],
                  category: currentPrompt[1],
                  prompt: t(currentPrompt[2], currentPrompt[0]),
                  answer: myAnswer,
                  partnerAnswer,
                }).then((res: any) => {
                  if (res?.result?.ok === false) showToast('info', t('msg_error', 'Error'), res.result?.msg || '');
                  refreshLoveSpace();
                });
                setMyAnswer(''); setPartnerAnswer('');
              }}
              className={btnRose}
            >
              {t('love_prompt_save', 'Simpan Jawaban')}
            </button>
          </div>

          <div className="p-5 bg-slate-900/70 border border-slate-800 rounded-2xl space-y-2">
            <h3 className="font-bold text-sm text-slate-200">{t('love_prompt_history', 'Riwayat Jawaban')}</h3>
            <div className="max-h-48 overflow-y-auto space-y-1">
              {(loveSpace.promptResponses || []).map((p) => (
                <div key={p.id} className="flex items-start gap-2 text-xs text-slate-300 py-1 border-b border-slate-800/50">
                  <div className="flex-1">
                    <span className="text-slate-500">{p.createdAt ? p.createdAt.split('T')[0] : p.promptKey}</span> · {p.prompt}
                    {p.answer && <div className="text-slate-400">🙋 {p.answer}</div>}
                    {p.partnerAnswer && <div className="text-slate-400">💞 {p.partnerAnswer}</div>}
                  </div>
                  <button type="button" onClick={() => deleteLovePrompt(p.id)} className="p-1 text-slate-500 hover:text-rose-400" title={t('love_delete_selected', 'Hapus yang Dipilih')}><Trash2 className="w-3.5 h-3.5" /></button>
                </div>
              ))}
              {!(loveSpace.promptResponses || []).length && <p className="text-xs text-slate-500">{t('love_prompt_empty_history', 'Belum ada jawaban tersimpan.')}</p>}
            </div>
          </div>

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
                loveWeekly({ weekStart: weekDate, appreciation: revAppr, wins: revWins, support: revSupport, intention: revIntent });
                setRevAppr(''); setRevWins(''); setRevSupport(''); setRevIntent('');
              }}
              className={btnRose}
            >
              {t('love_review_save', 'Simpan Review')}
            </button>
            <div className="max-h-40 overflow-y-auto space-y-1">
              {(loveSpace.weeklyReviews || []).map((w) => (
                <div key={w.id} className="flex items-start gap-2 text-xs text-slate-300 py-1 border-b border-slate-800/50">
                  <div className="flex-1">
                    <span className="text-slate-500">{w.weekStart}</span> — {w.appreciation}
                    {w.wins && <div className="text-slate-400">🏆 {w.wins}</div>}
                    {w.support && <div className="text-slate-400">🤝 {w.support}</div>}
                    {w.intention && <div className="text-slate-400">🎯 {w.intention}</div>}
                  </div>
                  <button type="button" onClick={() => deleteLoveWeekly(w.id)} className="p-1 text-slate-500 hover:text-rose-400" title={t('love_delete_selected', 'Hapus')}><Trash2 className="w-3.5 h-3.5" /></button>
                </div>
              ))}
              {!(loveSpace.weeklyReviews || []).length && <p className="text-xs text-slate-500">{t('love_review_empty_history', 'Belum ada review.')}</p>}
            </div>
          </div>
        </div>
      )}

      {/* ═══ TAB: CYCLE ═══ */}
      {tab === 'cycle' && (
        <div className="space-y-4">
          <div className="p-5 bg-slate-900/70 border border-rose-500/20 rounded-2xl space-y-2">
            <h3 className="font-bold text-sm text-slate-200">{t('love_cycle_prediction', 'Prediksi Siklus')}</h3>
            {loveSpace.cyclePrediction ? (
              <>
                <p className="text-sm text-rose-300 font-bold">
                  {trv('love_cycle_range', { start: loveSpace.cyclePrediction.predictedStart, end: loveSpace.cyclePrediction.predictedEnd }, `Perkiraan mulai ${loveSpace.cyclePrediction.predictedStart} hingga ${loveSpace.cyclePrediction.predictedEnd}`)}
                </p>
                <p className="text-xs text-slate-400">{trv('love_cycle_days_until', { days: loveSpace.cyclePrediction.daysUntil }, `${loveSpace.cyclePrediction.daysUntil} hari dari hari ini`)}</p>
              </>
            ) : (
              <p className="text-sm text-slate-300 font-bold">{t('love_cycle_no_data', 'Belum cukup data untuk prediksi.')}</p>
            )}
          </div>

          <div className="p-5 bg-slate-900/70 border border-slate-800 rounded-2xl space-y-3">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              <label className="space-y-1 text-xs">
                <span className="block text-slate-400">{t('love_cycle_for', 'Siklus untuk')}</span>
                <select value={cycPerson} onChange={(e) => setCycPerson(e.target.value as 'self' | 'partner')} className={inputCls}>
                  <option value="partner">{loveSpace.partnerName || 'Partner'}</option>
                  <option value="self">{t('love_myself', 'Diriku')}</option>
                </select>
              </label>
              <label className="space-y-1 text-xs">
                <span className="block text-slate-400">{t('love_last_period', 'Periode terakhir')}</span>
                <input type="date" value={cycStart} onChange={(e) => setCycStart(e.target.value)} className={inputCls} />
              </label>
              <label className="space-y-1 text-xs">
                <span className="block text-slate-400">{t('love_cycle_length', 'Panjang siklus')}</span>
                <input type="number" min={20} max={45} value={cycLen} onChange={(e) => setCycLen(Math.max(20, Math.min(45, Number(e.target.value) || 28)))} className={inputCls} />
              </label>
              <label className="space-y-1 text-xs">
                <span className="block text-slate-400">{t('love_period_length', 'Lama periode')}</span>
                <input type="number" min={2} max={10} value={perLen} onChange={(e) => setPerLen(Math.max(2, Math.min(10, Number(e.target.value) || 5)))} className={inputCls} />
              </label>
            </div>
            <div className="flex gap-2">
              <button
                type="button"
                onClick={() => loveCycle({ settings: { trackedPerson: cycPerson, lastPeriodStart: cycStart, cycleLength: cycLen, periodLength: perLen } })}
                className={btnRose}
              >
                {t('love_save_cycle', 'Simpan Pengaturan Siklus')}
              </button>
              <button
                type="button"
                onClick={() => loveCycle({ startDate: today, notes: '' })}
                className={btnGhost}
              >
                {t('love_log_cycle', 'Catat Periode Hari Ini')}
              </button>
            </div>
          </div>

          <div className="p-5 bg-slate-900/70 border border-slate-800 rounded-2xl space-y-2">
            <h3 className="font-bold text-sm text-slate-200">{t('love_cycle_history', 'Riwayat Siklus')}</h3>
            <div className="max-h-44 overflow-y-auto space-y-1">
              {(loveSpace.cycles || []).map((c) => (
                <div key={c.id} className="flex items-center gap-2 text-xs text-slate-300 py-1 border-b border-slate-800/50">
                  <span className="flex-1">
                    {t('love_period_start', 'Mulai')} {c.startDate}{c.endDate ? ` → ${t('love_period_end', 'Selesai')} ${c.endDate}` : ''}{c.notes ? ` · ${c.notes}` : ''}
                  </span>
                  <button type="button" onClick={() => deleteLoveCycle(c.id)} className="p-1 text-slate-500 hover:text-rose-400" title={t('love_delete_selected', 'Hapus')}><Trash2 className="w-3.5 h-3.5" /></button>
                </div>
              ))}
              {!(loveSpace.cycles || []).length && <p className="text-xs text-slate-500">—</p>}
            </div>
          </div>
          <p className="text-[10px] text-slate-500">{t('love_cycle_disclaimer', 'Prediksi hanya perkiraan — bukan pengganti saran medis.')}</p>
        </div>
      )}

      {/* ═══ TAB: MEMORIES ═══ */}
      {tab === 'memories' && (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="font-bold text-sm text-slate-200">{t('love_memories_title', 'Kenangan Berdua')}</h3>
            <button type="button" onClick={() => setShowAddMemModal(true)} className={btnRose}><Plus className="w-3.5 h-3.5 inline mr-1" />{t('love_add_memory', 'Tambah Kenangan')}</button>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            {(loveSpace.memories || []).map((m) => (
              <div key={m.id} className="p-4 bg-slate-900/70 border border-slate-800 rounded-2xl space-y-1">
                <div className="flex items-start justify-between gap-2">
                  <div>
                    <div className="font-bold text-sm text-slate-200">{m.emoji || '💖'} {m.title}</div>
                    <div className="text-[11px] text-slate-500">{m.date}</div>
                  </div>
                  <button type="button" onClick={() => deleteLoveMemory(m.id)} className="p-1 text-slate-500 hover:text-rose-400" title={t('love_delete_selected', 'Hapus')}><Trash2 className="w-3.5 h-3.5" /></button>
                </div>
                {m.description && <p className="text-xs text-slate-400">{m.description}</p>}
              </div>
            ))}
          </div>
          {!(loveSpace.memories || []).length && <p className="text-xs text-slate-500">—</p>}
        </div>
      )}

      {/* ═══ TAB: GALLERY (parity _build_gallery_tab) ═══ */}
      {tab === 'gallery' && (
        <div className="space-y-4">
          <div className="flex flex-wrap items-center gap-2">
            <h3 className="font-bold text-sm text-slate-200 flex-1">{t('love_gallery_title', 'Galeri')}</h3>
            <select value={gFilter} onChange={(e) => setGFilter(e.target.value as any)} className={`${inputCls} w-auto`}>
              <option value="all">{t('love_gallery_all', 'Semua')}</option>
              <option value="shared">{t('love_gallery_shared', 'Shared')}</option>
              <option value="private">{t('love_gallery_private', 'Private')}</option>
            </select>
            <button type="button" onClick={() => fileRef.current?.click()} className={btnRose}>
              <Camera className="w-3.5 h-3.5 inline mr-1" />{t('love_gallery_upload', 'Unggah Foto')}
            </button>
            <input ref={fileRef} type="file" accept="image/*" multiple title={t('love_gallery_pick_multi', 'Pilih Foto')} className="hidden" onChange={(e) => { onPickFiles(e.target.files); e.target.value = ''; }} />
            <button
              type="button"
              onClick={() => { setSelectMode((s) => !s); setSelected(new Set()); }}
              className={selectMode ? btnRose : btnGhost}
            >
              <Images className="w-3.5 h-3.5 inline mr-1" />{t('love_gallery_select', 'Pilih')}
            </button>
          </div>

          {/* Album bar (parity love_album_* toolbar) */}
          <div className="flex flex-wrap items-center gap-2 p-3 bg-slate-900/70 border border-slate-800 rounded-2xl">
            <span className="text-[11px] text-slate-400 font-bold">{t('love_album_title', 'Album')}</span>
            <select value={gAlbum} onChange={(e) => setGAlbum(e.target.value)} className={`${inputCls} w-auto`}>
              <option value="">{t('love_album_all', 'Semua Album')}</option>
              {albums.map((a) => (
                <option key={a.id} value={a.id}>
                  {a.name} · {a.scope === 'shared' ? t('love_album_shared', 'Shared') : t('love_album_personal', 'Personal')}
                </option>
              ))}
            </select>
            <button
              type="button"
              className={btnGhost}
              onClick={() => {
                const name = window.prompt(t('love_album_name_ph', 'Nama album…'))?.trim();
                if (!name) { showToast('info', t('msg_error', 'Error'), t('love_album_err_name', 'Nama album wajib diisi.')); return; }
                const scope = coupleActive && window.confirm(t('love_album_scope_label', 'Shared ke pasangan? OK=shared, Cancel=personal')) ? 'shared' : 'personal';
                createLoveAlbum(name, scope);
                showToast('success', t('berhasil_title', 'Berhasil'), trv('love_album_created', { name }, 'Album dibuat.'));
              }}
            >{t('love_album_new', 'Baru')}</button>
            <button
              type="button"
              disabled={!gAlbum}
              className={btnGhost}
              onClick={() => {
                const cur = albums.find((a) => a.id === gAlbum);
                const name = window.prompt(t('love_album_rename', 'Ubah nama album'), cur?.name || '')?.trim();
                if (!name || !cur) return;
                renameLoveAlbum(cur.id, name);
              }}
            >{t('love_album_rename', 'Ganti Nama')}</button>
            <button
              type="button"
              disabled={!gAlbum}
              className={btnDanger}
              onClick={() => {
                const cur = albums.find((a) => a.id === gAlbum);
                if (!cur) return;
                if (!window.confirm(trv('love_album_delete_confirm', { name: cur.name }, `Hapus album "${cur.name}"?`))) return;
                deleteLoveAlbum(cur.id);
                setGAlbum('');
              }}
            >{t('love_album_delete', 'Hapus Album')}</button>
          </div>

          {/* Bulk bar (parity select mode) */}
          {selectMode && (
            <div className="flex flex-wrap items-center gap-2 p-3 bg-rose-950/30 border border-rose-500/20 rounded-2xl">
              <span className="text-xs text-rose-300 font-bold flex-1">{trv('love_gallery_selected_count', { n: selected.size }, `${selected.size} foto dipilih`)}</span>
              <button
                type="button"
                className={btnGhost}
                onClick={() => {
                  const own = filteredPhotos.filter(myPhotosOwn).map((p) => String(p.id));
                  const allSel = own.length > 0 && own.every((id) => selected.has(id));
                  setSelected(allSel ? new Set() : new Set(own));
                }}
              >{selected.size && filteredPhotos.filter(myPhotosOwn).every((p) => selected.has(String(p.id))) ? t('love_gallery_deselect_all', 'Batal Pilih Semua') : t('love_gallery_select_all', 'Pilih Semua')}</button>
              <button type="button" className={btnDanger} onClick={bulkDelete}>{t('love_gallery_bulk_delete', 'Hapus Terpilih')}</button>
              <button type="button" className={btnGhost} onClick={() => bulkVis('private')}>{t('love_gallery_bulk_private', 'Jadikan Private')}</button>
              <button type="button" className={btnGhost} onClick={() => bulkVis('shared')} title={coupleActive ? '' : t('love_album_shared_need_couple', 'Butuh couple aktif')}>{t('love_gallery_bulk_shared', 'Jadikan Shared')}</button>
            </div>
          )}

          <div className="flex items-center justify-between text-[11px] text-slate-500">
            <span>{trv('love_gallery_count', { n: filteredPhotos.length, total: (loveSpace.photos || []).length }, `${filteredPhotos.length} foto`)}</span>
            <span className="italic">{t('love_gallery_privacy_hint', 'Foto private hanya kamu yang lihat.')}</span>
          </div>

          {filteredPhotos.length ? (
            <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-3">
              {filteredPhotos.map((ph) => {
                const pid = String(ph.id);
                const own = myPhotosOwn(ph);
                const inAlbum = albumOf(pid);
                return (
                  <div key={pid} className="space-y-1">
                    <PhotoThumb
                      photo={ph}
                      selectMode={selectMode}
                      selected={selected.has(pid)}
                      onClick={() => {
                        if (selectMode) {
                          if (!own) return;
                          setSelected((s) => { const n = new Set(s); n.has(pid) ? n.delete(pid) : n.add(pid); return n; });
                        } else setViewer(ph);
                      }}
                    />
                    <div className="flex items-center justify-between px-0.5">
                      <span className="text-[10px] text-slate-500 truncate">
                        {trv('love_gallery_meta', { date: ph.photoDate || (ph.createdAt || '').split('T')[0] || '—', uploader: ph.uploaderName || '—' }, ph.photoDate || '')}
                        {inAlbum ? ` · 📁 ${inAlbum.name}` : ''}
                      </span>
                      <span className={`text-[10px] font-bold ${ph.visibility === 'shared' ? 'text-rose-400' : 'text-slate-500'}`}>
                        {ph.visibility === 'shared' ? '💞' : '🔒'}
                      </span>
                    </div>
                    {own && !selectMode && (
                      <div className="flex items-center gap-1 px-0.5">
                        <button
                          type="button"
                          className="p-1 rounded bg-slate-800 hover:bg-slate-700 text-slate-300"
                          title={t('love_gallery_toggle_tip', 'Ubah visibilitas')}
                          onClick={() => updateLovePhotoMeta(pid, { caption: ph.caption, photoDate: ph.photoDate, visibility: ph.visibility === 'shared' ? 'private' : 'shared' })}
                        >{ph.visibility === 'shared' ? <Eye className="w-3 h-3" /> : <EyeOff className="w-3 h-3" />}</button>
                        <button type="button" className="p-1 rounded bg-slate-800 hover:bg-slate-700 text-slate-300" title={t('love_gallery_edit', 'Edit')} onClick={() => setViewer(ph)}><Pencil className="w-3 h-3" /></button>
                        <button
                          type="button"
                          className="p-1 rounded bg-slate-800 hover:bg-slate-700 text-slate-300"
                          title={t('love_album_title', 'Album')}
                          onClick={() => { setAlbumFor(ph); setAlbumTarget(albumOf(pid)?.id || albums[0]?.id || ''); }}
                        ><FolderOpen className="w-3 h-3" /></button>
                        <button
                          type="button"
                          className="p-1 rounded bg-slate-800 hover:bg-rose-900 text-rose-300"
                          title={t('love_delete', 'Hapus')}
                          onClick={() => { if (window.confirm(t('love_gallery_delete_confirm', 'Hapus foto ini?'))) deleteLovePhoto(pid); }}
                        ><Trash2 className="w-3 h-3" /></button>
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          ) : (
            <div className="p-8 text-center text-xs text-slate-500 bg-slate-900/50 border border-slate-800 rounded-2xl">{t('love_gallery_empty', 'Belum ada foto. Unggah momen pertama kalian!')}</div>
          )}
        </div>
      )}

      {/* ═══ TAB: PLANS (events + bucket list) ═══ */}
      {tab === 'plans' && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          <div className="p-5 bg-slate-900/70 border border-slate-800 rounded-2xl space-y-3">
            <div className="flex items-center justify-between">
              <h3 className="font-bold text-sm text-slate-200">{t('love_events', 'Acara Berdua')}</h3>
            </div>
            <div className="flex flex-wrap gap-2">
              <input value={evTitle} onChange={(e) => setEvTitle(e.target.value)} className={`${inputCls} flex-1 min-w-[120px]`} placeholder={t('love_title_label', 'Judul')} />
              <input type="date" value={evDate} onChange={(e) => setEvDate(e.target.value)} className={`${inputCls} w-auto`} />
              <select value={evCategory} onChange={(e) => setEvCategory(e.target.value)} className={`${inputCls} w-auto`}>
                {(['date', 'gift', 'milestone', 'dream'] as const).map((c) => (<option key={c} value={c}>{t(`love_category_${c}`, c)}</option>))}
              </select>
              <button
                type="button"
                className={btnRose}
                onClick={() => {
                  if (!evTitle.trim()) return;
                  loveEvent({ title: evTitle, date: evDate, category: evCategory, notes: evNotes });
                  setEvTitle(''); setEvNotes('');
                }}
              >{t('love_add', 'Tambah')}</button>
            </div>
            <div className="max-h-64 overflow-y-auto space-y-1">
              {[...(loveSpace.events || [])].sort((a, b) => a.date.localeCompare(b.date)).map((ev) => (
                <div key={ev.id} className="flex items-center gap-2 text-xs text-slate-300 py-1 border-b border-slate-800/50">
                  <span className="flex-1"><span className="text-slate-500">{ev.date}</span> · {ev.title} <span className="text-slate-500">({t(`love_category_${ev.category || 'date'}`, ev.category || 'date')})</span>{ev.notes ? ` · ${ev.notes}` : ''}</span>
                  <button type="button" onClick={() => deleteLoveEvent(ev.id)} className="p-1 text-slate-500 hover:text-rose-400" title={t('love_delete_selected', 'Hapus')}><Trash2 className="w-3.5 h-3.5" /></button>
                </div>
              ))}
              {!(loveSpace.events || []).length && <p className="text-xs text-slate-500">—</p>}
            </div>
          </div>

          <div className="p-5 bg-slate-900/70 border border-slate-800 rounded-2xl space-y-3">
            <div className="flex items-center justify-between">
              <h3 className="font-bold text-sm text-slate-200">{t('love_bucket_list', 'Bucket List')}</h3>
            </div>
            <div className="flex gap-2">
              <input value={bucketTitle} onChange={(e) => setBucketTitle(e.target.value)} className={`${inputCls} flex-1`} placeholder={t('love_title_label', 'Judul')} />
              <button
                type="button"
                className={btnRose}
                onClick={() => {
                  if (!bucketTitle.trim()) return;
                  studio.addBucket(bucketTitle).then(() => refreshLoveSpace());
                  setBucketTitle('');
                }}
              >{t('love_add', 'Tambah')}</button>
            </div>
            <div className="max-h-64 overflow-y-auto space-y-1">
              {(loveSpace.bucketList || []).map((b) => (
                <div key={b.id} className="flex items-center gap-2 text-xs text-slate-300 py-1 border-b border-slate-800/50">
                  <input
                    type="checkbox"
                    checked={!!b.isCompleted}
                    onChange={() => toggleLoveBucketItem(b.id)}
                    className="accent-rose-500"
                  />
                  <span className={`flex-1 ${b.isCompleted ? 'line-through text-slate-500' : ''}`}>
                    {b.title}{b.completedDate ? ` · ✅ ${b.completedDate.split(' ')[0]}` : ''}
                  </span>
                  <button type="button" onClick={() => deleteLoveBucket(b.id)} className="p-1 text-slate-500 hover:text-rose-400" title={t('love_delete_selected', 'Hapus')}><Trash2 className="w-3.5 h-3.5" /></button>
                </div>
              ))}
              {!(loveSpace.bucketList || []).length && <p className="text-xs text-slate-500">—</p>}
            </div>
          </div>
        </div>
      )}

      {/* ── Add Memory Modal ── */}
      {showAddMemModal && (
        <Modal title={t('love_add_memory', 'Tambah Kenangan')} onClose={() => setShowAddMemModal(false)}>
          <input value={newMemTitle} onChange={(e) => setNewMemTitle(e.target.value)} className={inputCls} placeholder={t('love_title_label', 'Judul kenangan')} />
          <input type="date" value={newMemDate} onChange={(e) => setNewMemDate(e.target.value)} className={inputCls} />
          <textarea value={newMemDesc} onChange={(e) => setNewMemDesc(e.target.value)} rows={3} className={inputCls} placeholder="…" />
          <div className="flex justify-end gap-2">
            <button type="button" className={btnGhost} onClick={() => setShowAddMemModal(false)}>{t('msg_cancel', 'Batal')}</button>
            <button
              type="button"
              className={btnRose}
              onClick={() => {
                if (!newMemTitle.trim()) { showToast('info', t('msg_error', 'Error'), t('love_title_label', 'Judul')); return; }
                addLoveMemory(newMemTitle, newMemDate, newMemDesc, '💖');
                setShowAddMemModal(false); setNewMemTitle(''); setNewMemDesc('');
              }}
            >{t('msg_ok', 'OK')}</button>
          </div>
        </Modal>
      )}

      {/* ── Photo lightbox + edit (parity _GalleryViewerDialog/_GalleryEditDialog) ── */}
      {viewer && (
        <Modal title={viewer.caption || t('love_gallery_untitled', 'Foto')} onClose={() => setViewer(null)} wide>
          <div className="rounded-xl overflow-hidden bg-slate-950 max-h-[55vh] flex items-center justify-center">
            <ViewerImage photo={viewer} />
          </div>
          {myPhotosOwn(viewer) && (
            <div className="grid grid-cols-1 md:grid-cols-3 gap-2">
              <input
                defaultValue={viewer.caption || ''}
                onBlur={(e) => updateLovePhotoMeta(viewer.id, { caption: e.target.value, photoDate: viewer.photoDate, visibility: viewer.visibility })}
                className={inputCls}
                placeholder={t('love_gallery_meta', 'Keterangan')}
              />
              <input
                type="date"
                defaultValue={viewer.photoDate || ''}
                onBlur={(e) => updateLovePhotoMeta(viewer.id, { caption: viewer.caption, photoDate: e.target.value, visibility: viewer.visibility })}
                className={inputCls}
              />
              <select
                value={viewer.visibility}
                onChange={(e) => updateLovePhotoMeta(viewer.id, { caption: viewer.caption, photoDate: viewer.photoDate, visibility: e.target.value })}
                className={inputCls}
              >
                <option value="private">🔒 {t('love_gallery_private', 'Private')}</option>
                <option value="shared">💞 {t('love_gallery_shared', 'Shared')}</option>
              </select>
            </div>
          )}
          <div className="flex justify-between items-center">
            <span className="text-[11px] text-slate-500">
              {trv('love_gallery_meta', { date: viewer.photoDate || '—', uploader: viewer.uploaderName || '—' }, '')}
            </span>
            {myPhotosOwn(viewer) && (
              <button
                type="button"
                className={btnDanger}
                onClick={() => {
                  if (!window.confirm(t('love_gallery_delete_confirm', 'Hapus foto ini?'))) return;
                  deleteLovePhoto(viewer.id);
                  setViewer(null);
                }}
              >{t('love_delete', 'Hapus')}</button>
            )}
          </div>
        </Modal>
      )}

      {/* ── Album assign modal (parity _open_photo_menu/_photo_to_album) ── */}
      {albumFor && (
        <Modal title={t('love_album_choose', 'Pilih Album')} onClose={() => setAlbumFor(null)}>
          {albums.length ? (
            <>
              <select value={albumTarget} onChange={(e) => setAlbumTarget(e.target.value)} className={inputCls}>
                {albums.map((a) => (
                  <option key={a.id} value={a.id}>{a.name} · {a.scope === 'shared' ? t('love_album_shared', 'Shared') : t('love_album_personal', 'Personal')}</option>
                ))}
              </select>
              <div className="flex gap-2 flex-wrap">
                <button
                  type="button"
                  className={btnRose}
                  onClick={() => {
                    if (albumTarget) loveAlbumAddPhoto(albumTarget, String(albumFor.id));
                    showToast('success', t('berhasil_title', 'Berhasil'), t('love_album_copied', 'Foto disalin ke album.'));
                    setAlbumFor(null);
                  }}
                >{t('love_album_copy_to', 'Salin ke Album')}</button>
                <button
                  type="button"
                  className={btnGhost}
                  onClick={() => {
                    if (albumTarget) loveAlbumMovePhoto(albumTarget, String(albumFor.id), albumOf(String(albumFor.id))?.id || null);
                    showToast('success', t('berhasil_title', 'Berhasil'), t('love_album_moved', 'Foto dipindah ke album.'));
                    setAlbumFor(null);
                  }}
                >{t('love_album_move_to', 'Pindah ke Album')}</button>
                {albumOf(String(albumFor.id)) && (
                  <button
                    type="button"
                    className={btnDanger}
                    onClick={() => {
                      const cur = albumOf(String(albumFor.id));
                      if (cur) loveAlbumRemovePhoto(cur.id, String(albumFor.id));
                      showToast('success', t('berhasil_title', 'Berhasil'), t('love_album_removed', 'Foto dikeluarkan dari album.'));
                      setAlbumFor(null);
                    }}
                  >{t('love_album_remove', 'Keluarkan dari Album')}</button>
                )}
              </div>
            </>
          ) : (
            <p className="text-xs text-slate-500">{t('love_album_no_albums', 'Belum ada album.')}</p>
          )}
        </Modal>
      )}

      {/* ── Upload metadata dialog per file (parity _GalleryPhotoDialog) ── */}
      {uploadIdx >= 0 && uploadQueue[uploadIdx] && (
        <Modal title={`${t('love_gallery_upload', 'Unggah Foto')} (${uploadIdx + 1}/${uploadQueue.length})`} onClose={() => { setUploadIdx(-1); setUploadQueue([]); }}>
          <p className="text-xs text-slate-400 truncate">{uploadQueue[uploadIdx].name} · {(uploadQueue[uploadIdx].size / 1024).toFixed(0)} KB</p>
          {uploadQueue[uploadIdx].size > UPLOAD_MAX && (
            <p className="text-xs text-rose-400">{t('web_upload_too_large', 'File terlalu besar (maks 8MB).')}</p>
          )}
          <input value={upCaption} onChange={(e) => setUpCaption(e.target.value)} className={inputCls} placeholder={t('love_gallery_meta', 'Keterangan foto (opsional)')} />
          <label className="block text-[11px] text-slate-400">{t('love_date_label', 'Tanggal')}</label>
          <input type="date" value={upDate} onChange={(e) => setUpDate(e.target.value)} className={inputCls} />
          <label className="block text-[11px] text-slate-400">{t('love_album_scope', 'Visibilitas')}</label>
          <select value={upVis} onChange={(e) => setUpVis(e.target.value as 'private' | 'shared')} className={inputCls}>
            <option value="private">🔒 {t('love_gallery_private_hint', 'Private — hanya kamu')}</option>
            <option value="shared" disabled={!coupleActive}>
              💞 {coupleActive ? t('love_gallery_shared_hint', 'Shared — terlihat pasangan') : t('love_album_shared_need_couple', 'Shared (butuh couple aktif)')}
            </option>
          </select>
          <div className="flex justify-end gap-2">
            <button type="button" className={btnGhost} onClick={() => processUpload(false)}>{t('msg_cancel', 'Lewati')}</button>
            <button type="button" className={btnRose} onClick={() => processUpload(true)}>{t('love_gallery_upload', 'Unggah')}</button>
          </div>
        </Modal>
      )}

      {/* ── Edit profile modal (parity _edit_profile) ── */}
      {showProfile && (
        <Modal title={t('love_edit_profile', 'Edit Profil')} onClose={() => setShowProfile(false)}>
          <label className="block text-[11px] text-slate-400">{t('love_partner_not_set', 'Nama pasangan')}</label>
          <input value={profPartner} onChange={(e) => setProfPartner(e.target.value)} className={inputCls} />
          <label className="block text-[11px] text-slate-400">{t('love_myself', 'Namaku')}</label>
          <input value={profMy} onChange={(e) => setProfMy(e.target.value)} className={inputCls} />
          <label className="block text-[11px] text-slate-400">{t('love_date_label', 'Tanggal jadian')}</label>
          <input type="date" value={profStart} onChange={(e) => setProfStart(e.target.value)} className={inputCls} />
          <div className="flex justify-end gap-2">
            <button type="button" className={btnGhost} onClick={() => setShowProfile(false)}>{t('msg_cancel', 'Batal')}</button>
            <button
              type="button"
              className={btnRose}
              onClick={() => {
                updateLoveSpace({ partnerName: profPartner, startDate: profStart, anniversaryDate: profStart, myName: profMy } as any);
                setShowProfile(false);
              }}
            >{t('msg_ok', 'OK')}</button>
          </div>
        </Modal>
      )}
    </div>
  );
};

export default LoveSpaceView;
