import { useEffect, useState } from 'react';
import { Outlet, useLocation } from 'react-router-dom';
import { X, Menu } from 'lucide-react';
import Sidebar from './Sidebar';
import { useAppData } from '../../state/useAppData';
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
  // On narrow screens the sidebar is a drawer; close it whenever the page changes
  const [menuOpen, setMenuOpen] = useState(false);
  const { pathname, search } = useLocation();
  useEffect(() => setMenuOpen(false), [pathname, search]);

  return (
    <div className="app-layout">
      <header className="mobile-bar">
        <button className="icon-button" onClick={() => setMenuOpen(true)} aria-label="Open menu"><Menu size={20} /></button>
        <span className="mobile-brand">Sentinel</span>
      </header>
      {menuOpen && <div className="scrim" onClick={() => setMenuOpen(false)} />}
      <Sidebar open={menuOpen} />
      <main className="content-area">
        <Outlet />
      </main>
      <Toasts />
    </div>
  );
}

export default AppLayout;
