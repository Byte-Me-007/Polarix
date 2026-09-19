import React, { useMemo, useState } from 'react';
import * as THREE from 'three';
import { useFrame } from '@react-three/fiber';
import { Html } from '@react-three/drei';

/**
 * BharatiSystemFlowOverlay — SYSTEM mode energy/utility flow for Bharati.
 *
 * Bharati-specific topology:
 *   FUEL FARM (south-west)  → GENERATOR PLANT → MICROGRID BUS
 *   SOLAR ARRAY (roof)      → SOLAR INVERTER  → MICROGRID BUS
 *   WIND TURBINE (research) → RESEARCH ROOF   → MICROGRID BUS
 *   BATTERY BANK            ↔ MICROGRID BUS
 *   MICROGRID BUS           → STATION LOAD
 *   MICROGRID BUS           → SEAWATER PUMP
 *   MICROGRID BUS           → COMMS SHELTER
 *   MICROGRID BUS           → RESEARCH LABS
 *
 * All node positions match the new Bharati zone layout:
 *   MAIN:      [0, 6.5, 0]
 *   ENERGY:    [-26, 5.5, -22]
 *   RESEARCH:  [34, 5.5, 6]
 *   STORAGE:   [24, 5.0, -18]
 *   GENERATOR: [-26, 4.5, -44]  (FUEL FARM)
 *   COMMS:     [6, 4.5, -46]
 *
 * Node badge positions are elevated above zone roofs for readability.
 */

// ─── Helpers (reused from SystemFlowOverlay pattern) ──────────────────────────

const parseKW = (v) => {
  if (typeof v === 'number') return v;
  if (!v) return 0;
  return parseFloat(v.toString().replace(/[^0-9.]/g, '')) || 0;
};

const makeCurvedRoute = (from, to, archElevation = 0.6) => {
  const dx = to[0] - from[0];
  const dz = to[2] - from[2];
  const dist = Math.hypot(dx, dz);
  const midY = Math.max(from[1], to[1]) + Math.min(1.8, Math.max(0.4, dist * 0.05)) + archElevation;
  const midPoint = new THREE.Vector3((from[0] + to[0]) / 2, midY, (from[2] + to[2]) / 2);
  return new THREE.QuadraticBezierCurve3(
    new THREE.Vector3(...from),
    midPoint,
    new THREE.Vector3(...to)
  );
};

// ─── ConduitSegment ───────────────────────────────────────────────────────────
const ConduitSegment = ({ circuit, isEmphasized = false, isDimmed = false, globalSpeed = 0.35 }) => {
  const { from, to, active, direction = 'forward', color, baseWidth = 0.12, arch = 0.4, pulses = 2, isCritical } = circuit;
  const curve = useMemo(() => makeCurvedRoute(from, to, arch), [from, to, arch]);
  const geometry = useMemo(() => new THREE.TubeGeometry(curve, 24, baseWidth, 6, false), [curve, baseWidth]);
  const pulseRefs = useMemo(() => Array.from({ length: pulses }).map(() => React.createRef()), [pulses]);

  useFrame((state) => {
    if (!active || direction === 'idle') return;
    const time = state.clock.elapsedTime;
    const speed = globalSpeed * (circuit.speedMultiplier || 1.0);
    pulseRefs.forEach((ref, idx) => {
      if (!ref.current) return;
      const offset = idx / pulses;
      let t = ((time * speed + offset) % 1.0);
      if (direction === 'reverse') t = 1.0 - t;
      t = Math.max(0.02, Math.min(0.98, t));
      const pt = curve.getPoint(t);
      const tangent = curve.getTangent(t);
      ref.current.position.copy(pt);
      if (direction === 'reverse') tangent.negate();
      ref.current.quaternion.setFromUnitVectors(new THREE.Vector3(0, 1, 0), tangent);
    });
  });

  const conduitOpacity = isEmphasized ? 0.95 : isDimmed ? 0.18 : active ? 0.72 : 0.12;
  const actualColor = isCritical ? '#b5382b' : color;

  return (
    <group name={`bhr-circuit-${circuit.id}`}>
      <mesh geometry={geometry} renderOrder={20} raycast={() => null}>
        <meshStandardMaterial
          color={active ? actualColor : '#64748b'}
          roughness={0.45}
          metalness={0.4}
          transparent
          opacity={conduitOpacity}
          depthWrite={false}
        />
      </mesh>
      {active && direction !== 'idle' && (
        <>
          {Array.from({ length: pulses }).map((_, idx) => (
            <mesh key={`bhr-pulse-${idx}`} ref={pulseRefs[idx]} renderOrder={22} raycast={() => null}>
              <coneGeometry args={[baseWidth * 1.55, baseWidth * 3.6, 6]} />
              <meshBasicMaterial
                color={actualColor}
                transparent
                opacity={isDimmed ? 0.35 : 0.95}
                depthWrite={false}
              />
            </mesh>
          ))}
        </>
      )}
    </group>
  );
};

// ─── UtilityJunctionBox ───────────────────────────────────────────────────────
const UtilityJunctionBox = ({ position, label, subLabel, status = 'NOMINAL', color = '#475569', onClick }) => {
  const [hovered, setHovered] = useState(false);
  const statusColor = status === 'CRITICAL' ? '#e53e3e' : status === 'WARNING' ? '#d97706' : status === 'OFFLINE' ? '#64748b' : '#38a169';

  return (
    <group position={position}>
      <mesh
        castShadow
        onClick={(e) => { e.stopPropagation(); if (onClick) onClick(); }}
        onPointerOver={(e) => { e.stopPropagation(); setHovered(true); document.body.style.cursor = 'pointer'; }}
        onPointerOut={(e) => { e.stopPropagation(); setHovered(false); document.body.style.cursor = 'default'; }}
      >
        <boxGeometry args={[1.2, 0.8, 0.9]} />
        <meshStandardMaterial color={hovered ? '#b65a1f' : color} metalness={0.65} roughness={0.35} />
      </mesh>
      <mesh position={[0, 0.45, 0]}>
        <cylinderGeometry args={[0.3, 0.3, 0.12, 8]} />
        <meshStandardMaterial color="#334155" metalness={0.8} />
      </mesh>
      <mesh position={[0, 0.55, 0]}>
        <sphereGeometry args={[0.12, 12, 8]} />
        <meshBasicMaterial color={statusColor} />
      </mesh>
      <Html position={[0, 1.1, 0]} center distanceFactor={34} zIndexRange={[60, 0]}>
        <div
          onClick={(e) => { e.stopPropagation(); if (onClick) onClick(); }}
          style={{
            background: 'rgba(24, 28, 36, 0.94)',
            border: `1px solid ${hovered ? '#b65a1f' : statusColor}`,
            borderRadius: '2px',
            padding: '2px 5px',
            fontFamily: 'JetBrains Mono, monospace',
            fontSize: '7.5px',
            fontWeight: 800,
            letterSpacing: '0.06em',
            color: '#ffffff',
            whiteSpace: 'nowrap',
            pointerEvents: 'auto',
            cursor: 'pointer',
            boxShadow: '0 2px 8px rgba(0,0,0,0.3)',
            display: 'flex',
            alignItems: 'center',
            gap: '4px',
            userSelect: 'none'
          }}
        >
          <span style={{ width: '4px', height: '4px', borderRadius: '50%', background: statusColor, flexShrink: 0 }} />
          <span>{label}</span>
          {subLabel && <span style={{ color: '#94a3b8', fontSize: '6.5px' }}>{subLabel}</span>}
        </div>
      </Html>
    </group>
  );
};

// ─── SystemNodeBadge ──────────────────────────────────────────────────────────
const SystemNodeBadge = ({ node, value, subMetric, status, isHighlighted = false, onClick }) => {
  const [isHovered, setIsHovered] = useState(false);

  const statusPalette = {
    NOMINAL:     { border: '#4f6f52', bg: 'rgba(79,111,82,0.12)',  dot: '#38a169', text: 'NOMINAL' },
    ACTIVE:      { border: '#b65a1f', bg: 'rgba(182,90,31,0.12)', dot: '#38a169', text: 'ACTIVE' },
    CHARGING:    { border: '#4f6f52', bg: 'rgba(79,111,82,0.14)',  dot: '#38a169', text: 'CHARGING' },
    DISCHARGING: { border: '#d97706', bg: 'rgba(217,119,6,0.14)',  dot: '#d97706', text: 'DISCHARGE' },
    CRITICAL:    { border: '#b5382b', bg: 'rgba(181,56,43,0.16)',  dot: '#e53e3e', text: 'CRITICAL' },
    OFFLINE:     { border: '#94a3b8', bg: 'rgba(148,163,184,0.14)',dot: '#64748b', text: 'OFFLINE' },
    STANDBY:     { border: '#94a3b8', bg: 'rgba(148,163,184,0.12)',dot: '#94a3b8', text: 'STANDBY' }
  };

  const styleMeta = statusPalette[status] || statusPalette.ACTIVE;
  const handleClick = (e) => { e.stopPropagation(); if (onClick) onClick(node); };

  return (
    <group position={node.pos}>
      <mesh position={[0, (node.roofPos[1] - node.pos[1]) / 2, 0]} raycast={() => null}>
        <cylinderGeometry args={[0.07, 0.07, node.pos[1] - node.roofPos[1], 8]} />
        <meshStandardMaterial color="#94a3b8" metalness={0.4} roughness={0.6} transparent opacity={0.6} />
      </mesh>
      <mesh position={[0, -0.25, 0]} raycast={() => null}>
        <cylinderGeometry args={[0.32, 0.42, 0.18, 12]} />
        <meshStandardMaterial color="#64748b" metalness={0.6} roughness={0.4} />
      </mesh>
      <mesh
        position={[0, 0.4, 0]}
        onClick={handleClick}
        onPointerOver={(e) => { e.stopPropagation(); setIsHovered(true); document.body.style.cursor = 'pointer'; }}
        onPointerOut={(e) => { e.stopPropagation(); setIsHovered(false); document.body.style.cursor = 'default'; }}
      >
        <boxGeometry args={[2.8, 1.8, 2.0]} />
        <meshBasicMaterial transparent opacity={0} depthWrite={false} />
      </mesh>
      <Html center distanceFactor={40} zIndexRange={[75, 0]}>
        <div
          onClick={handleClick}
          onMouseEnter={() => setIsHovered(true)}
          onMouseLeave={() => setIsHovered(false)}
          style={{
            background: 'rgba(255, 253, 248, 0.97)',
            border: `1.5px solid ${isHighlighted ? '#b65a1f' : isHovered ? '#b65a1f' : styleMeta.border}`,
            borderRadius: '4px',
            padding: '4px 9px',
            fontFamily: 'JetBrains Mono, monospace',
            fontSize: '9.5px',
            fontWeight: 700,
            letterSpacing: '0.05em',
            color: '#191c20',
            whiteSpace: 'nowrap',
            pointerEvents: 'auto',
            cursor: 'pointer',
            userSelect: 'none',
            boxShadow: isHighlighted || isHovered ? '0 4px 14px rgba(182,90,31,0.35)' : '0 2px 10px rgba(0,0,0,0.12)',
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            gap: '2px',
            minWidth: '64px',
            transition: 'all 0.15s ease',
            transform: isHovered ? 'scale(1.05)' : 'scale(1.0)'
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
            <span style={{ width: '5px', height: '5px', borderRadius: '50%', background: styleMeta.dot }} />
            <span style={{ fontSize: '7.5px', fontWeight: 800, color: styleMeta.border, letterSpacing: '0.08em' }}>
              {styleMeta.text}
            </span>
          </div>
          <div style={{ fontSize: '10px', fontWeight: 800, color: '#191c20' }}>{node.shortLabel}</div>
          {value && (
            <div style={{ fontSize: '9px', fontWeight: 700, color: '#475569', background: styleMeta.bg, padding: '1px 4px', borderRadius: '2px' }}>
              {value}
            </div>
          )}
          {subMetric && <div style={{ fontSize: '7.5px', color: '#64748b', fontWeight: 500 }}>{subMetric}</div>}
        </div>
      </Html>
    </group>
  );
};

// ─── Bharati Node Definitions ─────────────────────────────────────────────────
// Positions anchor to Bharati zone roofs + elevation above
const BHARATI_NODES = {
  SOLAR: {
    id: 'SOLAR', label: 'SOLAR ARRAY', shortLabel: 'SOLAR',
    pos:     [-14.0, 11.0, -22.0],
    roofPos: [-14.0,  5.5, -22.0],
    zone: 'ENERGY',
    defaultAsset: { id: 'ENERGY-INV-02', type: 'INVERTER', label: 'SOLAR INVERTER', zone: 'ENERGY' }
  },
  WIND: {
    id: 'WIND', label: 'WIND TURBINE', shortLabel: 'WIND',
    pos:     [42.0, 13.5,   2.0],
    roofPos: [42.0,  5.5,   2.0],
    zone: 'RESEARCH',
    defaultAsset: { id: 'RESEARCH-RES-01', type: 'RESEARCH', label: 'MET ARRAY', zone: 'RESEARCH' }
  },
  FUEL_FARM: {
    id: 'FUEL_FARM', label: 'FUEL FARM', shortLabel: 'FUEL FARM',
    pos:     [-26.0, 11.0, -44.0],
    roofPos: [-26.0,  4.5, -44.0],
    zone: 'GENERATOR',
    defaultAsset: { id: 'GENERATOR-FUEL-01', type: 'FUEL_TANK', label: 'DAY TANK', zone: 'GENERATOR' }
  },
  DIESEL: {
    id: 'DIESEL', label: 'CHP GENERATOR', shortLabel: 'CHP GEN',
    pos:     [-20.0, 10.2, -38.0],
    roofPos: [-20.0,  4.5, -38.0],
    zone: 'GENERATOR',
    defaultAsset: { id: 'GENERATOR-GEN-01', type: 'GENERATOR', label: 'DIESEL GEN #1', zone: 'GENERATOR' }
  },
  MICROGRID: {
    id: 'MICROGRID', label: 'MICROGRID BUS', shortLabel: 'MICROGRID',
    pos:     [-26.0, 12.0, -22.0],
    roofPos: [-26.0,  5.5, -22.0],
    zone: 'ENERGY',
    defaultAsset: { id: 'ENERGY-INV-01', type: 'INVERTER', label: 'MICROGRID INVERTER', zone: 'ENERGY' }
  },
  BATTERY: {
    id: 'BATTERY', label: 'BATTERY BANK', shortLabel: 'BATTERY',
    pos:     [-32.0, 10.8, -22.0],
    roofPos: [-32.0,  5.5, -22.0],
    zone: 'ENERGY',
    defaultAsset: { id: 'ENERGY-BATT-01', type: 'BATTERY', label: 'BATTERY BANK', zone: 'ENERGY' }
  },
  STATION: {
    id: 'STATION', label: 'STATION LOAD', shortLabel: 'STATION LOAD',
    pos:     [ 0.0, 13.0,   0.0],
    roofPos: [ 0.0,  6.5,   0.0],
    zone: 'MAIN',
    defaultAsset: { id: 'MAIN-PANEL-01', type: 'CONTROL', label: 'COMMAND CONSOLE', zone: 'MAIN' }
  },
  SEA_WATER: {
    id: 'SEA_WATER', label: 'SEAWATER PUMP', shortLabel: 'SEA PUMP',
    pos:     [-22.0, 9.2, 18.0],
    roofPos: [-22.0, 3.8, 18.0],
    zone: 'MAIN',
    defaultAsset: { id: 'MAIN-HVAC-02', type: 'HVAC', label: 'LIFE SUPPORT', zone: 'MAIN' }
  }
};

// ─── BharatiSystemFlowOverlay ─────────────────────────────────────────────────
export const BharatiSystemFlowOverlay = ({
  telemetry = {},
  station,
  selectedAssetId = null,
  selectedSensor = null,
  onSelectAsset,
  incidentGraph = null,
}) => {
  const power   = telemetry?.power   || {};
  const battery = telemetry?.battery || {};

  const solarKW   = parseKW(power.solarGeneration);
  const windKW    = parseKW(power.windGeneration);
  const dieselKW  = parseKW(power.dieselGeneration);
  const currentKW = parseKW(power.currentPower) || (solarKW + windKW + dieselKW) || 92.6;
  const loadPct   = power.loadPercentage || 54;

  const battPercent   = battery.percentage ?? 89;
  const battState     = (battery.state || 'FLOAT').toUpperCase();
  const isDischarging = battState.includes('DISCHARG') || battPercent < 45;
  const isCharging    = !isDischarging && (battState.includes('CHARG') || battState.includes('FLOAT'));
  const isCriticalBatt = isDischarging && (battPercent < 50 || battState.includes('CRITICAL'));

  const solarActive  = solarKW > 0.5;
  const windActive   = windKW > 0.5;
  const dieselActive = dieselKW > 0.5;

  // ─── Node focus from selected asset/sensor ────────────────────────────────
  const focusedNodeId = useMemo(() => {
    if (selectedAssetId) {
      if (selectedAssetId.includes('BATT'))   return 'BATTERY';
      if (selectedAssetId.includes('GEN') || selectedAssetId.includes('FUEL')) return 'DIESEL';
      if (selectedAssetId.includes('INV-02') || selectedAssetId.includes('SOLAR')) return 'SOLAR';
      if (selectedAssetId.includes('INV-01') || selectedAssetId.includes('TRANS')) return 'MICROGRID';
      if (selectedAssetId.includes('MAIN') || selectedAssetId.includes('PANEL') || selectedAssetId.includes('HVAC')) return 'STATION';
      if (selectedAssetId.includes('RES')) return 'WIND';
    }
    if (selectedSensor) {
      const sname = (selectedSensor.name || '').toUpperCase();
      if (sname.includes('GEN') || sname.includes('CHP') || sname.includes('FUEL FARM')) return 'FUEL_FARM';
      if (sname.includes('DG-') || sname.includes('CHP GEN')) return 'DIESEL';
      if (sname.includes('BATTERY') || sname.includes('BATT')) return 'BATTERY';
      if (sname.includes('SOLAR') || sname.includes('PYRANOMETER')) return 'SOLAR';
      if (sname.includes('WIND') || sname.includes('TURBINE')) return 'WIND';
      if (sname.includes('MICROGRID')) return 'MICROGRID';
      if (sname.includes('SEAWATER') || sname.includes('PUMP')) return 'SEA_WATER';
      if (selectedSensor.zone === 'MAIN') return 'STATION';
    }
    return null;
  }, [selectedAssetId, selectedSensor]);

  // ─── Circuit topology ─────────────────────────────────────────────────────
  const circuits = useMemo(() => {
    const list = [];

    // ======================================================================
    // A. FUEL FARM → CHP GENERATOR PLANT (south-west)
    // ======================================================================
    list.push({
      id: 'bhr-fuel-chp',
      category: 'fuel',
      from: [-20.0, 3.2, -52.0],
      to: [-26.0, 3.6, -44.0],
      active: dieselActive,
      direction: 'forward',
      color: '#d97706',
      baseWidth: 0.10,
      pulses: 1,
      arch: 0.2
    });

    // ======================================================================
    // B. CHP GENERATOR → ENERGY SUBSTATION
    // ======================================================================
    list.push({
      id: 'bhr-chp-substation-1',
      category: 'generation',
      from: [-26.0, 3.6, -44.0],
      to: [-26.0, 5.0, -32.0],
      active: dieselActive,
      direction: 'forward',
      color: dieselActive ? '#b65a1f' : '#64748b',
      baseWidth: 0.15,
      pulses: 2,
      arch: 0.3
    });

    list.push({
      id: 'bhr-chp-substation-2',
      category: 'generation',
      from: [-26.0, 5.0, -32.0],
      to: [-26.0, 6.0, -22.0],
      active: dieselActive,
      direction: 'forward',
      color: dieselActive ? '#b65a1f' : '#64748b',
      baseWidth: 0.15,
      pulses: 2,
      arch: 0.25
    });

    // ======================================================================
    // C. SOLAR ARRAY (ENERGY zone roof) → MICROGRID BUS
    // ======================================================================
    list.push({
      id: 'bhr-solar-inv',
      category: 'solar',
      from: [-14.0, 10.2, -28.0],
      to: [-22.0, 6.5, -22.0],
      active: solarActive,
      direction: 'forward',
      color: '#d97706',
      baseWidth: 0.12,
      pulses: 2,
      arch: 0.35
    });

    list.push({
      id: 'bhr-solar-bus',
      category: 'solar',
      from: [-22.0, 6.5, -22.0],
      to: [-26.0, 6.5, -22.0],
      active: solarActive,
      direction: 'forward',
      color: '#d97706',
      baseWidth: 0.13,
      pulses: 2,
      arch: 0.15
    });

    // ======================================================================
    // D. WIND TURBINE (RESEARCH roof) → MICROGRID BUS
    // ======================================================================
    list.push({
      id: 'bhr-wind-res',
      category: 'wind',
      from: [46.0, 12.5, 2.0],
      to: [34.0, 6.0, 4.0],
      active: windActive,
      direction: 'forward',
      color: '#4f6f52',
      baseWidth: 0.12,
      pulses: 2,
      arch: 0.5,
      speedMultiplier: windKW > 40 ? 1.8 : 1.0
    });

    list.push({
      id: 'bhr-wind-res-main',
      category: 'wind',
      from: [34.0, 6.0, 4.0],
      to: [0.0, 7.0, 0.0],
      active: windActive,
      direction: 'forward',
      color: '#4f6f52',
      baseWidth: 0.13,
      pulses: 2,
      arch: 0.3
    });

    list.push({
      id: 'bhr-wind-main-energy',
      category: 'wind',
      from: [0.0, 7.0, 0.0],
      to: [-26.0, 6.5, -22.0],
      active: windActive,
      direction: 'forward',
      color: '#4f6f52',
      baseWidth: 0.13,
      pulses: 2,
      arch: 0.35
    });

    // ======================================================================
    // E. BATTERY BANK ↔ MICROGRID BUS
    // ======================================================================
    list.push({
      id: 'bhr-batt-a',
      category: 'battery',
      from: [-34.0, 4.5, -24.0],
      to: [-29.0, 5.5, -22.0],
      active: true,
      direction: isDischarging ? 'forward' : isCharging ? 'reverse' : 'idle',
      color: isCriticalBatt ? '#b5382b' : isDischarging ? '#d97706' : '#4f6f52',
      baseWidth: 0.13,
      pulses: 2,
      arch: 0.2,
      isCritical: isCriticalBatt
    });

    list.push({
      id: 'bhr-batt-b',
      category: 'battery',
      from: [-34.0, 4.5, -20.0],
      to: [-29.0, 5.5, -22.0],
      active: true,
      direction: isDischarging ? 'forward' : isCharging ? 'reverse' : 'idle',
      color: isCriticalBatt ? '#b5382b' : isDischarging ? '#d97706' : '#4f6f52',
      baseWidth: 0.13,
      pulses: 2,
      arch: 0.2,
      isCritical: isCriticalBatt
    });

    // ======================================================================
    // F. MICROGRID BUS → STATION LOADS
    // ======================================================================
    const gridEnergized = (solarActive || windActive || dieselActive || isDischarging);

    // MICROGRID → MAIN BUILDING (spine feeder)
    list.push({
      id: 'bhr-bus-main',
      category: 'load',
      from: [-26.0, 6.5, -22.0],
      to: [0.0, 7.0, 0.0],
      active: gridEnergized,
      direction: 'forward',
      color: isCriticalBatt ? '#d97706' : '#b65a1f',
      baseWidth: 0.18,
      pulses: 3,
      arch: 0.3
    });

    // MAIN BUILDING branch feeders
    list.push({
      id: 'bhr-main-command',
      category: 'load',
      from: [0.0, 7.0, 0.0],
      to: [0.0, 3.2, 0.0],
      active: gridEnergized,
      direction: 'forward',
      color: '#b65a1f',
      baseWidth: 0.12,
      pulses: 1,
      arch: 0.15
    });

    list.push({
      id: 'bhr-main-lifesupport',
      category: 'load',
      from: [0.0, 7.0, 0.0],
      to: [8.0, 3.2, 5.0],
      active: gridEnergized,
      direction: 'forward',
      color: '#38a169',
      baseWidth: 0.13,
      pulses: 2,
      arch: 0.25
    });

    // MICROGRID → STORAGE (container logistics)
    list.push({
      id: 'bhr-bus-storage',
      category: 'load',
      from: [-26.0, 6.5, -22.0],
      to: [24.0, 5.5, -18.0],
      active: gridEnergized,
      direction: 'forward',
      color: '#b65a1f',
      baseWidth: 0.13,
      pulses: 2,
      arch: 0.3
    });

    // MICROGRID → RESEARCH labs
    list.push({
      id: 'bhr-bus-research',
      category: 'load',
      from: [0.0, 7.0, 0.0],
      to: [34.0, 6.0, 5.0],
      active: gridEnergized && !isCriticalBatt,
      direction: 'forward',
      color: '#4f6f52',
      baseWidth: 0.12,
      pulses: 2,
      arch: 0.28
    });

    // MICROGRID → COMMS shelter
    list.push({
      id: 'bhr-bus-comms',
      category: 'load',
      from: [-26.0, 6.5, -22.0],
      to: [6.0, 5.0, -46.0],
      active: gridEnergized,
      direction: 'forward',
      color: '#38a169',
      baseWidth: 0.13,
      pulses: 2,
      arch: 0.28
    });

    // MICROGRID → SEA WATER PUMP (coastal life support)
    list.push({
      id: 'bhr-bus-seawater',
      category: 'load',
      from: [-26.0, 6.5, -22.0],
      to: [-22.0, 4.5, 10.0],
      active: gridEnergized,
      direction: 'forward',
      color: '#2d8a8a',
      baseWidth: 0.11,
      pulses: 1,
      arch: 0.3
    });

    return list;
  }, [dieselActive, solarActive, windActive, windKW, isCharging, isDischarging, isCriticalBatt]);

  // ─── Handle node badge click ──────────────────────────────────────────────
  const handleNodeClick = (node) => {
    if (onSelectAsset && node.defaultAsset) {
      onSelectAsset(node.defaultAsset);
    }
  };

  // ─── Circuit emphasis ─────────────────────────────────────────────────────
  const incidentNodeIds = useMemo(() => {
    if (!incidentGraph?.isActive) return new Set();
    const s = new Set();
    (incidentGraph.nodes || []).forEach(n => s.add(n.id));
    return s;
  }, [incidentGraph]);

  const incidentCategories = useMemo(() => {
    const cats = new Set();
    if (!incidentGraph?.isActive) return cats;
    if (incidentNodeIds.has('SOLAR'))     cats.add('solar');
    if (incidentNodeIds.has('WIND'))      cats.add('wind');
    if (incidentNodeIds.has('DIESEL') || incidentNodeIds.has('FUEL_FARM')) cats.add('generation');
    if (incidentNodeIds.has('BATTERY'))   cats.add('battery');
    if (incidentNodeIds.has('MICROGRID') || incidentNodeIds.has('STATION')) cats.add('load');
    return cats;
  }, [incidentGraph, incidentNodeIds]);

  return (
    <group name="bharati-system-flow-overlay">
      {/* 1. Conduit circuits */}
      {circuits.map((circuit) => {
        const assetBased = focusedNodeId ? (
          (focusedNodeId === 'BATTERY'   && circuit.category === 'battery') ||
          (focusedNodeId === 'DIESEL'    && circuit.category === 'generation') ||
          (focusedNodeId === 'FUEL_FARM' && circuit.category === 'fuel') ||
          (focusedNodeId === 'SOLAR'     && circuit.category === 'solar') ||
          (focusedNodeId === 'WIND'      && circuit.category === 'wind') ||
          (focusedNodeId === 'STATION'   && circuit.category === 'load') ||
          (focusedNodeId === 'SEA_WATER' && circuit.category === 'load') ||
          (focusedNodeId === 'MICROGRID' && (circuit.category === 'load' || circuit.id.includes('bus')))
        ) : false;

        const incidentBased = incidentGraph?.isActive && incidentCategories.has(circuit.category);
        const isEmphasized = assetBased || incidentBased;
        const isDimmed = (focusedNodeId ? !assetBased : false) ||
                         (incidentGraph?.isActive && incidentCategories.size > 0 && !incidentBased && !focusedNodeId);

        return (
          <ConduitSegment
            key={circuit.id}
            circuit={circuit}
            isEmphasized={isEmphasized}
            isDimmed={isDimmed}
          />
        );
      })}

      {/* 2. Junction tap boxes */}
      <UtilityJunctionBox
        position={[-26.0, 5.0, -44.0]}
        label="FUEL FARM TAP"
        subLabel="HSD MANIFOLD"
        status={dieselActive ? 'ACTIVE' : 'OFFLINE'}
        color="#334155"
        onClick={() => onSelectAsset && onSelectAsset(BHARATI_NODES.FUEL_FARM.defaultAsset)}
      />
      <UtilityJunctionBox
        position={[-26.0, 7.2, -22.0]}
        label="SUBSTATION BUS"
        subLabel="415V • 50Hz"
        status={isCriticalBatt ? 'CRITICAL' : 'NOMINAL'}
        color="#1e293b"
        onClick={() => onSelectAsset && onSelectAsset(BHARATI_NODES.MICROGRID.defaultAsset)}
      />
      <UtilityJunctionBox
        position={[0.0, 7.8, 0.0]}
        label="HAB DISTRIBUTION"
        subLabel="230V AC"
        status="NOMINAL"
        color="#334155"
        onClick={() => onSelectAsset && onSelectAsset(BHARATI_NODES.STATION.defaultAsset)}
      />
      <UtilityJunctionBox
        position={[34.0, 6.5, 4.0]}
        label="SCIENCE SUBPANEL"
        subLabel="LAB BUS"
        status={windActive ? 'ACTIVE' : 'NOMINAL'}
        color="#334155"
        onClick={() => onSelectAsset && onSelectAsset(BHARATI_NODES.WIND.defaultAsset)}
      />
      <UtilityJunctionBox
        position={[6.0, 5.5, -46.0]}
        label="COMMS RF TAP"
        subLabel="UPS BUS"
        status="NOMINAL"
        color="#334155"
        onClick={() => onSelectAsset && onSelectAsset({ id: 'COMMS-COMM-01', type: 'COMMS', label: 'RF SHELTER', zone: 'COMMS' })}
      />
      <UtilityJunctionBox
        position={[-22.0, 4.8, 10.0]}
        label="SEA PUMP TAP"
        subLabel="480V"
        status="NOMINAL"
        color="#1e4d4d"
        onClick={() => onSelectAsset && onSelectAsset(BHARATI_NODES.SEA_WATER.defaultAsset)}
      />

      {/* 3. System node badges */}
      <SystemNodeBadge
        node={BHARATI_NODES.SOLAR}
        value={solarActive ? `${solarKW.toFixed(1)} kW` : '0.0 kW'}
        subMetric={solarActive ? 'ROOF ARRAY ACTIVE' : 'STOWED / NIGHT'}
        status={solarActive ? 'ACTIVE' : 'OFFLINE'}
        isHighlighted={focusedNodeId === 'SOLAR'}
        onClick={handleNodeClick}
      />
      <SystemNodeBadge
        node={BHARATI_NODES.WIND}
        value={windActive ? `${windKW.toFixed(1)} kW` : '0.0 kW'}
        subMetric={windActive ? 'EAST RIDGE MAST' : 'CALM / PITCHED'}
        status={windActive ? 'NOMINAL' : 'OFFLINE'}
        isHighlighted={focusedNodeId === 'WIND'}
        onClick={handleNodeClick}
      />
      <SystemNodeBadge
        node={BHARATI_NODES.FUEL_FARM}
        value={`HSD FARM`}
        subMetric="TANK MANIFOLD"
        status={dieselActive ? 'ACTIVE' : 'STANDBY'}
        isHighlighted={focusedNodeId === 'FUEL_FARM'}
        onClick={handleNodeClick}
      />
      <SystemNodeBadge
        node={BHARATI_NODES.DIESEL}
        value={dieselActive ? `${dieselKW.toFixed(1)} kW` : '0.0 kW'}
        subMetric={dieselActive ? 'CHP ONLINE' : 'STANDBY'}
        status={dieselActive ? 'ACTIVE' : 'STANDBY'}
        isHighlighted={focusedNodeId === 'DIESEL'}
        onClick={handleNodeClick}
      />
      <SystemNodeBadge
        node={BHARATI_NODES.MICROGRID}
        value={`${currentKW.toFixed(1)} kW`}
        subMetric="415V • 50 Hz SYNCH"
        status={isCriticalBatt ? 'CRITICAL' : 'NOMINAL'}
        isHighlighted={focusedNodeId === 'MICROGRID'}
        onClick={handleNodeClick}
      />
      <SystemNodeBadge
        node={BHARATI_NODES.BATTERY}
        value={`${battPercent}%`}
        subMetric={isDischarging ? 'DISCHARGING' : isCharging ? 'CHARGING' : 'FLOAT'}
        status={isCriticalBatt ? 'CRITICAL' : isDischarging ? 'DISCHARGING' : 'CHARGING'}
        isHighlighted={focusedNodeId === 'BATTERY'}
        onClick={handleNodeClick}
      />
      <SystemNodeBadge
        node={BHARATI_NODES.STATION}
        value={`${currentKW.toFixed(1)} kW`}
        subMetric={`${loadPct}% DEMAND`}
        status={isCriticalBatt ? 'CRITICAL' : 'ACTIVE'}
        isHighlighted={focusedNodeId === 'STATION'}
        onClick={handleNodeClick}
      />
      <SystemNodeBadge
        node={BHARATI_NODES.SEA_WATER}
        value="COASTAL"
        subMetric="SEAWATER SUPPLY"
        status="NOMINAL"
        isHighlighted={focusedNodeId === 'SEA_WATER'}
        onClick={handleNodeClick}
      />
    </group>
  );
};

export default BharatiSystemFlowOverlay;
