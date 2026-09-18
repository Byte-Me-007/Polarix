/**
 * eventService.js
 * Extensible service abstraction for station event stream, mission logs, and timeline telemetry.
 * Ready for future REST (/api/v1/events), WebSocket, or MQTT ingestion with fallback
 * to local simulated Antarctic expedition history.
 */

import { BASE_EVENTS, SCENARIO_EVENTS } from '../data/eventsData';

class EventService {
  constructor() {
    this.subscribers = new Set();
    this.backendConnected = false;
    this.baseUrl = '';
    this.localOverrides = [];
  }

  /**
   * Subscribe to live event feed
   */
  subscribe(callback) {
    this.subscribers.add(callback);
    return () => this.subscribers.delete(callback);
  }

  notifySubscribers(eventType, data) {
    this.subscribers.forEach((cb) => {
      try {
        cb(eventType, data);
      } catch (err) {
        console.error('[EventService] Subscriber error:', err);
      }
    });
  }

  /**
   * Fetch events for a given station and active scenario
   */
  async getEvents(stationId = 'MAITRI', scenario = 'NORMAL') {
    if (this.backendConnected) {
      try {
        const response = await fetch(`${this.baseUrl}/events?station=${stationId}&scenario=${scenario}`);
        if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
        return await response.json();
      } catch (err) {
        console.warn('[EventService] Remote endpoint unavailable, falling back to local simulation:', err);
      }
    }

    // Local simulation store
    const base = BASE_EVENTS[stationId] || BASE_EVENTS.MAITRI;
    const scenarioAdditions = SCENARIO_EVENTS[scenario] || [];

    // Combine scenario events at the top (newest first), then base events, then user local additions
    const combined = [...this.localOverrides, ...scenarioAdditions, ...base];

    // Deduplicate by ID
    const seen = new Set();
    const result = [];
    for (const evt of combined) {
      if (!seen.has(evt.id)) {
        seen.add(evt.id);
        result.push(evt);
      }
    }

    return Promise.resolve(result);
  }

  /**
   * Inject a new event locally or dispatch to backend
   */
  async emitEvent(newEvent) {
    const formatted = {
      id: newEvent.id || `EVT-${Date.now()}`,
      timestamp: newEvent.timestamp || new Date().toLocaleTimeString('en-GB', { timeZone: 'UTC' }) + ' UTC',
      date: newEvent.date || new Date().toISOString().split('T')[0],
      isToday: true,
      timeAgo: 'Just now',
      category: newEvent.category || 'SYSTEM',
      severity: newEvent.severity || 'INFO',
      title: newEvent.title || 'System Activity Recorded',
      description: newEvent.description || '',
      zone: newEvent.zone || 'MAIN BUILDING',
      source: newEvent.source || 'POLARIS OPERATIONAL EVENT STREAM',
      status: 'ACTIVE',
      ...newEvent
    };

    if (this.backendConnected) {
      try {
        const res = await fetch(`${this.baseUrl}/events`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(formatted)
        });
        const saved = await res.json();
        this.notifySubscribers('NEW_EVENT', saved);
        return saved;
      } catch (err) {
        console.warn('[EventService] Remote emit failed, queuing locally:', err);
      }
    }

    this.localOverrides.unshift(formatted);
    this.notifySubscribers('NEW_EVENT', formatted);
    return formatted;
  }

  /**
   * Find correlated events by causal IDs
   */
  getCorrelatedEvents(allEvents, targetEvent) {
    if (!targetEvent || !targetEvent.related_event_ids || targetEvent.related_event_ids.length === 0) {
      return [];
    }
    const relatedIds = new Set(targetEvent.related_event_ids);
    return allEvents.filter((e) => relatedIds.has(e.id));
  }
}

export const eventService = new EventService();
export default eventService;
