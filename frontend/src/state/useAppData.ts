import { createContext, useContext } from 'react';
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

export const AppDataContext = createContext<AppData | null>(null);

export function useAppData(): AppData {
  const v = useContext(AppDataContext);
  if (!v) throw new Error('useAppData outside AppDataProvider');
  return v;
}
