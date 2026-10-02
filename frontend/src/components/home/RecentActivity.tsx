import { Link } from 'react-router-dom';
import { Clock, TrendingUp, TrendingDown } from 'lucide-react';
import type { HomeSummary } from '../../api/client';
import SentimentBadge from '../shared/SentimentBadge';
import type { SentimentType } from '../../types';
import './RecentActivity.css';

interface RecentActivityProps {
  activity: HomeSummary['recent_activity'];
}

function RecentActivity({ activity }: RecentActivityProps) {
  const formatTime = (dateStr: string) => {
    const date = new Date(dateStr);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffMins = Math.floor(diffMs / (1000 * 60));
    const diffHours = Math.floor(diffMins / 60);
    const diffDays = Math.floor(diffHours / 24);

    if (diffMins < 1) return 'Just now';
    if (diffMins < 60) return `${diffMins}m ago`;
    if (diffHours < 24) return `${diffHours}h ago`;
    if (diffDays === 1) return '1d ago';
    return `${diffDays}d ago`;
  };

  if (activity.length === 0) {
    return (
      <div className="recent-activity">
        <h2 className="section-title">
          <Clock size={20} />
          Recent Activity
        </h2>
        <div className="empty-activity">
          <p>No sync activity yet. Start by syncing a company!</p>
        </div>
      </div>
    );
  }

  return (
    <div className="recent-activity">
      <h2 className="section-title">
        <Clock size={20} />
        Recent Activity
      </h2>

      <div className="activity-list">
        {activity.map((item) => (
          <Link
            key={item.sync_id}
            to={`/companies/${item.company_id}`}
            className="activity-item"
          >
            <div className="activity-main">
              <div className="activity-company">
                <span className="activity-name">{item.company_name}</span>
                {item.company_ticker && (
                  <span className="activity-ticker">{item.company_ticker}</span>
                )}
              </div>
              <span className="activity-time">{formatTime(item.synced_at)}</span>
            </div>

            {item.ai_summary && (
              <div className="activity-summary">
                {item.ai_summary.length > 150
                  ? `${item.ai_summary.substring(0, 150)}...`
                  : item.ai_summary}
              </div>
            )}

            <div className="activity-meta">
              {item.stock_price && (
                <div className="activity-price">
                  ${item.stock_price.toFixed(2)}
                  {item.price_change !== null && (
                    <span
                      className={`price-indicator ${
                        item.price_change >= 0 ? 'positive' : 'negative'
                      }`}
                    >
                      {item.price_change >= 0 ? (
                        <TrendingUp size={12} />
                      ) : (
                        <TrendingDown size={12} />
                      )}
                      {Math.abs(item.price_change).toFixed(2)}%
                    </span>
                  )}
                </div>
              )}
              {item.ai_sentiment && (
                <SentimentBadge sentiment={item.ai_sentiment as SentimentType} />
              )}
            </div>
          </Link>
        ))}
      </div>
    </div>
  );
}

export default RecentActivity;
