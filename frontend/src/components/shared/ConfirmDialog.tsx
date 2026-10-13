import { useEffect, useRef } from 'react';
import { useAppData } from '../../state/useAppData';
import './ConfirmDialog.css';

/** The app's confirm dialog (opened with `confirm()` from useAppData). Enter confirms, Escape cancels. */
function ConfirmDialog() {
  const { pendingConfirm: c, settleConfirm } = useAppData();
  const cancelRef = useRef<HTMLButtonElement>(null);
  const okRef = useRef<HTMLButtonElement>(null);

  useEffect(() => {
    if (!c) return;
    // Destructive actions default to Cancel, so a stray Enter doesn't delete anything
    (c.danger ? cancelRef : okRef).current?.focus();
    const onKey = (e: KeyboardEvent) => { if (e.key === 'Escape') settleConfirm(false); };
    document.addEventListener('keydown', onKey);
    return () => document.removeEventListener('keydown', onKey);
  }, [c, settleConfirm]);

  if (!c) return null;
  return (
    <div className="confirm-overlay" onMouseDown={(e) => { if (e.target === e.currentTarget) settleConfirm(false); }}>
      <div className="confirm-dialog" role="alertdialog" aria-modal="true" aria-labelledby="confirm-title" aria-describedby="confirm-message">
        <h2 id="confirm-title">{c.title}</h2>
        <p id="confirm-message">{c.message}</p>
        <div className="confirm-actions">
          <button ref={cancelRef} className="btn btn-secondary" onClick={() => settleConfirm(false)}>Cancel</button>
          <button ref={okRef} className={`btn ${c.danger ? 'btn-danger' : 'btn-primary'}`} onClick={() => settleConfirm(true)}>
            {c.confirmLabel ?? 'OK'}
          </button>
        </div>
      </div>
    </div>
  );
}

export default ConfirmDialog;
