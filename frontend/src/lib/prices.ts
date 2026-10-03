import type { Company, CompanyWithSync } from '../types';
import { parseTime } from './format';

/** The freshest price we have: the quote refresh or the last sync, whichever is newer. */
export function livePrice(c: CompanyWithSync | Company): { price: number; change: number | null; at: string } | null {
  const sync = 'latest_sync' in c ? c.latest_sync : null;
  const fromSync = sync?.stock_price != null ? { price: sync.stock_price, change: sync.price_change, at: sync.synced_at } : null;
  const fromQuote = c.quote_price != null && c.quote_at ? { price: c.quote_price, change: c.quote_change, at: c.quote_at } : null;
  if (fromQuote && (!fromSync || parseTime(fromQuote.at) >= parseTime(fromSync.at))) return fromQuote;
  return fromSync;
}

/** Price alert that the latest price has crossed, if any. */
export function triggeredAlert(c: CompanyWithSync): { kind: 'above' | 'below'; level: number; price: number } | null {
  const price = livePrice(c)?.price;
  if (price == null) return null;
  if (c.alert_above != null && price >= c.alert_above) return { kind: 'above', level: c.alert_above, price };
  if (c.alert_below != null && price <= c.alert_below) return { kind: 'below', level: c.alert_below, price };
  return null;
}
