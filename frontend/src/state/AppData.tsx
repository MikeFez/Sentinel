import { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState, type ReactNode } from 'react';
import { getCompanies, getTags, getSettings } from '../api/client';
import type { CompanyWithSync, Tag } from '../types';

export interface Toast {
  id: number;
  kind: 'info' | 'success' | 'error';
  text: string;
}

interface AppData {
  companies: CompanyWithSync[];
  tags: Tag[];
  stalenessHours: number;
  loaded: boolean;
  /** Re-fetch companies and tags (after an add/edit/delete or a sync). */
  refresh: () => Promise<void>;
  toast: (text: string, kind?: Toast['kind']) => void;
  toasts: Toast[];
  dismissToast: (id: number) => void;
}

const Ctx = createContext<AppData | null>(null);

// Poll quickly while anything is syncing so progress shows up everywhere, slowly otherwise.
const FAST_MS = 3000;
const SLOW_MS = 60000;

export function AppDataProvider({ children }: { children: ReactNode }) {
  const [companies, setCompanies] = useState<CompanyWithSync[]>([]);
  const [tags, setTags] = useState<Tag[]>([]);
  const [stalenessHours, setStalenessHours] = useState(24);
  const [loaded, setLoaded] = useState(false);
  const [toasts, setToasts] = useState<Toast[]>([]);
  const nextId = useRef(1);

  const toast = useCallback((text: string, kind: Toast['kind'] = 'info') => {
    const id = nextId.current++;
    setToasts((t) => [...t, { id, kind, text }]);
    setTimeout(() => setToasts((t) => t.filter((x) => x.id !== id)), kind === 'error' ? 8000 : 4000);
  }, []);
  const dismissToast = useCallback((id: number) => setToasts((t) => t.filter((x) => x.id !== id)), []);

  const refresh = useCallback(async () => {
    try {
      const [c, t, s] = await Promise.all([getCompanies(), getTags(), getSettings()]);
      setCompanies(c);
      setTags(t);
      const h = parseFloat(s.staleness_hours);
      if (h > 0) setStalenessHours(h);
    } catch (err) {
      console.error('Failed to load companies:', err);
    } finally {
      setLoaded(true);
    }
  }, []);

  const anySyncing = companies.some((c) => c.is_syncing);
  const wasSyncing = useRef<Set<string>>(new Set());

  // Tell the user when a sync they were waiting on finishes or fails.
  useEffect(() => {
    const now = new Set(companies.filter((c) => c.is_syncing).map((c) => c.id));
    for (const id of wasSyncing.current) {
      if (now.has(id)) continue;
      const c = companies.find((x) => x.id === id);
      if (!c) continue;
      if (c.sync_error) toast(`${c.name}: sync failed — ${c.sync_error}`, 'error');
      else if (c.latest_sync?.error) toast(`${c.name} updated, but ${c.latest_sync.error.replace(/^AI analysis unavailable: /, 'the AI analysis failed: ')}`, 'error');
      else toast(`${c.name} updated`, 'success');
    }
    wasSyncing.current = now;
  }, [companies, toast]);

  useEffect(() => {
    refresh();
  }, [refresh]);

  useEffect(() => {
    const t = setInterval(refresh, anySyncing ? FAST_MS : SLOW_MS);
    return () => clearInterval(t);
  }, [refresh, anySyncing]);

  const value = useMemo(
    () => ({ companies, tags, stalenessHours, loaded, refresh, toast, toasts, dismissToast }),
    [companies, tags, stalenessHours, loaded, refresh, toast, toasts, dismissToast],
  );
  return <Ctx.Provider value={value}>{children}</Ctx.Provider>;
}

export function useAppData(): AppData {
  const v = useContext(Ctx);
  if (!v) throw new Error('useAppData outside AppDataProvider');
  return v;
}

/** Price alert that the latest price has crossed, if any. */
export function triggeredAlert(c: CompanyWithSync): { kind: 'above' | 'below'; level: number; price: number } | null {
  const price = c.latest_sync?.stock_price;
  if (price == null) return null;
  if (c.alert_above != null && price >= c.alert_above) return { kind: 'above', level: c.alert_above, price };
  if (c.alert_below != null && price <= c.alert_below) return { kind: 'below', level: c.alert_below, price };
  return null;
}
