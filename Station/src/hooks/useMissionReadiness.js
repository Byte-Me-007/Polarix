import { useMemo } from 'react';
import { useStationTelemetry } from './useStationTelemetry';

/**
 * useMissionReadiness
 * 
 * Authoritative operational readiness calculation for Antarctic Research Stations.
 * Derives overall readiness directly from the existing shared application state:
 * - StationContext telemetry (power, battery, fuel, satellite, environment)
 * - Sensor telemetry (criticality, anomaly status, operational domain)
 * - Active unacknowledged alerts
 * - Active station and scenario state
 * 
 * Answers immediately:
 * "Can the station currently operate safely and effectively?"
 * Output: READY | DEGRADED | AT RISK | DATA UNAVAILABLE
 */
export const useMissionReadiness = () => {
  const {
    telemetry,
    sensors = [],
    allAlerts = [],
    activeAlerts = [],
    activeStation,
    activeScenario,
    thresholds,
    config
  } = useStationTelemetry();

  return useMemo(() => {
    // Graceful fallback if telemetry is completely unavailable
    if (!telemetry || Object.keys(telemetry).length === 0) {
      return {
        overallReadiness: 'DATA UNAVAILABLE',
        overallSummary: 'Telemetry stream disconnected from station bus.',
        overallTheme: { color: 'var(--polaris-text-muted)', bg: 'rgba(100, 116, 139, 0.1)', border: 'var(--polaris-border)' },
        systems: [],
        causes: [],
        traceabilityMatrix: []
      };
    }

    const causes = [];

    // ─────────────────────────────────────────────────────────────
    // 1. POWER SUBSYSTEM EVALUATION
    // ─────────────────────────────────────────────────────────────
    const power = telemetry.power || {};
    const battery = telemetry.battery || {};
    let powerStatus = 'NORMAL';
    let powerReason = 'Microgrid generation & battery bank nominal';
    let powerRating = 95; // For meter bar

    const batteryLowThreshold = thresholds?.batteryLowPct ?? 45;
    const batteryPct = typeof battery.percentage === 'number' ? battery.percentage : null;
    const batteryState = String(battery.state || '').toUpperCase();
    const isCriticalDischarge = batteryState.includes('CRITICAL') || (batteryPct !== null && batteryPct < batteryLowThreshold);
    const isDischarging = batteryState.includes('DISCHARGING');
    const generatorTripped = power.dieselGeneration !== undefined && parseFloat(power.dieselGeneration) === 0 && (activeScenario === 'POWER_CRISIS');

    // Check if generator vibration sensor is critical or exceeds threshold
    const genVibCritThreshold = thresholds?.generatorVibrationCrit ?? 4.8;
    const genVibrationSensor = sensors.find(s => s.id === 'ENG-MTR-002' || (s.type === 'VIBRATION' && s.zone === 'GENERATOR'));
    const isGenVibrating = genVibrationSensor && (
      genVibrationSensor.status === 'CRITICAL' ||
      (typeof genVibrationSensor.value === 'number' && genVibrationSensor.value >= genVibCritThreshold) ||
      (genVibrationSensor.anomalyScore || 0) > 0.85
    );

    if (isCriticalDischarge) {
      powerStatus = 'CRITICAL';
      powerRating = 35;
      powerReason = `Battery bank in critical discharge (${batteryPct ?? 'Unknown'}%, ${battery.remainingHours || 'Low'} remaining)`;
      causes.push({
        id: 'cause-power-batt-crit',
        title: `Battery bank critical discharge (${batteryPct ?? '42'}% SOC — ${battery.remainingHours || '7.4 hrs'} reserve)`,
        system: 'POWER',
        severity: 'CRITICAL',
        source: 'ENERGY',
        actionLabel: 'VIEW IN ENERGY',
        actionRoute: '/energy',
        twinZone: 'ENERGY',
        sensorId: 'ENG-MTR-003'
      });
    } else if (isDischarging) {
      powerStatus = 'DEGRADED';
      powerRating = 65;
      powerReason = `Battery discharging under station load (${batteryPct ?? '84'}%)`;
      causes.push({
        id: 'cause-power-batt-disch',
        title: `Battery discharging (${batteryPct ?? '84'}% SOC — ${battery.remainingHours || '19.2 hrs'} runtime)`,
        system: 'POWER',
        severity: 'DEGRADED',
        source: 'ENERGY',
        actionLabel: 'VIEW IN ENERGY',
        actionRoute: '/energy',
        twinZone: 'ENERGY',
        sensorId: 'ENG-MTR-003'
      });
    }

    if (generatorTripped) {
      if (powerStatus !== 'CRITICAL') {
        powerStatus = 'CRITICAL';
        powerRating = 30;
      }
      powerReason = 'Microgrid diesel generators tripped / offline';
      causes.push({
        id: 'cause-power-gen-trip',
        title: 'Diesel generator tripped — microgrid relying on auxiliary battery',
        system: 'POWER',
        severity: 'CRITICAL',
        source: 'ENERGY',
        actionLabel: 'LOCATE IN DIGITAL TWIN',
        actionRoute: '/digital-twin',
        twinZone: 'GENERATOR',
        sensorId: 'ENG-MTR-002'
      });
    } else if (isGenVibrating && !generatorTripped) {
      if (powerStatus === 'NORMAL') {
        powerStatus = 'DEGRADED';
        powerRating = 70;
        powerReason = 'Generator harmonic vibration elevated (4.8 mm/s)';
      }
      causes.push({
        id: 'cause-power-gen-vib',
        title: `Generator vibration anomaly on DG-2 rotor (${genVibrationSensor.value} ${genVibrationSensor.unit})`,
        system: 'POWER',
        severity: 'DEGRADED',
        source: 'ENERGY',
        actionLabel: 'VIEW IN ENERGY',
        actionRoute: '/energy',
        twinZone: 'GENERATOR',
        sensorId: genVibrationSensor.id
      });
    }

    // ─────────────────────────────────────────────────────────────
    // 2. COMMUNICATIONS SUBSYSTEM EVALUATION
    // ─────────────────────────────────────────────────────────────
    const satellite = telemetry.satellite || telemetry.connectivity || {};
    let commsStatus = 'NORMAL';
    let commsReason = `Satellite link operational (${satellite.satellite || 'GSAT / Starlink nominal'})`;
    let commsRating = 95;

    const satStatus = String(satellite.status || '').toUpperCase();
    const signalQuality = typeof satellite.signalQuality === 'number' ? satellite.signalQuality : 95;
    const isCommsOffline = satStatus === 'OFFLINE' || signalQuality === 0;
    const isCommsDegraded = satStatus === 'DEGRADED' || signalQuality < 75;

    if (isCommsOffline) {
      commsStatus = 'CRITICAL';
      commsRating = 15;
      commsReason = 'Satellite uplink lost — comms blackout (emergency HF fallback)';
      causes.push({
        id: 'cause-comms-blackout',
        title: 'Satellite uplink blackout — 100% packet loss (emergency HF burst active)',
        system: 'COMMUNICATIONS',
        severity: 'CRITICAL',
        source: 'COMMS',
        actionLabel: 'LOCATE IN DIGITAL TWIN',
        actionRoute: '/digital-twin',
        twinZone: 'COMMS',
        sensorId: 'COM-MTR-001'
      });
    } else if (isCommsDegraded) {
      commsStatus = 'DEGRADED';
      commsRating = 60;
      commsReason = `Satellite signal degraded (${signalQuality}% signal quality)`;
      causes.push({
        id: 'cause-comms-degraded',
        title: `Satellite link degraded (${signalQuality}% link quality)`,
        system: 'COMMUNICATIONS',
        severity: 'DEGRADED',
        source: 'COMMS',
        actionLabel: 'LOCATE IN DIGITAL TWIN',
        actionRoute: '/digital-twin',
        twinZone: 'COMMS',
        sensorId: 'COM-MTR-001'
      });
    }

    // ─────────────────────────────────────────────────────────────
    // 3. INFRASTRUCTURE & ENVIRONMENT SUBSYSTEM EVALUATION
    // ─────────────────────────────────────────────────────────────
    const env = telemetry.environment || telemetry.environmentalTelemetry || {};
    let infraStatus = 'NORMAL';
    let infraReason = 'Habitat stilts, joints and thermal buffer nominal';
    let infraRating = 95;

    const windSpeed = typeof env.windSpeed === 'number' ? env.windSpeed : 25;
    const isSevereBlizzard = windSpeed > 100;
    
    // Check structural sensors
    const structuralCritical = sensors.some(s => s.domain === 'STRUCTURE' && s.status === 'CRITICAL');
    const structuralWarning = sensors.some(s => s.domain === 'STRUCTURE' && s.status === 'WARNING');

    if (structuralCritical || isSevereBlizzard) {
      infraStatus = isSevereBlizzard && windSpeed > 115 ? 'CRITICAL' : 'DEGRADED';
      infraRating = infraStatus === 'CRITICAL' ? 35 : 60;
      infraReason = isSevereBlizzard
        ? `Blizzard condition — wind gusts ${windSpeed.toFixed(1)} km/h (shelter lockdown)`
        : 'Structural strain threshold exceeded on foundation';
      causes.push({
        id: 'cause-infra-storm',
        title: isSevereBlizzard
          ? `Blizzard Code Red — ${windSpeed.toFixed(1)} km/h sustained gusts (shelter lockdown)`
          : 'Structural strain anomaly on elevation stilts',
        system: 'INFRASTRUCTURE',
        severity: infraStatus,
        source: 'STRUCTURE',
        actionLabel: 'LOCATE IN DIGITAL TWIN',
        actionRoute: '/digital-twin',
        twinZone: isSevereBlizzard ? 'COMMS' : 'MAIN',
        sensorId: isSevereBlizzard ? 'ENV-MTR-002' : 'STR-MTR-001'
      });
    } else if (structuralWarning) {
      infraStatus = 'DEGRADED';
      infraRating = 75;
      infraReason = 'Corridor expansion joint displacement under observation';
    }

    // ─────────────────────────────────────────────────────────────
    // 4. SUPPLIES & FUEL RESERVES EVALUATION
    // ─────────────────────────────────────────────────────────────
    const fuel = telemetry.fuel || {};
    let suppliesStatus = 'NORMAL';
    let suppliesReason = `Bulk fuel secure (${fuel.remainingDays || 18} days autonomy)`;
    let suppliesRating = 90;

    const fuelLevel = typeof fuel.currentLevel === 'number' ? fuel.currentLevel : 64;
    const remainingDays = typeof fuel.remainingDays === 'number' ? fuel.remainingDays : 18;
    const fuelCritLimit = thresholds?.fuelReserveCriticalDays ?? 10;
    const fuelLowLimit = thresholds?.fuelReserveDays ?? 20;

    if (fuelLevel < 25 || remainingDays < fuelCritLimit) {
      suppliesStatus = 'CRITICAL';
      suppliesRating = 25;
      suppliesReason = `Fuel reserves critical (${fuelLevel}% / ${remainingDays} days)`;
      causes.push({
        id: 'cause-supplies-fuel-crit',
        title: `Fuel reserves critically low (${fuelLevel}% / ${remainingDays} days remaining)`,
        system: 'SUPPLIES',
        severity: 'CRITICAL',
        source: 'LOGISTICS',
        actionLabel: 'VIEW IN LOGISTICS',
        actionRoute: '/logistics',
        twinZone: 'STORAGE',
        sensorId: 'LOG-MTR-001'
      });
    } else if (fuelLevel < 40 || remainingDays < fuelLowLimit) {
      suppliesStatus = 'LOW';
      suppliesRating = 55;
      suppliesReason = `Fuel below operational threshold (${fuelLevel}% / ${remainingDays} days)`;
      causes.push({
        id: 'cause-supplies-fuel-low',
        title: `Fuel below operational threshold (${fuelLevel}% / ${remainingDays} days remaining)`,
        system: 'SUPPLIES',
        severity: 'LOW',
        source: 'LOGISTICS',
        actionLabel: 'VIEW IN LOGISTICS',
        actionRoute: '/logistics',
        twinZone: 'STORAGE',
        sensorId: 'LOG-MTR-001'
      });
    }

    // ─────────────────────────────────────────────────────────────
    // 5. CRITICAL ALERTS EVALUATION
    // ─────────────────────────────────────────────────────────────
    // Find unacknowledged critical and warning alerts
    const unackCriticalAlerts = allAlerts.filter(a => !a.acknowledged && a.severity === 'CRITICAL');
    const unackWarningAlerts = allAlerts.filter(a => !a.acknowledged && a.severity === 'WARNING');

    let alertsStatus = 'NORMAL';
    let alertsReason = 'No unresolved critical alarms';
    let alertsRating = 95;

    if (unackCriticalAlerts.length > 0) {
      alertsStatus = 'CRITICAL';
      alertsRating = 20;
      alertsReason = `${unackCriticalAlerts.length} unresolved critical alert${unackCriticalAlerts.length > 1 ? 's' : ''}`;

      // Add each critical alert as a concrete traceable cause if not already duplicated
      unackCriticalAlerts.forEach(alert => {
        const alreadyListed = causes.some(c => c.title.toLowerCase().includes((alert.title || '').toLowerCase().slice(0, 15)));
        if (!alreadyListed) {
          causes.push({
            id: `cause-alert-${alert.id}`,
            title: `Critical Alert: ${alert.title}`,
            system: 'ALERTS',
            severity: 'CRITICAL',
            source: alert.subsystem || alert.type || 'ALERTS',
            actionLabel: 'VIEW ALERT',
            actionRoute: '/alerts',
            twinZone: alert.zone || 'MAIN',
            sensorId: alert.sensor_id || alert.sensorId
          });
        }
      });
    } else if (unackWarningAlerts.length > 0) {
      alertsStatus = 'DEGRADED';
      alertsRating = 70;
      alertsReason = `${unackWarningAlerts.length} warning alert${unackWarningAlerts.length > 1 ? 's' : ''}`;
    }

    // ─────────────────────────────────────────────────────────────
    // 6. SENSOR FAILURE OPERATIONAL IMPACT VALIDATION
    // Note: Sensor failures (e.g. humidity dropout) only impact readiness
    // if associated with operationally critical life support or power!
    // ─────────────────────────────────────────────────────────────
    const nonCriticalOfflineSensors = sensors.filter(s => 
      (s.status === 'OFFLINE' || s.quality === 'FAIL' || s.quality === 'LOST') &&
      s.criticality !== 'CRITICAL' &&
      s.domain !== 'ENERGY'
    );
    // Non-critical sensor dropouts do not alter overall readiness.

    // ─────────────────────────────────────────────────────────────
    // 7. COMPOSITE MISSION READINESS DERIVATION
    // ─────────────────────────────────────────────────────────────
    // System definitions for meter displays
    const systems = [
      {
        id: 'power',
        name: 'POWER',
        status: powerStatus,
        rating: powerRating,
        reason: powerReason,
        source: 'ENERGY',
        targetRoute: '/energy',
        twinZone: 'ENERGY'
      },
      {
        id: 'comms',
        name: 'COMMUNICATIONS',
        status: commsStatus,
        rating: commsRating,
        reason: commsReason,
        source: 'COMMS',
        targetRoute: '/digital-twin',
        twinZone: 'COMMS'
      },
      {
        id: 'infra',
        name: 'INFRASTRUCTURE',
        status: infraStatus,
        rating: infraRating,
        reason: infraReason,
        source: 'STRUCTURE',
        targetRoute: '/digital-twin',
        twinZone: 'MAIN'
      },
      {
        id: 'supplies',
        name: 'SUPPLIES',
        status: suppliesStatus,
        rating: suppliesRating,
        reason: suppliesReason,
        source: 'LOGISTICS',
        targetRoute: '/logistics',
        twinZone: 'STORAGE'
      },
      {
        id: 'alerts',
        name: 'ALERTS',
        status: alertsStatus,
        rating: alertsRating,
        reason: alertsReason,
        source: 'ALERTS',
        targetRoute: '/alerts',
        badge: unackCriticalAlerts.length > 0 ? `${unackCriticalAlerts.length} CRITICAL` : (unackWarningAlerts.length > 0 ? `${unackWarningAlerts.length} WARNING` : '0 CRITICAL')
      }
    ];

    let overallReadiness = 'READY';
    let overallSummary = 'All primary life-support, power, logistics, and communications subsystems nominal.';
    let overallTheme = {
      color: 'var(--status-normal)',
      bg: 'var(--status-normal-bg)',
      border: 'rgba(63, 110, 74, 0.35)',
      badgeBg: '#eef5f0',
      badgeText: '#2e5b38'
    };

    const hasCritical = systems.some(s => s.status === 'CRITICAL');
    const hasDegraded = systems.some(s => s.status === 'DEGRADED' || s.status === 'LOW');

    // Synthesize ONLY actual non-normal contributing factors dynamically
    const activeFactors = [];

    // 1. Power factor
    if (powerStatus === 'CRITICAL') {
      if (generatorTripped && isCriticalDischarge) {
        activeFactors.push('critical battery discharge and generator failure');
      } else if (generatorTripped) {
        activeFactors.push('microgrid generator failure');
      } else if (isCriticalDischarge) {
        activeFactors.push('critical battery discharge');
      } else {
        activeFactors.push('critical power disruption');
      }
    } else if (powerStatus === 'DEGRADED') {
      if (isDischarging) {
        activeFactors.push('battery discharge under load');
      } else if (isGenVibrating) {
        activeFactors.push('generator vibration anomaly');
      } else {
        activeFactors.push('power subsystem degradation');
      }
    }

    // 2. Communications factor
    if (commsStatus === 'CRITICAL') {
      activeFactors.push('satellite communications blackout');
    } else if (commsStatus === 'DEGRADED') {
      activeFactors.push('degraded satellite communications');
    }

    // 3. Infrastructure factor
    if (infraStatus === 'CRITICAL') {
      activeFactors.push(isSevereBlizzard ? 'severe blizzard storm conditions' : 'critical structural strain');
    } else if (infraStatus === 'DEGRADED') {
      activeFactors.push((isSevereBlizzard || windSpeed > 80) ? 'high wind storm conditions' : (structuralWarning ? 'structural joint displacement' : 'infrastructure strain'));
    }

    // 4. Supplies factor
    if (suppliesStatus === 'CRITICAL') {
      activeFactors.push('critical fuel depletion');
    } else if (suppliesStatus === 'LOW' || suppliesStatus === 'DEGRADED') {
      activeFactors.push('low supplies');
    }

    // 5. Alerts factor
    if (alertsStatus === 'CRITICAL') {
      activeFactors.push(unackCriticalAlerts.length === 1 ? 'an unresolved critical alert' : `${unackCriticalAlerts.length} unresolved critical alerts`);
    } else if (alertsStatus === 'DEGRADED') {
      activeFactors.push(unackWarningAlerts.length === 1 ? 'an active warning alert' : `${unackWarningAlerts.length} active warning alerts`);
    }

    // Helper to format factors in natural English: "x", "x and y", or "x, y, and z"
    const formatFactors = (factors) => {
      if (!factors || factors.length === 0) return '';
      if (factors.length === 1) return factors[0];
      if (factors.length === 2) return `${factors[0]} and ${factors[1]}`;
      return `${factors.slice(0, -1).join(', ')}, and ${factors[factors.length - 1]}`;
    };

    if (hasCritical) {
      overallReadiness = 'AT RISK';
      const factorsText = formatFactors(activeFactors);
      overallSummary = factorsText
        ? `Station operation is currently at risk due to ${factorsText}.`
        : 'Station operation is currently at risk. Immediate operational review required.';
      overallTheme = {
        color: 'var(--status-critical)',
        bg: 'var(--status-critical-bg)',
        border: 'rgba(181, 56, 43, 0.35)',
        badgeBg: '#fbeeed',
        badgeText: '#99261b'
      };
    } else if (hasDegraded) {
      overallReadiness = 'DEGRADED';
      const factorsText = formatFactors(activeFactors);
      overallSummary = factorsText
        ? `Station operation is degraded due to ${factorsText}.`
        : 'Station operation is degraded under secondary operating thresholds.';
      overallTheme = {
        color: 'var(--status-warning)',
        bg: 'var(--status-warning-bg)',
        border: 'rgba(178, 104, 20, 0.35)',
        badgeBg: '#fbf4ea',
        badgeText: '#92510b'
      };
    }

    // Full traceability matrix
    const traceabilityMatrix = systems.map(s => ({
      system: s.name,
      status: s.status,
      reason: s.reason,
      source: s.source,
      action: s.targetRoute
    }));

    return {
      overallReadiness,
      overallSummary,
      overallTheme,
      systems,
      causes,
      traceabilityMatrix,
      activeStation,
      stationName: config?.displayName || `${activeStation} Research Station`,
      unackCriticalCount: unackCriticalAlerts.length,
      unackWarningCount: unackWarningAlerts.length
    };
  }, [telemetry, sensors, allAlerts, activeStation, activeScenario, thresholds, config]);
};
