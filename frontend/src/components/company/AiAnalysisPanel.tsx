import { useState } from 'react';
import { Brain, ChevronDown, ChevronUp } from 'lucide-react';
import type { Sync } from '../../types';
import SentimentBadge from '../shared/SentimentBadge';
import './AiAnalysisPanel.css';

interface AiAnalysisPanelProps {
  sync: Sync;
  companyName: string;
  ticker: string | null;
  status: string;
}

function AiAnalysisPanel({ sync, companyName, ticker, status }: AiAnalysisPanelProps) {
  const [showPrompt, setShowPrompt] = useState(false);

  if (!sync.ai_summary && !sync.ai_sentiment) {
    return null;
  }

  // Reconstruct the prompt that was sent to the LLM
  const buildPrompt = () => {
    let prompt = `You are a financial analyst. Analyze the following information about ${companyName}`;

    if (ticker) {
      prompt += ` (${ticker})`;
    }

    prompt += `.\n\nCompany Status: ${status.replace('_', ' ')}\n`;

    // Stock data
    if (sync.stock_price) {
      prompt += '\nStock Data:\n';
      prompt += `- Current Price: $${sync.stock_price.toFixed(2)}\n`;
      if (sync.price_change !== null && sync.price_change !== undefined) {
        prompt += `- Price Change: ${sync.price_change.toFixed(2)}%\n`;
      }
      if (sync.market_cap) {
        prompt += `- Market Cap: ${sync.market_cap}\n`;
      }
      if (sync.pe_ratio !== null && sync.pe_ratio !== undefined) {
        prompt += `- P/E Ratio: ${sync.pe_ratio.toFixed(2)}\n`;
      }
    } else {
      prompt += '\nStock Data: N/A (not publicly traded)\n';
    }

    // Analyst ratings
    if (sync.analyst_ratings) {
      prompt += '\nAnalyst Ratings:\n';
      if (sync.analyst_ratings.buy) prompt += `- Buy: ${sync.analyst_ratings.buy}\n`;
      if (sync.analyst_ratings.hold) prompt += `- Hold: ${sync.analyst_ratings.hold}\n`;
      if (sync.analyst_ratings.sell) prompt += `- Sell: ${sync.analyst_ratings.sell}\n`;
      if (sync.analyst_ratings.strongBuy) prompt += `- Strong Buy: ${sync.analyst_ratings.strongBuy}\n`;
      if (sync.analyst_ratings.strongSell) prompt += `- Strong Sell: ${sync.analyst_ratings.strongSell}\n`;
    }

    // Insider transactions
    if (sync.insider_transactions && sync.insider_transactions.length > 0) {
      prompt += `\nRecent Insider Transactions (${sync.insider_transactions.length} transactions):\n`;
      sync.insider_transactions.slice(0, 5).forEach((txn, i) => {
        if (txn.change !== null && txn.change !== undefined) {
          const transactionType = txn.change > 0 ? 'Bought' : 'Sold';
          prompt += `${i + 1}. ${txn.name} ${transactionType} ${Math.abs(txn.change).toLocaleString()} shares\n`;
        }
      });
    }

    // News
    if (sync.raw_news && sync.raw_news.length > 0) {
      prompt += `\nRecent News (${sync.raw_news.length} articles):\n`;
      sync.raw_news.forEach((article, i) => {
        prompt += `\n${i + 1}. ${article.title}`;
        if (article.source) {
          prompt += ` - ${article.source}`;
        }
        prompt += '\n';
      });
    } else {
      prompt += '\nRecent News: No recent news found\n';
    }

    prompt += `
Based on the information above, provide:

1. A concise summary (2-3 paragraphs) of recent developments and the company's current situation.
   - Consider stock performance, analyst sentiment, insider activity, and news developments
   - If analyst ratings show strong consensus (mostly buy or sell), mention it
   - If insider transactions show significant buying or selling, note this as it can signal confidence or concern
2. Overall sentiment analysis.

Format your response EXACTLY as follows:

SUMMARY:
[Your 2-3 paragraph summary here]

SENTIMENT: [Choose ONE: bullish, bearish, neutral, or mixed]

Be objective and balanced in your analysis. Focus on facts from the data and news provided.`;

    return prompt;
  };

  return (
    <div className="ai-analysis-panel">
      <div className="ai-header">
        <div className="ai-title">
          <Brain size={20} />
          <h2 className="section-title">AI Analysis</h2>
        </div>
        {sync.ai_sentiment && <SentimentBadge sentiment={sync.ai_sentiment} />}
      </div>

      {sync.ai_summary && (
        <div className="ai-summary">
          {sync.ai_summary.split('\n').map((paragraph, index) => (
            <p key={index}>{paragraph}</p>
          ))}
        </div>
      )}

      {!sync.ai_summary && sync.ai_sentiment && (
        <div className="ai-summary">
          <p className="ai-no-summary">
            Sentiment analysis available, but no detailed summary was generated.
          </p>
        </div>
      )}

      <button
        className="show-prompt-button"
        onClick={() => setShowPrompt(!showPrompt)}
      >
        {showPrompt ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
        {showPrompt ? 'Hide' : 'Show'} LLM Prompt
        {!sync.llm_prompt && <span className="prompt-reconstructed">(reconstructed)</span>}
      </button>

      {showPrompt && (
        <div className="ai-prompt">
          <pre>{sync.llm_prompt || buildPrompt()}</pre>
        </div>
      )}
    </div>
  );
}

export default AiAnalysisPanel;
