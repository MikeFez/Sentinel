import { useState, useEffect } from 'react';
import { X } from 'lucide-react';
import { createCompany, updateCompany, getTags, assignTags, errorDetail } from '../../api/client';
import type { Company, CompanyCreate, CompanyStatus, Tag } from '../../types';
import { useAppData } from '../../state/useAppData';
import { livePrice } from '../../lib/prices';
import { money } from '../../lib/format';
import './AddCompanyModal.css';

interface AddCompanyModalProps {
  onClose: () => void;
  onSuccess: () => void;
  company?: Company;
}

function AddCompanyModal({ onClose, onSuccess, company }: AddCompanyModalProps) {
  const [formData, setFormData] = useState({
    name: company?.name || '',
    ticker: company?.ticker || '',
    status: (company?.status || 'public') as CompanyStatus,
    description: company?.description || '',
    website: company?.website || '',
    shares_owned: company?.shares_owned?.toString() || '',
    alert_above: company?.alert_above?.toString() || '',
    alert_below: company?.alert_below?.toString() || '',
  });
  const [tags, setTags] = useState<Tag[]>([]);
  const [selectedTagIds, setSelectedTagIds] = useState<string[]>(
    company?.tags.map((t) => t.id) || []
  );
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const { companies } = useAppData();

  useEffect(() => {
    loadTags();
  }, []);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => { if (e.key === 'Escape') onClose(); };
    document.addEventListener('keydown', onKey);
    return () => document.removeEventListener('keydown', onKey);
  }, [onClose]);

  const loadTags = async () => {
    try {
      const tagsData = await getTags();
      setTags(tagsData);
    } catch (error) {
      console.error('Failed to load tags:', error);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const ticker = formData.ticker.trim().toUpperCase();
    const duplicate = ticker && companies.find((c) => c.id !== company?.id && c.ticker?.toUpperCase() === ticker);
    if (duplicate) {
      setError(`You're already tracking ${ticker} as ${duplicate.name}.`);
      return;
    }
    setLoading(true);
    setError('');

    try {
      // Empty fields are sent as null so that clearing one (an alert, shares, the website) sticks
      const text = (v: string) => v.trim() || null;
      const number = (v: string) => (v.trim() ? parseFloat(v) : null);
      const data = {
        name: formData.name.trim(),
        status: formData.status,
        ticker: text(formData.ticker)?.toUpperCase() ?? null,
        description: text(formData.description),
        website: text(formData.website),
        shares_owned: number(formData.shares_owned),
        alert_above: number(formData.alert_above),
        alert_below: number(formData.alert_below),
      };

      let companyId: string;

      if (company) {
        const updated = await updateCompany(company.id, data);
        companyId = updated.id;
      } else {
        const created = await createCompany(data as CompanyCreate);
        companyId = created.id;
      }

      // Always send the tag list when editing, so removing every tag works too
      if (company || selectedTagIds.length > 0) {
        await assignTags(companyId, selectedTagIds);
      }

      onSuccess();
    } catch (err) {
      setError(errorDetail(err, 'Failed to save company'));
    } finally {
      setLoading(false);
    }
  };

  const toggleTag = (tagId: string) => {
    setSelectedTagIds((prev) =>
      prev.includes(tagId)
        ? prev.filter((id) => id !== tagId)
        : [...prev, tagId]
    );
  };

  const STATUSES: { value: CompanyStatus; label: string }[] = [
    { value: 'public', label: 'Public' },
    { value: 'pre_ipo', label: 'Pre-IPO' },
    { value: 'private', label: 'Private' },
    { value: 'acquired', label: 'Acquired' },
  ];
  const live = company ? livePrice(company) : null;
  const above = parseFloat(formData.alert_above);
  const below = parseFloat(formData.alert_below);
  const alertProblem =
    !isNaN(above) && !isNaN(below) && below >= above
      ? 'The "below" alert should be lower than the "above" alert.'
      : live && ((!isNaN(above) && live.price >= above) || (!isNaN(below) && live.price <= below))
        ? `The current price (${money(live.price)}) already crosses this alert, so it will show as triggered.`
        : '';
  const showTicker = formData.status !== 'private';

  return (
    <div className="modal-overlay" onMouseDown={onClose}>
      <div className="modal-content" onMouseDown={(e) => e.stopPropagation()} role="dialog" aria-modal="true" aria-labelledby="company-modal-title">
        <div className="modal-header">
          <h2 id="company-modal-title">{company ? `Edit ${company.name}` : 'Add a company'}</h2>
          <button className="icon-button" onClick={onClose} aria-label="Close"><X size={18} /></button>
        </div>

        <form onSubmit={handleSubmit} className="modal-form">
          <section className="form-section">
            <div className="form-group">
              <label htmlFor="name">Name</label>
              <input id="name" type="text" value={formData.name} autoFocus required placeholder="e.g. Rocket Lab"
                onChange={(e) => setFormData({ ...formData, name: e.target.value })} />
            </div>

            <div className="form-group">
              <label id="status-label">Status</label>
              <div className="segmented" role="radiogroup" aria-labelledby="status-label">
                {STATUSES.map((st) => (
                  <button key={st.value} type="button" role="radio" aria-checked={formData.status === st.value}
                    className={formData.status === st.value ? 'active' : ''}
                    onClick={() => setFormData({ ...formData, status: st.value })}>
                    {st.label}
                  </button>
                ))}
              </div>
              <small className="form-hint">
                {formData.status === 'public'
                  ? 'Public companies get prices, analyst ratings, insider trades and news.'
                  : 'Only news is fetched for companies that aren’t publicly traded.'}
              </small>
            </div>

            <div className={`form-row ${showTicker ? '' : 'single'}`}>
              {showTicker && (
                <div className="form-group">
                  <label htmlFor="ticker">Ticker{formData.status !== 'public' && <span className="optional"> (if known)</span>}</label>
                  <input id="ticker" type="text" className="mono" value={formData.ticker} placeholder="e.g. RKLB"
                    onChange={(e) => setFormData({ ...formData, ticker: e.target.value.toUpperCase() })} />
                </div>
              )}
              <div className="form-group">
                <label htmlFor="website">Website <span className="optional">(optional)</span></label>
                <input id="website" type="url" value={formData.website} placeholder="https://example.com"
                  onChange={(e) => setFormData({ ...formData, website: e.target.value })} />
              </div>
            </div>

            <div className="form-group">
              <label htmlFor="description">Notes <span className="optional">(optional)</span></label>
              <textarea id="description" rows={3} value={formData.description} placeholder="Your thesis, concerns, reminders…"
                onChange={(e) => setFormData({ ...formData, description: e.target.value })} />
            </div>
          </section>

          {formData.status === 'public' && (
            <section className="form-section">
              <h3>Position &amp; price alerts {live && <span className="optional">· now {money(live.price)}</span>}</h3>
              <div className="form-row three-col">
                <div className="form-group">
                  <label htmlFor="shares-owned">Shares owned</label>
                  <input id="shares-owned" type="number" min="0" step="any" value={formData.shares_owned} placeholder="None"
                    onChange={(e) => setFormData({ ...formData, shares_owned: e.target.value })} />
                </div>
                <div className="form-group">
                  <label htmlFor="alert-above">Alert above ($)</label>
                  <input id="alert-above" type="number" min="0" step="any" value={formData.alert_above} placeholder="None"
                    onChange={(e) => setFormData({ ...formData, alert_above: e.target.value })} />
                </div>
                <div className="form-group">
                  <label htmlFor="alert-below">Alert below ($)</label>
                  <input id="alert-below" type="number" min="0" step="any" value={formData.alert_below} placeholder="None"
                    onChange={(e) => setFormData({ ...formData, alert_below: e.target.value })} />
                </div>
              </div>
              <small className={`form-hint ${alertProblem ? 'form-warn' : ''}`}>
                {alertProblem || (parseFloat(formData.shares_owned) > 0
                  ? 'In your portfolio. Clear the shares to move it to your watchlist.'
                  : 'On your watchlist. Enter shares owned to move it to your portfolio.')}
              </small>
            </section>
          )}

          {tags.length > 0 && (
            <section className="form-section">
              <h3>Tags</h3>
              <div className="tag-select">
                {tags.map((tag) => {
                  const on = selectedTagIds.includes(tag.id);
                  return (
                    <button key={tag.id} type="button" aria-pressed={on} className={`tag-chip ${on ? 'selected' : ''}`} onClick={() => toggleTag(tag.id)}
                      style={{ borderColor: on ? tag.color : 'var(--border-color)', backgroundColor: on ? `${tag.color}22` : 'transparent' }}>
                      <span className="tag-chip-dot" style={{ backgroundColor: tag.color }} />
                      {tag.name}
                    </button>
                  );
                })}
              </div>
            </section>
          )}

          {error && <div className="form-error">{error}</div>}

          <div className="modal-footer">
            <button type="button" className="btn btn-secondary" onClick={onClose}>Cancel</button>
            <button type="submit" className="btn btn-primary" disabled={loading || !formData.name.trim()}>
              {loading ? 'Saving…' : company ? 'Save changes' : 'Add company'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

export default AddCompanyModal;
