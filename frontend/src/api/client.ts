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

// Peers
export interface Peer {
  ticker: string;
  name: string | null;
  industry: string | null;
  price: number | null;
  change: number | null;
  tracked_company_id: string | null;
}

export const getPeers = async (companyId: string): Promise<Peer[]> => {
  const response = await api.get(`/companies/${companyId}/peers`);
  return response.data;
};

// Export / import
export type ExportFile = Record<string, unknown> & { format: string; version: number };

export interface ImportSummary {
  created: string[];
  updated: string[];
  tags_created: number;
  settings_changed: number;
}

export const exportData = async (): Promise<ExportFile> => {
  const response = await api.get('/export');
  return response.data;
};

export const importData = async (data: ExportFile, includeSettings: boolean, dryRun: boolean): Promise<ImportSummary> => {
  const response = await api.post('/import', { data, include_settings: includeSettings, dry_run: dryRun });
  return response.data;
};

// Scorecard
export interface ScoreSummary {
  calls: number;
  graded: number;
  hits: number;
  hit_rate: number | null;
  avg_return: Record<'bullish' | 'bearish' | 'neutral' | 'mixed', number | null>;
  pending: number;
}

export interface ScoredCall {
  company_id: string;
  name: string;
  at: string;
  sentiment: string;
  price: number;
  later_price: number | null;
  later_at: string | null;
  return: number | null;
  hit: boolean | null;
  model: string | null;
}

export interface Scorecard {
  horizon_days: number;
  overall: ScoreSummary;
  by_company: (ScoreSummary & { company_id: string; name: string; ticker: string | null })[];
  by_model: (ScoreSummary & { model: string })[];
  recent: ScoredCall[];
}

export const getScorecard = async (horizon: number, companyId?: string): Promise<Scorecard> => {
  const response = await api.get('/scorecard', { params: { horizon, company_id: companyId } });
  return response.data;
};

// Filings, stories, themes
export interface FilingSummary {
  id: string;
  form: string;
  filed_on: string;
  items: string | null;
  url: string;
  summary: string | null;
  new_risks: string[] | null;
}

export const getFilings = async (companyId: string): Promise<FilingSummary[]> => {
  const response = await api.get(`/companies/${companyId}/filings`);
  return response.data;
};

export interface Story {
  id: string;
  company_id: string;
  company_name: string;
  company_ticker: string | null;
  title: string;
  summary: string | null;
  material: boolean;
  themes: string[];
  first_seen_at: string;
  last_seen_at: string;
  articles: { id: string; title: string; url: string; source: string | null; published_at: number | null }[];
}

export const getStories = async (companyId?: string, materialOnly = false): Promise<Story[]> => {
  const response = await api.get('/news/stories', { params: { company_id: companyId, material_only: materialOnly, limit: 200 } });
  return response.data;
};

export interface ThemeTrend {
  theme: string;
  weekly: number[];
  total: number;
  rising: boolean;
}

export const getThemes = async (companyId: string): Promise<ThemeTrend[]> => {
  const response = await api.get(`/companies/${companyId}/themes`);
  return response.data;
};

// Activity (observability)
export type ActivityKind = 'llm' | 'finnhub' | 'sec' | 'sync' | 'job';

export interface ActivityOperation {
  kind: ActivityKind;
  name: string;
  count: number;
  errors: number;
  avg_ms: number;
  p95_ms: number | null;
  tokens: number;
  last_error: string | null;
  last_at: string;
}

export interface ActivityRunning {
  kind: ActivityKind;
  name: string;
  company_id: string | null;
  company_name: string | null;
  started: string;
  seconds: number;
}

export interface ActivitySummary {
  hours: number;
  since: string;
  bucket_seconds: number;
  totals: Record<ActivityKind, { count: number; errors: number; busy_seconds: number }>;
  llm_tokens: { prompt: number; completion: number };
  series: Record<ActivityKind, number[]>;
  operations: ActivityOperation[];
  running: ActivityRunning[];
  api: { method: string; route: string; count: number; errors: number; avg_ms: number; max_ms: number }[];
}

export interface ActivityEvent {
  id: string;
  at: string;
  kind: ActivityKind;
  name: string;
  status: 'ok' | 'error';
  duration_ms: number;
  company_id: string | null;
  company_name: string | null;
  prompt_tokens: number | null;
  completion_tokens: number | null;
  detail: string | null;
}

export const getActivitySummary = async (hours: number): Promise<ActivitySummary> => {
  const response = await api.get('/activity/summary', { params: { hours } });
  return response.data;
};

export const getActivityEvents = async (kind: string | null, errorsOnly: boolean): Promise<ActivityEvent[]> => {
  const response = await api.get('/activity/events', { params: { kind: kind || undefined, errors_only: errorsOnly, limit: 150 } });
  return response.data;
};
