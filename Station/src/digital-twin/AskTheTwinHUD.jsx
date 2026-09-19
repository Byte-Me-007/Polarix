import React, { useState } from 'react';
import { queryTwin } from '../services/askTwinService';

/**
 * AskTheTwinHUD
 *
 * Compact mission-control natural language command bar and query engine
 * embedded inside the Digital Twin viewport HUD.
 *
 * Uses deterministic query routing and what-if simulation against live station telemetry.
 * Modular architecture ready for future Person C ML model connection.
 */
export const AskTheTwinHUD = ({
  stationCode = 'MTR',
  stationTitle = 'Maitri Research Station',
  telemetry = {},
  sensors = [],
  readiness = {}
}) => {
  const [inputQuery, setInputQuery] = useState('');
  const [response, setResponse] = useState(null);
  const [isExpanded, setIsExpanded] = useState(false);

  const handleSubmit = (e) => {
    if (e) e.preventDefault();
    if (!inputQuery.trim()) return;

    const res = queryTwin(inputQuery, {
      stationCode,
      stationTitle,
      telemetry,
      sensors,
      readiness
    });

    setResponse(res);
    setIsExpanded(true);
  };

  const handleSelectSuggested = (suggested) => {
    setInputQuery(suggested);
    const res = queryTwin(suggested, {
      stationCode,
      stationTitle,
      telemetry,
      sensors,
      readiness
    });
    setResponse(res);
    setIsExpanded(true);
  };

  const handleClear = () => {
    setResponse(null);
    setInputQuery('');
    setIsExpanded(false);
  };

  return (
    <div className={`station-hud-card hud-ask-twin ${isExpanded ? 'expanded' : ''}`} aria-label="Ask The Twin Command Interface">
      {/* ── Header ── */}
      <div className="hud-card-header ask-twin-header">
        <div className="ask-twin-header-left">
          <span className="hud-pulse-dot" style={{ background: response?.isSimulation ? 'var(--polaris-amber)' : 'var(--polaris-copper)' }} />
          <span className="hud-header-title ask-twin-brand-title">ASK THE TWIN</span>
        </div>
        <div className="ask-twin-header-right">
          <span className="ask-twin-station-pill">
            {stationCode} · TELEMETRY CLI
          </span>
          {response && (
            <button
              type="button"
              className="ask-twin-dismiss-btn"
              onClick={handleClear}
              title="Clear inquiry response"
              aria-label="Clear response"
            >
              ×
            </button>
          )}
        </div>
      </div>

      {/* ── Command Input Bar ── */}
      <form onSubmit={handleSubmit} className="ask-twin-form">
        <div className="ask-twin-input-icon">›</div>
        <input
          type="text"
          className="ask-twin-input"
          placeholder="Ask station telemetry (fuel, battery, power, risk)..."
          value={inputQuery}
          onChange={(e) => setInputQuery(e.target.value)}
          aria-label="Ask station telemetry"
        />
        <button
          type="submit"
          className="ask-twin-submit-btn"
          title="Execute telemetry query"
        >
          <span>EXEC</span>
          <kbd className="ask-twin-kbd">↵</kbd>
        </button>
      </form>

      {/* ── Response Container ── */}
      {response && (
        <div className="ask-twin-response-pane">
          {/* Response Title */}
          <div className="response-header-row">
            <div className="response-title-wrap">
              <span className={`response-status-bullet ${response.isSimulation ? 'sim' : response.status === 'SUCCESS' ? 'success' : 'alert'}`} />
              <span className={`response-tag ${response.isSimulation ? 'sim' : response.status === 'UNSUPPORTED' ? 'unsupported' : response.status === 'INSUFFICIENT' ? 'insufficient' : 'normal'}`}>
                {response.title}
              </span>
            </div>
            {response.isSimulation && (
              <span className="response-sim-pill">
                WHAT-IF SIMULATION
              </span>
            )}
          </div>

          {/* Response Content */}
          {response.status === 'SUCCESS' ? (
            <div className="response-body">
              {response.summary && (
                <div className="response-summary-text">{response.summary}</div>
              )}

              <div className="response-metrics-grid">
                {response.metrics?.map((m, idx) => (
                  <div key={idx} className={`response-metric-card ${m.isAlert ? 'metric-alert' : ''}`}>
                    <span className="response-metric-label">{m.label}</span>
                    <span className={`response-metric-val ${m.isAlert ? 'alert' : ''}`}>
                      {m.value}
                    </span>
                  </div>
                ))}
              </div>

              {response.note && (
                <div className="response-note">
                  <span className="response-note-label">NOTE:</span>
                  <span>{response.note}</span>
                </div>
              )}

              {response.source && (
                <div className="response-source">
                  <span className="source-label">DATA SOURCE:</span>
                  <span className="source-path">{response.source}</span>
                </div>
              )}
            </div>
          ) : response.status === 'INSUFFICIENT' ? (
            <div className="response-body">
              <div className="response-insufficient-msg">
                <span className="response-status-bullet alert" />
                <strong>TELEMETRY INSUFFICIENT</strong>
              </div>
              <p className="response-msg-text">{response.message}</p>
            </div>
          ) : (
            /* UNSUPPORTED QUERY */
            <div className="response-body">
              <div className="response-unsupported-msg">
                <span className="response-status-bullet" style={{ background: '#94a3b8' }} />
                <strong>QUERY NOT RECOGNIZED</strong>
              </div>
              <p className="response-msg-text">{response.message}</p>
              <div className="suggested-queries-list">
                <span className="suggested-heading">SUPPORTED OPERATIONAL INQUIRIES:</span>
                <div className="suggested-queries-chips">
                  {response.suggestedQueries?.slice(0, 4).map((sq, i) => (
                    <button
                      key={i}
                      type="button"
                      className="suggested-query-chip-btn"
                      onClick={() => handleSelectSuggested(sq)}
                    >
                      › {sq}
                    </button>
                  ))}
                </div>
              </div>
            </div>
          )}
        </div>
      )}

      {/* Suggested Quick Queries */}
      {!response && (
        <div className="ask-twin-quick-section">
          <div className="ask-twin-quick-heading">COMMON OPERATIONAL QUERIES:</div>
          <div className="ask-twin-quick-chips">
            {[
              'Days of fuel left?',
              'What is battery level?',
              'What if wind drops 20%?',
              'Is station at risk?'
            ].map((queryText, i) => (
              <button
                key={i}
                type="button"
                className="quick-chip-btn"
                onClick={() => handleSelectSuggested(queryText)}
              >
                {queryText}
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};

export default AskTheTwinHUD;
