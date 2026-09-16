/**
 * galleryParts.tsx — potongan UI galeri yang dipakai bersama (A11).
 *
 * Sebelumnya keempat komponen ini tinggal di dalam `LoveSpaceView.tsx`; sejak
 * tab galeri dipindah ke `LoveGalleryPanel.tsx`, keduanya perlu akses yang sama
 * (LoveSpaceView memakai `Modal` untuk dialog profil/tracking/upload dan
 * `PhotoThumb` untuk thumbnail kenangan). Satu sumber kebenaran = tidak ada
 * salinan yang bisa berbeda diam-diam.
 */
import React, { useCallback, useEffect, useState } from 'react';
import { CheckSquare, Square, X } from 'lucide-react';
import { studio } from '../../api/studio';

/** Thumbnail foto Love Space; URL ber-autentikasi diambil sekali per foto. */
export const PhotoThumb: React.FC<{ photo: any; onClick?: () => void; selected?: boolean; selectMode?: boolean }> = ({ photo, onClick, selected, selectMode }) => {
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

/** Gambar ukuran penuh untuk lightbox. */
export const ViewerImage: React.FC<{ photo: any }> = ({ photo }) => {
  const [url, setUrl] = useState('');
  useEffect(() => {
    let alive = true;
    if (photo?.id) studio.lovePhotoImage(photo.id).then((u) => { if (alive) setUrl(u); }).catch(() => setUrl(''));
    return () => { alive = false; };
  }, [photo?.id]);
  if (!url) return <div className="w-full h-full flex items-center justify-center text-slate-600 text-4xl">🖼️</div>;
  return <img src={url} alt="" className="w-full h-full object-contain" />;
};

/**
 * Penampil foto dengan zoom + pan (parity `_GalleryViewerDialog`).
 * A11: `zoomLevel` bisa dipaksa dari luar (tombol 1×/2× + keyboard +/-) melalui
 * prop `zoomSignal` — nilai berubah = zoom di-set (2 = 200%, 1 = 100%).
 */
export const ZoomableViewer: React.FC<{ photo: any; t: (k: string, fb: string) => string; zoomSignal?: number }> = ({ photo, t, zoomSignal }) => {
  const [url, setUrl] = useState('');
  const [zoom, setZoom] = useState(1.0);
  const [drag, setDrag] = useState<{ x: number; y: number } | null>(null);
  const [pos, setPos] = useState({ x: 0, y: 0 });
  const reset = useCallback(() => { setZoom(1); setPos({ x: 0, y: 0 }); }, []);
  useEffect(() => {
    let alive = true;
    if (photo?.id) studio.lovePhotoImage(photo.id).then((u) => { if (alive) setUrl(u); }).catch(() => setUrl(''));
    return () => { alive = false; reset(); };
  }, [photo?.id, reset]);
  useEffect(() => { if (zoomSignal) setZoom(Math.min(4.0, Math.max(0.25, zoomSignal))); }, [zoomSignal]);
  const clamp = (z: number) => Math.min(4.0, Math.max(0.25, z));
  const zoomIn = () => setZoom((z) => clamp(z * 1.25));
  const zoomOut = () => setZoom((z) => clamp(z / 1.25));
  const onMouseDown = (e: React.MouseEvent) => { setDrag({ x: e.clientX - pos.x, y: e.clientY - pos.y }); };
  const onMouseMove = (e: React.MouseEvent) => {
    if (drag) setPos({ x: e.clientX - drag.x, y: e.clientY - drag.y });
  };
  const onMouseUp = () => setDrag(null);
  return (
    <div className="space-y-2">
      {/* Toolbar (parity zoom bar) */}
      <div className="flex items-center gap-1.5">
        <button type="button" onClick={zoomOut} title={t('love_gallery_zoom_out_tip', 'Perkecil')}
          className="w-8 h-8 rounded-lg bg-slate-800 hover:bg-slate-700 border border-slate-700 flex items-center justify-center text-slate-200">➖</button>
        <button type="button" onClick={zoomIn} title={t('love_gallery_zoom_in_tip', 'Perbesar')}
          className="w-8 h-8 rounded-lg bg-slate-800 hover:bg-slate-700 border border-slate-700 flex items-center justify-center text-slate-200">➕</button>
        <button type="button" onClick={reset} title={t('love_gallery_zoom_reset_tip', 'Reset zoom')}
          className="w-8 h-8 rounded-lg bg-slate-800 hover:bg-slate-700 border border-slate-700 flex items-center justify-center text-slate-200">🔄</button>
        <span className="text-[11px] text-slate-500 px-1">{Math.round(zoom * 100)}%</span>
        <span className="text-[10px] text-slate-600 ml-auto hidden sm:inline">{t('love_gallery_zoom_hint', 'Tombol ← → ganti foto · Esc tutup')}</span>
      </div>
      <div className="rounded-xl overflow-hidden bg-slate-950 max-h-[55vh] flex items-center justify-center cursor-grab active:cursor-grabbing">
        {url ? (
          <div className="overflow-auto w-full h-full max-h-[55vh]" style={{ cursor: 'grab' }}>
            <img
              src={url} alt=""
              draggable={false}
              className="select-none object-contain transition-transform"
              style={{
                transform: `translate(${pos.x}px, ${pos.y}px) scale(${zoom})`,
                transition: drag ? 'none' : 'transform 0.15s ease-out',
                transformOrigin: 'center',
              }}
              onMouseDown={onMouseDown}
              onMouseMove={onMouseMove}
              onMouseUp={onMouseUp}
              onMouseLeave={onMouseUp}
            />
          </div>
        ) : (
          <div className="w-full h-full flex items-center justify-center text-slate-600 text-4xl">🖼️</div>
        )}
      </div>
    </div>
  );
};

/** Dialog generik Love Space (dipakai lightbox, pilih album, unggah, profil, tracking). */
export const Modal: React.FC<{ title: string; onClose: () => void; children: React.ReactNode; wide?: boolean }> = ({ title, onClose, children, wide }) => (
  <div className="ct-backdrop fixed inset-0 z-[120] flex items-center justify-center p-4" onClick={onClose}>
    <div
      className={`ct-dialog w-full ${wide ? 'max-w-3xl' : 'max-w-md'} p-5 space-y-3 max-h-[90vh] overflow-y-auto`}
      onClick={(e) => e.stopPropagation()}
    >
      <div className="flex items-center justify-between">
        <h3 className="font-bold text-sm text-slate-200">{title}</h3>
        <button onClick={onClose} className="ct-act"><X className="w-4 h-4" /></button>
      </div>
      {children}
    </div>
  </div>
);
