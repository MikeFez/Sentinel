/** % change from the price an analysis was written at to now, or null if either is unknown. */
export function driftSince(analysisPrice: number | null | undefined, now: number | null | undefined): number | null {
  if (!analysisPrice || now == null) return null;
  return (now / analysisPrice - 1) * 100;
}
