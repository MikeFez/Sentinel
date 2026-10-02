export type CompanyStatus = 'public' | 'pre_ipo' | 'private' | 'acquired';
export type SyncStatus = 'pending' | 'syncing' | 'completed' | 'failed';
export type SentimentType = 'bullish' | 'bearish' | 'neutral' | 'mixed';

export interface Tag {
  id: string;
  name: string;
  color: string;
}

export interface Company {
  id: string;
  name: string;
  ticker: string | null;
  status: CompanyStatus;
  description: string | null;
  website: string | null;
  industry: string | null;
  created_at: string;
  updated_at: string | null;
  tags: Tag[];
  alert_above: number | null;
  alert_below: number | null;
  shares_owned: number | null;
}

export interface SyncSummary {
  id: string;
  synced_at: string;
  stock_price: number | null;
  price_change: number | null;
  ai_sentiment: SentimentType | null;
  status: SyncStatus;
}

export interface CompanyWithSync extends Company {
  latest_sync: SyncSummary | null;
  is_stale: boolean;
  is_syncing: boolean;
  has_alert: boolean;
}

export interface AnalystRatings {
  buy?: number;
  hold?: number;
  sell?: number;
  strongBuy?: number;
  strongSell?: number;
}

export interface EarningsDate {
  date: string;
  epsActual?: number;
  epsEstimate?: number;
  quarter?: number;
  year?: number;
}

export interface InsiderTransaction {
  name: string;
  share: number;
  change: number;
  filingDate: string;
  transactionDate: string;
  transactionPrice?: number;
}

export interface Financials {
  marketCapitalization?: number;
  peRatio?: number;
  pbRatio?: number;
  dividendYield?: number;
  beta?: number;
  eps?: number;
  revenuePerShare?: number;
  profitMargin?: number;
  operatingMargin?: number;
}

export interface Sync {
  id: string;
  company_id: string;
  synced_at: string;
  stock_price: number | null;
  price_change: number | null;
  market_cap: string | null;
  pe_ratio: number | null;
  volume: number | null;
  fifty_two_wk_hi: number | null;
  fifty_two_wk_lo: number | null;
  raw_news: NewsArticle[] | null;
  analyst_ratings: AnalystRatings | null;
  earnings_dates: EarningsDate[] | null;
  insider_transactions: InsiderTransaction[] | null;
  financials: Financials | null;
  ai_summary: string | null;
  ai_sentiment: SentimentType | null;
  llm_prompt: string | null;
  status: SyncStatus;
}

export interface NewsArticle {
  title: string;
  url: string;
  published_at: number;
  source: string | null;
  summary?: string;
}

export interface CompanyCreate {
  name: string;
  ticker?: string;
  status: CompanyStatus;
  description?: string;
  website?: string;
  shares_owned?: number;
  alert_above?: number;
  alert_below?: number;
}

export interface CompanyUpdate {
  name?: string;
  ticker?: string;
  status?: CompanyStatus;
  description?: string;
  website?: string;
  shares_owned?: number;
  alert_above?: number;
  alert_below?: number;
}

export interface TagCreate {
  name: string;
  color?: string;
}

export interface TagUpdate {
  name?: string;
  color?: string;
}

export interface IPOEntry {
  id: string;
  name: string;
  symbol: string | null;
  date: string;
  price_range_low: number | null;
  price_range_high: number | null;
  shares: number | null;
  exchange: string | null;
  status: string | null;
  total_shares_value: number | null;
  debut_price: number | null;
  current_price: number | null;
  fetched_at: string;
}
