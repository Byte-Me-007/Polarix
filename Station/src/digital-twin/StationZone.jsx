import React, { useRef } from 'react';
import { Html } from '@react-three/drei';

export const StationZone = ({ zone, showLabels = true }) => {
  const meshRef = useRef();

  const [px, py, pz] = zone.position;
  const [sx, sy, sz] = zone.size;

  // Stilt pillars count and placement based on width & depth
  const stiltRadius = 0.12;
  const stiltHeight = py + 0.2; // from ground y=0 to module bottom
  const stiltY = stiltHeight / 2;

  // Calculate 4 corner stilt positions
  const cornerOffsets = [
    [-sx * 0.42, stiltY, -sz * 0.42],
    [sx * 0.42, stiltY, -sz * 0.42],
    [-sx * 0.42, stiltY, sz * 0.42],
    [sx * 0.42, stiltY, sz * 0.42]
  ];

  return (
    <group position={[px, py, pz]}>
      {/* Module Building Geometry */}
      {zone.shape === 'cylinder' ? (
        <group>
          {/* Main communications radome/mast */}
          <mesh castShadow receiveShadow position={[0, sy / 2, 0]}>
            <cylinderGeometry args={[sx * 0.6, sx * 0.8, sy, 24]} />
            <meshStandardMaterial 
              color={zone.color || '#b65a1f'} 
              roughness={0.4} 
              metalness={0.2} 
            />
          </mesh>
          {/* Radome Top Dome */}
          <mesh position={[0, sy + 0.2, 0]}>
            <sphereGeometry args={[sx * 0.62, 24, 16, 0, Math.PI * 2, 0, Math.PI * 0.5]} />
            <meshStandardMaterial color="#f8f6f0" roughness={0.3} metalness={0.1} />
          </mesh>
        </group>
      ) : (
        <group>
          {/* Main rectangular module structure */}
          <mesh castShadow receiveShadow position={[0, sy / 2, 0]}>
            <boxGeometry args={[sx, sy, sz]} />
            <meshStandardMaterial
              color={zone.color || '#e8e4dc'}
              roughness={0.65}
              metalness={0.1}
            />
          </mesh>

          {/* Roof solar / mechanical strip accent */}
          <mesh position={[0, sy + 0.04, 0]}>
            <boxGeometry args={[sx * 0.88, 0.06, sz * 0.88]} />
            <meshStandardMaterial
              color="#5d6672"
              roughness={0.3}
              metalness={0.6}
            />
          </mesh>

          {/* Under-structure Pilings / Elevated Stilts (ground y=0 up to module) */}
          {cornerOffsets.map(([cx, cy, cz], idx) => (
            <mesh key={idx} position={[cx, -stiltY, cz]}>
              <cylinderGeometry args={[stiltRadius, stiltRadius, stiltHeight, 8]} />
              <meshStandardMaterial color="#4b525d" roughness={0.8} metalness={0.4} />
            </mesh>
          ))}
        </group>
      )}

      {/* Floating 3D Area Name Label */}
      {showLabels && (
        <Html
          position={[0, sy + (zone.shape === 'cylinder' ? 1.0 : 0.6), 0]}
          center
          distanceFactor={28}
          zIndexRange={[100, 0]}
        >
          <div
            style={{
              background: 'rgba(25, 28, 32, 0.85)',
              color: '#f8f6f0',
              padding: '2px 7px',
              borderRadius: '2px',
              fontFamily: 'JetBrains Mono, monospace',
              fontSize: '11px',
              fontWeight: 700,
              letterSpacing: '0.08em',
              whiteSpace: 'nowrap',
              pointerEvents: 'none',
              border: '1px solid rgba(226, 221, 212, 0.3)',
              boxShadow: '0 2px 6px rgba(0,0,0,0.15)',
              display: 'flex',
              alignItems: 'center',
              gap: '4px'
            }}
          >
            <span style={{ width: '4px', height: '4px', borderRadius: '50%', background: '#b65a1f' }} />
            <span>{zone.name}</span>
          </div>
        </Html>
      )}
    </group>
  );
};

export default StationZone;
