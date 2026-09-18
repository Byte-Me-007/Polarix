import React from 'react';

/**
 * AlertFilterBar
 * Provides multi-dimensional filtering for operational alert monitoring:
 * - Severity buttons (ALL, CRITICAL, WARNING, OFFLINE, ACKNOWLEDGED)
 * - Zone dropdown selector (MAIN BUILDING, RESEARCH, ENERGY, GENERATOR, STORAGE, COMMUNICATIONS)
 * - Search input matching sensor IDs, titles, and messages
 */
export const AlertFilterBar = ({
  activeSeverity = 'ALL',
  onSelectSeverity,
  selectedZone = 'ALL',
  onSelectZone,
  searchQuery = '',
  onSearchChange,
  availableZones = [
    'MAIN BUILDING',
    'RESEARCH',
    'ENERGY',
    'GENERATOR',
    'STORAGE',
    'COMMUNICATIONS'
  ]
}) => {
  const severityTabs = [
    { key: 'ALL', label: 'ALL' },
    { key: 'CRITICAL', label: 'CRITICAL' },
    { key: 'WARNING', label: 'WARNING' },
    { key: 'OFFLINE', label: 'OFFLINE' },
    { key: 'ACKNOWLEDGED', label: 'ACKNOWLEDGED' }
  ];

  return (
    <div className="alert-filter-toolbar" role="toolbar" aria-label="Alert Filters">
      {/* 1. Severity Filter Buttons */}
      <div className="alert-filter-pills" role="tablist">
        {severityTabs.map((tab) => {
          const isActive = activeSeverity === tab.key;
          return (
            <button
              key={tab.key}
              type="button"
              role="tab"
              aria-selected={isActive}
              className={`filter-pill-btn ${isActive ? 'active' : ''} ${tab.key.toLowerCase()}`}
              onClick={() => onSelectSeverity && onSelectSeverity(tab.key)}
            >
              {tab.label}
            </button>
          );
        })}
      </div>

      {/* 2. Zone Filter & Search Inputs */}
      <div className="alert-filter-controls">
        {/* Zone Selector */}
        <div className="filter-select-group">
          <label htmlFor="alert-zone-filter" className="filter-select-label">
            ZONE:
          </label>
          <select
            id="alert-zone-filter"
            className="filter-dropdown"
            value={selectedZone}
            onChange={(e) => onSelectZone && onSelectZone(e.target.value)}
          >
            <option value="ALL">ALL ZONES</option>
            {availableZones.map((z) => (
              <option key={z} value={z}>
                {z}
              </option>
            ))}
          </select>
        </div>

        {/* Search Field */}
        <div className="filter-search-group">
          <input
            type="text"
            className="filter-search-input"
            placeholder="SEARCH SENSOR / ALERT..."
            value={searchQuery}
            onChange={(e) => onSearchChange && onSearchChange(e.target.value)}
            aria-label="Search sensor or alert keywords"
          />
          {searchQuery && (
            <button
              type="button"
              className="filter-search-clear"
              onClick={() => onSearchChange && onSearchChange('')}
              title="Clear search"
            >
              ×
            </button>
          )}
        </div>
      </div>
    </div>
  );
};

export default AlertFilterBar;
