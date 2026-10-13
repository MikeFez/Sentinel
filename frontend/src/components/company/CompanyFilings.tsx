import { useEffect, useState } from 'react';
import { ExternalLink } from 'lucide-react';
import { getFilings, type FilingSummary } from '../../api/client';
import { shortDate } from '../../lib/format';

const FORM_LABEL: Record<string, string> = { '8-K': 'Current report', '10-Q': 'Quarterly report', '10-K': 'Annual report' };

// 8-K item numbers in plain words (SEC Form 8-K instructions)
const ITEM_LABEL: Record<string, string> = {
  '1.01': 'Material agreement', '1.02': 'Agreement ended', '1.03': 'Bankruptcy', '1.04': 'Mine safety',
  '1.05': 'Cybersecurity incident', '2.01': 'Acquisition or sale completed', '2.02': 'Results',
  '2.03': 'New debt', '2.04': 'Debt accelerated', '2.05': 'Restructuring costs', '2.06': 'Impairment',
  '3.01': 'Listing notice', '3.02': 'Unregistered share sale', '3.03': "Shareholders' rights changed",
  '4.01': 'Auditor change', '4.02': 'Restatement', '5.01': 'Change in control', '5.02': 'Executive or board change',
  '5.03': 'Bylaws changed', '5.04': 'Benefit plan blackout', '5.05': 'Ethics code', '5.07': 'Shareholder vote',
  '5.08': 'Director nominations', '7.01': 'Reg FD disclosure', '8.01': 'Other events', '9.01': 'Exhibits',
};

/** "7.01,8.01,9.01" → "Reg FD disclosure · Other events" (exhibits only if that's all there is). */
function itemNames(items: string): string {
  const codes = items.split(',').map((c) => c.trim()).filter(Boolean);
  const shown = codes.length > 1 ? codes.filter((c) => c !== '9.01') : codes;
  return shown.map((c) => ITEM_LABEL[c] ?? `Item ${c}`).join(' · ');
}

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
        <article key={f.id} className={`card filing ${f.routine ? 'filing-routine' : ''}`}>
          <header>
            <span className="filing-form mono">{f.form}</span>
            <span className="muted" title={f.items ? `Items ${f.items}` : undefined}>{f.items ? itemNames(f.items) : FORM_LABEL[f.form] ?? ''}</span>
            {f.routine && <span className="filing-routine-tag" title="Nothing new for investors; left out of the AI analysis">Routine</span>}
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
