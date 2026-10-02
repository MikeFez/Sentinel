import { useState } from 'react';
import { Users, TrendingUp, TrendingDown, ChevronDown, ChevronRight } from 'lucide-react';
import type { InsiderTransaction } from '../../types';
import './InsiderTransactions.css';

interface InsiderTransactionsProps {
  transactions: InsiderTransaction[];
}

function InsiderTransactions({ transactions }: InsiderTransactionsProps) {
  const [isExpanded, setIsExpanded] = useState(false);

  if (!transactions || transactions.length === 0) {
    return null;
  }

  const formatDate = (dateStr: string) => {
    const date = new Date(dateStr);
    return date.toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
    });
  };

  const formatShares = (shares: number) => {
    if (Math.abs(shares) >= 1000000) {
      return `${(Math.abs(shares) / 1000000).toFixed(2)}M`;
    }
    if (Math.abs(shares) >= 1000) {
      return `${(Math.abs(shares) / 1000).toFixed(1)}K`;
    }
    return Math.abs(shares).toLocaleString();
  };

  const formatPrice = (price: number | undefined) => {
    if (price === undefined) return null;
    return `$${price.toFixed(2)}`;
  };

  return (
    <div className="insider-transactions-wrapper">
      <button
        className="insider-transactions-toggle"
        onClick={() => setIsExpanded(!isExpanded)}
      >
        {isExpanded ? <ChevronDown size={20} /> : <ChevronRight size={20} />}
        <Users size={18} />
        <h2 className="section-title">Insider Transactions ({transactions.length})</h2>
      </button>

      {isExpanded && (
        <div className="insider-transactions panel">
          <div className="transactions-list">
            {transactions.slice(0, 10).map((txn, index) => {
              if (txn.change === null || txn.change === undefined) {
                return null;
              }

              const isBuy = txn.change > 0;

              return (
                <div key={index} className="transaction-item">
                  <div className="transaction-icon">
                    {isBuy ? (
                      <TrendingUp size={20} className="transaction-buy" />
                    ) : (
                      <TrendingDown size={20} className="transaction-sell" />
                    )}
                  </div>

                  <div className="transaction-content">
                    <div className="transaction-header">
                      <span className="transaction-name">{txn.name}</span>
                      <span className={`transaction-type ${isBuy ? 'buy' : 'sell'}`}>
                        {isBuy ? 'BUY' : 'SELL'}
                      </span>
                    </div>

                    <div className="transaction-details">
                      <div className="transaction-detail">
                        <span className="transaction-detail-label">Shares</span>
                        <span className="transaction-detail-value">
                          {formatShares(txn.change)}
                        </span>
                      </div>

                      {txn.transactionPrice && (
                        <div className="transaction-detail">
                          <span className="transaction-detail-label">Price</span>
                          <span className="transaction-detail-value">
                            {formatPrice(txn.transactionPrice)}
                          </span>
                        </div>
                      )}

                      <div className="transaction-detail">
                        <span className="transaction-detail-label">Date</span>
                        <span className="transaction-detail-value">
                          {formatDate(txn.transactionDate)}
                        </span>
                      </div>
                    </div>

                    {txn.transactionPrice && txn.change !== null && txn.change !== undefined && (
                      <div className="transaction-value">
                        Total: ~${((Math.abs(txn.change) * txn.transactionPrice) / 1000000).toFixed(2)}M
                      </div>
                    )}
                  </div>
                </div>
              );
            })}
          </div>

          {transactions.length > 10 && (
            <div className="transactions-footer">
              Showing 10 of {transactions.length} transactions
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export default InsiderTransactions;
