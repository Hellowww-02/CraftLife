/**
 * galleryUtils.ts — logika murni tab `gallery` (fase A11).
 *
 * Album (sampul, jumlah foto, tanggal), navigasi keyboard lightbox, dan aksi
 * massal diuji di sini tanpa React/DOM.
 */

export interface PhotoRow {
  id: string;
  caption?: string;
  photoDate?: string;
  visibility?: string;
  ownerUserId?: string;
  uploaderName?: string;
  createdAt?: string;
}

export interface AlbumRow {
  id: string;
  name: string;
  scope?: string;
  photoIds?: string[];
  photoCount?: number;
  coverPhotoId?: string;
  hasCover?: boolean;
  createdAt?: string;
}

export type GalleryFilter = 'all' | 'shared' | 'private';

export function photoId(value: unknown): string {
  return value === null || value === undefined ? '' : String(value);
}

/** Foto milik user yang sedang login (foto pasangan tidak boleh diubah/dihapus). */
export function isOwnPhoto(photo: PhotoRow | undefined, userId: string): boolean {
  if (!photo) return false;
  const owner = photoId(photo.ownerUserId);
  return !owner || owner === photoId(userId);
}

/** Daftar foto setelah filter visibilitas + album dipilih. */
export function filterPhotos(
  photos: PhotoRow[] = [],
  albums: AlbumRow[] = [],
  filter: GalleryFilter = 'all',
  albumId = '',
): PhotoRow[] {
  let out = photos || [];
  if (filter !== 'all') out = out.filter((p) => (p.visibility || 'private') === filter);
  if (albumId) {
    const album = (albums || []).find((a) => photoId(a.id) === photoId(albumId));
    if (album) {
      const ids = new Set((album.photoIds || []).map(photoId));
      out = out.filter((p) => ids.has(photoId(p.id)));
    }
  }
  return out;
}

/** Album yang memuat sebuah foto (bila ada beberapa, ambil yang pertama). */
export function albumOf(photoIdValue: string, albums: AlbumRow[] = []): AlbumRow | undefined {
  const pid = photoId(photoIdValue);
  return (albums || []).find((a) => (a.photoIds || []).map(photoId).includes(pid));
}

/** Ringkasan album untuk bar galeri: sampul (pilihan user → foto pertama) + jumlah. */
export function albumSummary(albums: AlbumRow[] = [], photos: PhotoRow[] = []): Array<AlbumRow & { count: number; cover: string }> {
  const available = new Set((photos || []).map((p) => photoId(p.id)));
  return (albums || []).map((a) => {
    const ids = (a.photoIds || []).map(photoId);
    const cover = photoId(a.coverPhotoId || ids[0] || '');
    return {
      ...a,
      photoIds: ids,
      count: ids.length,
      // Sampul yang menunjuk foto terhapus tidak ditampilkan (server juga sudah
      // membersihkannya, ini jaring pengaman untuk data lama).
      cover: cover && available.has(cover) ? cover : '',
    };
  });
}

/** Label jumlah foto album. */
export function albumCountText(album: AlbumRow & { count?: number }): string {
  const n = typeof album.count === 'number' ? album.count : (album.photoIds || []).length;
  return `${n}`;
}

/** Tanggal album (YYYY-MM-DD) untuk keterangan di chip album. */
export function albumDate(album: AlbumRow): string {
  return String(album.createdAt || '').slice(0, 10);
}

/**
 * Foto berikutnya/sebelumnya untuk navigasi keyboard lightbox (← →).
 * `step` -1 = sebelumnya, +1 = berikutnya; memutar (wrap) di ujung daftar.
 */
export function neighborPhoto(photos: PhotoRow[] = [], currentId: string, step: number): PhotoRow | null {
  const list = photos || [];
  if (!list.length) return null;
  const idx = list.findIndex((p) => photoId(p.id) === photoId(currentId));
  if (idx < 0) return list[0] || null;
  const next = (idx + step + list.length) % list.length;
  return list[next] || null;
}

/** Peta keydown lightbox → aksi (`next`, `prev`, `close`, `zoom`). */
export function lightboxAction(key: string): 'next' | 'prev' | 'close' | 'zoom-in' | 'zoom-out' | '' {
  switch (key) {
    case 'ArrowRight':
    case 'ArrowDown':
    case ' ':
      return 'next';
    case 'ArrowLeft':
    case 'ArrowUp':
      return 'prev';
    case 'Escape':
      return 'close';
    case '+':
    case '=':
      return 'zoom-in';
    case '-':
    case '_':
      return 'zoom-out';
    default:
      return '';
  }
}

/** Id foto yang boleh dipilih di mode pilih-massal: hanya milik sendiri. */
export function selectableIds(photos: PhotoRow[] = [], userId: string): string[] {
  return (photos || []).filter((p) => isOwnPhoto(p, userId)).map((p) => photoId(p.id));
}

/** Orientasi tombol "pilih semua / batal pilih": true = semuanya sudah dipilih. */
export function allSelected(photos: PhotoRow[] = [], selected: Iterable<string>, userId: string): boolean {
  const ids = selectableIds(photos, userId);
  const set = new Set([...selected].map(photoId));
  return ids.length > 0 && ids.every((id) => set.has(id));
}
