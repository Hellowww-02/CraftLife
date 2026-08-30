import React, { useRef, useState } from 'react';
import {
  Bell, BellOff, Plus, RefreshCw, Pencil, Trash2, Play, FolderOpen, X, Volume2,
} from 'lucide-react';
import { useGame } from '../../context/GameContext';
import { t } from '../../i18n';
import { apiUploadFile } from '../../api/client';
import { playReminderSound, startReminderLoop, stopReminderLoop } from '../../utils/sound';
import type { ReminderItem } from '../../types';

const tr = (key: string, vars?: Record<string, string>) => {
  let s = t(key, key);
  if (vars) for (const [k, v] of Object.entries(vars)) s = s.split(`{${k}}`).join(v);
  return s;
};

interface ReminderForm {
  title: string;
  description: string;
  date: string; // yyyy-mm-dd
  time: string; // HH:mm
  repeat: 'none' | 'daily' | 'weekly' | 'custom';
  repeatDays: Set<number>; // 0=Sen .. 6=Min sama dengan indeks checkbox PyQt
  sound: 'default' | 'beep1' | 'beep2' | 'custom';
  soundFile: string; // path relatif media, mis. reminder_sounds/x.mp3
  soundFileLabel: string; // basename utk tampilan (parity sound_file_label)
}

const DAY_SHORT_KEYS = [
  'day_mon_short', 'day_tue_short', 'day_wed_short', 'day_thu_short', 'day_fri_short', 'day_sat_short', 'day_sun_short',
] as const;

function fmtDate(d: Date) {
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
}
function fmtTime(d: Date) {
  return `${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`;
}

function emptyForm(): ReminderForm {
  // Parity ReminderDialog default: datetime = sekarang.
  const now = new Date();
  return {
    title: '', description: '', date: fmtDate(now), time: fmtTime(now),
    repeat: 'none', repeatDays: new Set<number>(),
    sound: 'default', soundFile: '', soundFileLabel: '',
  };
}

export const RemindersView: React.FC = () => {
  const {
    reminders, addReminder, editReminder, deleteReminder, toggleReminder,
    lang,
  } = useGame();

  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [formOpen, setFormOpen] = useState<null | { mode: 'add' } | { mode: 'edit'; rem: ReminderItem }>(null);
  const [deleteTarget, setDeleteTarget] = useState<ReminderItem | null>(null);
  const [testTarget, setTestTarget] = useState<ReminderItem | null>(null);
  const [pastConfirm, setPastConfirm] = useState<(() => void) | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [form, setForm] = useState<ReminderForm>(emptyForm());
  const fileRef = useRef<HTMLInputElement | null>(null);

  // refresh list tidak perlu (snapshot reaktif via applyLive) — tombol tetap ada parity _btn refresh.
  const refresh = () => { /* snapshot auto-refresh; no-op visual */ };

  const openAdd = () => { setEditReset(); setForm(emptyForm()); setFormOpen({ mode: 'add' }); };
  const openEdit = () => {
    const r = reminders.find((x) => x.id === selectedId);
    if (!r) return;
    setEditReset();
    // Parity _load_data
    const dt = (r.datetime || '').replace('T', ' ');
    const dayParts = (r.repeatDays || '').split(',').map((p) => p.trim()).filter(Boolean).map((p) => parseInt(p, 10));
    setForm({
      title: r.title, description: r.description || '',
      date: dt.slice(0, 10) || fmtDate(new Date()), time: dt.slice(11, 16) || fmtTime(new Date()),
      repeat: r.repeat, repeatDays: new Set(dayParts.filter((n) => !isNaN(n))),
      sound: r.sound, soundFile: r.soundFile || '', soundFileLabel: r.soundFile ? r.soundFile.split('/').pop() || '' : '',
    });
    setFormOpen({ mode: 'edit', rem: r });
  };
  const setEditReset = () => { setErr(null); };

  // ── Parity _browse_file: input file .mp3 → upload ke server (QFileDialog→browser picker) ──
  const browseMp3 = async (f: File) => {
    if (!f.name.toLowerCase().endsWith('.mp3')) {
      setErr(`${tr('msg_error')}: ${tr('reminders_select_mp3')}`);
      return;
    }
    const res = await apiUploadFile<any>('reminder_sound', f);
    const inner = res?.result ?? res;
    if (inner?.ok !== false && inner?.path) {
      setForm((p) => ({ ...p, soundFile: inner.path as string, soundFileLabel: f.name }));
    } else {
      setErr(`${tr('gagal_title')}: ${(inner && (inner.msg || inner.error)) || 'upload'}`);
    }
  };

  // ── Parity _save ──
  const save = () => {
    const title = form.title.trim();
    if (!title) { setErr(`${tr('msg_error')}: ${tr('reminders_title_required')}`); return; }
    if (!form.date || !form.time) { setErr(`${tr('msg_error')}: ${tr('reminders_invalid_datetime')}`); return; }
    const dt = new Date(`${form.date}T${form.time}:00`);
    if (isNaN(dt.getTime())) { setErr(`${tr('msg_error')}: ${tr('reminders_invalid_datetime')}`); return; }
    const proceed = () => {
      if (form.sound === 'custom' && !form.soundFile) {
        setErr(`${tr('msg_error')}: ${tr('reminders_custom_file_required')}`);
        return;
      }
      let repeatDays = '';
      if (form.repeat === 'custom') {
        if (form.repeatDays.size === 0) {
          setErr(`${tr('msg_error')}: ${tr('reminders_custom_days_required')}`);
          return;
        }
        repeatDays = [...form.repeatDays].sort((a, b) => a - b).join(',');
      }
      const payload = {
        title,
        description: form.description.trim(),
        reminderDatetime: `${form.date} ${form.time}:00`,
        repeat: form.repeat,
        repeatDays,
        soundType: form.sound,
        soundFile: form.sound === 'custom' ? form.soundFile : undefined,
      };
      if (formOpen?.mode === 'edit') {
        editReminder(formOpen.rem.id, payload);
      } else {
        addReminder(payload);
      }
      setFormOpen(null);
      setErr(null);
    };
    // Parity: waktu di masa lalu → konfirmasi dlg dulu.
    if (dt.getTime() < Date.now()) {
      setPastConfirm(() => () => { setPastConfirm(null); proceed(); });
      return;
    }
    proceed();
  };

  // ── Parity _test_selected ──
  const openTest = () => {
    const r = reminders.find((x) => x.id === selectedId);
    if (!r) return;
    stopReminderLoop();
    if (r.sound === 'custom' && r.soundFile) {
      startReminderLoop('custom', `/music/stream?path=${encodeURIComponent(r.soundFile)}`);
    } else {
      playReminderSound(r.sound);
    }
    setTestTarget(r);
  };
  const closeTest = () => { stopReminderLoop(); setTestTarget(null); };

  // ── Parity _toggle_selected / _delete_selected ──
  const doToggle = () => { if (selectedId) { stopReminderLoop(); toggleReminder(selectedId); } };
  const doDelete = () => {
    if (!deleteTarget) return;
    stopReminderLoop();
    deleteReminder(deleteTarget.id);
    if (selectedId === deleteTarget.id) setSelectedId(null);
    setDeleteTarget(null);
  };

  return (
    <div className="px-4 md:px-8 pb-24 pt-4 max-w-4xl mx-auto space-y-4 animate-fade-in-up">
      {/* Header halaman (parity PageHeader('reminders'): subtitle atas, judul bawah) */}
      <header>
        <p className="text-[11px] uppercase tracking-[0.2em] text-amber-400/80 font-bold">
          {tr('page_reminders_subtitle')}
        </p>
        <h2 className="text-2xl font-black text-slate-100">{tr('page_reminders_title')}</h2>
      </header>

      {/* Toolbar (parity toolbar) */}
      <div className="flex items-center gap-2">
        <button
          type="button" onClick={openAdd}
          className="flex items-center gap-1.5 px-3 py-2 rounded-xl bg-amber-500 hover:bg-amber-400 text-slate-950 text-xs font-black"
        >
          <Plus className="w-3.5 h-3.5" /> {tr('reminders_add')}
        </button>
        <button
          type="button" onClick={refresh}
          className="flex items-center gap-1.5 px-3 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-bold"
        >
          <RefreshCw className="w-3.5 h-3.5" /> {tr('reminders_refresh')}
        </button>
      </div>

      {/* Daftar reminder (parity reminder_list: 🔔/🔕 judul - waktu ✅) */}
      <div className="rounded-2xl border border-slate-800 bg-slate-900/60 overflow-hidden">
        {reminders.length === 0 && (
          <p className="text-xs text-slate-500 text-center py-10">{tr('reminders_empty')}</p>
        )}
        {reminders.map((r) => {
          const selected = r.id === selectedId;
          const timeStr = (r.datetime || '').slice(0, 16).replace('T', ' ') || r.time;
          return (
            <button
              key={r.id}
              type="button"
              onClick={() => setSelectedId(r.id)}
              className={`w-full text-left px-4 py-3 flex items-center gap-2 border-b border-slate-800/60 last:border-0 transition-colors ${
                selected ? 'bg-amber-500/10 border-l-2 border-l-amber-400' : 'hover:bg-slate-800/40'
              } ${!r.isActive ? 'opacity-50' : ''}`}
            >
              {r.isActive
                ? <Bell className="w-4 h-4 text-amber-400 shrink-0" />
                : <BellOff className="w-4 h-4 text-slate-500 shrink-0" />}
              <span className="flex-1 min-w-0">
                <span className="text-sm font-bold text-slate-100 truncate block">{r.title}</span>
                <span className="text-[11px] text-slate-400 font-mono">{timeStr}</span>
              </span>
              {r.triggered && <span className="text-emerald-400 text-sm shrink-0">✅</span>}
            </button>
          );
        })}
      </div>

      {/* Tombol aksi item terpilih (parity action_row) */}
      <div className="flex flex-wrap items-center gap-2">
        <button type="button" onClick={openEdit} disabled={!selectedId}
          className="flex items-center gap-1.5 px-3 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-bold disabled:opacity-40">
          <Pencil className="w-3.5 h-3.5" /> {tr('reminders_edit')}
        </button>
        <button type="button" onClick={() => { const r = reminders.find((x) => x.id === selectedId); if (r) setDeleteTarget(r); }} disabled={!selectedId}
          className="flex items-center gap-1.5 px-3 py-2 rounded-xl bg-rose-900/40 hover:bg-rose-900/70 text-rose-300 text-xs font-bold disabled:opacity-40">
          <Trash2 className="w-3.5 h-3.5" /> {tr('reminders_delete')}
        </button>
        <button type="button" onClick={doToggle} disabled={!selectedId}
          className="flex items-center gap-1.5 px-3 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-bold disabled:opacity-40">
          {selectedId && reminders.find((x) => x.id === selectedId)?.isActive
            ? <><BellOff className="w-3.5 h-3.5" /> {tr('reminders_toggle')}</>
            : <><Bell className="w-3.5 h-3.5" /> {tr('reminders_toggle')}</>}
        </button>
        <button type="button" onClick={openTest} disabled={!selectedId}
          className="flex items-center gap-1.5 px-3 py-2 rounded-xl bg-amber-600/30 hover:bg-amber-600/50 text-amber-300 text-xs font-bold disabled:opacity-40">
          <Play className="w-3.5 h-3.5" /> {tr('reminders_test')}
        </button>
      </div>

      {/* ── Dialog tambah/edit (parity ReminderDialog) ── */}
      {formOpen && (
        <div className="fixed inset-0 z-[70] bg-slate-950/80 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-slate-700 rounded-2xl p-6 w-full max-w-lg space-y-3 max-h-[90vh] overflow-y-auto">
            <h3 className="text-sm font-black text-slate-100">
              {formOpen.mode === 'edit' ? tr('reminders_edit_title') : tr('reminders_add_title')}
            </h3>
            {err && <p className="text-xs text-rose-400">{err}</p>}

            {/* Judul */}
            <label className="block space-y-1">
              <span className="text-[11px] uppercase tracking-wider text-slate-500">{tr('reminders_title_label')}</span>
              <input value={form.title} onChange={(e) => setForm((p) => ({ ...p, title: e.target.value }))}
                placeholder={tr('reminders_title_ph')}
                className="w-full px-3 py-2 rounded-xl bg-slate-950 border border-slate-800 text-sm text-slate-100" />
            </label>

            {/* Deskripsi */}
            <label className="block space-y-1">
              <span className="text-[11px] uppercase tracking-wider text-slate-500">{tr('reminders_desc_label')}</span>
              <textarea value={form.description} onChange={(e) => setForm((p) => ({ ...p, description: e.target.value }))}
                placeholder={tr('reminders_desc_ph')} rows={2}
                className="w-full px-3 py-2 rounded-xl bg-slate-950 border border-slate-800 text-sm text-slate-100 resize-none" />
            </label>

            {/* Waktu (parity QDateTimeEdit yyyy-MM-dd HH:mm) */}
            <label className="block space-y-1">
              <span className="text-[11px] uppercase tracking-wider text-slate-500">{tr('reminders_datetime_label')}</span>
              <div className="flex gap-2">
                <input type="date" value={form.date} onChange={(e) => setForm((p) => ({ ...p, date: e.target.value }))}
                  className="flex-1 px-3 py-2 rounded-xl bg-slate-950 border border-slate-800 text-sm text-slate-100" />
                <input type="time" value={form.time} onChange={(e) => setForm((p) => ({ ...p, time: e.target.value }))}
                  className="px-3 py-2 rounded-xl bg-slate-950 border border-slate-800 text-sm text-slate-100 font-mono" />
              </div>
            </label>

            {/* Ulangi (parity repeat_combo + custom days) */}
            <label className="block space-y-1">
              <span className="text-[11px] uppercase tracking-wider text-slate-500">{tr('reminders_repeat_label')}</span>
              <select value={form.repeat} onChange={(e) => setForm((p) => ({ ...p, repeat: e.target.value as ReminderForm['repeat'] }))}
                className="w-full px-3 py-2 rounded-xl bg-slate-950 border border-slate-800 text-sm text-slate-100">
                <option value="none">{tr('reminders_repeat_none')}</option>
                <option value="daily">{tr('reminders_repeat_daily')}</option>
                <option value="weekly">{tr('reminders_repeat_weekly')}</option>
                <option value="custom">{tr('reminders_repeat_custom')}</option>
              </select>
            </label>
            {form.repeat === 'custom' && (
              <div className="flex flex-wrap gap-2">
                {DAY_SHORT_KEYS.map((key, i) => {
                  const active = form.repeatDays.has(i);
                  return (
                    <button key={key} type="button"
                      onClick={() => setForm((p) => {
                        const s = new Set(p.repeatDays);
                        if (s.has(i)) s.delete(i); else s.add(i);
                        return { ...p, repeatDays: s };
                      })}
                      className={`px-2.5 py-1.5 rounded-lg border text-xs font-bold ${
                        active ? 'border-amber-400 bg-amber-500/20 text-amber-300' : 'border-slate-700 text-slate-400'
                      }`}>
                      {tr(key)}
                    </button>
                  );
                })}
              </div>
            )}

            {/* Suara (parity sound_combo + browse_btn + label file) */}
            <label className="block space-y-1">
              <span className="text-[11px] uppercase tracking-wider text-slate-500">{tr('reminders_sound_label')}</span>
              <div className="flex gap-2">
                <select value={form.sound} onChange={(e) => setForm((p) => ({
                  ...p, sound: e.target.value as ReminderForm['sound'],
                  ...(e.target.value !== 'custom' ? { soundFile: '', soundFileLabel: '' } : {}),
                }))}
                  className="flex-1 px-3 py-2 rounded-xl bg-slate-950 border border-slate-800 text-sm text-slate-100">
                  <option value="default">{tr('reminders_sound_default')}</option>
                  <option value="beep1">{tr('reminders_sound_beep1')}</option>
                  <option value="beep2">{tr('reminders_sound_beep2')}</option>
                  <option value="custom">{tr('reminders_sound_custom')}</option>
                </select>
                <button type="button" disabled={form.sound !== 'custom'}
                  onClick={() => fileRef.current?.click()}
                  className="flex items-center gap-1.5 px-3 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-bold disabled:opacity-40">
                  <FolderOpen className="w-3.5 h-3.5" /> {tr('reminders_browse')}
                </button>
                <input ref={fileRef} type="file" accept=".mp3,audio/mpeg" className="hidden"
                  onChange={(e) => { const f = e.target.files?.[0]; if (f) void browseMp3(f); e.target.value = ''; }} />
              </div>
              {form.soundFileLabel && (
                <p className="text-[11px] text-emerald-400 flex items-center gap-1">
                  <Volume2 className="w-3 h-3" /> {form.soundFileLabel}
                </p>
              )}
            </label>

            <div className="flex justify-end gap-2 pt-2">
              <button type="button" onClick={() => { setFormOpen(null); setErr(null); }}
                className="px-4 py-2 rounded-xl bg-slate-800 text-slate-300 text-xs font-bold">
                <X className="w-3.5 h-3.5 inline mr-1" />{tr('dialog_cancel') !== 'dialog_cancel' ? tr('dialog_cancel') : (lang === 'id' ? 'Batal' : 'Cancel')}
              </button>
              <button type="button" onClick={save}
                className="px-4 py-2 rounded-xl bg-amber-500 hover:bg-amber-400 text-slate-950 text-xs font-black">
                {tr('dialog_save')}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ── Konfirmasi waktu lampau (parity past_datetime_confirm) ── */}
      {pastConfirm && (
        <div className="fixed inset-0 z-[80] bg-slate-950/80 flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-slate-700 rounded-2xl p-6 w-full max-w-sm space-y-4">
            <h3 className="text-sm font-black text-slate-100">{tr('confirm_title')}</h3>
            <p className="text-xs text-slate-300">{tr('reminders_past_datetime_confirm')}</p>
            <div className="flex justify-end gap-2">
              <button type="button" onClick={() => setPastConfirm(null)}
                className="px-4 py-2 rounded-xl bg-slate-800 text-slate-300 text-xs font-bold">{tr('msg_no')}</button>
              <button type="button" onClick={() => pastConfirm()}
                className="px-4 py-2 rounded-xl bg-amber-500 text-slate-950 text-xs font-black">{tr('msg_yes')}</button>
            </div>
          </div>
        </div>
      )}

      {/* ── Konfirmasi hapus (parity reminders_delete_confirm) ── */}
      {deleteTarget && (
        <div className="fixed inset-0 z-[80] bg-slate-950/80 flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-slate-700 rounded-2xl p-6 w-full max-w-sm space-y-4">
            <h3 className="text-sm font-black text-slate-100">{tr('confirm_title')}</h3>
            <p className="text-xs text-slate-300">{tr('reminders_delete_confirm')}</p>
            <div className="flex justify-end gap-2">
              <button type="button" onClick={() => setDeleteTarget(null)}
                className="px-4 py-2 rounded-xl bg-slate-800 text-slate-300 text-xs font-bold">{tr('msg_no')}</button>
              <button type="button" onClick={doDelete}
                className="px-4 py-2 rounded-xl bg-rose-600 hover:bg-rose-500 text-white text-xs font-black">{tr('msg_yes')}</button>
            </div>
          </div>
        </div>
      )}

      {/* ── Dialog tes suara (parity _test_selected: suara jalan → OK menghentikan) ── */}
      {testTarget && (
        <div className="fixed inset-0 z-[80] bg-slate-950/80 flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-slate-700 rounded-2xl p-6 w-full max-w-sm space-y-4 text-center">
            <h3 className="text-sm font-black text-slate-100">{tr('reminders_test_title')}</h3>
            <p className="text-xs text-slate-300">
              {tr('reminders_test_msg', { title: testTarget.title })}
            </p>
            <button type="button" onClick={closeTest}
              className="px-6 py-2 rounded-xl bg-amber-500 text-slate-950 text-xs font-black">{tr('msg_ok')}</button>
          </div>
        </div>
      )}
    </div>
  );
};
