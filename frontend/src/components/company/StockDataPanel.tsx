import type { Sync } from '../../types';
import { money } from '../../lib/format';
import './StockDataPanel.css';

interface StockDataPanelProps {
  sync: Sync;
  ticker: string | null;
  /** The freshest price (livePrice()); placed on the 52-week range. */
  live: { price: number; change: number | null } | null;
}

const marketCap = (value: number | undefined) => {
  if (!value) return null;
  // Finnhub reports market cap in millions
  const dollars = value * 1e6;
  if (dollars >= 1e12) return `$${(dollars / 1e12).toFixed(2)}T`;
  if (dollars >= 1e9) return `$${(dollars / 1e9).toFixed(2)}B`;
  return `$${(dollars / 1e6).toFixed(0)}M`;
};

const percent = (value: number | undefined | null) => (value == null ? null : `${(value * 100).toFixed(2)}%`);
const fixed = (value: number | undefined | null) => (value == null ? null : value.toFixed(2));

/** Where the price sits in its 52-week range. */
function RangeBar({ lo, hi, price }: { lo: number; hi: number; price: number }) {
  const at = Math.min(100, Math.max(0, ((price - lo) / (hi - lo || 1)) * 100));
  const fromHigh = (price / hi - 1) * 100;
  return (
    <div className="sd-range">
      <div className="sd-range-head">
        <span className="sd-label">52-week range</span>
        <span className="muted">{fromHigh > -0.5 ? 'at the 52-week high' : `${Math.round(-fromHigh)}% below the high`}</span>
      </div>
      <div className="sd-range-track" role="img" aria-label={`${money(price)} within a 52-week range of ${money(lo)} to ${money(hi)}`}>
        <div className="sd-range-fill" style={{ width: `${at}%` }} />
        <div className="sd-range-marker" style={{ left: `${at}%` }} />
      </div>
      <div className="sd-range-ends num"><span>{money(lo)}</span><span>{money(hi)}</span></div>
    </div>
  );
}

/** Chart, valuation and risk numbers for a public company (the price itself is in the page header). */
function StockDataPanel({ sync, ticker, live }: StockDataPanelProps) {
  const price = live?.price ?? sync.stock_price;
  const f = sync.financials;
  const stats = [
    { label: 'Market cap', value: sync.market_cap || marketCap(f?.marketCapitalization) },
    { label: 'P/E', value: fixed(sync.pe_ratio ?? f?.peRatio) },
    { label: 'EPS', value: f?.eps != null ? money(f.eps) : null },
    { label: 'Beta', value: fixed(f?.beta) },
    { label: 'Volume', value: sync.volume ? sync.volume.toLocaleString() : null },
    { label: 'Dividend yield', value: f?.dividendYield ? percent(f.dividendYield) : null },
    { label: 'Profit margin', value: f?.profitMargin ? percent(f.profitMargin) : null },
    { label: 'P/B', value: fixed(f?.pbRatio) },
  ].filter((s) => s.value);
  const lo = sync.fifty_two_wk_lo, hi = sync.fifty_two_wk_hi;

  if (!ticker && !stats.length) return null;

  return (
    <div className="stock-data-panel">
      <h2 className="section-title">Stock data</h2>

      {ticker && (
        <div className="sd-chart">
          <iframe
            src={`https://www.tradingview.com/widgetembed/?frameElementId=tradingview_chart&symbol=${ticker}&interval=D&hidesidetoolbar=1&symboledit=1&saveimage=0&toolbarbg=1a1f2e&studies=[]&theme=dark&style=1&timezone=Etc%2FUTC&withdateranges=1&showpopupbutton=1&studies_overrides={}&overrides={}&enabled_features=[]&disabled_features=[]&showpopupbutton=1&locale=en&utm_source=localhost&utm_medium=widget_new&utm_campaign=chart&utm_term=${ticker}`}
            title="TradingView Chart"
            width="100%"
            height="400"
            frameBorder="0"
            allowTransparency={true}
            scrolling="no"
          />
        </div>
      )}

      {price != null && lo != null && hi != null && hi > lo && <RangeBar lo={lo} hi={hi} price={price} />}

      {stats.length > 0 && (
        <dl className="sd-stats">
          {stats.map((s) => (
            <div key={s.label} className="sd-stat">
              <dt className="sd-label">{s.label}</dt>
              <dd className="num">{s.value}</dd>
            </div>
          ))}
        </dl>
      )}
    </div>
  );
}

export default StockDataPanel;
