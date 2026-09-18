import React, { useState, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import { useStationTelemetry } from '../hooks/useStationTelemetry';
import { StationSelector } from '../components/StationSelector';
import { DemoMode } from '../components/DemoMode';
import { LOGISTICS_DATA } from '../data/logisticsData';

import { ExecutiveLogisticsStrip } from '../components/logistics/ExecutiveLogisticsStrip';
import { ResupplyCoverageCard } from '../components/logistics/ResupplyCoverageCard';
import { CriticalStockSection } from '../components/logistics/CriticalStockSection';
import { InventoryTable } from '../components/logistics/InventoryTable';
import { SupplyForecastChart } from '../components/logistics/SupplyForecastChart';
import { ResupplyOperationsTimeline } from '../components/logistics/ResupplyOperationsTimeline';
import { StorageUtilizationCard } from '../components/logistics/StorageUtilizationCard';
import { FuelLogisticsCard } from '../components/logistics/FuelLogisticsCard';
import { DeliveryConditionsCard } from '../components/logistics/DeliveryConditionsCard';
import { LogisticsAlertsCard } from '../components/logistics/LogisticsAlertsCard';
import { CargoManifestModal } from '../components/logistics/CargoManifestModal';

/**
 * Logistics Page
 * Remote Antarctic Expedition Logistics Control Console.
 * Directly answers:
 * WHAT DO WE HAVE → WHAT ARE WE USING → HOW LONG WILL IT LAST → WHAT IS COMING → WILL IT ARRIVE IN TIME?
 */
export const Logistics = () => {
  const navigate = useNavigate();
  const {
    config,
    activeStation,
    telemetry,
    activeAlerts,
    scenario
  } = useStationTelemetry();

  // Active Manifest Modal State
  const [selectedMissionForManifest, setSelectedMissionForManifest] = useState(null);

  // Station dataset fallback
  const stationLogistics = useMemo(() => {
    return LOGISTICS_DATA[activeStation] || LOGISTICS_DATA.MAITRI;
  }, [activeStation]);

  // Adjust next resupply ETA if scenario is STORM (air transport delayed by 5 days)
  const isStorm = scenario === 'STORM';
  const effectiveEtaDays = isStorm
    ? stationLogistics.nextResupplyEtaDays + 5
    : stationLogistics.nextResupplyEtaDays;

  // Real fuel telemetry integration (Energy & Fuel cohesion)
  const fuelReservePct = telemetry.fuel?.currentLevel ?? 64;
  const fuelTotalLiters = telemetry.fuel?.totalLiters ?? 53400;
  const fuelCapacityLiters = telemetry.fuel?.capacityLiters ?? 83400;
  const fuelDailyBurnRate = telemetry.fuel?.dailyBurnRate ?? 480;
  const fuelAutonomyDays = telemetry.fuel?.remainingDays ?? 18.4;

  // Update fuel inventory item in the inventory list with active telemetry values
  const integratedInventory = useMemo(() => {
    return stationLogistics.inventory.map((item) => {
      if (item.category === 'FUEL' && item.item.includes('Arctic Diesel')) {
        return {
          ...item,
          stock: fuelTotalLiters,
          capacity: fuelCapacityLiters,
          dailyConsumption: fuelDailyBurnRate,
          remainingDays: fuelAutonomyDays,
          status: fuelReservePct < 35 || fuelAutonomyDays < effectiveEtaDays ? 'WARNING' : 'NORMAL'
        };
      }
      return item;
    });
  }, [stationLogistics.inventory, fuelTotalLiters, fuelCapacityLiters, fuelDailyBurnRate, fuelAutonomyDays, fuelReservePct, effectiveEtaDays]);

  // Digital Twin Cross-Navigation
  const handleLocateInTwin = (sensorId, zone = 'STORAGE') => {
    navigate('/digital-twin', {
      state: {
        locateSensorId: sensorId || 'LOG-MTR-004',
        focusZone: zone,
        twinMode: 'XRAY'
      }
    });
  };

  const handleLocateFuelInTwin = () => {
    navigate('/digital-twin', {
      state: { focusZone: 'GENERATOR', twinMode: 'XRAY' }
    });
  };


  const stationTitle = config.displayName || `${activeStation} Research Station`;
  const stationCode = config.shortCode || config.id || activeStation;

  return (
    <main className="main-viewport logistics-page-container">
      {/* ─────────────────────────────────────────────────────────────── */}
      {/* 1. OPERATIONAL LOGISTICS HEADER                                 */}
      {/* ─────────────────────────────────────────────────────────────── */}
      <section className="logistics-header-bar" aria-label="Logistics Management Header">
        <div className="logistics-title-group">
          <h1>LOGISTICS & SUPPLY</h1>
          <p className="logistics-subtitle">
            RESUPPLY / INVENTORY / CARGO OPERATIONS
          </p>
        </div>

        <div className="logistics-header-right">
          <StationSelector />

          <div className="logistics-station-badge">
            <span className="station-name-tag">
              {stationCode} // {stationTitle.toUpperCase()}
            </span>
            <span className="online-indicator">
              <span className="status-dot-sm live" />
              ONLINE
            </span>
          </div>

          <div className="next-resupply-badge-pill">
            <span className="eta-label">NEXT RESUPPLY:</span>
            <span className="eta-val">
              {effectiveEtaDays} DAYS ({stationLogistics.nextResupplyMissionId})
            </span>
          </div>
        </div>
      </section>

      {/* ─────────────────────────────────────────────────────────────── */}
      {/* 2. EXECUTIVE OVERVIEW STRIP                                     */}
      {/* ─────────────────────────────────────────────────────────────── */}
      <ExecutiveLogisticsStrip
        totalInventoryTons={stationLogistics.summary.totalInventoryTons}
        criticalStockCount={stationLogistics.summary.criticalStockCount}
        daysOfSupply={Math.min(fuelAutonomyDays, 12.7)}
        incomingCargoTons={stationLogistics.summary.incomingCargoTons}
        storageUtilization={stationLogistics.summary.storageUtilizationPct}
      />

      {/* ─────────────────────────────────────────────────────────────── */}
      {/* 3. WILL SUPPLIES LAST? (RESUPPLY COVERAGE ANALYSIS)             */}
      {/* ─────────────────────────────────────────────────────────────── */}
      <ResupplyCoverageCard
        nextResupplyEta={effectiveEtaDays}
        missionId={stationLogistics.nextResupplyMissionId}
        transport={stationLogistics.nextResupplyTransport}
        inventory={integratedInventory}
      />

      {/* ─────────────────────────────────────────────────────────────── */}
      {/* 4. CRITICAL STOCK + FUEL LOGISTICS (Two-Column Grid)            */}
      {/* ─────────────────────────────────────────────────────────────── */}
      <div className="logistics-two-col-grid">
        <CriticalStockSection
          inventory={integratedInventory}
          onLocateInTwin={handleLocateInTwin}
        />

        <FuelLogisticsCard
          fuelReservePct={fuelReservePct}
          totalLiters={fuelTotalLiters}
          capacityLiters={fuelCapacityLiters}
          dailyBurnRate={fuelDailyBurnRate}
          remainingDays={fuelAutonomyDays}
          nextDeliveryEta={32}
        />
      </div>

      {/* ─────────────────────────────────────────────────────────────── */}
      {/* 5. SUPPLY CONSUMPTION FORECAST (ECharts)                        */}
      {/* ─────────────────────────────────────────────────────────────── */}
      <SupplyForecastChart
        nextResupplyEta={effectiveEtaDays}
      />

      {/* ─────────────────────────────────────────────────────────────── */}
      {/* 6. INVENTORY STATUS (Main Table with Category Tabs)             */}
      {/* ─────────────────────────────────────────────────────────────── */}
      <InventoryTable
        inventory={integratedInventory}
        onLocateInTwin={handleLocateInTwin}
      />

      {/* ─────────────────────────────────────────────────────────────── */}
      {/* 7. RESUPPLY OPERATIONS & ROUTE CONDITIONS (Two-Column Grid)    */}
      {/* ─────────────────────────────────────────────────────────────── */}
      <div className="logistics-two-col-grid">
        <ResupplyOperationsTimeline
          missions={stationLogistics.resupplyMissions}
          onOpenManifest={(mission) => setSelectedMissionForManifest(mission)}
        />

        <DeliveryConditionsCard
          conditions={stationLogistics.deliveryConditions}
          scenario={scenario}
        />
      </div>

      {/* ─────────────────────────────────────────────────────────────── */}
      {/* 8. STORAGE CAPACITY & LOGISTICS ALERTS (Two-Column Grid)        */}
      {/* ─────────────────────────────────────────────────────────────── */}
      <div className="logistics-two-col-grid">
        <StorageUtilizationCard
          facilities={stationLogistics.storageFacilities}
          onLocateInTwin={handleLocateInTwin}
        />

        <LogisticsAlertsCard
          alerts={activeAlerts}
          activeStation={activeStation}
        />
      </div>

      {/* ─────────────────────────────────────────────────────────────── */}
      {/* 9. EMBEDDED DEMO SIMULATION DOCK                                */}
      {/* ─────────────────────────────────────────────────────────────── */}
      <section style={{ marginTop: '0.75rem' }}>
        <DemoMode />
      </section>

      {/* ─────────────────────────────────────────────────────────────── */}
      {/* 10. CARGO MANIFEST MODAL                                        */}
      {/* ─────────────────────────────────────────────────────────────── */}
      <CargoManifestModal
        mission={selectedMissionForManifest}
        onClose={() => setSelectedMissionForManifest(null)}
      />
    </main>
  );
};

export default Logistics;
