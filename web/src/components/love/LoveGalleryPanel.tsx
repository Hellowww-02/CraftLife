/**
 * LoveGalleryPanel.tsx — tab `gallery` Love Space (fase A11).
 *
 * Isi: bar album dengan **sampul + jumlah foto + tanggal**, aksi massal
 * (pilih → hapus / visibilitas / **pindahkan ke album**), grid foto, dan
 * lightbox dengan **navigasi keyboard ← → / Esc**, zoom, serta tombol **Simpan**
 * untuk keterangan (dulu nilai tersimpan diam-diam saat blur).
 */
import React, { useEffect, useMemo, useState } from 'react';
import { Camera, Eye, EyeOff, FolderOpen, Image as Images, Pencil, Star, Trash2 } from 'lucide-react';
import { Modal, PhotoThumb, ZoomableViewer } from './galleryParts';
import {
  albumDate,
  albumOf,
  albumSummary,
  allSelected,
  filterPhotos,
  isOwnPhoto,
  lightboxAction,
  neighborPhoto,
  selectableIds,
  type AlbumRow,
  type GalleryFilter,
  type PhotoRow,
} from './galleryUtils';

const inputCls = 'ct-input w-full px-2 py-1.5 rounded-lg text-slate-200 text-xs';
const btnRose = 'ct-btn ct-btn-rose ct-btn-sm';
const btnGhost = 'ct-btn ct-btn-secondary ct-btn-sm';
const btnDanger = 'ct-btn ct-btn-danger ct-btn-sm';

export interface LoveGalleryPanelProps {
  t: (k: string, fb: string) => string;
  trv: (k: string, vars: Record<string, string | number>, fb: string) => string;
  photos: PhotoRow[];
  albums: AlbumRow[];
  userId: string;
  coupleActive: boolean;
  today: string;
  onPickFiles: (files: FileList | null) => void;
  onDeletePhoto: (id: string) => void;
  onPhotoMeta: (id: string, body: Record<string, unknown>) => void;
  onBulk: (payload: { action: 'delete' | 'visibility' | 'move'; ids: string[]; albumId?: string; visibility?: string }) => void;
  onCreateAlbum: (name: string, scope: string) => void;
  onRenameAlbum: (id: string, name: string) => void;
  onDeleteAlbum: (id: string) => void;
  onAlbumPhoto: (albumId: string, photoId: string, mode: 'add' | 'move' | 'remove') => void;
  onAlbumCover: (albumId: string, photoId: string) => void;
  showToast: (kind: any, title: string, msg: string) => void;
}

export const LoveGalleryPanel: React.FC<LoveGalleryPanelProps> = ({
  t, trv, photos, albums, userId, coupleActive, today,
  onPickFiles, onDeletePhoto, onPhotoMeta, onBulk, onCreateAlbum, onRenameAlbum, onDeleteAlbum,
  onAlbumPhoto, onAlbumCover, showToast,
}) => {
  const fileRef = React.useRef<HTMLInputElement>(null);
  const [gFilter, setGFilter] = useState<GalleryFilter>('all');
  const [gAlbum, setGAlbum] = useState('');
  const [selectMode, setSelectMode] = useState(false);
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [viewer, setViewer] = useState<PhotoRow | null>(null);
  const [albumFor, setAlbumFor] = useState<PhotoRow | null>(null);
  const [albumTarget, setAlbumTarget] = useState('');
  const [bulkAlbum, setBulkAlbum] = useState('');
  const [meta, setMeta] = useState<{ caption: string; photoDate: string; visibility: string }>({ caption: '', photoDate: '', visibility: 'private' });
  const [zoomSignal, setZoomSignal] = useState(0);

  const summary = useMemo(() => albumSummary(albums, photos), [albums, photos]);
  const filtered = useMemo(() => filterPhotos(photos, albums, gFilter, gAlbum), [photos, albums, gFilter, gAlbum]);
  const own = (ph?: PhotoRow) => isOwnPhoto(ph, userId);

  // Buka lightbox: siapkan nilai form keterangan (disimpan hanya bila ditekan "Simpan").
  useEffect(() => {
    if (viewer) {
      setMeta({
        caption: viewer.caption || '',
        photoDate: viewer.photoDate || '',
        visibility: viewer.visibility || 'private',
      });
      setZoomSignal(0);
    }
  }, [viewer?.id]); // eslint-disable-line react-hooks/exhaustive-deps

  // Navigasi keyboard lightbox: ← → ganti foto, Esc tutup, +/- zoom.
  useEffect(() => {
    if (!viewer || typeof window === 'undefined') return;
    const onKey = (e: KeyboardEvent) => {
      const action = lightboxAction(e.key);
      if (!action) return;
      e.preventDefault();
      if (action === 'close') { setViewer(null); return; }
      if (action === 'zoom-in') { setZoomSignal(2); return; }
      if (action === 'zoom-out') { setZoomSignal(1); return; }
      const next = neighborPhoto(filtered, String(viewer.id), action === 'next' ? 1 : -1);
      if (next) setViewer(next);
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [viewer, filtered]);

  const toggleSelect = (pid: string) => {
    setSelected((s) => {
      const next = new Set(s);
      if (next.has(pid)) next.delete(pid); else next.add(pid);
      return next;
    });
  };

  const selectedIds = [...selected];

  return (
    <div className="space-y-4" data-testid="love-gallery-panel">
      {/* ── Toolbar ── */}
      <div className="flex flex-wrap items-center gap-2">
        <h3 className="font-bold text-sm text-slate-200 flex-1">{t('love_gallery_title', 'Galeri')}</h3>
        <select value={gFilter} onChange={(e) => setGFilter(e.target.value as GalleryFilter)} className={`${inputCls} w-auto`} data-testid="love-gallery-filter">
          <option value="all">{t('love_gallery_all', 'Semua')}</option>
          <option value="shared">{t('love_gallery_shared', 'Shared')}</option>
          <option value="private">{t('love_gallery_private', 'Private')}</option>
        </select>
        <button type="button" onClick={() => fileRef.current?.click()} className={btnRose}>
          <Camera className="w-3.5 h-3.5 inline mr-1" />{t('love_gallery_upload', 'Unggah Foto')}
        </button>
        <input
          ref={fileRef} type="file" accept="image/*" multiple title={t('love_gallery_pick_multi', 'Pilih Foto')}
          className="hidden" data-testid="love-gallery-file"
          onChange={(e) => { onPickFiles(e.target.files); e.target.value = ''; }}
        />
        <button
          type="button"
          onClick={() => { setSelectMode((s) => !s); setSelected(new Set()); }}
          className={selectMode ? btnRose : btnGhost}
          data-testid="love-gallery-select-mode"
          title={t('love_gallery_select_mode', 'Pilih beberapa')}
        >
          <Images className="w-3.5 h-3.5 inline mr-1" />{t('love_gallery_select', 'Pilih')}
        </button>
      </div>

      {/* ── Bar album (sampul + jumlah + tanggal) ── */}
      <div className="ct-panel flex flex-wrap items-center gap-2 p-3 rounded-2xl">
        <span className="text-[11px] text-slate-400 font-bold">{t('love_album_title', 'Album')}</span>
        <select value={gAlbum} onChange={(e) => setGAlbum(e.target.value)} className={`${inputCls} w-auto`} data-testid="love-gallery-album-select">
          <option value="">{t('love_album_all', 'Semua Album')}</option>
          {summary.map((a) => (
            <option key={a.id} value={a.id}>
              {a.name} · {a.count} {t('love_gallery_photos_short', 'foto')}
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
            onCreateAlbum(name, scope);
          }}
        >{t('love_album_new', 'Baru')}</button>
        <button
          type="button"
          disabled={!gAlbum}
          className={btnGhost}
          onClick={() => {
            const cur = summary.find((a) => String(a.id) === String(gAlbum));
            const name = window.prompt(t('love_album_rename', 'Ubah nama album'), cur?.name || '')?.trim();
            if (!name || !cur) return;
            onRenameAlbum(String(cur.id), name);
          }}
        >{t('love_album_rename', 'Ganti Nama')}</button>
        <button
          type="button"
          disabled={!gAlbum}
          className={btnDanger}
          onClick={() => {
            const cur = summary.find((a) => String(a.id) === String(gAlbum));
            if (!cur) return;
            if (!window.confirm(trv('love_album_delete_confirm', { name: cur.name }, `Hapus album "${cur.name}"?`))) return;
            onDeleteAlbum(String(cur.id));
            setGAlbum('');
          }}
        >{t('love_album_delete', 'Hapus Album')}</button>

        {/* Chip album: sampul + jumlah + tanggal */}
        {summary.length > 0 && (
          <div className="flex flex-wrap gap-2 w-full pt-1" data-testid="love-gallery-album-chips">
            {summary.map((a) => (
              <button
                key={a.id}
                type="button"
                onClick={() => setGAlbum((cur) => (String(cur) === String(a.id) ? '' : String(a.id)))}
                className={`flex items-center gap-2 px-2 py-1 rounded-xl border text-left ${String(gAlbum) === String(a.id) ? 'border-rose-500/60 bg-rose-950/30' : 'border-slate-800 bg-slate-900/60 hover:border-rose-500/30'}`}
                data-testid="love-gallery-album-chip"
              >
                <span className="w-8 h-8 rounded-lg overflow-hidden bg-slate-950 border border-slate-800 flex items-center justify-center text-slate-600">
                  {a.cover ? <PhotoThumb photo={{ id: a.cover }} /> : <span className="text-xs">📁</span>}
                </span>
                <span className="leading-tight">
                  <span className="block text-[11px] text-slate-200 font-semibold max-w-[10rem] truncate">{a.name}</span>
                  <span className="block text-[10px] text-slate-500">
                    {trv('love_gallery_album_count', { n: a.count }, `${a.count} foto`)}
                    {albumDate(a) ? ` · ${albumDate(a)}` : ''}
                    {a.hasCover ? ' · ⭐' : ''}
                  </span>
                </span>
              </button>
            ))}
          </div>
        )}
      </div>

      {/* ── Aksi massal ── */}
      {selectMode && (
        <div className="flex flex-wrap items-center gap-2 p-3 bg-rose-950/30 border border-rose-500/20 rounded-2xl" data-testid="love-gallery-bulk">
          <span className="text-xs text-rose-300 font-bold flex-1">{trv('love_gallery_selected_count', { n: selected.size }, `${selected.size} foto dipilih`)}</span>
          <button
            type="button"
            className={btnGhost}
            onClick={() => {
              const ids = selectableIds(filtered, userId);
              setSelected(allSelected(filtered, selected, userId) ? new Set() : new Set(ids));
            }}
          >
            {allSelected(filtered, selected, userId) ? t('love_gallery_deselect_all', 'Batal Pilih Semua') : t('love_gallery_select_all', 'Pilih Semua')}
          </button>
          <select value={bulkAlbum} onChange={(e) => setBulkAlbum(e.target.value)} className={`${inputCls} w-auto`} data-testid="love-gallery-bulk-album">
            <option value="">{t('love_gallery_bulk_move', 'Pindahkan ke album')}</option>
            {summary.map((a) => (<option key={a.id} value={a.id}>{a.name}</option>))}
          </select>
          <button
            type="button"
            className={btnGhost}
            disabled={!bulkAlbum || !selected.size}
            data-testid="love-gallery-bulk-move-go"
            onClick={() => { onBulk({ action: 'move', ids: selectedIds, albumId: bulkAlbum }); setSelected(new Set()); }}
          >
            {t('love_gallery_bulk_move_go', 'Pindahkan')}
          </button>
          <button type="button" className={btnDanger} onClick={() => onBulk({ action: 'delete', ids: selectedIds })} data-testid="love-gallery-bulk-delete">
            {t('love_gallery_bulk_delete', 'Hapus Terpilih')}
          </button>
          <button type="button" className={btnGhost} onClick={() => { onBulk({ action: 'visibility', ids: selectedIds, visibility: 'private' }); setSelected(new Set()); }}>
            {t('love_gallery_bulk_private', 'Jadikan Private')}
          </button>
          <button
            type="button"
            className={btnGhost}
            title={coupleActive ? '' : t('love_album_shared_need_couple', 'Butuh couple aktif')}
            onClick={() => { onBulk({ action: 'visibility', ids: selectedIds, visibility: 'shared' }); setSelected(new Set()); }}
          >
            {t('love_gallery_bulk_shared', 'Jadikan Shared')}
          </button>
        </div>
      )}

      <div className="flex items-center justify-between text-[11px] text-slate-500">
        <span>{trv('love_gallery_count', { n: filtered.length, total: photos.length }, `${filtered.length} foto`)}</span>
        <span className="italic">{t('love_gallery_privacy_hint', 'Foto private hanya kamu yang lihat.')}</span>
      </div>

      {/* ── Grid ── */}
      {filtered.length ? (
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-3">
          {filtered.map((ph) => {
            const pid = String(ph.id);
            const mine = own(ph);
            const inAlbum = albumOf(pid, albums);
            return (
              <div key={pid} className="space-y-1">
                <PhotoThumb
                  photo={ph}
                  selectMode={selectMode}
                  selected={selected.has(pid)}
                  onClick={() => {
                    if (selectMode) {
                      if (!mine) return;
                      toggleSelect(pid);
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
                {mine && !selectMode && (
                  <div className="flex items-center gap-1 px-0.5">
                    <button
                      type="button"
                      className="p-1 rounded bg-slate-800 hover:bg-slate-700 text-slate-300"
                      title={t('love_gallery_toggle_tip', 'Ubah visibilitas')}
                      onClick={() => onPhotoMeta(pid, { caption: ph.caption, photoDate: ph.photoDate, visibility: ph.visibility === 'shared' ? 'private' : 'shared' })}
                    >{ph.visibility === 'shared' ? <Eye className="w-3 h-3" /> : <EyeOff className="w-3 h-3" />}</button>
                    <button type="button" className="p-1 rounded bg-slate-800 hover:bg-slate-700 text-slate-300" title={t('love_gallery_edit', 'Edit')} onClick={() => setViewer(ph)}><Pencil className="w-3 h-3" /></button>
                    <button
                      type="button"
                      className="p-1 rounded bg-slate-800 hover:bg-slate-700 text-slate-300"
                      title={t('love_album_title', 'Album')}
                      onClick={() => { setAlbumFor(ph); setAlbumTarget(inAlbum?.id ? String(inAlbum.id) : (summary[0] ? String(summary[0].id) : '')); }}
                    ><FolderOpen className="w-3 h-3" /></button>
                    <button
                      type="button"
                      className="p-1 rounded bg-slate-800 hover:bg-slate-700 text-slate-300"
                      title={t('love_gallery_album_cover', 'Jadikan cover album')}
                      data-testid="love-gallery-set-cover"
                      onClick={() => {
                        const target = inAlbum?.id ? String(inAlbum.id) : (summary[0] ? String(summary[0].id) : '');
                        if (!target) {
                          showToast('info', t('msg_error', 'Error'), t('love_gallery_cover_need_album', 'Buat album dulu untuk menandai sampul.'));
                          return;
                        }
                        onAlbumCover(target, pid);
                      }}
                    ><Star className="w-3 h-3" /></button>
                    <button
                      type="button"
                      className="ct-act text-rose-300"
                      title={t('love_delete', 'Hapus')}
                      onClick={() => { if (window.confirm(t('love_gallery_delete_confirm', 'Hapus foto ini?'))) onDeletePhoto(pid); }}
                    ><Trash2 className="w-3 h-3" /></button>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      ) : (
        <div className="p-8 text-center text-xs text-slate-500 bg-slate-900/50 border border-slate-800 rounded-2xl" data-testid="love-gallery-empty">
          {photos.length
            ? t('love_gallery_no_match', 'Tidak ada foto pada filter ini.')
            : t('love_gallery_empty', 'Belum ada foto. Unggah momen pertama kalian!')}
        </div>
      )}

      {/* ── Lightbox (keyboard ← → / Esc, zoom, Simpan keterangan) ── */}
      {viewer && (
        <Modal title={viewer.caption || t('love_gallery_untitled', 'Foto')} onClose={() => setViewer(null)} wide>
          <ZoomableViewer photo={viewer} t={t} zoomSignal={zoomSignal} />
          {own(viewer) && (
            <div className="space-y-2" data-testid="love-gallery-viewer-meta">
              <div className="grid grid-cols-1 md:grid-cols-3 gap-2">
                <input
                  value={meta.caption}
                  onChange={(e) => setMeta((m) => ({ ...m, caption: e.target.value }))}
                  className={inputCls}
                  placeholder={t('love_gallery_caption_ph', 'Keterangan foto…')}
                />
                <input
                  type="date"
                  value={meta.photoDate}
                  onChange={(e) => setMeta((m) => ({ ...m, photoDate: e.target.value }))}
                  className={inputCls}
                />
                <select
                  value={meta.visibility}
                  onChange={(e) => setMeta((m) => ({ ...m, visibility: e.target.value }))}
                  className={inputCls}
                >
                  <option value="private">🔒 {t('love_gallery_private', 'Private')}</option>
                  <option value="shared">💞 {t('love_gallery_shared', 'Shared')}</option>
                </select>
              </div>
              <div className="flex flex-wrap items-center gap-2">
                <button
                  type="button"
                  className={btnRose}
                  data-testid="love-gallery-save-meta"
                  onClick={() => {
                    onPhotoMeta(String(viewer.id), meta);
                    setViewer(null);
                  }}
                >
                  {t('love_gallery_save_meta', 'Simpan keterangan')}
                </button>
                <select value={albumTarget} onChange={(e) => setAlbumTarget(e.target.value)} className={`${inputCls} w-auto`} data-testid="love-gallery-viewer-album">
                  <option value="">{t('love_album_choose', 'Pilih Album')}</option>
                  {summary.map((a) => (<option key={a.id} value={a.id}>{a.name}</option>))}
                </select>
                <button
                  type="button"
                  className={btnGhost}
                  disabled={!albumTarget}
                  data-testid="love-gallery-viewer-album-go"
                  onClick={() => { onAlbumPhoto(albumTarget, String(viewer.id), 'add'); setAlbumTarget(''); }}
                >
                  {t('love_gallery_add_to_album', 'Simpan ke album')}
                </button>
              </div>
            </div>
          )}
          <div className="flex justify-between items-center">
            <span className="text-[11px] text-slate-500">
              {trv('love_gallery_meta', { date: viewer.photoDate || '—', uploader: viewer.uploaderName || '—' }, '')}
            </span>
            <div className="flex items-center gap-2">
              <button
                type="button"
                className={btnGhost}
                data-testid="love-gallery-prev"
                onClick={() => { const prev = neighborPhoto(filtered, String(viewer.id), -1); if (prev) setViewer(prev); }}
              >←</button>
              <button
                type="button"
                className={btnGhost}
                data-testid="love-gallery-next"
                onClick={() => { const next = neighborPhoto(filtered, String(viewer.id), 1); if (next) setViewer(next); }}
              >→</button>
              {own(viewer) && (
                <button
                  type="button"
                  className={btnDanger}
                  onClick={() => {
                    if (!window.confirm(t('love_gallery_delete_confirm', 'Hapus foto ini?'))) return;
                    onDeletePhoto(String(viewer.id));
                    setViewer(null);
                  }}
                >{t('love_delete', 'Hapus')}</button>
              )}
            </div>
          </div>
        </Modal>
      )}

      {/* ── Pilih album untuk satu foto ── */}
      {albumFor && (
        <Modal title={t('love_album_choose', 'Pilih Album')} onClose={() => setAlbumFor(null)}>
          {summary.length ? (
            <>
              <select value={albumTarget} onChange={(e) => setAlbumTarget(e.target.value)} className={inputCls}>
                {summary.map((a) => (
                  <option key={a.id} value={a.id}>{a.name} · {a.scope === 'shared' ? t('love_album_shared', 'Shared') : t('love_album_personal', 'Personal')}</option>
                ))}
              </select>
              <div className="flex gap-2 flex-wrap">
                <button
                  type="button"
                  className={btnRose}
                  onClick={() => { if (albumTarget) { onAlbumPhoto(albumTarget, String(albumFor.id), 'add'); setAlbumFor(null); } }}
                >{t('love_album_copy_to', 'Tambahkan ke album')}</button>
                <button
                  type="button"
                  className={btnGhost}
                  onClick={() => {
                    const src = albumOf(String(albumFor.id), albums);
                    if (!albumTarget) return;
                    onAlbumPhoto(albumTarget, String(albumFor.id), src ? 'move' : 'add');
                    setAlbumFor(null);
                  }}
                >{t('love_album_move_to', 'Pindahkan')}</button>
                <button
                  type="button"
                  className={btnGhost}
                  onClick={() => {
                    const src = albumOf(String(albumFor.id), albums);
                    if (src) onAlbumPhoto(String(src.id), String(albumFor.id), 'remove');
                    setAlbumFor(null);
                  }}
                >{t('love_album_remove', 'Keluarkan dari album')}</button>
              </div>
              <p className="text-[10px] text-slate-500">{trv('love_album_picked', { n: summary.length }, `${summary.length} album tersedia`)}</p>
            </>
          ) : (
            <p className="text-xs text-slate-500">{t('love_album_no_albums', 'Belum ada album.')}</p>
          )}
        </Modal>
      )}
    </div>
  );
};
