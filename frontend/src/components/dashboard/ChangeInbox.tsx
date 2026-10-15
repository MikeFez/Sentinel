import { useCallback, useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { Check, Clock, ExternalLink, Inbox, RefreshCw } from 'lucide-react';
import { errorDetail, getInbox, reviewInbox, type InboxItem } from '../../api/client';
import { useAppData } from '../../state/useAppData';
import { ago, shortDate } from '../../lib/format';
import './ChangeInbox.css';

const LABELS: Record<InboxItem['kind'], string> = {
  story: 'Material story', risk: 'New risk', filing: 'SEC filing', sentiment: 'Sentiment change',
  analysis: 'Analysis change', catalyst: 'Upcoming catalyst',
};

export default function ChangeInbox() {
  const { companies, toast } = useAppData();
  const [items, setItems] = useState<InboxItem[]>([]);
  const [loaded, setLoaded] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [view, setView] = useState<InboxItem['state']>('active');
  const [holdings, setHoldings] = useState(false);
  const [limit, setLimit] = useState(6);
  const [busy, setBusy] = useState<Set<string>>(new Set());
  const load = useCallback(async () => {
    try {
      const data = await getInbox();
      setItems(data.items); setLoaded(true); setError(null);
    } catch (err) {
      setError(errorDetail(err, 'Could not load your briefing.'));
    }
  }, []);
  // Refresh after new syncs/news, and periodically so reminders return without a reload.
  const revision = companies.map((c) => `${c.id}:${c.latest_sync?.id}:${c.latest_news_at}`).join('|');
  useEffect(() => { void load(); }, [load, revision]);
  useEffect(() => {
    const timer = window.setInterval(() => { void load(); }, 60_000);
    return () => window.clearInterval(timer);
  }, [load]);

  const act = async (item: InboxItem, action: 'review' | 'snooze' | 'reopen') => {
    setBusy((s) => new Set(s).add(item.key));
    try {
      await reviewInbox(item.key, action);
      await load();
      toast(action === 'snooze' ? 'Reminder set for tomorrow' : action === 'review' ? 'Marked reviewed' : 'Returned to inbox', 'info');
    } catch (err) {
      toast(errorDetail(err, 'Could not save your review. Please retry.'), 'error');
    } finally {
      setBusy((s) => { const next = new Set(s); next.delete(item.key); return next; });
    }
  };
  const filtered = items.filter((i) => i.state === view && (!holdings || i.owned));
  return (
    <section className="card change-inbox" aria-label="What changed">
      <div className="ci-header">
        <div><h2><Inbox size={17} /> What changed?</h2><p className="muted">Past 30 days and the next week’s earnings. Holdings and material developments first.</p></div>
        <button className="btn btn-ghost btn-sm" onClick={() => void load()} aria-label="Refresh briefing"><RefreshCw size={14} /></button>
      </div>
      <div className="ci-controls">
        <div className="segmented" role="group" aria-label="Review status">
          {(['active', 'snoozed', 'reviewed'] as const).map((v) => (
            <button key={v} aria-pressed={view === v} className={view === v ? 'active' : ''} onClick={() => { setView(v); setLimit(6); }}>
              {v === 'active' ? 'Inbox' : v === 'snoozed' ? 'Reminders' : 'Reviewed'} <span className="muted">{items.filter((i) => i.state === v && (!holdings || i.owned)).length}</span>
            </button>
          ))}
        </div>
        <label><input type="checkbox" checked={holdings} onChange={(e) => { setHoldings(e.target.checked); setLimit(6); }} /> Holdings only</label>
      </div>
      {error && <div className="notice notice-error" role="alert">{error} <button className="btn btn-ghost btn-sm" onClick={() => void load()}>Retry</button></div>}
      {!loaded && !error && <p className="muted">Loading briefing…</p>}
      {loaded && !error && filtered.length === 0 && <p className="ci-empty muted">{view === 'active' ? 'All caught up. New developments will appear here as companies refresh.' : view === 'reviewed' ? 'No reviewed developments in this period.' : 'No reminders set.'}</p>}
      <div className="ci-items">
        {filtered.slice(0, limit).map((i) => (
          <article key={i.key} className={`ci-item ci-${i.kind}`}>
            <div className="ci-meta"><span>{LABELS[i.kind]}</span>{i.owned && <span className="ci-holding">Holding</span>}<span className="muted">{i.company_name}{i.ticker ? ` · ${i.ticker}` : ''}</span><span className="muted">{i.kind === 'catalyst' ? shortDate(i.at) : ago(i.at)}</span></div>
            <Link to={i.href} className="ci-title">{i.title}</Link>
            {i.detail && <p className="ci-detail">{i.detail}</p>}
            {i.sources.length > 0 && <details className="ci-evidence"><summary>Supporting evidence ({i.sources.length})</summary><ul>{i.sources.map((s, n) => <li key={n}>{s.url ? <a href={s.url} target="_blank" rel="noopener noreferrer">{s.title} <ExternalLink size={11} /></a> : s.title}</li>)}</ul></details>}
            <div className="ci-actions">
              <Link to={i.href} className="btn btn-ghost btn-sm">Open company</Link>
              {i.state !== 'reviewed' && <button disabled={busy.has(i.key)} className="btn btn-secondary btn-sm" onClick={() => void act(i, 'review')}><Check size={13} /> Mark reviewed</button>}
              {i.state === 'active' && <button disabled={busy.has(i.key)} className="btn btn-ghost btn-sm" onClick={() => void act(i, 'snooze')}><Clock size={13} /> Remind tomorrow</button>}
              {i.state !== 'active' && <button disabled={busy.has(i.key)} className="btn btn-ghost btn-sm" onClick={() => void act(i, 'reopen')}>Return to inbox</button>}
              {i.state === 'snoozed' && i.snoozed_until && <span className="muted">Returns {new Date(i.snoozed_until).toLocaleString()}</span>}
            </div>
          </article>
        ))}
      </div>
      {filtered.length > limit && <button className="btn btn-ghost btn-sm" onClick={() => setLimit((l) => l + 12)}>Show more ({filtered.length - limit} remaining)</button>}
    </section>
  );
}
