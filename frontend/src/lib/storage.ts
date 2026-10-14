/**
 * Safe localStorage helpers for NON-sensitive conveniences only (guest wishlist slugs, recently
 * viewed). Storage can be unavailable (private mode, blocked cookies), so every call is guarded
 * and the app works without it. Never store tokens or personal data here.
 */

export function readList(key: string): string[] {
  try {
    const raw = window.localStorage.getItem(key);
    const parsed: unknown = raw ? JSON.parse(raw) : [];
    return Array.isArray(parsed) ? parsed.filter((v): v is string => typeof v === 'string') : [];
  } catch {
    return [];
  }
}

export function writeList(key: string, values: string[]): void {
  try {
    window.localStorage.setItem(key, JSON.stringify(values));
    window.dispatchEvent(new CustomEvent('local-list-change', { detail: key }));
  } catch {
    /* storage unavailable — feature degrades gracefully */
  }
}
