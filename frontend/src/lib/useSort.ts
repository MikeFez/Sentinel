import { useState } from 'react';

export type SortDir = 'asc' | 'desc';
export interface SortState { key: string; dir: SortDir }

function read(storageKey: string, fallback: SortState): SortState {
  try {
    const v = JSON.parse(localStorage.getItem(storageKey) ?? 'null');
    if (v && typeof v.key === 'string' && (v.dir === 'asc' || v.dir === 'desc')) return v;
  } catch {
    /* blocked storage: use the default */
  }
  return fallback;
}

/**
 * Sortable table state, remembered per browser. `values` maps a column key to the value to sort by;
 * nulls always sort last. Clicking a column sorts it (text ascending, numbers descending first),
 * clicking it again flips the direction.
 */
export function useSort<T>(storageKey: string, fallback: SortState, values: Record<string, (row: T) => string | number | null | undefined>) {
  const [sort, setSort] = useState(() => read(storageKey, fallback));

  const toggle = (key: string, numeric: boolean) => {
    const next: SortState = sort.key === key
      ? { key, dir: sort.dir === 'asc' ? 'desc' : 'asc' }
      : { key, dir: numeric ? 'desc' : 'asc' };
    setSort(next);
    try {
      localStorage.setItem(storageKey, JSON.stringify(next));
    } catch {
      /* not remembered */
    }
  };

  const apply = (rows: T[]) => {
    const get = values[sort.key];
    if (!get) return rows;
    const sign = sort.dir === 'asc' ? 1 : -1;
    return [...rows].sort((a, b) => {
      const x = get(a), y = get(b);
      if (x == null || y == null) return x == null ? (y == null ? 0 : 1) : -1;
      return sign * (typeof x === 'string' ? x.localeCompare(String(y)) : x - (y as number));
    });
  };

  return { sort, toggle, apply };
}
