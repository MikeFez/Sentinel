import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { Plus, Check, Users } from 'lucide-react';
import { createCompany, getPeers, type Peer } from '../../api/client';
import { useAppData } from '../../state/useAppData';
import { money, pct, direction } from '../../lib/format';

/** Comparable companies (Finnhub peers) with their price and one-click tracking. */
function PeersPanel({ companyId, refreshKey }: { companyId: string; refreshKey: string }) {
  const { refresh, toast } = useAppData();
  const [peers, setPeers] = useState<Peer[] | null>(null);

  useEffect(() => {
    setPeers(null);
    getPeers(companyId).then(setPeers).catch(() => setPeers([]));
  }, [companyId, refreshKey]);

  if (!peers || peers.length === 0) return null;

  const track = async (p: Peer) => {
    try {
      const created = await createCompany({ name: p.name ?? p.ticker, ticker: p.ticker, status: 'public' });
      setPeers((list) => list?.map((x) => (x.ticker === p.ticker ? { ...x, tracked_company_id: created.id } : x)) ?? null);
      await refresh();
      toast(`Now tracking ${created.name}`, 'success');
    } catch {
      toast(`Could not add ${p.ticker}`, 'error');
    }
  };

  return (
    <div className="card">
      <h2><Users size={15} /> Peers</h2>
      <table className="data-table">
        <tbody>
          {peers.map((p) => (
            <tr key={p.ticker}>
              <td>
                <span className="peer-name">{p.name ?? p.ticker}</span>
                <span className="mono muted peer-ticker">{p.ticker}</span>
              </td>
              <td className="r num">{money(p.price)}</td>
              <td className={`r num ${direction(p.change)}`}>{pct(p.change)}</td>
              <td className="r">
                {p.tracked_company_id ? (
                  <Link to={`/companies/${p.tracked_company_id}`} className="peer-tracked"><Check size={13} /> Tracking</Link>
                ) : (
                  <button className="btn btn-ghost btn-sm" onClick={() => track(p)}><Plus size={13} /> Track</button>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export default PeersPanel;
