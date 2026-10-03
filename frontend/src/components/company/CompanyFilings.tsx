import { useEffect, useState } from 'react';
import { ExternalLink } from 'lucide-react';
import { getFilings, type FilingSummary } from '../../api/client';
import { shortDate } from '../../lib/format';

const FORM_LABEL: Record<string, string> = { '8-K': 'Current report', '10-Q': 'Quarterly report', '10-K': 'Annual report' };

/** SEC filings with their AI summaries, and new risk factors for annual reports. */
function CompanyFilings({ companyId, onCount }: { companyId: string; onCount?: (n: number) => void }) {
  const [filings, setFilings] = useState<FilingSummary[] | null>(null);

  useEffect(() => {
    getFilings(companyId)
      .then((f) => { setFilings(f); onCount?.(f.length); })
      .catch(() => setFilings([]));
  }, [companyId, onCount]);

  if (filings === null) return <div className="muted">Loading…</div>;
  if (!filings.length) {
    return <div className="card muted">No filings yet. New 8-K, 10-Q and 10-K filings are checked once a day and summarized.</div>;
  }
  return (
    <div className="filings">
      {filings.map((f) => (
        <article key={f.id} className="card filing">
          <header>
            <span className="filing-form mono">{f.form}</span>
            <span className="muted">{FORM_LABEL[f.form] ?? ''}{f.items ? ` · items ${f.items}` : ''}</span>
            <span className="muted filing-date">{shortDate(f.filed_on)}</span>
            <a href={f.url} target="_blank" rel="noopener noreferrer" className="filing-link">SEC <ExternalLink size={12} /></a>
          </header>
          {f.summary && <p>{f.summary}</p>}
          {f.new_risks && f.new_risks.length > 0 && (
            <div className="filing-risks">
              <h3>New risk factors since the previous 10-K</h3>
              <ul>{f.new_risks.map((r, i) => <li key={i}>{r}</li>)}</ul>
            </div>
          )}
          {f.new_risks && f.new_risks.length === 0 && f.form === '10-K' && <p className="muted">No new risk factors since the previous 10-K.</p>}
        </article>
      ))}
    </div>
  );
}

export default CompanyFilings;
