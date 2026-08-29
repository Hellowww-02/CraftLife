import React, { useState, useEffect } from 'react';
import { useGame } from '../../context/GameContext';
import { t } from '../../i18n';
import { studio } from '../../api/studio';
import { bridge } from '../../bridge';
import { X } from 'lucide-react';
import {
  Heart,
  Calendar,
  Sparkles,
  Plus,
  CheckCircle2,
  Circle,
  MessageSquareHeart,
  Camera,
  Flame,
  Send,
  Star,
  Award,
} from 'lucide-react';

/** Thumbnail for a Love Space photo; fetches the authed image URL once. */
const PhotoThumb: React.FC<{ photo: any; onClick: () => void }> = ({ photo, onClick }) => {
  const [url, setUrl] = useState('');
  useEffect(() => {
    let alive = true;
    studio.lovePhotoImage(photo.id).then((u) => { if (alive) setUrl(u); }).catch(() => setUrl(''));
    return () => { alive = false; };
  }, [photo.id]);
  return (
    <div
      onClick={onClick}
      className="cursor-pointer group relative overflow-hidden rounded-lg border border-slate-800 aspect-video bg-slate-950 hover:border-rose-500/40 transition-colors"
    >
      {url ? (
        <img src={url} alt="" className="w-full h-full object-cover group-hover:scale-105 transition-transform" />
      ) : (
        <div className="w-full h-full flex items-center justify-center text-slate-600 text-3xl">🖼️</div>
      )}
      {photo.caption && (
        <span className="absolute bottom-0 inset-x-0 px-2 py-1 text-[10px] text-white bg-black/60 truncate">{photo.caption}</span>
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

export const LoveSpaceView: React.FC = () => {
  const {
    loveSpace,
    updateLoveSpace,
    addLoveMemory,
    toggleLoveBucketItem,
    answerLovePrompt,
    loveCheckin,
    lovePhoto,
    updateLovePhotoMeta,
    loveEvent,
    loveWeekly,
    loveCycle,
    lang,
    showToast,
  } = useGame();
  const [evTitle, setEvTitle] = useState('');
  const [evDate, setEvDate] = useState(new Date().toISOString().split('T')[0]);
  const [weekAppr, setWeekAppr] = useState('');
  const [weekWins, setWeekWins] = useState('');
  const [cycleStart, setCycleStart] = useState(new Date().toISOString().split('T')[0]);
  const [myMood, setMyMood] = useState(3);
  const [partnerMood, setPartnerMood] = useState(3);
  const [connScore, setConnScore] = useState(3);
  const [checkNote, setCheckNote] = useState('');

  const [promptAnswerInput, setPromptAnswerInput] = useState('');
  const [showAddMemModal, setShowAddMemModal] = useState(false);
  const [newMemTitle, setNewMemTitle] = useState('');
  const [newMemDate, setNewMemDate] = useState(new Date().toISOString().split('T')[0]);
  const [newMemDesc, setNewMemDesc] = useState('');
  const [newMemEmoji, setNewMemEmoji] = useState('💖');

  const [showAddBucketModal, setShowAddBucketModal] = useState(false);
  const [newBucketTitle, setNewBucketTitle] = useState('');
  const [newBucketYear, setNewBucketYear] = useState<number>(2026);

  // Lightbox photo viewer (parity with PyQt _GalleryViewerDialog).
  const [viewer, setViewer] = useState<any>(null);

  // Calculate Days Together
  const calculateDaysTogether = () => {
    try {
      const start = new Date(loveSpace.anniversaryDate);
      const now = new Date();
      const diffTime = Math.abs(now.getTime() - start.getTime());
      return Math.ceil(diffTime / (1000 * 60 * 60 * 24));
    } catch {
      return 1;
    }
  };

  const daysTogether = calculateDaysTogether();

  const currentPrompt = loveSpace.prompts[0] || {
    id: 'p_default',
    prompt: 'What made you smile thinking about each other today?',
    date: new Date().toISOString().split('T')[0],
  };

  return (
    <div id="love-space-view" className="space-y-6">
      {/* Header Hero Banner */}
      <div className="p-6 bg-gradient-to-r from-rose-950/60 via-slate-900 to-pink-950/40 border border-rose-500/20 rounded-2xl flex flex-col md:flex-row items-center justify-between gap-6 shadow-xl">
        <div className="flex items-center gap-4 text-center md:text-left">
          <div className="w-16 h-16 rounded-2xl bg-rose-500/10 border border-rose-500/30 flex items-center justify-center text-3xl shadow-lg shrink-0">
            {loveSpace.partnerAvatar || '🌸'}
          </div>
          <div>
            <div className="flex items-center gap-2 justify-center md:justify-start">
              <h1 className="text-xl font-bold text-slate-100">
                {lang === 'id' ? 'Ruang Cinta (Love Space)' : 'Love Space'}
              </h1>
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

        {/* Anniversary Counter Pill */}
        <div className="flex items-center gap-4 bg-slate-950/70 p-4 rounded-xl border border-slate-800">
          <div className="text-center">
            <span className="text-2xl font-extrabold text-rose-400 font-mono">{daysTogether}</span>
            <span className="block text-[10px] uppercase tracking-wider text-slate-500 font-bold">
              {lang === 'id' ? 'Hari Bersama' : 'Days Together'}
            </span>
          </div>
          <div className="h-8 w-px bg-slate-800" />
          <div className="text-center">
            <span className="text-2xl font-extrabold text-emerald-400 font-mono">{loveSpace.connectionScore}%</span>
            <span className="block text-[10px] uppercase tracking-wider text-slate-500 font-bold">
              {lang === 'id' ? 'Skor Harmoni' : 'Harmony Score'}
            </span>
          </div>
        </div>
      </div>

      <button
        type="button"
        onClick={() => {
          if (!window.confirm(lang === 'id' ? 'Akhiri hubungan couple lokal?' : 'End local couple relationship?')) return;
          studio.endCouple().then((r) => showToast(r.ok ? 'success' : 'info', r.result?.msg || r.result?.code || 'couple', ''));
        }}
        className="px-3 py-2 rounded-xl bg-rose-900/50 text-rose-200 text-xs font-bold"
      >
        {lang === 'id' ? 'Akhiri couple' : 'End couple'}
      </button>

      <div className="p-4 rounded-2xl bg-slate-900 border border-rose-500/20 space-y-2 text-xs">
        <h3 className="font-bold text-sm">{lang === 'id' ? 'Check-in harian (LovePage)' : 'Daily check-in (LovePage)'}</h3>
        <div className="flex flex-wrap gap-2 items-center">
          <label>me <input type="range" min={1} max={5} value={myMood} onChange={(e) => setMyMood(Number(e.target.value))} /></label>
          <label>partner <input type="range" min={1} max={5} value={partnerMood} onChange={(e) => setPartnerMood(Number(e.target.value))} /></label>
          <label>conn <input type="range" min={1} max={5} value={connScore} onChange={(e) => setConnScore(Number(e.target.value))} /></label>
        </div>
        <input value={checkNote} onChange={(e) => setCheckNote(e.target.value)} className="w-full px-2 py-1 rounded-lg bg-slate-950 border border-slate-800" placeholder="note" />
        <button
          type="button"
          onClick={() => loveCheckin({ myMood, partnerMood, connectionScore: connScore, note: checkNote })}
          className="px-3 py-1.5 rounded-lg bg-rose-600 text-white font-bold"
        >
          {lang === 'id' ? 'Simpan check-in' : 'Save check-in'}
        </button>
      </div>

      {/* Main Grid: Daily Prompt & Bucket List + Timeline Memories */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left 1 Column: Daily Connection Prompt & Love Note */}
        <div className="space-y-6">
          {/* Daily Connection Prompt Card */}
          <div className="p-5 bg-slate-900/70 border border-slate-800 rounded-2xl space-y-4 shadow-md">
            <div className="flex items-center gap-2 text-rose-400">
              <MessageSquareHeart className="w-4 h-4" />
              <h3 className="font-bold text-sm text-slate-200">
                {lang === 'id' ? 'Pertanyaan Harian Berdua' : 'Daily Connection Prompt'}
              </h3>
            </div>

            <p className="text-sm font-semibold text-slate-100 bg-rose-950/20 border border-rose-500/20 p-3.5 rounded-xl">
              "{currentPrompt.prompt}"
            </p>

            {/* Answer Display */}
            {currentPrompt.userAnswer && (
              <div className="p-3 bg-slate-950 rounded-xl border border-slate-800 text-xs space-y-1">
                <span className="font-bold text-rose-300">You:</span>
                <p className="text-slate-300 italic">{currentPrompt.userAnswer}</p>
              </div>
            )}
            {currentPrompt.partnerAnswer && (
              <div className="p-3 bg-slate-950 rounded-xl border border-slate-800 text-xs space-y-1">
                <span className="font-bold text-pink-300">{loveSpace.partnerName}:</span>
                <p className="text-slate-300 italic">{currentPrompt.partnerAnswer}</p>
              </div>
            )}

            {!currentPrompt.userAnswer && (
              <div className="space-y-2">
                <textarea
                  rows={3}
                  value={promptAnswerInput}
                  onChange={(e) => setPromptAnswerInput(e.target.value)}
                  placeholder={lang === 'id' ? 'Tulis jawabanmu untuk pasangan...' : 'Write your reflection for your partner...'}
                  className="w-full bg-slate-950 border border-slate-800 rounded-xl p-3 text-xs text-slate-100 placeholder-slate-500 focus:outline-none focus:border-rose-500"
                />
                <button
                  onClick={() => {
                    if (!promptAnswerInput.trim()) return;
                    answerLovePrompt(currentPrompt.id, promptAnswerInput.trim());
                    setPromptAnswerInput('');
                  }}
                  className="w-full py-2 bg-rose-600 hover:bg-rose-500 text-white font-semibold text-xs rounded-xl transition-colors flex items-center justify-center gap-1.5 shadow-md shadow-rose-600/20"
                >
                  <Send className="w-3.5 h-3.5" />
                  <span>{lang === 'id' ? 'Kirim Jawaban' : 'Submit Answer'}</span>
                </button>
              </div>
            )}
          </div>

          {/* Mutual Bucket List */}
          <div className="p-5 bg-slate-900/70 border border-slate-800 rounded-2xl space-y-4">
            <div className="flex items-center justify-between">
              <h3 className="font-bold text-sm text-slate-200 flex items-center gap-2">
                <Award className="w-4 h-4 text-amber-400" />
                <span>{lang === 'id' ? 'Bucket List Impian Berdua' : 'Shared Bucket List'}</span>
              </h3>
              <button
                onClick={() => setShowAddBucketModal(true)}
                className="text-xs text-rose-400 hover:text-rose-300 flex items-center gap-1 font-semibold"
              >
                <Plus className="w-3.5 h-3.5" />
                <span>{lang === 'id' ? 'Tambah' : 'Add'}</span>
              </button>
            </div>

            <div className="space-y-2 max-h-[300px] overflow-y-auto pr-1">
              {loveSpace.bucketList.map((item) => (
                <div
                  key={item.id}
                  onClick={() => toggleLoveBucketItem(item.id)}
                  className={`p-3 rounded-xl border flex items-center justify-between gap-3 cursor-pointer transition-all ${
                    item.isCompleted
                      ? 'bg-rose-950/20 border-rose-500/30 text-slate-400'
                      : 'bg-slate-950/60 border-slate-800 text-slate-200 hover:border-slate-700'
                  }`}
                >
                  <div className="flex items-center gap-2.5">
                    {item.isCompleted ? (
                      <CheckCircle2 className="w-4 h-4 text-rose-400 shrink-0" />
                    ) : (
                      <Circle className="w-4 h-4 text-slate-600 shrink-0" />
                    )}
                    <span className={`text-xs font-medium ${item.isCompleted ? 'line-through text-slate-500' : ''}`}>
                      {item.title}
                    </span>
                  </div>
                  {item.targetYear && (
                    <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-slate-900 text-slate-400">
                      {item.targetYear}
                    </span>
                  )}
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Right 2 Columns: Memories Timeline & Gallery */}
        <div className="lg:col-span-2 space-y-6">
          <div className="p-5 bg-slate-900/70 border border-slate-800 rounded-2xl space-y-4">
            <div className="flex items-center justify-between">
              <h3 className="font-bold text-sm text-slate-200 flex items-center gap-2">
                <Camera className="w-4 h-4 text-rose-400" />
                <span>{lang === 'id' ? 'Timeline Kenangan Indah' : 'Cherished Memory Timeline'}</span>
              </h3>
              <button
                onClick={() => setShowAddMemModal(true)}
                className="flex items-center gap-1.5 px-3 py-1.5 bg-rose-600 hover:bg-rose-500 text-white font-semibold text-xs rounded-xl transition-colors shadow-md shadow-rose-600/20"
              >
                <Plus className="w-3.5 h-3.5" />
                <span>{lang === 'id' ? 'Tambah Kenangan' : 'Add Memory'}</span>
              </button>
            </div>

            {/* Timeline Cards */}
            <div className="space-y-4">
              {loveSpace.memories.map((mem) => (
                <div
                  key={mem.id}
                  className="p-4 bg-slate-950/70 border border-slate-800 rounded-xl flex items-start gap-4 hover:border-slate-700 transition-colors"
                >
                  <span className="text-3xl p-2 rounded-xl bg-slate-900 border border-slate-800 shrink-0">
                    {mem.emoji || '💖'}
                  </span>
                  <div className="space-y-1 flex-1">
                    <div className="flex items-center justify-between">
                      <h4 className="font-bold text-sm text-slate-100">{mem.title}</h4>
                      <span className="text-xs font-mono text-rose-400/80">{mem.date}</span>
                    </div>
                    <p className="text-xs text-slate-300 leading-relaxed">{mem.description}</p>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="p-4 bg-slate-900/70 border border-slate-800 rounded-2xl space-y-2 text-xs">
          <h3 className="font-bold text-sm text-slate-200">{lang === 'id' ? 'Acara / Date' : 'Events'}</h3>
          <input value={evTitle} onChange={(e) => setEvTitle(e.target.value)} placeholder="Title" className="w-full bg-slate-950 border border-slate-800 rounded-lg px-2 py-1" />
          <input type="date" value={evDate} onChange={(e) => setEvDate(e.target.value)} className="w-full bg-slate-950 border border-slate-800 rounded-lg px-2 py-1" />
          <button onClick={() => { if (!evTitle.trim()) return; loveEvent({ title: evTitle.trim(), date: evDate }); setEvTitle(''); }} className="w-full py-1.5 bg-rose-600 text-white rounded-lg font-semibold">{lang === 'id' ? 'Simpan acara' : 'Save event'}</button>
          <ul className="max-h-32 overflow-y-auto space-y-1 text-slate-400">
            {(loveSpace.events || []).map((e) => <li key={e.id}>{e.date} · {e.title}</li>)}
          </ul>
        </div>
        <div className="p-4 bg-slate-900/70 border border-slate-800 rounded-2xl space-y-2 text-xs">
          <h3 className="font-bold text-sm text-slate-200">{lang === 'id' ? 'Review mingguan' : 'Weekly review'}</h3>
          <textarea value={weekAppr} onChange={(e) => setWeekAppr(e.target.value)} placeholder="Appreciation" className="w-full bg-slate-950 border border-slate-800 rounded-lg p-2" rows={2} />
          <textarea value={weekWins} onChange={(e) => setWeekWins(e.target.value)} placeholder="Wins" className="w-full bg-slate-950 border border-slate-800 rounded-lg p-2" rows={2} />
          <button onClick={() => { loveWeekly({ weekStart: new Date().toISOString().slice(0, 10), appreciation: weekAppr, wins: weekWins }); setWeekAppr(''); setWeekWins(''); }} className="w-full py-1.5 bg-rose-600 text-white rounded-lg font-semibold">{lang === 'id' ? 'Simpan review' : 'Save review'}</button>
        </div>
        <div className="p-4 bg-slate-900/70 border border-slate-800 rounded-2xl space-y-2 text-xs">
          <h3 className="font-bold text-sm text-slate-200">{lang === 'id' ? 'Siklus' : 'Cycle log'}</h3>
          <input type="date" value={cycleStart} onChange={(e) => setCycleStart(e.target.value)} className="w-full bg-slate-950 border border-slate-800 rounded-lg px-2 py-1" />
          <button onClick={() => loveCycle({ startDate: cycleStart })} className="w-full py-1.5 bg-rose-600 text-white rounded-lg font-semibold">{lang === 'id' ? 'Log siklus' : 'Log cycle'}</button>
          <ul className="max-h-32 overflow-y-auto space-y-1 text-slate-400">
            {(loveSpace.cycles || []).map((c) => <li key={c.id}>{c.startDate}</li>)}
          </ul>
        </div>
      </div>

      {(loveSpace.photos || []).length > 0 && (
        <div className="p-5 bg-slate-900/70 border border-slate-800 rounded-2xl space-y-3">
          <h3 className="font-bold text-sm text-slate-200">{lang === 'id' ? 'Galeri (klik untuk lihat & edit)' : 'Gallery (click to view & edit)'}</h3>
          <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-3">
            {(loveSpace.photos || []).map((ph) => (
              <PhotoThumb key={ph.id} photo={ph} onClick={() => setViewer(ph)} />
            ))}
          </div>
        </div>
      )}

      {/* Lightbox photo viewer + editor (parity _GalleryViewerDialog / _GalleryEditDialog) */}
      {viewer && (
        <div className="fixed inset-0 z-50 bg-black/80 backdrop-blur-sm flex items-center justify-center p-4" onClick={() => setViewer(null)}>
          <div className="bg-slate-900 border border-slate-700 rounded-2xl max-w-3xl w-full max-h-[90vh] overflow-y-auto p-5 space-y-4" onClick={(e) => e.stopPropagation()}>
            <div className="flex items-center justify-between">
              <h4 className="font-bold text-sm text-slate-100">{lang === 'id' ? 'Foto Kenangan' : 'Memory Photo'}</h4>
              <button onClick={() => setViewer(null)} className="p-1.5 rounded-lg bg-slate-800 text-slate-300 hover:text-white transition-colors"><X className="w-4 h-4" /></button>
            </div>
            <div className="rounded-xl overflow-hidden border border-slate-800 bg-slate-950 aspect-video flex items-center justify-center">
              <ViewerImage photo={viewer} />
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 text-xs">
              <div className="space-y-1">
                <label className="text-[10px] uppercase text-slate-500">{lang === 'id' ? 'Caption' : 'Caption'}</label>
                <input
                  defaultValue={viewer.caption || ''}
                  className="w-full bg-slate-950 border border-slate-700 rounded-lg px-2 py-1.5 text-slate-100"
                  onBlur={(e) => updateLovePhotoMeta(viewer.id, { caption: e.target.value, photoDate: viewer.photoDate, visibility: viewer.visibility })}
                />
              </div>
              <div className="space-y-1">
                <label className="text-[10px] uppercase text-slate-500">{lang === 'id' ? 'Tanggal' : 'Date'}</label>
                <input
                  type="date"
                  defaultValue={viewer.photoDate || ''}
                  className="w-full bg-slate-950 border border-slate-700 rounded-lg px-2 py-1.5 text-slate-100"
                  onBlur={(e) => updateLovePhotoMeta(viewer.id, { caption: viewer.caption, photoDate: e.target.value, visibility: viewer.visibility })}
                />
              </div>
              <div className="space-y-1">
                <label className="text-[10px] uppercase text-slate-500">{lang === 'id' ? 'Visibilitas' : 'Visibility'}</label>
                <select
                  defaultValue={viewer.visibility || 'private'}
                  className="w-full bg-slate-950 border border-slate-700 rounded-lg px-2 py-1.5 text-slate-100"
                  onChange={(e) => updateLovePhotoMeta(viewer.id, { caption: viewer.caption, photoDate: viewer.photoDate, visibility: e.target.value })}
                >
                  <option value="private">{lang === 'id' ? 'Pribadi' : 'Private'}</option>
                  <option value="shared">{lang === 'id' ? 'Bersama' : 'Shared'}</option>
                </select>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Modal: Add Memory */}
      {showAddMemModal && (
        <div className="fixed inset-0 bg-slate-950/80 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 max-w-md w-full space-y-4 shadow-2xl">
            <h3 className="font-bold text-lg text-slate-100">{lang === 'id' ? 'Tambah Kenangan Indah' : 'Add Cherished Memory'}</h3>
            <div className="space-y-3 text-sm">
              <div>
                <label className="block text-xs font-bold text-slate-400 mb-1">{lang === 'id' ? 'Judul Kenangan' : 'Memory Title'}</label>
                <input
                  type="text"
                  value={newMemTitle}
                  onChange={(e) => setNewMemTitle(e.target.value)}
                  placeholder="e.g. Picnic in the park, First anniversary trip"
                  className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3.5 py-2 text-slate-100 text-sm focus:outline-none focus:border-rose-500"
                />
              </div>
              <div>
                <label className="block text-xs font-bold text-slate-400 mb-1">{lang === 'id' ? 'Tanggal' : 'Date'}</label>
                <input
                  type="date"
                  value={newMemDate}
                  onChange={(e) => setNewMemDate(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3.5 py-2 text-slate-100 text-sm focus:outline-none focus:border-rose-500"
                />
              </div>
              <div>
                <label className="block text-xs font-bold text-slate-400 mb-1">Emoji Icon</label>
                <div className="flex gap-2">
                  {['💖', '🌅', '⛺', '✈️', '🌸', '☕', '🍰', '💍'].map((emoji) => (
                    <button
                      key={emoji}
                      onClick={() => setNewMemEmoji(emoji)}
                      className={`text-xl p-2 rounded-lg border ${
                        newMemEmoji === emoji ? 'bg-rose-600/30 border-rose-500' : 'bg-slate-950 border-slate-800'
                      }`}
                    >
                      {emoji}
                    </button>
                  ))}
                </div>
              </div>
              <div>
                <label className="block text-xs font-bold text-slate-400 mb-1">{lang === 'id' ? 'Deskripsi / Cerita' : 'Story / Description'}</label>
                <textarea
                  rows={3}
                  value={newMemDesc}
                  onChange={(e) => setNewMemDesc(e.target.value)}
                  placeholder="Write a sweet memory or note..."
                  className="w-full bg-slate-950 border border-slate-800 rounded-xl p-3 text-slate-100 text-xs focus:outline-none focus:border-rose-500"
                />
              </div>
            </div>
            <div className="flex justify-end gap-3 pt-2">
              <button
                onClick={() => setShowAddMemModal(false)}
                className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-xs font-semibold text-slate-300 rounded-xl"
              >
                Cancel
              </button>
              <button
                onClick={() => {
                  if (!newMemTitle.trim()) return;
                  addLoveMemory(newMemTitle.trim(), newMemDate, newMemDesc.trim(), newMemEmoji);
                  setShowAddMemModal(false);
                  setNewMemTitle('');
                  setNewMemDesc('');
                }}
                className="px-4 py-2 bg-rose-600 hover:bg-rose-500 text-xs font-semibold text-white rounded-xl"
              >
                {lang === 'id' ? 'Simpan Kenangan' : 'Save Memory'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Modal: Add Bucket List Item */}
      {showAddBucketModal && (
        <div className="fixed inset-0 bg-slate-950/80 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 max-w-md w-full space-y-4 shadow-2xl">
            <h3 className="font-bold text-lg text-slate-100">{lang === 'id' ? 'Tambah Impian Berdua' : 'Add Bucket List Goal'}</h3>
            <div className="space-y-3 text-sm">
              <div>
                <label className="block text-xs font-bold text-slate-400 mb-1">{lang === 'id' ? 'Target Impian' : 'Goal'}</label>
                <input
                  type="text"
                  value={newBucketTitle}
                  onChange={(e) => setNewBucketTitle(e.target.value)}
                  placeholder="e.g. Visit Iceland to see Aurora Borealis"
                  className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3.5 py-2 text-slate-100 text-sm focus:outline-none focus:border-rose-500"
                />
              </div>
              <div>
                <label className="block text-xs font-bold text-slate-400 mb-1">{lang === 'id' ? 'Target Tahun' : 'Target Year'}</label>
                <input
                  type="number"
                  value={newBucketYear}
                  onChange={(e) => setNewBucketYear(Number(e.target.value))}
                  className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3.5 py-2 text-slate-100 text-sm focus:outline-none focus:border-rose-500"
                />
              </div>
            </div>
            <div className="flex justify-end gap-3 pt-2">
              <button
                onClick={() => setShowAddBucketModal(false)}
                className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-xs font-semibold text-slate-300 rounded-xl"
              >
                Cancel
              </button>
              <button
                onClick={() => {
                  if (!newBucketTitle.trim()) return;
                  const newItem = {
                    id: 'b_' + Date.now(),
                    title: newBucketTitle.trim(),
                    isCompleted: false,
                    targetYear: newBucketYear,
                  };
                  updateLoveSpace({ bucketList: [...loveSpace.bucketList, newItem] });
                  setShowAddBucketModal(false);
                  setNewBucketTitle('');
                }}
                className="px-4 py-2 bg-rose-600 hover:bg-rose-500 text-xs font-semibold text-white rounded-xl"
              >
                {lang === 'id' ? 'Tambah Impian' : 'Add Goal'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
