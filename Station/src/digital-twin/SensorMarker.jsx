import React, { useState, useRef } from 'react';
import { useFrame } from '@react-three/fiber';
import { Html } from '@react-three/drei';

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

  // Pulse animation for critical sensors or currently selected sensor
  useFrame(({ clock }) => {
    const t = clock.getElapsedTime();
    if (beaconRef.current && (isCritical || isSelected)) {
      const scale = 1 + Math.sin(t * 4.5) * (isCritical ? 0.22 : 0.15);
      beaconRef.current.scale.set(scale, scale, scale);
    }
    if (ringRef.current) {
      ringRef.current.rotation.z = t * 0.5;
    }
  });

  // Keep stored sensor position intact for data/inspection,
  // but add small visual Y elevation offset so marker is prominently visible
  // above roofs and never hidden inside building geometry.
  const visualOffset = 0.85;
  const visualX = sensor.x || 0;
  const visualY = (sensor.y || 0) + visualOffset;
  const visualZ = sensor.z || 0;

  return (
    <group position={[visualX, visualY, visualZ]}>
      {/* ----------------------------------------------------------- */}
      {/* 1. VERTICAL INDICATOR STEM (Anchors down to mounting plane) */}
      {/* ----------------------------------------------------------- */}
      <mesh position={[0, -visualOffset / 2, 0]}>
        <cylinderGeometry args={[0.025, 0.025, visualOffset, 8]} />
        <meshBasicMaterial color="#2d333b" />
      </mesh>

      {/* Surface Mounting Foot Ring */}
      <mesh position={[0, -visualOffset, 0]} rotation={[-Math.PI / 2, 0, 0]}>
        <ringGeometry args={[0.08, 0.16, 12]} />
        <meshBasicMaterial color="#3d444e" side={2} />
      </mesh>

      {/* ----------------------------------------------------------- */}
      {/* 2. CIRCULAR STATUS RING (Horizontal instrumentation ring)   */}
      {/* ----------------------------------------------------------- */}
      <mesh ref={ringRef} rotation={[-Math.PI / 2, 0, 0]}>
        <ringGeometry args={[0.32, 0.40, 24]} />
        <meshBasicMaterial color={color} side={2} transparent opacity={0.85} />
      </mesh>

      {/* Outer Selected Ring */}
      {isSelected && (
        <mesh rotation={[-Math.PI / 2, 0, 0]}>
          <ringGeometry args={[0.48, 0.56, 32]} />
          <meshBasicMaterial color="#b65a1f" side={2} />
        </mesh>
      )}

      {/* ----------------------------------------------------------- */}
      {/* 3. LUMINOUS BEACON POINT (Clickable instrument head)       */}
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
        <sphereGeometry args={[hovered || isSelected ? 0.28 : 0.22, 16, 16]} />
        <meshStandardMaterial
          color={color}
          emissive={color}
          emissiveIntensity={hovered || isSelected ? 0.7 : 0.4}
          roughness={0.25}
          metalness={0.3}
        />
      </mesh>

      {/* ----------------------------------------------------------- */}
      {/* 4. FLOATING SENSOR IDENTIFIER TAG                           */}
      {/* ----------------------------------------------------------- */}
      {(hovered || isSelected || isCritical) && (
        <Html
          position={[0, 0.52, 0]}
          center
          distanceFactor={22}
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
              borderRadius: '2px',
              padding: '3px 7px',
              boxShadow: '0 4px 12px rgba(0,0,0,0.15)',
              fontFamily: 'JetBrains Mono, monospace',
              fontSize: '10px',
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
                gap: '4px',
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
            <div style={{ fontSize: '9px', color: '#4b525d', fontWeight: 600 }}>
              {sensor.value} {sensor.unit}
            </div>
          </div>
        </Html>
      )}
    </group>
  );
};

export default SensorMarker;
