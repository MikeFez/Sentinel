import type { SentimentType } from '../../types';
import './SentimentBadge.css';

const SENTIMENT_TOOLTIPS: Record<string, string> = {
  bullish: 'Bullish — positive outlook; the AI expects the stock or company to perform well',
  bearish: 'Bearish — negative outlook; the AI sees headwinds, risks, or declining momentum',
  neutral: 'Neutral — no strong signal either way; mixed or insufficient data to lean bullish or bearish',
  mixed:   'Mixed — conflicting signals; some positive factors offset by negatives, making direction unclear',
};

interface SentimentBadgeProps {
  sentiment: SentimentType;
}

function SentimentBadge({ sentiment }: SentimentBadgeProps) {
  return (
    <span
      className={`sentiment-badge sentiment-${sentiment}`}
      title={SENTIMENT_TOOLTIPS[sentiment] ?? sentiment}
    >
      {sentiment}
    </span>
  );
}

export default SentimentBadge;
