import type { Sync } from '../../types';
import './SentimentSparkline.css';

interface Props {
  syncs: Sync[];
}

const SENTIMENT_COLOR: Record<string, string> = {
  bullish: '#10b981',
  bearish: '#ef4444',
  neutral: '#6b7280',
  mixed: '#f59e0b',
};

const SENTIMENT_LABEL: Record<string, string> = {
  bullish: 'Bullish',
  bearish: 'Bearish',
  neutral: 'Neutral',
  mixed: 'Mixed',
};

function SentimentSparkline({ syncs }: Props) {
  const withSentiment = [...syncs]
    .filter((s) => s.ai_sentiment)
    .reverse() // oldest → newest left to right
    .slice(-12);

  if (withSentiment.length < 2) return null;

  return (
    <div className="sentiment-sparkline">
      <div className="sparkline-label">Sentiment trend</div>
      <div className="sparkline-dots">
        {withSentiment.map((sync) => {
          const s = sync.ai_sentiment!;
          return (
            <span
              key={sync.id}
              className="sparkline-dot"
              style={{ backgroundColor: SENTIMENT_COLOR[s] ?? '#6b7280' }}
              title={`${SENTIMENT_LABEL[s] ?? s} — ${new Date(sync.synced_at).toLocaleDateString()}`}
            />
          );
        })}
      </div>
    </div>
  );
}

export default SentimentSparkline;
