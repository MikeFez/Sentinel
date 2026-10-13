import { createContext, useContext } from 'react';
import type { CompanyWithSync, Tag } from '../types';

export interface Toast {
  id: number;
  kind: 'info' | 'success' | 'error';
  text: string;
}

export interface ConfirmOptions {
  title: string;
  message: string;
  confirmLabel?: string;
  danger?: boolean;
}

export interface NewsSeen {
  /** When the News page was last left (ms); 0 if never. */
  lastVisit: number;
  /** When each company's News tab was last opened (ms). */
  byCompany: Record<string, number>;
}

interface AppData {
  companies: CompanyWithSync[];
  tags: Tag[];
  stalenessHours: number;
  /** Price move (%) since an analysis at which it's flagged as out of date (and re-run). */
  driftPercent: number;
  loaded: boolean;
  /** Re-fetch companies and tags (after an add/edit/delete or a sync). */
  refresh: () => Promise<void>;
  toast: (text: string, kind?: Toast['kind']) => void;
  toasts: Toast[];
  dismissToast: (id: number) => void;
  /** Ask the user to confirm in an in-app dialog; resolves true if they did. */
  confirm: (options: ConfirmOptions) => Promise<boolean>;
  pendingConfirm: ConfirmOptions | null;
  settleConfirm: (ok: boolean) => void;
  newsSeen: NewsSeen;
  /** Mark all news (null) or one company's news as read. */
  markNewsSeen: (companyId: string | null) => void;
}

export const AppDataContext = createContext<AppData | null>(null);

export function useAppData(): AppData {
  const v = useContext(AppDataContext);
  if (!v) throw new Error('useAppData outside AppDataProvider');
  return v;
}
