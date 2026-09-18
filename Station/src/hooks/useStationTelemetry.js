import { useStation } from '../context/StationContext';

/**
 * Custom hook for accessing station telemetry and control state.
 * Structured to allow easy drop-in replacement with real WebSocket / MQTT hooks later.
 */
export const useStationTelemetry = () => {
  const station = useStation();

  return {
    activeStation: station.activeStation,
    setActiveStation: station.setActiveStation,
    config: station.stationConfig,
    telemetry: station.telemetry,
    alerts: station.alerts,
    activeAlerts: station.activeAlerts || station.alerts,
    allAlerts: station.allAlerts || station.alerts,
    sensors: station.sensors || station.stationConfig?.sensors || [],
    updateSensor: station.updateSensor,
    clearSensorOverrides: station.clearSensorOverrides,
    acknowledgeAlert: station.acknowledgeAlert,
    scenario: station.activeScenario,
    setScenario: station.setScenario,
    lastUpdated: station.lastUpdated,
    refresh: station.refreshTelemetry,
    isOnline: station.telemetry.connectivity?.status === 'ONLINE'
  };
};

export default useStationTelemetry;
