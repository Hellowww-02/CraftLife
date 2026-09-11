/**
 * NoteAttachments.tsx — panel lampiran catatan (P54).
 *
 * Menampilkan daftar file yang dilampirkan ke note aktif (metadata dari
 * snapshot `noteAttachments`): thumbnail untuk gambar, chip untuk file lain.
 * Aksi: buka (tab baru), unduh, hapus (file + baris DB via endpoint server).
 */
import React from 'react';
import { t } from '../../i18n';
import { Paperclip, Trash2, FileText, FileDown } from 'lucide-react';
import { apiBase } from '../../api/client';
import { NoteAttachment } from '../../types';

/** URL serve file lampiran (owner-checked di server). */
export const attachmentUrl = (id: string): string =>
  `${apiBase()}/api/notes/attachment/file?id=${encodeURIComponent(id)}`;

const fmtSize = (n: number): string => {
  if (!n) return '';
  if (n < 1024) return `${n} B`;
  if (n < 1024 * 1024) return `${(n / 1024).toFixed(0)} KB`;
  return `${(n / (1024 * 1024)).toFixed(1)} MB`;
};

interface NoteAttachmentsProps {
  attachments: NoteAttachment[];
  onDelete: (id: string) => void;
}

export const NoteAttachments: React.FC<NoteAttachmentsProps> = ({ attachments, onDelete }) => {
  if (!attachments.length) return null;
  return (
    <div className="rounded-xl bg-slate-950/60 border border-slate-800 p-3 space-y-2">
      <div className="flex items-center gap-1.5 text-[11px] font-bold text-slate-400">
        <Paperclip className="w-3.5 h-3.5" />
        {t('notes_attach_file', '📎 Lampirkan File')} ({attachments.length})
      </div>
      <div className="flex flex-wrap gap-2">
        {attachments.map((a) => (
          <div
            key={a.id}
            className="flex items-center gap-2 rounded-lg bg-slate-900 border border-slate-700 pl-2 pr-1 py-1 max-w-full"
          >
            {a.kind === 'image' ? (
              <img src={attachmentUrl(a.id)} alt={a.fileName} className="w-8 h-8 rounded object-cover shrink-0" />
            ) : (
              <FileText className="w-4 h-4 text-cyan-300 shrink-0" />
            )}
            <div className="min-w-0">
              <a
                href={attachmentUrl(a.id)}
                target="_blank"
                rel="noreferrer"
                title={a.fileName}
                className="block text-[11px] font-bold text-slate-200 hover:text-cyan-300 truncate max-w-[140px]"
              >
                {a.fileName}
              </a>
              <span className="text-[9px] text-slate-500">{fmtSize(a.size)}</span>
            </div>
            <a
              href={attachmentUrl(a.id)}
              download={a.fileName}
              title={t('notes_attach_download', 'Unduh')}
              className="p-1 rounded hover:bg-slate-800 text-slate-400 hover:text-cyan-300"
            >
              <FileDown className="w-3.5 h-3.5" />
            </a>
            <button
              type="button"
              title={t('notes_attach_delete_confirm', 'Hapus lampiran ini? (File juga dihapus dari disk)')}
              onClick={() => {
                if (window.confirm(t('notes_attach_delete_confirm', 'Hapus lampiran ini? (File juga dihapus dari disk)'))) {
                  onDelete(a.id);
                }
              }}
              className="p-1 rounded hover:bg-rose-950 text-slate-400 hover:text-rose-300"
            >
              <Trash2 className="w-3.5 h-3.5" />
            </button>
          </div>
        ))}
      </div>
    </div>
  );
};
