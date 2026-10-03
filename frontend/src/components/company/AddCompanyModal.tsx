import { useState, useEffect } from 'react';
import { X } from 'lucide-react';
import { createCompany, updateCompany, getTags, assignTags } from '../../api/client';
import type { Company, CompanyCreate, CompanyStatus, Tag } from '../../types';
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

  useEffect(() => {
    loadTags();
  }, []);

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
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to save company');
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

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h2>{company ? 'Edit Company' : 'Add Company'}</h2>
          <button className="icon-button" onClick={onClose}>
            <X size={20} />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="modal-form">
          <div className="form-group">
            <label htmlFor="name">Company Name *</label>
            <input
              id="name"
              type="text"
              value={formData.name}
              onChange={(e) => setFormData({ ...formData, name: e.target.value })}
              required
            />
          </div>

          <div className="form-row">
            <div className="form-group">
              <label htmlFor="ticker">Ticker Symbol</label>
              <input
                id="ticker"
                type="text"
                value={formData.ticker}
                onChange={(e) =>
                  setFormData({ ...formData, ticker: e.target.value.toUpperCase() })
                }
                placeholder="e.g. AAPL"
              />
            </div>

            <div className="form-group">
              <label htmlFor="status">Status *</label>
              <select
                id="status"
                value={formData.status}
                onChange={(e) =>
                  setFormData({ ...formData, status: e.target.value as CompanyStatus })
                }
                required
              >
                <option value="public">Public</option>
                <option value="pre_ipo">Pre-IPO</option>
                <option value="private">Private</option>
                <option value="acquired">Acquired</option>
              </select>
            </div>
          </div>

          <div className="form-group">
            <label htmlFor="website">Website</label>
            <input
              id="website"
              type="url"
              value={formData.website}
              onChange={(e) => setFormData({ ...formData, website: e.target.value })}
              placeholder="https://example.com"
            />
          </div>

          <div className="form-group">
            <label htmlFor="description">Description</label>
            <textarea
              id="description"
              value={formData.description}
              onChange={(e) => setFormData({ ...formData, description: e.target.value })}
              rows={3}
              placeholder="Notes about this company..."
            />
          </div>

          <div className="form-section-label">Tracking</div>

          <div className="form-row three-col">
            <div className="form-group">
              <label htmlFor="shares-owned">Shares Owned</label>
              <input
                id="shares-owned"
                type="number"
                min="0"
                step="any"
                value={formData.shares_owned}
                onChange={(e) => setFormData({ ...formData, shares_owned: e.target.value })}
                placeholder="0"
              />
            </div>
            <div className="form-group">
              <label htmlFor="alert-above">Alert Above ($)</label>
              <input
                id="alert-above"
                type="number"
                min="0"
                step="any"
                value={formData.alert_above}
                onChange={(e) => setFormData({ ...formData, alert_above: e.target.value })}
                placeholder="e.g. 200.00"
              />
            </div>
            <div className="form-group">
              <label htmlFor="alert-below">Alert Below ($)</label>
              <input
                id="alert-below"
                type="number"
                min="0"
                step="any"
                value={formData.alert_below}
                onChange={(e) => setFormData({ ...formData, alert_below: e.target.value })}
                placeholder="e.g. 150.00"
              />
            </div>
          </div>

          <div className="form-group">
            <label>Tags</label>
            <div className="tag-select">
              {tags.map((tag) => (
                <button
                  key={tag.id}
                  type="button"
                  className={`tag-chip ${selectedTagIds.includes(tag.id) ? 'selected' : ''}`}
                  onClick={() => toggleTag(tag.id)}
                  style={{
                    borderColor: selectedTagIds.includes(tag.id) ? tag.color : 'transparent',
                    backgroundColor: selectedTagIds.includes(tag.id)
                      ? `${tag.color}20`
                      : 'var(--bg-tertiary)',
                  }}
                >
                  <span className="tag-chip-dot" style={{ backgroundColor: tag.color }} />
                  {tag.name}
                </button>
              ))}
            </div>
          </div>

          {error && <div className="form-error">{error}</div>}

          <div className="modal-footer">
            <button type="button" className="btn btn-secondary" onClick={onClose}>
              Cancel
            </button>
            <button type="submit" className="btn btn-primary" disabled={loading}>
              {loading ? 'Saving...' : company ? 'Update' : 'Create'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

export default AddCompanyModal;
