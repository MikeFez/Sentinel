import { useState } from 'react';
import { Brain, ChevronDown, ChevronUp, GitCompareArrows } from 'lucide-react';
import type { Sync } from '../../types';
import { ago } from '../../lib/format';
import SentimentBadge from '../shared/SentimentBadge';
import './AiAnalysisPanel.css';

function AiAnalysisPanel({ sync }: { sync: Sync }) {
  const [showPrompt, setShowPrompt] = useState(false);
  if (!sync.ai_summary) return null;
  const keyPoints = sync.ai_key_points ?? [];
  const risks = sync.ai_risks ?? [];

  return (
    <div className="ai-analysis-panel">
      <div className="ai-header">
        <div className="ai-title">
          <Brain size={20} />
          <h2 className="section-title">AI Analysis</h2>
          <span className="muted ai-when">{ago(sync.synced_at)}</span>
        </div>
        {sync.ai_sentiment && <SentimentBadge sentiment={sync.ai_sentiment} />}
      </div>

      {sync.ai_changes && (
        <div className="ai-changes">
          <GitCompareArrows size={16} />
          <div><strong>Since the last analysis:</strong> {sync.ai_changes}</div>
        </div>
      )}

      <div className="ai-summary">
        {sync.ai_summary.split('\n').filter((p) => p.trim()).map((paragraph, i) => <p key={i}>{paragraph}</p>)}
      </div>

      {(keyPoints.length > 0 || risks.length > 0) && (
        <div className="ai-lists">
          {keyPoints.length > 0 && (
            <div>
              <h3>Key points</h3>
              <ul>{keyPoints.map((k, i) => <li key={i}>{k}</li>)}</ul>
            </div>
          )}
          {risks.length > 0 && (
            <div>
              <h3>Risks</h3>
              <ul className="ai-risks">{risks.map((r, i) => <li key={i}>{r}</li>)}</ul>
            </div>
          )}
        </div>
      )}

      {sync.llm_prompt && (
        <>
          <button className="show-prompt-button" onClick={() => setShowPrompt(!showPrompt)}>
            {showPrompt ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
            {showPrompt ? 'Hide' : 'Show'} the prompt sent to the LLM
          </button>
          {showPrompt && <div className="ai-prompt"><pre>{sync.llm_prompt}</pre></div>}
        </>
      )}
    </div>
  );
}

export default AiAnalysisPanel;
