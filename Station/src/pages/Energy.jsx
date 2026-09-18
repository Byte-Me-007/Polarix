import React, { useState, useMemo } from 'react';
import { useStationTelemetry } from '../hooks/useStationTelemetry';
import { StationSelector } from '../components/StationSelector';
import { ExecutiveEnergyStrip } from '../components/energy/ExecutiveEnergyStrip';
import { PowerFlowDiagram } from '../components/energy/PowerFlowDiagram';
import { BatteryOperations } from '../components/energy/BatteryOperations';
import { FuelReserveCard } from '../components/energy/FuelReserveCard';
import { EnergyLoadProfileChart } from '../components/energy/EnergyLoadProfileChart';
import { GenerationBreakdown } from '../components/energy/GenerationBreakdown';
import { EnergyOperatingMode } from '../components/energy/EnergyOperatingMode';
import { EnergyRecommendation } from '../components/energy/EnergyRecommendation';
import { EnergyAlertsList } from '../components/energy/EnergyAlertsList';
import { DemoMode } from '../components/DemoMode';

/**
 * Energy Page
 * Remote Antarctic Infrastructure Control Console for power generation,
 * battery storage buffers, polar fuel reserves, and microgrid topology.
 */
export const Energy = () => {
  const {
    config,
    activeStation,
    telemetry,
    activeAlerts,
    scenario
  } = useStationTelemetry();

  // Helper to parse numbers safely from strings like "84.3 kW"
  const parseNum = (val, defaultVal = 0) => {
    if (typeof val === 'number') return val;
    if (typeof val === 'string') {
      const match = val.match(/[-+]?[0-9]*\.?[0-9]+/);
      return match ? parseFloat(match[0]) : defaultVal;
    }
    return defaultVal;
  };

  // Derive dynamic energy values
  const loadKw = parseNum(telemetry.power?.currentPower, 84.3);
  const solarKw = parseNum(telemetry.power?.solarGeneration, 42.8);
  const windKw = parseNum(telemetry.power?.windGeneration, 18.4);
  const dieselKw = parseNum(telemetry.power?.dieselGeneration, 23.1);
  const totalGenKw = Number((solarKw + windKw + dieselKw).toFixed(1));
  const renewableKw = Number((solarKw + windKw).toFixed(1));
  const renewableShare = totalGenKw > 0 ? Math.round((renewableKw / totalGenKw) * 100) : 0;

  const batterySoc = telemetry.battery?.percentage ?? 78;
  const batteryState = telemetry.battery?.state || 'CHARGING';
  const batteryVoltage = telemetry.battery?.voltage || '418.2 V';
  const batteryCurrent = telemetry.battery?.current || '+38.4 A';
  const batteryRuntime = telemetry.battery?.remainingHours || '38.5 hrs';
  const batteryHealth = telemetry.battery?.health || '98.2%';
  const batteryCycles = telemetry.battery?.cycles || 1420;

  const fuelReserve = telemetry.fuel?.currentLevel ?? 64;
  const fuelAutonomyDays = telemetry.fuel?.remainingDays ?? 18.4;
  const dailyBurnRate = telemetry.fuel?.dailyBurnRate ?? 480;
  const totalLiters = telemetry.fuel?.totalLiters ?? 53400;
  const capacityLiters = telemetry.fuel?.capacityLiters ?? 83400;
  const reserveStatus = telemetry.fuel?.reserveStatus || 'SECURE';

  // Determine active operational energy mode based on real telemetry
  const activeMode = useMemo(() => {
    if (scenario === 'POWER_CRISIS' || batterySoc <= 45 || batteryState.includes('CRITICAL')) {
      return 'EMERGENCY POWER';
    }
    if (batteryState.includes('DISCHARGING') && renewableShare < 40) {
      return 'POWER CONSERVATION';
    }
    if (renewableShare >= 65) {
      return 'RENEWABLE PRIORITY';
    }
    if (dieselKw > renewableKw) {
      return 'DIESEL BACKUP';
    }
    return 'NORMAL MICROGRID';
  }, [scenario, batterySoc, batteryState, renewableShare, dieselKw, renewableKw]);

  // Operational rule recommendation
  const recommendation = useMemo(() => {
    if (scenario === 'POWER_CRISIS') {
      return {
        title: 'POWER CONSERVATION RECOMMENDED',
        severity: 'CRITICAL',
        trigger: 'Auxiliary diesel generator trip; battery bank sustaining station demand under severe discharge load.',
        condition: `Diesel generation = 0.0 kW while station demand is ${loadKw.toFixed(1)} kW.`,
        action: 'Engage non-essential load shedding protocol. Disable auxiliary laboratory heating. Conserve battery buffer.',
        metrics: [
          { label: 'Active Gensets Online', val: '0 / 2' },
          { label: 'Critical Load Buffer', val: batteryRuntime }
        ]
      };
    }

    if (scenario === 'STORM') {
      return {
        title: 'TURBINE PITCH DAMPENING ACTIVE',
        severity: 'WARNING',
        trigger: 'Severe Antarctic blizzard wind velocities exceeding 110 km/h.',
        condition: 'Wind turbine aerodynamic pitch dampeners engaged to prevent rotor mechanical overspeed.',
        action: 'Maintain automated microgrid bus balancing. Keep auxiliary diesel plant in hot-standby readiness.',
        metrics: [
          { label: 'Wind Turbine Generation', val: `${windKw.toFixed(1)} kW` },
          { label: 'Blade Pitch Angle', val: '14.5°' }
        ]
      };
    }

    if (batteryState.includes('DISCHARGING')) {
      return {
        title: 'POWER CONSERVATION RECOMMENDED',
        severity: 'WARNING',
        trigger: 'Battery state declining while renewable generation is below station demand.',
        condition: `Renewable generation (${renewableKw.toFixed(1)} kW) < station demand (${loadKw.toFixed(1)} kW).`,
        action: 'Reduce non-essential loads. Throttle auxiliary scientific sample freezer defrost cycles.',
        metrics: [
          { label: 'Net Discharge Rate', val: batteryCurrent },
          { label: 'Estimated Reserve', val: batteryRuntime }
        ]
      };
    }

    // Nominal conditions
    return null;
  }, [scenario, batteryState, loadKw, renewableKw, batteryRuntime, batteryCurrent, windKw]);

  const stationTitle = config.displayName || `${activeStation} Research Station`;
  const stationCode = config.shortCode || activeStation;

  return (
    <main className="main-viewport energy-page-container">
      {/* ─────────────────────────────────────────────────────────────── */}
      {/* 1. OPERATIONAL HEADER                                           */}
      {/* ─────────────────────────────────────────────────────────────── */}
      <section className="energy-header-bar" aria-label="Energy Management Header">
        <div className="energy-title-group">
          <h1>ENERGY MANAGEMENT</h1>
          <p className="energy-subtitle">
            POWER GENERATION / STORAGE / FUEL OPERATIONS
          </p>
        </div>

        <div className="energy-header-right">
          <StationSelector />

          <div className="energy-station-badge">
            <span className="station-name-tag">
              {stationCode} // {stationTitle.toUpperCase()}
            </span>
            <span className="online-indicator">
              <span className="status-dot-sm live" />
              ONLINE
            </span>
          </div>

          <div className="active-mode-badge-pill">
            <span className="mode-label">MODE:</span>
            <span className="mode-val">{activeMode}</span>
          </div>
        </div>
      </section>

      {/* ─────────────────────────────────────────────────────────────── */}
      {/* 2. EXECUTIVE ENERGY METRICS STRIP                               */}
      {/* ─────────────────────────────────────────────────────────────── */}
      <ExecutiveEnergyStrip
        loadKw={loadKw}
        totalGenKw={totalGenKw}
        batterySoc={batterySoc}
        batteryState={batteryState}
        fuelReserve={fuelReserve}
        autonomyDays={fuelAutonomyDays}
        renewableShare={renewableShare}
      />

      {/* ─────────────────────────────────────────────────────────────── */}
      {/* 3. VISUAL POWER FLOW DIAGRAM                                    */}
      {/* ─────────────────────────────────────────────────────────────── */}
      <PowerFlowDiagram
        solarKw={solarKw}
        windKw={windKw}
        dieselKw={dieselKw}
        totalGenKw={totalGenKw}
        loadKw={loadKw}
        batterySoc={batterySoc}
        batteryState={batteryState}
        batteryCurrent={batteryCurrent}
      />

      {/* ─────────────────────────────────────────────────────────────── */}
      {/* 4. BATTERY OPERATIONS + FUEL RESERVE (2-Column Grid)            */}
      {/* ─────────────────────────────────────────────────────────────── */}
      <div className="energy-two-col-grid">
        <BatteryOperations
          batterySoc={batterySoc}
          batteryState={batteryState}
          voltage={batteryVoltage}
          current={batteryCurrent}
          remainingHours={batteryRuntime}
          health={batteryHealth}
          cycles={batteryCycles}
        />

        <FuelReserveCard
          fuelReserve={fuelReserve}
          autonomyDays={fuelAutonomyDays}
          dailyBurnRate={dailyBurnRate}
          totalLiters={totalLiters}
          capacityLiters={capacityLiters}
          dieselKw={dieselKw}
          reserveStatus={reserveStatus}
        />
      </div>

      {/* ─────────────────────────────────────────────────────────────── */}
      {/* 5. 24-HOUR LOAD & GENERATION PROFILE (ECharts)                  */}
      {/* ─────────────────────────────────────────────────────────────── */}
      <EnergyLoadProfileChart
        loadKw={loadKw}
        totalGenKw={totalGenKw}
        solarKw={solarKw}
        windKw={windKw}
        peakLoad={telemetry.power?.peakLoad || 89.2}
      />

      {/* ─────────────────────────────────────────────────────────────── */}
      {/* 6. GENERATION MIX BREAKDOWN (Solar, Wind, Diesel)               */}
      {/* ─────────────────────────────────────────────────────────────── */}
      <GenerationBreakdown
        solarKw={solarKw}
        windKw={windKw}
        dieselKw={dieselKw}
        totalGenKw={totalGenKw}
      />

      {/* ─────────────────────────────────────────────────────────────── */}
      {/* 7. ENERGY OPERATING MODE SELECTOR / REGIME                      */}
      {/* ─────────────────────────────────────────────────────────────── */}
      <EnergyOperatingMode
        activeMode={activeMode}
      />

      {/* ─────────────────────────────────────────────────────────────── */}
      {/* 8. EXPLAINABLE RULE RECOMMENDATION PANEL                        */}
      {/* ─────────────────────────────────────────────────────────────── */}
      <EnergyRecommendation
        recommendation={recommendation}
        batterySoc={batterySoc}
        renewableShare={renewableShare}
        loadKw={loadKw}
        remainingHours={batteryRuntime}
      />

      {/* ─────────────────────────────────────────────────────────────── */}
      {/* 9. ENERGY ALERTS & DIGITAL TWIN CROSS-NAVIGATION               */}
      {/* ─────────────────────────────────────────────────────────────── */}
      <EnergyAlertsList
        alerts={activeAlerts}
        activeStation={activeStation}
      />

      {/* ─────────────────────────────────────────────────────────────── */}
      {/* 10. EMBEDDED DEMO SIMULATION DOCK                               */}
      {/* ─────────────────────────────────────────────────────────────── */}
      <section style={{ marginTop: '0.75rem' }}>
        <DemoMode />
      </section>
    </main>
  );
};

export default Energy;
