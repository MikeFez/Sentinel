import { Outlet } from 'react-router-dom';
import { X } from 'lucide-react';
import Sidebar from './Sidebar';
import { useAppData } from '../../state/AppData';
import './AppLayout.css';

function Toasts() {
  const { toasts, dismissToast } = useAppData();
  if (!toasts.length) return null;
  return (
    <div className="toasts" role="status" aria-live="polite">
      {toasts.map((t) => (
        <div key={t.id} className={`toast toast-${t.kind}`}>
          <span>{t.text}</span>
          <button className="icon-button" onClick={() => dismissToast(t.id)} aria-label="Dismiss"><X size={14} /></button>
        </div>
      ))}
    </div>
  );
}

function AppLayout() {
  return (
    <div className="app-layout">
      <Sidebar />
      <main className="content-area">
        <Outlet />
      </main>
      <Toasts />
    </div>
  );
}

export default AppLayout;
