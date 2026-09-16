export function apiBase(): string {
  const params = new URLSearchParams(window.location.search);
  const fromEnv = (import.meta as any).env?.VITE_API_BASE as string | undefined;
  if (fromEnv) return fromEnv.replace(/\/$/, '');
  if (params.get('api')) return params.get('api')!.replace(/\/$/, '');
  return '';
}

export function authToken(): string | null {
  const params = new URLSearchParams(window.location.search);
  const q = params.get('token');
  if (q) {
    try {
      sessionStorage.setItem('craftlife_token', q);
    } catch {
      /* ignore */
    }
    return q;
  }
  try {
    return sessionStorage.getItem('craftlife_token');
  } catch {
    return null;
  }
}

export async function apiGet<T = any>(path: string): Promise<T> {
  const token = authToken();
  const headers: Record<string, string> = { Accept: 'application/json' };
  if (token) headers.Authorization = `Bearer ${token}`;
  const res = await fetch(`${apiBase()}${path}`, { headers, credentials: 'include' });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error((data && (data.error || data.msg)) || `HTTP ${res.status}`);
  return data;
}

export async function apiPost<T = any>(path: string, body: unknown): Promise<T> {
  const token = authToken();
  const headers: Record<string, string> = {
    Accept: 'application/json',
    'Content-Type': 'application/json',
  };
  if (token) headers.Authorization = `Bearer ${token}`;
  const res = await fetch(`${apiBase()}${path}`, {
    method: 'POST',
    headers,
    credentials: 'include',
    body: JSON.stringify(body ?? {}),
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error((data && (data.error || data.msg)) || `HTTP ${res.status}`);
  return data;
}

/** GET binary (download attachment); return blob + nama file dari header. */
export async function apiGetBlob(path: string, fallbackName = 'attachment'): Promise<{ blob: Blob; name: string }> {
  const token = authToken();
  const headers: Record<string, string> = { Accept: '*/*' };
  if (token) headers.Authorization = `Bearer ${token}`;
  const res = await fetch(`${apiBase()}${path}`, { headers, credentials: 'include' });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  const blob = await res.blob();
  const disp = res.headers.get('Content-Disposition') || '';
  const m = /filename\*?=(?:UTF-8'')?"?([^";]+)"?/i.exec(disp);
  const name = m ? decodeURIComponent(m[1]) : fallbackName;
  return { blob, name };
}

/** Target upload yang didukung server (parity QFileDialog PyQt). */
export type UploadTarget = 'love_photo' | 'profile_photo' | 'reminder_sound' | 'music' | 'learning_source' | 'note_attachment' | 'playlist_icon';

function fileToBase64(file: File): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onerror = () => reject(new Error('read_failed'));
    reader.onload = () => {
      const result = String(reader.result || '');
      const comma = result.indexOf(',');
      resolve(comma >= 0 ? result.slice(comma + 1) : result);
    };
    reader.readAsDataURL(file);
  });
}

/**
 * Upload file browser (QWebEngineView membuka native file dialog untuk <input type=file>).
 * Server menyimpan bytes ke lokasi yang sama seperti PyQt (BLOB SQLite / folder musik lokal).
 */
export async function apiUploadFile<T = any>(
  target: UploadTarget,
  file: File,
  extra?: Record<string, unknown>,
): Promise<T> {
  const dataBase64 = await fileToBase64(file);
  return apiPost<T>('/api/upload/file', {
    target,
    name: file.name,
    mime: file.type || '',
    dataBase64,
    ...(extra || {}),
  });
}

// ─────────────────────────────────────────────────────────────────────────────
// A03.5 — UNDUHAN KE KOMPUTER (kanonik, dipakai SEMUA fitur ekspor)
//
// Sebelumnya tiap fitur membuat <a download> sendiri dengan blob + a.click()
// TANPA menyisipkan anchor ke DOM, dan shell Qt WebEngine tidak punya handler
// `downloadRequested` → unduhan dibuang diam-diam (berkas tidak pernah muncul
// di komputer). Sekarang:
//   • `saveBlobToFile()`  — untuk berkas yang dibuat di sisi klien (JSON/txt);
//   • `downloadApiFile()` — navigasi ke endpoint ATTACHMENT server (nama file
//     dari Content-Disposition, streaming, paling andal di Qt WebEngine);
//   • `openDownloadsFolder()` + `downloadTargetInfo()` — lokasi berkas ke user.
// Shell (web_shell.py) memanggil `window.craftlifeDownloadEvent(status, name, path)`
// setelah berkas benar-benar tersimpan, sehingga UI bisa memberi tahu lokasinya.
// ─────────────────────────────────────────────────────────────────────────────

/** Tautan absolut + token sesi (endpoint unduhan menerima ?token=). */
export function downloadUrl(path: string): string {
  const token = authToken();
  const sep = path.includes('?') ? '&' : '?';
  const withToken = token && !path.includes('token=') ? `${path}${sep}token=${encodeURIComponent(token)}` : path;
  return `${apiBase()}${withToken}`;
}

/** Simpan Blob jadi berkas di komputer (anchor WAJIB masuk DOM dulu). */
export function saveBlobToFile(blob: Blob, name: string): void {
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = name || 'craftlife-download';
  a.rel = 'noopener';
  a.style.display = 'none';
  document.body.appendChild(a);
  a.click();
  setTimeout(() => {
    a.remove();
    URL.revokeObjectURL(url);
  }, 4000);
}

/**
 * Unduh endpoint server sebagai berkas (jalur attachment).
 * Dipakai untuk ekspor yang SUDAH mengirim `Content-Disposition: attachment`
 * (nutrisi, lirik .lrc/.txt, lampiran) — nama berkas ditentukan server.
 */
export function downloadApiFile(path: string, fallbackName = 'craftlife-download'): boolean {
  try {
    const a = document.createElement('a');
    a.href = downloadUrl(path);
    a.rel = 'noopener';
    a.download = fallbackName; // dipakai Qt bila server tidak mengirim nama berkas
    a.style.display = 'none';
    document.body.appendChild(a);
    a.click();
    setTimeout(() => a.remove(), 4000);
    return true;
  } catch {
    return false;
  }
}

/** Info folder unduhan (dipakai UI untuk menampilkan lokasi berkas). */
export async function downloadTargetInfo(): Promise<{ dir: string; lastName: string; lastPath: string; active: boolean }> {
  try {
    const d = await apiGet<any>('/api/system/downloads-info');
    return {
      dir: d?.dir || '', lastName: d?.lastName || '', lastPath: d?.lastPath || '',
      active: !!d?.active,
    };
  } catch {
    return { dir: '', lastName: '', lastPath: '', active: false };
  }
}

/** Buka folder unduhan CraftLife di file explorer (Windows/macOS/Linux). */
export async function openDownloadsFolder(path = ''): Promise<boolean> {
  try {
    const res = await apiPost<any>('/api/system/open-downloads', path ? { path } : {});
    return !!res?.ok;
  } catch {
    return false;
  }
}

export type DownloadEvent = { status: 'start' | 'done' | 'failed'; name: string; path: string };

/**
 * Daftarkan jembatan dari shell: `window.craftlifeDownloadEvent` dipanggil
 * web_shell.py saat unduhan mulai/selesai/gagal. Return fungsi pembatal.
 */
export function onDownloadEvent(handler: (e: DownloadEvent) => void): () => void {
  const w = window as any;
  const previous = w.craftlifeDownloadEvent;
  w.craftlifeDownloadEvent = (status: string, name: string, path: string) =>
    handler({ status: (status as DownloadEvent['status']) || 'done', name: name || '', path: path || '' });
  return () => {
    if (previous) w.craftlifeDownloadEvent = previous;
    else { try { delete w.craftlifeDownloadEvent; } catch { /* ignore */ } }
  };
}

/**
 * Simpan berkas BUATAN KLIEN (JSON/txt) ke komputer lewat jalur attachment server:
 * isi dikirim ke `/api/system/stage-file`, lalu diunduh sebagai HTTP attachment
 * (nama + tipe dari server). Fallback ke blob bila staging tidak tersedia.
 */
export async function saveFileToComputer(opts: {
  name: string; mime?: string; text?: string; base64?: string; blob?: Blob;
}): Promise<'server' | 'blob'> {
  try {
    let b64 = opts.base64;
    if (!b64 && opts.blob) b64 = await blobToBase64(opts.blob);
    const staged = await apiPost<any>('/api/system/stage-file', {
      name: opts.name, mime: opts.mime || 'application/octet-stream',
      base64: b64, text: opts.text,
    });
    if (staged?.ok && staged.id) {
      downloadApiFile(`/api/system/download-file?id=${encodeURIComponent(staged.id)}`, opts.name);
      return 'server';
    }
  } catch {
    /* fallback blob di bawah */
  }
  const blob = opts.blob
    || new Blob([opts.text ?? ''], { type: (opts.mime || 'text/plain') + ';charset=utf-8' });
  saveBlobToFile(blob, opts.name);
  return 'blob';
}

function blobToBase64(blob: Blob): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onerror = () => reject(new Error('read_failed'));
    reader.onload = () => {
      const res = String(reader.result || '');
      resolve(res.includes(',') ? res.split(',', 2)[1] : res);
    };
    reader.readAsDataURL(blob);
  });
}
