import React from 'react';

/**
 * ReplayController — REPLAY mode UI architecture.
 *
 * Full incident replay requires historical state snapshots from backend.
 * This component renders the UI skeleton and demonstrates compatibility
 * with the existing Events timeline architecture.
 *
 * When connected to a backend:
 *   - incident_id, timestamp, event sequence, and state snapshots
 *     would be loaded and the scrubber would enable.
 *
 * For now: renders the control with DEMO SCENARIO integration.
 */

const SCENARIO_TIMELINE = [
  { t: 0,  label: 'NORMAL',          color: '#4f6f52', note: 'All systems nominal' },
  { t: 12, label: 'RENEWABLES ↓',    color: '#b26814', note: 'Solar output drops' },
  { t: 24, label: 'BATT DISCHARGE',  color: '#b26814', note: 'Battery sustaining load' },
  { t: 36, label: 'GEN START',       color: '#b5382b', note: 'Diesel generator activates' },
  { t: 48, label: 'POWER CONSERV.',  color: '#b5382b', note: 'Non-essential loads shed' },
  { t: 60, label: 'ALERT ACTIVE',    color: '#b5382b', note: 'Critical alert generated' },
  { t: 72, label: 'ACKNOWLEDGED',    color: '#5d6672', note: 'Operator acknowledged' }
];

export const ReplayController = ({ activeScenario }) => {
  const isAvailable = false; // Set true when backend provides historical snapshots

  return (
    <div className="replay-controller-dock">
      {/* Header */}
      <div className="replay-header">
        <span className="replay-title">INCIDENT REPLAY</span>
        {!isAvailable && (
          <span className="replay-unavail-badge">LIVE DATA ONLY</span>
        )}
      </div>

      {/* Architecture preview: scenario event markers */}
      <div className="replay-timeline-track">
        <div className="replay-track-bar">
          {SCENARIO_TIMELINE.map((ev, i) => (
            <div
              key={i}
              className="replay-event-marker"
              style={{
                left: `${(ev.t / 72) * 100}%`,
                '--marker-color': ev.color
              }}
              title={`${ev.label} — ${ev.note}`}
            >
              <div className="replay-marker-dot" />
              <div className="replay-marker-label">{ev.label}</div>
            </div>
          ))}
          {/* Scrubber handle — disabled until backend provides snapshots */}
          <div
            className={`replay-scrubber-handle ${isAvailable ? 'active' : 'disabled'}`}
            style={{ left: '0%' }}
          />
        </div>

        {/* Time axis */}
        <div className="replay-time-axis">
          {SCENARIO_TIMELINE.map((ev, i) => (
            <div key={i} style={{ left: `${(ev.t / 72) * 100}%` }} className="replay-time-tick">
              T+{ev.t}m
            </div>
          ))}
        </div>
      </div>

      {/* Status note */}
      <div className="replay-status-note">
        {isAvailable
          ? 'Drag playhead to inspect station state at any incident timestamp.'
          : (
            <>
              <span style={{ opacity: 0.6 }}>REPLAY DATA UNAVAILABLE</span>
              {' — '}
              <span>Use Demo Mode scenarios to simulate incident propagation in real-time.</span>
            </>
          )
        }
      </div>
    </div>
  );
};

export default ReplayController;
