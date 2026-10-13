import type { CompanyWithSync } from '../types';

/**
 * A sync that is "syncing" but has no progress hasn't started yet: syncs run one at a time, so
 * scheduled refreshes wait their turn.
 */
export const isQueued = (c: CompanyWithSync) => c.is_syncing && !c.sync_progress;

/** "Step 2 of 4: Grouping news into stories", for tooltips. */
export function syncStepText(c: CompanyWithSync): string {
  const p = c.sync_progress;
  if (!p) return 'Queued: waiting for other syncs to finish';
  const step = `Step ${p.current + 1} of ${p.steps.length}: ${p.steps[p.current]}`;
  return p.waiting ? `${step} (waiting for the LLM)` : step;
}
