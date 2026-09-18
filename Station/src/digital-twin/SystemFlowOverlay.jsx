import React, { useRef, useMemo, useState } from 'react';
import * as THREE from 'three';
import { useFrame } from '@react-three/fiber';
import { Html } from '@react-three/drei';

/**
 * SystemFlowOverlay — Comprehensive Polar Research Station Electrical & Utility Grid
 *
 * Simulates an authentic Antarctic station multi-circuit microgrid:
 * 1. Heavy Generation Circuits:
 *    - DG #1 & DG #2 branch feeders to local generator switchgear
 *    - Day Tank fuel feed manifold
 *    - West Utility Bridge conduit to central substation
 * 2. Renewable Energy Feeders:
 *    - Dual rooftop solar array feeders (Storage & Main) to solar inverters
 *    - East ridge wind turbine feeder routing via Research Corridor to microgrid
 * 3. Energy Storage Dual-Bus:
 *    - Battery Bank A & B LiFePO4 cabinet circuits to BMS inverter
 *    - Bidirectional charging (Microgrid -> Battery) and discharging (Battery -> Microgrid)
 * 4. Facility Sub-Distribution Feeders (Station Loads):
 *    - Main Spine 415V busway through South Corridor into Main Habitat Hub
 *    - Command & Expedition Console feeder
 *    - Environmental Life Support feeder
 *    - HVAC Mechanical & Thermal Plant loop
 *    - Scientific Laboratories & Optical Radome feeder
 *    - Logistics, Fuel Transfer & Cryo-Freezer feeder
 *    - Deep Space Satellite Tracking & Comms RF Shelter feeder
 * 5. Industrial Substation Junction Tap Boxes at module entryways with live status LEDs
 * 6. Live telemetry synchronization with POWER CRISIS, STORM, and NORMAL scenarios
 */

// Helper to extract numerical kW values safely
const parseKW = (v) => {
  if (typeof v === 'number') return v;
  if (!v) return 0;
  return parseFloat(v.toString().replace(/[^0-9.]/g, '')) || 0;
};

// Create smooth multi-point path routed along utility bridge corridors
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

// Individual animated technical conduit segment
const ConduitSegment = ({
  circuit,
  isEmphasized = false,
  isDimmed = false,
  globalSpeed = 0.35
}) => {
  const { from, to, active, direction = 'forward', color, baseWidth = 0.12, arch = 0.4, pulses = 2, isCritical } = circuit;
  const curve = useMemo(() => makeCurvedRoute(from, to, arch), [from, to, arch]);
  const geometry = useMemo(() => new THREE.TubeGeometry(curve, 24, baseWidth, 6, false), [curve, baseWidth]);

  // Animated energy chevron pulses
  const pulseRefs = useMemo(() => Array.from({ length: pulses }).map(() => React.createRef()), [pulses]);

  useFrame((state) => {
    if (!active || direction === 'idle') return;
    const time = state.clock.elapsedTime;
    const speed = globalSpeed * (circuit.speedMultiplier || 1.0);

    pulseRefs.forEach((ref, idx) => {
      if (!ref.current) return;
      const offset = idx / pulses;
      let t = ((time * speed + offset) % 1.0);
      if (direction === 'reverse') {
        t = 1.0 - t;
      }
      t = Math.max(0.02, Math.min(0.98, t));
      const pt = curve.getPoint(t);
      const tangent = curve.getTangent(t);

      ref.current.position.copy(pt);
      if (direction === 'reverse') tangent.negate();
      ref.current.quaternion.setFromUnitVectors(new THREE.Vector3(0, 1, 0), tangent);
    });
  });

  const conduitOpacity = isEmphasized
    ? 0.95
    : isDimmed
    ? 0.18
    : active
    ? 0.72
    : 0.12;

  const actualColor = isCritical ? '#b5382b' : color;

  return (
    <group name={`circuit-${circuit.id}`}>
      {/* Base Conduit Tube */}
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

      {/* Directional Chevron Pulses */}
      {active && direction !== 'idle' && (
        <>
          {Array.from({ length: pulses }).map((_, idx) => (
            <mesh
              key={`pulse-${idx}`}
              ref={pulseRefs[idx]}
              renderOrder={22}
              raycast={() => null}
            >
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

// Industrial Substation Tap Box with glowing status LED mounted at corridor junctions
const UtilityJunctionBox = ({
  position,
  label,
  subLabel,
  status = 'NOMINAL',
  color = '#475569',
  onClick
}) => {
  const [hovered, setHovered] = useState(false);
  const statusColor = status === 'CRITICAL' ? '#e53e3e' : status === 'WARNING' ? '#d97706' : status === 'OFFLINE' ? '#64748b' : '#38a169';

  return (
    <group position={position}>
      {/* Heavy Weatherproof Junction Enclosure */}
      <mesh
        castShadow
        onClick={(e) => { e.stopPropagation(); if (onClick) onClick(); }}
        onPointerOver={(e) => { e.stopPropagation(); setHovered(true); document.body.style.cursor = 'pointer'; }}
        onPointerOut={(e) => { e.stopPropagation(); setHovered(false); document.body.style.cursor = 'default'; }}
      >
        <boxGeometry args={[1.2, 0.8, 0.9]} />
        <meshStandardMaterial
          color={hovered ? '#b65a1f' : color}
          metalness={0.65}
          roughness={0.35}
        />
      </mesh>

      {/* Top Mounting Collar */}
      <mesh position={[0, 0.45, 0]}>
        <cylinderGeometry args={[0.3, 0.3, 0.12, 8]} />
        <meshStandardMaterial color="#334155" metalness={0.8} />
      </mesh>

      {/* Glowing Status Pilot Beacon */}
      <mesh position={[0, 0.55, 0]}>
        <sphereGeometry args={[0.12, 12, 8]} />
        <meshBasicMaterial color={statusColor} />
      </mesh>

      {/* Technical Junction Label */}
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

// Major Interactive System Node (HTML badge with comprehensive telemetry)
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

// Physical 3D spatial node definitions anchored to building facilities
const NODE_DEFINITIONS = {
  SOLAR: {
    id: 'SOLAR',
    label: 'SOLAR ARRAY',
    shortLabel: 'SOLAR',
    pos: [10.0, 11.8, -28.0],
    roofPos: [10.0, 6.5, -28.0],
    zone: 'ENERGY',
    defaultAsset: { id: 'ENERGY-INV-02', type: 'INVERTER', label: 'SOLAR INVERTER', zone: 'ENERGY' },
    icon: '☀'
  },
  WIND: {
    id: 'WIND',
    label: 'WIND TURBINE',
    shortLabel: 'WIND',
    pos: [44.0, 14.5, -10.0],
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
    pos: [0.0, 12.2, -28.0],
    roofPos: [0.0, 6.5, -28.0],
    zone: 'ENERGY',
    defaultAsset: { id: 'ENERGY-INV-01', type: 'INVERTER', label: 'MICROGRID INVERTER', zone: 'ENERGY' },
    icon: '⎇'
  },
  BATTERY: {
    id: 'BATTERY',
    label: 'BATTERY BANK',
    shortLabel: 'BATTERY',
    pos: [-7.5, 11.2, -26.0],
    roofPos: [-7.5, 6.5, -26.0],
    zone: 'ENERGY',
    defaultAsset: { id: 'ENERGY-BATT-01', type: 'BATTERY', label: 'BATTERY BANK', zone: 'ENERGY' },
    icon: '🔋'
  },
  STATION: {
    id: 'STATION',
    label: 'STATION LOAD',
    shortLabel: 'STATION LOAD',
    pos: [0.0, 13.8, 0.0],
    roofPos: [0.0, 7.0, 0.0],
    zone: 'MAIN',
    defaultAsset: { id: 'MAIN-PANEL-01', type: 'CONTROL', label: 'COMMAND CONSOLE', zone: 'MAIN' },
    icon: '⌂'
  }
};

export const SystemFlowOverlay = ({
  telemetry = {},
  station,
  selectedAssetId = null,
  selectedSensor = null,
  onSelectAsset,
  incidentGraph = null,
}) => {
  const power     = telemetry?.power     || {};
  const battery   = telemetry?.battery   || {};

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

  // 2. Focused System Node Detection
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

  // 3. Multi-circuit Realistic Electrical Grid Topology
  const circuits = useMemo(() => {
    const list = [];

    // =========================================================================
    // A. DIESEL GENERATION FACILITY (West Subsystem)
    // =========================================================================
    // 1. DG #1 Engine Feeder to Local Generator Switchgear
    list.push({
      id: 'gen-dg1-swg',
      category: 'generation',
      from: [-34.5, 3.2, -27.0],
      to: [-28.0, 5.0, -30.0],
      active: dieselActive,
      direction: 'forward',
      color: dieselActive ? '#b65a1f' : '#64748b',
      baseWidth: 0.11,
      pulses: 1,
      arch: 0.2
    });

    // 2. DG #2 Engine Feeder to Local Generator Switchgear
    list.push({
      id: 'gen-dg2-swg',
      category: 'generation',
      from: [-25.5, 3.2, -27.0],
      to: [-28.0, 5.0, -30.0],
      active: dieselActive,
      direction: 'forward',
      color: dieselActive ? '#b65a1f' : '#64748b',
      baseWidth: 0.11,
      pulses: 1,
      arch: 0.2
    });

    // 3. Day Tank Fuel Supply Loop
    list.push({
      id: 'gen-fuel-feed',
      category: 'fuel',
      from: [-30.0, 3.2, -35.0],
      to: [-30.0, 3.2, -28.5],
      active: dieselActive,
      direction: 'forward',
      color: '#d97706',
      baseWidth: 0.09,
      pulses: 1,
      arch: 0.15
    });

    // 4. West Utility Corridor 3 Trunk: Generator Switchgear -> Energy Substation Bus
    list.push({
      id: 'gen-swg-corridor',
      category: 'generation',
      from: [-28.0, 5.0, -30.0],
      to: [-16.5, 7.8, -30.0],
      active: dieselActive,
      direction: 'forward',
      color: dieselActive ? '#b65a1f' : '#64748b',
      baseWidth: 0.15,
      pulses: 2,
      arch: 0.3
    });

    list.push({
      id: 'gen-corridor-substation',
      category: 'generation',
      from: [-16.5, 7.8, -30.0],
      to: [-2.0, 5.5, -30.0],
      active: dieselActive,
      direction: 'forward',
      color: dieselActive ? '#b65a1f' : '#64748b',
      baseWidth: 0.15,
      pulses: 2,
      arch: 0.3
    });

    // =========================================================================
    // B. RENEWABLE SOLAR & WIND INFEEDS
    // =========================================================================
    // 5. Storage Rooftop Solar Array Trunk -> Corridor 4
    list.push({
      id: 'solar-stor-c4',
      category: 'solar',
      from: [30.5, 11.2, -28.5],
      to: [17.5, 7.8, -30.0],
      active: solarActive,
      direction: 'forward',
      color: '#d97706',
      baseWidth: 0.12,
      pulses: 2,
      arch: 0.4
    });

    // 6. Corridor 4 -> Solar Inverter INV-02 in Energy Zone
    list.push({
      id: 'solar-c4-inv',
      category: 'solar',
      from: [17.5, 7.8, -30.0],
      to: [5.5, 3.5, -26.5],
      active: solarActive,
      direction: 'forward',
      color: '#d97706',
      baseWidth: 0.12,
      pulses: 2,
      arch: 0.3
    });

    // 7. Solar Inverter -> Substation Central Microgrid Bus
    list.push({
      id: 'solar-inv-bus',
      category: 'solar',
      from: [5.5, 3.5, -26.5],
      to: [0.0, 5.5, -28.0],
      active: solarActive,
      direction: 'forward',
      color: '#d97706',
      baseWidth: 0.14,
      pulses: 2,
      arch: 0.2
    });

    // 8. Wind Turbine East Mast -> Research Roof Subpanel
    list.push({
      id: 'wind-mast-res',
      category: 'wind',
      from: [48.0, 14.0, -14.0],
      to: [38.0, 7.2, 0.0],
      active: windActive,
      direction: 'forward',
      color: '#4f6f52',
      baseWidth: 0.13,
      pulses: 2,
      arch: 0.5,
      speedMultiplier: windKW > 40 ? 1.8 : 1.0
    });

    // 9. Research Subpanel -> Corridor 1 Trunk
    list.push({
      id: 'wind-res-c1',
      category: 'wind',
      from: [38.0, 7.2, 0.0],
      to: [22.0, 7.8, 0.0],
      active: windActive,
      direction: 'forward',
      color: '#4f6f52',
      baseWidth: 0.13,
      pulses: 2,
      arch: 0.3
    });

    // 10. Corridor 1 -> Main Building Junction
    list.push({
      id: 'wind-c1-main',
      category: 'wind',
      from: [22.0, 7.8, 0.0],
      to: [0.0, 7.5, 0.0],
      active: windActive,
      direction: 'forward',
      color: '#4f6f52',
      baseWidth: 0.14,
      pulses: 2,
      arch: 0.3
    });

    // 11. Main Junction -> Corridor 2 Spine -> Substation Bus
    list.push({
      id: 'wind-main-spine',
      category: 'wind',
      from: [0.0, 7.5, 0.0],
      to: [0.0, 8.0, -16.0],
      active: windActive,
      direction: 'forward',
      color: '#4f6f52',
      baseWidth: 0.14,
      pulses: 2,
      arch: 0.3
    });

    list.push({
      id: 'wind-spine-bus',
      category: 'wind',
      from: [0.0, 8.0, -16.0],
      to: [0.0, 5.5, -28.0],
      active: windActive,
      direction: 'forward',
      color: '#4f6f52',
      baseWidth: 0.14,
      pulses: 2,
      arch: 0.3
    });

    // =========================================================================
    // C. ENERGY STORAGE DUAL-BANK (Substation <-> Battery Banks)
    // =========================================================================
    // 12. Battery Bank A (BATT-01) <-> Substation BMS
    list.push({
      id: 'batt-bank-a',
      category: 'battery',
      from: [-7.0, 3.2, -34.0],
      to: [-3.5, 4.8, -30.0],
      active: true,
      direction: isDischarging ? 'forward' : isCharging ? 'reverse' : 'idle',
      color: isCriticalBatt ? '#b5382b' : isDischarging ? '#d97706' : '#4f6f52',
      baseWidth: 0.13,
      pulses: 2,
      arch: 0.2,
      isCritical: isCriticalBatt
    });

    // 13. Battery Bank B (BATT-02) <-> Substation BMS
    list.push({
      id: 'batt-bank-b',
      category: 'battery',
      from: [-7.0, 3.2, -26.0],
      to: [-3.5, 4.8, -30.0],
      active: true,
      direction: isDischarging ? 'forward' : isCharging ? 'reverse' : 'idle',
      color: isCriticalBatt ? '#b5382b' : isDischarging ? '#d97706' : '#4f6f52',
      baseWidth: 0.13,
      pulses: 2,
      arch: 0.2,
      isCritical: isCriticalBatt
    });

    // 14. BMS Subpanel <-> Central Microgrid Bus
    list.push({
      id: 'batt-bms-bus',
      category: 'battery',
      from: [-3.5, 4.8, -30.0],
      to: [0.0, 5.5, -28.0],
      active: true,
      direction: isDischarging ? 'forward' : isCharging ? 'reverse' : 'idle',
      color: isCriticalBatt ? '#b5382b' : isDischarging ? '#d97706' : '#4f6f52',
      baseWidth: 0.16,
      pulses: 3,
      arch: 0.25,
      isCritical: isCriticalBatt
    });

    // =========================================================================
    // D. FACILITY LOAD DISTRIBUTION FEEDERS (Substation -> Station Facilities)
    // =========================================================================
    const gridEnergized = (solarActive || windActive || dieselActive || isDischarging);

    // 15. Primary Spine Feeder Trunk: Substation -> Corridor 2 -> Main Habitat Master Panel
    list.push({
      id: 'bus-spine-c2',
      category: 'load',
      from: [0.0, 5.5, -28.0],
      to: [0.0, 8.0, -16.0],
      active: gridEnergized,
      direction: 'forward',
      color: isCriticalBatt ? '#d97706' : '#b65a1f',
      baseWidth: 0.18,
      pulses: 3,
      arch: 0.2
    });

    list.push({
      id: 'spine-c2-mainhub',
      category: 'load',
      from: [0.0, 8.0, -16.0],
      to: [0.0, 7.5, -2.0],
      active: gridEnergized,
      direction: 'forward',
      color: isCriticalBatt ? '#d97706' : '#b65a1f',
      baseWidth: 0.18,
      pulses: 3,
      arch: 0.2
    });

    // 16. Main Hub Branch -> Expedition Command Console
    list.push({
      id: 'main-command-feed',
      category: 'load',
      from: [0.0, 7.5, -2.0],
      to: [0.0, 3.0, 0.0],
      active: gridEnergized,
      direction: 'forward',
      color: '#b65a1f',
      baseWidth: 0.12,
      pulses: 1,
      arch: 0.2
    });

    // 17. Main Hub Branch -> Environmental Life Support Plant (Vital Load)
    list.push({
      id: 'main-lifesupport-feed',
      category: 'load',
      from: [0.0, 7.5, -2.0],
      to: [8.5, 3.0, 5.0],
      active: gridEnergized,
      direction: 'forward',
      color: '#38a169',
      baseWidth: 0.14,
      pulses: 2,
      arch: 0.3
    });

    // 18. Main Hub Branch -> HVAC Thermal Plant Loop
    list.push({
      id: 'main-hvac-feed',
      category: 'load',
      from: [0.0, 7.5, -2.0],
      to: [-8.5, 3.0, -4.0],
      active: gridEnergized,
      direction: 'forward',
      color: isCriticalBatt ? '#d97706' : '#38a169',
      baseWidth: 0.13,
      pulses: 2,
      arch: 0.3
    });

    // 19. Main Hub -> Corridor 1 -> Research Laboratories (Scientific Instruments)
    list.push({
      id: 'main-c1-reslab',
      category: 'load',
      from: [0.0, 7.5, -2.0],
      to: [22.0, 7.8, 0.0],
      active: gridEnergized && !isCriticalBatt, // Load shedding in extreme power crisis
      direction: 'forward',
      color: '#4f6f52',
      baseWidth: 0.12,
      pulses: 2,
      arch: 0.25
    });

    list.push({
      id: 'c1-reslab-gear',
      category: 'load',
      from: [22.0, 7.8, 0.0],
      to: [38.0, 3.5, 0.0],
      active: gridEnergized && !isCriticalBatt,
      direction: 'forward',
      color: '#4f6f52',
      baseWidth: 0.12,
      pulses: 2,
      arch: 0.3
    });

    // 20. Substation -> Corridor 4 -> Logistics & Cold Provisions (Cryo Freezer)
    list.push({
      id: 'substation-c4-storage',
      category: 'load',
      from: [0.0, 5.5, -28.0],
      to: [17.5, 7.8, -30.0],
      active: gridEnergized,
      direction: 'forward',
      color: '#b65a1f',
      baseWidth: 0.13,
      pulses: 2,
      arch: 0.25
    });

    list.push({
      id: 'c4-storage-freezer',
      category: 'load',
      from: [17.5, 7.8, -30.0],
      to: [32.0, 4.0, -30.0],
      active: gridEnergized,
      direction: 'forward',
      color: '#b65a1f',
      baseWidth: 0.13,
      pulses: 2,
      arch: 0.25
    });

    // 21. Substation -> Corridor 5 -> Comms & Ku-Band Dish Shelter
    list.push({
      id: 'substation-c5-comms',
      category: 'load',
      from: [0.0, 5.5, -28.0],
      to: [0.0, 6.0, -43.0],
      active: gridEnergized,
      direction: 'forward',
      color: '#38a169',
      baseWidth: 0.13,
      pulses: 2,
      arch: 0.2
    });

    list.push({
      id: 'c5-comms-shelter',
      category: 'load',
      from: [0.0, 6.0, -43.0],
      to: [0.0, 4.5, -54.0],
      active: gridEnergized,
      direction: 'forward',
      color: '#38a169',
      baseWidth: 0.13,
      pulses: 2,
      arch: 0.25
    });

    return list;
  }, [dieselActive, solarActive, windActive, windKW, isCharging, isDischarging, isCriticalBatt]);

  // Handle click on node badge: focus and inspect matching operational machinery
  const handleNodeClick = (node) => {
    if (onSelectAsset && node.defaultAsset) {
      onSelectAsset(node.defaultAsset);
    }
  };

  // ─── Circuit emphasis: from asset/sensor selection OR incident ───────────────
  const incidentNodeIds = useMemo(() => {
    if (!incidentGraph?.isActive) return new Set();
    const s = new Set();
    (incidentGraph.nodes || []).forEach(n => s.add(n.id));
    return s;
  }, [incidentGraph]);

  // Determine which circuit categories the incident involves
  const incidentCategories = useMemo(() => {
    const cats = new Set();
    if (!incidentGraph?.isActive) return cats;
    if (incidentNodeIds.has('SOLAR'))     cats.add('solar');
    if (incidentNodeIds.has('WIND'))      cats.add('wind');
    if (incidentNodeIds.has('DIESEL'))    cats.add('generation');
    if (incidentNodeIds.has('BATTERY'))   cats.add('battery');
    if (incidentNodeIds.has('MICROGRID')) cats.add('load');
    if (incidentNodeIds.has('STATION'))   cats.add('load');
    return cats;
  }, [incidentGraph, incidentNodeIds]);

  return (
    <group name="system-flow-overlay">
      {/* 1. Multi-Circuit Technical Power Grid Conduits */}
      {circuits.map((circuit) => {
        // Asset/sensor-based emphasis
        const assetBased = focusedNodeId
          ? (
              (focusedNodeId === 'BATTERY'   && circuit.category === 'battery') ||
              (focusedNodeId === 'DIESEL'    && circuit.category === 'generation') ||
              (focusedNodeId === 'SOLAR'     && circuit.category === 'solar') ||
              (focusedNodeId === 'WIND'      && circuit.category === 'wind') ||
              (focusedNodeId === 'STATION'   && circuit.category === 'load') ||
              (focusedNodeId === 'MICROGRID' && (circuit.category === 'load' || circuit.id.includes('bus')))
            )
          : false;

        // Incident-based emphasis: highlight circuits involved in the incident chain
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

      {/* 2. Industrial Substation Junction Tap Boxes at Corridor Intersections */}
      <UtilityJunctionBox
        position={[-28.0, 5.0, -30.0]}
        label="DG SWITCHGEAR"
        subLabel="415V"
        status={dieselActive ? 'ACTIVE' : 'OFFLINE'}
        color="#334155"
        onClick={() => onSelectAsset && onSelectAsset(NODE_DEFINITIONS.DIESEL.defaultAsset)}
      />

      <UtilityJunctionBox
        position={[0.0, 7.8, -28.0]}
        label="SUBSTATION BUS"
        subLabel="415V • 50Hz"
        status={isCriticalBatt ? 'CRITICAL' : 'NOMINAL'}
        color="#1e293b"
        onClick={() => onSelectAsset && onSelectAsset(NODE_DEFINITIONS.MICROGRID.defaultAsset)}
      />

      <UtilityJunctionBox
        position={[0.0, 8.2, -2.0]}
        label="HAB DISTRIBUTION"
        subLabel="230V AC"
        status="NOMINAL"
        color="#334155"
        onClick={() => onSelectAsset && onSelectAsset(NODE_DEFINITIONS.STATION.defaultAsset)}
      />

      <UtilityJunctionBox
        position={[38.0, 7.2, 0.0]}
        label="RESEARCH SUBPANEL"
        subLabel="LAB BUS"
        status={windActive ? 'ACTIVE' : 'NOMINAL'}
        color="#334155"
        onClick={() => onSelectAsset && onSelectAsset(NODE_DEFINITIONS.WIND.defaultAsset)}
      />

      <UtilityJunctionBox
        position={[32.0, 6.2, -30.0]}
        label="COLD LOGISTICS TAP"
        subLabel="3-PHASE"
        status="NOMINAL"
        color="#334155"
        onClick={() => onSelectAsset && onSelectAsset({ id: 'STORAGE-FREEZE-01', type: 'FREEZER', label: 'CRYO FREEZER', zone: 'STORAGE' })}
      />

      <UtilityJunctionBox
        position={[0.0, 5.8, -50.0]}
        label="COMMS RF TAP"
        subLabel="UPS BUS"
        status="NOMINAL"
        color="#334155"
        onClick={() => onSelectAsset && onSelectAsset({ id: 'COMMS-COMM-01', type: 'COMMS', label: 'RF SHELTER', zone: 'COMMS' })}
      />

      {/* 3. Major Interactive System Node Badges with Real Telemetry */}
      <SystemNodeBadge
        node={NODE_DEFINITIONS.SOLAR}
        value={solarActive ? `${solarKW.toFixed(1)} kW` : '0.0 kW'}
        subMetric={solarActive ? 'DUAL ARRAY' : 'STOWED / NIGHT'}
        status={solarActive ? 'ACTIVE' : 'OFFLINE'}
        isHighlighted={focusedNodeId === 'SOLAR'}
        onClick={handleNodeClick}
      />

      <SystemNodeBadge
        node={NODE_DEFINITIONS.WIND}
        value={windActive ? `${windKW.toFixed(1)} kW` : '0.0 kW'}
        subMetric={windActive ? 'EAST RIDGE MAST' : 'CALM'}
        status={windActive ? 'NOMINAL' : 'OFFLINE'}
        isHighlighted={focusedNodeId === 'WIND'}
        onClick={handleNodeClick}
      />

      <SystemNodeBadge
        node={NODE_DEFINITIONS.DIESEL}
        value={dieselActive ? `${dieselKW.toFixed(1)} kW` : '0.0 kW'}
        subMetric={dieselActive ? 'DG #1 & #2 ONLINE' : 'TRIPPED / STANDBY'}
        status={dieselActive ? 'ACTIVE' : 'OFFLINE'}
        isHighlighted={focusedNodeId === 'DIESEL'}
        onClick={handleNodeClick}
      />

      <SystemNodeBadge
        node={NODE_DEFINITIONS.MICROGRID}
        value={`${currentKW.toFixed(1)} kW`}
        subMetric="415V • 50 Hz SYNCH"
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
