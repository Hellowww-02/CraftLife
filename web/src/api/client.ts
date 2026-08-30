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

/** Target upload yang didukung server (parity QFileDialog PyQt). */
export type UploadTarget = 'love_photo' | 'profile_photo' | 'reminder_sound' | 'music' | 'learning_source';

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
