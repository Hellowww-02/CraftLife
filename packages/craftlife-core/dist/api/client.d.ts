export declare function apiBase(): string;
export declare function authToken(): string | null;
export declare function apiGet<T = any>(path: string): Promise<T>;
export declare function apiPost<T = any>(path: string, body: unknown): Promise<T>;
/** GET binary (download attachment); return blob + nama file dari header. */
export declare function apiGetBlob(path: string, fallbackName?: string): Promise<{
    blob: Blob;
    name: string;
}>;
/** Target upload yang didukung server (parity QFileDialog PyQt). */
export type UploadTarget = 'love_photo' | 'profile_photo' | 'reminder_sound' | 'music' | 'learning_source' | 'note_attachment' | 'playlist_icon';
/**
 * Upload file browser (QWebEngineView membuka native file dialog untuk <input type=file>).
 * Server menyimpan bytes ke lokasi yang sama seperti PyQt (BLOB SQLite / folder musik lokal).
 */
export declare function apiUploadFile<T = any>(target: UploadTarget, file: File, extra?: Record<string, unknown>): Promise<T>;
/** Tautan absolut + token sesi (endpoint unduhan menerima ?token=). */
export declare function downloadUrl(path: string): string;
/** Simpan Blob jadi berkas di komputer (anchor WAJIB masuk DOM dulu). */
export declare function saveBlobToFile(blob: Blob, name: string): void;
/**
 * Unduh endpoint server sebagai berkas (jalur attachment).
 * Dipakai untuk ekspor yang SUDAH mengirim `Content-Disposition: attachment`
 * (nutrisi, lirik .lrc/.txt, lampiran) — nama berkas ditentukan server.
 */
export declare function downloadApiFile(path: string, fallbackName?: string): boolean;
/** Info folder unduhan (dipakai UI untuk menampilkan lokasi berkas). */
export declare function downloadTargetInfo(): Promise<{
    dir: string;
    lastName: string;
    lastPath: string;
    active: boolean;
}>;
/** Buka folder unduhan CraftLife di file explorer (Windows/macOS/Linux). */
export declare function openDownloadsFolder(path?: string): Promise<boolean>;
export type DownloadEvent = {
    status: 'start' | 'done' | 'failed';
    name: string;
    path: string;
};
/**
 * Daftarkan jembatan dari shell: `window.craftlifeDownloadEvent` dipanggil
 * web_shell.py saat unduhan mulai/selesai/gagal. Return fungsi pembatal.
 */
export declare function onDownloadEvent(handler: (e: DownloadEvent) => void): () => void;
/**
 * Simpan berkas BUATAN KLIEN (JSON/txt) ke komputer lewat jalur attachment server:
 * isi dikirim ke `/api/system/stage-file`, lalu diunduh sebagai HTTP attachment
 * (nama + tipe dari server). Fallback ke blob bila staging tidak tersedia.
 */
export declare function saveFileToComputer(opts: {
    name: string;
    mime?: string;
    text?: string;
    base64?: string;
    blob?: Blob;
}): Promise<'server' | 'blob'>;
//# sourceMappingURL=client.d.ts.map