import { useCallback, useEffect, useMemo, useRef, useState, type ReactNode } from 'react';
import { AppDataContext as Ctx, type ConfirmOptions, type NewsSeen, type Toast } from './useAppData';
import { readLastVisit, readSeenByCompany, writeSeen } from '../lib/newsSeen';
import { getCompanies, getTags, getSettings } from '../api/client';
import type { CompanyWithSync, Tag } from '../types';

// Poll quickly while anything is syncing so progress shows up everywhere, slowly otherwise.
const FAST_MS = 3000;
const SLOW_MS = 60000;

export function AppDataProvider({ children }: { children: ReactNode }) {
  const [companies, setCompanies] = useState<CompanyWithSync[]>([]);
  const [tags, setTags] = useState<Tag[]>([]);
  const [stalenessHours, setStalenessHours] = useState(24);
  const [driftPercent, setDriftPercent] = useState(15);
  const [loaded, setLoaded] = useState(false);
  const [toasts, setToasts] = useState<Toast[]>([]);
  const nextId = useRef(1);

  const toast = useCallback((text: string, kind: Toast['kind'] = 'info') => {
    const id = nextId.current++;
    setToasts((t) => [...t, { id, kind, text }]);
    setTimeout(() => setToasts((t) => t.filter((x) => x.id !== id)), kind === 'error' ? 8000 : 4000);
  }, []);
  const dismissToast = useCallback((id: number) => setToasts((t) => t.filter((x) => x.id !== id)), []);

  // One confirm dialog at a time; AppLayout renders it
  const [pendingConfirm, setPendingConfirm] = useState<ConfirmOptions | null>(null);
  const resolveConfirm = useRef<((ok: boolean) => void) | null>(null);
  const confirm = useCallback((options: ConfirmOptions) => {
    resolveConfirm.current?.(false);
    setPendingConfirm(options);
    return new Promise<boolean>((resolve) => { resolveConfirm.current = resolve; });
  }, []);
  const settleConfirm = useCallback((ok: boolean) => {
    resolveConfirm.current?.(ok);
    resolveConfirm.current = null;
    setPendingConfirm(null);
  }, []);

  const [newsSeen, setNewsSeen] = useState<NewsSeen>(() => {
    // First run: start counting from now, so existing news isn't all "unread"
    if (!readLastVisit()) writeSeen(null);
    return { lastVisit: readLastVisit(), byCompany: readSeenByCompany() };
  });
  const markNewsSeen = useCallback((companyId: string | null) => {
    writeSeen(companyId);
    setNewsSeen({ lastVisit: readLastVisit(), byCompany: readSeenByCompany() });
  }, []);

  const refresh = useCallback(async () => {
    try {
      const [c, t, s] = await Promise.all([getCompanies(), getTags(), getSettings()]);
      setCompanies(c);
      setTags(t);
      const h = parseFloat(s.staleness_hours);
      if (h > 0) setStalenessHours(h);
      const d = parseFloat(s.analysis_drift_percent);
      if (d > 0) setDriftPercent(d);
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
    () => ({
      companies, tags, stalenessHours, driftPercent, loaded, refresh, toast, toasts, dismissToast,
      confirm, pendingConfirm, settleConfirm, newsSeen, markNewsSeen,
    }),
    [companies, tags, stalenessHours, driftPercent, loaded, refresh, toast, toasts, dismissToast, confirm, pendingConfirm, settleConfirm, newsSeen, markNewsSeen],
  );
  return <Ctx.Provider value={value}>{children}</Ctx.Provider>;
}
