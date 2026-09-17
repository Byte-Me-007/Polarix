import React from 'react';
import { Html } from '@react-three/drei';

export const StationZone = ({ zone, showLabels = true }) => {
  const [px, py, pz] = zone.position;
  const [sx, sy, sz] = zone.size;
  const code = zone.code || zone.id;

  // Stilt footing calculations - polar foundation elevated above ground y=0
  const stiltRadius = 0.22;
  const stiltHeight = py + 0.2;
  const stiltY = -py / 2;

  // Calculate robust grid of structural pilings based on module dimensions
  const numStiltsX = Math.max(3, Math.round(sx / 4.5));
  const numStiltsZ = Math.max(2, Math.round(sz / 5.0));
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
      {/* 1. STRUCTURAL STEEL STILTS & CONCRETE FOOTING PADS            */}
      {/* ------------------------------------------------------------- */}
      {code !== 'COMMS' && stilts.map(([cx, cz], idx) => (
        <group key={`stilt-${idx}`} position={[cx, stiltY, cz]}>
          {/* Main steel column */}
          <mesh castShadow>
            <cylinderGeometry args={[stiltRadius, stiltRadius, stiltHeight, 8]} />
            <meshStandardMaterial color="#2d333b" roughness={0.7} metalness={0.5} />
          </mesh>
          {/* Concrete/Steel ground spreader pad on snow */}
          <mesh position={[0, -stiltHeight / 2 + 0.06, 0]}>
            <boxGeometry args={[0.75, 0.14, 0.75]} />
            <meshStandardMaterial color="#3d444e" roughness={0.8} metalness={0.3} />
          </mesh>
        </group>
      ))}

      {/* ------------------------------------------------------------- */}
      {/* 2. ZONE-SPECIFIC ARCHITECTURAL STRUCTURES                     */}
      {/* ------------------------------------------------------------- */}

      {/* === A. MAIN BUILDING (Central Anchor & Primary Habitat Hub) === */}
      {code === 'MAIN' && (
        <group>
          {/* Lower Habitat Tier */}
          <mesh castShadow receiveShadow position={[0, sy * 0.28, 0]}>
            <boxGeometry args={[sx, sy * 0.56, sz]} />
            <meshStandardMaterial color="#eae5dd" roughness={0.6} metalness={0.15} />
          </mesh>

          {/* Upper Habitat Tier (slightly stepped with architectural parapet) */}
          <mesh castShadow receiveShadow position={[0, sy * 0.78, 0]}>
            <boxGeometry args={[sx * 0.96, sy * 0.44, sz * 0.94]} />
            <meshStandardMaterial color="#e4ded5" roughness={0.55} metalness={0.2} />
          </mesh>

          {/* Mid-level Structural Belt Line Trim */}
          <mesh position={[0, sy * 0.56, 0]}>
            <boxGeometry args={[sx + 0.15, 0.2, sz + 0.15]} />
            <meshStandardMaterial color="#383f4a" roughness={0.7} metalness={0.4} />
          </mesh>

          {/* Roof Parapet Fascia Overhang */}
          <mesh position={[0, sy + 0.1, 0]}>
            <boxGeometry args={[sx * 0.98, 0.22, sz * 0.96]} />
            <meshStandardMaterial color="#2d333b" roughness={0.6} metalness={0.5} />
          </mesh>

          {/* Recessed Membrane Roof Deck */}
          <mesh position={[0, sy + 0.18, 0]}>
            <boxGeometry args={[sx * 0.92, 0.04, sz * 0.88]} />
            <meshStandardMaterial color="#474f5c" roughness={0.8} metalness={0.3} />
          </mesh>

          {/* South Facade Ribbon Windows (Lower & Upper) */}
          <mesh position={[0, sy * 0.35, sz / 2 + 0.03]}>
            <boxGeometry args={[sx * 0.75, 0.8, 0.05]} />
            <meshStandardMaterial color="#1a2028" roughness={0.1} metalness={0.85} />
          </mesh>
          <mesh position={[0, sy * 0.75, sz * 0.47 + 0.03]}>
            <boxGeometry args={[sx * 0.70, 0.7, 0.05]} />
            <meshStandardMaterial color="#1a2028" roughness={0.1} metalness={0.85} />
          </mesh>

          {/* North Facade Ribbon Windows */}
          <mesh position={[0, sy * 0.35, -sz / 2 - 0.03]}>
            <boxGeometry args={[sx * 0.75, 0.8, 0.05]} />
            <meshStandardMaterial color="#1a2028" roughness={0.1} metalness={0.85} />
          </mesh>

          {/* South Entry Airlock Portal & Vestibule */}
          <group position={[0, sy * 0.25, sz / 2 + 1.2]}>
            <mesh castShadow>
              <boxGeometry args={[4.4, sy * 0.5, 2.4]} />
              <meshStandardMaterial color="#dcd5cb" roughness={0.6} metalness={0.2} />
            </mesh>
            {/* Safety Orange Trim Frame */}
            <mesh position={[0, 0, 1.22]}>
              <boxGeometry args={[2.4, sy * 0.42, 0.06]} />
              <meshStandardMaterial color="#b65a1f" roughness={0.4} metalness={0.5} />
            </mesh>
          </group>

          {/* Central Rooftop HVAC & Environmental Control Plant */}
          <group position={[0, sy + 0.7, 0]}>
            <mesh castShadow position={[0, 0, 0]}>
              <boxGeometry args={[6.0, 1.2, 4.5]} />
              <meshStandardMaterial color="#c2bbb0" roughness={0.6} metalness={0.3} />
            </mesh>
            {/* Ventilation Louver Grills */}
            {[-2.0, 2.0].map((lx, i) => (
              <mesh key={`hvac-louver-${i}`} position={[lx, 0.1, 2.27]}>
                <boxGeometry args={[1.5, 0.8, 0.06]} />
                <meshStandardMaterial color="#2d333b" roughness={0.9} />
              </mesh>
            ))}
          </group>
        </group>
      )}

      {/* === B. RESEARCH BUILDING (Specialized Scientific Laboratory) === */}
      {code === 'RESEARCH' && (
        <group>
          {/* Main Laboratory Body */}
          <mesh castShadow receiveShadow position={[0, sy / 2, 0]}>
            <boxGeometry args={[sx, sy, sz]} />
            <meshStandardMaterial color="#e5ded4" roughness={0.55} metalness={0.2} />
          </mesh>

          {/* Roof Parapet Trim */}
          <mesh position={[0, sy + 0.1, 0]}>
            <boxGeometry args={[sx + 0.15, 0.2, sz + 0.15]} />
            <meshStandardMaterial color="#323944" roughness={0.6} metalness={0.4} />
          </mesh>

          {/* Laboratory Observation Ribbon Windows (South & East) */}
          <mesh position={[0, sy * 0.55, sz / 2 + 0.03]}>
            <boxGeometry args={[sx * 0.8, 0.85, 0.05]} />
            <meshStandardMaterial color="#1a2028" roughness={0.1} metalness={0.85} />
          </mesh>
          <mesh position={[sx / 2 + 0.03, sy * 0.55, 0]} rotation={[0, Math.PI / 2, 0]}>
            <boxGeometry args={[sz * 0.7, 0.85, 0.05]} />
            <meshStandardMaterial color="#1a2028" roughness={0.1} metalness={0.85} />
          </mesh>

          {/* Rooftop Scientific Optical / Lidar Observation Dome */}
          <group position={[-2.5, sy + 0.2, 1.5]}>
            {/* Base Turret Collar */}
            <mesh position={[0, 0.4, 0]}>
              <cylinderGeometry args={[2.2, 2.4, 0.8, 24]} />
              <meshStandardMaterial color="#3a424e" roughness={0.5} metalness={0.4} />
            </mesh>
            {/* Hemispherical Dome Shell */}
            <mesh castShadow position={[0, 0.8, 0]}>
              <sphereGeometry args={[2.2, 24, 16, 0, Math.PI * 2, 0, Math.PI * 0.5]} />
              <meshStandardMaterial color="#f8f6f0" roughness={0.2} metalness={0.2} />
            </mesh>
            {/* Optical Observation Slit */}
            <mesh position={[0, 1.9, 0.9]}>
              <boxGeometry args={[0.5, 2.0, 0.3]} />
              <meshStandardMaterial color="#15181c" roughness={0.2} metalness={0.8} />
            </mesh>
          </group>

          {/* Rooftop Atmospheric Chemistry Sampling Mast & Met Arm */}
          <group position={[3.5, sy + 1.6, -2.0]}>
            <mesh castShadow>
              <cylinderGeometry args={[0.12, 0.16, 3.2, 8]} />
              <meshStandardMaterial color="#2d333b" roughness={0.5} metalness={0.7} />
            </mesh>
            {/* Cross arms */}
            <mesh position={[0, 1.2, 0]}>
              <boxGeometry args={[1.8, 0.08, 0.08]} />
              <meshStandardMaterial color="#b65a1f" roughness={0.4} metalness={0.6} />
            </mesh>
          </group>

          {/* Cleanroom Air Filtration Duct Unit (East wall) */}
          <group position={[sx / 2 + 0.5, sy * 0.5, -2.0]}>
            <mesh castShadow>
              <boxGeometry args={[1.0, sy * 0.7, 3.0]} />
              <meshStandardMaterial color="#c0b8ac" roughness={0.6} metalness={0.3} />
            </mesh>
          </group>
        </group>
      )}

      {/* === C. ENERGY / POWER (Power Infrastructure & Substation) === */}
      {code === 'ENERGY' && (
        <group>
          {/* Main Power Module Body */}
          <mesh castShadow receiveShadow position={[0, sy / 2, 0]}>
            <boxGeometry args={[sx, sy, sz]} />
            <meshStandardMaterial color="#ded7cc" roughness={0.6} metalness={0.2} />
          </mesh>

          {/* Roof Parapet Trim */}
          <mesh position={[0, sy + 0.1, 0]}>
            <boxGeometry args={[sx + 0.15, 0.2, sz + 0.15]} />
            <meshStandardMaterial color="#323944" roughness={0.6} metalness={0.4} />
          </mesh>

          {/* Dual Angled Photovoltaic Solar Array Test Racks on Roof */}
          <group position={[-2.5, sy + 0.7, 0]}>
            {[-2.5, 2.5].map((zOffset, i) => (
              <group key={`pv-rack-${i}`} position={[0, 0, zOffset]} rotation={[0.35, 0, 0]}>
                {/* Solar panel frame */}
                <mesh castShadow>
                  <boxGeometry args={[7.0, 0.12, 3.2]} />
                  <meshStandardMaterial color="#182333" roughness={0.2} metalness={0.85} />
                </mesh>
                {/* Solar panel cell divider grids */}
                <mesh position={[0, 0.07, 0]}>
                  <boxGeometry args={[6.8, 0.02, 3.0]} />
                  <meshStandardMaterial color="#2d4059" roughness={0.3} metalness={0.7} />
                </mesh>
              </group>
            ))}
          </group>

          {/* High-Voltage Exterior Transformer Yard (East roof) */}
          <group position={[4.8, sy + 0.8, 0]}>
            <mesh castShadow position={[0, 0, 0]}>
              <boxGeometry args={[3.6, 1.4, 4.0]} />
              <meshStandardMaterial color="#4a5360" roughness={0.5} metalness={0.5} />
            </mesh>
            {/* Cooling Fin Banks */}
            {[-1.8, 1.8].map((fx, i) => (
              <mesh key={`xfr-fin-${i}`} position={[fx, 0, 0]}>
                <boxGeometry args={[0.1, 1.2, 3.6]} />
                <meshStandardMaterial color="#2d333b" roughness={0.8} metalness={0.4} />
              </mesh>
            ))}
          </group>

          {/* Outdoor Battery Storage Bank Enclosure Cabinets (North facade) */}
          <group position={[0, sy * 0.45, -sz / 2 - 0.7]}>
            <mesh castShadow>
              <boxGeometry args={[sx * 0.7, sy * 0.8, 1.3]} />
              <meshStandardMaterial color="#b26814" roughness={0.5} metalness={0.3} />
            </mesh>
            {/* Exhaust vents */}
            {[-3.0, 0, 3.0].map((vx, i) => (
              <mesh key={`bat-vent-${i}`} position={[vx, 0.3, -0.67]}>
                <boxGeometry args={[1.2, 0.8, 0.05]} />
                <meshStandardMaterial color="#1a1d22" roughness={0.9} />
              </mesh>
            ))}
          </group>
        </group>
      )}

      {/* === D. GENERATOR (Industrial Power Plant Facility) === */}
      {code === 'GENERATOR' && (
        <group>
          {/* Main Industrial Housing Body (Heavy ribbed panel appearance) */}
          <mesh castShadow receiveShadow position={[0, sy / 2, 0]}>
            <boxGeometry args={[sx, sy, sz]} />
            <meshStandardMaterial color="#d4ccc0" roughness={0.7} metalness={0.2} />
          </mesh>

          {/* Heavy Steel Roof Fascia */}
          <mesh position={[0, sy + 0.1, 0]}>
            <boxGeometry args={[sx + 0.15, 0.2, sz + 0.15]} />
            <meshStandardMaterial color="#2d333b" roughness={0.7} metalness={0.4} />
          </mesh>

          {/* Prominent Twin Diesel Exhaust Stacks with Rain Caps */}
          {[-2.2, 2.2].map((offX, i) => (
            <group key={`gen-exhaust-${i}`} position={[offX, sy + 2.4, -sz * 0.2]}>
              {/* Vertical Stack Column */}
              <mesh castShadow>
                <cylinderGeometry args={[0.35, 0.42, 4.8, 16]} />
                <meshStandardMaterial color="#3d444e" roughness={0.6} metalness={0.6} />
              </mesh>
              {/* Rain hood cap */}
              <mesh position={[0, 2.5, 0]}>
                <coneGeometry args={[0.65, 0.45, 16]} />
                <meshStandardMaterial color="#22262c" roughness={0.5} metalness={0.5} />
              </mesh>
            </group>
          ))}

          {/* Massive Western Cooling Radiator & Ventilation Louver Bank */}
          <group position={[-sx / 2 - 0.6, sy * 0.5, 0]}>
            <mesh castShadow>
              <boxGeometry args={[1.2, sy * 0.8, sz * 0.75]} />
              <meshStandardMaterial color="#373d47" roughness={0.8} metalness={0.4} />
            </mesh>
            {/* Louver Grill Shroud */}
            <mesh position={[-0.62, 0, 0]}>
              <boxGeometry args={[0.06, sy * 0.7, sz * 0.68]} />
              <meshStandardMaterial color="#1a1d22" roughness={0.9} />
            </mesh>
          </group>

          {/* Heavy Cylindrical Fuel Day-Tank on Structural Saddles (South facade) */}
          <group position={[0, sy * 0.4, sz / 2 + 1.2]} rotation={[0, 0, Math.PI / 2]}>
            {/* Tank Cylinder */}
            <mesh castShadow>
              <cylinderGeometry args={[1.0, 1.0, 6.5, 20]} />
              <meshStandardMaterial color="#7a7062" roughness={0.5} metalness={0.5} />
            </mesh>
            {/* Domed End Caps */}
            <mesh position={[0, 3.3, 0]}>
              <sphereGeometry args={[1.0, 20, 10, 0, Math.PI * 2, 0, Math.PI / 2]} />
              <meshStandardMaterial color="#63594c" roughness={0.5} metalness={0.5} />
            </mesh>
            <mesh position={[0, -3.3, 0]} rotation={[Math.PI, 0, 0]}>
              <sphereGeometry args={[1.0, 20, 10, 0, Math.PI * 2, 0, Math.PI / 2]} />
              <meshStandardMaterial color="#63594c" roughness={0.5} metalness={0.5} />
            </mesh>
          </group>
        </group>
      )}

      {/* === E. STORAGE (Logistics Warehouse & Cold Provisions Bay) === */}
      {code === 'STORAGE' && (
        <group>
          {/* Main Warehouse Enclosure */}
          <mesh castShadow receiveShadow position={[0, sy / 2, 0]}>
            <boxGeometry args={[sx, sy, sz]} />
            <meshStandardMaterial color="#cfc7b9" roughness={0.65} metalness={0.2} />
          </mesh>

          {/* Roof Parapet Trim */}
          <mesh position={[0, sy + 0.1, 0]}>
            <boxGeometry args={[sx + 0.15, 0.2, sz + 0.15]} />
            <meshStandardMaterial color="#323944" roughness={0.7} metalness={0.3} />
          </mesh>

          {/* Horizontal Polar Container Ribbing Lines */}
          {[-1.2, -0.4, 0.4, 1.2].map((yOff, i) => (
            <mesh key={`stor-rib-${i}`} position={[0, sy / 2 + yOff, sz / 2 + 0.04]}>
              <boxGeometry args={[sx * 0.94, 0.2, 0.06]} />
              <meshStandardMaterial color="#b5ad9e" roughness={0.6} metalness={0.3} />
            </mesh>
          ))}

          {/* Heavy Logistics Overhead Cargo Door (East facade) */}
          <group position={[sx / 2 + 0.04, sy * 0.45, 0]}>
            <mesh>
              <boxGeometry args={[0.06, sy * 0.75, sz * 0.65]} />
              <meshStandardMaterial color="#2d333b" roughness={0.8} metalness={0.4} />
            </mesh>
            {/* Safety Yellow Outline Strip */}
            <mesh position={[0.04, 0, 0]}>
              <boxGeometry args={[0.02, sy * 0.78, sz * 0.68]} />
              <meshStandardMaterial color="#b65a1f" roughness={0.4} metalness={0.6} />
            </mesh>
          </group>

          {/* Exterior Cargo Staging Platform with Supply Pallet & Drums */}
          <group position={[sx / 2 + 2.0, 0.4, 0]}>
            <mesh receiveShadow>
              <boxGeometry args={[3.2, 0.3, 5.5]} />
              <meshStandardMaterial color="#4a4237" roughness={0.9} />
            </mesh>
            {/* Supplies Cargo Pod */}
            <mesh castShadow position={[0, 0.85, 0]}>
              <boxGeometry args={[2.0, 1.4, 3.5]} />
              <meshStandardMaterial color="#887967" roughness={0.7} />
            </mesh>
          </group>
        </group>
      )}

      {/* === F. COMMS (Telecommunications Facility, Mast & Dish) === */}
      {code === 'COMMS' && (
        <group>
          {/* Base RF Telemetry Operations Shelter */}
          <mesh castShadow receiveShadow position={[0, sy / 2, 0]}>
            <boxGeometry args={[sx, sy, sz]} />
            <meshStandardMaterial color="#dcd5c9" roughness={0.6} metalness={0.2} />
          </mesh>

          {/* Base Parapet Trim */}
          <mesh position={[0, sy + 0.08, 0]}>
            <boxGeometry args={[sx + 0.12, 0.16, sz + 0.12]} />
            <meshStandardMaterial color="#333842" roughness={0.6} metalness={0.5} />
          </mesh>

          {/* Heavy Steel Mast Pedestal Collar */}
          <mesh position={[0, sy + 0.35, 0]}>
            <cylinderGeometry args={[2.0, 2.5, 0.5, 16]} />
            <meshStandardMaterial color="#2b313b" roughness={0.6} metalness={0.6} />
          </mesh>

          {/* Open-Truss Structural Communications Mast (Rising high above station) */}
          <group position={[0, sy + 6.0, 0]}>
            {/* Central Mast Column */}
            <mesh castShadow>
              <cylinderGeometry args={[0.35, 0.6, 11.0, 8]} />
              <meshStandardMaterial color="#3e4652" roughness={0.5} metalness={0.7} />
            </mesh>
            {/* 4 Outer Truss Corner Chords */}
            {[
              [-1.0, -1.0],
              [1.0, -1.0],
              [-1.0, 1.0],
              [1.0, 1.0]
            ].map(([tx, tz], i) => (
              <mesh key={`comms-chord-${i}`} position={[tx, 0, tz]}>
                <cylinderGeometry args={[0.08, 0.1, 11.0, 6]} />
                <meshStandardMaterial color="#2d333b" roughness={0.6} metalness={0.6} />
              </mesh>
            ))}
          </group>

          {/* Large Parabolic Ku-Band Satellite Tracking Dish (Angled skyward) */}
          <group position={[0, sy + 7.5, 1.2]} rotation={[0.42, 0, 0]}>
            {/* Dish Reflector Bowl (Diameter ~4.4 units) */}
            <mesh castShadow>
              <sphereGeometry args={[2.2, 24, 16, 0, Math.PI * 2, 0, Math.PI * 0.42]} />
              <meshStandardMaterial color="#ede8df" roughness={0.3} metalness={0.3} side={2} />
            </mesh>
            {/* Central Sub-reflector Feed Horn & Quad-Struts */}
            <mesh position={[0, 0, 1.1]} rotation={[Math.PI / 2, 0, 0]}>
              <cylinderGeometry args={[0.12, 0.16, 1.0, 8]} />
              <meshStandardMaterial color="#b65a1f" roughness={0.3} metalness={0.7} />
            </mesh>
            {/* Antenna Gimbal Drive Box */}
            <mesh position={[0, -0.6, -0.4]}>
              <boxGeometry args={[1.2, 1.0, 1.0]} />
              <meshStandardMaterial color="#282d36" roughness={0.6} metalness={0.6} />
            </mesh>
          </group>

          {/* High-Altitude VHF/UHF Omnidirectional Dipole Spire */}
          <mesh castShadow position={[0, sy + 13.0, -0.8]}>
            <cylinderGeometry args={[0.05, 0.08, 5.0, 8]} />
            <meshStandardMaterial color="#22262e" roughness={0.4} metalness={0.8} />
          </mesh>
        </group>
      )}

      {/* ------------------------------------------------------------- */}
      {/* 3. 3D MODULE IDENTIFIER BADGE                                 */}
      {/* ------------------------------------------------------------- */}
      {showLabels && (
        <Html
          position={[0, sy + (code === 'COMMS' ? 9.5 : 2.2), 0]}
          center
          distanceFactor={42}
          zIndexRange={[100, 0]}
        >
          <div
            style={{
              background: 'rgba(25, 28, 32, 0.92)',
              color: '#f8f6f0',
              padding: '3px 10px',
              borderRadius: '3px',
              fontFamily: 'JetBrains Mono, monospace',
              fontSize: '12px',
              fontWeight: 700,
              letterSpacing: '0.08em',
              whiteSpace: 'nowrap',
              pointerEvents: 'none',
              border: '1px solid rgba(226, 221, 212, 0.35)',
              boxShadow: '0 4px 10px rgba(0,0,0,0.22)',
              display: 'flex',
              alignItems: 'center',
              gap: '6px'
            }}
          >
            <span
              style={{
                width: '6px',
                height: '6px',
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
