import { TrendingUp } from 'lucide-react';
import type { AnalystRatings as AnalystRatingsType } from '../../types';
import './AnalystRatings.css';

interface AnalystRatingsProps {
  ratings: AnalystRatingsType;
}

function AnalystRatings({ ratings }: AnalystRatingsProps) {
  const total =
    (ratings.strongBuy || 0) +
    (ratings.buy || 0) +
    (ratings.hold || 0) +
    (ratings.sell || 0) +
    (ratings.strongSell || 0);

  if (total === 0) {
    return null;
  }

  const calculatePercentage = (value: number | undefined) => {
    if (!value || total === 0) return 0;
    return (value / total) * 100;
  };

  const getConsensus = () => {
    const bullish = (ratings.strongBuy || 0) + (ratings.buy || 0);
    const bearish = (ratings.strongSell || 0) + (ratings.sell || 0);

    if (bullish > bearish * 2) return { text: 'Strong Buy', color: 'var(--success-dark)' };
    if (bullish > bearish) return { text: 'Buy', color: 'var(--success)' };
    if (bearish > bullish * 2) return { text: 'Sell', color: 'var(--danger-dark)' };
    if (bearish > bullish) return { text: 'Hold/Sell', color: 'var(--warning)' };
    return { text: 'Hold', color: 'var(--text-muted)' };
  };

  const consensus = getConsensus();

  return (
    <div className="analyst-ratings panel">
      <div className="panel-header">
        <TrendingUp size={20} />
        <h2>Analyst Ratings</h2>
      </div>

      <div className="analyst-consensus">
        <div className="consensus-label">Consensus</div>
        <div className="consensus-value" style={{ color: consensus.color }}>
          {consensus.text}
        </div>
        <div className="consensus-count">{total} analysts</div>
      </div>

      <div className="ratings-breakdown">
        {ratings.strongBuy !== undefined && ratings.strongBuy > 0 && (
          <div className="rating-row">
            <span className="rating-label">Strong Buy</span>
            <div className="rating-bar-container">
              <div
                className="rating-bar strong-buy"
                style={{ width: `${calculatePercentage(ratings.strongBuy)}%` }}
              />
            </div>
            <span className="rating-count">{ratings.strongBuy}</span>
          </div>
        )}

        {ratings.buy !== undefined && ratings.buy > 0 && (
          <div className="rating-row">
            <span className="rating-label">Buy</span>
            <div className="rating-bar-container">
              <div
                className="rating-bar buy"
                style={{ width: `${calculatePercentage(ratings.buy)}%` }}
              />
            </div>
            <span className="rating-count">{ratings.buy}</span>
          </div>
        )}

        {ratings.hold !== undefined && ratings.hold > 0 && (
          <div className="rating-row">
            <span className="rating-label">Hold</span>
            <div className="rating-bar-container">
              <div
                className="rating-bar hold"
                style={{ width: `${calculatePercentage(ratings.hold)}%` }}
              />
            </div>
            <span className="rating-count">{ratings.hold}</span>
          </div>
        )}

        {ratings.sell !== undefined && ratings.sell > 0 && (
          <div className="rating-row">
            <span className="rating-label">Sell</span>
            <div className="rating-bar-container">
              <div
                className="rating-bar sell"
                style={{ width: `${calculatePercentage(ratings.sell)}%` }}
              />
            </div>
            <span className="rating-count">{ratings.sell}</span>
          </div>
        )}

        {ratings.strongSell !== undefined && ratings.strongSell > 0 && (
          <div className="rating-row">
            <span className="rating-label">Strong Sell</span>
            <div className="rating-bar-container">
              <div
                className="rating-bar strong-sell"
                style={{ width: `${calculatePercentage(ratings.strongSell)}%` }}
              />
            </div>
            <span className="rating-count">{ratings.strongSell}</span>
          </div>
        )}
      </div>
    </div>
  );
}

export default AnalystRatings;
