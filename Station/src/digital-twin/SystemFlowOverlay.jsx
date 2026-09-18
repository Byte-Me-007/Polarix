import React, { useRef, useMemo } from 'react';
import * as THREE from 'three';
import { useFrame } from '@react-three/fiber';
import { Html } from '@react-three/drei';

/**
 * SystemFlowOverlay — SYSTEM mode energy flow visualization
 *
 * Draws thin copper tube lines between energy infrastructure nodes.
 * Direction of each flow respects telemetry state.
 * No neon; no glowing beams. Warm neutral + copper palette.
 *
 * Station world-space positions match StationModel zone layout:
 *   GENERATOR:  [-30, 2.8, -30]  → visualised near [-30, 8, -30]
 *   ENERGY:     [0,   3.0, -30]  → visualised near [0,  8, -30]
 *   RESEARCH:   [38,  3.2, 0]    → wind turbine on roof → [48, 15, -10]
 *   MAIN:       [0,   3.5, 0]    → station load centre
 *   COMMS:      [0,   2.6, -54]  → satellite
 */

// Utility: create a tapered tube between two points
const makeTubePath = (from, to) => {
  const curve = new THREE.LineCurve3(
    new THREE.Vector3(...from),
    new THREE.Vector3(...to)
  );
  return curve;
};

// Animated flow line component
const FlowLine = ({ from, to, color = '#b65a1f', active = true, direction = 1, width = 0.12, opacity = 0.72 }) => {
  const meshRef = useRef();
  const dashRef = useRef(0);

  const curve = useMemo(() => makeTubePath(from, to), [from, to]);
  const geometry = useMemo(() => new THREE.TubeGeometry(curve, 12, width, 6, false), [curve, width]);

  useFrame((_, delta) => {
    if (!meshRef.current || !active) return;
    // Animate dash offset to suggest flow direction
    dashRef.current += delta * direction * 1.2;
    if (meshRef.current.material) {
      meshRef.current.material.dashOffset = -dashRef.current;
    }
  });

  if (!active) return null;

  return (
    <mesh ref={meshRef} geometry={geometry} renderOrder={20}>
      <meshBasicMaterial
        color={color}
        transparent
        opacity={opacity}
        depthWrite={false}
      />
    </mesh>
  );
};

// Arrow marker at midpoint of a flow line
const FlowArrow = ({ from, to, color = '#b65a1f', active = true }) => {
  const mid = useMemo(() => [
    (from[0] + to[0]) / 2,
    (from[1] + to[1]) / 2 + 0.3,
    (from[2] + to[2]) / 2
  ], [from, to]);

  const dir = useMemo(() => {
    const v = new THREE.Vector3(to[0] - from[0], to[1] - from[1], to[2] - from[2]).normalize();
    return v;
  }, [from, to]);

  const quaternion = useMemo(() => {
    const q = new THREE.Quaternion();
    q.setFromUnitVectors(new THREE.Vector3(0, 1, 0), dir);
    return q;
  }, [dir]);

  if (!active) return null;

  return (
    <mesh position={mid} quaternion={quaternion} renderOrder={21}>
      <coneGeometry args={[0.28, 0.75, 6]} />
      <meshBasicMaterial color={color} transparent opacity={0.85} depthWrite={false} />
    </mesh>
  );
};

// Node label bubble
const FlowNode = ({ position, label, status = 'ACTIVE', value = null }) => {
  const statusColor = {
    ACTIVE: '#4f6f52',
    WARNING: '#b26814',
    OFFLINE: '#5d6672',
    CRITICAL: '#b5382b',
    CHARGING: '#4f6f52',
    DISCHARGING: '#b26814'
  }[status] || '#4f6f52';

  const statusText = {
    ACTIVE: 'ON',
    WARNING: 'WARN',
    OFFLINE: 'OFF',
    CRITICAL: 'CRIT',
    CHARGING: '↑ CHG',
    DISCHARGING: '↓ DSC'
  }[status] || status;

  return (
    <Html position={position} center distanceFactor={38} zIndexRange={[50, 0]}>
      <div style={{
        background: 'rgba(255,253,248,0.96)',
        border: `1.5px solid ${statusColor}`,
        borderRadius: '3px',
        padding: '4px 8px',
        fontFamily: 'JetBrains Mono, monospace',
        fontSize: '10px',
        fontWeight: 700,
        letterSpacing: '0.06em',
        color: '#191c20',
        whiteSpace: 'nowrap',
        pointerEvents: 'none',
        boxShadow: '0 2px 8px rgba(0,0,0,0.10)',
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        gap: '1px',
        minWidth: '56px',
        textAlign: 'center'
      }}>
        <span style={{ color: statusColor, fontSize: '8px', letterSpacing: '0.1em' }}>{statusText}</span>
        <span>{label}</span>
        {value && <span style={{ color: '#727b87', fontSize: '9px', fontWeight: 400 }}>{value}</span>}
      </div>
    </Html>
  );
};

/**
 * SYSTEM MODE ENERGY FLOW DIAGRAM
 *
 * Nodes (world-space, elevated ~8-12 units above buildings for visibility):
 *   SOLAR    → near ENERGY zone roof   [5,  9.5, -30]
 *   WIND     → near RESEARCH roof     [48, 12,  -10]
 *   DIESEL   → GENERATOR zone         [-30, 9,  -30]
 *   MICROGRID→ ENERGY zone centre     [0,  9,   -30]
 *   BATTERY  → ENERGY zone            [-7, 9,   -26]
 *   STATION  → MAIN zone              [0,  9.5,   0]
 */

const NODES = {
  SOLAR:     [5,   9.5, -30],
  WIND:      [48,  12,  -10],
  DIESEL:    [-30, 9,   -30],
  MICROGRID: [0,   9,   -30],
  BATTERY:   [-7,  9,   -26],
  STATION:   [0,   9.5,   0]
};

export const SystemFlowOverlay = ({ telemetry }) => {
  const power     = telemetry?.power     || {};
  const battery   = telemetry?.battery   || {};
  const satellite = telemetry?.satellite || {};

  // Parse generation values (string like "42.8 kW" → number)
  const parseKW = (v) => {
    if (typeof v === 'number') return v;
    if (!v) return 0;
    return parseFloat(v.toString().replace(/[^0-9.]/g, '')) || 0;
  };

  const solarKW   = parseKW(power.solarGeneration);
  const windKW    = parseKW(power.windGeneration);
  const dieselKW  = parseKW(power.dieselGeneration);

  const solarActive   = solarKW > 0.5;
  const windActive    = windKW > 0.5;
  const dieselActive  = dieselKW > 0.5;

  const battState = (battery.state || 'CHARGING').toUpperCase();
  const isDischarging = battState.includes('DISCHARGING') || battState.includes('DISCHARGE');
  const isCharging    = battState.includes('CHARGING') || battState.includes('FLOAT');
  const battPercent   = battery.percentage ?? 78;

  const solarStatus   = solarActive ? 'ACTIVE' : 'OFFLINE';
  const windStatus    = windActive  ? 'ACTIVE' : 'OFFLINE';
  const dieselStatus  = dieselActive ? 'WARNING' : 'OFFLINE';

  const solarVal  = solarActive  ? `${solarKW.toFixed(1)} kW`  : 'OFFLINE';
  const windVal   = windActive   ? `${windKW.toFixed(1)} kW`   : 'OFFLINE';
  const dieselVal = dieselActive ? `${dieselKW.toFixed(1)} kW` : 'OFFLINE';
  const battVal   = `${battPercent}% ${isDischarging ? '↓' : isCharging ? '↑' : '—'}`;

  return (
    <group name="system-flow-overlay">
      {/* ---- Generation → Microgrid flows ---- */}
      {solarActive && (
        <>
          <FlowLine from={NODES.SOLAR} to={NODES.MICROGRID} color="#b26814" active width={0.14} opacity={0.65} />
          <FlowArrow from={NODES.SOLAR} to={NODES.MICROGRID} color="#b26814" active />
        </>
      )}

      {windActive && (
        <>
          <FlowLine from={NODES.WIND} to={NODES.MICROGRID} color="#4f6f52" active width={0.14} opacity={0.65} />
          <FlowArrow from={NODES.WIND} to={NODES.MICROGRID} color="#4f6f52" active />
        </>
      )}

      {dieselActive && (
        <>
          <FlowLine from={NODES.DIESEL} to={NODES.MICROGRID} color="#b5382b" active width={0.16} opacity={0.7} />
          <FlowArrow from={NODES.DIESEL} to={NODES.MICROGRID} color="#b5382b" active />
        </>
      )}

      {/* ---- Microgrid → Station Load (always if any generation active) ---- */}
      {(solarActive || windActive || dieselActive) && (
        <>
          <FlowLine from={NODES.MICROGRID} to={NODES.STATION} color="#b65a1f" active width={0.18} opacity={0.70} />
          <FlowArrow from={NODES.MICROGRID} to={NODES.STATION} color="#b65a1f" active />
        </>
      )}

      {/* ---- Battery flow (bidirectional, but only one direction shown) ---- */}
      {isCharging && !isDischarging && (
        <>
          <FlowLine from={NODES.MICROGRID} to={NODES.BATTERY} color="#4f6f52" active width={0.13} opacity={0.6} />
          <FlowArrow from={NODES.MICROGRID} to={NODES.BATTERY} color="#4f6f52" active />
        </>
      )}
      {isDischarging && (
        <>
          <FlowLine from={NODES.BATTERY} to={NODES.STATION} color="#b26814" active width={0.15} opacity={0.65} />
          <FlowArrow from={NODES.BATTERY} to={NODES.STATION} color="#b26814" active />
        </>
      )}

      {/* ---- Idle battery (no flow) but still show node ---- */}
      {!isCharging && !isDischarging && (
        <FlowLine from={NODES.MICROGRID} to={NODES.BATTERY} color="#9aa2ac" active={false} width={0.10} opacity={0.25} />
      )}

      {/* ---- Node Labels ---- */}
      <FlowNode position={NODES.SOLAR}     label="SOLAR"     status={solarStatus}  value={solarVal} />
      <FlowNode position={NODES.WIND}      label="WIND"      status={windStatus}   value={windVal} />
      <FlowNode position={NODES.DIESEL}    label="DIESEL"    status={dieselStatus} value={dieselVal} />
      <FlowNode position={NODES.MICROGRID} label="MICROGRID" status="ACTIVE"       value={null} />
      <FlowNode position={NODES.BATTERY}   label="BATTERY"   status={isDischarging ? 'DISCHARGING' : isCharging ? 'CHARGING' : 'ACTIVE'} value={battVal} />
      <FlowNode position={NODES.STATION}   label="STATION"   status="ACTIVE"       value="LOAD" />
    </group>
  );
};

export default SystemFlowOverlay;
