import { useState } from 'react';
import { Link } from 'react-router-dom';
import { AlertTriangle, Brain, ChevronDown, ChevronUp, GitCompareArrows } from 'lucide-react';
import type { ScoreSummary } from '../../api/client';
import type { Sync } from '../../types';
import { ago, money, pct } from '../../lib/format';
import { driftSince } from '../../lib/drift';
import SentimentBadge from '../shared/SentimentBadge';
import { EvidenceLinks, EvidenceSources } from '../shared/AnalysisEvidence';
import './AiAnalysisPanel.css';

interface Props {
  sync: Sync;
  /** How this company's past calls played out (30 days on), from the scorecard. */
  trackRecord?: ScoreSummary | null;
  /** The latest price, to show how far it has moved since the analysis was written. */
  livePrice?: number | null;
  /** Moves at least this big (%) are flagged: the analysis may no longer hold. */
  driftPercent?: number;
}

/** "4 of 13 calls on this stock were right 30 days later; after bullish calls it moved −15.7% on average." */
function TrackRecord({ s }: { s: ScoreSummary }) {
  const rate = s.hits / s.graded;
  const poor = s.graded >= 5 && rate <= 0.4;
  const bullish = s.avg_return.bullish, bearish = s.avg_return.bearish;
  return (
    <p className={`ai-track ${poor ? 'ai-track-poor' : 'muted'}`}>
      Track record: {s.hits} of {s.graded} {s.graded === 1 ? 'call' : 'calls'} on this stock were right 30 days later
      {bullish != null && <>; after bullish calls it moved {pct(bullish)} on average</>}
      {bearish != null && <>, after bearish calls {pct(bearish)}</>}.{' '}
      <Link to="/scorecard">Scorecard</Link>
    </p>
  );
}

function AiAnalysisPanel({ sync, trackRecord, livePrice, driftPercent = 15 }: Props) {
  const [showPrompt, setShowPrompt] = useState(false);
  const [showDebate, setShowDebate] = useState(false);
  if (!sync.ai_summary) return null;
  const keyPoints = sync.ai_key_points ?? [];
  const risks = sync.ai_risks ?? [];
  const drift = driftSince(sync.stock_price, livePrice);
  const evidence = sync.ai_evidence;
  const citations = (section: string, index: number) => <EvidenceLinks evidence={evidence} section={section} index={index} scope={sync.id} />;

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
      {trackRecord && <TrackRecord s={trackRecord} />}
      <p className="ai-track muted">
        {sync.analysis_horizon_days ? `${sync.analysis_horizon_days}-day outlook` : 'Outlook horizon not recorded'}
        {sync.llm_model && <> · {sync.llm_model}</>}
        {sync.prompt_version && <> · <span title="Identifies the analysis format, instructions and debate mode">{sync.prompt_version}</span></>}
      </p>
      {!evidence && <p className="ai-track muted">This older analysis has no saved evidence references. New analyses link claims to their sources.</p>}

      {drift != null && Math.abs(drift) >= driftPercent ? (
        <div className="notice notice-warning ai-drift">
          <AlertTriangle size={16} />
          <span>
            Written when the price was {money(sync.stock_price)}. It's {money(livePrice)} now ({pct(drift)}), so this
            analysis may no longer hold. A new one runs automatically after moves this big.
          </span>
        </div>
      ) : drift != null && Math.abs(drift) >= 1 ? (
        <p className="ai-track muted">Written at {money(sync.stock_price)} ({pct(drift)} since).</p>
      ) : null}

      {sync.ai_changes && (
        <div className="ai-changes">
          <GitCompareArrows size={16} />
          <div><strong>Since the last analysis:</strong> {sync.ai_changes}{citations('changes', 0)}</div>
        </div>
      )}

      <div className="ai-summary">
        {sync.ai_summary.split('\n').filter((p) => p.trim()).map((paragraph, i) => <p key={i}>{paragraph}{citations('summary', i)}</p>)}
      </div>

      {(keyPoints.length > 0 || risks.length > 0) && (
        <div className="ai-lists">
          {keyPoints.length > 0 && (
            <div>
              <h3>Key points</h3>
              <ul>{keyPoints.map((k, i) => <li key={i}>{k}{citations('key_points', i)}</li>)}</ul>
            </div>
          )}
          {risks.length > 0 && (
            <div>
              <h3>Risks</h3>
              <ul className="ai-risks">{risks.map((r, i) => <li key={i}>{r}{citations('risks', i)}</li>)}</ul>
            </div>
          )}
        </div>
      )}

      <EvidenceSources evidence={evidence} scope={sync.id} />

      {sync.ai_bull && sync.ai_bear && (
        <>
          <button className="show-prompt-button" onClick={() => setShowDebate(!showDebate)}>
            {showDebate ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
            {showDebate ? 'Hide' : 'Show'} the bull and bear cases behind this verdict
          </button>
          {showDebate && (
            <div className="ai-debate">
              <div><h3 className="up">Bull case</h3><p>{sync.ai_bull}</p></div>
              <div><h3 className="down">Bear case</h3><p>{sync.ai_bear}</p></div>
            </div>
          )}
        </>
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
