import axios from 'axios';
import type {
  Company,
  CompanyWithSync,
  CompanyCreate,
  CompanyUpdate,
  Tag,
  TagCreate,
  TagUpdate,
  Sync,
  IPOEntry,
} from '../types';

/** The server's error message (FastAPI's `detail`), or `fallback`. */
export function errorDetail(err: unknown, fallback: string): string {
  if (axios.isAxiosError(err)) {
    const detail = err.response?.data?.detail;
    if (typeof detail === 'string') return detail;
  }
  return fallback;
}

const api = axios.create({
  baseURL: '/api',
  headers: {
    'Content-Type': 'application/json',
  },
});

// Companies
export const getCompanies = async (): Promise<CompanyWithSync[]> => {
  const response = await api.get('/companies');
  return response.data;
};

export const getCompany = async (id: string): Promise<Company> => {
  const response = await api.get(`/companies/${id}`);
  return response.data;
};

export const createCompany = async (data: CompanyCreate): Promise<Company> => {
  const response = await api.post('/companies', data);
  return response.data;
};

export const updateCompany = async (
  id: string,
  data: CompanyUpdate
): Promise<Company> => {
  const response = await api.put(`/companies/${id}`, data);
  return response.data;
};

export const deleteCompany = async (id: string): Promise<void> => {
  await api.delete(`/companies/${id}`);
};

export const assignTags = async (
  companyId: string,
  tagIds: string[]
): Promise<Company> => {
  const response = await api.post(`/companies/${companyId}/tags`, {
    tag_ids: tagIds,
  });
  return response.data;
};

export const removeTag = async (
  companyId: string,
  tagId: string
): Promise<void> => {
  await api.delete(`/companies/${companyId}/tags/${tagId}`);
};

// Tags
export const getTags = async (): Promise<Tag[]> => {
  const response = await api.get('/tags');
  return response.data;
};

export const createTag = async (data: TagCreate): Promise<Tag> => {
  const response = await api.post('/tags', data);
  return response.data;
};

export const updateTag = async (id: string, data: TagUpdate): Promise<Tag> => {
  const response = await api.put(`/tags/${id}`, data);
  return response.data;
};

export const deleteTag = async (id: string): Promise<void> => {
  await api.delete(`/tags/${id}`);
};

// Syncs
export const triggerSync = async (companyId: string): Promise<Sync> => {
  const response = await api.post(`/companies/${companyId}/sync`);
  return response.data;
};

export const getCompanySyncs = async (companyId: string): Promise<Sync[]> => {
  const response = await api.get(`/companies/${companyId}/syncs`);
  return response.data;
};

export const getSync = async (syncId: string): Promise<Sync> => {
  const response = await api.get(`/syncs/${syncId}`);
  return response.data;
};

// Settings
export const getSettings = async (): Promise<Record<string, string>> => {
  const response = await api.get('/settings');
  return response.data;
};

export const updateSettings = async (
  settings: Record<string, string>
): Promise<Record<string, string>> => {
  const response = await api.put('/settings', settings);
  return response.data;
};

export const getLLMModels = async (): Promise<string[]> => {
  const response = await api.get('/settings/llm/models');
  return response.data;
};

export const checkLLMHealth = async (): Promise<{
  healthy: boolean;
  url: string;
}> => {
  const response = await api.get('/settings/llm/health');
  return response.data;
};

// Home
export interface UpcomingEarning {
  company_id: string;
  company_name: string;
  ticker: string | null;
  date: string;
  eps_estimate: number | null;
  quarter: number | null;
  year: number | null;
}

export interface HomeSummary {
  upcoming_earnings: UpcomingEarning[];
}

export interface NewsFeedArticle {
  id: string;
  first_seen_at: string;
  company_id: string;
  company_name: string;
  company_ticker: string | null;
  title: string;
  url: string;
  source: string | null;
  published_at: number;
  summary: string;
}

export const getNewsFeed = async (limit = 200, companyId?: string): Promise<NewsFeedArticle[]> => {
  const response = await api.get('/news/feed', { params: { limit, company_id: companyId } });
  return response.data;
};

export interface FinnhubStatus {
  configured: boolean;
  ok: boolean | null;
  error: string | null;
  at: string | null;
}

export const getFinnhubStatus = async (check = false): Promise<FinnhubStatus> => {
  const response = await api.get('/settings/finnhub/status', { params: { check } });
  return response.data;
};

export const syncStaleCompanies = async (): Promise<{ queued: number; message: string }> => {
  const response = await api.post('/syncs/sync-stale');
  return response.data;
};

export const getHomeSummary = async (): Promise<HomeSummary> => {
  const response = await api.get('/home/summary');
  return response.data;
};

// IPO Calendar
export const getIPOCalendar = async (): Promise<IPOEntry[]> => {
  const response = await api.get('/ipo/calendar');
  return response.data;
};

export const refreshIPOCalendar = async (): Promise<{ message: string }> => {
  const response = await api.post('/ipo/refresh');
  return response.data;
};

// Ad-hoc analysis
export interface AnalyzeRequest {
  ticker?: string;
  company_name?: string;
  notes?: string;
}

export interface AnalyzeResult {
  summary: string | null;
  sentiment: string | null;
  key_points: string[];
  risks: string[];
  prompt: string | null;
  stock_data: Record<string, unknown> | null;
}

export const runAnalysis = async (request: AnalyzeRequest): Promise<AnalyzeResult> => {
  const response = await api.post('/analyze', request);
  return response.data;
};

// Domain Discovery

export interface DiscoverCompany {
  ticker: string;
  name: string;
  cik: string;
  edgar_hits: number;
  status: 'pending' | 'fetching' | 'analyzing' | 'complete' | 'failed';
  stock_price: number | null;
  price_change: number | null;
  market_cap: string | null;
  industry: string | null;
  sentiment: string | null;
  summary: string | null;
}

export interface DiscoverSession {
  session_id: string;
  theme: string;
  status: 'starting' | 'expanding' | 'searching' | 'validating' | 'analyzing' | 'complete' | 'failed';
  error: string | null;
  keywords: string[];
  etf_hints: string[];
  rationale: string;
  companies: DiscoverCompany[];
  progress: { current: number; total: number };
  created_at: string;
}

export const startDiscover = async (theme: string): Promise<DiscoverSession> => {
  const response = await api.post('/discover', { theme });
  return response.data;
};

export const getDiscoverSession = async (sessionId: string): Promise<DiscoverSession> => {
  const response = await api.get(`/discover/${sessionId}`);
  return response.data;
};

export const analyzeDiscoverCompany = async (sessionId: string, ticker: string): Promise<void> => {
  await api.post(`/discover/${sessionId}/analyze/${ticker}`);
};

// Sync queue
export interface SyncQueueItem {
  company_id: string;
  company_name: string;
}

export const getSyncQueue = async (): Promise<SyncQueueItem[]> => {
  const response = await api.get('/syncs/queue/active');
  return response.data;
};
