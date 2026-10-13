import type { ScoreSummary } from '../api/client';

const MIN_CALLS = 20;
const RARE = 0.05;

/** A one-line warning when the AI almost never makes one of the two directional calls, else null. */
export function sentimentBias(s: Pick<ScoreSummary, 'calls' | 'counts'> | null | undefined): string | null {
  if (!s?.counts || s.calls < MIN_CALLS) return null;
  const { bullish, bearish } = s.counts;
  const share = (n: number) => Math.round((n / s.calls) * 100);
  if (bearish / s.calls < RARE) {
    return `The AI made ${bearish === 0 ? 'no' : `only ${bearish}`} bearish ${bearish === 1 ? 'call' : 'calls'} in ${s.calls} (${share(bullish)}% bullish), so its sentiment says little about downside.`;
  }
  if (bullish / s.calls < RARE) {
    return `The AI made ${bullish === 0 ? 'no' : `only ${bullish}`} bullish ${bullish === 1 ? 'call' : 'calls'} in ${s.calls} (${share(bearish)}% bearish), so its sentiment says little about upside.`;
  }
  return null;
}
