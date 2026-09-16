import React, { useRef, useState } from 'react';
import {
  X, Upload, FileText, Download, Copy, Check, AlertTriangle, Music4, Clock, Info, ClipboardCheck,
} from 'lucide-react';
import { studio } from '../../api/studio';
import { downloadApiFile, saveBlobToFile, downloadTargetInfo } from '../../api/client';

type TrFn = (key: string, vars?: Record<string, string | number>, fb?: string) => string;

export interface LyricsReport {
  format: 'lrc' | 'plain';
  timedLines: number;
  breakLines: number;
  firstMs: number;
  lastMs: number;
  lineCount: number;
  offsetMs: number;
  metadata: Record<string, string>;
  warnings: string[];
  preview: string[];
}

const fmtMs = (ms: number) => {
  const s = Math.max(0, Math.round(ms / 1000));
  return `${Math.floor(s / 60)}:${String(s % 60).padStart(2, '0')}`;
};

const EXAMPLE_LRC = [
  '[ar:Nama Artis]',
  '[ti:Judul Lagu]',
  '[al:Nama Album]',
  '[offset:0]',
  '',
  '[00:00.00]Contoh baris pembuka',
  '[00:05.35]Baris kedua mulai di detik 5,35',
  '[00:11.00]Baris ketiga',
  '[00:16.20][00:48.00]Reff — satu teks, dua timestamp',
  '[00:24.00]',
  '[00:26.50]Baris terakhir contoh',
].join('\n');

/** Terjemahkan kode peringatan backend (mis. "untimed_lines:3") → teks id/en. */
function warningText(code: string, tr: TrFn): string {
  const [name, raw] = code.split(':');
  const n = raw || '';
  switch (name) {
    case 'no_timestamps': return tr('music_lyrics_warn_no_timestamps');
    case 'untimed_lines': return tr('music_lyrics_warn_untimed_lines', { n });
    case 'duplicate_timestamps': return tr('music_lyrics_warn_duplicate_timestamps', { n });
    case 'unknown_tags': return tr('music_lyrics_warn_unknown_tags', { n });
    case 'too_few_lines': return tr('music_lyrics_warn_too_few_lines');
    case 'first_line_late': return tr('music_lyrics_warn_first_line_late');
    case 'beyond_track_duration': return tr('music_lyrics_warn_beyond_track_duration');
    case 'offset_bad_value': return tr('music_lyrics_warn_offset_bad_value');
    default: return code;
  }
}

/**
 * A03 — LyricsImportDialog: SATU tempat untuk (a) panduan format lirik dan
 * (b) import file dari komputer dengan VALIDASI sebelum simpan.
 *
 * Sebelumnya import hanya tombol file + toast "format tidak valid" tanpa penjelasan;
 * sekarang: drop-zone, 3 blok panduan format, contoh siap salin, template .lrc siap
 * unduh, dan panel hasil validasi (baris bertimestamp, rentang waktu, jeda, metadata,
 * peringatan) sebelum lirik disimpan.
 */
export const LyricsImportDialog: React.FC<{
  keyName: string;
  trackTitle: string;
  trackArtist: string;
  trackDurationSec?: number;
  initialTab?: 'import' | 'guide';
  tr: TrFn;
  showToast: (type: 'boss' | 'success' | 'damage' | 'level_up' | 'info', title: string, message: string) => void;
  onClose: () => void;
  /** Dipanggil setelah import berhasil tersimpan (payload lirik siap pakai). */
  onImported: (lyrics: { plain: string; synced: string; offsetMs: number }, report: LyricsReport | null) => void;
}> = ({
  keyName, trackTitle, trackArtist, trackDurationSec = 0,
  initialTab = 'import', tr, showToast, onClose, onImported,
}) => {
  const [tab, setTab] = useState<'import' | 'guide'>(initialTab);
  const [fileName, setFileName] = useState('');
  const [content, setContent] = useState('');
  const [report, setReport] = useState<LyricsReport | null>(null);
  const [busy, setBusy] = useState(false);
  const [dragging, setDragging] = useState(false);
  const [copied, setCopied] = useState(false);
  const fileRef = useRef<HTMLInputElement | null>(null);

  const readFile = (f: File) => {
    setFileName(f.name);
    const reader = new FileReader();
    reader.onload = () => {
      const text = String(reader.result || '');
      setContent(text);
      validate(text);
    };
    reader.readAsText(f);
  };

  const validate = (text: string) => {
    if (!text.trim()) return;
    setBusy(true);
    studio.musicLyricsValidate({ key: keyName, content: text, duration: trackDurationSec || undefined })
      .then((d) => setReport(d?.report || d?.result?.report || null))
      .catch(() => setReport(null))
      .finally(() => setBusy(false));
  };

  const save = () => {
    if (!content.trim()) return;
    setBusy(true);
    studio.musicLyricsImport({
      key: keyName, title: trackTitle, artist: trackArtist,
      content, duration: trackDurationSec || undefined,
    })
      .then((res) => {
        const d = res?.result || {};
        if (d.ok && d.lyrics) {
          const rep: LyricsReport | null = d.report || null;
          onImported(
            { plain: d.lyrics.plain || '', synced: d.lyrics.synced || '', offsetMs: Number(d.lyrics.offsetMs) || 0 },
            rep as LyricsReport,
          );
          showToast('success', tr('music_lyrics_import_ok'),
            rep?.format === 'lrc' ? tr('music_lyrics_validate_ok', {
              n: rep.timedLines, first: fmtMs(rep.firstMs), last: fmtMs(rep.lastMs),
            }) : tr('music_lyrics_validate_plain'));
          onClose();
        } else if (d.msg === 'empty_content') {
          showToast('info', tr('music_lyrics_import_invalid'), tr('music_lyrics_import_empty'));
        } else {
          showToast('info', tr('music_lyrics_import_invalid'), '');
        }
      })
      .catch(() => showToast('info', tr('music_lyrics_import_invalid'), ''))
      .finally(() => setBusy(false));
  };

  // A03.5: template diunduh lewat jalur attachment server (Content-Disposition),
  // lalu lokasi berkasnya diberitahukan — sebelumnya Qt WebEngine membuang unduhan blob.
  const downloadTemplate = () => {
    const ok = downloadApiFile('/api/music/lyrics-template', 'craftlife-lyrics-template.lrc');
    if (!ok) { showToast('info', tr('music_lyrics_import_invalid'), ''); return; }
    downloadTargetInfo().then((info) => {
      if (info.dir) showToast('info', tr('music_lyrics_download_template'),
        tr('download_started_msg', { dir: info.dir }));
    }).catch(() => undefined);
  };

  const copyExample = async () => {
    try {
      await navigator.clipboard.writeText(EXAMPLE_LRC);
      setCopied(true);
      showToast('success', tr('music_lyrics_copied'), '');
      setTimeout(() => setCopied(false), 2500);
    } catch { /* clipboard diblokir browser */ }
  };

  const metaList = report ? Object.entries(report.metadata || {}).filter(([k]) => k !== 'offset').map(([k, v]) => `${k.toUpperCase()}: ${v}`).join(' · ') : '';

  const card = 'rounded-xl border border-slate-800 bg-[#121212]/60 p-4';
  const btn = 'flex items-center gap-1.5 px-3 py-2 rounded-xl text-[11px] font-bold transition-colors disabled:opacity-40';

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4" onClick={onClose}>
      <div onClick={(e) => e.stopPropagation()}
        className="w-full max-w-2xl max-h-[88vh] flex flex-col rounded-2xl bg-[#181818] border border-slate-700 shadow-2xl overflow-hidden">
        {/* Header */}
        <div className="px-5 py-4 border-b border-slate-800 flex items-start gap-3">
          <div className="w-9 h-9 rounded-xl bg-indigo-500/15 flex items-center justify-center shrink-0">
            <Upload className="w-4 h-4 text-indigo-300" />
          </div>
          <div className="min-w-0 mr-auto">
            <h2 className="text-sm font-black text-white truncate">{tr('music_lyrics_import_title')}</h2>
            <p className="text-[11px] text-slate-400 truncate flex items-center gap-1">
              <Music4 className="w-3 h-3 shrink-0" />
              {trackTitle || '—'}{trackArtist ? ` · ${trackArtist}` : ''}
              {trackDurationSec ? ` · ${fmtMs(trackDurationSec * 1000)}` : ''}
            </p>
          </div>
          <button type="button" onClick={onClose}
            className="p-1.5 rounded-lg text-slate-400 hover:text-slate-100 hover:bg-slate-800">
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Tab: Import | Panduan */}
        <div className="px-5 pt-3 flex items-center gap-1 border-b border-slate-800">
          {([['import', tr('music_lyrics_import_tab')], ['guide', tr('music_lyrics_guide_tab')]] as const).map(([id, label]) => (
            <button key={id} type="button" onClick={() => setTab(id)}
              className={`px-3 py-2 text-[11px] font-bold rounded-t-lg border-b-2 transition-colors ${
                tab === id ? 'border-emerald-500 text-emerald-300' : 'border-transparent text-slate-400 hover:text-slate-200'}`}>
              {label}
            </button>
          ))}
          <button type="button" onClick={downloadTemplate}
            className="ml-auto mb-1 flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-[10px] font-bold text-slate-200">
            <Download className="w-3 h-3" />{tr('music_lyrics_download_template')}
          </button>
        </div>

        <div className="flex-1 overflow-y-auto px-5 py-4 space-y-3">
          {tab === 'guide' && (
            <>
              <div className={card}>
                <p className="text-[11px] font-black text-emerald-300 mb-1">{tr('music_lyrics_import_format')}</p>
                <ul className="space-y-2 text-[11px] text-slate-300">
                  <li className="flex gap-2"><FileText className="w-3.5 h-3.5 text-emerald-400 shrink-0 mt-0.5" />{tr('music_lyrics_format_lrc_desc')}</li>
                  <li className="flex gap-2"><FileText className="w-3.5 h-3.5 text-slate-400 shrink-0 mt-0.5" />{tr('music_lyrics_format_plain_desc')}</li>
                  <li className="flex gap-2"><Info className="w-3.5 h-3.5 text-indigo-300 shrink-0 mt-0.5" />{tr('music_lyrics_format_tags_desc')}</li>
                </ul>
              </div>
              <div className={card}>
                <div className="flex items-center gap-2 mb-2">
                  <p className="text-[11px] font-black text-slate-200 mr-auto">{tr('music_lyrics_copy_example')}</p>
                  <button type="button" onClick={copyExample} className={`${btn} bg-slate-800 hover:bg-slate-700 text-slate-200`}>
                    {copied ? <Check className="w-3 h-3" /> : <Copy className="w-3 h-3" />}
                    {tr('music_lyrics_copy_example')}
                  </button>
                </div>
                <pre className="text-[10px] leading-relaxed text-slate-400 whitespace-pre-wrap font-mono bg-[#0d0d0d] rounded-lg p-3 border border-slate-800">{EXAMPLE_LRC}</pre>
              </div>
            </>
          )}

          {tab === 'import' && (
            <>
              {/* Drop zone */}
              <div
                onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
                onDragLeave={() => setDragging(false)}
                onDrop={(e) => {
                  e.preventDefault(); setDragging(false);
                  const f = e.dataTransfer.files?.[0];
                  if (f) readFile(f);
                }}
                onClick={() => fileRef.current?.click()}
                className={`rounded-xl border-2 border-dashed p-6 text-center cursor-pointer transition-colors ${
                  dragging ? 'border-emerald-500 bg-emerald-500/5' : 'border-slate-700 hover:border-slate-500'}`}>
                <Upload className="w-6 h-6 mx-auto mb-2 text-slate-400" />
                <p className="text-[11px] font-bold text-slate-200">{tr('music_lyrics_import_drop')}</p>
                <p className="text-[10px] text-slate-500 mt-1">.lrc · .txt — UTF-8</p>
                {fileName && (
                  <p className="mt-2 text-[10px] text-emerald-300 font-mono truncate">
                    {tr('music_lyrics_import_file')}: {fileName} · {content.split('\n').filter((l) => l.trim()).length} baris
                  </p>
                )}
                <input ref={fileRef} type="file" accept=".lrc,.txt,text/plain" className="hidden"
                  onChange={(e) => { const f = e.target.files?.[0]; if (f) readFile(f); e.target.value = ''; }} />
              </div>

              {/* Panduan singkat (juga tersedia di tab Panduan) */}
              <div className="text-[10px] text-slate-500 leading-relaxed">
                <p>• {tr('music_lyrics_format_lrc_desc')}</p>
                <p>• {tr('music_lyrics_format_tags_desc')}</p>
              </div>

              {/* Panel hasil validasi */}
              {report && (
                <div className={card}>
                  <div className="flex items-center gap-2 mb-2">
                    <ClipboardCheck className={`w-4 h-4 ${report.format === 'lrc' ? 'text-emerald-300' : 'text-slate-300'}`} />
                    <span className={`text-[10px] font-black uppercase tracking-wider px-1.5 py-0.5 rounded-md ${
                      report.format === 'lrc' ? 'bg-emerald-500/15 text-emerald-300' : 'bg-slate-700 text-slate-200'}`}>
                      {report.format === 'lrc' ? 'LRC' : 'PLAIN'}
                    </span>
                    <span className="text-[11px] text-slate-300 mr-auto">
                      {report.format === 'lrc'
                        ? tr('music_lyrics_validate_ok', {
                            n: report.timedLines, first: fmtMs(report.firstMs), last: fmtMs(report.lastMs),
                          })
                        : tr('music_lyrics_validate_plain')}
                    </span>
                  </div>

                  <div className="flex flex-wrap items-center gap-2 text-[10px] text-slate-400">
                    <span className="inline-flex items-center gap-1"><Clock className="w-3 h-3" />{fmtMs(report.firstMs)} → {fmtMs(report.lastMs)}</span>
                    {report.breakLines > 0 && <span>· {tr('music_lyrics_breaks', { n: report.breakLines })}</span>}
                    {report.offsetMs !== 0 && <span>· {tr('music_lyrics_offset_applied', { ms: report.offsetMs })}</span>}
                    {metaList && <span className="text-slate-500">· {tr('music_lyrics_meta_read', { list: metaList })}</span>}
                  </div>

                  {report.warnings.length > 0 && (
                    <div className="mt-3 rounded-lg bg-amber-500/10 border border-amber-500/25 p-2.5">
                      <p className="flex items-start gap-1.5 text-[10px] text-amber-200 leading-relaxed">
                        <AlertTriangle className="w-3.5 h-3.5 shrink-0 mt-0.5" />
                        {tr('music_lyrics_validate_warn', { list: report.warnings.map((w) => warningText(w, tr)).join(' · ') })}
                      </p>
                    </div>
                  )}

                  {report.preview.length > 0 && (
                    <pre className="mt-3 text-[10px] leading-relaxed text-slate-400 whitespace-pre-wrap font-mono max-h-28 overflow-hidden border-t border-slate-800 pt-2">
                      {report.preview.join('\n')}
                    </pre>
                  )}
                </div>
              )}
            </>
          )}
        </div>

        {/* Footer */}
        <div className="px-5 py-3 border-t border-slate-800 flex items-center gap-2">
          <button type="button" onClick={() => content && validate(content)} disabled={!content || busy}
            className={`${btn} bg-slate-800 hover:bg-slate-700 text-slate-200`}>
            <ClipboardCheck className="w-3.5 h-3.5" />{tr('music_lyrics_validate')}
          </button>
          <button type="button" onClick={downloadTemplate}
            className={`${btn} bg-slate-800 hover:bg-slate-700 text-slate-200`}>
            <Download className="w-3.5 h-3.5" />{tr('music_lyrics_download_template')}
          </button>
          <button type="button" onClick={onClose}
            className={`${btn} ml-auto bg-slate-800 hover:bg-slate-700 text-slate-200`}>
            {tr('music_lyrics_close')}
          </button>
          <button type="button" onClick={save} disabled={!content || busy}
            className={`${btn} bg-emerald-600 hover:bg-emerald-500 text-white`}>
            <Check className="w-3.5 h-3.5" />{tr('music_lyrics_import_save')}
          </button>
        </div>
      </div>
    </div>
  );
};

/** A03/A03.5: berkas lirik dari sisi klien (dipakai bila lirik belum tersimpan). */
export function lyricsBlob(
  title: string, artist: string, album: string, offsetMs: number,
  plain: string, synced: string, format: 'lrc' | 'txt',
): { blob: Blob; name: string } {
  const head = [`[ti:${title || ''}]`, `[ar:${artist || ''}]`];
  if (album) head.push(`[al:${album}]`);
  head.push(`[offset:${Math.round(offsetMs || 0)}]`, '[re:CraftLife]');
  const body = format === 'txt'
    ? (plain || synced.replace(/^\[(ar|ti|al|by|re|ve|length|offset)\s*:[^\]]*\]\s*$/gim, '').replace(/\[\d{1,3}:\d{1,2}(?:[.:]\d{1,3})?\]/g, '').split('\n').map((l) => l.trim()).filter(Boolean).join('\n'))
    : (synced || plain);
  const text = `${head.join('\n')}\n\n${body}\n`;
  const blob = new Blob([text], { type: 'text/plain;charset=utf-8' });
  return {
    blob,
    name: `${`${artist} - ${title}`.replace(/[/\\?%*:|"<>]/g, '-').trim() || 'lyrics'}.${format}`,
  };
}

/**
 * A03.5: ekspor lirik — lirik tersimpan diunduh LANGSUNG dari endpoint attachment
 * server (header [ti:][ar:][al:][offset:] lengkap, nama berkas dari server);
 * bila belum tersimpan, berkas dibuat dari tampilan saat ini.
 */
export function exportLyrics(
  key: string, format: 'lrc' | 'txt',
  opts: { title: string; artist: string; album: string; offsetMs: number; plain: string; synced: string; saved: boolean },
): 'server' | 'local' {
  if (opts.saved) {
    const ok = downloadApiFile(
      `/api/music/lyrics-export?key=${encodeURIComponent(key)}&format=${format}` +
      `&title=${encodeURIComponent(opts.title || '')}&artist=${encodeURIComponent(opts.artist || '')}` +
      `&album=${encodeURIComponent(opts.album || '')}`,
      `lyrics.${format}`,
    );
    if (ok) return 'server';
  }
  const { blob, name } = lyricsBlob(opts.title, opts.artist, opts.album, opts.offsetMs, opts.plain, opts.synced, format);
  saveBlobToFile(blob, name);
  return 'local';
}
