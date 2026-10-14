import { useCallback, useSyncExternalStore } from 'react';

import { readList, writeList } from '@/lib/storage';

function subscribe(callback: () => void): () => void {
  window.addEventListener('local-list-change', callback);
  window.addEventListener('storage', callback); // other tabs
  return () => {
    window.removeEventListener('local-list-change', callback);
    window.removeEventListener('storage', callback);
  };
}

const snapshots = new Map<string, { raw: string; value: string[] }>();

function getSnapshot(key: string): string[] {
  const value = readList(key);
  const raw = JSON.stringify(value);
  const cached = snapshots.get(key);
  if (cached && cached.raw === raw) return cached.value; // stable reference for React
  snapshots.set(key, { raw, value });
  return value;
}

/** A list of strings persisted in localStorage and shared live between components/tabs. */
export function useLocalList(key: string, max = 50) {
  const items = useSyncExternalStore(
    subscribe,
    () => getSnapshot(key),
    () => [],
  );

  const add = useCallback(
    (value: string, options: { toFront?: boolean } = {}) => {
      const current = readList(key).filter((v) => v !== value);
      const next = options.toFront ? [value, ...current] : [...current, value];
      writeList(key, next.slice(0, max));
    },
    [key, max],
  );

  const remove = useCallback(
    (value: string) => {
      writeList(
        key,
        readList(key).filter((v) => v !== value),
      );
    },
    [key],
  );

  const clear = useCallback(() => {
    writeList(key, []);
  }, [key]);

  return { items, add, remove, clear, has: (value: string) => items.includes(value) };
}

export const GUEST_WISHLIST_KEY = 'anvika:wishlist:v1';
export const RECENTLY_VIEWED_KEY = 'anvika:recently-viewed:v1';
