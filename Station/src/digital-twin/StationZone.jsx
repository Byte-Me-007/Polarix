import React, { useRef } from 'react';
import { Html } from '@react-three/drei';

export const StationZone = ({ zone, showLabels = true }) => {
  const meshRef = useRef();

  const [px, py, pz] = zone.position;
  const [sx, sy, sz] = zone.size;
  const code = zone.code || zone.id;

  // Stilt footing calculations - polar foundation elevated above ground y=0
  const stiltRadius = 0.12;
  const stiltHeight = py + 0.1; 
  const stiltY = -py / 2;

  // 6 or 8 foundation pilings per module with ground spreader pads
  const numStiltsX = sx > 10 ? 4 : 3;
  const numStiltsZ = sz > 6 ? 3 : 2;
  const stilts = [];
  for (let ix = 0; ix < numStiltsX; ix++) {
    for (let iz = 0; iz < numStiltsZ; iz++) {
      const cx = -sx * 0.44 + (ix / (numStiltsX - 1)) * sx * 0.88;
      const cz = -sz * 0.44 + (iz / (numStiltsZ - 1)) * sz * 0.88;
      stilts.push([cx, cz]);
    }
  }

  return (
    <group position={[px, py, pz]}>
      {/* ------------------------------------------------------------- */}
      {/* 1. FOUNDATION PILINGS & GROUND PADS (Elevated polar stilts) */}
      {/* ------------------------------------------------------------- */}
      {code !== 'COMMS' && stilts.map(([cx, cz], idx) => (
        <group key={`stilt-${idx}`} position={[cx, stiltY, cz]}>
          {/* Steel column */}
          <mesh>
            <cylinderGeometry args={[stiltRadius, stiltRadius, stiltHeight, 8]} />
            <meshStandardMaterial color="#333842" roughness={0.7} metalness={0.5} />
          </mesh>
          {/* Concrete/Steel ground spreader pad on snow */}
          <mesh position={[0, -stiltHeight / 2 + 0.05, 0]}>
            <boxGeometry args={[0.42, 0.1, 0.42]} />
            <meshStandardMaterial color="#424954" roughness={0.8} metalness={0.3} />
          </mesh>
        </group>
      ))}

      {/* ------------------------------------------------------------- */}
      {/* 2. ZONE-SPECIFIC ARCHITECTURAL GEOMETRY */}
      {/* ------------------------------------------------------------- */}

      {/* === A. MAIN BUILDING (Central Anchor & Habitat Hub) === */}
      {code === 'MAIN' && (
        <group>
          {/* Main Core Habitat Body */}
          <mesh castShadow receiveShadow position={[0, sy / 2, 0]}>
            <boxGeometry args={[sx, sy, sz]} />
            <meshStandardMaterial color="#ece8e1" roughness={0.55} metalness={0.15} />
          </mesh>

          {/* Heavy perimeter roof fascia / parapet trim */}
          <mesh position={[0, sy + 0.08, 0]}>
            <boxGeometry args={[sx + 0.15, 0.16, sz + 0.15]} />
            <meshStandardMaterial color="#3b424d" roughness={0.6} metalness={0.3} />
          </mesh>

          {/* Roof weather-seal top deck */}
          <mesh position={[0, sy + 0.17, 0]}>
            <boxGeometry args={[sx * 0.94, 0.04, sz * 0.94]} />
            <meshStandardMaterial color="#505866" roughness={0.7} metalness={0.4} />
          </mesh>

          {/* Recessed Thermal Window Strips (North & South facades) */}
          <mesh position={[0, sy * 0.55, sz / 2 + 0.02]}>
            <boxGeometry args={[sx * 0.82, 0.45, 0.04]} />
            <meshStandardMaterial color="#212730" roughness={0.1} metalness={0.8} />
          </mesh>
          <mesh position={[0, sy * 0.55, -sz / 2 - 0.02]}>
            <boxGeometry args={[sx * 0.82, 0.45, 0.04]} />
            <meshStandardMaterial color="#212730" roughness={0.1} metalness={0.8} />
          </mesh>

          {/* Roof Central HVAC / Atmospheric Intake Pod */}
          <group position={[0, sy + 0.45, 0]}>
            <mesh castShadow position={[0, 0, 0]}>
              <boxGeometry args={[2.8, 0.55, 2.0]} />
              <meshStandardMaterial color="#c5beaf" roughness={0.6} metalness={0.3} />
            </mesh>
            {/* Louver grills */}
            <mesh position={[0, 0.05, 1.02]}>
              <boxGeometry args={[2.2, 0.35, 0.04]} />
              <meshStandardMaterial color="#333842" roughness={0.8} metalness={0.2} />
            </mesh>
          </group>

          {/* South Entry Vestibule / Airlock Portal facing Access walkway */}
          <group position={[0, sy * 0.4, sz / 2 + 0.5]}>
            <mesh castShadow>
              <boxGeometry args={[2.2, sy * 0.8, 1.0]} />
              <meshStandardMaterial color="#ded7cc" roughness={0.6} metalness={0.2} />
            </mesh>
            {/* Safety Accent Door Frame */}
            <mesh position={[0, 0, 0.51]}>
              <boxGeometry args={[1.2, sy * 0.65, 0.04]} />
              <meshStandardMaterial color="#b65a1f" roughness={0.5} metalness={0.3} />
            </mesh>
          </group>
        </group>
      )}

      {/* === B. ENERGY (Power Infrastructure & Battery Station) === */}
      {code === 'ENERGY' && (
        <group>
          {/* Main Power Building */}
          <mesh castShadow receiveShadow position={[0, sy / 2, 0]}>
            <boxGeometry args={[sx, sy, sz]} />
            <meshStandardMaterial color="#ded7cc" roughness={0.6} metalness={0.2} />
          </mesh>

          {/* Roof Parapet */}
          <mesh position={[0, sy + 0.06, 0]}>
            <boxGeometry args={[sx + 0.1, 0.12, sz + 0.1]} />
            <meshStandardMaterial color="#3a414b" roughness={0.6} metalness={0.3} />
          </mesh>

          {/* Photovoltaic Solar Array Test Racks (Angled polar orientation) */}
          <group position={[-1.2, sy + 0.35, 0]}>
            {[-1.0, 1.0].map((offsetZ, i) => (
              <mesh key={`pv-${i}`} position={[0, 0, offsetZ]} rotation={[0.3, 0, 0]}>
                <boxGeometry args={[2.2, 0.06, 1.2]} />
                <meshStandardMaterial color="#1e293b" roughness={0.2} metalness={0.8} />
              </mesh>
            ))}
          </group>

          {/* High-Voltage Transformer / Substation Unit on Roof */}
          <group position={[1.8, sy + 0.35, 0]}>
            <mesh castShadow position={[0, 0, 0]}>
              <boxGeometry args={[1.4, 0.6, 1.8]} />
              <meshStandardMaterial color="#535c69" roughness={0.5} metalness={0.5} />
            </mesh>
            {/* Cooling fins */}
            <mesh position={[0.72, 0, 0]}>
              <boxGeometry args={[0.05, 0.5, 1.6]} />
              <meshStandardMaterial color="#2d333b" roughness={0.8} metalness={0.4} />
            </mesh>
          </group>

          {/* Exterior Battery Storage Rack Cabinets (North Face) */}
          <group position={[0, sy * 0.4, -sz / 2 - 0.35]}>
            <mesh castShadow>
              <boxGeometry args={[sx * 0.7, sy * 0.8, 0.6]} />
              <meshStandardMaterial color="#b26814" roughness={0.5} metalness={0.3} />
            </mesh>
          </group>
        </group>
      )}

      {/* === C. GENERATOR (Industrial Power Plant) === */}
      {code === 'GENERATOR' && (
        <group>
          {/* Main Industrial Housing (Heavy paneled enclosure) */}
          <mesh castShadow receiveShadow position={[0, sy / 2, 0]}>
            <boxGeometry args={[sx, sy, sz]} />
            <meshStandardMaterial color="#d4ccc0" roughness={0.7} metalness={0.2} />
          </mesh>

          {/* Heavy Steel Roof Fascia */}
          <mesh position={[0, sy + 0.05, 0]}>
            <boxGeometry args={[sx + 0.12, 0.1, sz + 0.12]} />
            <meshStandardMaterial color="#2c323b" roughness={0.7} metalness={0.4} />
          </mesh>

          {/* Dual Heavy Diesel Exhaust Stacks (Tall with rain caps) */}
          {[-0.8, 0.8].map((offX, i) => (
            <group key={`exhaust-${i}`} position={[offX, sy + 1.1, -sz * 0.25]}>
              {/* Vertical Stack */}
              <mesh castShadow>
                <cylinderGeometry args={[0.16, 0.18, 2.0, 16]} />
                <meshStandardMaterial color="#3d444e" roughness={0.6} metalness={0.6} />
              </mesh>
              {/* Rain hood cap */}
              <mesh position={[0, 1.05, 0]}>
                <coneGeometry args={[0.3, 0.22, 16]} />
                <meshStandardMaterial color="#22262c" roughness={0.5} metalness={0.5} />
              </mesh>
            </group>
          ))}

          {/* Large External Cooling Radiator & Louver Bank (West Face) */}
          <group position={[-sx / 2 - 0.25, sy * 0.5, 0]}>
            <mesh castShadow>
              <boxGeometry args={[0.45, sy * 0.75, sz * 0.7]} />
              <meshStandardMaterial color="#373d47" roughness={0.8} metalness={0.4} />
            </mesh>
            {/* Louver grill pattern */}
            <mesh position={[-0.23, 0, 0]}>
              <boxGeometry args={[0.04, sy * 0.65, sz * 0.6]} />
              <meshStandardMaterial color="#1a1d22" roughness={0.9} />
            </mesh>
          </group>

          {/* Cylindrical Fuel Buffer Day-Tank on Cradle (South side) */}
          <group position={[0.5, sy * 0.35, sz / 2 + 0.55]} rotation={[0, 0, Math.PI / 2]}>
            <mesh castShadow>
              <cylinderGeometry args={[0.42, 0.42, 2.2, 16]} />
              <meshStandardMaterial color="#8c7e6d" roughness={0.5} metalness={0.5} />
            </mesh>
            {/* Tank end caps */}
            <mesh position={[0, 1.12, 0]}>
              <sphereGeometry args={[0.42, 16, 8, 0, Math.PI * 2, 0, Math.PI / 2]} />
              <meshStandardMaterial color="#6e6254" roughness={0.5} metalness={0.5} />
            </mesh>
            <mesh position={[0, -1.12, 0]} rotation={[Math.PI, 0, 0]}>
              <sphereGeometry args={[0.42, 16, 8, 0, Math.PI * 2, 0, Math.PI / 2]} />
              <meshStandardMaterial color="#6e6254" roughness={0.5} metalness={0.5} />
            </mesh>
          </group>
        </group>
      )}

      {/* === D. STORAGE (Logistics & Cold-Provisions Containers) === */}
      {code === 'STORAGE' && (
        <group>
          {/* Twin 20ft ISO-Style Polar Container Enclosure */}
          <mesh castShadow receiveShadow position={[0, sy / 2, 0]}>
            <boxGeometry args={[sx, sy, sz]} />
            <meshStandardMaterial color="#cfc7b9" roughness={0.65} metalness={0.2} />
          </mesh>

          {/* Roof Edge Rib */}
          <mesh position={[0, sy + 0.05, 0]}>
            <boxGeometry args={[sx + 0.1, 0.1, sz + 0.1]} />
            <meshStandardMaterial color="#3e4550" roughness={0.7} metalness={0.3} />
          </mesh>

          {/* Horizontal Container Fluting / Corrugation Strips */}
          {[-0.5, 0, 0.5].map((yOff, i) => (
            <mesh key={`rib-${i}`} position={[0, sy / 2 + yOff, sz / 2 + 0.03]}>
              <boxGeometry args={[sx * 0.92, 0.12, 0.04]} />
              <meshStandardMaterial color="#b3ab9c" roughness={0.6} metalness={0.3} />
            </mesh>
          ))}

          {/* Heavy Logistics Double Cargo Doors (East Face) */}
          <group position={[sx / 2 + 0.02, sy * 0.45, 0]}>
            <mesh>
              <boxGeometry args={[0.04, sy * 0.75, sz * 0.65]} />
              <meshStandardMaterial color="#2d333b" roughness={0.8} metalness={0.4} />
            </mesh>
            {/* Door seam & handles */}
            <mesh position={[0.03, 0, 0]}>
              <boxGeometry args={[0.02, sy * 0.7, 0.08]} />
              <meshStandardMaterial color="#b65a1f" roughness={0.4} metalness={0.6} />
            </mesh>
          </group>

          {/* Exterior Cargo Staging Platform with Supply Pallet */}
          <group position={[sx / 2 + 0.7, 0.15, 0]}>
            <mesh receiveShadow>
              <boxGeometry args={[1.1, 0.15, 2.0]} />
              <meshStandardMaterial color="#554d42" roughness={0.9} />
            </mesh>
            {/* Supplies Box */}
            <mesh castShadow position={[0, 0.3, 0]}>
              <boxGeometry args={[0.7, 0.45, 1.2]} />
              <meshStandardMaterial color="#8f7e6c" roughness={0.7} />
            </mesh>
          </group>
        </group>
      )}

      {/* === E. RESEARCH (Specialized Scientific Laboratory) === */}
      {code === 'RESEARCH' && (
        <group>
          {/* Main Laboratory Building */}
          <mesh castShadow receiveShadow position={[0, sy / 2, 0]}>
            <boxGeometry args={[sx, sy, sz]} />
            <meshStandardMaterial color="#eae4da" roughness={0.55} metalness={0.2} />
          </mesh>

          {/* Roof Parapet */}
          <mesh position={[0, sy + 0.06, 0]}>
            <boxGeometry args={[sx + 0.12, 0.12, sz + 0.12]} />
            <meshStandardMaterial color="#373e48" roughness={0.6} metalness={0.3} />
          </mesh>

          {/* Rooftop Scientific Observation Optical Dome */}
          <group position={[-1.2, sy + 0.1, 0.8]}>
            {/* Base collar */}
            <mesh position={[0, 0.15, 0]}>
              <cylinderGeometry args={[0.9, 0.95, 0.3, 24]} />
              <meshStandardMaterial color="#3b424d" roughness={0.5} metalness={0.4} />
            </mesh>
            {/* Hemispherical Dome */}
            <mesh castShadow position={[0, 0.3, 0]}>
              <sphereGeometry args={[0.9, 24, 16, 0, Math.PI * 2, 0, Math.PI * 0.5]} />
              <meshStandardMaterial color="#f8f6f0" roughness={0.25} metalness={0.15} />
            </mesh>
            {/* Optical aperture slit */}
            <mesh position={[0, 0.75, 0.4]}>
              <boxGeometry args={[0.22, 0.8, 0.15]} />
              <meshStandardMaterial color="#1a1c20" roughness={0.2} metalness={0.8} />
            </mesh>
          </group>

          {/* Atmospheric Air Sampling Intake & Met Arm */}
          <group position={[1.4, sy + 0.8, -1.0]}>
            <mesh castShadow>
              <cylinderGeometry args={[0.06, 0.08, 1.4, 8]} />
              <meshStandardMaterial color="#2d333b" roughness={0.5} metalness={0.7} />
            </mesh>
            {/* Sensor cross arm */}
            <mesh position={[0, 0.6, 0]}>
              <boxGeometry args={[0.8, 0.04, 0.04]} />
              <meshStandardMaterial color="#b65a1f" roughness={0.4} metalness={0.6} />
            </mesh>
          </group>

          {/* Lab Clean-Room Filter Enclosure (East Face) */}
          <mesh castShadow position={[sx / 2 + 0.25, sy * 0.5, 0]}>
            <boxGeometry args={[0.45, sy * 0.6, 1.8]} />
            <meshStandardMaterial color="#c8c1b3" roughness={0.6} metalness={0.3} />
          </mesh>
        </group>
      )}

      {/* === F. COMMS (Telecommunications Mast & Radome/Dish) === */}
      {code === 'COMMS' && (
        <group>
          {/* Ground Foundation Equipment Pod */}
          <mesh castShadow receiveShadow position={[0, 0.7, 0]}>
            <boxGeometry args={[2.8, 1.4, 2.8]} />
            <meshStandardMaterial color="#dcd5c9" roughness={0.6} metalness={0.2} />
          </mesh>

          {/* Heavy Steel Tower Base Collar */}
          <mesh position={[0, 1.45, 0]}>
            <cylinderGeometry args={[0.9, 1.1, 0.2, 16]} />
            <meshStandardMaterial color="#333842" roughness={0.6} metalness={0.5} />
          </mesh>

          {/* Open-Truss Structural Lattice Mast */}
          <group position={[0, 3.2, 0]}>
            {/* Central Mast Column */}
            <mesh castShadow>
              <cylinderGeometry args={[0.18, 0.32, 3.4, 8]} />
              <meshStandardMaterial color="#3e4652" roughness={0.5} metalness={0.7} />
            </mesh>
            {/* 4 Outer Truss Corner Legs */}
            {[
              [-0.45, -0.45],
              [0.45, -0.45],
              [-0.45, 0.45],
              [0.45, 0.45]
            ].map(([tx, tz], i) => (
              <mesh key={`truss-${i}`} position={[tx, 0, tz]}>
                <cylinderGeometry args={[0.04, 0.05, 3.4, 6]} />
                <meshStandardMaterial color="#2d333b" roughness={0.6} metalness={0.6} />
              </mesh>
            ))}
          </group>

          {/* Parabolic Satellite Tracking Dish (Angled skyward) */}
          <group position={[0, 5.1, 0.3]} rotation={[0.45, 0, 0]}>
            {/* Dish Reflector Bowl */}
            <mesh castShadow>
              <sphereGeometry args={[1.3, 24, 16, 0, Math.PI * 2, 0, Math.PI * 0.42]} />
              <meshStandardMaterial color="#ece7de" roughness={0.3} metalness={0.3} side={2} />
            </mesh>
            {/* Central Feed Horn & Struts */}
            <mesh position={[0, 0, 0.65]} rotation={[Math.PI / 2, 0, 0]}>
              <cylinderGeometry args={[0.06, 0.08, 0.5, 8]} />
              <meshStandardMaterial color="#b65a1f" roughness={0.3} metalness={0.7} />
            </mesh>
            {/* Antenna Gimbal Mount */}
            <mesh position={[0, -0.3, -0.2]}>
              <boxGeometry args={[0.5, 0.4, 0.4]} />
              <meshStandardMaterial color="#2c323a" roughness={0.6} metalness={0.6} />
            </mesh>
          </group>

          {/* Omni VHF/UHF Dipole Antenna Spire extending higher */}
          <mesh castShadow position={[0, 6.2, -0.4]}>
            <cylinderGeometry args={[0.025, 0.04, 2.2, 8]} />
            <meshStandardMaterial color="#252a32" roughness={0.4} metalness={0.8} />
          </mesh>
        </group>
      )}

      {/* ------------------------------------------------------------- */}
      {/* 3. FLOATING 3D AREA NAME LABEL */}
      {/* ------------------------------------------------------------- */}
      {showLabels && (
        <Html
          position={[0, sy + (code === 'COMMS' ? 3.4 : 1.2), 0]}
          center
          distanceFactor={30}
          zIndexRange={[100, 0]}
        >
          <div
            style={{
              background: 'rgba(25, 28, 32, 0.90)',
              color: '#f8f6f0',
              padding: '2px 8px',
              borderRadius: '2px',
              fontFamily: 'JetBrains Mono, monospace',
              fontSize: '11px',
              fontWeight: 700,
              letterSpacing: '0.08em',
              whiteSpace: 'nowrap',
              pointerEvents: 'none',
              border: '1px solid rgba(226, 221, 212, 0.35)',
              boxShadow: '0 3px 8px rgba(0,0,0,0.18)',
              display: 'flex',
              alignItems: 'center',
              gap: '5px'
            }}
          >
            <span
              style={{
                width: '5px',
                height: '5px',
                borderRadius: '50%',
                background: code === 'MAIN' ? '#b65a1f' : '#8c95a3'
              }}
            />
            <span>{zone.name}</span>
          </div>
        </Html>
      )}
    </group>
  );
};

export default StationZone;
