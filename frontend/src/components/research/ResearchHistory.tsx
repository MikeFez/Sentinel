import { useEffect, useState } from 'react';
import { History, Trash2 } from 'lucide-react';
import { listResearch, deleteResearch, type ResearchListItem } from '../../api/client';
import { useAppData } from '../../state/useAppData';
import { ago } from '../../lib/format';
import SentimentBadge from '../shared/SentimentBadge';
import type { SentimentType } from '../../types';
import './ResearchHistory.css';

interface Props {
  kind: 'analysis' | 'discovery';
  /** Bump to reload (after a new result is saved). */
  refreshKey?: unknown;
  /** The item on screen, highlighted in the list. */
  currentId?: string | null;
  onOpen: (id: string) => void;
}

/** Past Research results of one kind, newest first: reopen or delete. */
function ResearchHistory({ kind, refreshKey, currentId, onOpen }: Props) {
  const { confirm, toast } = useAppData();
  const [items, setItems] = useState<ResearchListItem[] | null>(null);

  useEffect(() => {
    listResearch(kind).then(setItems).catch(() => setItems([]));
  }, [kind, refreshKey]);

  if (!items?.length) return null;

  const remove = async (item: ResearchListItem) => {
    const ok = await confirm({ title: `Delete “${item.title}”?`, message: 'It is removed from your research history.', confirmLabel: 'Delete', danger: true });
    if (!ok) return;
    try {
      await deleteResearch(item.id);
      setItems((xs) => xs?.filter((x) => x.id !== item.id) ?? null);
    } catch {
      toast('Could not delete it', 'error');
    }
  };

  return (
    <section className="card research-history">
      <h2><History size={15} /> {kind === 'analysis' ? 'Recent analyses' : 'Recent discoveries'}</h2>
      <ul>
        {items.map((item) => (
          <li key={item.id} className={item.id === currentId ? 'current' : ''}>
            <button className="rh-open" onClick={() => onOpen(item.id)}>
              <span className="rh-title">{item.title}</span>
              {kind === 'analysis' ? (
                item.sentiment && <SentimentBadge sentiment={item.sentiment as SentimentType} />
              ) : (
                <span className="muted rh-meta">
                  {item.status === 'failed' ? 'failed' : `${item.companies} companies${item.analyzed ? `, ${item.analyzed} analyzed` : ''}`}
                </span>
              )}
              <span className="muted rh-when">{ago(item.created_at)}</span>
            </button>
            <button className="icon-button rh-delete" onClick={() => remove(item)} aria-label={`Delete ${item.title}`} title="Delete">
              <Trash2 size={14} />
            </button>
          </li>
        ))}
      </ul>
    </section>
  );
}

export default ResearchHistory;
