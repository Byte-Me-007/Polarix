import React from 'react';
import { StationZone } from './StationZone';

export const StationModel = ({ station, showLabels = true }) => {
  const zones = station?.digitalTwin?.zones || [];

  return (
    <group name="station-model-root">
      {/* ------------------------------------------------------------- */}
      {/* 1. ANTARCTIC PERMAFROST & SNOWFIELD TERRAIN                   */}
      {/* ------------------------------------------------------------- */}
      {/* Smooth Antarctic Packed Snow Plane */}
      <mesh receiveShadow rotation={[-Math.PI / 2, 0, 0]} position={[0, -0.05, -8]}>
        <planeGeometry args={[160, 160, 1, 1]} />
        <meshStandardMaterial 
          color="#f4f1ea" 
          roughness={0.92} 
          metalness={0.04} 
        />
      </mesh>

      {/* Subtle Coordinate Survey Grid on Snow Surface */}
      <gridHelper 
        args={[140, 40, '#d8d1c5', '#ece7df']} 
        position={[0, 0.01, -8]} 
      />

      {/* ------------------------------------------------------------- */}
      {/* 2. SPATIAL STATION FACILITIES (6 Required Modules)            */}
      {/* ------------------------------------------------------------- */}
      {zones.map((zone) => (
        <StationZone 
          key={zone.id} 
          zone={zone} 
          showLabels={showLabels} 
        />
      ))}

      {/* ------------------------------------------------------------- */}
      {/* 3. SUBSTANTIAL ENCLOSED CONNECTING CORRIDORS                  */}
      {/* ------------------------------------------------------------- */}

      {/* Corridor 1: MAIN BUILDING ↔ RESEARCH (East Habitat Connector) */}
      <group position={[13.5, 2.6, 0]}>
        {/* Main Enclosed Breezeway Body */}
        <mesh castShadow receiveShadow>
          <boxGeometry args={[5.2, 3.2, 3.4]} />
          <meshStandardMaterial color="#ded7cc" roughness={0.6} metalness={0.2} />
        </mesh>
        {/* Roof Parapet Trim */}
        <mesh position={[0, 1.7, 0]}>
          <boxGeometry args={[5.3, 0.2, 3.5]} />
          <meshStandardMaterial color="#383f4a" roughness={0.7} metalness={0.4} />
        </mesh>
        {/* Insulated Expansion Joint Bellows at Building Interfaces */}
        {[-2.3, 2.3].map((bx, i) => (
          <mesh key={`res-joint-${i}`} position={[bx, 0, 0]}>
            <boxGeometry args={[0.35, 3.3, 3.5]} />
            <meshStandardMaterial color="#2d333b" roughness={0.8} />
          </mesh>
        ))}
        {/* Observation Ribbon Windows along connector */}
        <mesh position={[0, 0.3, 1.72]}>
          <boxGeometry args={[3.2, 0.7, 0.05]} />
          <meshStandardMaterial color="#1a2028" roughness={0.1} metalness={0.85} />
        </mesh>
        <mesh position={[0, 0.3, -1.72]}>
          <boxGeometry args={[3.2, 0.7, 0.05]} />
          <meshStandardMaterial color="#1a2028" roughness={0.1} metalness={0.85} />
        </mesh>
        {/* Elevated Foundation Stilts under Corridor */}
        {[-1.5, 1.5].map((stX, i) => (
          <group key={`res-corr-stilt-${i}`} position={[stX, -2.0, 0]}>
            <mesh castShadow>
              <cylinderGeometry args={[0.18, 0.18, 2.4, 8]} />
              <meshStandardMaterial color="#2d333b" roughness={0.7} metalness={0.5} />
            </mesh>
            <mesh position={[0, -1.1, 0]}>
              <boxGeometry args={[0.6, 0.12, 0.6]} />
              <meshStandardMaterial color="#3d444e" roughness={0.8} />
            </mesh>
          </group>
        ))}
      </group>

      {/* Corridor 2: MAIN BUILDING ↔ ENERGY (North Spine Connector) */}
      <group position={[0, 2.5, -9.5]}>
        {/* Main Central Spine Enclosed Body */}
        <mesh castShadow receiveShadow>
          <boxGeometry args={[3.8, 3.2, 5.2]} />
          <meshStandardMaterial color="#ded7cc" roughness={0.6} metalness={0.2} />
        </mesh>
        {/* Roof Parapet Trim */}
        <mesh position={[0, 1.7, 0]}>
          <boxGeometry args={[3.9, 0.2, 5.3]} />
          <meshStandardMaterial color="#383f4a" roughness={0.7} metalness={0.4} />
        </mesh>
        {/* Insulated Expansion Joint Collars */}
        {[-2.3, 2.3].map((bz, i) => (
          <mesh key={`spine-joint-${i}`} position={[0, 0, bz]}>
            <boxGeometry args={[3.9, 3.3, 0.35]} />
            <meshStandardMaterial color="#2d333b" roughness={0.8} />
          </mesh>
        ))}
        {/* Elevated Foundation Stilts under North Spine */}
        {[-1.2, 1.2].map((stX, i) => (
          <group key={`spine-stilt-${i}`} position={[stX, -1.9, 0]}>
            <mesh castShadow>
              <cylinderGeometry args={[0.18, 0.18, 2.2, 8]} />
              <meshStandardMaterial color="#2d333b" roughness={0.7} metalness={0.5} />
            </mesh>
            <mesh position={[0, -1.0, 0]}>
              <boxGeometry args={[0.6, 0.12, 0.6]} />
              <meshStandardMaterial color="#3d444e" roughness={0.8} />
            </mesh>
          </group>
        ))}
      </group>

      {/* Corridor 3: ENERGY ↔ GENERATOR (West Utility Breezeway) */}
      <group position={[-9.75, 2.3, -18.0]}>
        <mesh castShadow receiveShadow>
          <boxGeometry args={[3.7, 3.0, 3.2]} />
          <meshStandardMaterial color="#d4ccc0" roughness={0.65} metalness={0.2} />
        </mesh>
        {/* Heavy Expansion Joint Bands */}
        {[-1.6, 1.6].map((bx, i) => (
          <mesh key={`gen-joint-${i}`} position={[bx, 0, 0]}>
            <boxGeometry args={[0.3, 3.1, 3.3]} />
            <meshStandardMaterial color="#2d333b" roughness={0.8} />
          </mesh>
        ))}
        {/* Stilts */}
        <group position={[0, -1.8, 0]}>
          <mesh castShadow>
            <cylinderGeometry args={[0.16, 0.16, 2.0, 8]} />
            <meshStandardMaterial color="#2d333b" roughness={0.7} metalness={0.5} />
          </mesh>
          <mesh position={[0, -0.9, 0]}>
            <boxGeometry args={[0.55, 0.12, 0.55]} />
            <meshStandardMaterial color="#3d444e" roughness={0.8} />
          </mesh>
        </group>
      </group>

      {/* Corridor 4: ENERGY ↔ STORAGE (East Logistics Connector) */}
      <group position={[9.5, 2.2, -18.0]}>
        <mesh castShadow receiveShadow>
          <boxGeometry args={[3.2, 3.0, 3.2]} />
          <meshStandardMaterial color="#d4ccc0" roughness={0.65} metalness={0.2} />
        </mesh>
        {/* Expansion Bands */}
        {[-1.4, 1.4].map((bx, i) => (
          <mesh key={`stor-joint-${i}`} position={[bx, 0, 0]}>
            <boxGeometry args={[0.3, 3.1, 3.3]} />
            <meshStandardMaterial color="#2d333b" roughness={0.8} />
          </mesh>
        ))}
        {/* Stilts */}
        <group position={[0, -1.7, 0]}>
          <mesh castShadow>
            <cylinderGeometry args={[0.16, 0.16, 1.9, 8]} />
            <meshStandardMaterial color="#2d333b" roughness={0.7} metalness={0.5} />
          </mesh>
          <mesh position={[0, -0.85, 0]}>
            <boxGeometry args={[0.55, 0.12, 0.55]} />
            <meshStandardMaterial color="#3d444e" roughness={0.8} />
          </mesh>
        </group>
      </group>

      {/* Corridor 5: ENERGY ↔ COMMUNICATIONS (North Covered Utility Corridor & Cable Bridge) */}
      <group position={[0, 1.8, -26.0]}>
        {/* Covered Enclosed Walkway */}
        <mesh castShadow receiveShadow>
          <boxGeometry args={[2.4, 2.4, 4.2]} />
          <meshStandardMaterial color="#424954" roughness={0.8} metalness={0.3} />
        </mesh>
        {/* Twin High-Voltage & Telemetry Conduits running along exterior */}
        {[-1.3, 1.3].map((cx, i) => (
          <mesh key={`comms-cable-${i}`} position={[cx, 0, 0]} rotation={[Math.PI / 2, 0, 0]}>
            <cylinderGeometry args={[0.1, 0.1, 4.2, 8]} />
            <meshStandardMaterial color="#1a1d22" roughness={0.5} />
          </mesh>
        ))}
        {/* Stilts */}
        <group position={[0, -1.3, 0]}>
          <mesh castShadow>
            <cylinderGeometry args={[0.16, 0.16, 1.6, 8]} />
            <meshStandardMaterial color="#2d333b" roughness={0.7} metalness={0.5} />
          </mesh>
          <mesh position={[0, -0.7, 0]}>
            <boxGeometry args={[0.55, 0.12, 0.55]} />
            <meshStandardMaterial color="#3d444e" roughness={0.8} />
          </mesh>
        </group>
      </group>

      {/* ------------------------------------------------------------- */}
      {/* 4. UTILITY PIPELINE & INFRASTRUCTURE RACK (Generator ↔ Main)   */}
      {/* ------------------------------------------------------------- */}
      {/* Heavy insulated heating & fuel pipe manifold running south from Generator to Main Building */}
      <group position={[-14.0, 0.9, -9.0]}>
        {/* Insulated Twin Main Pipes */}
        <mesh position={[0, 0, 0]} rotation={[Math.PI / 2, 0, 0]}>
          <cylinderGeometry args={[0.15, 0.15, 9.0, 12]} />
          <meshStandardMaterial color="#6a7280" roughness={0.4} metalness={0.6} />
        </mesh>
        <mesh position={[0.4, 0, 0]} rotation={[Math.PI / 2, 0, 0]}>
          <cylinderGeometry args={[0.1, 0.1, 9.0, 12]} />
          <meshStandardMaterial color="#b65a1f" roughness={0.4} metalness={0.6} />
        </mesh>
        {/* Pipeline Support Saddles & Footings */}
        {[-3.0, 0, 3.0].map((pz, i) => (
          <mesh key={`pipe-saddle-${i}`} position={[0.2, -0.5, pz]}>
            <boxGeometry args={[0.9, 0.7, 0.3]} />
            <meshStandardMaterial color="#2c323a" roughness={0.8} />
          </mesh>
        ))}
      </group>

      {/* ------------------------------------------------------------- */}
      {/* 5. SOUTH ACCESS & EXPEDITION STAGING PLATFORM                 */}
      {/* ------------------------------------------------------------- */}
      <group position={[0, 1.0, 10.5]}>
        {/* Wide Staging Platform Deck */}
        <mesh receiveShadow position={[0, 0, 0]}>
          <boxGeometry args={[7.0, 0.4, 4.5]} />
          <meshStandardMaterial color="#3b424d" roughness={0.8} metalness={0.3} />
        </mesh>

        {/* High-Visibility Safety Edge Tread */}
        <mesh position={[0, 0.22, 2.2]}>
          <boxGeometry args={[6.8, 0.04, 0.2]} />
          <meshStandardMaterial color="#b65a1f" roughness={0.4} metalness={0.5} />
        </mesh>

        {/* Safety Handrail Stanchions (East & West sides) */}
        {[-3.4, 3.4].map((rx, i) => (
          <mesh key={`access-rail-${i}`} position={[rx, 0.7, 0]}>
            <boxGeometry args={[0.06, 1.0, 4.4]} />
            <meshStandardMaterial color="#b65a1f" roughness={0.4} metalness={0.5} />
          </mesh>
        ))}

        {/* Access Stairs & Vehicle Ramp descending forward to snow datum */}
        <group position={[0, -0.4, 3.2]}>
          {[0, 1, 2, 3].map((step) => (
            <mesh key={`access-step-${step}`} position={[0, -step * 0.2, step * 0.5]}>
              <boxGeometry args={[5.5, 0.2, 0.6]} />
              <meshStandardMaterial color="#2c323b" roughness={0.8} />
            </mesh>
          ))}
        </group>

        {/* Platform Support Stilts */}
        {[-2.8, 2.8].map((px, i) => (
          <group key={`plat-stilt-${i}`} position={[px, -0.6, 0]}>
            <mesh castShadow>
              <cylinderGeometry args={[0.16, 0.16, 1.0, 8]} />
              <meshStandardMaterial color="#2d333b" roughness={0.7} metalness={0.5} />
            </mesh>
            <mesh position={[0, -0.45, 0]}>
              <boxGeometry args={[0.55, 0.1, 0.55]} />
              <meshStandardMaterial color="#3d444e" roughness={0.8} />
            </mesh>
          </group>
        ))}
      </group>

      {/* ------------------------------------------------------------- */}
      {/* 6. POLAR BOUNDARY SURVEY STAKES & HIGH-VISIBILITY MARKERS     */}
      {/* ------------------------------------------------------------- */}
      {[
        [-28.0, 1.2, -28.0],
        [32.0, 1.2, -28.0],
        [-28.0, 1.2, 12.0],
        [32.0, 1.2, 12.0]
      ].map(([fx, fy, fz], idx) => (
        <group key={`survey-flag-${idx}`} position={[fx, fy, fz]}>
          <mesh>
            <cylinderGeometry args={[0.06, 0.06, 2.4, 6]} />
            <meshStandardMaterial color="#2d333b" roughness={0.7} />
          </mesh>
          <mesh position={[0.25, 0.85, 0]}>
            <boxGeometry args={[0.5, 0.35, 0.03]} />
            <meshStandardMaterial color="#b65a1f" roughness={0.5} />
          </mesh>
        </group>
      ))}
    </group>
  );
};

export default StationModel;
