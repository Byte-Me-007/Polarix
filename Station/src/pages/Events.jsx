import React, { useState, useEffect, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import { useStationTelemetry } from '../hooks/useStationTelemetry';
import { StationSelector } from '../components/StationSelector';
import { DemoMode } from '../components/DemoMode';
import { eventService } from '../services/eventService';

import { EventCountersStrip } from '../components/events/EventCountersStrip';
import { EventFilterBar } from '../components/events/EventFilterBar';
import { EventTimeline } from '../components/events/EventTimeline';
import { EventDetailDrawer } from '../components/events/EventDetailDrawer';

/**
 * Events Page
 * Unified operational mission timeline connecting telemetry, incidents, energy, logistics, and research.
 * Directly answers:
 * WHAT HAPPENED → WHEN → WHERE → WHICH SYSTEM → WHAT ACTION FOLLOWED?
 */
export const Events = () => {
  const navigate = useNavigate();
  const {
    config,
    activeStation,
    scenario
  } = useStationTelemetry();

  const [rawEvents, setRawEvents] = useState([]);
  const [selectedEventId, setSelectedEventId] = useState(null);

  // Filters State
  const [selectedSeverity, setSelectedSeverity] = useState('ALL');
  const [selectedCategory, setSelectedCategory] = useState('ALL');
  const [selectedTimeRange, setSelectedTimeRange] = useState('ALL');
  const [searchQuery, setSearchQuery] = useState('');

  // Load events for active station and scenario via eventService
  useEffect(() => {
    let isMounted = true;
    eventService.getEvents(activeStation, scenario).then((events) => {
      if (isMounted) {
        setRawEvents(events);
        // Default select top event if none selected or selection not in list
        if (events.length > 0 && (!selectedEventId || !events.find((e) => e.id === selectedEventId))) {
          setSelectedEventId(events[0].id);
        }
      }
    });

    // Subscribe to live new events
    const unsubscribe = eventService.subscribe((eventType, newEvt) => {
      if (eventType === 'NEW_EVENT') {
        setRawEvents((prev) => [newEvt, ...prev]);
        setSelectedEventId(newEvt.id);
      }
    });

    return () => {
      isMounted = false;
      unsubscribe();
    };
  }, [activeStation, scenario]);

  // Derived filtered events
  const filteredEvents = useMemo(() => {
    return rawEvents.filter((e) => {
      // 1. Severity filter
      if (selectedSeverity !== 'ALL' && e.severity !== selectedSeverity) {
        return false;
      }

      // 2. Category filter
      if (selectedCategory !== 'ALL' && e.category !== selectedCategory) {
        return false;
      }

      // 3. Time Range Filter (simulated against mock timestamps)
      if (selectedTimeRange === '1H') {
        // Only events within 1 hour (contains 'm ago' or 'Just now', but not 'h ago' and must be today)
        if (!e.isToday || (e.timeAgo && e.timeAgo.includes('h ago'))) return false;
      } else if (selectedTimeRange === '6H') {
        if (!e.isToday) return false;
        if (e.timeAgo && e.timeAgo.includes('h ago')) {
          const hours = parseInt(e.timeAgo);
          if (!isNaN(hours) && hours > 6) return false;
        }
      } else if (selectedTimeRange === '24H') {
        if (!e.isToday) return false;
      }

      // 4. Free-text Search
      if (searchQuery.trim() !== '') {
        const query = searchQuery.toLowerCase();
        const titleMatch = (e.title || '').toLowerCase().includes(query);
        const descMatch = (e.description || '').toLowerCase().includes(query);
        const sensorMatch = (e.sensor_id || '').toLowerCase().includes(query);
        const zoneMatch = (e.zone || '').toLowerCase().includes(query);
        const missionMatch = (e.mission_id || '').toLowerCase().includes(query);
        const catMatch = (e.category || '').toLowerCase().includes(query);
        const idMatch = (e.id || '').toLowerCase().includes(query);

        if (!titleMatch && !descMatch && !sensorMatch && !zoneMatch && !missionMatch && !catMatch && !idMatch) {
          return false;
        }
      }

      return true;
    });
  }, [rawEvents, selectedSeverity, selectedCategory, selectedTimeRange, searchQuery]);

  // Currently inspected event
  const selectedEvent = useMemo(() => {
    if (!selectedEventId) return null;
    return rawEvents.find((e) => e.id === selectedEventId) || null;
  }, [rawEvents, selectedEventId]);

  // Counter metrics derived from rawEvents
  const todayCount = rawEvents.filter((e) => e.isToday).length;
  const criticalCount = rawEvents.filter((e) => e.severity === 'CRITICAL').length;
  const warningCount = rawEvents.filter((e) => e.severity === 'WARNING').length;
  const infoCount = rawEvents.filter((e) => e.severity === 'INFO' || e.severity === 'NORMAL').length;
  const lastEventTime = rawEvents.length > 0 ? rawEvents[0].timestamp : 'TIME UNAVAILABLE';

  // Cross Navigation Handlers
  const handleViewSensor = (sensorId) => {
    navigate('/digital-twin', { state: { locateSensorId: sensorId } });
  };

  const handleViewAlert = (alertId) => {
    navigate('/alerts', { state: { highlightAlertId: alertId } });
  };

  const handleViewEnergy = () => {
    navigate('/energy');
  };

  const handleViewLogistics = () => {
    navigate('/logistics');
  };

  const handleResetFilters = () => {
    setSelectedSeverity('ALL');
    setSelectedCategory('ALL');
    setSelectedTimeRange('ALL');
    setSearchQuery('');
  };

  const stationTitle = config.displayName || `${activeStation} Research Station`;
  const stationCode = config.shortCode || config.id || activeStation;

  return (
    <main className="main-viewport events-page-container">
      {/* ─────────────────────────────────────────────────────────────── */}
      {/* 1. OPERATIONAL EVENTS HEADER                                    */}
      {/* ─────────────────────────────────────────────────────────────── */}
      <section className="events-header-bar" aria-label="Events Management Header">
        <div className="events-title-group">
          <h1>EVENTS & MISSION LOG</h1>
          <p className="events-subtitle">
            STATION ACTIVITY / INCIDENTS / OPERATIONS TIMELINE
          </p>
        </div>

        <div className="events-header-right">
          <StationSelector />

          <div className="events-station-badge">
            <span className="station-name-tag">
              {stationCode} // {stationTitle.toUpperCase()}
            </span>
            <span className="online-indicator">
              <span className="status-dot-sm live" />
              ONLINE
            </span>
          </div>

          <div className="events-today-badge-pill">
            <span className="badge-label">EVENTS TODAY:</span>
            <span className="badge-val">{todayCount}</span>
          </div>

          <div className="last-event-badge-pill">
            <span className="badge-label">LAST EVENT:</span>
            <span className="badge-val">{lastEventTime}</span>
          </div>
        </div>
      </section>

      {/* ─────────────────────────────────────────────────────────────── */}
      {/* 2. EXECUTIVE EVENT COUNTERS STRIP                               */}
      {/* ─────────────────────────────────────────────────────────────── */}
      <EventCountersStrip
        totalCount={rawEvents.length}
        criticalCount={criticalCount}
        warningCount={warningCount}
        infoCount={infoCount}
        lastEventTime={lastEventTime}
      />

      {/* ─────────────────────────────────────────────────────────────── */}
      {/* 3. MULTI-TIER FILTER & SEARCH BAR                               */}
      {/* ─────────────────────────────────────────────────────────────── */}
      <EventFilterBar
        selectedSeverity={selectedSeverity}
        onSelectSeverity={setSelectedSeverity}
        selectedCategory={selectedCategory}
        onSelectCategory={setSelectedCategory}
        selectedTimeRange={selectedTimeRange}
        onSelectTimeRange={setSelectedTimeRange}
        searchQuery={searchQuery}
        onSearchChange={setSearchQuery}
        onResetFilters={handleResetFilters}
      />

      {/* ─────────────────────────────────────────────────────────────── */}
      {/* 4. MAIN WORKSPACE: TIMELINE + DETAIL DRAWER                     */}
      {/* ─────────────────────────────────────────────────────────────── */}
      <div className="events-workspace-layout">
        {/* Left / Center: Chronological Vertical Timeline */}
        <section className="events-timeline-section" aria-label="Chronological Activity Stream">
          <div className="timeline-header-meta">
            <span className="timeline-count-label">
              SHOWING {filteredEvents.length} OF {rawEvents.length} RECORDED EVENTS
            </span>
            {scenario !== 'NORMAL' && (
              <span className="scenario-indicator-tag">
                ● DEMO SCENARIO ACTIVE: {scenario}
              </span>
            )}
          </div>

          <EventTimeline
            events={filteredEvents}
            selectedEventId={selectedEventId}
            onSelectEvent={(evt) => setSelectedEventId(evt.id)}
            onViewSensor={handleViewSensor}
            onViewAlert={handleViewAlert}
            onViewEnergy={handleViewEnergy}
            onViewLogistics={handleViewLogistics}
          />
        </section>

        {/* Right Panel: Event Detail Drawer */}
        <EventDetailDrawer
          event={selectedEvent}
          allEvents={rawEvents}
          onClose={() => setSelectedEventId(null)}
          onSelectEvent={(evt) => setSelectedEventId(evt.id)}
          onViewSensor={handleViewSensor}
          onViewAlert={handleViewAlert}
          onViewEnergy={handleViewEnergy}
          onViewLogistics={handleViewLogistics}
        />
      </div>

      {/* ─────────────────────────────────────────────────────────────── */}
      {/* 5. EMBEDDED DEMO SIMULATION DOCK                                */}
      {/* ─────────────────────────────────────────────────────────────── */}
      <section style={{ marginTop: '0.75rem' }}>
        <DemoMode />
      </section>
    </main>
  );
};

export default Events;
