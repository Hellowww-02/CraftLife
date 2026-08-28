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
