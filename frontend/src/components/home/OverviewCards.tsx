import { Link } from 'react-router-dom';
import { TrendingUp, TrendingDown } from 'lucide-react';
import type { CompanyWithSync } from '../../types';
import './OverviewCards.css';

interface OverviewCardsProps {
  companies: CompanyWithSync[];
}

function OverviewCards({ companies }: OverviewCardsProps) {
  const getSentimentColor = (sentiment: string | null) => {
    if (!sentiment) return 'var(--text-muted)';
    const colors = {
      bullish: 'var(--sentiment-bullish)',
      bearish: 'var(--sentiment-bearish)',
      neutral: 'var(--sentiment-neutral)',
      mixed: 'var(--sentiment-mixed)',
    };
    return colors[sentiment as keyof typeof colors] || 'var(--text-muted)';
  };

  const formatDate = (dateStr: string) => {
    const date = new Date(dateStr);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffHours = Math.floor(diffMs / (1000 * 60 * 60));
    const diffDays = Math.floor(diffHours / 24);

    if (diffHours < 1) return 'Less than an hour ago';
    if (diffHours < 24) return `${diffHours} hours ago`;
    if (diffDays === 1) return '1 day ago';
    return `${diffDays} days ago`;
  };

  if (companies.length === 0) {
    return null;
  }

  return (
    <div className="overview-section">
      <h2 className="section-title">All Companies</h2>
      <div className="overview-grid">
        {companies.map((company) => (
          <Link
            key={company.id}
            to={`/companies/${company.id}`}
            className="overview-card"
          >
            <div className="overview-card-header">
              <div>
                <h3 className="company-title">{company.name}</h3>
                {company.ticker && (
                  <div className="company-ticker">{company.ticker}</div>
                )}
              </div>
              {company.latest_sync?.ai_sentiment && (
                <div
                  className="sentiment-badge-small"
                  style={{ color: getSentimentColor(company.latest_sync.ai_sentiment) }}
                >
                  {company.latest_sync.ai_sentiment}
                </div>
              )}
            </div>

            {company.status === 'public' && company.latest_sync?.stock_price && (
              <div className="price-info">
                <div className="price">${company.latest_sync.stock_price.toFixed(2)}</div>
                {company.latest_sync.price_change !== null && (
                  <div
                    className="price-change"
                    style={{
                      color:
                        company.latest_sync.price_change >= 0
                          ? 'var(--sentiment-bullish)'
                          : 'var(--sentiment-bearish)',
                    }}
                  >
                    {company.latest_sync.price_change >= 0 ? (
                      <TrendingUp size={14} />
                    ) : (
                      <TrendingDown size={14} />
                    )}
                    {Math.abs(company.latest_sync.price_change).toFixed(2)}%
                  </div>
                )}
              </div>
            )}

            <div className="card-footer">
              <div className="tag-list">
                {company.tags.slice(0, 2).map((tag) => (
                  <span
                    key={tag.id}
                    className="mini-tag"
                    style={{ backgroundColor: `${tag.color}30`, color: tag.color }}
                  >
                    {tag.name}
                  </span>
                ))}
                {company.tags.length > 2 && (
                  <span className="mini-tag">+{company.tags.length - 2}</span>
                )}
              </div>
              {company.latest_sync && (
                <div className="sync-time">
                  {formatDate(company.latest_sync.synced_at)}
                </div>
              )}
            </div>
          </Link>
        ))}
      </div>
    </div>
  );
}

export default OverviewCards;
