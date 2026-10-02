import { TrendingUp, TrendingDown } from 'lucide-react';
import type { Sync } from '../../types';
import './StockDataPanel.css';

interface StockDataPanelProps {
  sync: Sync;
  ticker: string | null;
}

function StockDataPanel({ sync, ticker }: StockDataPanelProps) {
  if (!sync.stock_price) {
    return null;
  }

  const priceChange = sync.price_change || 0;
  const isPositive = priceChange >= 0;
  const financials = sync.financials;

  const formatMarketCap = (value: number | undefined) => {
    if (!value) return null;
    if (value >= 1e12) return `$${(value / 1e12).toFixed(2)}T`;
    if (value >= 1e9) return `$${(value / 1e9).toFixed(2)}B`;
    if (value >= 1e6) return `$${(value / 1e6).toFixed(2)}M`;
    return `$${value.toLocaleString()}`;
  };

  const formatPercentage = (value: number | undefined) => {
    if (value === undefined) return null;
    return `${(value * 100).toFixed(2)}%`;
  };

  return (
    <div className="stock-data-panel">
      <h2 className="section-title">Stock Data</h2>

      {ticker && (
        <div className="price-chart">
          <iframe
            src={`https://www.tradingview.com/widgetembed/?frameElementId=tradingview_chart&symbol=${ticker}&interval=D&hidesidetoolbar=1&symboledit=1&saveimage=0&toolbarbg=f1f3f6&studies=[]&theme=light&style=1&timezone=Etc%2FUTC&withdateranges=1&showpopupbutton=1&studies_overrides={}&overrides={}&enabled_features=[]&disabled_features=[]&showpopupbutton=1&locale=en&utm_source=localhost&utm_medium=widget_new&utm_campaign=chart&utm_term=${ticker}`}
            title="TradingView Chart"
            width="100%"
            height="400"
            frameBorder="0"
            allowTransparency={true}
            scrolling="no"
          />
        </div>
      )}

      <div className="stock-grid">
        <div className="stock-item stock-price-main">
          <div className="stock-label">Current Price</div>
          <div className="stock-value-large">
            ${sync.stock_price.toFixed(2)}
          </div>
          {sync.price_change !== null && (
            <div
              className={`price-change-large ${isPositive ? 'positive' : 'negative'}`}
            >
              {isPositive ? <TrendingUp size={20} /> : <TrendingDown size={20} />}
              {isPositive ? '+' : ''}
              {priceChange.toFixed(2)}%
            </div>
          )}
        </div>

        {(sync.market_cap || financials?.marketCapitalization) && (
          <div className="stock-item">
            <div className="stock-label">Market Cap</div>
            <div className="stock-value">
              {sync.market_cap || formatMarketCap(financials?.marketCapitalization)}
            </div>
          </div>
        )}

        {((sync.pe_ratio !== null && sync.pe_ratio !== undefined) || (financials?.peRatio !== null && financials?.peRatio !== undefined)) && (
          <div className="stock-item">
            <div className="stock-label">P/E Ratio</div>
            <div className="stock-value">
              {sync.pe_ratio !== null && sync.pe_ratio !== undefined
                ? sync.pe_ratio.toFixed(2)
                : financials!.peRatio!.toFixed(2)}
            </div>
          </div>
        )}

        {sync.volume && (
          <div className="stock-item">
            <div className="stock-label">Volume</div>
            <div className="stock-value">{sync.volume.toLocaleString()}</div>
          </div>
        )}

        {sync.fifty_two_wk_hi !== null && sync.fifty_two_wk_hi !== undefined && (
          <div className="stock-item">
            <div className="stock-label">52-Week High</div>
            <div className="stock-value">${sync.fifty_two_wk_hi.toFixed(2)}</div>
          </div>
        )}

        {sync.fifty_two_wk_lo !== null && sync.fifty_two_wk_lo !== undefined && (
          <div className="stock-item">
            <div className="stock-label">52-Week Low</div>
            <div className="stock-value">${sync.fifty_two_wk_lo.toFixed(2)}</div>
          </div>
        )}

        {financials?.eps !== null && financials?.eps !== undefined && (
          <div className="stock-item">
            <div className="stock-label">EPS</div>
            <div className="stock-value">${financials.eps.toFixed(2)}</div>
          </div>
        )}

        {financials?.beta !== null && financials?.beta !== undefined && (
          <div className="stock-item">
            <div className="stock-label">Beta</div>
            <div className="stock-value">{financials.beta.toFixed(2)}</div>
          </div>
        )}

        {financials?.dividendYield && (
          <div className="stock-item">
            <div className="stock-label">Dividend Yield</div>
            <div className="stock-value">{formatPercentage(financials.dividendYield)}</div>
          </div>
        )}

        {financials?.profitMargin && (
          <div className="stock-item">
            <div className="stock-label">Profit Margin</div>
            <div className="stock-value">{formatPercentage(financials.profitMargin)}</div>
          </div>
        )}

        {financials?.pbRatio !== null && financials?.pbRatio !== undefined && (
          <div className="stock-item">
            <div className="stock-label">P/B Ratio</div>
            <div className="stock-value">{financials.pbRatio.toFixed(2)}</div>
          </div>
        )}
      </div>
    </div>
  );
}

export default StockDataPanel;
