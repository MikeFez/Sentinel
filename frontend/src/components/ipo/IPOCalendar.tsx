import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { RefreshCw, Plus, Check } from 'lucide-react';
import { getIPOCalendar, refreshIPOCalendar, createCompany } from '../../api/client';
import { useAppData } from '../../state/useAppData';
import type { IPOEntry } from '../../types';
import { ago, daysUntil, inDays, money, shortDate } from '../../lib/format';
import './IPOCalendar.css';
import { useTitle } from '../../lib/useTitle';

type View = 'upcoming' | 'recent' | 'withdrawn';

const compact = (n: number | null, prefix = '') => {
  if (!n) return '—';
  if (n >= 1e9) return `${prefix}${(n / 1e9).toFixed(2)}B`;
  if (n >= 1e6) return `${prefix}${(n / 1e6).toFixed(n >= 1e8 ? 0 : 1)}M`;
  if (n >= 1e3) return `${prefix}${(n / 1e3).toFixed(0)}K`;
  return `${prefix}${n}`;
};

const priceRange = (low: number | null, high: number | null) =>
  low && high && low !== high ? `${money(low)}–${money(high)}` : low || high ? money(low || high) : '—';

/** Lock-up periods usually end 180 days after the IPO. */
const lockupEnd = (date: string) => {
  const d = new Date(`${date}T00:00:00`);
  d.setDate(d.getDate() + 180);
  return d.toISOString().slice(0, 10);
};

function IPOCalendar() {
  useTitle('IPOs');
  const { companies, refresh, toast } = useAppData();
  const [ipos, setIpos] = useState<IPOEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [view, setView] = useState<View>('upcoming');

  const load = async () => {
    try {
      setIpos(await getIPOCalendar());
    } catch {
      toast('Could not load the IPO calendar', 'error');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const reload = async () => {
    setRefreshing(true);
    try {
      await refreshIPOCalendar();
      await load();
    } catch {
      toast('Could not refresh the IPO calendar from Finnhub', 'error');
    } finally {
      setRefreshing(false);
    }
  };

  const trackedFor = (ipo: IPOEntry) =>
    companies.find((c) => (ipo.symbol && c.ticker?.toUpperCase() === ipo.symbol.toUpperCase()) || c.name.toLowerCase() === ipo.name.toLowerCase());

  const track = async (ipo: IPOEntry) => {
    const listed = ['listed', 'priced'].includes(ipo.status?.toLowerCase() ?? '') || daysUntil(ipo.date) < 0;
    try {
      await createCompany({ name: ipo.name, ticker: ipo.symbol || null, status: listed ? 'public' : 'pre_ipo' });
      await refresh();
      toast(`Now tracking ${ipo.name}`, 'success');
    } catch {
      toast(`Could not add ${ipo.name}`, 'error');
    }
  };

  const withdrawn = (i: IPOEntry) => i.status?.toLowerCase() === 'withdrawn';
  const groups: Record<View, IPOEntry[]> = {
    upcoming: ipos.filter((i) => !withdrawn(i) && daysUntil(i.date) >= 0).sort((a, b) => a.date.localeCompare(b.date)),
    recent: ipos.filter((i) => !withdrawn(i) && daysUntil(i.date) < 0).sort((a, b) => b.date.localeCompare(a.date)),
    withdrawn: ipos.filter(withdrawn).sort((a, b) => b.date.localeCompare(a.date)),
  };
  const rows = groups[view];
  const fetchedAt = ipos.reduce<string | null>((latest, i) => (!latest || i.fetched_at > latest ? i.fetched_at : latest), null);

  const TrackCell = ({ ipo }: { ipo: IPOEntry }) => {
    const tracked = trackedFor(ipo);
    return tracked ? (
      <Link to={`/companies/${tracked.id}`} className="ipo-tracked"><Check size={13} /> Tracking</Link>
    ) : (
      <button className="btn btn-ghost btn-sm" onClick={() => track(ipo)}><Plus size={13} /> Track</button>
    );
  };

  const Company = ({ ipo }: { ipo: IPOEntry }) => (
    <span className="ipo-company">
      <span>{ipo.name}</span>
      {ipo.symbol && <span className="mono muted ipo-symbol">{ipo.symbol}</span>}
    </span>
  );

  return (
    <div className="page">
      <header className="page-head">
        <div>
          <h1>IPOs</h1>
          <p className="muted">From Finnhub's IPO calendar{fetchedAt ? ` · fetched ${ago(fetchedAt)}` : ''}</p>
        </div>
        <button className="btn btn-secondary" onClick={reload} disabled={refreshing}>
          <RefreshCw size={15} className={refreshing ? 'spinning' : ''} /> {refreshing ? 'Refreshing…' : 'Refresh'}
        </button>
      </header>

      <div className="tabs" role="tablist">
        {(['upcoming', 'recent', 'withdrawn'] as View[]).map((v) => (
          <button key={v} role="tab" aria-selected={view === v} className={`tab ${view === v ? 'active' : ''}`} onClick={() => setView(v)}>
            {v[0].toUpperCase() + v.slice(1)}<span className="tab-count">{groups[v].length}</span>
          </button>
        ))}
      </div>

      {loading ? (
        <div className="muted">Loading…</div>
      ) : rows.length === 0 ? (
        <div className="card ipo-empty">
          <p className="muted">{view === 'upcoming' ? 'No upcoming IPOs in the calendar.' : view === 'recent' ? 'No recent IPOs.' : 'No withdrawn IPOs.'}</p>
        </div>
      ) : (
        <div className="card table-scroll">
          <table className="data-table">
            {view === 'upcoming' && (
              <>
                <thead><tr><th>Date</th><th>Company</th><th>Exchange</th><th className="r">Price range</th><th className="r hide-sm">Shares</th><th className="r">Deal size</th><th className="hide-sm">Status</th><th /></tr></thead>
                <tbody>
                  {rows.map((ipo) => (
                    <tr key={ipo.id}>
                      <td className="nowrap">{shortDate(ipo.date)} <span className="muted">· {inDays(ipo.date)}</span></td>
                      <td><Company ipo={ipo} /></td>
                      <td className="muted">{ipo.exchange ?? '—'}</td>
                      <td className="r num">{priceRange(ipo.price_range_low, ipo.price_range_high)}</td>
                      <td className="r num hide-sm">{compact(ipo.shares)}</td>
                      <td className="r num">{compact(ipo.total_shares_value, '$')}</td>
                      <td className="hide-sm"><span className="ipo-status">{ipo.status ?? '—'}</span></td>
                      <td className="r"><TrackCell ipo={ipo} /></td>
                    </tr>
                  ))}
                </tbody>
              </>
            )}
            {view === 'recent' && (
              <>
                <thead><tr><th>Listed</th><th>Company</th><th className="r">Debut</th><th className="r">Now</th><th className="r">Since debut</th><th className="hide-sm">Lock-up ends</th><th /></tr></thead>
                <tbody>
                  {rows.map((ipo) => {
                    const since = ipo.debut_price && ipo.current_price != null ? ((ipo.current_price - ipo.debut_price) / ipo.debut_price) * 100 : null;
                    const lockup = lockupEnd(ipo.date);
                    return (
                      <tr key={ipo.id}>
                        <td className="nowrap">{shortDate(ipo.date)}</td>
                        <td><Company ipo={ipo} /></td>
                        <td className="r num">{money(ipo.debut_price)}</td>
                        <td className="r num">{money(ipo.current_price)}</td>
                        <td className={`r num ${since == null ? 'muted' : since >= 0 ? 'up' : 'down'}`}>{since == null ? '—' : `${since >= 0 ? '+' : '−'}${Math.abs(since).toFixed(1)}%`}</td>
                        <td className="nowrap hide-sm">{shortDate(lockup)} <span className="muted">· {inDays(lockup)}</span></td>
                        <td className="r"><TrackCell ipo={ipo} /></td>
                      </tr>
                    );
                  })}
                </tbody>
              </>
            )}
            {view === 'withdrawn' && (
              <>
                <thead><tr><th>Was planned for</th><th>Company</th><th>Exchange</th><th className="r">Deal size</th></tr></thead>
                <tbody>
                  {rows.map((ipo) => (
                    <tr key={ipo.id}>
                      <td className="nowrap">{shortDate(ipo.date)}</td>
                      <td><Company ipo={ipo} /></td>
                      <td className="muted">{ipo.exchange ?? '—'}</td>
                      <td className="r num">{compact(ipo.total_shares_value, '$')}</td>
                    </tr>
                  ))}
                </tbody>
              </>
            )}
          </table>
        </div>
      )}
    </div>
  );
}

export default IPOCalendar;
