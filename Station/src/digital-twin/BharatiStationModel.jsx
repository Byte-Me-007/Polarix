import React, { useMemo } from 'react';
import * as THREE from 'three';
import { StationZone } from './StationZone';
import { computeDisplayPos } from './SensorMarker';
import { getAssociatedAssetIdForSensor, ZONE_INTERNAL_ASSETS } from './stationAssets';
import { IndianFlagPole } from './IndianFlagPole';
import { ZONE_STATUS_CONFIG } from './StationModel';

/**
 * BharatiStationModel — Distinct 3D spatial representation of Bharati Research Station.
 *
 * Key characteristics vs Maitri:
 *  - ROCKY coastal terrain (Larsemann Hills promontory, near Thala Fjord / Quilty Bay)
 *  - COMPACT modular main building with elevated columns, container-style multi-level massing
 *  - FUEL FARM separated south-west (not adjacent to main building)
 *  - HELIPAD clear open area north of main station
 *  - SEAWATER PUMP HOUSE on coastal side
 *  - SUMMER / SUPPORT CONTAINER MODULES clustered near main building
 *  - FJORD EDGE visible to north — water subtle, not dominant
 *  - Darker exposed ROCK substrate, snow patches, low coastal terrain
 *  - No Maitri corridors or pipeline rack geometry
 *
 * Zone layout:
 *   MAIN:      [0, 6.5, 0]       28×13×20
 *   ENERGY:    [-26, 5.5, -22]   22×11×16
 *   RESEARCH:  [34, 5.5, 6]      20×11×16
 *   STORAGE:   [24, 5.0, -18]    18×10×14
 *   GENERATOR: [-26, 4.5, -44]   18×9×14  (FUEL FARM)
 *   COMMS:     [6, 4.5, -46]     12×9×12
 */

// ─── Bharati corridor/bridge helpers ────────────────────────────────────────

// Simple Bharati-specific connecting bridges between modules
const BharatiModuleBridge = ({ from, to, width = 4.0, height = 1.6, opacity, depthWrite, isXray, parOpacity }) => {
  const dx = to[0] - from[0];
  const dz = to[2] - from[2];
  const length = Math.hypot(dx, dz);
  const angle = Math.atan2(dz, dx);
  const midX = (from[0] + to[0]) / 2;
  const midY = Math.max(from[1], to[1]);
  const midZ = (from[2] + to[2]) / 2;

  return (
    <group position={[midX, midY, midZ]} rotation={[0, -angle, 0]}>
      {/* Enclosed walkway body */}
      <mesh castShadow receiveShadow>
        <boxGeometry args={[length, height, width]} />
        <meshStandardMaterial
          color="#dcd8d0"
          roughness={0.5}
          metalness={0.18}
          transparent={opacity < 1}
          opacity={opacity}
          depthWrite={depthWrite}
        />
      </mesh>
      {/* Parapet coping strip */}
      <mesh position={[0, height / 2 + 0.12, 0]}>
        <boxGeometry args={[length + 0.2, 0.22, width + 0.2]} />
        <meshStandardMaterial
          color={isXray ? '#e2e8f0' : '#334155'}
          roughness={0.6}
          metalness={0.4}
          transparent={opacity < 1}
          opacity={parOpacity}
          depthWrite={depthWrite}
        />
      </mesh>
      {/* Column legs */}
      {[-length * 0.3, length * 0.3].map((lx, i) => (
        <group key={i} position={[lx, -height / 2 - 2.5, 0]}>
          <mesh castShadow>
            <cylinderGeometry args={[0.22, 0.22, 5.0, 8]} />
            <meshStandardMaterial
              color="#242a35"
              roughness={0.8}
              metalness={0.1}
              transparent={opacity < 1}
              opacity={parOpacity}
              depthWrite={depthWrite}
            />
          </mesh>
        </group>
      ))}
    </group>
  );
};

// ─── Bharati Helipad ─────────────────────────────────────────────────────────
const BharatiHelipad = ({ position, opacity }) => {
  const [px, py, pz] = position;
  const isT = opacity < 1;
  return (
    <group position={position}>
      {/* Asphalt / compacted ground pad */}
      <mesh receiveShadow rotation={[-Math.PI / 2, 0, 0]} position={[0, 0.04, 0]}>
        <circleGeometry args={[9.5, 36]} />
        <meshStandardMaterial
          color="#5a6070"
          roughness={0.95}
          metalness={0.05}
          transparent={isT}
          opacity={opacity}
          depthWrite={!isT}
        />
      </mesh>
      {/* Yellow circle perimeter ring */}
      <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, 0.06, 0]}>
        <ringGeometry args={[8.0, 9.0, 48]} />
        <meshBasicMaterial
          color="#e8c14a"
          transparent
          opacity={isT ? opacity * 0.6 : 0.92}
          depthWrite={false}
          side={THREE.DoubleSide}
        />
      </mesh>
      {/* H marking — horizontal bar */}
      <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, 0.07, 0]}>
        <boxGeometry args={[5.4, 1.4, 0.06]} />
        <meshBasicMaterial color="#e8c14a" transparent opacity={isT ? opacity * 0.6 : 0.88} depthWrite={false} />
      </mesh>
      {/* H marking — vertical bar */}
      <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, 0.07, 0]}>
        <boxGeometry args={[1.4, 4.8, 0.06]} />
        <meshBasicMaterial color="#e8c14a" transparent opacity={isT ? opacity * 0.6 : 0.88} depthWrite={false} />
      </mesh>
      {/* Left leg */}
      <mesh rotation={[-Math.PI / 2, 0, 0]} position={[-2.0, 0.07, 0]}>
        <boxGeometry args={[1.4, 4.8, 0.06]} />
        <meshBasicMaterial color="#e8c14a" transparent opacity={isT ? opacity * 0.6 : 0.88} depthWrite={false} />
      </mesh>
      {/* Right leg */}
      <mesh rotation={[-Math.PI / 2, 0, 0]} position={[2.0, 0.07, 0]}>
        <boxGeometry args={[1.4, 4.8, 0.06]} />
        <meshBasicMaterial color="#e8c14a" transparent opacity={isT ? opacity * 0.6 : 0.88} depthWrite={false} />
      </mesh>
      {/* Wind indicator socket stub */}
      <mesh position={[8.0, 1.2, 0]}>
        <cylinderGeometry args={[0.08, 0.08, 2.4, 8]} />
        <meshStandardMaterial color="#e2e8f0" metalness={0.7} roughness={0.3} transparent={isT} opacity={opacity} />
      </mesh>
      <mesh position={[8.0, 2.8, 0.5]} rotation={[0, 0, -0.3]}>
        <coneGeometry args={[0.18, 0.6, 6]} />
        <meshStandardMaterial color="#e03131" transparent opacity={isT ? opacity * 0.8 : 0.9} depthWrite={!isT} />
      </mesh>
    </group>
  );
};

// ─── Seawater Pump House ─────────────────────────────────────────────────────
const SeawaterPumpHouse = ({ position, twinMode }) => {
  const isXray = twinMode === 'XRAY';
  const isSemi = isXray || twinMode === 'SYSTEM' || twinMode === 'HEATMAP';
  const op = isXray ? 0.14 : isSemi ? 0.38 : 1.0;
  const isT = isSemi;

  return (
    <group position={position}>
      {/* Shed body */}
      <mesh castShadow receiveShadow>
        <boxGeometry args={[8.0, 4.5, 6.0]} />
        <meshStandardMaterial
          color="#b8cdd4"
          roughness={0.55}
          metalness={0.3}
          transparent={isT}
          opacity={op}
          depthWrite={!isT}
        />
      </mesh>
      {/* Roof slant panel */}
      <mesh position={[0, 2.5, 0]} rotation={[0.15, 0, 0]}>
        <boxGeometry args={[8.2, 0.22, 6.4]} />
        <meshStandardMaterial color="#334155" roughness={0.6} metalness={0.4} transparent={isT} opacity={isXray ? 0.08 : op * 0.9} depthWrite={!isT} />
      </mesh>
      {/* Column stilts */}
      {[[-2.5, -3.5], [2.5, -3.5], [-2.5, 3.5], [2.5, 3.5]].map(([cx, cz], i) => (
        <mesh key={i} position={[cx, -3.8, cz]} castShadow>
          <cylinderGeometry args={[0.18, 0.18, 4.0, 8]} />
          <meshStandardMaterial color="#475569" roughness={0.8} metalness={0.1} transparent={isT} opacity={isXray ? 0.12 : op * 0.9} depthWrite={!isT} />
        </mesh>
      ))}
      {/* Pipe going toward coast */}
      <mesh position={[0, -1.8, 4.5]} rotation={[Math.PI / 2, 0, 0]}>
        <cylinderGeometry args={[0.16, 0.16, 9.0, 8]} />
        <meshStandardMaterial color="#64748b" roughness={0.4} metalness={0.6} transparent={isT} opacity={isXray ? 0.10 : op * 0.8} depthWrite={!isT} />
      </mesh>
      {/* Pump machinery silhouette inside */}
      {isXray && (
        <mesh position={[0, -0.8, 0]}>
          <boxGeometry args={[2.8, 1.8, 2.0]} />
          <meshStandardMaterial color="#1e88e5" wireframe opacity={0.55} transparent />
        </mesh>
      )}
    </group>
  );
};

// ─── Fuel Farm Tanks ──────────────────────────────────────────────────────────
const FuelFarmTanks = ({ position, twinMode }) => {
  const isXray = twinMode === 'XRAY';
  const isSemi = isXray || twinMode === 'SYSTEM' || twinMode === 'HEATMAP';
  const op = isXray ? 0.12 : isSemi ? 0.35 : 1.0;
  const isT = isSemi;

  // Tank positions relative to group origin — 4 industrial tanks
  const tanks = [
    { pos: [-7.0, 0, -3.5], r: 2.2, h: 4.8, color: '#8896a8' },
    { pos: [-7.0, 0,  3.5], r: 2.2, h: 4.8, color: '#8896a8' },
    { pos: [ 0.0, 0, -3.5], r: 2.6, h: 5.8, color: '#78899a' },
    { pos: [ 0.0, 0,  3.5], r: 2.6, h: 5.8, color: '#78899a' },
  ];

  return (
    <group position={position}>
      {tanks.map((t, i) => (
        <group key={i} position={t.pos}>
          {/* Tank cylinder */}
          <mesh castShadow>
            <cylinderGeometry args={[t.r, t.r, t.h, 16]} />
            <meshStandardMaterial
              color={t.color}
              roughness={0.45}
              metalness={0.6}
              transparent={isT}
              opacity={op}
              depthWrite={!isT}
            />
          </mesh>
          {/* Dome cap */}
          <mesh position={[0, t.h / 2 + 0.18, 0]}>
            <sphereGeometry args={[t.r * 0.55, 12, 8, 0, Math.PI * 2, 0, Math.PI / 2]} />
            <meshStandardMaterial color="#94a3b8" roughness={0.35} metalness={0.7} transparent={isT} opacity={isXray ? 0.08 : op} depthWrite={!isT} />
          </mesh>
          {/* Level gauge vertical strip */}
          <mesh position={[t.r - 0.08, 0, 0]}>
            <boxGeometry args={[0.12, t.h * 0.85, 0.12]} />
            <meshStandardMaterial color="#e2e8f0" roughness={0.3} metalness={0.8} transparent={isT} opacity={op} depthWrite={!isT} />
          </mesh>
        </group>
      ))}
      {/* Fuel manifold interconnect pipe */}
      <mesh position={[-3.5, 0, 0]} rotation={[Math.PI / 2, 0, 0]}>
        <cylinderGeometry args={[0.14, 0.14, 8.0, 8]} />
        <meshStandardMaterial color="#b45309" roughness={0.4} metalness={0.6} transparent={isT} opacity={isXray ? 0.1 : op * 0.85} depthWrite={!isT} />
      </mesh>
      {/* Berm / containment wall foundation */}
      <mesh receiveShadow rotation={[-Math.PI / 2, 0, 0]} position={[0, -2.8, 0]}>
        <planeGeometry args={[22.0, 14.0]} />
        <meshStandardMaterial color="#5c6472" roughness={0.95} metalness={0.02} transparent={isT} opacity={isXray ? 0.06 : op * 0.7} depthWrite={!isT} />
      </mesh>
    </group>
  );
};

// ─── Summer / Support Container Module ───────────────────────────────────────
const ContainerModule = ({ position, rotation = [0, 0, 0], color = '#c8cfd8', twinMode }) => {
  const isXray = twinMode === 'XRAY';
  const isSemi = isXray || twinMode === 'SYSTEM' || twinMode === 'HEATMAP';
  const op = isXray ? 0.12 : isSemi ? 0.36 : 1.0;
  const isT = isSemi;

  return (
    <group position={position} rotation={rotation}>
      {/* Container body */}
      <mesh castShadow receiveShadow>
        <boxGeometry args={[6.0, 2.8, 2.6]} />
        <meshStandardMaterial color={color} roughness={0.6} metalness={0.35} transparent={isT} opacity={op} depthWrite={!isT} />
      </mesh>
      {/* Corrugated ribbing strips */}
      {[-1.8, -0.6, 0.6, 1.8].map((rx, i) => (
        <mesh key={i} position={[rx, 0, 1.31]}>
          <boxGeometry args={[0.18, 2.8, 0.06]} />
          <meshStandardMaterial color="#8896a8" roughness={0.5} metalness={0.4} transparent={isT} opacity={isXray ? 0.08 : op * 0.7} depthWrite={!isT} />
        </mesh>
      ))}
      {/* Door outline */}
      <mesh position={[2.2, -0.25, 1.31]}>
        <boxGeometry args={[1.2, 2.2, 0.06]} />
        <meshStandardMaterial color="#475569" roughness={0.65} metalness={0.3} transparent={isT} opacity={isXray ? 0.06 : op * 0.6} depthWrite={!isT} />
      </mesh>
      {/* Mounting feet */}
      {[[-2.6, -1.6], [2.6, -1.6], [-2.6, 1.2], [2.6, 1.2]].map(([fx, fz], i) => (
        <mesh key={i} position={[fx, -1.6, fz]}>
          <boxGeometry args={[0.4, 0.28, 0.4]} />
          <meshStandardMaterial color="#334155" roughness={0.9} metalness={0.1} transparent={isT} opacity={isXray ? 0.06 : op * 0.8} depthWrite={!isT} />
        </mesh>
      ))}
    </group>
  );
};

// ─── Fuel Station Service Point ──────────────────────────────────────────────
const FuelStation = ({ position, twinMode }) => {
  const isXray = twinMode === 'XRAY';
  const isSemi = isXray || twinMode === 'SYSTEM' || twinMode === 'HEATMAP';
  const op = isXray ? 0.1 : isSemi ? 0.35 : 1.0;
  const isT = isSemi;

  return (
    <group position={position}>
      {/* Canopy frame */}
      <mesh position={[0, 3.2, 0]}>
        <boxGeometry args={[6.5, 0.22, 4.5]} />
        <meshStandardMaterial color="#334155" roughness={0.6} metalness={0.5} transparent={isT} opacity={op} depthWrite={!isT} />
      </mesh>
      {/* Canopy columns */}
      {[[-2.8, 0, -1.8], [2.8, 0, -1.8], [-2.8, 0, 1.8], [2.8, 0, 1.8]].map(([cx, cy, cz], i) => (
        <mesh key={i} position={[cx, 1.5, cz]} castShadow>
          <cylinderGeometry args={[0.12, 0.12, 3.2, 8]} />
          <meshStandardMaterial color="#475569" roughness={0.8} metalness={0.2} transparent={isT} opacity={op} depthWrite={!isT} />
        </mesh>
      ))}
      {/* Pump unit */}
      <mesh position={[0, 0.7, 0]} castShadow>
        <boxGeometry args={[1.2, 1.4, 0.5]} />
        <meshStandardMaterial color="#64748b" roughness={0.5} metalness={0.5} transparent={isT} opacity={op} depthWrite={!isT} />
      </mesh>
      {/* Hose reel */}
      <mesh position={[0.9, 0.8, 0]} rotation={[0, 0, Math.PI / 2]}>
        <torusGeometry args={[0.35, 0.1, 8, 16]} />
        <meshStandardMaterial color="#b45309" roughness={0.4} metalness={0.5} transparent={isT} opacity={op} depthWrite={!isT} />
      </mesh>
    </group>
  );
};

// ─── Rocky Terrain Outcrop ───────────────────────────────────────────────────
const RockOutcrop = ({ position, scale = [1, 1, 1], color = '#5a6070' }) => (
  <mesh position={position} scale={scale} castShadow receiveShadow rotation={[0, Math.random() * Math.PI, 0]}>
    <dodecahedronGeometry args={[1.0, 0]} />
    <meshStandardMaterial color={color} roughness={0.95} metalness={0.02} />
  </mesh>
);

// ─── BharatiStationModel (main export) ───────────────────────────────────────
export const BharatiStationModel = ({
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
  incidentAffectedZones = null,
  incidentPrimaryZones  = null,
  incidentActive        = false,
  incidentGraph         = null,
}) => {
  const zones = station?.digitalTwin?.zones || [];

  const isXray = twinMode === 'XRAY';
  const isSemiTransparent = showHeatmap || isXray || twinMode === 'SYSTEM';

  const terrainOp    = isXray ? 0.10 : isSemiTransparent ? 0.28 : 1.0;
  const terrainIsT   = isSemiTransparent;

  // Shared corridor/bridge material settings
  const bridgeOp    = isXray ? 0.12 : isSemiTransparent ? 0.38 : 1.0;
  const bridgeParOp = isXray ? 0.06 : isSemiTransparent ? 0.25 : 1.0;
  const bridgeDW    = !isSemiTransparent;

  // Sensor → asset relationship (same logic as StationModel)
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

    return { sensorDisp, assetWorld, dist, mid: [mid.x, mid.y, mid.z], quat, assetDef, assetId: targetAssetId };
  }, [selectedSensor, zones]);

  // Zone health from sensors
  const zoneHealth = useMemo(() => {
    const map = {};
    zones.forEach((z) => {
      const code = z.code || z.id;
      const zoneSensors = sensors.filter((s) => s.zone === code);
      let maxSev = -1;
      let dominant = 'NORMAL';
      zoneSensors.forEach((s) => {
        const stat = (s.status || 'NORMAL').toUpperCase();
        let sev = stat === 'CRITICAL' ? 3 : stat === 'WARNING' ? 2 : stat === 'OFFLINE' ? 1 : 0;
        if (sev > maxSev) { maxSev = sev; dominant = stat; }
      });
      map[code] = dominant;
    });
    return map;
  }, [sensors, zones]);

  return (
    <group name="bharati-station-model">
      {/* ─────────────────────────────────────────────────────────────────────
          1. COASTAL ROCKY TERRAIN — Larsemann Hills promontory
          Darker rocky Antarctic ground vs Maitri's white snow.
          Exposed rock substrate with snow patches, coastal edge.
      ───────────────────────────────────────────────────────────────────── */}

      {/* Main ground — dark rocky coastal substrate */}
      <mesh receiveShadow rotation={[-Math.PI / 2, 0, 0]} position={[0, -0.08, -10]}>
        <planeGeometry args={[280, 260, 1, 1]} />
        <meshStandardMaterial
          color="#4a5060"
          roughness={0.97}
          metalness={0.03}
          transparent={terrainIsT}
          opacity={terrainOp}
          depthWrite={!terrainIsT}
        />
      </mesh>

      {/* Subtle survey reference grid — darker for rocky terrain */}
      <gridHelper
        args={[220, 44, '#555e6e', '#4a5060']}
        position={[0, 0.01, -10]}
      />

      {/* Snow patches on rocky ground — irregular white patches */}
      {[
        { pos: [12, 0.02, 25], size: [14, 0.04, 10] },
        { pos: [-18, 0.02, 22], size: [10, 0.04, 8] },
        { pos: [35, 0.02, -8], size: [12, 0.04, 7] },
        { pos: [-8, 0.02, -55], size: [18, 0.04, 9] },
        { pos: [40, 0.02, -32], size: [8, 0.04, 6] },
        { pos: [-38, 0.02, -35], size: [10, 0.04, 8] },
        { pos: [16, 0.02, -42], size: [9, 0.04, 7] },
      ].map((p, i) => (
        <mesh key={`snow-${i}`} receiveShadow rotation={[-Math.PI / 2, 0, 0]} position={p.pos}>
          <planeGeometry args={[p.size[0], p.size[2]]} />
          <meshStandardMaterial
            color="#dce4ec"
            roughness={0.92}
            metalness={0.04}
            transparent={terrainIsT}
            opacity={terrainOp * 1.2}
            depthWrite={!terrainIsT}
          />
        </mesh>
      ))}

      {/* Rocky outcrops scattered around the promontory */}
      {[
        { pos: [-42, 1.4, 18],  scale: [2.8, 1.8, 2.2], color: '#4a5060' },
        { pos: [-36, 1.0, 28],  scale: [2.0, 1.2, 2.0], color: '#525c6a' },
        { pos: [48, 1.6, 20],   scale: [3.2, 2.0, 2.8], color: '#424d5c' },
        { pos: [52, 0.9, 10],   scale: [1.8, 1.0, 1.6], color: '#4a5060' },
        { pos: [-50, 1.2, -10], scale: [2.4, 1.4, 2.0], color: '#505a68' },
        { pos: [-48, 2.0, -28], scale: [3.0, 1.8, 2.4], color: '#424d5c' },
        { pos: [44, 1.8, -38],  scale: [2.2, 1.4, 1.8], color: '#4a5060' },
        { pos: [12, 1.2, -62],  scale: [2.8, 1.6, 2.4], color: '#525c6a' },
        { pos: [-20, 2.4, -58], scale: [3.4, 2.2, 3.0], color: '#424d5c' },
        { pos: [30, 1.0, 32],   scale: [2.0, 1.2, 1.8], color: '#505a68' },
        { pos: [-28, 1.8, 30],  scale: [2.6, 1.6, 2.2], color: '#4a5060' },
      ].map((r, i) => (
        <RockOutcrop key={`rock-${i}`} position={r.pos} scale={r.scale} color={r.color} />
      ))}

      {/* ─────────────────────────────────────────────────────────────────────
          2. FJORD EDGE — Thala Fjord / Quilty Bay coastal water plane
          Subtle, not dominant. Located north of station.
      ───────────────────────────────────────────────────────────────────── */}
      <mesh receiveShadow rotation={[-Math.PI / 2, 0, 0]} position={[0, -1.0, 62]}>
        <planeGeometry args={[220, 55, 1, 1]} />
        <meshStandardMaterial
          color="#2d4a6a"
          roughness={0.15}
          metalness={0.55}
          transparent
          opacity={terrainIsT ? terrainOp * 0.5 : 0.72}
          depthWrite={false}
        />
      </mesh>
      {/* Ice floe patches on fjord surface */}
      {[[-20, 60], [15, 68], [-5, 72], [30, 64], [-35, 70]].map(([fx, fz], i) => (
        <mesh key={`floe-${i}`} receiveShadow rotation={[-Math.PI / 2, 0, 0]} position={[fx, -0.5, fz]}>
          <circleGeometry args={[3.5 + i * 0.8, 12]} />
          <meshStandardMaterial
            color="#c8d8e8"
            roughness={0.88}
            metalness={0.06}
            transparent
            opacity={terrainIsT ? terrainOp * 0.6 : 0.65}
            depthWrite={false}
          />
        </mesh>
      ))}
      {/* Coastal rock shoreline edge */}
      <mesh position={[0, 0.3, 42]} rotation={[-Math.PI / 2, 0, 0]}>
        <planeGeometry args={[220, 8, 1, 1]} />
        <meshStandardMaterial
          color="#3a434e"
          roughness={0.98}
          metalness={0.02}
          transparent={terrainIsT}
          opacity={terrainOp}
          depthWrite={!terrainIsT}
        />
      </mesh>

      {/* ─────────────────────────────────────────────────────────────────────
          3. STATION ZONE BUILDINGS — driven by digitalTwin.zones
          Same component as Maitri (StationZone) — different positions
      ───────────────────────────────────────────────────────────────────── */}
      {zones.map((zone) => {
        const code = zone.code || zone.id;
        const status = zoneHealth[code] || 'NORMAL';
        const meta = ZONE_STATUS_CONFIG[status] || ZONE_STATUS_CONFIG.NORMAL;
        const isSelectedZone = Boolean(selectedZone && (code === selectedZone));
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

      {/* ─────────────────────────────────────────────────────────────────────
          4. BHARATI CONNECTING BRIDGES (not Maitri corridors)
          Compact bridges between MAIN, ENERGY, STORAGE, RESEARCH
      ───────────────────────────────────────────────────────────────────── */}

      {/* MAIN ↔ ENERGY bridge (west wing connector) */}
      <BharatiModuleBridge
        from={[-14, 5.5, 0]}
        to={[-15, 4.8, -14]}
        width={3.8}
        height={1.5}
        opacity={bridgeOp}
        depthWrite={bridgeDW}
        isXray={isXray}
        parOpacity={bridgeParOp}
      />

      {/* MAIN ↔ STORAGE bridge (east connector) */}
      <BharatiModuleBridge
        from={[14, 5.5, -2]}
        to={[15, 4.8, -11]}
        width={3.5}
        height={1.4}
        opacity={bridgeOp}
        depthWrite={bridgeDW}
        isXray={isXray}
        parOpacity={bridgeParOp}
      />

      {/* MAIN ↔ RESEARCH bridge (east-north) */}
      <BharatiModuleBridge
        from={[14, 5.5, 2]}
        to={[24, 4.8, 5]}
        width={3.2}
        height={1.4}
        opacity={bridgeOp}
        depthWrite={bridgeDW}
        isXray={isXray}
        parOpacity={bridgeParOp}
      />

      {/* ENERGY ↔ GENERATOR (FUEL FARM) conduit tunnel */}
      <BharatiModuleBridge
        from={[-26, 4.2, -30]}
        to={[-26, 3.8, -37]}
        width={3.0}
        height={1.3}
        opacity={bridgeOp}
        depthWrite={bridgeDW}
        isXray={isXray}
        parOpacity={bridgeParOp}
      />

      {/* ─────────────────────────────────────────────────────────────────────
          5. FUEL FARM — Separated industrial HSD storage complex
          South-west of main station, near GENERATOR zone
      ───────────────────────────────────────────────────────────────────── */}
      <FuelFarmTanks position={[-20, 4.0, -55]} twinMode={twinMode} />

      {/* Fuel manifold pipe to GENERATOR zone */}
      <group position={[-26, 1.2, -50]} rotation={[Math.PI / 2, 0, 0]}>
        <mesh>
          <cylinderGeometry args={[0.14, 0.14, 10.0, 8]} />
          <meshStandardMaterial
            color="#b45309"
            roughness={0.4}
            metalness={0.6}
            transparent={isSemiTransparent}
            opacity={isXray ? 0.10 : isSemiTransparent ? 0.45 : 0.85}
            depthWrite={!isSemiTransparent}
          />
        </mesh>
      </group>

      {/* ─────────────────────────────────────────────────────────────────────
          6. FUEL STATION — Vehicle service point, south of ENERGY zone
      ───────────────────────────────────────────────────────────────────── */}
      <FuelStation position={[-14, 0.1, -12]} twinMode={twinMode} />

      {/* ─────────────────────────────────────────────────────────────────────
          7. SEA WATER PUMP HOUSE — Coastal infrastructure, north-west
      ───────────────────────────────────────────────────────────────────── */}
      <SeawaterPumpHouse position={[-22, 3.8, 18]} twinMode={twinMode} />

      {/* Seawater supply pipe running north toward fjord */}
      <group position={[-22, 0.2, 32]} rotation={[Math.PI / 2, 0, 0]}>
        <mesh>
          <cylinderGeometry args={[0.12, 0.12, 20.0, 8]} />
          <meshStandardMaterial
            color="#475569"
            roughness={0.5}
            metalness={0.5}
            transparent={isSemiTransparent}
            opacity={isXray ? 0.08 : isSemiTransparent ? 0.4 : 0.75}
            depthWrite={!isSemiTransparent}
          />
        </mesh>
      </group>

      {/* ─────────────────────────────────────────────────────────────────────
          8. HELIPAD — Clear open landing area, north of main building
      ───────────────────────────────────────────────────────────────────── */}
      <BharatiHelipad
        position={[0, 0.1, 32]}
        opacity={isXray ? 0.18 : isSemiTransparent ? 0.55 : 1.0}
      />

      {/* Helipad approach lighting poles (2 each side) */}
      {[[-10, 28], [10, 28], [-10, 36], [10, 36]].map(([lx, lz], i) => (
        <group key={`heli-light-${i}`} position={[lx, 0.1, lz]}>
          <mesh castShadow>
            <cylinderGeometry args={[0.06, 0.06, 1.8, 6]} />
            <meshStandardMaterial color="#e2e8f0" metalness={0.7} roughness={0.3} transparent={isSemiTransparent} opacity={isXray ? 0.1 : bridgeOp} depthWrite={!isSemiTransparent} />
          </mesh>
          <mesh position={[0, 1.0, 0]}>
            <sphereGeometry args={[0.1, 8, 8]} />
            <meshBasicMaterial color="#f59e0b" transparent opacity={isSemiTransparent ? 0.4 : 0.9} />
          </mesh>
        </group>
      ))}

      {/* ─────────────────────────────────────────────────────────────────────
          9. SUMMER / SUPPORT CONTAINER MODULES — near main building
      ───────────────────────────────────────────────────────────────────── */}
      <ContainerModule position={[14, 1.4, 14]}  rotation={[0, 0.3, 0]}  color="#b8c4cc" twinMode={twinMode} />
      <ContainerModule position={[22, 1.4, 18]}  rotation={[0, 0.1, 0]}  color="#c2ccd4" twinMode={twinMode} />
      <ContainerModule position={[8, 1.4, 20]}   rotation={[0, -0.15, 0]} color="#aebbc4" twinMode={twinMode} />
      <ContainerModule position={[-10, 1.4, 24]} rotation={[0, 0.2, 0]}  color="#b4c0cc" twinMode={twinMode} />

      {/* ─────────────────────────────────────────────────────────────────────
          10. SCIENCE / RESEARCH EQUIPMENT — near RESEARCH zone exterior
      ───────────────────────────────────────────────────────────────────── */}
      {/* Meteorological mast */}
      <group position={[46, 0.1, 12]}>
        <mesh castShadow>
          <cylinderGeometry args={[0.08, 0.12, 8.0, 8]} />
          <meshStandardMaterial color="#94a3b8" metalness={0.6} roughness={0.4} transparent={isSemiTransparent} opacity={isXray ? 0.12 : bridgeOp} depthWrite={!isSemiTransparent} />
        </mesh>
        {/* Anemometer arms */}
        {[0, Math.PI / 2, Math.PI, Math.PI * 1.5].map((ang, i) => (
          <group key={i} position={[Math.cos(ang) * 0.7, 7.5, Math.sin(ang) * 0.7]}>
            <mesh>
              <sphereGeometry args={[0.18, 6, 6]} />
              <meshStandardMaterial color="#475569" metalness={0.7} roughness={0.3} transparent={isSemiTransparent} opacity={isXray ? 0.1 : bridgeOp} depthWrite={!isSemiTransparent} />
            </mesh>
          </group>
        ))}
      </group>

      {/* Science equipment shelter (generic) */}
      <mesh position={[42, 1.2, 18]} castShadow>
        <boxGeometry args={[3.5, 2.4, 2.8]} />
        <meshStandardMaterial color="#c8d0d8" roughness={0.55} metalness={0.25} transparent={isSemiTransparent} opacity={isXray ? 0.12 : bridgeOp} depthWrite={!isSemiTransparent} />
      </mesh>

      {/* ─────────────────────────────────────────────────────────────────────
          11. SENSOR ↔ ASSET RELATIONSHIP INDICATOR
      ───────────────────────────────────────────────────────────────────── */}
      {sensorRelationship && (
        <group name="sensor-asset-connector">
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
          <mesh
            position={[sensorRelationship.sensorDisp.x, sensorRelationship.sensorDisp.y, sensorRelationship.sensorDisp.z]}
            raycast={() => null}
          >
            <sphereGeometry args={[0.22, 12, 12]} />
            <meshStandardMaterial color="#b65a1f" emissive="#b65a1f" emissiveIntensity={0.9} />
          </mesh>
          <mesh
            position={[sensorRelationship.assetWorld[0], sensorRelationship.assetWorld[1] + 0.06, sensorRelationship.assetWorld[2]]}
            rotation={[-Math.PI / 2, 0, 0]}
            raycast={() => null}
          >
            <ringGeometry args={[1.6, 1.95, 32]} />
            <meshBasicMaterial color="#b65a1f" transparent opacity={0.85} depthWrite={false} side={THREE.DoubleSide} />
          </mesh>
        </group>
      )}

      {/* ─────────────────────────────────────────────────────────────────────
          12. BOUNDARY SURVEY STAKES — Bharati footprint corners
          Footprint: X -52..+54, Z -60..+44
      ───────────────────────────────────────────────────────────────────── */}
      {[
        [-52, 1.2, -60], [54, 1.2, -60], [-52, 1.2, 44], [54, 1.2, 44],
        [0, 1.2, -60], [0, 1.2, 44]
      ].map(([fx, fy, fz], idx) => (
        <group key={`bhr-stake-${idx}`} position={[fx, fy, fz]}>
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

      {/* ─────────────────────────────────────────────────────────────────────
          13. INDIAN NATIONAL FLAG — Bharati forecourt, landmark scale
          Positioned prominently in the open forecourt directly north of the
          main building entrance. Large enough to be immediately visible from
          the default camera overview. Pole height ~20 u, flag 7×4.7 u.
      ───────────────────────────────────────────────────────────────────── */}

      {/* Ceremonial concrete base platform */}
      <mesh receiveShadow position={[-14, 0.18, 12]} rotation={[-Math.PI / 2, 0, 0]}>
        <circleGeometry args={[3.2, 24]} />
        <meshStandardMaterial
          color="#5a6270"
          roughness={0.9}
          metalness={0.05}
          transparent={isSemiTransparent}
          opacity={terrainOp}
          depthWrite={!terrainIsT}
        />
      </mesh>
      {/* Outer paving ring */}
      <mesh receiveShadow position={[-14, 0.22, 12]} rotation={[-Math.PI / 2, 0, 0]}>
        <ringGeometry args={[3.0, 4.5, 36]} />
        <meshStandardMaterial
          color="#4e5666"
          roughness={0.95}
          metalness={0.02}
          transparent={isSemiTransparent}
          opacity={terrainOp}
          depthWrite={!terrainIsT}
        />
      </mesh>

      <IndianFlagPole
        position={[-14, 0, 12]}
        poleHeight={20}
        flagWidth={7.0}
        flagHeight={4.7}
        twinMode={twinMode}
      />



    </group>
  );
};

export default BharatiStationModel;
