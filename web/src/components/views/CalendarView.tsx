import React, { useEffect, useState } from 'react';
import { useGame } from '../../context/GameContext';
import { HOLIDAYS_2026 } from '../../data/holidaysData';
import { HolidayItem } from '../../types';
import { apiGet } from '../../api/client';
import {
  Calendar as CalendarIcon,
  ChevronLeft,
  ChevronRight,
  Clock,
  Plus,
  Trash2,
  Bell,
  BellOff,
  Volume2,
  Sparkles,
  CheckCircle2,
} from 'lucide-react';

export const CalendarView: React.FC = () => {
  const {
    reminders,
    addReminder,
    toggleReminder,
    deleteReminder,
    calendarNotes,
    saveCalendarNote,
    dailies,
    quests,
    lang,
    showToast,
  } = useGame();

  const [currentDate, setCurrentDate] = useState<Date>(new Date());
  const [selectedDay, setSelectedDay] = useState<number>(new Date().getDate());
  const [dayNoteDraft, setDayNoteDraft] = useState('');

  // New reminder modal
  const [showAddReminderModal, setShowAddReminderModal] = useState(false);
  const [remTitle, setRemTitle] = useState('');
  const [remTime, setRemTime] = useState('09:00');
  const [remRepeat, setRemRepeat] = useState<'none' | 'daily' | 'weekdays' | 'weekly'>('daily');
  const [remSound, setRemSound] = useState<'beep' | 'bell' | 'magic' | 'fanfare'>('bell');

  const year = currentDate.getFullYear();
  const month = currentDate.getMonth(); // 0-indexed
  const [holidays, setHolidays] = useState<HolidayItem[]>(HOLIDAYS_2026);

  useEffect(() => {
    apiGet<any>(`/api/holidays?year=${year}`)
      .then((res) => {
        if (Array.isArray(res?.holidays) && res.holidays.length) setHolidays(res.holidays);
      })
      .catch(() => undefined);
  }, [year]);

  // Month names
  const monthNamesId = [
    'Januari', 'Februari', 'Maret', 'April', 'Mei', 'Juni',
    'Juli', 'Agustus', 'September', 'Oktober', 'November', 'Desember'
  ];
  const monthNamesEn = [
    'January', 'February', 'March', 'April', 'May', 'June',
    'July', 'August', 'September', 'October', 'November', 'December'
  ];

  const currentMonthName = lang === 'id' ? monthNamesId[month] : monthNamesEn[month];

  // Days in month
  const daysInMonth = new Date(year, month + 1, 0).getDate();
  const firstDayOfWeek = new Date(year, month, 1).getDay(); // 0 = Sun, 1 = Mon ...

  const handlePrevMonth = () => {
    setCurrentDate(new Date(year, month - 1, 1));
  };

  const handleNextMonth = () => {
    setCurrentDate(new Date(year, month + 1, 1));
  };

  // Find holidays for current year & month
  const monthHolidays = holidays.filter((h: HolidayItem) => {
    const [hYear, hMonth] = h.date.split('-').map(Number);
    return hYear === year && hMonth === month + 1;
  });

  const selectedDateStr = `${year}-${String(month + 1).padStart(2, '0')}-${String(selectedDay).padStart(2, '0')}`;
  const selectedDayHoliday = HOLIDAYS_2026.find((h: HolidayItem) => h.date === selectedDateStr);
  const selectedCalNote = calendarNotes.find((n) => n.date === selectedDateStr)?.note || '';

  useEffect(() => {
    setDayNoteDraft(selectedCalNote);
  }, [selectedDateStr, selectedCalNote]);

  return (
    <div id="calendar-reminders-view" className="space-y-6">
      {/* Header Banner */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 bg-slate-900/80 border border-slate-800 p-5 rounded-2xl">
        <div className="flex items-center gap-3">
          <div className="w-12 h-12 rounded-xl bg-cyan-500/10 border border-cyan-500/20 flex items-center justify-center text-2xl">
            📅
          </div>
          <div>
            <h1 className="text-xl font-bold text-slate-100 flex items-center gap-2">
              <span>{lang === 'id' ? 'Kalender & Pengingat Alarm' : 'Calendar & Reminder Alarms'}</span>
              <span className="text-xs px-2 py-0.5 rounded-full bg-cyan-500/20 text-cyan-300 font-medium">
                Indonesian Holidays Included
              </span>
            </h1>
            <p className="text-xs text-slate-400">
              {lang === 'id'
                ? 'Pantau hari libur nasional Indonesia (holidays.py), agenda quest, serta jadwal pengingat berulang.'
                : 'Track Indonesian public holidays, agenda tasks, and set recurring sound alarm reminders.'}
            </p>
          </div>
        </div>
        <button
          onClick={() => setShowAddReminderModal(true)}
          className="flex items-center gap-2 px-4 py-2 bg-cyan-600 hover:bg-cyan-500 text-white text-sm font-semibold rounded-xl transition-colors shadow-lg shadow-cyan-600/20"
        >
          <Plus className="w-4 h-4" />
          <span>{lang === 'id' ? 'Set Pengingat' : 'Add Reminder'}</span>
        </button>
      </div>

      {/* Main Grid: Calendar Matrix + Daily Agenda & Reminders */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left 2 Columns: Calendar Matrix */}
        <div className="lg:col-span-2 p-6 bg-slate-900/70 border border-slate-800 rounded-2xl space-y-6">
          {/* Month Header Navigation */}
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <CalendarIcon className="w-5 h-5 text-cyan-400" />
              <h2 className="text-lg font-bold text-slate-100">
                {currentMonthName} {year}
              </h2>
            </div>
            <div className="flex items-center gap-2">
              <button
                onClick={handlePrevMonth}
                className="p-2 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-lg transition-colors"
              >
                <ChevronLeft className="w-4 h-4" />
              </button>
              <button
                type="button"
                onClick={() => setCurrentDate(new Date(year - 1, month, 1))}
                className="px-2 py-1.5 bg-slate-800 hover:bg-slate-700 text-xs font-semibold text-slate-300 rounded-lg"
              >
                « {year - 1}
              </button>
              <button
                onClick={() => setCurrentDate(new Date())}
                className="px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-xs font-semibold text-slate-300 rounded-lg transition-colors"
              >
                {lang === 'id' ? 'Hari Ini' : 'Today'}
              </button>
              <button
                type="button"
                onClick={() => setCurrentDate(new Date(year + 1, month, 1))}
                className="px-2 py-1.5 bg-slate-800 hover:bg-slate-700 text-xs font-semibold text-slate-300 rounded-lg"
              >
                {year + 1} »
              </button>
              <button
                onClick={handleNextMonth}
                className="p-2 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-lg transition-colors"
              >
                <ChevronRight className="w-4 h-4" />
              </button>
            </div>
          </div>

          {/* Weekday Headers */}
          <div className="grid grid-cols-7 gap-2 text-center text-xs font-bold text-slate-500 uppercase tracking-wider">
            {['Min', 'Sen', 'Sel', 'Rab', 'Kam', 'Jum', 'Sab'].map((day, idx) => (
              <div key={idx} className={idx === 0 ? 'text-rose-400' : ''}>
                {day}
              </div>
            ))}
          </div>

          {/* Days Grid */}
          <div className="grid grid-cols-7 gap-2">
            {/* Empty slots for first week offset */}
            {Array.from({ length: firstDayOfWeek }).map((_, i) => (
              <div key={`empty_${i}`} className="h-16 rounded-xl bg-slate-950/20 border border-transparent" />
            ))}

            {/* Month Days */}
            {Array.from({ length: daysInMonth }).map((_, i) => {
              const dayNum = i + 1;
              const dateStr = `${year}-${String(month + 1).padStart(2, '0')}-${String(dayNum).padStart(2, '0')}`;
              const holiday = holidays.find((h: HolidayItem) => h.date === dateStr);
              const hasNote = calendarNotes.some((n) => n.date === dateStr && n.note);
              const isToday =
                year === new Date().getFullYear() &&
                month === new Date().getMonth() &&
                dayNum === new Date().getDate();
              const isSelected = dayNum === selectedDay;
              const isSunday = (firstDayOfWeek + i) % 7 === 0;

              return (
                <div
                  key={dayNum}
                  onClick={() => setSelectedDay(dayNum)}
                  className={`min-h-[72px] p-2 rounded-xl border flex flex-col justify-between cursor-pointer transition-all ${
                    isSelected
                      ? 'bg-cyan-950/60 border-cyan-500/60 text-cyan-200 shadow-md ring-1 ring-cyan-500/50'
                      : holiday
                      ? 'bg-rose-950/30 border-rose-500/30 text-rose-300 hover:border-rose-400'
                      : 'bg-slate-950/50 border-slate-800 text-slate-300 hover:border-slate-700'
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <span
                      className={`text-xs font-bold ${
                        isSunday || holiday ? 'text-rose-400' : 'text-slate-200'
                      }`}
                    >
                      {dayNum}
                    </span>
                    {holiday && <span className="w-1.5 h-1.5 rounded-full bg-rose-400" />}
                    {hasNote && <span className="w-1.5 h-1.5 rounded-full bg-cyan-400" />}
                    {isToday && <span className="text-[9px] text-emerald-400">•</span>}
                  </div>

                  {holiday && (
                    <span className="text-[10px] text-rose-300/90 truncate block font-medium" title={lang === 'id' ? holiday.nameId : holiday.nameEn}>
                      {lang === 'id' ? holiday.nameId : holiday.nameEn}
                    </span>
                  )}
                </div>
              );
            })}
          </div>

          {/* Month Holidays Footnote */}
          {monthHolidays.length > 0 && (
            <div className="p-3.5 bg-slate-950/80 border border-slate-800 rounded-xl space-y-2">
              <span className="text-xs font-bold uppercase tracking-wider text-rose-400">
                {lang === 'id' ? 'Hari Libur Bulan Ini' : 'Holidays This Month'} ({monthHolidays.length})
              </span>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 text-xs">
                {monthHolidays.map((h: HolidayItem, i: number) => (
                  <div key={i} className="flex items-center gap-2 text-slate-300">
                    <span className="font-mono text-rose-400 font-bold">{h.date}:</span>
                    <span className="truncate">{lang === 'id' ? h.nameId : h.nameEn}</span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* Right 1 Column: Selected Day Agenda & Reminders */}
        <div className="space-y-6">
          {/* Selected Date Summary Card */}
          <div className="p-5 bg-slate-900/70 border border-slate-800 rounded-2xl space-y-3">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <div>
                <h3 className="font-bold text-base text-slate-100">
                  {selectedDay} {currentMonthName} {year}
                </h3>
                <span className="text-xs text-slate-400">Daily Schedule & Tasks</span>
              </div>
              {selectedDayHoliday && (
                <span className="text-xs px-2.5 py-1 rounded-lg bg-rose-500/20 text-rose-300 font-semibold">
                  Holiday 🏖️
                </span>
              )}
            </div>

            {selectedDayHoliday && (
              <div className="p-3 bg-rose-950/30 border border-rose-500/30 rounded-xl text-xs text-rose-200">
                <span className="font-bold">{lang === 'id' ? selectedDayHoliday.nameId : selectedDayHoliday.nameEn}</span>
                {selectedDayHoliday.type === 'national' && (
                  <span className="block text-[11px] text-rose-400">Libur Nasional Resmi</span>
                )}
              </div>
            )}

            <div className="space-y-2">
              <span className="text-xs font-bold uppercase tracking-wider text-slate-500 block">
                {lang === 'id' ? 'Catatan hari ini' : 'Day note'}
              </span>
              <textarea
                key={selectedDateStr}
                defaultValue={selectedCalNote}
                onChange={(e) => setDayNoteDraft(e.target.value)}
                rows={3}
                className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-xs text-slate-200"
                placeholder={lang === 'id' ? 'Agenda / catatan…' : 'Agenda / note…'}
              />
              <button
                type="button"
                onClick={() => saveCalendarNote(selectedDateStr, dayNoteDraft || selectedCalNote)}
                className="w-full py-1.5 rounded-lg bg-cyan-600 text-white text-xs font-bold"
              >
                {lang === 'id' ? 'Simpan catatan' : 'Save note'}
              </button>
              <button
                type="button"
                onClick={() => {
                  saveCalendarNote(selectedDateStr, '');
                  setDayNoteDraft('');
                }}
                className="w-full py-1.5 rounded-lg bg-slate-800 text-slate-300 text-xs font-bold"
              >
                {lang === 'id' ? 'Hapus catatan hari ini' : 'Delete day note'}
              </button>
            </div>

            {/* Active Dailies Snapshot */}
            <div className="space-y-2">
              <span className="text-xs font-bold uppercase tracking-wider text-slate-500 block">
                {lang === 'id' ? 'Tugas Harian Aktif' : 'Active Dailies'} ({dailies.length})
              </span>
              <div className="space-y-1.5 max-h-[140px] overflow-y-auto pr-1">
                {dailies.map((d) => (
                  <div
                    key={d.id}
                    className="p-2.5 bg-slate-950/70 border border-slate-800 rounded-lg text-xs flex items-center justify-between text-slate-300"
                  >
                    <span>{d.title}</span>
                    <span className="font-mono text-[11px] text-amber-400 font-bold">+{d.streak}d streak</span>
                  </div>
                ))}
              </div>
            </div>
          </div>

          {/* Alarm Reminders List */}
          <div className="p-5 bg-slate-900/70 border border-slate-800 rounded-2xl space-y-4">
            <div className="flex items-center justify-between">
              <h3 className="font-bold text-sm text-slate-200 flex items-center gap-2">
                <Clock className="w-4 h-4 text-cyan-400" />
                <span>{lang === 'id' ? 'Daftar Pengingat Alarm' : 'Alarms & Reminders'}</span>
              </h3>
              <button
                onClick={() => setShowAddReminderModal(true)}
                className="text-xs text-cyan-400 hover:text-cyan-300 flex items-center gap-1 font-semibold"
              >
                <Plus className="w-3.5 h-3.5" />
                <span>Add</span>
              </button>
            </div>

            <div className="space-y-2.5">
              {reminders.map((rem) => (
                <div
                  key={rem.id}
                  className={`p-3 rounded-xl border flex items-center justify-between gap-3 transition-all ${
                    rem.isActive
                      ? 'bg-slate-950/80 border-slate-800 text-slate-200'
                      : 'bg-slate-950/30 border-slate-900 text-slate-500'
                  }`}
                >
                  <div className="flex items-center gap-3">
                    <button
                      onClick={() => toggleReminder(rem.id)}
                      className={`p-1.5 rounded-lg ${
                        rem.isActive ? 'bg-cyan-500/20 text-cyan-300' : 'bg-slate-800 text-slate-500'
                      }`}
                    >
                      {rem.isActive ? <Bell className="w-4 h-4" /> : <BellOff className="w-4 h-4" />}
                    </button>
                    <div>
                      <h4 className="font-bold text-xs text-slate-200">{rem.title}</h4>
                      <div className="flex items-center gap-2 text-[11px] text-slate-400">
                        <span className="font-mono font-bold text-cyan-400">{rem.time}</span>
                        <span>· {rem.repeat}</span>
                        <span>· 🔊 {rem.sound}</span>
                      </div>
                    </div>
                  </div>

                  <button
                    onClick={() => deleteReminder(rem.id)}
                    className="text-slate-600 hover:text-rose-400 p-1"
                  >
                    <Trash2 className="w-3.5 h-3.5" />
                  </button>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* Modal: Add Reminder */}
      {showAddReminderModal && (
        <div className="fixed inset-0 bg-slate-950/80 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 max-w-md w-full space-y-4 shadow-2xl">
            <h3 className="font-bold text-lg text-slate-100">{lang === 'id' ? 'Set Pengingat Baru' : 'Set New Reminder'}</h3>
            <div className="space-y-3 text-sm">
              <div>
                <label className="block text-xs font-bold text-slate-400 mb-1">{lang === 'id' ? 'Judul / Catatan' : 'Title'}</label>
                <input
                  type="text"
                  value={remTitle}
                  onChange={(e) => setRemTitle(e.target.value)}
                  placeholder="e.g. Minum Air & Istirahatkan Mata"
                  className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3.5 py-2 text-slate-100 text-sm focus:outline-none focus:border-cyan-500"
                />
              </div>
              <div>
                <label className="block text-xs font-bold text-slate-400 mb-1">{lang === 'id' ? 'Waktu Alarm' : 'Time'}</label>
                <input
                  type="time"
                  value={remTime}
                  onChange={(e) => setRemTime(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3.5 py-2 text-slate-100 text-sm focus:outline-none focus:border-cyan-500 font-mono"
                />
              </div>
              <div>
                <label className="block text-xs font-bold text-slate-400 mb-1">{lang === 'id' ? 'Pengulangan' : 'Repeat'}</label>
                <div className="grid grid-cols-2 gap-2">
                  {(['none', 'daily', 'weekdays', 'weekly'] as const).map((r) => (
                    <button
                      key={r}
                      onClick={() => setRemRepeat(r)}
                      className={`py-1.5 capitalize text-xs font-bold rounded-lg border ${
                        remRepeat === r ? 'bg-cyan-600/30 border-cyan-500 text-cyan-300' : 'bg-slate-950 border-slate-800 text-slate-400'
                      }`}
                    >
                      {r}
                    </button>
                  ))}
                </div>
              </div>
              <div>
                <label className="block text-xs font-bold text-slate-400 mb-1">{lang === 'id' ? 'Suara Alarm' : 'Alarm Sound'}</label>
                <div className="grid grid-cols-2 gap-2">
                  {(['beep', 'bell', 'magic', 'fanfare'] as const).map((s) => (
                    <button
                      key={s}
                      onClick={() => setRemSound(s)}
                      className={`py-1.5 capitalize text-xs font-bold rounded-lg border ${
                        remSound === s ? 'bg-cyan-600/30 border-cyan-500 text-cyan-300' : 'bg-slate-950 border-slate-800 text-slate-400'
                      }`}
                    >
                      🔊 {s}
                    </button>
                  ))}
                </div>
              </div>
            </div>
            <div className="flex justify-end gap-3 pt-2">
              <button
                onClick={() => setShowAddReminderModal(false)}
                className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-xs font-semibold text-slate-300 rounded-xl"
              >
                Cancel
              </button>
              <button
                onClick={() => {
                  if (!remTitle.trim()) return;
                  addReminder(remTitle.trim(), remTime, remRepeat, remSound);
                  setShowAddReminderModal(false);
                  setRemTitle('');
                }}
                className="px-4 py-2 bg-cyan-600 hover:bg-cyan-500 text-xs font-semibold text-white rounded-xl"
              >
                {lang === 'id' ? 'Simpan Pengingat' : 'Save Reminder'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
