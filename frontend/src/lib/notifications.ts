// The events, in the order shown (keys are notify_<kind> settings)
export const NOTIFY_EVENTS: { kind: string; label: string; hint: string }[] = [
  { kind: 'price_alerts', label: 'Price alerts', hint: 'A price crosses one of your alert levels (once per level per day).' },
  { kind: 'big_moves', label: 'Big daily moves', hint: 'A public company moves at least the "Big daily move" % from Refresh & re-analysis.' },
  { kind: 'sentiment_flips', label: 'Sentiment changes', hint: 'A new analysis changes the sentiment, with what changed.' },
  { kind: 'earnings', label: 'Earnings results', hint: 'Results are out: EPS vs. the estimate and the updated sentiment.' },
  { kind: 'material_news', label: 'Material news', hint: 'A news story the AI marks as material (it could move the stock).' },
  { kind: 'filings', label: 'SEC filings', hint: 'A new 8-K, 10-Q or 10-K summary; routine 8-Ks are skipped.' },
  { kind: 'problems', label: 'Problems', hint: 'Syncs or the AI analysis are failing (at most once a day each).' },
  { kind: 'digest', label: 'Weekly digest', hint: 'Portfolio change, big movers, sentiment changes, material news and the week’s earnings.' },
];

export const DIGEST_DAYS = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday'];

