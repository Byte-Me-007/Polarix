import React, { useRef, useMemo, useState } from 'react';
import * as THREE from 'three';
import { useFrame } from '@react-three/fiber';
import { Html } from '@react-three/drei';

/**
 * SystemFlowOverlay — Live Spatial Infrastructure Flow Overlay for SYSTEM Mode
 *
 * Implements POLARIS Antarctic Research Station System Mode:
 * - Anchors major energy infrastructure as physical spatial nodes on station buildings
 * - Visualizes live electrical connections and energy flow directions
 * - Direction-aware battery charging (MICROGRID -> BATTERY) vs discharging (BATTERY -> MICROGRID / LOAD)
 * - Directly reflects live application telemetry (solar, wind, diesel, battery, load)
 * - Responsive to POWER CRISIS, STORM, and NORMAL operational scenarios
 * - Interactive: Clicking any node highlights/focuses the corresponding operational machinery
 * - Seamlessly integrates with sensor-to-asset hierarchy and station switching (Maitri & Bharati)
 */

// Helper to extract numerical kW values safely
const parseKW = (v) => {
  if (typeof v === 'number') return v;
  if (!v) return 0;
  return parseFloat(v.toString().replace(/[^0-9.]/g, '')) || 0;
};

// Physical 3D spatial node definitions anchored to building facilities
const NODE_DEFINITIONS = {
  SOLAR: {
    id: 'SOLAR',
    label: 'SOLAR ARRAY',
    shortLabel: 'SOLAR',
    pos: [10.0, 11.5, -28.0],
    roofPos: [10.0, 6.5, -28.0],
    zone: 'ENERGY',
    defaultAsset: { id: 'ENERGY-INV-02', type: 'INVERTER', label: 'SOLAR INVERTER', zone: 'ENERGY' },
    icon: '☀'
  },
  WIND: {
    id: 'WIND',
    label: 'WIND TURBINE',
    shortLabel: 'WIND',
    pos: [44.0, 14.0, -10.0],
    roofPos: [44.0, 6.5, -10.0],
    zone: 'RESEARCH',
    defaultAsset: { id: 'RESEARCH-RES-01', type: 'RESEARCH', label: 'MET ARRAY', zone: 'RESEARCH' },
    icon: '⚡'
  },
  DIESEL: {
    id: 'DIESEL',
    label: 'DIESEL PLANT',
    shortLabel: 'DIESEL',
    pos: [-30.0, 11.5, -30.0],
    roofPos: [-30.0, 5.5, -30.0],
    zone: 'GENERATOR',
    defaultAsset: { id: 'GENERATOR-GEN-02', type: 'GENERATOR', label: 'DIESEL GEN #2', zone: 'GENERATOR' },
    icon: '⚙'
  },
  MICROGRID: {
    id: 'MICROGRID',
    label: 'MICROGRID BUS',
    shortLabel: 'MICROGRID',
    pos: [0.0, 12.0, -28.0],
    roofPos: [0.0, 6.5, -28.0],
    zone: 'ENERGY',
    defaultAsset: { id: 'ENERGY-INV-01', type: 'INVERTER', label: 'MICROGRID INVERTER', zone: 'ENERGY' },
    icon: '⎇'
  },
  BATTERY: {
    id: 'BATTERY',
    label: 'BATTERY BANK',
    shortLabel: 'BATTERY',
    pos: [-7.5, 11.0, -26.0],
    roofPos: [-7.5, 6.5, -26.0],
    zone: 'ENERGY',
    defaultAsset: { id: 'ENERGY-BATT-01', type: 'BATTERY', label: 'BATTERY BANK', zone: 'ENERGY' },
    icon: '🔋'
  },
  STATION: {
    id: 'STATION',
    label: 'STATION LOAD',
    shortLabel: 'STATION LOAD',
    pos: [0.0, 13.5, 0.0],
    roofPos: [0.0, 7.0, 0.0],
    zone: 'MAIN',
    defaultAsset: { id: 'MAIN-PANEL-01', type: 'CONTROL', label: 'COMMAND CONSOLE', zone: 'MAIN' },
    icon: '⌂'
  }
};

// Create a smooth overhead conduit arch between two 3D spatial points
const makeCurvedRoute = (from, to) => {
  const dx = to[0] - from[0];
  const dz = to[2] - from[2];
  const dist = Math.hypot(dx, dz);
  const archHeight = Math.min(2.5, Math.max(0.9, dist * 0.075));
  const midY = Math.max(from[1], to[1]) + archHeight;
  const midPoint = new THREE.Vector3((from[0] + to[0]) / 2, midY, (from[2] + to[2]) / 2);

  return new THREE.QuadraticBezierCurve3(
    new THREE.Vector3(...from),
    midPoint,
    new THREE.Vector3(...to)
  );
};

// Single flow line with animated directional energy pulses along the curve
const FlowConduit = ({
  connection,
  isEmphasized = false,
  isDimmed = false
}) => {
  const { from, to, active, direction, color, baseWidth, isCritical } = connection;
  const curve = useMemo(() => makeCurvedRoute(from, to), [from, to]);
  const tubeGeometry = useMemo(() => new THREE.TubeGeometry(curve, 28, baseWidth, 8, false), [curve, baseWidth]);

  // Three directional pulse markers moving smoothly along the curve
  const pulseRefs = [useRef(), useRef(), useRef()];

  useFrame((state) => {
    if (!active || direction === 'idle') return;
    const time = state.clock.elapsedTime;
    const speed = 0.35; // deliberate, calm operational pace

    pulseRefs.forEach((ref, idx) => {
      if (!ref.current) return;
      const offset = idx / 3;
      let t = ((time * speed + offset) % 1.0);
      if (direction === 'reverse') {
        t = 1.0 - t;
      }

      // Safe bounds
      t = Math.max(0.01, Math.min(0.99, t));
      const pt = curve.getPoint(t);
      const tangent = curve.getTangent(t);

      ref.current.position.copy(pt);
      if (direction === 'reverse') {
        tangent.negate();
      }
      ref.current.quaternion.setFromUnitVectors(new THREE.Vector3(0, 1, 0), tangent);
    });
  });

  const conduitOpacity = isEmphasized
    ? 0.92
    : isDimmed
    ? 0.20
    : active
    ? 0.70
    : 0.15;

  const actualColor = isCritical ? '#b5382b' : color;

  return (
    <group name={`flow-${connection.id}`}>
      {/* Base Conduit Tube */}
      <mesh geometry={tubeGeometry} renderOrder={20} raycast={() => null}>
        <meshStandardMaterial
          color={active ? actualColor : '#94a3b8'}
          roughness={0.45}
          metalness={0.3}
          transparent
          opacity={conduitOpacity}
          depthWrite={false}
        />
      </mesh>

      {/* Directional Chevron / Cone Pulses */}
      {active && direction !== 'idle' && (
        <>
          {[0, 1, 2].map((idx) => (
            <mesh
              key={`pulse-${idx}`}
              ref={pulseRefs[idx]}
              renderOrder={22}
              raycast={() => null}
            >
              <coneGeometry args={[baseWidth * 1.55, baseWidth * 3.8, 8]} />
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

// Grounded Stanchion and Interactive HTML badge for each system node
const SystemNodeBadge = ({
  node,
  value,
  subMetric,
  status,
  isHighlighted = false,
  onClick
}) => {
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

  const handleClick = (e) => {
    e.stopPropagation();
    if (onClick) onClick(node);
  };

  return (
    <group position={node.pos}>
      {/* Grounding Conduit Stanchion descending to building roof below */}
      <mesh
        position={[0, (node.roofPos[1] - node.pos[1]) / 2, 0]}
        raycast={() => null}
      >
        <cylinderGeometry args={[0.07, 0.07, node.pos[1] - node.roofPos[1], 8]} />
        <meshStandardMaterial color="#94a3b8" metalness={0.4} roughness={0.6} transparent opacity={0.6} />
      </mesh>

      {/* Structural Substation Base Collar */}
      <mesh position={[0, -0.25, 0]} raycast={() => null}>
        <cylinderGeometry args={[0.32, 0.42, 0.18, 12]} />
        <meshStandardMaterial color="#64748b" metalness={0.6} roughness={0.4} />
      </mesh>

      {/* Clickable bounding box */}
      <mesh
        position={[0, 0.4, 0]}
        onClick={handleClick}
        onPointerOver={(e) => { e.stopPropagation(); setIsHovered(true); document.body.style.cursor = 'pointer'; }}
        onPointerOut={(e) => { e.stopPropagation(); setIsHovered(false); document.body.style.cursor = 'default'; }}
      >
        <boxGeometry args={[2.8, 1.8, 2.0]} />
        <meshBasicMaterial transparent opacity={0} depthWrite={false} />
      </mesh>

      {/* Interactive Node HTML Label */}
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
            boxShadow: isHighlighted || isHovered
              ? '0 4px 14px rgba(182,90,31,0.35)'
              : '0 2px 10px rgba(0,0,0,0.12)',
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            gap: '2px',
            minWidth: '64px',
            transition: 'all 0.15s ease',
            transform: isHovered ? 'scale(1.05)' : 'scale(1.0)'
          }}
        >
          {/* Top Status Pill */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
            <span
              style={{
                width: '5px',
                height: '5px',
                borderRadius: '50%',
                background: styleMeta.dot
              }}
            />
            <span
              style={{
                fontSize: '7.5px',
                fontWeight: 800,
                color: styleMeta.border,
                letterSpacing: '0.08em'
              }}
            >
              {styleMeta.text}
            </span>
          </div>

          {/* Node Title */}
          <div style={{ fontSize: '10px', fontWeight: 800, color: '#191c20' }}>
            {node.shortLabel}
          </div>

          {/* Primary Telemetry Metric */}
          {value && (
            <div
              style={{
                fontSize: '9px',
                fontWeight: 700,
                color: '#475569',
                background: styleMeta.bg,
                padding: '1px 4px',
                borderRadius: '2px'
              }}
            >
              {value}
            </div>
          )}

          {/* Secondary Sub-metric */}
          {subMetric && (
            <div style={{ fontSize: '7.5px', color: '#64748b', fontWeight: 500 }}>
              {subMetric}
            </div>
          )}
        </div>
      </Html>
    </group>
  );
};

export const SystemFlowOverlay = ({
  telemetry = {},
  station,
  selectedAssetId = null,
  selectedSensor = null,
  onSelectAsset
}) => {
  const power     = telemetry?.power     || {};
  const battery   = telemetry?.battery   || {};
  const health    = telemetry?.healthStatus || 'NOMINAL';

  // 1. Live Telemetry Extraction & Parsing
  const solarKW   = parseKW(power.solarGeneration);
  const windKW    = parseKW(power.windGeneration);
  const dieselKW  = parseKW(power.dieselGeneration);
  const currentKW = parseKW(power.currentPower) || (solarKW + windKW + dieselKW) || 84.3;
  const loadPct   = power.loadPercentage || 68;

  const battPercent = battery.percentage ?? 78;
  const battState   = (battery.state || 'CHARGING').toUpperCase();
  const isDischarging = battState.includes('DISCHARG') || battPercent < 45;
  const isCharging    = !isDischarging && (battState.includes('CHARG') || battState.includes('FLOAT'));
  const isCriticalBatt = isDischarging && (battPercent < 50 || battState.includes('CRITICAL'));

  const solarActive   = solarKW > 0.5;
  const windActive    = windKW > 0.5;
  const dieselActive  = dieselKW > 0.5;

  // 2. Determine Focused Node/Connection from Selected Asset or Sensor
  const focusedNodeId = useMemo(() => {
    if (selectedAssetId) {
      if (selectedAssetId.includes('BATT')) return 'BATTERY';
      if (selectedAssetId.includes('GEN'))  return 'DIESEL';
      if (selectedAssetId.includes('INV-02') || selectedAssetId.includes('SOLAR')) return 'SOLAR';
      if (selectedAssetId.includes('INV-01') || selectedAssetId.includes('TRANS')) return 'MICROGRID';
      if (selectedAssetId.includes('MAIN') || selectedAssetId.includes('PANEL') || selectedAssetId.includes('HVAC')) return 'STATION';
      if (selectedAssetId.includes('RES'))  return 'WIND';
    }
    if (selectedSensor) {
      const sid = (selectedSensor.id || '').toUpperCase();
      const sname = (selectedSensor.name || '').toUpperCase();
      if (sid === 'ENG-MTR-002' || sid === 'ENG-MTR-006' || sname.includes('GEN') || sname.includes('DG-')) return 'DIESEL';
      if (sid === 'ENG-MTR-003' || sname.includes('BATTERY')) return 'BATTERY';
      if (sid === 'ENG-MTR-001' || sname.includes('SOLAR') || sname.includes('PYRANOMETER')) return 'SOLAR';
      if (sid === 'ENG-MTR-004' || sname.includes('WIND')) return 'WIND';
      if (sid === 'ENG-MTR-005' || sname.includes('MICROGRID')) return 'MICROGRID';
      if (selectedSensor.zone === 'MAIN') return 'STATION';
    }
    return null;
  }, [selectedAssetId, selectedSensor]);

  // 3. Declarative System Connection Model
  const connections = useMemo(() => {
    const list = [];

    // Connection A: SOLAR -> MICROGRID
    list.push({
      id: 'solar-microgrid',
      source: 'SOLAR',
      target: 'MICROGRID',
      from: NODE_DEFINITIONS.SOLAR.pos,
      to: NODE_DEFINITIONS.MICROGRID.pos,
      active: solarActive,
      direction: 'forward',
      value: solarKW,
      color: '#d97706',
      baseWidth: 0.12 + Math.min(0.10, (solarKW / 60) * 0.10),
      isCritical: false
    });

    // Connection B: WIND -> MICROGRID
    list.push({
      id: 'wind-microgrid',
      source: 'WIND',
      target: 'MICROGRID',
      from: NODE_DEFINITIONS.WIND.pos,
      to: NODE_DEFINITIONS.MICROGRID.pos,
      active: windActive,
      direction: 'forward',
      value: windKW,
      color: '#4f6f52',
      baseWidth: 0.12 + Math.min(0.10, (windKW / 60) * 0.10),
      isCritical: false
    });

    // Connection C: DIESEL -> MICROGRID
    list.push({
      id: 'diesel-microgrid',
      source: 'DIESEL',
      target: 'MICROGRID',
      from: NODE_DEFINITIONS.DIESEL.pos,
      to: NODE_DEFINITIONS.MICROGRID.pos,
      active: dieselActive,
      direction: 'forward',
      value: dieselKW,
      color: dieselActive ? '#b65a1f' : '#94a3b8',
      baseWidth: dieselActive ? (0.13 + Math.min(0.09, (dieselKW / 50) * 0.09)) : 0.07,
      isCritical: false
    });

    // Connection D: BATTERY <-> MICROGRID (Direction depends on charge/discharge)
    if (isCharging) {
      list.push({
        id: 'microgrid-battery',
        source: 'MICROGRID',
        target: 'BATTERY',
        from: NODE_DEFINITIONS.MICROGRID.pos,
        to: NODE_DEFINITIONS.BATTERY.pos,
        active: true,
        direction: 'forward', // Microgrid -> Battery
        value: battPercent,
        color: '#4f6f52',
        baseWidth: 0.14,
        isCritical: false
      });
    } else if (isDischarging) {
      list.push({
        id: 'battery-microgrid',
        source: 'BATTERY',
        target: 'MICROGRID',
        from: NODE_DEFINITIONS.BATTERY.pos,
        to: NODE_DEFINITIONS.MICROGRID.pos,
        active: true,
        direction: 'forward', // Battery -> Microgrid
        value: battPercent,
        color: isCriticalBatt ? '#b5382b' : '#d97706',
        baseWidth: isCriticalBatt ? 0.18 : 0.14,
        isCritical: isCriticalBatt
      });
    } else {
      list.push({
        id: 'battery-idle',
        source: 'BATTERY',
        target: 'MICROGRID',
        from: NODE_DEFINITIONS.BATTERY.pos,
        to: NODE_DEFINITIONS.MICROGRID.pos,
        active: false,
        direction: 'idle',
        value: battPercent,
        color: '#94a3b8',
        baseWidth: 0.07,
        isCritical: false
      });
    }

    // Connection E: MICROGRID -> STATION LOAD
    const stationActive = (solarActive || windActive || dieselActive || isDischarging);
    list.push({
      id: 'microgrid-station',
      source: 'MICROGRID',
      target: 'STATION',
      from: NODE_DEFINITIONS.MICROGRID.pos,
      to: NODE_DEFINITIONS.STATION.pos,
      active: stationActive,
      direction: 'forward',
      value: currentKW,
      color: isCriticalBatt ? '#d97706' : '#b65a1f',
      baseWidth: 0.18,
      isCritical: isCriticalBatt
    });

    return list;
  }, [solarActive, solarKW, windActive, windKW, dieselActive, dieselKW, isCharging, isDischarging, isCriticalBatt, battPercent, currentKW]);

  // Handle click on node badge: focus and inspect matching operational machinery
  const handleNodeClick = (node) => {
    if (onSelectAsset && node.defaultAsset) {
      onSelectAsset(node.defaultAsset);
    }
  };

  return (
    <group name="system-flow-overlay">
      {/* 1. Technical Overhead Power Flow Conduits */}
      {connections.map((conn) => {
        const isEmphasized = focusedNodeId
          ? (conn.source === focusedNodeId || conn.target === focusedNodeId)
          : false;
        const isDimmed = focusedNodeId ? !isEmphasized : false;

        return (
          <FlowConduit
            key={conn.id}
            connection={conn}
            isEmphasized={isEmphasized}
            isDimmed={isDimmed}
          />
        );
      })}

      {/* 2. Interactive Grounded System Nodes with Real Telemetry */}
      <SystemNodeBadge
        node={NODE_DEFINITIONS.SOLAR}
        value={solarActive ? `${solarKW.toFixed(1)} kW` : '0.0 kW'}
        subMetric={solarActive ? 'ACTIVE' : 'STOWED / NIGHT'}
        status={solarActive ? 'ACTIVE' : 'OFFLINE'}
        isHighlighted={focusedNodeId === 'SOLAR'}
        onClick={handleNodeClick}
      />

      <SystemNodeBadge
        node={NODE_DEFINITIONS.WIND}
        value={windActive ? `${windKW.toFixed(1)} kW` : '0.0 kW'}
        subMetric={windActive ? 'EAST MAST' : 'CALM'}
        status={windActive ? 'NOMINAL' : 'OFFLINE'}
        isHighlighted={focusedNodeId === 'WIND'}
        onClick={handleNodeClick}
      />

      <SystemNodeBadge
        node={NODE_DEFINITIONS.DIESEL}
        value={dieselActive ? `${dieselKW.toFixed(1)} kW` : '0.0 kW'}
        subMetric={dieselActive ? 'DG #1 & #2' : 'TRIPPED / STBY'}
        status={dieselActive ? 'ACTIVE' : 'OFFLINE'}
        isHighlighted={focusedNodeId === 'DIESEL'}
        onClick={handleNodeClick}
      />

      <SystemNodeBadge
        node={NODE_DEFINITIONS.MICROGRID}
        value={`${currentKW.toFixed(1)} kW`}
        subMetric="415V • 50 Hz"
        status={isCriticalBatt ? 'CRITICAL' : 'NOMINAL'}
        isHighlighted={focusedNodeId === 'MICROGRID'}
        onClick={handleNodeClick}
      />

      <SystemNodeBadge
        node={NODE_DEFINITIONS.BATTERY}
        value={`${battPercent}%`}
        subMetric={isDischarging ? 'DISCHARGING' : isCharging ? 'CHARGING' : 'FLOAT'}
        status={isCriticalBatt ? 'CRITICAL' : isDischarging ? 'DISCHARGING' : 'CHARGING'}
        isHighlighted={focusedNodeId === 'BATTERY'}
        onClick={handleNodeClick}
      />

      <SystemNodeBadge
        node={NODE_DEFINITIONS.STATION}
        value={`${currentKW.toFixed(1)} kW`}
        subMetric={`${loadPct}% DEMAND`}
        status={isCriticalBatt ? 'CRITICAL' : 'ACTIVE'}
        isHighlighted={focusedNodeId === 'STATION'}
        onClick={handleNodeClick}
      />
    </group>
  );
};

export default SystemFlowOverlay;
