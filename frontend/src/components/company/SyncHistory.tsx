import { useState } from 'react';
import { ChevronDown, ChevronRight } from 'lucide-react';
import type { Sync } from '../../types';
import SentimentBadge from '../shared/SentimentBadge';
import './SyncHistory.css';

interface SyncHistoryProps {
  syncs: Sync[];
}

function SyncHistory({ syncs }: SyncHistoryProps) {
  const [isExpanded, setIsExpanded] = useState(false);

  const formatDate = (dateStr: string) => {
    const date = new Date(dateStr);
    return date.toLocaleString();
  };

  return (
    <div className="sync-history">
      <button
        className="sync-history-header"
        onClick={() => setIsExpanded(!isExpanded)}
      >
        {isExpanded ? <ChevronDown size={20} /> : <ChevronRight size={20} />}
        <h2 className="section-title">Sync History ({syncs.length})</h2>
      </button>

      {isExpanded && (
        <div className="sync-history-list">
          {syncs.map((sync) => (
            <div key={sync.id} className="sync-history-item">
              <div className="sync-history-main">
                <div className="sync-date">{formatDate(sync.synced_at)}</div>
                <div className="sync-meta">
                  {sync.stock_price && (
                    <span className="sync-price">
                      ${sync.stock_price.toFixed(2)}
                      {sync.price_change !== null && sync.price_change !== undefined && (
                        <span
                          className={`sync-change ${
                            sync.price_change >= 0 ? 'positive' : 'negative'
                          }`}
                        >
                          {sync.price_change >= 0 ? '+' : ''}
                          {sync.price_change.toFixed(2)}%
                        </span>
                      )}
                    </span>
                  )}
                  {sync.ai_sentiment && <SentimentBadge sentiment={sync.ai_sentiment} />}
                  <span className={`sync-status status-${sync.status}`}>
                    {sync.status}
                  </span>
                </div>
              </div>

              {sync.ai_summary && (
                <div className="sync-summary">{sync.ai_summary}</div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

export default SyncHistory;
