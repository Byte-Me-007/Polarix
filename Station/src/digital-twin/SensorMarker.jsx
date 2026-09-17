import React, { useState, useRef } from 'react';
import { useFrame } from '@react-three/fiber';
import { Html } from '@react-three/drei';

// Helper to determine the roof/surface elevation at any station coordinate (x, z)
// Ensures visual markers always hover visibly above structures without being occluded.
const getSurfaceElevation = (x, z) => {
  // Main Building footprint: x in [-11.5, 11.5], z in [-7.5, 7.5]
  if (Math.abs(x) <= 11.5 && Math.abs(z) <= 7.5) return 5.8;
  // Research footprint: x in [15.5, 30.5], z in [-6.5, 6.5]
  if (x >= 15.5 && x <= 30.5 && Math.abs(z) <= 6.5) return 5.4;
  // Energy footprint: x in [-8.5, 8.5], z in [-24.5, -11.5]
  if (Math.abs(x) <= 8.5 && z >= -24.5 && z <= -11.5) return 5.0;
  // Generator footprint: x in [-25.0, -11.0], z in [-24.5, -11.5]
  if (x >= -25.0 && x <= -11.0 && z >= -24.5 && z <= -11.5) return 4.8;
  // Storage footprint: x in [10.5, 25.5], z in [-24.5, -11.5]
  if (x >= 10.5 && x <= 25.5 && z >= -24.5 && z <= -11.5) return 4.6;
  // Communications base shelter footprint: x in [-4.5, 4.5], z in [-36.5, -27.5]
  if (Math.abs(x) <= 4.5 && z >= -36.5 && z <= -27.5) return 4.6;
  // Connecting Corridors:
  if (x >= 11.0 && x <= 16.0 && Math.abs(z) <= 2.0) return 4.2;
  if (Math.abs(x) <= 2.0 && z >= -12.0 && z <= -7.0) return 4.2;
  // Natural Antarctic ground/permafrost datum
  return 0.0;
};

export const SensorMarker = ({ sensor, isSelected, onSelect }) => {
  const [hovered, setHovered] = useState(false);
  const beaconRef = useRef();
  const ringRef = useRef();

  // Strict visual color language from POLARIS design system
  // NORMAL: muted sage, WARNING: amber, CRITICAL: restrained red, OFFLINE/UNKNOWN: neutral gray
  const getStatusColor = (status) => {
    switch (status?.toUpperCase()) {
      case 'NORMAL': return '#3f6e4a';   // Muted sage
      case 'WARNING': return '#b26814';  // Restrained amber
      case 'CRITICAL': return '#b5382b'; // Restrained red
      case 'OFFLINE': return '#5d6672';  // Neutral gray
      default: return '#727b87';
    }
  };

  const color = getStatusColor(sensor.status);
  const isCritical = sensor.status?.toUpperCase() === 'CRITICAL';

  // Subtle pulse animation for critical sensors or active selection
  useFrame(({ clock }) => {
    const t = clock.getElapsedTime();
    if (beaconRef.current && (isCritical || isSelected)) {
      const scale = 1 + Math.sin(t * 4.2) * (isCritical ? 0.22 : 0.15);
      beaconRef.current.scale.set(scale, scale, scale);
    }
    if (ringRef.current) {
      ringRef.current.rotation.z = t * 0.4;
    }
  });

  // Calculate guaranteed clear visual altitude above buildings
  const rawX = sensor.x || 0;
  const rawY = sensor.y || 0;
  const rawZ = sensor.z || 0;

  const surfaceY = getSurfaceElevation(rawX, rawZ);
  const anchorY = Math.max(rawY, surfaceY);
  const visualY = anchorY + 0.95;
  const stemHeight = visualY - rawY;

  return (
    <group position={[rawX, visualY, rawZ]}>
      {/* ----------------------------------------------------------- */}
      {/* 1. VERTICAL INDICATOR STEM (Anchors down to mounting plane) */}
      {/* ----------------------------------------------------------- */}
      <mesh position={[0, -stemHeight / 2, 0]}>
        <cylinderGeometry args={[0.035, 0.035, stemHeight, 8]} />
        <meshBasicMaterial color="#2d333b" />
      </mesh>

      {/* Surface Mounting Foot Collar */}
      <mesh position={[0, -stemHeight, 0]} rotation={[-Math.PI / 2, 0, 0]}>
        <ringGeometry args={[0.12, 0.28, 16]} />
        <meshBasicMaterial color="#383f4a" side={2} />
      </mesh>

      {/* ----------------------------------------------------------- */}
      {/* 2. CIRCULAR INSTRUMENTATION STATUS RING                     */}
      {/* ----------------------------------------------------------- */}
      <mesh ref={ringRef} rotation={[-Math.PI / 2, 0, 0]}>
        <ringGeometry args={[0.52, 0.68, 28]} />
        <meshBasicMaterial color={color} side={2} transparent opacity={0.88} />
      </mesh>

      {/* Outer Selected Ring */}
      {isSelected && (
        <mesh rotation={[-Math.PI / 2, 0, 0]}>
          <ringGeometry args={[0.82, 0.98, 32]} />
          <meshBasicMaterial color="#b65a1f" side={2} />
        </mesh>
      )}

      {/* ----------------------------------------------------------- */}
      {/* 3. ILLUMINATED BEACON POINT (Clickable instrument head)     */}
      {/* ----------------------------------------------------------- */}
      <mesh
        ref={beaconRef}
        onClick={(e) => {
          e.stopPropagation();
          onSelect(sensor); // Passes the pristine source sensor coordinate
        }}
        onPointerOver={(e) => {
          e.stopPropagation();
          setHovered(true);
          document.body.style.cursor = 'pointer';
        }}
        onPointerOut={(e) => {
          e.stopPropagation();
          setHovered(false);
          document.body.style.cursor = 'default';
        }}
      >
        <sphereGeometry args={[hovered || isSelected ? 0.48 : 0.36, 16, 16]} />
        <meshStandardMaterial
          color={color}
          emissive={color}
          emissiveIntensity={hovered || isSelected ? 0.75 : 0.45}
          roughness={0.25}
          metalness={0.3}
        />
      </mesh>

      {/* ----------------------------------------------------------- */}
      {/* 4. SENSOR IDENTIFIER TAG (Shown on Hover, Select, Critical) */}
      {/* ----------------------------------------------------------- */}
      {(hovered || isSelected || isCritical) && (
        <Html
          position={[0, 0.85, 0]}
          center
          distanceFactor={45}
          zIndexRange={[300, 0]}
        >
          <div
            onClick={(e) => {
              e.stopPropagation();
              onSelect(sensor);
            }}
            style={{
              background: '#ffffff',
              border: `1.5px solid ${isSelected ? '#b65a1f' : color}`,
              borderRadius: '3px',
              padding: '3px 8px',
              boxShadow: '0 4px 12px rgba(0,0,0,0.18)',
              fontFamily: 'JetBrains Mono, monospace',
              fontSize: '11px',
              whiteSpace: 'nowrap',
              pointerEvents: 'auto',
              cursor: 'pointer',
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
              lineHeight: 1.25
            }}
          >
            <div
              style={{
                fontWeight: 700,
                color: '#191c20',
                display: 'flex',
                alignItems: 'center',
                gap: '5px',
                letterSpacing: '0.04em'
              }}
            >
              <span
                style={{
                  width: '6px',
                  height: '6px',
                  borderRadius: '50%',
                  background: color
                }}
              />
              <span>{sensor.id}</span>
            </div>
            <div style={{ fontSize: '10px', color: '#4b525d', fontWeight: 600 }}>
              {sensor.value} {sensor.unit}
            </div>
          </div>
        </Html>
      )}
    </group>
  );
};

export default SensorMarker;
