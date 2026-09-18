import React from 'react';

/**
 * EventFilterBar
 * Multi-dimensional filter toolbar for operational events:
 * Severity selector, category filter pills, time window presets, and instant search.
 */
export const EventFilterBar = ({
  selectedSeverity = 'ALL',
  onSelectSeverity,
  selectedCategory = 'ALL',
  onSelectCategory,
  selectedTimeRange = 'ALL',
  onSelectTimeRange,
  searchQuery = '',
  onSearchChange,
  onResetFilters
}) => {
  const severities = ['ALL', 'CRITICAL', 'WARNING', 'INFO'];

  const categories = [
    'ALL',
    'SENSOR',
    'ALERT',
    'ENERGY',
    'LOGISTICS',
    'RESEARCH',
    'SYSTEM',
    'COMMUNICATION',
    'MAINTENANCE',
    'MISSION'
  ];

  const timeRanges = [
    { id: 'ALL', label: 'ALL TIME' },
    { id: '1H', label: 'LAST 1 HOUR' },
    { id: '6H', label: 'LAST 6 HOURS' },
    { id: '24H', label: 'LAST 24 HOURS' },
    { id: '7D', label: 'LAST 7 DAYS' }
  ];

  const hasActiveFilters =
    selectedSeverity !== 'ALL' ||
    selectedCategory !== 'ALL' ||
    selectedTimeRange !== 'ALL' ||
    searchQuery.trim() !== '';

  return (
    <section className="event-filter-bar-card" aria-label="Event Timeline Filters">
      {/* Top row: Search input + Time Range Presets */}
      <div className="filter-top-row">
        <div className="event-search-wrapper">
          <span className="search-icon">🔍</span>
          <input
            type="text"
            className="event-search-input"
            placeholder="Search events by title, description, sensor ID, zone, mission, category..."
            value={searchQuery}
            onChange={(e) => onSearchChange(e.target.value)}
            aria-label="Search events"
          />
          {searchQuery && (
            <button
              type="button"
              className="search-clear-btn"
              onClick={() => onSearchChange('')}
              aria-label="Clear search"
            >
              ✕
            </button>
          )}
        </div>

        <div className="time-range-presets" role="group" aria-label="Time range filters">
          {timeRanges.map((tr) => (
            <button
              key={tr.id}
              type="button"
              className={`time-preset-btn ${selectedTimeRange === tr.id ? 'active' : ''}`}
              onClick={() => onSelectTimeRange(tr.id)}
            >
              {tr.label}
            </button>
          ))}
        </div>

        {hasActiveFilters && (
          <button
            type="button"
            className="reset-filters-btn"
            onClick={onResetFilters}
          >
            RESET FILTERS ✕
          </button>
        )}
      </div>

      {/* Middle row: Severity Selector */}
      <div className="filter-severity-row">
        <span className="filter-group-label">SEVERITY:</span>
        <div className="severity-btn-group">
          {severities.map((sev) => {
            const isSelected = selectedSeverity === sev;
            const cls = sev.toLowerCase();
            return (
              <button
                key={sev}
                type="button"
                className={`severity-filter-btn ${cls} ${isSelected ? 'active' : ''}`}
                onClick={() => onSelectSeverity(sev)}
              >
                ● {sev}
              </button>
            );
          })}
        </div>
      </div>

      {/* Bottom row: Category Filter Tabs */}
      <div className="filter-categories-row" role="tablist" aria-label="Category tabs">
        <span className="filter-group-label">CATEGORY:</span>
        <div className="categories-scroll-wrap">
          {categories.map((cat) => (
            <button
              key={cat}
              type="button"
              role="tab"
              aria-selected={selectedCategory === cat}
              className={`category-pill-btn ${selectedCategory === cat ? 'active' : ''}`}
              onClick={() => onSelectCategory(cat)}
            >
              {cat}
            </button>
          ))}
        </div>
      </div>
    </section>
  );
};

export default EventFilterBar;
