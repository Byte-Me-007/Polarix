/**
 * Alert Service
 * Clean abstraction layer for Alert lifecycle, acknowledgment, and real-time streaming.
 * Prepared for REST integration (POST /alerts/{id}/ack) and future WebSocket/MQTT ingestion.
 */

import { INITIAL_ALERTS } from '../data/stationData';

class AlertService {
  constructor() {
    this.subscribers = new Set();
    this.backendConnected = false; // Flag for when live backend API is attached
    this.baseUrl = ''; // Will hold backend endpoint when connected, e.g., '/api/v1'
  }

  /**
   * Fetch active and historical alerts for a given station
   */
  async getAlerts(stationId = 'MAITRI') {
    if (this.backendConnected) {
      try {
        const response = await fetch(`${this.baseUrl}/alerts?station=${stationId}`);
        if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
        return await response.json();
      } catch (err) {
        console.warn('[AlertService] Remote endpoint unavailable, falling back to local store:', err);
      }
    }

    // Local simulation fallback
    return Promise.resolve(
      INITIAL_ALERTS.filter(
        (a) => a.station === stationId || a.station === 'ALL' || a.station_id === stationId || a.station_id === 'ALL'
      )
    );
  }

  /**
   * Acknowledge an alert by ID.
   * Directly compatible with POST /alerts/{id}/ack.
   * If remote backend is not connected, safely acknowledges in local state
   * without fabricating fake HTTP response headers.
   */
  async acknowledgeAlert(alertId) {
    if (this.backendConnected) {
      try {
        const response = await fetch(`${this.baseUrl}/alerts/${alertId}/ack`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' }
        });
        if (!response.ok) throw new Error(`Failed to acknowledge alert ${alertId}`);
        const result = await response.json();
        this.notifySubscribers('ALERT_ACKNOWLEDGED', result);
        return { success: true, alertId, remote: true, data: result };
      } catch (err) {
        console.warn(`[AlertService] POST /alerts/${alertId}/ack failed:`, err);
        throw err;
      }
    }

    // Local state acknowledgment
    const ackPayload = {
      alertId,
      acknowledged: true,
      status: 'ACKNOWLEDGED',
      acknowledgedAt: new Date().toISOString(),
      remote: false
    };

    this.notifySubscribers('ALERT_ACKNOWLEDGED', ackPayload);
    return Promise.resolve({ success: true, ...ackPayload });
  }

  /**
   * Real-time subscription hook for WebSocket events:
   * NEW_ALERT, ALERT_UPDATE, ALERT_ACKNOWLEDGED, ALERT_RESOLVED
   */
  subscribeAlerts(callback) {
    this.subscribers.add(callback);
    return () => {
      this.subscribers.delete(callback);
    };
  }

  notifySubscribers(eventType, payload) {
    this.subscribers.forEach((cb) => {
      try {
        cb(eventType, payload);
      } catch (err) {
        console.error('[AlertService] Subscriber error:', err);
      }
    });
  }
}

export const alertService = new AlertService();
export default alertService;
