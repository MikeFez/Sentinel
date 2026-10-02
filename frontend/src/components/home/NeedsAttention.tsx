import { Link } from 'react-router-dom';
import { AlertTriangle, RefreshCw } from 'lucide-react';
import type { HomeSummary } from '../../api/client';
import './NeedsAttention.css';

interface NeedsAttentionProps {
  staleCompanies: HomeSummary['stale_companies'];
}

function NeedsAttention({ staleCompanies }: NeedsAttentionProps) {
  if (staleCompanies.length === 0) {
    return (
      <div className="needs-attention">
        <h2 className="section-title">
          <AlertTriangle size={20} />
          Needs Attention
        </h2>
        <div className="no-stale">
          <p>All companies are up to date! ✓</p>
        </div>
      </div>
    );
  }

  const getStalenessLevel = (daysSinceSync: number | null) => {
    if (daysSinceSync === null) return 'never';
    if (daysSinceSync >= 30) return 'critical';
    if (daysSinceSync >= 14) return 'high';
    return 'medium';
  };

  const getStalenessText = (lastSync: string | null, daysSinceSync: number | null) => {
    if (!lastSync) return 'Never synced';
    if (daysSinceSync === null) return 'Never synced';
    if (daysSinceSync === 1) return '1 day ago';
    if (daysSinceSync < 30) return `${daysSinceSync} days ago`;
    const months = Math.floor(daysSinceSync / 30);
    return months === 1 ? '1 month ago' : `${months} months ago`;
  };

  return (
    <div className="needs-attention">
      <h2 className="section-title">
        <AlertTriangle size={20} />
        Needs Attention ({staleCompanies.length})
      </h2>

      <div className="stale-list">
        {staleCompanies.map((company) => {
          const staleness = getStalenessLevel(company.days_since_sync);
          const staleness_text = getStalenessText(company.last_sync, company.days_since_sync);

          return (
            <Link
              key={company.id}
              to={`/companies/${company.id}`}
              className={`stale-item staleness-${staleness}`}
            >
              <div className="stale-main">
                <div className="stale-company">
                  <span className="stale-name">{company.name}</span>
                  {company.ticker && (
                    <span className="stale-ticker">{company.ticker}</span>
                  )}
                </div>
                <div className="stale-badge">
                  <RefreshCw size={14} />
                  {staleness_text}
                </div>
              </div>
              <div className="stale-status">
                Status: {company.status.replace('_', '-')}
              </div>
            </Link>
          );
        })}
      </div>
    </div>
  );
}

export default NeedsAttention;
