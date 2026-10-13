import type { CompanyWithSync } from '../../types';
import './SyncSteps.css';

/** The steps of a running sync, with the current one highlighted. */
function SyncSteps({ company }: { company: CompanyWithSync }) {
  const p = company.sync_progress;
  if (!p) return <span>Queued: this sync starts when the ones ahead of it finish.</span>;
  return (
    <div className="sync-steps">
      <ol>
        {p.steps.map((s, i) => (
          <li key={s} className={i < p.current ? 'done' : i === p.current ? 'current' : ''} aria-current={i === p.current ? 'step' : undefined}>
            {s}
          </li>
        ))}
      </ol>
      {p.waiting && (
        <div className="sync-steps-wait">Waiting for the LLM, which is busy with another sync or job.</div>
      )}
    </div>
  );
}

export default SyncSteps;
