import React, { useMemo } from 'react';
import * as THREE from 'three';
import { StationZone } from './StationZone';
import { SystemFlowOverlay } from './SystemFlowOverlay';
import { computeDisplayPos } from './SensorMarker';
import { getAssociatedAssetIdForSensor, ZONE_INTERNAL_ASSETS } from './stationAssets';
import { IndianFlagPole } from './IndianFlagPole';
import { BharatiStationModel } from './BharatiStationModel';
import { BharatiSystemFlowOverlay } from './BharatiSystemFlowOverlay';

// New station layout (all zones scaled ~1.75x from original):
//   MAIN:      pos [0, 3.5, 0],    size [34, 7, 22]   → X: -17..+17   Z: -11..+11
//   RESEARCH:  pos [38, 3.2, 0],   size [22, 6.4, 18] → X: +27..+49   Z: -9..+9
//   ENERGY:    pos [0, 3.0, -30],  size [26, 6, 18]   → X: -13..+13   Z: -39..-21
//   GENERATOR: pos [-30, 2.8, -30],size [20, 5.6, 18] → X: -40..-20   Z: -39..-21
//   STORAGE:   pos [32, 2.8, -30], size [20, 5.6, 18] → X: +22..+42   Z: -39..-21
//   COMMS:     pos [0, 2.6, -54],  size [14, 5.2, 14] → X: -7..+7     Z: -61..-47
//
// Gap analysis (all comfortable, 6-10 unit service clearance):
//   MAIN ↔ RESEARCH (x gap):   17 → 27  = 10 units  → Corridor at x=22
//   MAIN ↔ ENERGY (z gap):     -11 → -21 = 10 units  → Corridor at z=-16
//   ENERGY ↔ GENERATOR (x gap):-13 → -20 = 7 units   → Corridor at x=-16.5
//   ENERGY ↔ STORAGE (x gap):  +13 → +22 = 9 units   → Corridor at x=+17.5
//   ENERGY ↔ COMMS (z gap):    -39 → -47 = 8 units   → Corridor at z=-43

export const ZONE_STATUS_CONFIG = {
  CRITICAL: {
    hex: '#e03131',
    rgb: '224, 49, 49',
    name: 'CRITICAL',
    floorOpacity: 0.65,
    glowOpacity: 0.95
  },
  WARNING: {
    hex: '#f59f00',
    rgb: '245, 159, 0',
    name: 'WARNING',
    floorOpacity: 0.55,
    glowOpacity: 0.88
  },
  NORMAL: {
    hex: '#2b8a3e',
    rgb: '43, 138, 62',
    name: 'NORMAL',
    floorOpacity: 0.35,
    glowOpacity: 0.60
  },
  OFFLINE: {
    hex: '#868e96',
    rgb: '134, 142, 150',
    name: 'OFFLINE',
    floorOpacity: 0.22,
    glowOpacity: 0.35
  }
};

export const StationModel = ({
  station,
  sensors = [],
  showLabels = true,
  showHeatmap = false,
  selectedZone = null,
  selectedSensor = null,
  twinMode = 'NORMAL',
  focusZone = null,
  telemetry = {},
  onSelectAsset,
  selectedAssetId = null,
  // Incident visualization
  incidentAffectedZones = null,
  incidentPrimaryZones  = null,
  incidentActive        = false,
  incidentGraph         = null,
}) => {
  const zones = station?.digitalTwin?.zones || [];

  // Detect active station from zone ids — must be computed BEFORE any hooks
  // but CANNOT cause an early return (Rules of Hooks).
  const isBharati = zones.length > 0 && (zones[0].id || '').startsWith('Z-BHR-');

  // --- ALL HOOKS MUST RUN UNCONDITIONALLY (Rules of Hooks) ---

  const isXray = twinMode === 'XRAY';
  const isSemiTransparent = showHeatmap || isXray || twinMode === 'SYSTEM';

  // Connecting Corridor Material Styles (Maitri only, but computed always)
  const isSystem = twinMode === 'SYSTEM';
  const corridorOpacity     = isXray ? 0.12 : isSystem ? 0.45 : isSemiTransparent ? 0.30 : 1.0;
  const corridorParapetOp   = isXray ? 0.06 : isSystem ? 0.28 : isSemiTransparent ? 0.18 : 1.0;
  const corridorLegOpacity  = isXray ? 0.08 : isSystem ? 0.35 : isSemiTransparent ? 0.35 : 1.0;
  const corridorLegColor    = isXray ? '#94a3b8' : isSystem ? '#475569' : '#242a35';
  const corridorCastShadow  = !isXray;
  const corridorRaycast     = isXray ? () => null : undefined;

  // Resolve associated internal asset world position for the selected sensor
  const sensorRelationship = useMemo(() => {
    if (!selectedSensor) return null;
    const targetAssetId = getAssociatedAssetIdForSensor(selectedSensor);
    if (!targetAssetId) return null;
    const [zoneCode, rawId] = targetAssetId.split('-');
    const zone = zones.find(z => (z.code || z.id) === zoneCode);
    if (!zone) return null;
    const zoneDefs = ZONE_INTERNAL_ASSETS[zoneCode] || [];
    const assetDef = zoneDefs.find(a => `${zoneCode}-${a.id}` === targetAssetId || a.id === rawId);
    if (!assetDef) return null;

    const sensorDisp = computeDisplayPos(selectedSensor, zones);
    const assetWorld = [
      zone.position[0] + assetDef.relPos[0],
      zone.position[1] + assetDef.relPos[1],
      zone.position[2] + assetDef.relPos[2]
    ];

    const p1 = new THREE.Vector3(sensorDisp.x, sensorDisp.y, sensorDisp.z);
    const p2 = new THREE.Vector3(assetWorld[0], assetWorld[1] + 1.2, assetWorld[2]);
    const dist = p1.distanceTo(p2);
    const mid = new THREE.Vector3().addVectors(p1, p2).multiplyScalar(0.5);
    const dir = new THREE.Vector3().subVectors(p2, p1).normalize();
    const quat = new THREE.Quaternion().setFromUnitVectors(new THREE.Vector3(0, 1, 0), dir);

    return {
      sensorDisp,
      assetWorld,
      dist,
      mid: [mid.x, mid.y, mid.z],
      quat,
      assetDef,
      assetId: targetAssetId
    };
  }, [selectedSensor, zones]);

  // Compute dominant health status per zone from sensors
  const zoneHealth = useMemo(() => {
    const map = {};
    zones.forEach((z) => {
      const code = z.code || z.id;
      const zoneSensors = sensors.filter((s) => s.zone === code);
      let maxSev = -1;
      let dominant = 'NORMAL';
      zoneSensors.forEach((s) => {
        const stat = (s.status || 'NORMAL').toUpperCase();
        let sev = 0;
        if (stat === 'CRITICAL') sev = 3;
        else if (stat === 'WARNING') sev = 2;
        else if (stat === 'OFFLINE') sev = 1;
        else sev = 0;

        if (sev > maxSev) {
          maxSev = sev;
          dominant = stat;
        }
      });
      map[code] = dominant;
    });
    return map;
  }, [sensors, zones]);



  return (
    <group name="station-model-root">

      {/* ================================================================= */}
      {/* BHARATI — delegate to dedicated coastal model                      */}
      {/* ================================================================= */}
      {isBharati ? (
        <>
          <BharatiStationModel
            station={station}
            sensors={sensors}
            showLabels={showLabels}
            showHeatmap={showHeatmap}
            selectedZone={selectedZone}
            selectedSensor={selectedSensor}
            twinMode={twinMode}
            focusZone={focusZone}
            telemetry={telemetry}
            onSelectAsset={onSelectAsset}
            selectedAssetId={selectedAssetId}
            incidentAffectedZones={incidentAffectedZones}
            incidentPrimaryZones={incidentPrimaryZones}
            incidentActive={incidentActive}
            incidentGraph={incidentGraph}
          />
          {twinMode === 'SYSTEM' && (
            <BharatiSystemFlowOverlay
              telemetry={telemetry}
              station={station}
              selectedAssetId={selectedAssetId}
              selectedSensor={selectedSensor}
              onSelectAsset={onSelectAsset}
              incidentGraph={incidentGraph}
            />
          )}
        </>
      ) : (
        <>
      {/* ================================================================= */}
      {/* MAITRI — original rendering path, completely unchanged             */}
      {/* ================================================================= */}

      {/* ------------------------------------------------------------- */}
      {/* 1. ANTARCTIC PERMAFROST & SNOWFIELD TERRAIN                   */}
      {/* ------------------------------------------------------------- */}
      {/* Smooth Antarctic Packed Snow Plane */}
      <mesh receiveShadow rotation={[-Math.PI / 2, 0, 0]} position={[4, -0.05, -24]}>
        <planeGeometry args={[300, 300, 1, 1]} />
        <meshStandardMaterial color="#f2efe6" roughness={0.92} metalness={0.04} />
      </mesh>

      {/* Coordinate Survey Grid on Snow Surface */}
      <gridHelper
        args={[240, 48, '#ddd8cc', '#e8e3d8']}
        position={[4, 0.01, -24]}
      />

      {/* ------------------------------------------------------------- */}
      {/* 2. SPATIAL STATION FACILITIES (6 Required Modules)            */}
      {/* ------------------------------------------------------------- */}
      {zones.map((zone) => {
        const code = zone.code || zone.id;
        const status = zoneHealth[code] || 'NORMAL';
        const meta = ZONE_STATUS_CONFIG[status] || ZONE_STATUS_CONFIG.NORMAL;
        const isSelectedZone = Boolean(selectedZone && (code === selectedZone));

        // Incident visual emphasis — unaffected zones quieted, primary zones kept prominent
        const isIncidentAffected = incidentActive && incidentAffectedZones?.has(code);
        const isIncidentPrimary  = incidentActive && incidentPrimaryZones?.has(code);
        const isIncidentDimmed   = incidentActive && incidentAffectedZones?.size > 0 && !isIncidentAffected;

        return (
          <StationZone
            key={zone.id}
            zone={zone}
            showLabels={showLabels}
            showHeatmap={showHeatmap}
            zoneStatus={status}
            statusMeta={meta}
            isSelectedZone={isSelectedZone}
            hasSelectedZone={Boolean(selectedZone)}
            twinMode={twinMode}
            isHighlighted={Boolean(focusZone && code === focusZone)}
            sensors={sensors}
            telemetry={telemetry}
            onSelectAsset={onSelectAsset}
            selectedAssetId={selectedAssetId}
            selectedSensor={selectedSensor}
            incidentDimmed={isIncidentDimmed}
            incidentHighlighted={isIncidentPrimary}
          />
        );
      })}

      {/* System Mode Energy Flow Overlay */}
      {twinMode === 'SYSTEM' && (
        <SystemFlowOverlay
          telemetry={telemetry}
          station={station}
          selectedAssetId={selectedAssetId}
          selectedSensor={selectedSensor}
          onSelectAsset={onSelectAsset}
          incidentGraph={incidentGraph}
        />
      )}

      {/* ------------------------------------------------------------- */}
      {/* SENSOR ↔ ASSET RELATIONSHIP INDICATOR (Selected Sensor Focus)   */}
      {/* ------------------------------------------------------------- */}
      {sensorRelationship && (
        <group name="sensor-asset-connector">
          {/* Subtle connecting guide beam from rooftop marker to internal machinery */}
          <group position={sensorRelationship.mid} quaternion={sensorRelationship.quat}>
            <mesh raycast={() => null}>
              <cylinderGeometry args={[0.045, 0.045, sensorRelationship.dist, 8]} />
              <meshStandardMaterial
                color="#b65a1f"
                emissive="#b65a1f"
                emissiveIntensity={0.8}
                transparent
                opacity={0.80}
                depthWrite={false}
              />
            </mesh>
          </group>

          {/* Glowing connector node at sensor end */}
          <mesh
            position={[sensorRelationship.sensorDisp.x, sensorRelationship.sensorDisp.y, sensorRelationship.sensorDisp.z]}
            raycast={() => null}
          >
            <sphereGeometry args={[0.22, 12, 12]} />
            <meshStandardMaterial
              color="#b65a1f"
              emissive="#b65a1f"
              emissiveIntensity={0.9}
            />
          </mesh>

          {/* Target highlight ring at asset footprint */}
          <mesh
            position={[sensorRelationship.assetWorld[0], sensorRelationship.assetWorld[1] + 0.06, sensorRelationship.assetWorld[2]]}
            rotation={[-Math.PI / 2, 0, 0]}
            raycast={() => null}
          >
            <ringGeometry args={[1.6, 1.95, 32]} />
            <meshBasicMaterial
              color="#b65a1f"
              transparent
              opacity={0.85}
              depthWrite={false}
              side={THREE.DoubleSide}
            />
          </mesh>
        </group>
      )}

      {/* ------------------------------------------------------------- */}
      {/* 3. ENCLOSED CONNECTING CORRIDORS & UTILITY BRIDGES             */}
      {/* Insulated arctic umbilical corridors connecting facilities     */}
      {/* ------------------------------------------------------------- */}

      {/* Corridor 1: MAIN ↔ RESEARCH (East Habitat Connector) */}
      <group position={[22, 6.0, 0]}>
        <mesh castShadow={corridorCastShadow} receiveShadow raycast={corridorRaycast}>
          <boxGeometry args={[8.0, 7.6, 5.2]} />
          <meshStandardMaterial
            color="#e2e8f0"
            roughness={0.4}
            metalness={0.2}
            transparent={isSemiTransparent}
            opacity={corridorOpacity}
            depthWrite={!isSemiTransparent}
          />
        </mesh>
        {/* Parapet Coping */}
        <mesh position={[0, 3.9, 0]} raycast={corridorRaycast}>
          <boxGeometry args={[8.2, 0.24, 5.4]} />
          <meshStandardMaterial
            color={isXray ? '#e2e8f0' : '#334155'}
            roughness={0.6}
            metalness={0.4}
            transparent={isSemiTransparent}
            opacity={corridorParapetOp}
            depthWrite={!isSemiTransparent}
          />
        </mesh>
        {/* Continuous Ribbon Windows */}
        {[-2.65, 2.65].map((wz, wi) => (
          <mesh key={`c1-win-${wi}`} position={[0, 0.4, wz]} raycast={corridorRaycast}>
            <boxGeometry args={[6.2, 1.4, 0.08]} />
            <meshStandardMaterial
              color="#0f172a"
              roughness={0.08}
              metalness={0.92}
              transparent={isSemiTransparent}
              opacity={corridorOpacity}
              depthWrite={!isSemiTransparent}
            />
          </mesh>
        ))}
        {/* Roof Utility Conduit Tray */}
        <mesh position={[0, 4.15, 0]} raycast={corridorRaycast}>
          <boxGeometry args={[8.0, 0.12, 0.5]} />
          <meshStandardMaterial
            color="#b45309"
            metalness={0.6}
            roughness={0.4}
            transparent={isSemiTransparent}
            opacity={corridorOpacity}
            depthWrite={!isSemiTransparent}
          />
        </mesh>
        {/* Steel Support Stilts with Cross-brace */}
        {[-2.5, 2.5].map((stX, i) => (
          <group key={i} position={[stX, -5.5, 0]}>
            <mesh castShadow={corridorCastShadow} raycast={corridorRaycast}>
              <cylinderGeometry args={[0.24, 0.24, 6.0, 8]} />
              <meshStandardMaterial
                color={corridorLegColor}
                roughness={0.8}
                metalness={0.1}
                transparent={isSemiTransparent}
                opacity={corridorLegOpacity}
                depthWrite={!isSemiTransparent}
              />
            </mesh>
            <mesh position={[0, -2.9, 0]} raycast={corridorRaycast}>
              <boxGeometry args={[0.9, 0.18, 0.9]} />
              <meshStandardMaterial
                color={isXray ? '#cbd5e1' : '#3a4454'}
                roughness={0.9}
                metalness={0.1}
                transparent={isSemiTransparent}
                opacity={corridorLegOpacity}
                depthWrite={!isSemiTransparent}
              />
            </mesh>
          </group>
        ))}
      </group>

      {/* Corridor 2: MAIN ↔ ENERGY (South Spine Connector) */}
      <group position={[0, 6.0, -16]}>
        <mesh castShadow={corridorCastShadow} receiveShadow raycast={corridorRaycast}>
          <boxGeometry args={[5.2, 7.6, 8.0]} />
          <meshStandardMaterial
            color="#e2e8f0"
            roughness={0.4}
            metalness={0.2}
            transparent={isSemiTransparent}
            opacity={corridorOpacity}
            depthWrite={!isSemiTransparent}
          />
        </mesh>
        <mesh position={[0, 3.9, 0]} raycast={corridorRaycast}>
          <boxGeometry args={[5.4, 0.24, 8.2]} />
          <meshStandardMaterial
            color={isXray ? '#e2e8f0' : '#334155'}
            roughness={0.6}
            metalness={0.4}
            transparent={isSemiTransparent}
            opacity={corridorParapetOp}
            depthWrite={!isSemiTransparent}
          />
        </mesh>
        {/* Side Ribbon Windows */}
        {[-2.65, 2.65].map((wx, wi) => (
          <mesh key={`c2-win-${wi}`} position={[wx, 0.4, 0]} rotation={[0, Math.PI / 2, 0]} raycast={corridorRaycast}>
            <boxGeometry args={[6.2, 1.4, 0.08]} />
            <meshStandardMaterial
              color="#0f172a"
              roughness={0.08}
              metalness={0.92}
              transparent={isSemiTransparent}
              opacity={corridorOpacity}
              depthWrite={!isSemiTransparent}
            />
          </mesh>
        ))}
        {/* High-Voltage Copper Busway on Corridor Roof */}
        <mesh position={[0, 4.15, 0]} raycast={corridorRaycast}>
          <boxGeometry args={[0.6, 0.15, 8.0]} />
          <meshStandardMaterial
            color="#f59e0b"
            metalness={0.7}
            roughness={0.3}
            transparent={isSemiTransparent}
            opacity={corridorOpacity}
            depthWrite={!isSemiTransparent}
          />
        </mesh>
        {/* Steel Pilings */}
        {[-1.8, 1.8].map((stX, i) => (
          <group key={i} position={[stX, -5.2, 0]}>
            <mesh castShadow={corridorCastShadow} raycast={corridorRaycast}>
              <cylinderGeometry args={[0.24, 0.24, 6.0, 8]} />
              <meshStandardMaterial
                color={corridorLegColor}
                roughness={0.8}
                metalness={0.1}
                transparent={isSemiTransparent}
                opacity={corridorLegOpacity}
                depthWrite={!isSemiTransparent}
              />
            </mesh>
            <mesh position={[0, -2.9, 0]} raycast={corridorRaycast}>
              <boxGeometry args={[0.9, 0.18, 0.9]} />
              <meshStandardMaterial
                color={isXray ? '#cbd5e1' : '#3a4454'}
                roughness={0.9}
                metalness={0.1}
                transparent={isSemiTransparent}
                opacity={corridorLegOpacity}
                depthWrite={!isSemiTransparent}
              />
            </mesh>
          </group>
        ))}
      </group>

      {/* Corridor 3: ENERGY ↔ GENERATOR (West Utility Breezeway) */}
      <group position={[-16.5, 5.5, -30]}>
        <mesh castShadow={corridorCastShadow} receiveShadow raycast={corridorRaycast}>
          <boxGeometry args={[5.5, 6.5, 4.5]} />
          <meshStandardMaterial
            color="#cbd5e1"
            roughness={0.45}
            metalness={0.25}
            transparent={isSemiTransparent}
            opacity={corridorOpacity}
            depthWrite={!isSemiTransparent}
          />
        </mesh>
        <mesh position={[0, 3.4, 0]} raycast={corridorRaycast}>
          <boxGeometry args={[5.6, 0.24, 4.6]} />
          <meshStandardMaterial
            color={isXray ? '#e2e8f0' : '#334155'}
            roughness={0.6}
            metalness={0.4}
            transparent={isSemiTransparent}
            opacity={corridorParapetOp}
            depthWrite={!isSemiTransparent}
          />
        </mesh>
        {/* Roof Fuel/Coolant Manifold Pipes */}
        {[-0.8, 0.8].map((pyOff, pi) => (
          <mesh key={`c3-pipe-${pi}`} position={[0, 3.65, pyOff]} rotation={[0, 0, Math.PI / 2]} raycast={corridorRaycast}>
            <cylinderGeometry args={[0.12, 0.12, 5.5, 8]} />
            <meshStandardMaterial
              color={pi === 0 ? '#b45309' : '#475569'}
              metalness={0.7}
              transparent={isSemiTransparent}
              opacity={corridorOpacity}
              depthWrite={!isSemiTransparent}
            />
          </mesh>
        ))}
        <group position={[0, -4.5, 0]}>
          <mesh castShadow={corridorCastShadow} raycast={corridorRaycast}>
            <cylinderGeometry args={[0.24, 0.24, 5.0, 8]} />
            <meshStandardMaterial
              color={corridorLegColor}
              roughness={0.8}
              metalness={0.1}
              transparent={isSemiTransparent}
              opacity={corridorLegOpacity}
              depthWrite={!isSemiTransparent}
            />
          </mesh>
          <mesh position={[0, -2.4, 0]} raycast={corridorRaycast}>
            <boxGeometry args={[0.85, 0.16, 0.85]} />
            <meshStandardMaterial
              color={isXray ? '#cbd5e1' : '#3a4454'}
              roughness={0.9}
              metalness={0.1}
              transparent={isSemiTransparent}
              opacity={corridorLegOpacity}
              depthWrite={!isSemiTransparent}
            />
          </mesh>
        </group>
      </group>

      {/* Corridor 4: ENERGY ↔ STORAGE (East Logistics Connector) */}
      <group position={[17.5, 5.5, -30]}>
        <mesh castShadow={corridorCastShadow} receiveShadow raycast={corridorRaycast}>
          <boxGeometry args={[5.5, 6.5, 4.5]} />
          <meshStandardMaterial
            color="#cbd5e1"
            roughness={0.45}
            metalness={0.25}
            transparent={isSemiTransparent}
            opacity={corridorOpacity}
            depthWrite={!isSemiTransparent}
          />
        </mesh>
        <mesh position={[0, 3.4, 0]} raycast={corridorRaycast}>
          <boxGeometry args={[5.6, 0.24, 4.6]} />
          <meshStandardMaterial
            color={isXray ? '#e2e8f0' : '#334155'}
            roughness={0.6}
            metalness={0.4}
            transparent={isSemiTransparent}
            opacity={corridorParapetOp}
            depthWrite={!isSemiTransparent}
          />
        </mesh>
        <group position={[0, -4.5, 0]}>
          <mesh castShadow={corridorCastShadow} raycast={corridorRaycast}>
            <cylinderGeometry args={[0.24, 0.24, 5.0, 8]} />
            <meshStandardMaterial
              color={corridorLegColor}
              roughness={0.8}
              metalness={0.1}
              transparent={isSemiTransparent}
              opacity={corridorLegOpacity}
              depthWrite={!isSemiTransparent}
            />
          </mesh>
          <mesh position={[0, -2.4, 0]} raycast={corridorRaycast}>
            <boxGeometry args={[0.85, 0.16, 0.85]} />
            <meshStandardMaterial
              color={isXray ? '#cbd5e1' : '#3a4454'}
              roughness={0.9}
              metalness={0.1}
              transparent={isSemiTransparent}
              opacity={corridorLegOpacity}
              depthWrite={!isSemiTransparent}
            />
          </mesh>
        </group>
      </group>

      {/* Corridor 5: ENERGY ↔ COMMS (South Covered Utility Corridor) */}
      <group position={[0, 4.5, -43]}>
        <mesh castShadow={corridorCastShadow} receiveShadow raycast={corridorRaycast}>
          <boxGeometry args={[3.5, 6.0, 6.0]} />
          <meshStandardMaterial
            color="#334155"
            roughness={0.7}
            metalness={0.3}
            transparent={isSemiTransparent}
            opacity={corridorOpacity}
            depthWrite={!isSemiTransparent}
          />
        </mesh>
        {[-1.8, 1.8].map((cx, i) => (
          <mesh key={i} position={[cx, 0, 0]} rotation={[Math.PI / 2, 0, 0]} raycast={corridorRaycast}>
            <cylinderGeometry args={[0.12, 0.12, 6.0, 8]} />
            <meshStandardMaterial
              color="#1e293b"
              roughness={0.5}
              transparent={isSemiTransparent}
              opacity={corridorOpacity}
              depthWrite={!isSemiTransparent}
            />
          </mesh>
        ))}
        <group position={[0, -4.2, 0]}>
          <mesh castShadow={corridorCastShadow} raycast={corridorRaycast}>
            <cylinderGeometry args={[0.22, 0.22, 4.5, 8]} />
            <meshStandardMaterial
              color={corridorLegColor}
              roughness={0.8}
              metalness={0.1}
              transparent={isSemiTransparent}
              opacity={corridorLegOpacity}
              depthWrite={!isSemiTransparent}
            />
          </mesh>
          <mesh position={[0, -2.1, 0]} raycast={corridorRaycast}>
            <boxGeometry args={[0.8, 0.14, 0.8]} />
            <meshStandardMaterial
              color={isXray ? '#cbd5e1' : '#3a4454'}
              roughness={0.9}
              metalness={0.1}
              transparent={isSemiTransparent}
              opacity={corridorLegOpacity}
              depthWrite={!isSemiTransparent}
            />
          </mesh>
        </group>
      </group>

      {/* ------------------------------------------------------------- */}
      {/* 4. UTILITY PIPELINE RACK (Generator ↔ Main Building)          */}
      {/* ------------------------------------------------------------- */}
      {/* Heavy insulated pipe manifold running diagonally from Generator region toward Main */}
      <group position={[-22, 1.0, -15]}>
        {/* Insulated Twin Main Pipes */}
        <mesh position={[0, 0, 0]} rotation={[Math.PI / 2, 0, 0]} raycast={corridorRaycast}>
          <cylinderGeometry args={[0.18, 0.18, 14.0, 12]} />
          <meshStandardMaterial
            color="#64748b"
            roughness={0.4}
            metalness={0.6}
            transparent={isSemiTransparent}
            opacity={corridorOpacity}
            depthWrite={!isSemiTransparent}
          />
        </mesh>
        <mesh position={[0.5, 0, 0]} rotation={[Math.PI / 2, 0, 0]} raycast={corridorRaycast}>
          <cylinderGeometry args={[0.12, 0.12, 14.0, 12]} />
          <meshStandardMaterial
            color="#b45309"
            roughness={0.4}
            metalness={0.6}
            transparent={isSemiTransparent}
            opacity={corridorOpacity}
            depthWrite={!isSemiTransparent}
          />
        </mesh>
        {/* Pipeline Support Saddles */}
        {[-4.5, -1.5, 1.5, 4.5].map((pz, i) => (
          <mesh key={`pipe-saddle-${i}`} position={[0.25, -0.6, pz]} raycast={corridorRaycast}>
            <boxGeometry args={[1.1, 0.8, 0.4]} />
            <meshStandardMaterial
              color={corridorLegColor}
              roughness={0.8}
              metalness={0.1}
              transparent={isSemiTransparent}
              opacity={corridorLegOpacity}
              depthWrite={!isSemiTransparent}
            />
          </mesh>
        ))}
      </group>

      {/* ------------------------------------------------------------- */}
      {/* 6. POLAR BOUNDARY SURVEY STAKES & HIGH-VISIBILITY MARKERS     */}
      {/* Placed at the 4 outer corners of the full station footprint   */}
      {/* Footprint: X -44..+52, Z -64..+20                            */}
      {/* ------------------------------------------------------------- */}
      {[
        [-46.0, 1.2, -64.0],
        [ 54.0, 1.2, -64.0],
        [-46.0, 1.2,  20.0],
        [ 54.0, 1.2,  20.0],
        [  4.0, 1.2, -64.0],
        [  4.0, 1.2,  20.0],
      ].map(([fx, fy, fz], idx) => (
        <group key={`survey-flag-${idx}`} position={[fx, fy, fz]}>
          <mesh>
            <cylinderGeometry args={[0.08, 0.08, 3.0, 6]} />
            <meshStandardMaterial color="#2d333b" roughness={0.7} />
          </mesh>
          <mesh position={[0.32, 1.1, 0]}>
            <boxGeometry args={[0.65, 0.42, 0.04]} />
            <meshStandardMaterial color="#b65a1f" roughness={0.5} />
          </mesh>
        </group>
      ))}

      {/* ------------------------------------------------------------- */}
      {/* 7. INDIAN NATIONAL FLAGPOLE & TRICOLOR (Station Forecourt)    */}
      {/* Grounded on permafrost snowfield at x=-8.5, z=18.0             */}
      {/* ------------------------------------------------------------- */}
      <IndianFlagPole
        position={[-8.5, 0, 18.0]}
        twinMode={twinMode}
      />
        </>
      )}
    </group>
  );
};

export default StationModel;
