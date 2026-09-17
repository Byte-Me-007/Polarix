import React from 'react';
import { StationZone } from './StationZone';

// New station layout (all zones scaled ~1.75x from original):
//   MAIN:      pos [0, 3.5, 0],    size [34, 7, 22]   → X: -17..+17   Z: -11..+11
//   RESEARCH:  pos [38, 3.2, 0],   size [22, 6.4, 18] → X: +27..+49   Z: -9..+9
//   ENERGY:    pos [0, 3.0, -30],  size [26, 6, 18]   → X: -13..+13   Z: -39..-21
//   GENERATOR: pos [-30, 2.8, -30],size [20, 5.6, 18] → X: -40..-20   Z: -39..-21
//   STORAGE:   pos [32, 2.8, -30], size [20, 5.6, 18] → X: +22..+42   Z: -39..-21
//   COMMS:     pos [0, 2.6, -54],  size [14, 5.2, 14] → X: -7..+7     Z: -61..-47
//
// Gap analysis (all comfortable, 6-10 unit service clearance):
//   MAIN ↔ RESEARCH (x gap):   17 → 27  = 10 units  → Corridor at x=22
//   MAIN ↔ ENERGY (z gap):     -11 → -21 = 10 units  → Corridor at z=-16
//   ENERGY ↔ GENERATOR (x gap):-13 → -20 = 7 units   → Corridor at x=-16.5
//   ENERGY ↔ STORAGE (x gap):  +13 → +22 = 9 units   → Corridor at x=+17.5
//   ENERGY ↔ COMMS (z gap):    -39 → -47 = 8 units   → Corridor at z=-43

export const StationModel = ({ station, showLabels = true }) => {
  const zones = station?.digitalTwin?.zones || [];

  return (
    <group name="station-model-root">
      {/* ------------------------------------------------------------- */}
      {/* 1. ANTARCTIC PERMAFROST & SNOWFIELD TERRAIN                   */}
      {/* ------------------------------------------------------------- */}
      {/* Smooth Antarctic Packed Snow Plane — large enough for full station */}
      <mesh receiveShadow rotation={[-Math.PI / 2, 0, 0]} position={[4, -0.05, -24]}>
        <planeGeometry args={[240, 240, 1, 1]} />
        <meshStandardMaterial color="#f4f1ea" roughness={0.92} metalness={0.04} />
      </mesh>

      {/* Subtle Coordinate Survey Grid on Snow Surface */}
      <gridHelper
        args={[180, 36, '#e2dcce', '#ede8df']}
        position={[4, 0.01, -24]}
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
      {/* 3. ENCLOSED CONNECTING CORRIDORS                              */}
      {/* Each corridor bridges the gap between adjacent modules.       */}
      {/* ------------------------------------------------------------- */}

      {/* Corridor 1: MAIN BUILDING ↔ RESEARCH (East Habitat Connector) */}
      {/* Gap: x=17 to x=27, centered at x=22, z=0 */}
      <group position={[22, 3.0, 0]}>
        {/* Main Enclosed Breezeway Body */}
        <mesh castShadow receiveShadow>
          <boxGeometry args={[8.0, 4.2, 5.0]} />
          <meshStandardMaterial color="#ded7cc" roughness={0.6} metalness={0.2} />
        </mesh>
        {/* Roof Parapet Trim */}
        <mesh position={[0, 2.2, 0]}>
          <boxGeometry args={[8.1, 0.25, 5.1]} />
          <meshStandardMaterial color="#383f4a" roughness={0.7} metalness={0.4} />
        </mesh>
        {/* Expansion Joint Bellows at Building Interfaces */}
        {[-3.8, 3.8].map((bx, i) => (
          <mesh key={`res-joint-${i}`} position={[bx, 0, 0]}>
            <boxGeometry args={[0.45, 4.3, 5.1]} />
            <meshStandardMaterial color="#2d333b" roughness={0.8} />
          </mesh>
        ))}
        {/* Observation Ribbon Windows along connector */}
        <mesh position={[0, 0.4, 2.52]}>
          <boxGeometry args={[5.0, 0.9, 0.06]} />
          <meshStandardMaterial color="#1a2028" roughness={0.1} metalness={0.85} />
        </mesh>
        <mesh position={[0, 0.4, -2.52]}>
          <boxGeometry args={[5.0, 0.9, 0.06]} />
          <meshStandardMaterial color="#1a2028" roughness={0.1} metalness={0.85} />
        </mesh>
        {/* Elevated Foundation Stilts */}
        {[-2.5, 0, 2.5].map((stX, i) => (
          <group key={`res-corr-stilt-${i}`} position={[stX, -2.6, 0]}>
            <mesh castShadow>
              <cylinderGeometry args={[0.22, 0.22, 3.0, 8]} />
              <meshStandardMaterial color="#2d333b" roughness={0.7} metalness={0.5} />
            </mesh>
            <mesh position={[0, -1.4, 0]}>
              <boxGeometry args={[0.7, 0.14, 0.7]} />
              <meshStandardMaterial color="#3d444e" roughness={0.8} />
            </mesh>
          </group>
        ))}
      </group>

      {/* Corridor 2: MAIN BUILDING ↔ ENERGY (South Spine Connector) */}
      {/* Gap: z=-11 to z=-21, centered at z=-16, x=0 */}
      <group position={[0, 3.0, -16]}>
        {/* Main Central Spine Enclosed Body */}
        <mesh castShadow receiveShadow>
          <boxGeometry args={[5.5, 4.2, 8.0]} />
          <meshStandardMaterial color="#ded7cc" roughness={0.6} metalness={0.2} />
        </mesh>
        {/* Roof Parapet */}
        <mesh position={[0, 2.2, 0]}>
          <boxGeometry args={[5.6, 0.25, 8.1]} />
          <meshStandardMaterial color="#383f4a" roughness={0.7} metalness={0.4} />
        </mesh>
        {/* Expansion Joint Collars */}
        {[-3.8, 3.8].map((bz, i) => (
          <mesh key={`spine-joint-${i}`} position={[0, 0, bz]}>
            <boxGeometry args={[5.6, 4.3, 0.45]} />
            <meshStandardMaterial color="#2d333b" roughness={0.8} />
          </mesh>
        ))}
        {/* Stilts */}
        {[-1.8, 1.8].map((stX, i) => (
          <group key={`spine-stilt-${i}`} position={[stX, -2.5, 0]}>
            <mesh castShadow>
              <cylinderGeometry args={[0.22, 0.22, 2.8, 8]} />
              <meshStandardMaterial color="#2d333b" roughness={0.7} metalness={0.5} />
            </mesh>
            <mesh position={[0, -1.3, 0]}>
              <boxGeometry args={[0.7, 0.14, 0.7]} />
              <meshStandardMaterial color="#3d444e" roughness={0.8} />
            </mesh>
          </group>
        ))}
      </group>

      {/* Corridor 3: ENERGY ↔ GENERATOR (West Utility Breezeway) */}
      {/* Gap: x=-13 to x=-20, centered at x=-16.5, z=-30 */}
      <group position={[-16.5, 2.8, -30]}>
        <mesh castShadow receiveShadow>
          <boxGeometry args={[5.5, 3.8, 4.5]} />
          <meshStandardMaterial color="#d4ccc0" roughness={0.65} metalness={0.2} />
        </mesh>
        <mesh position={[0, 2.0, 0]}>
          <boxGeometry args={[5.6, 0.22, 4.6]} />
          <meshStandardMaterial color="#2d333b" roughness={0.7} metalness={0.4} />
        </mesh>
        {[-2.5, 2.5].map((bx, i) => (
          <mesh key={`gen-joint-${i}`} position={[bx, 0, 0]}>
            <boxGeometry args={[0.4, 3.9, 4.6]} />
            <meshStandardMaterial color="#2d333b" roughness={0.8} />
          </mesh>
        ))}
        <group position={[0, -2.1, 0]}>
          <mesh castShadow>
            <cylinderGeometry args={[0.2, 0.2, 2.4, 8]} />
            <meshStandardMaterial color="#2d333b" roughness={0.7} metalness={0.5} />
          </mesh>
          <mesh position={[0, -1.1, 0]}>
            <boxGeometry args={[0.65, 0.14, 0.65]} />
            <meshStandardMaterial color="#3d444e" roughness={0.8} />
          </mesh>
        </group>
      </group>

      {/* Corridor 4: ENERGY ↔ STORAGE (East Logistics Connector) */}
      {/* Gap: x=+13 to x=+22, centered at x=+17.5, z=-30 */}
      <group position={[17.5, 2.8, -30]}>
        <mesh castShadow receiveShadow>
          <boxGeometry args={[5.5, 3.8, 4.5]} />
          <meshStandardMaterial color="#d4ccc0" roughness={0.65} metalness={0.2} />
        </mesh>
        <mesh position={[0, 2.0, 0]}>
          <boxGeometry args={[5.6, 0.22, 4.6]} />
          <meshStandardMaterial color="#2d333b" roughness={0.7} metalness={0.4} />
        </mesh>
        {[-2.5, 2.5].map((bx, i) => (
          <mesh key={`stor-joint-${i}`} position={[bx, 0, 0]}>
            <boxGeometry args={[0.4, 3.9, 4.6]} />
            <meshStandardMaterial color="#2d333b" roughness={0.8} />
          </mesh>
        ))}
        <group position={[0, -2.1, 0]}>
          <mesh castShadow>
            <cylinderGeometry args={[0.2, 0.2, 2.4, 8]} />
            <meshStandardMaterial color="#2d333b" roughness={0.7} metalness={0.5} />
          </mesh>
          <mesh position={[0, -1.1, 0]}>
            <boxGeometry args={[0.65, 0.14, 0.65]} />
            <meshStandardMaterial color="#3d444e" roughness={0.8} />
          </mesh>
        </group>
      </group>

      {/* Corridor 5: ENERGY ↔ COMMUNICATIONS (South Covered Utility Corridor) */}
      {/* Gap: z=-39 to z=-47, centered at z=-43, x=0 */}
      <group position={[0, 2.2, -43]}>
        {/* Covered Enclosed Walkway */}
        <mesh castShadow receiveShadow>
          <boxGeometry args={[3.5, 3.2, 6.0]} />
          <meshStandardMaterial color="#424954" roughness={0.8} metalness={0.3} />
        </mesh>
        {/* Twin High-Voltage & Telemetry Conduits */}
        {[-1.8, 1.8].map((cx, i) => (
          <mesh key={`comms-cable-${i}`} position={[cx, 0, 0]} rotation={[Math.PI / 2, 0, 0]}>
            <cylinderGeometry args={[0.12, 0.12, 6.0, 8]} />
            <meshStandardMaterial color="#1a1d22" roughness={0.5} />
          </mesh>
        ))}
        {/* Stilts */}
        <group position={[0, -1.8, 0]}>
          <mesh castShadow>
            <cylinderGeometry args={[0.18, 0.18, 2.0, 8]} />
            <meshStandardMaterial color="#2d333b" roughness={0.7} metalness={0.5} />
          </mesh>
          <mesh position={[0, -0.9, 0]}>
            <boxGeometry args={[0.6, 0.12, 0.6]} />
            <meshStandardMaterial color="#3d444e" roughness={0.8} />
          </mesh>
        </group>
      </group>

      {/* ------------------------------------------------------------- */}
      {/* 4. UTILITY PIPELINE RACK (Generator ↔ Main Building)          */}
      {/* ------------------------------------------------------------- */}
      {/* Heavy insulated pipe manifold running diagonally from Generator region toward Main */}
      <group position={[-22, 1.0, -15]}>
        {/* Insulated Twin Main Pipes — angled to span from generator area to main */}
        <mesh position={[0, 0, 0]} rotation={[Math.PI / 2, 0, 0]}>
          <cylinderGeometry args={[0.18, 0.18, 14.0, 12]} />
          <meshStandardMaterial color="#6a7280" roughness={0.4} metalness={0.6} />
        </mesh>
        <mesh position={[0.5, 0, 0]} rotation={[Math.PI / 2, 0, 0]}>
          <cylinderGeometry args={[0.12, 0.12, 14.0, 12]} />
          <meshStandardMaterial color="#b65a1f" roughness={0.4} metalness={0.6} />
        </mesh>
        {/* Pipeline Support Saddles */}
        {[-4.5, -1.5, 1.5, 4.5].map((pz, i) => (
          <mesh key={`pipe-saddle-${i}`} position={[0.25, -0.6, pz]}>
            <boxGeometry args={[1.1, 0.8, 0.4]} />
            <meshStandardMaterial color="#2c323a" roughness={0.8} />
          </mesh>
        ))}
      </group>

      {/* ------------------------------------------------------------- */}
      {/* 5. SOUTH ACCESS & EXPEDITION STAGING PLATFORM                 */}
      {/* Positioned at the front (south) face of MAIN BUILDING         */}
      {/* ------------------------------------------------------------- */}
      <group position={[0, 1.2, 17]}>
        {/* Wide Staging Platform Deck */}
        <mesh receiveShadow position={[0, 0, 0]}>
          <boxGeometry args={[11.0, 0.5, 6.5]} />
          <meshStandardMaterial color="#3b424d" roughness={0.8} metalness={0.3} />
        </mesh>

        {/* High-Visibility Safety Edge Tread */}
        <mesh position={[0, 0.28, 3.2]}>
          <boxGeometry args={[10.6, 0.05, 0.25]} />
          <meshStandardMaterial color="#b65a1f" roughness={0.4} metalness={0.5} />
        </mesh>

        {/* Safety Handrail Stanchions (East & West sides) */}
        {[-5.2, 5.2].map((rx, i) => (
          <mesh key={`access-rail-${i}`} position={[rx, 0.85, 0]}>
            <boxGeometry args={[0.08, 1.2, 6.3]} />
            <meshStandardMaterial color="#b65a1f" roughness={0.4} metalness={0.5} />
          </mesh>
        ))}

        {/* Access Stairs descending to snow datum */}
        <group position={[0, -0.5, 4.5]}>
          {[0, 1, 2, 3, 4].map((step) => (
            <mesh key={`access-step-${step}`} position={[0, -step * 0.22, step * 0.6]}>
              <boxGeometry args={[8.5, 0.22, 0.7]} />
              <meshStandardMaterial color="#2c323b" roughness={0.8} />
            </mesh>
          ))}
        </group>

        {/* Platform Support Stilts */}
        {[-4.2, 0, 4.2].map((px, i) => (
          <group key={`plat-stilt-${i}`} position={[px, -0.75, 0]}>
            <mesh castShadow>
              <cylinderGeometry args={[0.2, 0.2, 1.2, 8]} />
              <meshStandardMaterial color="#2d333b" roughness={0.7} metalness={0.5} />
            </mesh>
            <mesh position={[0, -0.55, 0]}>
              <boxGeometry args={[0.65, 0.12, 0.65]} />
              <meshStandardMaterial color="#3d444e" roughness={0.8} />
            </mesh>
          </group>
        ))}
      </group>

      {/* ------------------------------------------------------------- */}
      {/* 6. POLAR BOUNDARY SURVEY STAKES & HIGH-VISIBILITY MARKERS     */}
      {/* Placed at the 4 outer corners of the full station footprint   */}
      {/* Footprint: X -44..+52, Z -64..+20                            */}
      {/* ------------------------------------------------------------- */}
      {[
        [-46.0, 1.2, -64.0],
        [ 54.0, 1.2, -64.0],
        [-46.0, 1.2,  20.0],
        [ 54.0, 1.2,  20.0],
        [  4.0, 1.2, -64.0],
        [  4.0, 1.2,  20.0],
      ].map(([fx, fy, fz], idx) => (
        <group key={`survey-flag-${idx}`} position={[fx, fy, fz]}>
          <mesh>
            <cylinderGeometry args={[0.08, 0.08, 3.0, 6]} />
            <meshStandardMaterial color="#2d333b" roughness={0.7} />
          </mesh>
          <mesh position={[0.32, 1.1, 0]}>
            <boxGeometry args={[0.65, 0.42, 0.04]} />
            <meshStandardMaterial color="#b65a1f" roughness={0.5} />
          </mesh>
        </group>
      ))}
    </group>
  );
};

export default StationModel;
