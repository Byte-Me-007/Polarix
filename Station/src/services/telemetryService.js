/**
 * Antarctic Telemetry Service
 * Architecture-ready abstraction for future REST API / WebSocket / MQTT backend integration.
 * Currently serves deterministic mock telemetry and scenario overrides.
 */

import { STATIONS, BASE_TELEMETRY, INITIAL_ALERTS, DEMO_SCENARIOS } from "../data/stationData";

class TelemetryService {
  constructor() {
    this.subscribers = new Set();
    this.activeStation = "MAITRI";
    this.activeScenario = "NORMAL";
  }

  /**
   * Fetch static metadata for all stations
   */
  async getStations() {
    return Promise.resolve(STATIONS);
  }

  /**
   * Fetch current station configuration
   */
  async getStationConfig(stationKey = this.activeStation) {
    return Promise.resolve(STATIONS[stationKey] || STATIONS.MAITRI);
  }

  /**
   * Fetch snapshot telemetry for active station
   */
  async getTelemetrySnapshot(stationKey = this.activeStation) {
    const base = BASE_TELEMETRY[stationKey] || BASE_TELEMETRY.MAITRI;
    return Promise.resolve(JSON.parse(JSON.stringify(base)));
  }

  /**
   * Fetch active alerts for station
   */
  async getAlerts(stationKey = this.activeStation) {
    return Promise.resolve(INITIAL_ALERTS.filter(a => a.station === stationKey));
  }

  /**
   * Stub for acknowledging alert
   */
  async acknowledgeAlert(alertId) {
    // In future: await fetch(`/api/v1/alerts/${alertId}/ack`, { method: 'POST' });
    return Promise.resolve({ success: true, alertId });
  }

  /**
   * Future WebSocket / MQTT real-time stream subscription hook
   */
  subscribeTelemetry(stationKey, onMessage) {
    // In future: connect to ws://... or mqtt://...
    this.subscribers.add(onMessage);
    return () => {
      this.subscribers.delete(onMessage);
    };
  }
}

export const telemetryService = new TelemetryService();
