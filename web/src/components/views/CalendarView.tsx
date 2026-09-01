import React, { useEffect, useMemo, useState } from 'react';
import { ChevronLeft, ChevronRight } from 'lucide-react';
import { useGame } from '../../context/GameContext';
import { t } from '../../i18n';
import { authToken } from '../../api/client';
function auth(): Record<string, string> {
  return authToken() ? { Authorization: `Bearer ${authToken()}` } : {};
}


const tr = (key: string, vars?: Record<string, string>) => {
  let s = t(key, key);
  if (vars) for (const [k, v] of Object.entries(vars)) s = s.split(`{${k}}`).join(v);
  return s;
};

interface HolidayMap { [date: string]: { nameId: string; nameEn: string } }

function pad(n: number) { return String(n).padStart(2, '0'); }

export const CalendarView: React.FC = () => {
  const { calendarNotes, saveCalendarNote, deleteCalendarNote, lang, nowDate } = useGame();
  const now = nowDate() ?? new Date();
  // Parity CalendarPage.__init__: tampilkan SATU TAHUN penuh (12 bulan, grid 3 kolom).
  const [year, setYear] = useState(now.getFullYear());
  const [holidays, setHolidays] = useState<HolidayMap>({});
  const [noteDialog, setNoteDialog] = useState<string | null>(null); // date_str
  const [draft, setDraft] = useState('');

  const todayStr = `${now.getFullYear()}-${pad(now.getMonth() + 1)}-${pad(now.getDate())}`;

  // Map snapshot calendarNotes (parity _fetch_notes untuk 3 tahun; snapshot sudah lengkap)
  const notes = useMemo(() => {
    const m: Record<string, string> = {};
    for (const n of calendarNotes) if (n.note?.trim()) m[n.date] = n.note;
    return m;
  }, [calendarNotes]);

  // Parity _fetch_holidays: 3 tahun (server mengembalikan y-1..y+1)
  useEffect(() => {
    let alive = true;
    fetch(`/api/holidays?year=${year}`, { headers: auth() })
      .then((r) => (r.ok ? r.json() : null))
      .then((data) => {
        if (!alive || !data) return;
        const m: HolidayMap = {};
        for (const h of data.holidays || []) m[h.date] = { nameId: h.nameId, nameEn: h.nameEn };
        setHolidays(m);
      })
      .catch(() => { /* offline: biarkan kosong */ });
    return () => { alive = false; };
  }, [year]);

  // ── Parity header actions: ◀ tahun | label | tahun ▶ | Hari Ini ──
  const prevYear = () => setYear((y) => y - 1);
  const nextYear = () => setYear((y) => y + 1);
  const gotoToday = () => setYear(now.getFullYear());

  const holidayName = (ds: string) => {
    const h = holidays[ds];
    if (!h) return '';
    return lang === 'id' ? h.nameId : h.nameEn;
  };

  // ── Parity _open_note_dialog ──
  const openNote = (ds: string) => {
    setDraft(notes[ds] || '');
    setNoteDialog(ds);
  };
  // Parity _save_note: strip; kosong → hapus
  const saveNote = () => {
    if (!noteDialog) return;
    saveCalendarNote(noteDialog, draft);
    setNoteDialog(null);
  };
  const removeNote = () => {
    if (!noteDialog) return;
    deleteCalendarNote(noteDialog);
    setNoteDialog(null);
  };

  const dayHeaders = [0, 1, 2, 3, 4, 5, 6].map((i) => tr(`day_${i}`));

  const renderMonth = (month: number) => {
    const first = new Date(year, month - 1, 1);
    // Python calmod.monthrange: Senin=0..Minggu=6 — JS getDay(): Minggu=0 → shift
    const firstDay = (first.getDay() + 6) % 7;
    const daysInMonth = new Date(year, month, 0).getDate();
    const cells: (string | null)[] = [];
    for (let i = 0; i < firstDay; i++) cells.push(null);
    for (let d = 1; d <= daysInMonth; d++) cells.push(`${year}-${pad(month)}-${pad(d)}`);

    return (
      <div key={month} className="rounded-2xl border border-slate-800 bg-slate-900/60 p-3 flex flex-col">
        <h3 className="text-center text-sm font-black text-amber-200 pb-2">{tr(`month_${pad(month)}`)}</h3>
        <div className="grid grid-cols-7 gap-1 text-center">
          {dayHeaders.map((d, i) => (
            <div key={i} className="text-[10px] font-bold text-slate-500 pb-1">{d}</div>
          ))}
          {cells.map((ds, idx) => {
            if (!ds) return <div key={`x${idx}`} />;
            const day = parseInt(ds.slice(8), 10);
            const isToday = ds === todayStr;
            const isHoliday = ds in holidays;
            const hasNote = ds in notes;
            // Parity gaya: hover primary; today primary+accent border;
            // holiday teks merah + tooltip nama; note 📝 + border accent.
            return (
              <button
                key={ds}
                type="button"
                title={isHoliday ? `🏷️ ${holidayName(ds) || 'Libur'}` : undefined}
                onClick={() => openNote(ds)}
                className={`min-h-[34px] rounded-md text-xs font-bold border transition-colors leading-tight ${
                  isToday
                    ? 'bg-amber-500 text-slate-950 border-amber-300 border-2'
                    : 'bg-slate-950 border-slate-800 hover:bg-amber-500/80 hover:text-slate-950'
                } ${isHoliday && !isToday ? 'text-rose-400' : ''} ${
                  hasNote ? 'border-amber-400/80' : ''
                }`}
              >
                {day}
                {hasNote && <span className="block text-[9px] leading-none">📝</span>}
              </button>
            );
          })}
        </div>
      </div>
    );
  };

  return (
    <div className="px-4 md:px-8 pb-24 pt-4 max-w-7xl mx-auto space-y-4 animate-fade-in-up">
      {/* Header halaman (parity PageHeader('calendar') + aksi tahun) */}
      <header className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <p className="text-[11px] uppercase tracking-[0.2em] text-amber-400/80 font-bold">
            {tr('page_calendar_subtitle')}
          </p>
          <h2 className="text-2xl font-black text-slate-100">{tr('page_calendar_title')}</h2>
        </div>
        <div className="flex items-center gap-2">
          <button type="button" onClick={prevYear} aria-label="prev-year"
            className="p-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-200">
            <ChevronLeft className="w-4 h-4" />
          </button>
          <span className="text-sm font-black text-slate-100 w-14 text-center">{year}</span>
          <button type="button" onClick={nextYear} aria-label="next-year"
            className="p-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-200">
            <ChevronRight className="w-4 h-4" />
          </button>
          <button type="button" onClick={gotoToday}
            className="px-3 py-2 rounded-xl bg-amber-500 hover:bg-amber-400 text-slate-950 text-xs font-black">
            {tr('food_today')}
          </button>
        </div>
      </header>

      {/* Grid 12 bulan (parity months_grid 3 kolom; responsif 1/2/3) */}
      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
        {[1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12].map(renderMonth)}
      </div>

      {/* ── Dialog catatan (parity _open_note_dialog) ── */}
      {noteDialog && (
        <div className="fixed inset-0 z-[70] bg-slate-950/80 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-slate-700 rounded-2xl p-6 w-full max-w-md space-y-3">
            <h3 className="text-sm font-black text-slate-100">
              {tr('calendar_note_title', { date: noteDialog })}
            </h3>
            {holidayName(noteDialog) ? (
              <p className="text-xs font-bold text-amber-300">
                {tr('calendar_holiday_info', { name: holidayName(noteDialog) })}
              </p>
            ) : null}
            <label className="block space-y-1">
              <span className="text-[11px] uppercase tracking-wider text-slate-500">
                {tr('calendar_note_label')}
              </span>
              <textarea
                value={draft}
                onChange={(e) => setDraft(e.target.value)}
                placeholder={tr('calendar_note_placeholder')}
                rows={5}
                className="w-full px-3 py-2 rounded-xl bg-slate-950 border border-slate-800 text-sm text-slate-100 resize-none"
              />
            </label>
            <div className="flex justify-between gap-2 pt-1">
              <button type="button" onClick={removeNote}
                className="px-4 py-2 rounded-xl bg-rose-900/40 hover:bg-rose-900/70 text-rose-300 text-xs font-bold">
                {tr('calendar_delete')}
              </button>
              <div className="flex gap-2">
                <button type="button" onClick={() => setNoteDialog(null)}
                  className="px-4 py-2 rounded-xl bg-slate-800 text-slate-300 text-xs font-bold">
                  {tr('btn_cancel')}
                </button>
                <button type="button" onClick={saveNote}
                  className="px-4 py-2 rounded-xl bg-amber-500 hover:bg-amber-400 text-slate-950 text-xs font-black">
                  {tr('dialog_save')}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

