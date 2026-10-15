import type { AnalysisEvidence } from '../../types';
import './AnalysisEvidence.css';

export function EvidenceLinks({ evidence, section, index, scope }: {
  evidence?: AnalysisEvidence | null; section: string; index: number; scope: string;
}) {
  const ids = [...new Set(evidence?.citations.filter((c) => c.section === section && c.index === index).flatMap((c) => c.source_ids) ?? [])];
  return ids.length ? <span className="evidence-links">{ids.map((id) => (
    <a key={id} href={`#evidence-${scope}-${id}`} title={evidence?.sources.find((s) => s.id === id)?.title}>[{id}]</a>
  ))}</span> : evidence ? <span className="evidence-uncited" title="The model provided no linked evidence for this claim">No linked evidence</span> : null;
}

export function EvidenceSources({ evidence, scope }: { evidence?: AnalysisEvidence | null; scope: string }) {
  if (!evidence?.sources.length) return null;
  return (
    <section className="analysis-evidence" aria-label="Analysis evidence">
      <h3>Evidence at analysis time</h3>
      <p className="muted">References point to supplied sources; they do not independently verify a claim. Filing and story excerpts below are summaries.</p>
      {evidence.sources.map((s) => (
        <div key={s.id} id={`evidence-${scope}-${s.id}`} className="evidence-source" tabIndex={-1}>
          <div><span className="mono">[{s.id}]</span> {s.url ? <a href={s.url} target="_blank" rel="noopener noreferrer">{s.title} ↗</a> : <strong>{s.title}</strong>}</div>
          {s.excerpt && <details><summary>{s.kind === 'metrics' ? 'View metric snapshot' : 'View supplied excerpt'}</summary><pre>{s.excerpt}</pre></details>}
        </div>
      ))}
    </section>
  );
}
