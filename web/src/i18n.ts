import { apiGet } from './api/client';

const cache: Record<string, string> = {};

async function loadBundled(lang: 'id' | 'en') {
  try {
    const res = await fetch(`/i18n/messages.json`);
    if (!res.ok) return;
    const bundled = await res.json();
    Object.assign(cache, bundled[lang] || {});
  } catch {
    /* optional file */
  }
}

export async function loadMessages(lang: 'id' | 'en') {
  await loadBundled(lang);
  try {
    const data = await apiGet<{ messages: Record<string, string> }>(`/api/i18n?lang=${lang}`);
    Object.assign(cache, data.messages || {});
  } catch {
    /* offline */
  }
}

export function t(key: string, fallback: string): string {
  return cache[key] || fallback;
}
