/**
 * NotebookRail.tsx — rail kiri ala NotebookLM (A07, dirapikan di A15).
 *
 * Isi rail: pemilih notebook (ikon/emoji **yang benar-benar diinput user**, notebook aktif
 * ditandai), tombol **+ Notebook**, aksi ganti nama/hapus (mode melebar), dan pemilih
 * bahasa id/en.
 *
 * C01: navigasi Sumber/Chat/Studio dihapus dari rail — di desktop ketiga panel kini
 * tampil sejajar dengan divider seret + collapse di LearningShell (ala NotebookLM),
 * sehingga tombol penukar tidak lagi bermakna. Di mobile, tab strip LearningShell
 * yang mengatur view (seperti sebelumnya).
 *
 * A15 — perbaikan HANYA di rail kiri:
 *  · **Ikon sesuai input user.** Dulu rail menggambar emoji *dan* avatar inisial sekaligus
 *    (dua “avatar” bertumpuk) karena `icon` tidak pernah dikirim/disimpan server; sekarang
 *    satu avatar saja — emoji user apa adanya, dan hanya kalau benar-benar kosong jatuh ke
 *    inisial judul (`notebookGlyph`). `icon` kini tersimpan di `learning_notebooks.icon`.
 *  · **Tata letak rapi.** Lebar rail mengikuti `--rail-w` dari LearningShell (72 px menyempit /
 *    220 px melebar), tinggi penuh, judul terpotong rapi (`truncate` + `min-w-0`), tombol
 *    + Notebook & navigasi ikut melebar (kelas `.is-row`), daftar panjang bisa digulir,
 *    penanda aktif jelas, dan setiap tombol punya `title`/`aria-label`.
 *
 * Kelas `.ct-nlm-rail*` berada di index.css TANPA `@layer`, jadi ia mengalahkan utility
 * Tailwind: karena itu penyesuaian ukuran/visibilitas memakai modifier rail khusus
 * (`.is-row`, `.is-sm`) dan pembungkus `hidden lg:block` — bukan `!important` atau utility
 * display yang bertabrakan. Di bawah 1024 px rail menjadi bottom-bar (aturannya juga di CSS).
 */
import React from 'react';
import { Plus, FileText, Bot, Sparkles, Languages, Pencil, Trash2, BookOpen } from 'lucide-react';

export type LearningViewKey = 'sources' | 'chat' | 'studio';

export interface RailNotebook {
  id: string;
  title: string;
  icon?: string;
}

export interface NotebookRailProps {
  notebooks: RailNotebook[];
  activeId: string;
  expanded: boolean;
  onToggleExpanded: () => void;
  onSelect: (id: string) => void;
  onCreate: () => void;
  onRename: () => void;
  onDelete: () => void;
  lang: 'id' | 'en';
  onLang: (l: 'id' | 'en') => void;
  tr: (key: string, vars?: Record<string, string | number>, fallback?: string) => string;
}

/** Inisial notebook untuk avatar (2 huruf, aman untuk judul non-latin). */
export function notebookInitials(title: string): string {
  const clean = String(title || '').trim();
  if (!clean) return 'NB';
  const words = clean.split(/\s+/).filter(Boolean);
  if (words.length >= 2) return (words[0][0] + words[1][0]).toUpperCase();
  return clean.slice(0, 2).toUpperCase();
}

/**
 * A15: avatar notebook = **satu** penanda.
 * Ikon (emoji) dari user dipakai apa adanya; hanya bila kosong/berisi spasi → inisial judul.
 */
export function notebookGlyph(nb: { icon?: string; title?: string }): { kind: 'icon' | 'initials'; text: string } {
  const icon = String(nb?.icon ?? '').trim();
  if (icon) return { kind: 'icon', text: icon };
  return { kind: 'initials', text: notebookInitials(String(nb?.title ?? '')) };
}

const NotebookRail: React.FC<NotebookRailProps> = ({
  notebooks, activeId, expanded, onToggleExpanded, onSelect, onCreate, onRename, onDelete,
  lang, onLang, tr,
}) => {
  const activeNb = notebooks.find((n) => String(n.id) === String(activeId));

  /** Satu avatar notebook — emoji user atau inisial; tidak pernah dua-duanya. */
  const Glyph: React.FC<{ nb: RailNotebook }> = ({ nb }) => {
    const g = notebookGlyph(nb);
    return (
      <span
        className={`shrink-0 grid place-items-center leading-none border border-white/10 bg-black/25 ${
          expanded ? 'w-7 h-7 rounded-xl text-[15px]' : 'w-6 h-6 rounded-lg text-[12px]'
        } ${g.kind === 'initials' ? 'font-black tracking-wide ct-nlm-num' : ''}`}
        data-testid="notebook-avatar"
        data-glyph={g.kind}
      >
        {g.text}
      </span>
    );
  };

  return (
    <nav
      className="ct-nlm ct-nlm-rail flex lg:flex-col items-center gap-2 p-2 max-lg:flex-row max-lg:justify-between lg:h-full lg:w-[var(--rail-w)] lg:shrink-0 transition-[width] duration-200"
      aria-label={tr('learning_nb_switcher', {}, 'Notebook')}
    >
      {/* Header rail (desktop): lebarkan/sempitkan + jumlah notebook */}
      <div className="hidden lg:block w-full">
        <button
          onClick={onToggleExpanded}
          className={`ct-nlm-railbtn ${expanded ? 'is-row' : ''}`}
          title={expanded
            ? tr('learning_rail_collapse', {}, 'Sempitkan rail')
            : tr('learning_rail_expand', {}, 'Lebarkan rail')}
          data-testid="rail-toggle"
        >
          <BookOpen className="w-4 h-4 shrink-0" />
          {expanded && (
            <>
              <span className="min-w-0 flex-1 truncate text-left text-[11px] font-bold uppercase tracking-wider">
                {tr('learning_workspace_short', {}, 'Learning')}
              </span>
              <span className="ct-nlm-chip ct-nlm-num shrink-0">{notebooks.length}</span>
            </>
          )}
        </button>
      </div>

      {/* ── Daftar notebook ── */}
      <div
        className={`flex lg:flex-col items-center gap-1.5 max-lg:flex-row max-lg:overflow-x-auto max-lg:max-w-[52vw] lg:w-full ct-nlm-scroll lg:max-h-[38vh] lg:overflow-y-auto ${
          expanded ? 'lg:items-stretch' : ''
        }`}
      >
        {notebooks.map((nb) => {
          const active = String(nb.id) === String(activeId);
          return (
            <button
              key={nb.id}
              onClick={() => onSelect(nb.id)}
              title={nb.title}
              aria-label={nb.title}
              aria-current={active ? 'true' : undefined}
              data-testid="rail-notebook"
              data-active={active ? 'true' : 'false'}
              className={`ct-nlm-railbtn gap-2 ${expanded ? 'is-row' : ''} ${active ? 'is-active' : ''} ${
                expanded ? '' : 'justify-center'
              }`}
            >
              {/* Penanda aktif: batang kecil di kiri saat melebar (jelas, tanpa menggeser tata letak) */}
              {expanded && (
                <span
                  className={`w-[3px] self-stretch rounded-full shrink-0 ${
                    active ? 'bg-[var(--ct-primary)]' : 'bg-transparent'
                  }`}
                  aria-hidden
                />
              )}
              <Glyph nb={nb} />
              {expanded && (
                <span
                  className={`min-w-0 flex-1 truncate text-left text-[11.5px] ${
                    active ? 'font-bold text-[var(--ct-text)]' : 'font-medium'
                  }`}
                  data-testid="rail-notebook-title"
                >
                  {nb.title}
                </span>
              )}
            </button>
          );
        })}

        {/* Tambah notebook — ikut melebar agar tidak “menggantung” di kolom sempit */}
        <button
          onClick={onCreate}
          title={tr('learning_new_notebook_title', {}, 'New Notebook')}
          data-testid="rail-new-notebook"
          className={`ct-nlm-railbtn border border-dashed border-[var(--ct-nlm-line)] gap-2 ${
            expanded ? 'is-row' : ''
          }`}
        >
          <Plus className="w-4 h-4 shrink-0" />
          {expanded && (
            <span className="min-w-0 flex-1 truncate text-left text-[11.5px] font-bold">
              {tr('learning_new_notebook', {}, 'Notebook Baru')}
            </span>
          )}
        </button>
      </div>

      {/* Aksi notebook aktif (hanya saat melebar) */}
      {expanded && (
        <div className="hidden lg:flex items-center gap-1 w-full px-0.5" data-testid="rail-actions">
          <button
            onClick={onRename}
            className="ct-nlm-railbtn is-sm"
            title={tr('learning_rename_notebook', {}, 'Ganti nama notebook')}
          >
            <Pencil className="w-3.5 h-3.5" />
          </button>
          <button
            onClick={onDelete}
            className="ct-nlm-railbtn is-sm hover:text-rose-300!"
            title={tr('learning_delete', {}, 'Hapus')}
          >
            <Trash2 className="w-3.5 h-3.5" />
          </button>
          <span className="min-w-0 flex-1 truncate text-right text-[10px] text-[var(--ct-nlm-dim)]">
            {activeNb?.title || ''}
          </span>
        </div>
      )}

      <div className="hidden lg:block w-full h-px bg-[var(--ct-nlm-line-soft)] my-0.5" />

      <div className="hidden lg:block flex-1" />

      {/* Pemilih bahasa */}
      <button
        onClick={() => onLang(lang === 'id' ? 'en' : 'id')}
        className="ct-nlm-railbtn flex-col gap-0.5"
        title={tr('settings_language', {}, 'Bahasa')}
      >
        <Languages className="w-4 h-4 shrink-0" />
        <span className="text-[10px] font-black uppercase leading-none">{lang}</span>
      </button>
    </nav>
  );
};

export default NotebookRail;
