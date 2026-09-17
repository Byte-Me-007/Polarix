import React from 'react';
import { StationZone } from './StationZone';

export const StationModel = ({ station, showLabels = true }) => {
  const zones = station?.digitalTwin?.zones || [];

  return (
    <group name="station-model-root">
      {/* ------------------------------------------------------------- */}
      {/* 1. ANTARCTIC TERRAIN & PERMAFROST GRID DATUM                  */}
      {/* ------------------------------------------------------------- */}
      {/* Packed Snow & Ice Ground Plane */}
      <mesh receiveShadow rotation={[-Math.PI / 2, 0, 0]} position={[0, -0.05, -2]}>
        <planeGeometry args={[80, 80, 1, 1]} />
        <meshStandardMaterial 
          color="#f4f1ea" 
          roughness={0.92} 
          metalness={0.04} 
        />
      </mesh>

      {/* Coordinate Survey Grid on Snow Surface */}
      <gridHelper 
        args={[70, 35, '#d3cbc0', '#e9e5dc']} 
        position={[0, 0.01, -2]} 
      />

      {/* ------------------------------------------------------------- */}
      {/* 2. SPATIAL STATION MODULES (6 Required Zones)                */}
      {/* ------------------------------------------------------------- */}
      {zones.map((zone) => (
        <StationZone 
          key={zone.id} 
          zone={zone} 
          showLabels={showLabels} 
        />
      ))}

      {/* ------------------------------------------------------------- */}
      {/* 3. INTER-MODULE CONNECTING CORRIDORS & WALKWAYS              */}
      {/* ------------------------------------------------------------- */}

      {/* Corridors are narrower than main buildings, elevated on stilts, */}
      {/* with intentional expansion gaps revealing the ground below.    */}

      {/* Corridor 1: MAIN BUILDING ↔ RESEARCH (East corridor) */}
      <group position={[6.25, 1.5, 0]}>
        {/* Enclosed tubular breezeway body */}
        <mesh castShadow receiveShadow>
          <boxGeometry args={[1.3, 1.7, 1.7]} />
          <meshStandardMaterial color="#ded7cc" roughness={0.6} metalness={0.2} />
        </mesh>
        {/* Exterior expansion boot collar */}
        <mesh position={[0, 0, 0]}>
          <boxGeometry args={[1.34, 1.76, 1.76]} />
          <meshStandardMaterial color="#3d444e" roughness={0.7} metalness={0.4} />
        </mesh>
        {/* Stilts supporting corridor */}
        <mesh position={[0, -0.9, 0]}>
          <cylinderGeometry args={[0.08, 0.08, 1.2, 8]} />
          <meshStandardMaterial color="#333842" roughness={0.7} metalness={0.5} />
        </mesh>
      </group>

      {/* Corridor 2: MAIN BUILDING ↔ ENERGY (North spine corridor) */}
      <group position={[0, 1.5, -4.1]}>
        {/* Enclosed central breezeway body */}
        <mesh castShadow receiveShadow>
          <boxGeometry args={[2.0, 1.8, 1.4]} />
          <meshStandardMaterial color="#ded7cc" roughness={0.6} metalness={0.2} />
        </mesh>
        {/* Roof trim collar */}
        <mesh position={[0, 0.95, 0]}>
          <boxGeometry args={[2.08, 0.1, 1.48]} />
          <meshStandardMaterial color="#3d444e" roughness={0.7} metalness={0.4} />
        </mesh>
        {/* Stilts under spine corridor */}
        {[-0.6, 0.6].map((sx, i) => (
          <mesh key={`spine-stilt-${i}`} position={[sx, -0.95, 0]}>
            <cylinderGeometry args={[0.08, 0.08, 1.1, 8]} />
            <meshStandardMaterial color="#333842" roughness={0.7} metalness={0.5} />
          </mesh>
        ))}
      </group>

      {/* Corridor 3: ENERGY ↔ GENERATOR (West utility breezeway) */}
      <group position={[-4.375, 1.4, -7.2]}>
        <mesh castShadow receiveShadow>
          <boxGeometry args={[2.9, 1.6, 1.6]} />
          <meshStandardMaterial color="#d4ccc0" roughness={0.65} metalness={0.2} />
        </mesh>
        {/* Expansion joint bands */}
        {[-0.9, 0.9].map((bx, i) => (
          <mesh key={`gen-band-${i}`} position={[bx, 0, 0]}>
            <boxGeometry args={[0.18, 1.66, 1.66]} />
            <meshStandardMaterial color="#383e47" roughness={0.8} />
          </mesh>
        ))}
        {/* Stilts */}
        <mesh position={[0, -0.9, 0]}>
          <cylinderGeometry args={[0.08, 0.08, 1.0, 8]} />
          <meshStandardMaterial color="#333842" roughness={0.7} metalness={0.5} />
        </mesh>
      </group>

      {/* Corridor 4: ENERGY ↔ STORAGE (East logistics breezeway) */}
      <group position={[4.25, 1.35, -7.2]}>
        <mesh castShadow receiveShadow>
          <boxGeometry args={[2.6, 1.6, 1.6]} />
          <meshStandardMaterial color="#d4ccc0" roughness={0.65} metalness={0.2} />
        </mesh>
        {/* Expansion joint bands */}
        {[-0.8, 0.8].map((bx, i) => (
          <mesh key={`stor-band-${i}`} position={[bx, 0, 0]}>
            <boxGeometry args={[0.18, 1.66, 1.66]} />
            <meshStandardMaterial color="#383e47" roughness={0.8} />
          </mesh>
        ))}
        {/* Stilts */}
        <mesh position={[0, -0.9, 0]}>
          <cylinderGeometry args={[0.08, 0.08, 0.9, 8]} />
          <meshStandardMaterial color="#333842" roughness={0.7} metalness={0.5} />
        </mesh>
      </group>

      {/* Corridor 5: ENERGY ↔ COMMUNICATIONS (North utility bridge / cable walkway) */}
      <group position={[0, 0.95, -10.9]}>
        {/* Gangway platform floor */}
        <mesh castShadow receiveShadow>
          <boxGeometry args={[1.3, 0.25, 2.6]} />
          <meshStandardMaterial color="#424954" roughness={0.8} metalness={0.4} />
        </mesh>
        {/* Safety handrail stanchions */}
        {[-0.6, 0.6].map((rx, i) => (
          <mesh key={`rail-${i}`} position={[rx, 0.45, 0]}>
            <boxGeometry args={[0.04, 0.65, 2.5]} />
            <meshStandardMaterial color="#b65a1f" roughness={0.4} metalness={0.5} />
          </mesh>
        ))}
        {/* Twin high-voltage & telemetry conduits running alongside */}
        {[-0.45, 0.45].map((cx, i) => (
          <mesh key={`cable-${i}`} position={[cx, -0.2, 0]} rotation={[Math.PI / 2, 0, 0]}>
            <cylinderGeometry args={[0.05, 0.05, 2.6, 8]} />
            <meshStandardMaterial color="#1a1c20" roughness={0.5} />
          </mesh>
        ))}
        {/* Stilts under comms bridge */}
        <mesh position={[0, -0.5, 0]}>
          <cylinderGeometry args={[0.08, 0.08, 0.8, 8]} />
          <meshStandardMaterial color="#333842" roughness={0.7} metalness={0.5} />
        </mesh>
      </group>

      {/* ------------------------------------------------------------- */}
      {/* 4. UTILITY PIPES & INFRASTRUCTURE (Generator ↔ Main & Energy) */}
      {/* ------------------------------------------------------------- */}
      {/* Heavy insulated heating & fuel conduits running from Generator */}
      <group position={[-6.8, 0.45, -3.8]}>
        {/* Pipe run 1: Parallel insulated conduit lines */}
        <mesh position={[0, 0, 0]} rotation={[Math.PI / 2, 0, 0]}>
          <cylinderGeometry args={[0.07, 0.07, 4.8, 12]} />
          <meshStandardMaterial color="#6a7280" roughness={0.4} metalness={0.6} />
        </mesh>
        <mesh position={[0.2, 0, 0]} rotation={[Math.PI / 2, 0, 0]}>
          <cylinderGeometry args={[0.05, 0.05, 4.8, 12]} />
          <meshStandardMaterial color="#b65a1f" roughness={0.4} metalness={0.6} />
        </mesh>
        {/* Pipe support saddles on snow */}
        {[-1.8, 0, 1.8].map((pz, i) => (
          <mesh key={`saddle-${i}`} position={[0.1, -0.25, pz]}>
            <boxGeometry args={[0.5, 0.35, 0.15]} />
            <meshStandardMaterial color="#2c323a" roughness={0.8} />
          </mesh>
        ))}
      </group>

      {/* ------------------------------------------------------------- */}
      {/* 5. ACCESS (South Entrance Gangway, Stairs & Platform)         */}
      {/* ------------------------------------------------------------- */}
      <group position={[0, 0.5, 5.0]}>
        {/* Elevated Entry Platform (Gangway) */}
        <mesh receiveShadow position={[0, 0, 0]}>
          <boxGeometry args={[3.2, 0.25, 2.2]} />
          <meshStandardMaterial color="#424954" roughness={0.8} metalness={0.3} />
        </mesh>

        {/* High-visibility safety tread edge */}
        <mesh position={[0, 0.13, 1.1]}>
          <boxGeometry args={[3.0, 0.02, 0.12]} />
          <meshStandardMaterial color="#b65a1f" roughness={0.4} metalness={0.4} />
        </mesh>

        {/* Safety Handrail Stanchions */}
        {[-1.55, 1.55].map((hx, i) => (
          <mesh key={`access-rail-${i}`} position={[hx, 0.45, 0]}>
            <boxGeometry args={[0.04, 0.65, 2.1]} />
            <meshStandardMaterial color="#b65a1f" roughness={0.4} metalness={0.5} />
          </mesh>
        ))}

        {/* Access Stairs descending to snow level */}
        <group position={[0, -0.2, 1.7]}>
          {[0, 1, 2].map((step) => (
            <mesh key={`step-${step}`} position={[0, -step * 0.12, step * 0.32]}>
              <boxGeometry args={[2.4, 0.12, 0.35]} />
              <meshStandardMaterial color="#353b45" roughness={0.8} />
            </mesh>
          ))}
        </group>

        {/* Platform Support Stilts */}
        {[-1.3, 1.3].map((px, i) => (
          <mesh key={`plat-stilt-${i}`} position={[px, -0.3, 0]}>
            <cylinderGeometry args={[0.07, 0.07, 0.5, 8]} />
            <meshStandardMaterial color="#333842" roughness={0.7} metalness={0.5} />
          </mesh>
        ))}
      </group>

      {/* ------------------------------------------------------------- */}
      {/* 6. POLAR BOUNDARY MARKER STAKES (Perimeter snow poles)        */}
      {/* ------------------------------------------------------------- */}
      {[
        [-13.5, 0.8, -12.0],
        [13.5, 0.8, -12.0],
        [-13.5, 0.8, 6.0],
        [13.5, 0.8, 6.0]
      ].map(([fx, fy, fz], idx) => (
        <group key={`flag-${idx}`} position={[fx, fy, fz]}>
          <mesh>
            <cylinderGeometry args={[0.03, 0.03, 1.6, 6]} />
            <meshStandardMaterial color="#373d47" roughness={0.7} />
          </mesh>
          <mesh position={[0.15, 0.6, 0]}>
            <boxGeometry args={[0.3, 0.2, 0.02]} />
            <meshStandardMaterial color="#b65a1f" roughness={0.5} />
          </mesh>
        </group>
      ))}
    </group>
  );
};

export default StationModel;
