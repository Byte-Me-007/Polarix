import React, { useState, useRef } from 'react';
import { useFrame } from '@react-three/fiber';
import { Html } from '@react-three/drei';

export const SensorMarker = ({ sensor, isSelected, onSelect }) => {
  const [hovered, setHovered] = useState(false);
  const beaconRef = useRef();

  const getStatusColor = (status) => {
    switch (status?.toUpperCase()) {
      case 'NORMAL': return '#3f6e4a'; // Muted sage
      case 'WARNING': return '#b26814'; // Restrained amber
      case 'CRITICAL': return '#b5382b'; // Restrained red
      case 'OFFLINE': return '#5d6672'; // Neutral gray
      default: return '#727b87';
    }
  };

  const color = getStatusColor(sensor.status);
  const isCritical = sensor.status?.toUpperCase() === 'CRITICAL';

  // Subtle beacon pulse animation for critical / active sensors
  useFrame(({ clock }) => {
    if (beaconRef.current && isCritical) {
      const t = clock.getElapsedTime();
      const scale = 1 + Math.sin(t * 5) * 0.25;
      beaconRef.current.scale.set(scale, scale, scale);
    }
  });

  const position = [sensor.x || 0, sensor.y || 0, sensor.z || 0];

  return (
    <group position={position}>
      {/* Sensor Pin Stem (connecting down to mounting surface) */}
      <mesh position={[0, -0.25, 0]}>
        <cylinderGeometry args={[0.03, 0.03, 0.5, 8]} />
        <meshBasicMaterial color="#191c20" />
      </mesh>

      {/* Main Sensor Beacon Sphere */}
      <mesh
        ref={beaconRef}
        onClick={(e) => {
          e.stopPropagation();
          onSelect(sensor);
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
        <sphereGeometry args={[hovered || isSelected ? 0.32 : 0.24, 16, 16]} />
        <meshStandardMaterial
          color={color}
          emissive={color}
          emissiveIntensity={hovered || isSelected ? 0.6 : 0.3}
          roughness={0.2}
          metalness={0.4}
        />
      </mesh>

      {/* Selected Indicator Ring */}
      {isSelected && (
        <mesh rotation={[-Math.PI / 2, 0, 0]}>
          <ringGeometry args={[0.38, 0.46, 24]} />
          <meshBasicMaterial color="#b65a1f" side={2} />
        </mesh>
      )}

      {/* Hover & Permanent Technical Tag */}
      {(hovered || isSelected || isCritical) && (
        <Html
          position={[0, 0.45, 0]}
          center
          distanceFactor={22}
          zIndexRange={[200, 0]}
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
              padding: '2px 6px',
              boxShadow: '0 4px 10px rgba(0,0,0,0.12)',
              fontFamily: 'JetBrains Mono, monospace',
              fontSize: '10px',
              whiteSpace: 'nowrap',
              pointerEvents: 'auto',
              cursor: 'pointer',
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
              lineHeight: 1.2
            }}
          >
            <div style={{ fontWeight: 700, color: '#191c20', display: 'flex', alignItems: 'center', gap: '3px' }}>
              <span style={{ width: '5px', height: '5px', borderRadius: '50%', background: color }} />
              <span>{sensor.id}</span>
            </div>
            <div style={{ fontSize: '9px', color: '#4b525d' }}>
              {sensor.value} {sensor.unit}
            </div>
          </div>
        </Html>
      )}
    </group>
  );
};

export default SensorMarker;
