import { getApiPlatformAdapter } from './platform';
export function apiBase() {
    // Adapter platform diperiksa PALING AWAL. Di React Native `window.location`
    // tidak ada, jadi baris URLSearchParams di bawah akan melempar TypeError
    // sebelum sempat fallback — urutannya bukan sekadar preferensi.
    const injected = getApiPlatformAdapter()?.apiBase();
    if (injected)
        return injected.replace(/\/$/, '');
    const params = new URLSearchParams(window.location.search);
    const fromEnv = import.meta.env?.VITE_API_BASE;
    if (fromEnv)
        return fromEnv.replace(/\/$/, '');
    if (params.get('api'))
        return params.get('api').replace(/\/$/, '');
    return '';
}
export function authToken() {
    const injected = getApiPlatformAdapter()?.authToken();
    if (injected !== undefined)
        return injected;
    // G9: token tidak lagi dibaca dari query string. Token di URL dokumen bocor
    // lewat riwayat navigasi, log, dan header Referer. Shell desktop menyuntik
    // token ke sessionStorage sebelum bundle ini berjalan (web_shell.py), dan
    // login web menyimpannya sendiri dari respons /api/login.
    try {
        return sessionStorage.getItem('craftlife_token');
    }
    catch {
        return null;
    }
}
export async function apiGet(path) {
    const token = authToken();
    const headers = { Accept: 'application/json' };
    if (token)
        headers.Authorization = `Bearer ${token}`;
    const res = await fetch(`${apiBase()}${path}`, { headers, credentials: 'include' });
    const data = await res.json().catch(() => ({}));
    if (!res.ok)
        throw new Error((data && (data.error || data.msg)) || `HTTP ${res.status}`);
    return data;
}
export async function apiPost(path, body) {
    const token = authToken();
    const headers = {
        Accept: 'application/json',
        'Content-Type': 'application/json',
    };
    if (token)
        headers.Authorization = `Bearer ${token}`;
    const res = await fetch(`${apiBase()}${path}`, {
        method: 'POST',
        headers,
        credentials: 'include',
        body: JSON.stringify(body ?? {}),
    });
    const data = await res.json().catch(() => ({}));
    if (!res.ok)
        throw new Error((data && (data.error || data.msg)) || `HTTP ${res.status}`);
    return data;
}
/** GET binary (download attachment); return blob + nama file dari header. */
export async function apiGetBlob(path, fallbackName = 'attachment') {
    const token = authToken();
    const headers = { Accept: '*/*' };
    if (token)
        headers.Authorization = `Bearer ${token}`;
    const res = await fetch(`${apiBase()}${path}`, { headers, credentials: 'include' });
    if (!res.ok)
        throw new Error(`HTTP ${res.status}`);
    const blob = await res.blob();
    const disp = res.headers.get('Content-Disposition') || '';
    const m = /filename\*?=(?:UTF-8'')?"?([^";]+)"?/i.exec(disp);
    const name = m ? decodeURIComponent(m[1]) : fallbackName;
    return { blob, name };
}
function fileToBase64(file) {
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
export async function apiUploadFile(target, file, extra) {
    const dataBase64 = await fileToBase64(file);
    return apiPost('/api/upload/file', {
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
export function downloadUrl(path) {
    const token = authToken();
    const sep = path.includes('?') ? '&' : '?';
    const withToken = token && !path.includes('token=') ? `${path}${sep}token=${encodeURIComponent(token)}` : path;
    return `${apiBase()}${withToken}`;
}
/** Simpan Blob jadi berkas di komputer (anchor WAJIB masuk DOM dulu). */
export function saveBlobToFile(blob, name) {
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
export function downloadApiFile(path, fallbackName = 'craftlife-download') {
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
    }
    catch {
        return false;
    }
}
/** Info folder unduhan (dipakai UI untuk menampilkan lokasi berkas). */
export async function downloadTargetInfo() {
    try {
        const d = await apiGet('/api/system/downloads-info');
        return {
            dir: d?.dir || '', lastName: d?.lastName || '', lastPath: d?.lastPath || '',
            active: !!d?.active,
        };
    }
    catch {
        return { dir: '', lastName: '', lastPath: '', active: false };
    }
}
/** Buka folder unduhan CraftLife di file explorer (Windows/macOS/Linux). */
export async function openDownloadsFolder(path = '') {
    try {
        const res = await apiPost('/api/system/open-downloads', path ? { path } : {});
        return !!res?.ok;
    }
    catch {
        return false;
    }
}
/**
 * Daftarkan jembatan dari shell: `window.craftlifeDownloadEvent` dipanggil
 * web_shell.py saat unduhan mulai/selesai/gagal. Return fungsi pembatal.
 */
export function onDownloadEvent(handler) {
    const w = window;
    const previous = w.craftlifeDownloadEvent;
    w.craftlifeDownloadEvent = (status, name, path) => handler({ status: status || 'done', name: name || '', path: path || '' });
    return () => {
        if (previous)
            w.craftlifeDownloadEvent = previous;
        else {
            try {
                delete w.craftlifeDownloadEvent;
            }
            catch { /* ignore */ }
        }
    };
}
/**
 * Simpan berkas BUATAN KLIEN (JSON/txt) ke komputer lewat jalur attachment server:
 * isi dikirim ke `/api/system/stage-file`, lalu diunduh sebagai HTTP attachment
 * (nama + tipe dari server). Fallback ke blob bila staging tidak tersedia.
 */
export async function saveFileToComputer(opts) {
    try {
        let b64 = opts.base64;
        if (!b64 && opts.blob)
            b64 = await blobToBase64(opts.blob);
        const staged = await apiPost('/api/system/stage-file', {
            name: opts.name, mime: opts.mime || 'application/octet-stream',
            base64: b64, text: opts.text,
        });
        if (staged?.ok && staged.id) {
            downloadApiFile(`/api/system/download-file?id=${encodeURIComponent(staged.id)}`, opts.name);
            return 'server';
        }
    }
    catch {
        /* fallback blob di bawah */
    }
    const blob = opts.blob
        || new Blob([opts.text ?? ''], { type: (opts.mime || 'text/plain') + ';charset=utf-8' });
    saveBlobToFile(blob, opts.name);
    return 'blob';
}
function blobToBase64(blob) {
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
//# sourceMappingURL=client.js.map