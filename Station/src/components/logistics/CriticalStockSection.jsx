import React, { useState } from 'react';

/**
 * CriticalStockSection
 * Displays items currently flagged as WARNING or CRITICAL.
 * Clicking an item expands an inline detail drawer with storage location and consumption rate.
 */
export const CriticalStockSection = ({
  inventory = [],
  onLocateInTwin
}) => {
  const [selectedItemId, setSelectedItemId] = useState(null);

  // Filter items that are CRITICAL or WARNING (or under 30 days)
  const criticalItems = inventory.filter(
    (item) => item.status === 'CRITICAL' || item.status === 'WARNING' || item.remainingDays < 30
  );

  const toggleItemDetail = (id) => {
    setSelectedItemId((prev) => (prev === id ? null : id));
  };

  return (
    <section className="critical-stock-card" aria-label="Critical and Low Stock Alerts">
      <div className="card-header-row">
        <div>
          <h3 className="card-title">CRITICAL / LOW STOCK ATTENTION</h3>
          <span className="card-subtitle">
            ITEMS REQUIRING IMMEDIATE EXPEDITION MONITORING ({criticalItems.length})
          </span>
        </div>
        {criticalItems.length > 0 && (
          <span className="critical-count-tag">
            ● {criticalItems.length} ACTIVE DEFICIT WATCH
          </span>
        )}
      </div>

      {criticalItems.length === 0 ? (
        <div className="critical-empty-state">
          ✓ NO CRITICAL STOCK ITEMS — All inventory categories are sustained within nominal operational safety buffers.
        </div>
      ) : (
        <div className="critical-items-list">
          {criticalItems.map((item) => {
            const isCrit = item.status === 'CRITICAL' || item.remainingDays < 15;
            const color = isCrit ? '#c82a2a' : '#d9821a';
            const isSelected = selectedItemId === item.id;

            return (
              <div
                key={item.id}
                className={`critical-item-card ${isCrit ? 'is-crit' : 'is-warn'} ${isSelected ? 'is-open' : ''}`}
                style={{ borderLeftColor: color }}
              >
                <div
                  className="critical-item-header"
                  onClick={() => toggleItemDetail(item.id)}
                  role="button"
                  tabIndex={0}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter' || e.key === ' ') {
                      e.preventDefault();
                      toggleItemDetail(item.id);
                    }
                  }}
                  aria-expanded={isSelected}
                >
                  <div className="critical-item-title-group">
                    <span className="critical-icon" style={{ color }}>
                      {isCrit ? '⚠' : '◈'}
                    </span>
                    <span className="critical-name">{item.item}</span>
                    <span
                      className="critical-badge"
                      style={{
                        color,
                        borderColor: color,
                        background: isCrit ? 'rgba(200,42,42,0.08)' : 'rgba(217,130,26,0.08)'
                      }}
                    >
                      ● {item.status} ({item.priority} PRIORITY)
                    </span>
                  </div>

                  <div className="critical-metrics-group">
                    <span className="critical-days" style={{ color }}>
                      {item.remainingDays.toFixed(1)} DAYS REMAINING
                    </span>
                    <span className="expand-indicator">
                      {isSelected ? '▲' : '▼'}
                    </span>
                  </div>
                </div>

                {isSelected && (
                  <div className="critical-detail-panel">
                    <div className="critical-detail-grid">
                      <div className="c-detail-item">
                        <span className="c-label">CURRENT STOCK</span>
                        <span className="c-val">{item.stock.toLocaleString()} {item.unit}</span>
                      </div>
                      <div className="c-detail-item">
                        <span className="c-label">DAILY BURN RATE</span>
                        <span className="c-val">{item.dailyConsumption} {item.unit}/day</span>
                      </div>
                      <div className="c-detail-item">
                        <span className="c-label">STORAGE LOCATION</span>
                        <span className="c-val">{item.location}</span>
                      </div>
                      <div className="c-detail-item">
                        <span className="c-label">CATEGORY</span>
                        <span className="c-val">{item.category}</span>
                      </div>
                    </div>

                    <div className="critical-actions-row">
                      {item.sensorRef && onLocateInTwin && (
                        <button
                          type="button"
                          className="twin-locate-btn"
                          onClick={() => onLocateInTwin(item.sensorRef)}
                        >
                          ⌖ VIEW STORAGE IN DIGITAL TWIN
                        </button>
                      )}
                    </div>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}
    </section>
  );
};

export default CriticalStockSection;
