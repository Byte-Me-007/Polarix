import React, { useRef } from 'react';
import { useFrame } from '@react-three/fiber';
import { Html } from '@react-three/drei';
import * as THREE from 'three';

const STATUS_COLOR = {
  RUNNING:  '#2d8a4e',
  NORMAL:   '#2d8a4e',
  CHARGING: '#2d8a4e',
  WARNING:  '#c87a1a',
  CRITICAL: '#c0392b',
  OFFLINE:  '#5d6672'
};

const getColor = (status) => STATUS_COLOR[status?.toUpperCase()] || STATUS_COLOR.RUNNING;

// ─── Diesel Generator — Large industrial engine with radiator, control panel ───
const DieselGeneratorMesh = ({ status }) => {
  const isOffline = status === 'OFFLINE';
  const isCritical = status === 'CRITICAL';
  const engColor = isOffline ? '#5a5a5a' : '#2c3540';
  const trimColor = isCritical ? '#8b1a1a' : '#1a2030';

  return (
    <group>
      {/* Main engine block */}
      <mesh castShadow position={[0, 0.9, 0]}>
        <boxGeometry args={[3.2, 1.8, 1.5]} />
        <meshStandardMaterial color={engColor} roughness={0.55} metalness={0.7} />
      </mesh>
      {/* Engine top casing */}
      <mesh castShadow position={[0, 1.85, 0]}>
        <boxGeometry args={[3.0, 0.2, 1.3]} />
        <meshStandardMaterial color="#1a2030" roughness={0.4} metalness={0.8} />
      </mesh>
      {/* Alternator housing (cylinder) */}
      <mesh castShadow position={[1.4, 0.9, 0]} rotation={[0, 0, Math.PI / 2]}>
        <cylinderGeometry args={[0.55, 0.55, 1.2, 16]} />
        <meshStandardMaterial color="#2a3545" roughness={0.5} metalness={0.75} />
      </mesh>
      {/* Cooling fins array */}
      {[-0.5, -0.2, 0.1, 0.4].map((dx, i) => (
        <mesh key={i} castShadow position={[dx - 0.6, 0.85, 0.78]}>
          <boxGeometry args={[0.06, 1.4, 0.12]} />
          <meshStandardMaterial color="#1c2535" roughness={0.6} metalness={0.8} />
        </mesh>
      ))}
      {/* Exhaust header pipe */}
      <mesh castShadow position={[0, 2.05, -0.3]} rotation={[0, 0, 0]}>
        <cylinderGeometry args={[0.12, 0.14, 0.4, 8]} />
        <meshStandardMaterial color="#383838" roughness={0.7} metalness={0.8} />
      </mesh>
      <mesh castShadow position={[0, 2.45, -0.3]}>
        <cylinderGeometry args={[0.12, 0.12, 0.8, 8]} />
        <meshStandardMaterial color="#222" roughness={0.8} metalness={0.7} />
      </mesh>
      {/* Base skid frame */}
      <mesh receiveShadow position={[0, 0.06, 0]}>
        <boxGeometry args={[3.6, 0.12, 1.8]} />
        <meshStandardMaterial color="#1a1f28" roughness={0.7} metalness={0.6} />
      </mesh>
      {/* Control panel */}
      <mesh position={[-1.6, 1.0, 0]}>
        <boxGeometry args={[0.08, 1.0, 0.8]} />
        <meshStandardMaterial color="#1c2030" roughness={0.3} metalness={0.7} />
      </mesh>
      {/* Control panel display */}
      <mesh position={[-1.65, 1.1, 0]}>
        <boxGeometry args={[0.02, 0.5, 0.55]} />
        <meshStandardMaterial color={isOffline ? '#111' : '#0a2a18'} roughness={0.1} metalness={0.9} emissive={isOffline ? '#000' : '#0a4020'} emissiveIntensity={0.4} />
      </mesh>
      {/* Status LEDs */}
      {[0, 1, 2].map(i => (
        <mesh key={i} position={[-1.66, 0.6 + i * 0.12, 0.18]}>
          <sphereGeometry args={[0.03, 6, 4]} />
          <meshBasicMaterial color={i === 0 ? getColor(status) : i === 1 ? '#c87a1a' : '#1a3a8a'} />
        </mesh>
      ))}
      {/* Vibration mounts */}
      {[[-1.4, -2], [1.4, -2], [-1.4, 2], [1.4, 2]].map(([mx, mz], i) => (
        <mesh key={i} position={[mx, 0, mz * 0.38]}>
          <cylinderGeometry args={[0.1, 0.12, 0.14, 8]} />
          <meshStandardMaterial color="#333" roughness={0.7} metalness={0.4} />
        </mesh>
      ))}
    </group>
  );
};

// ─── Battery Rack — Tall industrial LiFePO4 cabinet system ───
const BatteryRackMesh = ({ status }) => {
  const isCharging = status === 'RUNNING' || status === 'CHARGING';
  const chargeColor = isCharging ? '#1a5c3a' : status === 'CRITICAL' ? '#6b1212' : '#3a3a3a';

  return (
    <group>
      {/* Main cabinet enclosure */}
      <mesh castShadow>
        <boxGeometry args={[1.6, 4.2, 0.8]} />
        <meshStandardMaterial color="#1a2535" roughness={0.4} metalness={0.75} />
      </mesh>
      {/* Cabinet door frame */}
      <mesh position={[0, 0, 0.42]}>
        <boxGeometry args={[1.5, 4.0, 0.04]} />
        <meshStandardMaterial color="#212d3f" roughness={0.3} metalness={0.85} />
      </mesh>
      {/* Cell rows — 8 rows of battery cells */}
      {Array.from({ length: 8 }, (_, i) => (
        <group key={i} position={[0, -1.6 + i * 0.44, 0.43]}>
          {/* Cell tray */}
          <mesh>
            <boxGeometry args={[1.35, 0.32, 0.06]} />
            <meshStandardMaterial color="#151e2d" roughness={0.5} metalness={0.7} />
          </mesh>
          {/* Cell indicator strip */}
          <mesh position={[0, 0, 0.04]}>
            <boxGeometry args={[1.2, 0.12, 0.02]} />
            <meshBasicMaterial color={i < 6 ? chargeColor : '#1a1a1a'} />
          </mesh>
        </group>
      ))}
      {/* Top BMS module */}
      <mesh position={[0, 2.3, 0.43]}>
        <boxGeometry args={[1.3, 0.3, 0.06]} />
        <meshStandardMaterial color="#1a3050" roughness={0.3} metalness={0.8} />
      </mesh>
      {/* Status LED panel */}
      <mesh position={[0, 2.1, 0.44]}>
        <boxGeometry args={[0.3, 0.18, 0.02]} />
        <meshBasicMaterial color={getColor(status)} />
      </mesh>
      {/* Cable conduit bottom */}
      <mesh position={[0, -2.25, 0]}>
        <boxGeometry args={[1.7, 0.1, 0.9]} />
        <meshStandardMaterial color="#111827" roughness={0.6} metalness={0.6} />
      </mesh>
      {/* Ventilation slots top */}
      {[-0.4, 0, 0.4].map((dx, i) => (
        <mesh key={i} position={[dx, 2.0, 0.42]}>
          <boxGeometry args={[0.25, 0.06, 0.04]} />
          <meshBasicMaterial color="#0a1020" />
        </mesh>
      ))}
    </group>
  );
};

// ─── Industrial Inverter Cabinet ───
const InverterMesh = ({ status }) => (
  <group>
    <mesh castShadow>
      <boxGeometry args={[0.9, 3.0, 0.55]} />
      <meshStandardMaterial color="#1c2a3a" roughness={0.35} metalness={0.8} />
    </mesh>
    {/* Front door */}
    <mesh position={[0, 0, 0.29]}>
      <boxGeometry args={[0.82, 2.85, 0.04]} />
      <meshStandardMaterial color="#22324a" roughness={0.25} metalness={0.85} />
    </mesh>
    {/* Display screen */}
    <mesh position={[0, 0.8, 0.32]}>
      <boxGeometry args={[0.5, 0.35, 0.02]} />
      <meshStandardMaterial color="#041520" roughness={0.05} metalness={0.9} emissive="#042a50" emissiveIntensity={0.6} />
    </mesh>
    {/* Vent grilles */}
    {[1.1, -1.1].map((dy, i) => (
      <mesh key={i} position={[0, dy, 0.30]}>
        <boxGeometry args={[0.7, 0.4, 0.03]} />
        <meshStandardMaterial color="#111820" roughness={0.7} metalness={0.5} />
      </mesh>
    ))}
    {/* Status LED */}
    <mesh position={[0.3, 0.6, 0.32]}>
      <sphereGeometry args={[0.04, 8, 6]} />
      <meshBasicMaterial color={getColor(status)} />
    </mesh>
  </group>
);

// ─── HV Power Transformer ───
const TransformerMesh = () => (
  <group>
    {/* Main tank */}
    <mesh castShadow>
      <boxGeometry args={[2.2, 2.6, 1.4]} />
      <meshStandardMaterial color="#2d3845" roughness={0.6} metalness={0.65} />
    </mesh>
    {/* Cooling fins */}
    {[-0.7, -0.35, 0, 0.35, 0.7].map((dx, i) => (
      <mesh key={i} castShadow position={[dx, 0, 0.75]}>
        <boxGeometry args={[0.06, 2.2, 0.12]} />
        <meshStandardMaterial color="#1c2535" roughness={0.7} metalness={0.7} />
      </mesh>
    ))}
    {/* Bushings on top */}
    {[-0.5, 0, 0.5].map((dx, i) => (
      <mesh key={i} castShadow position={[dx, 1.55, 0]}>
        <cylinderGeometry args={[0.12, 0.15, 0.7, 8]} />
        <meshStandardMaterial color="#e8e0d0" roughness={0.3} metalness={0.2} />
      </mesh>
    ))}
  </group>
);

// ─── HVAC Air Handler Unit ───
const HVACMesh = ({ status }) => (
  <group>
    {/* Main unit body */}
    <mesh castShadow>
      <boxGeometry args={[3.8, 1.4, 2.0]} />
      <meshStandardMaterial color="#8a9aaa" roughness={0.45} metalness={0.5} />
    </mesh>
    {/* Intake grille */}
    <mesh position={[1.95, 0, 0]}>
      <boxGeometry args={[0.06, 1.2, 1.8]} />
      <meshStandardMaterial color="#2a3545" roughness={0.8} metalness={0.4} />
    </mesh>
    {/* Fan face */}
    <mesh position={[1.94, 0, 0]}>
      <circleGeometry args={[0.6, 12]} />
      <meshStandardMaterial color="#1a2535" roughness={0.5} metalness={0.7} />
    </mesh>
    {/* Exhaust duct */}
    <mesh castShadow position={[-1.95, 0.3, 0]}>
      <boxGeometry args={[0.08, 0.8, 1.4]} />
      <meshStandardMaterial color="#6a7a8a" roughness={0.5} metalness={0.6} />
    </mesh>
    {/* Refrigerant lines */}
    <mesh position={[0, 0.75, -0.9]} rotation={[0, 0, Math.PI / 2]}>
      <cylinderGeometry args={[0.06, 0.06, 3.2, 6]} />
      <meshStandardMaterial color="#3d4e5f" roughness={0.5} metalness={0.8} />
    </mesh>
    <mesh position={[0, 0.62, -0.9]} rotation={[0, 0, Math.PI / 2]}>
      <cylinderGeometry args={[0.04, 0.04, 3.0, 6]} />
      <meshStandardMaterial color="#2d3e50" roughness={0.5} metalness={0.8} />
    </mesh>
    {/* Control box */}
    <mesh position={[0.8, 0.85, -1.05]}>
      <boxGeometry args={[0.5, 0.4, 0.1]} />
      <meshStandardMaterial color="#1a2535" roughness={0.3} metalness={0.8} />
    </mesh>
    {/* Status indicator */}
    <mesh position={[0.8, 0.92, -1.06]}>
      <sphereGeometry args={[0.04, 8, 6]} />
      <meshBasicMaterial color={getColor(status)} />
    </mesh>
  </group>
);

// ─── Research Instrument Station ───
const ResearchMesh = ({ status }) => (
  <group>
    {/* Bench body */}
    <mesh castShadow position={[0, 0.55, 0]}>
      <boxGeometry args={[2.8, 0.12, 1.2]} />
      <meshStandardMaterial color="#ddd8cc" roughness={0.6} metalness={0.15} />
    </mesh>
    {/* Bench legs */}
    {[[-1.1, -1.1], [-1.1, 1.1], [1.1, -1.1], [1.1, 1.1]].map(([x, z], i) => (
      <mesh key={i} castShadow position={[x * 0.45, 0.25, z * 0.4]}>
        <boxGeometry args={[0.06, 0.5, 0.06]} />
        <meshStandardMaterial color="#5a5a5a" roughness={0.7} metalness={0.4} />
      </mesh>
    ))}
    {/* Monitor stack */}
    <mesh castShadow position={[-0.6, 1.1, 0.35]}>
      <boxGeometry args={[0.8, 0.6, 0.06]} />
      <meshStandardMaterial color="#111820" roughness={0.2} metalness={0.85} />
    </mesh>
    <mesh position={[-0.6, 1.1, 0.38]}>
      <boxGeometry args={[0.7, 0.5, 0.02]} />
      <meshStandardMaterial color="#020d18" roughness={0.05} metalness={0.9} emissive="#041e38" emissiveIntensity={0.8} />
    </mesh>
    {/* Sensor instrument box */}
    <mesh castShadow position={[0.7, 0.75, 0.1]}>
      <boxGeometry args={[0.7, 0.35, 0.6]} />
      <meshStandardMaterial color="#2d3a4a" roughness={0.4} metalness={0.7} />
    </mesh>
    {/* Instrument rack */}
    <mesh castShadow position={[0, 0.62, -0.52]}>
      <boxGeometry args={[2.6, 0.2, 0.04]} />
      <meshStandardMaterial color="#3d4e60" roughness={0.3} metalness={0.8} />
    </mesh>
    {/* Status LEDs */}
    {[0, 1, 2, 3].map(i => (
      <mesh key={i} position={[0.7, 0.82, 0.41 + i * 0.06]}>
        <sphereGeometry args={[0.025, 6, 4]} />
        <meshBasicMaterial color={i === 0 ? getColor(status) : '#1a3a8a'} />
      </mesh>
    ))}
  </group>
);

// ─── Lab Bench / Atmospheric Sampler ───
const LabBenchMesh = () => (
  <group>
    <mesh castShadow position={[0, 0.5, 0]}>
      <boxGeometry args={[2.4, 0.1, 0.9]} />
      <meshStandardMaterial color="#d8d3c8" roughness={0.55} metalness={0.15} />
    </mesh>
    {/* Sample cylinder array */}
    {[-0.7, 0, 0.7].map((dx, i) => (
      <mesh key={i} castShadow position={[dx, 0.85, 0]}>
        <cylinderGeometry args={[0.12, 0.12, 0.6, 10]} />
        <meshStandardMaterial color="#4a5a6a" roughness={0.35} metalness={0.75} />
      </mesh>
    ))}
    {/* Instrument hood */}
    <mesh position={[0, 1.3, -0.3]}>
      <boxGeometry args={[2.2, 0.8, 0.3]} />
      <meshStandardMaterial color="#8a9aaa" roughness={0.4} metalness={0.5} transparent opacity={0.7} />
    </mesh>
    {/* Control interface */}
    <mesh castShadow position={[0.8, 0.65, 0.5]}>
      <boxGeometry args={[0.45, 0.28, 0.06]} />
      <meshStandardMaterial color="#1c2530" roughness={0.3} metalness={0.8} />
    </mesh>
  </group>
);

// ─── Fuel / Storage Tank ───
const FuelTankMesh = ({ status }) => (
  <group>
    {/* Horizontal cylindrical tank */}
    <mesh castShadow rotation={[0, 0, Math.PI / 2]}>
      <cylinderGeometry args={[1.4, 1.4, 5.0, 20]} />
      <meshStandardMaterial color="#6a6258" roughness={0.5} metalness={0.6} />
    </mesh>
    {/* End caps */}
    {[-2.6, 2.6].map((dx, i) => (
      <mesh key={i} castShadow position={[dx, 0, 0]} rotation={[0, 0, Math.PI / 2]}>
        <sphereGeometry args={[1.4, 16, 10, 0, Math.PI * 2, 0, Math.PI / 2]} />
        <meshStandardMaterial color="#5a5248" roughness={0.5} metalness={0.6} />
      </mesh>
    ))}
    {/* Level sight glass */}
    <mesh castShadow position={[1.8, 0.6, 1.42]}>
      <boxGeometry args={[0.08, 1.6, 0.1]} />
      <meshStandardMaterial color="#aaccee" roughness={0.05} metalness={0.3} transparent opacity={0.8} />
    </mesh>
    {/* Piping connections */}
    <mesh castShadow position={[-2.4, -0.8, 0]}>
      <cylinderGeometry args={[0.1, 0.1, 0.6, 8]} />
      <meshStandardMaterial color="#4a4840" roughness={0.6} metalness={0.7} />
    </mesh>
    {/* Support saddles */}
    {[-1.5, 1.5].map((dx, i) => (
      <mesh key={i} receiveShadow position={[dx, -1.5, 0]}>
        <boxGeometry args={[0.6, 0.2, 3.2]} />
        <meshStandardMaterial color="#3d3830" roughness={0.7} metalness={0.5} />
      </mesh>
    ))}
    {/* Status indicator */}
    <mesh position={[2.0, 0.8, 1.43]}>
      <sphereGeometry args={[0.07, 8, 6]} />
      <meshBasicMaterial color={getColor(status)} />
    </mesh>
  </group>
);

// ─── Cooling Radiator ───
const RadiatorMesh = () => (
  <group>
    {/* Frame */}
    <mesh castShadow>
      <boxGeometry args={[0.3, 3.5, 4.0]} />
      <meshStandardMaterial color="#2a3545" roughness={0.6} metalness={0.7} />
    </mesh>
    {/* Fins */}
    {Array.from({ length: 18 }, (_, i) => (
      <mesh key={i} position={[0.18, -1.6 + i * 0.19, 0]}>
        <boxGeometry args={[0.06, 0.14, 3.7]} />
        <meshStandardMaterial color="#1c2535" roughness={0.5} metalness={0.8} />
      </mesh>
    ))}
    {/* Header pipes */}
    {[-1.8, 1.8].map((dz, i) => (
      <mesh key={i} position={[0.1, 0, dz]}>
        <cylinderGeometry args={[0.14, 0.14, 3.5, 8]} />
        <meshStandardMaterial color="#3a4a5a" roughness={0.5} metalness={0.75} />
      </mesh>
    ))}
  </group>
);

// ─── Comms RF Shelter ───
const CommsMesh = ({ status }) => (
  <group>
    {/* Shelter box */}
    <mesh castShadow>
      <boxGeometry args={[2.2, 2.0, 1.6]} />
      <meshStandardMaterial color="#2d3b4a" roughness={0.5} metalness={0.6} />
    </mesh>
    {/* Equipment bay door */}
    <mesh position={[0, 0, 0.82]}>
      <boxGeometry args={[1.8, 1.6, 0.06]} />
      <meshStandardMaterial color="#232f3e" roughness={0.3} metalness={0.75} />
    </mesh>
    {/* RF equipment panel */}
    <mesh position={[0, 0.3, 0.86]}>
      <boxGeometry args={[1.4, 0.8, 0.04]} />
      <meshStandardMaterial color="#111820" roughness={0.2} metalness={0.85} emissive="#040c18" emissiveIntensity={0.3} />
    </mesh>
    {/* Antenna stub */}
    <mesh castShadow position={[0.6, 1.2, 0]}>
      <cylinderGeometry args={[0.05, 0.07, 1.4, 8]} />
      <meshStandardMaterial color={getColor(status)} roughness={0.4} metalness={0.8} />
    </mesh>
    {/* Status */}
    <mesh position={[0.5, 0.6, 0.87]}>
      <sphereGeometry args={[0.05, 8, 6]} />
      <meshBasicMaterial color={getColor(status)} />
    </mesh>
  </group>
);

// ─── Server / Telemetry Rack ───
const ServerRackMesh = ({ status }) => (
  <group>
    {/* Rack enclosure */}
    <mesh castShadow>
      <boxGeometry args={[0.6, 2.6, 0.9]} />
      <meshStandardMaterial color="#1a2030" roughness={0.3} metalness={0.85} />
    </mesh>
    {/* Rack door */}
    <mesh position={[0, 0, 0.47]}>
      <boxGeometry args={[0.55, 2.5, 0.04]} />
      <meshStandardMaterial color="#202a3a" roughness={0.2} metalness={0.9} />
    </mesh>
    {/* 1U server units */}
    {Array.from({ length: 10 }, (_, i) => (
      <group key={i} position={[0, -1.0 + i * 0.22, 0.48]}>
        <mesh>
          <boxGeometry args={[0.48, 0.16, 0.06]} />
          <meshStandardMaterial color="#151e2d" roughness={0.3} metalness={0.8} />
        </mesh>
        <mesh position={[0.18, 0, 0.04]}>
          <sphereGeometry args={[0.025, 6, 4]} />
          <meshBasicMaterial color={i % 3 === 0 ? getColor(status) : '#0a2a50'} />
        </mesh>
      </group>
    ))}
    {/* Patch panel top */}
    <mesh position={[0, 1.3, 0.47]}>
      <boxGeometry args={[0.5, 0.14, 0.08]} />
      <meshStandardMaterial color="#1c2840" roughness={0.4} metalness={0.7} />
    </mesh>
  </group>
);

// ─── Cryo Freezer ───
const FreezerMesh = ({ status }) => (
  <group>
    {/* Main insulated cabinet */}
    <mesh castShadow>
      <boxGeometry args={[1.8, 2.8, 1.2]} />
      <meshStandardMaterial color="#d0dce8" roughness={0.55} metalness={0.2} />
    </mesh>
    {/* Door gasket frame */}
    <mesh position={[0, 0, 0.62]}>
      <boxGeometry args={[1.6, 2.6, 0.06]} />
      <meshStandardMaterial color="#b8c8d8" roughness={0.4} metalness={0.25} />
    </mesh>
    {/* Handle */}
    <mesh position={[0.6, 0, 0.68]}>
      <boxGeometry args={[0.06, 0.6, 0.06]} />
      <meshStandardMaterial color="#4a5a6a" roughness={0.4} metalness={0.7} />
    </mesh>
    {/* Temp display */}
    <mesh position={[-0.5, 1.2, 0.66]}>
      <boxGeometry args={[0.5, 0.22, 0.03]} />
      <meshStandardMaterial color="#041520" roughness={0.05} metalness={0.9} emissive="#002838" emissiveIntensity={0.7} />
    </mesh>
    {/* Compressor unit bottom */}
    <mesh castShadow position={[0, -1.55, -0.1]}>
      <boxGeometry args={[1.6, 0.2, 1.0]} />
      <meshStandardMaterial color="#7a8a9a" roughness={0.6} metalness={0.4} />
    </mesh>
    {/* Status */}
    <mesh position={[-0.5, 1.2, 0.68]}>
      <sphereGeometry args={[0.04, 8, 6]} />
      <meshBasicMaterial color={getColor(status)} />
    </mesh>
  </group>
);

// ─── Command Console ───
const ControlPanelMesh = ({ status }) => (
  <group>
    {/* Main console desk */}
    <mesh castShadow position={[0, 0.4, 0]}>
      <boxGeometry args={[4.0, 0.12, 1.4]} />
      <meshStandardMaterial color="#c8c0b0" roughness={0.55} metalness={0.2} />
    </mesh>
    {/* Front panel */}
    <mesh castShadow position={[0, 0.2, 0.72]}>
      <boxGeometry args={[4.0, 0.4, 0.08]} />
      <meshStandardMaterial color="#2d3545" roughness={0.4} metalness={0.7} />
    </mesh>
    {/* Monitor array — 3 screens */}
    {[-1.3, 0, 1.3].map((dx, i) => (
      <group key={i} position={[dx, 1.0, 0.45]}>
        <mesh castShadow>
          <boxGeometry args={[1.0, 0.65, 0.06]} />
          <meshStandardMaterial color="#111820" roughness={0.2} metalness={0.85} />
        </mesh>
        <mesh position={[0, 0, 0.04]}>
          <boxGeometry args={[0.9, 0.56, 0.02]} />
          <meshStandardMaterial
            color="#020e1c"
            roughness={0.05}
            metalness={0.9}
            emissive={i === 1 ? '#0c2c0c' : '#0a1a30'}
            emissiveIntensity={0.7}
          />
        </mesh>
        {/* Monitor base */}
        <mesh position={[0, -0.45, -0.1]}>
          <boxGeometry args={[0.3, 0.1, 0.2]} />
          <meshStandardMaterial color="#1a2030" roughness={0.5} metalness={0.7} />
        </mesh>
      </group>
    ))}
    {/* Control buttons strip */}
    {Array.from({ length: 8 }, (_, i) => (
      <mesh key={i} position={[-1.4 + i * 0.4, 0.5, 0.72]}>
        <cylinderGeometry args={[0.06, 0.06, 0.04, 8]} />
        <meshBasicMaterial color={i < 2 ? '#b5382b' : i < 5 ? '#c87a1a' : '#2d7a4a'} />
      </mesh>
    ))}
  </group>
);

// ─── Dispatch table ───
const ASSET_MESH_MAP = {
  GENERATOR:   DieselGeneratorMesh,
  BATTERY:     BatteryRackMesh,
  INVERTER:    InverterMesh,
  TRANSFORMER: TransformerMesh,
  HVAC:        HVACMesh,
  RESEARCH:    ResearchMesh,
  LAB_BENCH:   LabBenchMesh,
  FUEL_TANK:   FuelTankMesh,
  STORAGE:     FuelTankMesh,
  RADIATOR:    RadiatorMesh,
  COMMS:       CommsMesh,
  SERVER_RACK: ServerRackMesh,
  FREEZER:     FreezerMesh,
  CONTROL:     ControlPanelMesh
};

// ─── Main exported component ───
export const InternalAssetMarker = ({
  id,
  type = 'GENERATOR',
  label = 'ASSET',
  position = [0, 0, 0],
  status = 'RUNNING',
  isHighlighted = false,
  isSelected = false,
  showLabel = true,
  onClick
}) => {
  const groupRef = useRef();
  const col = getColor(status);

  useFrame(({ clock }) => {
    if (!groupRef.current) return;
    if (isHighlighted || isSelected) {
      const s = 1 + Math.sin(clock.getElapsedTime() * 2.5) * 0.015;
      groupRef.current.scale.setScalar(s);
    } else {
      groupRef.current.scale.setScalar(1);
    }
  });

  const MeshComponent = ASSET_MESH_MAP[type] || ASSET_MESH_MAP.CONTROL;

  const handleClick = (e) => {
    e.stopPropagation();
    if (onClick) onClick(id);
  };

  return (
    <group ref={groupRef} position={position} onClick={handleClick}>
      {/* Realistic 3D equipment model */}
      <MeshComponent status={status} />

      {/* Floor shadow footprint */}
      <mesh
        position={[0, -0.02, 0]}
        rotation={[-Math.PI / 2, 0, 0]}
        renderOrder={2}
        raycast={() => null}
      >
        <planeGeometry args={[4.0, 3.0]} />
        <meshBasicMaterial
          color="#000000"
          transparent
          opacity={0.08}
          depthWrite={false}
        />
      </mesh>

      {/* Highlight selection ring */}
      {(isHighlighted || isSelected) && (
        <mesh
          position={[0, 0.02, 0]}
          rotation={[-Math.PI / 2, 0, 0]}
          renderOrder={30}
        >
          <ringGeometry args={[1.8, 2.1, 32]} />
          <meshBasicMaterial
            color={isHighlighted ? '#b65a1f' : col}
            transparent
            opacity={0.7}
            depthWrite={false}
            side={THREE.DoubleSide}
          />
        </mesh>
      )}

      {/* Subtle status floor glow */}
      <mesh
        position={[0, 0.01, 0]}
        rotation={[-Math.PI / 2, 0, 0]}
        renderOrder={1}
        raycast={() => null}
      >
        <circleGeometry args={[1.4, 16]} />
        <meshBasicMaterial
          color={col}
          transparent
          opacity={status === 'CRITICAL' ? 0.18 : status === 'WARNING' ? 0.12 : 0.06}
          depthWrite={false}
        />
      </mesh>

      {/* HTML label — compact and clean */}
      {showLabel && (
        <Html
          position={[0, 3.2, 0]}
          center
          distanceFactor={38}
          zIndexRange={[60, 0]}
          occlude={false}
        >
          <div style={{
            background: 'rgba(18,22,30,0.92)',
            border: `1px solid ${isHighlighted ? '#b65a1f' : col}`,
            borderRadius: '2px',
            padding: '3px 8px',
            fontFamily: 'JetBrains Mono, monospace',
            fontSize: '10px',
            fontWeight: 700,
            letterSpacing: '0.06em',
            color: '#f0ece4',
            whiteSpace: 'nowrap',
            pointerEvents: 'none',
            boxShadow: '0 2px 8px rgba(0,0,0,0.4)',
            display: 'flex',
            alignItems: 'center',
            gap: '5px',
            lineHeight: 1
          }}>
            <span style={{
              width: '6px',
              height: '6px',
              borderRadius: '50%',
              background: col,
              flexShrink: 0,
              boxShadow: `0 0 4px ${col}`
            }} />
            <span>{label}</span>
          </div>
        </Html>
      )}
    </group>
  );
};

export default InternalAssetMarker;
