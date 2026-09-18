import React, { useMemo } from 'react';
import * as THREE from 'three';

/**
 * Photorealistic Architectural Infrastructure Components for Polaris Antarctic Station
 * Based on authentic polar scientific facilities (Bharati, Maitri, Halley VI, Amundsen-Scott)
 */

// ============================================================================
// 1. ROOFTOP PHOTOVOLTAIC SOLAR ARRAY (Tilted PV Panels on Aluminum Rack)
// ============================================================================
export const SolarPanelArray = ({
  rows = 2,
  cols = 3,
  panelWidth = 2.4,
  panelHeight = 3.6,
  tiltAngle = 0.35, // ~20 degrees
  position = [0, 0, 0],
  rotation = [0, 0, 0],
  spacing = 0.25,
  rackColor = '#718096',
  cellColor = '#0f1f38',
  frameColor = '#a0aec0',
  opacity = 1.0,
  depthWrite = true
}) => {
  const isTransparent = opacity < 1.0;

  // Calculate panel grid
  const panels = useMemo(() => {
    const list = [];
    const totalW = cols * panelWidth + (cols - 1) * spacing;
    const totalH = rows * panelHeight + (rows - 1) * spacing;
    const startX = -totalW / 2 + panelWidth / 2;
    const startZ = -totalH / 2 + panelHeight / 2;

    for (let r = 0; r < rows; r++) {
      for (let c = 0; c < cols; c++) {
        list.push({
          x: startX + c * (panelWidth + spacing),
          z: startZ + r * (panelHeight + spacing),
          id: `p-${r}-${c}`
        });
      }
    }
    return { list, totalW, totalH };
  }, [rows, cols, panelWidth, panelHeight, spacing]);

  return (
    <group position={position} rotation={rotation}>
      {/* Aluminum Structural Mounting Racks (Truss Rails under panels) */}
      {[-panels.totalW * 0.42, 0, panels.totalW * 0.42].map((rx, idx) => (
        <group key={`rack-${idx}`} position={[rx, 0.3, 0]}>
          {/* Longitudinal rail tilted */}
          <mesh rotation={[tiltAngle, 0, 0]} castShadow>
            <boxGeometry args={[0.12, 0.12, panels.totalH * 1.08]} />
            <meshStandardMaterial
              color={rackColor}
              metalness={0.7}
              roughness={0.35}
              transparent={isTransparent}
              opacity={opacity}
              depthWrite={depthWrite}
            />
          </mesh>
          {/* Front short stanchion */}
          <mesh position={[0, 0.2, panels.totalH * 0.4]}>
            <cylinderGeometry args={[0.05, 0.05, 0.4, 6]} />
            <meshStandardMaterial
              color={rackColor}
              metalness={0.7}
              roughness={0.4}
              transparent={isTransparent}
              opacity={opacity}
              depthWrite={depthWrite}
            />
          </mesh>
          {/* Rear tall stanchion (creating the tilt angle) */}
          <mesh position={[0, panels.totalH * 0.4 * Math.sin(tiltAngle) + 0.2, -panels.totalH * 0.4]}>
            <cylinderGeometry args={[0.05, 0.05, panels.totalH * 0.8 * Math.sin(tiltAngle) + 0.4, 6]} />
            <meshStandardMaterial
              color={rackColor}
              metalness={0.7}
              roughness={0.4}
              transparent={isTransparent}
              opacity={opacity}
              depthWrite={depthWrite}
            />
          </mesh>
        </group>
      ))}

      {/* Photovoltaic Solar Panels */}
      {panels.list.map((p) => (
        <group
          key={p.id}
          position={[p.x, 0.45 + (p.z * -Math.sin(tiltAngle)), p.z * Math.cos(tiltAngle)]}
          rotation={[tiltAngle, 0, 0]}
        >
          {/* Aluminum Outer Frame */}
          <mesh castShadow>
            <boxGeometry args={[panelWidth, 0.08, panelHeight]} />
            <meshStandardMaterial
              color="#cbd5e1"
              metalness={0.8}
              roughness={0.25}
              transparent={isTransparent}
              opacity={opacity}
              depthWrite={depthWrite}
            />
          </mesh>

          {/* Deep Photovoltaic Silicon Wafer Surface (Vibrant Solar Blue) */}
          <mesh position={[0, 0.045, 0]}>
            <boxGeometry args={[panelWidth - 0.10, 0.02, panelHeight - 0.10]} />
            <meshStandardMaterial
              color="#1d4ed8"
              emissive="#1e3a8a"
              emissiveIntensity={0.35}
              metalness={0.85}
              roughness={0.15}
              transparent={isTransparent}
              opacity={opacity}
              depthWrite={depthWrite}
            />
          </mesh>

          {/* Silicon Cell Grid Lines (Silver Busbars) */}
          {[-0.6, 0, 0.6].map((bx, bi) => (
            <mesh key={`bb-${bi}`} position={[bx, 0.058, 0]}>
              <boxGeometry args={[0.025, 0.01, panelHeight - 0.14]} />
              <meshStandardMaterial
                color="#f8fafc"
                metalness={0.9}
                roughness={0.2}
                transparent={isTransparent}
                opacity={opacity}
                depthWrite={depthWrite}
              />
            </mesh>
          ))}

          {/* Horizontal Cell Interconnect Lines */}
          {[-1.2, -0.6, 0, 0.6, 1.2].map((bz, bi) => (
            <mesh key={`hw-${bi}`} position={[0, 0.058, bz]}>
              <boxGeometry args={[panelWidth - 0.14, 0.01, 0.025]} />
              <meshStandardMaterial
                color="#94a3b8"
                metalness={0.8}
                roughness={0.25}
                transparent={isTransparent}
                opacity={opacity * 0.8}
                depthWrite={depthWrite}
              />
            </mesh>
          ))}
        </group>
      ))}
    </group>
  );
};

// ============================================================================
// 2. COMMERCIAL ROOFTOP HVAC AIR-HANDLING UNIT (Dual/Single Condenser Fans)
// ============================================================================
export const RooftopHVACUnit = ({
  fans = 2,
  width = 4.8,
  height = 1.8,
  depth = 3.2,
  position = [0, 0, 0],
  rotation = [0, 0, 0],
  bodyColor = '#e2e8f0',
  fanColor = '#1e293b',
  pipeColor = '#b45309', // copper / insulated lines
  opacity = 1.0,
  depthWrite = true
}) => {
  const isTransparent = opacity < 1.0;
  const fanSpacing = width / (fans + 1);

  return (
    <group position={position} rotation={rotation}>
      {/* Vibration Damping Base Curb */}
      <mesh position={[0, 0.12, 0]} castShadow>
        <boxGeometry args={[width + 0.3, 0.24, depth + 0.3]} />
        <meshStandardMaterial
          color="#334155"
          roughness={0.8}
          metalness={0.3}
          transparent={isTransparent}
          opacity={opacity}
          depthWrite={depthWrite}
        />
      </mesh>

      {/* Main Sheet Metal Equipment Enclosure */}
      <mesh position={[0, height / 2 + 0.24, 0]} castShadow receiveShadow>
        <boxGeometry args={[width, height, depth]} />
        <meshStandardMaterial
          color={bodyColor}
          roughness={0.45}
          metalness={0.4}
          transparent={isTransparent}
          opacity={opacity}
          depthWrite={depthWrite}
        />
      </mesh>

      {/* Condenser Coil Louvered Side Panels (Front & Back) */}
      {[-depth / 2 - 0.02, depth / 2 + 0.02].map((zPos, zi) => (
        <group key={`louver-z-${zi}`} position={[0, height / 2 + 0.24, zPos]}>
          <mesh>
            <planeGeometry args={[width * 0.85, height * 0.7]} />
            <meshStandardMaterial
              color="#1e293b"
              roughness={0.7}
              metalness={0.5}
              transparent={isTransparent}
              opacity={opacity}
              depthWrite={depthWrite}
            />
          </mesh>
          {/* Louver Blades */}
          {[-0.4, -0.2, 0, 0.2, 0.4].map((ly, li) => (
            <mesh key={`lblade-${li}`} position={[0, ly, 0.01]}>
              <boxGeometry args={[width * 0.82, 0.03, 0.02]} />
              <meshStandardMaterial
                color="#475569"
                metalness={0.6}
                roughness={0.4}
                transparent={isTransparent}
                opacity={opacity}
                depthWrite={depthWrite}
              />
            </mesh>
          ))}
        </group>
      ))}

      {/* Top Condenser Fans with Cowling & Grilles */}
      {Array.from({ length: fans }).map((_, fi) => {
        const fx = -width / 2 + (fi + 1) * fanSpacing;
        return (
          <group key={`fan-${fi}`} position={[fx, height + 0.24, 0]}>
            {/* Raised Circular Cowling Collar */}
            <mesh position={[0, 0.12, 0]} castShadow>
              <cylinderGeometry args={[0.9, 0.96, 0.24, 24, 1, true]} />
              <meshStandardMaterial
                color="#334155"
                metalness={0.6}
                roughness={0.4}
                side={THREE.DoubleSide}
                transparent={isTransparent}
                opacity={opacity}
                depthWrite={depthWrite}
              />
            </mesh>

            {/* Fan Recess Floor */}
            <mesh position={[0, 0.02, 0]}>
              <cylinderGeometry args={[0.88, 0.88, 0.04, 24]} />
              <meshStandardMaterial
                color="#0f172a"
                metalness={0.8}
                roughness={0.2}
                transparent={isTransparent}
                opacity={opacity}
                depthWrite={depthWrite}
              />
            </mesh>

            {/* Protective Heavy Wire Fan Grille (Concentric Rings) */}
            {[0.3, 0.6, 0.85].map((gr, gi) => (
              <mesh key={`gr-${gi}`} position={[0, 0.22, 0]} rotation={[Math.PI / 2, 0, 0]}>
                <torusGeometry args={[gr, 0.02, 6, 24]} />
                <meshStandardMaterial
                  color="#94a3b8"
                  metalness={0.85}
                  roughness={0.3}
                  transparent={isTransparent}
                  opacity={opacity}
                  depthWrite={depthWrite}
                />
              </mesh>
            ))}

            {/* Fan Center Motor Hub */}
            <mesh position={[0, 0.14, 0]}>
              <cylinderGeometry args={[0.22, 0.22, 0.16, 16]} />
              <meshStandardMaterial
                color="#1e293b"
                metalness={0.7}
                roughness={0.3}
                transparent={isTransparent}
                opacity={opacity}
                depthWrite={depthWrite}
              />
            </mesh>

            {/* Cross Spider Brackets */}
            <mesh position={[0, 0.23, 0]}>
              <boxGeometry args={[1.75, 0.025, 0.04]} />
              <meshStandardMaterial color="#64748b" metalness={0.7} roughness={0.4} />
            </mesh>
            <mesh position={[0, 0.23, 0]}>
              <boxGeometry args={[0.04, 0.025, 1.75]} />
              <meshStandardMaterial color="#64748b" metalness={0.7} roughness={0.4} />
            </mesh>
          </group>
        );
      })}

      {/* Electrical Service Disconnect Box */}
      <group position={[width / 2 + 0.12, height * 0.6, 0.4]}>
        <mesh castShadow>
          <boxGeometry args={[0.24, 0.7, 0.45]} />
          <meshStandardMaterial color="#475569" metalness={0.5} roughness={0.5} />
        </mesh>
        <mesh position={[0.13, 0.1, 0]}>
          <boxGeometry args={[0.04, 0.15, 0.08]} />
          <meshStandardMaterial color="#e2e8f0" metalness={0.8} />
        </mesh>
      </group>

      {/* Insulated Refrigerant & Chilled Water Lines Penetrating Roof */}
      <group position={[-width / 2 - 0.2, 0.4, -0.5]}>
        {/* Horizontal run */}
        <mesh rotation={[0, 0, Math.PI / 2]}>
          <cylinderGeometry args={[0.08, 0.08, 0.6, 12]} />
          <meshStandardMaterial color={pipeColor} metalness={0.65} roughness={0.3} />
        </mesh>
        {/* 90-degree elbow to roof */}
        <mesh position={[-0.3, -0.2, 0]}>
          <cylinderGeometry args={[0.08, 0.08, 0.5, 12]} />
          <meshStandardMaterial color={pipeColor} metalness={0.65} roughness={0.3} />
        </mesh>
      </group>
    </group>
  );
};

// ============================================================================
// 3. EXPEDITION AIRLOCK ENTRANCE MODULE (With Sealed Hatch, Screens & Stairs)
// ============================================================================
export const AirlockEntranceModule = ({
  width = 5.6,
  height = 5.2,
  depth = 3.6,
  position = [0, 0, 0],
  stairElevation = 3.8,
  opacity = 1.0,
  depthWrite = true
}) => {
  const isTransparent = opacity < 1.0;

  return (
    <group position={position}>
      {/* Insulated Vestibule Shell */}
      <mesh position={[0, height / 2, depth / 2]} castShadow receiveShadow>
        <boxGeometry args={[width, height, depth]} />
        <meshStandardMaterial
          color="#f1f5f9"
          roughness={0.3}
          metalness={0.2}
          transparent={isTransparent}
          opacity={opacity}
          depthWrite={depthWrite}
        />
      </mesh>

      {/* Exterior Architectural Frame / Bevel Collar */}
      <mesh position={[0, height / 2, depth + 0.06]}>
        <boxGeometry args={[width + 0.25, height + 0.25, 0.12]} />
        <meshStandardMaterial
          color="#334155"
          roughness={0.5}
          metalness={0.5}
          transparent={isTransparent}
          opacity={opacity}
          depthWrite={depthWrite}
        />
      </mesh>

      {/* Heavy Sealed Arctic Airlock Hatch */}
      <group position={[0, height / 2, depth + 0.14]}>
        {/* Door Frame with Illuminated Status Beacon Border */}
        <mesh>
          <boxGeometry args={[2.2, 3.6, 0.12]} />
          <meshStandardMaterial
            color="#1e293b"
            roughness={0.4}
            metalness={0.7}
            transparent={isTransparent}
            opacity={opacity}
            depthWrite={depthWrite}
          />
        </mesh>

        {/* Status Light Trim (Green nominal status border) */}
        <mesh position={[0, 0, 0.07]}>
          <boxGeometry args={[2.0, 3.4, 0.02]} />
          <meshStandardMaterial
            color="#059669"
            emissive="#10b981"
            emissiveIntensity={0.6}
            roughness={0.2}
          />
        </mesh>

        {/* Stainless Steel Heavy Pressure Door Core */}
        <mesh position={[0, 0, 0.09]}>
          <boxGeometry args={[1.7, 3.1, 0.06]} />
          <meshStandardMaterial
            color="#cbd5e1"
            metalness={0.85}
            roughness={0.25}
          />
        </mesh>

        {/* Multi-pane Heated Observation Glass Window */}
        <mesh position={[0, 0.6, 0.13]}>
          <boxGeometry args={[0.55, 0.8, 0.04]} />
          <meshStandardMaterial
            color="#0284c7"
            metalness={0.9}
            roughness={0.1}
            emissive="#0369a1"
            emissiveIntensity={0.25}
          />
        </mesh>

        {/* Industrial Locking Wheel / Lever */}
        <mesh position={[0.6, 0, 0.15]} rotation={[0, 0, 0.4]}>
          <cylinderGeometry args={[0.08, 0.08, 0.5, 8]} />
          <meshStandardMaterial color="#f97316" metalness={0.7} roughness={0.3} />
        </mesh>
      </group>

      {/* Outdoor Biometric / Status Terminal Screens (Left & Right) */}
      {[-width * 0.38, width * 0.38].map((tx, ti) => (
        <group key={`screen-${ti}`} position={[tx, height * 0.55, depth + 0.2]}>
          {/* Articulated Steel Mounting Arm */}
          <mesh position={[ti === 0 ? 0.2 : -0.2, 0, -0.15]}>
            <boxGeometry args={[0.3, 0.08, 0.3]} />
            <meshStandardMaterial color="#475569" metalness={0.8} />
          </mesh>

          {/* Screen Ruggedized Metal Housing */}
          <mesh castShadow>
            <boxGeometry args={[0.9, 0.65, 0.1]} />
            <meshStandardMaterial color="#1e293b" roughness={0.4} metalness={0.6} />
          </mesh>

          {/* Active Terminal Display (Emissive HUD glowing screen) */}
          <mesh position={[0, 0, 0.055]}>
            <planeGeometry args={[0.8, 0.55]} />
            <meshStandardMaterial
              color="#0f172a"
              emissive={ti === 0 ? '#10b981' : '#0284c7'}
              emissiveIntensity={0.55}
              roughness={0.2}
            />
          </mesh>
        </group>
      ))}

      {/* Exterior Galvanized Steel Grating Entrance Porch */}
      <group position={[0, 0, depth + 2.2]}>
        {/* Diamond Grip Deck Plate */}
        <mesh position={[0, 0.15, 0]} receiveShadow>
          <boxGeometry args={[width * 1.05, 0.3, 3.8]} />
          <meshStandardMaterial
            color="#334155"
            roughness={0.85}
            metalness={0.4}
            transparent={isTransparent}
            opacity={opacity}
            depthWrite={depthWrite}
          />
        </mesh>

        {/* High-Visibility Copper / Orange Perimeter Edge Trim */}
        <mesh position={[0, 0.32, 1.9]}>
          <boxGeometry args={[width * 1.05, 0.06, 0.15]} />
          <meshStandardMaterial color="#b45309" metalness={0.6} roughness={0.4} />
        </mesh>

        {/* Safety Railings (Left, Right, and Front openings) */}
        {[-width * 0.51, width * 0.51].map((rx, ri) => (
          <group key={`airlock-rail-${ri}`} position={[rx, 1.0, 0]}>
            {/* Top rail */}
            <mesh>
              <boxGeometry args={[0.08, 0.08, 3.8]} />
              <meshStandardMaterial color="#b45309" metalness={0.6} roughness={0.35} />
            </mesh>
            {/* Mid rail */}
            <mesh position={[0, -0.4, 0]}>
              <boxGeometry args={[0.06, 0.06, 3.8]} />
              <meshStandardMaterial color="#64748b" metalness={0.7} />
            </mesh>
            {/* Vertical stanchions */}
            {[-1.6, 0, 1.6].map((sz, si) => (
              <mesh key={`post-${si}`} position={[0, -0.45, sz]}>
                <cylinderGeometry args={[0.05, 0.05, 0.9, 8]} />
                <meshStandardMaterial color="#334155" metalness={0.7} />
              </mesh>
            ))}
          </group>
        ))}

        {/* Industrial Grating Stairs Descending to Snow Datum */}
        <group position={[0, 0, 2.0]}>
          {Array.from({ length: 5 }).map((_, stepIdx) => {
            const stepY = -stepIdx * (stairElevation / 5.2);
            const stepZ = (stepIdx + 1) * 0.75;
            return (
              <group key={`step-${stepIdx}`} position={[0, stepY, stepZ]}>
                {/* Tread */}
                <mesh castShadow receiveShadow>
                  <boxGeometry args={[3.2, 0.16, 0.7]} />
                  <meshStandardMaterial color="#1e293b" roughness={0.8} metalness={0.5} />
                </mesh>
                {/* Tread nosing */}
                <mesh position={[0, 0.08, 0.35]}>
                  <boxGeometry args={[3.2, 0.04, 0.06]} />
                  <meshStandardMaterial color="#b45309" metalness={0.5} />
                </mesh>
              </group>
            );
          })}
        </group>

        {/* Diagonal Under-porch Support Space Truss */}
        {[-width * 0.35, width * 0.35].map((sx, si) => (
          <mesh
            key={`porch-brace-${si}`}
            position={[sx, -stairElevation * 0.5, 0.8]}
            rotation={[0.45, 0, 0]}
          >
            <cylinderGeometry args={[0.12, 0.12, stairElevation * 1.3, 8]} />
            <meshStandardMaterial color="#1e293b" metalness={0.7} roughness={0.4} />
          </mesh>
        ))}
      </group>
    </group>
  );
};

// ============================================================================
// 4. HIGH-TECH PARABOLIC SATELLITE TRACKING DISH ASSEMBLY
// ============================================================================
export const ParabolicDishAssembly = ({
  radius = 2.4,
  position = [0, 0, 0],
  azimuth = 0.3,
  elevation = 0.45,
  dishColor = '#f8fafc',
  yokeColor = '#1e293b',
  feedColor = '#b45309',
  opacity = 1.0,
  depthWrite = true
}) => {
  const isTransparent = opacity < 1.0;

  return (
    <group position={position} rotation={[0, azimuth, 0]}>
      {/* Heavy Steel Pedestal Mounting Base */}
      <mesh position={[0, 0.35, 0]} castShadow>
        <cylinderGeometry args={[0.7, 0.9, 0.7, 16]} />
        <meshStandardMaterial
          color={yokeColor}
          metalness={0.7}
          roughness={0.4}
          transparent={isTransparent}
          opacity={opacity}
          depthWrite={depthWrite}
        />
      </mesh>

      {/* Dual-Axis Gimbal Yoke */}
      <group position={[0, 0.85, 0]}>
        {/* Azimuth Rotor Hub */}
        <mesh position={[0, 0.2, 0]}>
          <cylinderGeometry args={[0.55, 0.55, 0.4, 16]} />
          <meshStandardMaterial color="#334155" metalness={0.8} roughness={0.3} />
        </mesh>

        {/* Dual Support Yoke Arms */}
        {[-0.65, 0.65].map((yx, yi) => (
          <mesh key={`yoke-arm-${yi}`} position={[yx, 0.75, 0]}>
            <boxGeometry args={[0.18, 0.95, 0.35]} />
            <meshStandardMaterial color={yokeColor} metalness={0.7} roughness={0.4} />
          </mesh>
        ))}

        {/* Tilted Elevation Head (Parabolic Dish + Feed Horn) */}
        <group position={[0, 1.1, 0]} rotation={[elevation, 0, 0]}>
          {/* Parabolic Reflector Dish (Curved Shell) */}
          <mesh castShadow receiveShadow>
            <sphereGeometry args={[radius, 32, 16, 0, Math.PI * 2, 0, Math.PI * 0.38]} />
            <meshStandardMaterial
              color={dishColor}
              metalness={0.4}
              roughness={0.25}
              side={THREE.DoubleSide}
              transparent={isTransparent}
              opacity={opacity}
              depthWrite={depthWrite}
            />
          </mesh>

          {/* Dish Aluminum Rim Reinforcing Ring */}
          <mesh position={[0, 0, radius * (1 - Math.cos(Math.PI * 0.38))]} rotation={[Math.PI / 2, 0, 0]}>
            <torusGeometry args={[radius * Math.sin(Math.PI * 0.38), 0.045, 8, 32]} />
            <meshStandardMaterial color="#64748b" metalness={0.8} />
          </mesh>

          {/* Rear Stiffener Rib Ring */}
          <mesh position={[0, 0, -0.3]}>
            <cylinderGeometry args={[0.9, 1.2, 0.3, 16]} />
            <meshStandardMaterial color={yokeColor} metalness={0.7} roughness={0.4} />
          </mesh>

          {/* Feed Horn Support Struts (Quad-pod) */}
          {[0, Math.PI / 2, Math.PI, (3 * Math.PI) / 2].map((angle, ai) => {
            const strutR = radius * 0.65;
            const sx = Math.cos(angle) * strutR;
            const sy = Math.sin(angle) * strutR;
            return (
              <mesh
                key={`dish-strut-${ai}`}
                position={[sx * 0.5, sy * 0.5, radius * 0.6]}
                rotation={[sy > 0 ? -0.4 : 0.4, sx > 0 ? 0.4 : -0.4, 0]}
              >
                <cylinderGeometry args={[0.035, 0.035, radius * 0.9, 6]} />
                <meshStandardMaterial color="#64748b" metalness={0.8} />
              </mesh>
            );
          })}

          {/* Primary Sub-reflector & LNB Feed Horn */}
          <group position={[0, 0, radius * 0.95]}>
            <mesh rotation={[Math.PI / 2, 0, 0]}>
              <cylinderGeometry args={[0.18, 0.28, 0.35, 16]} />
              <meshStandardMaterial color={feedColor} metalness={0.8} roughness={0.25} />
            </mesh>
            <mesh position={[0, 0, 0.2]}>
              <sphereGeometry args={[0.14, 16, 12]} />
              <meshStandardMaterial color="#0f172a" metalness={0.9} />
            </mesh>
          </group>
        </group>
      </group>
    </group>
  );
};

// ============================================================================
// 5. STEEL OPEN-LATTICE COMMUNICATIONS & METEOROLOGICAL TOWER
// ============================================================================
export const LatticeTower = ({
  height = 10.0,
  baseWidth = 2.2,
  topWidth = 0.9,
  sections = 4,
  position = [0, 0, 0],
  steelColor = '#475569',
  hasMetGear = true,
  opacity = 1.0,
  depthWrite = true
}) => {
  const isTransparent = opacity < 1.0;
  const sectionHeight = height / sections;

  return (
    <group position={position}>
      {/* 4 Main Corner Steel Chords */}
      {[-1, 1].map((cx) =>
        [-1, 1].map((cz) => {
          const key = `chord-${cx}-${cz}`;
          return (
            <mesh
              key={key}
              position={[
                (cx * (baseWidth + topWidth)) / 4,
                height / 2,
                (cz * (baseWidth + topWidth)) / 4
              ]}
              rotation={[
                cz * Math.atan2((baseWidth - topWidth) / 2, height),
                0,
                -cx * Math.atan2((baseWidth - topWidth) / 2, height)
              ]}
              castShadow
            >
              <cylinderGeometry args={[0.08, 0.12, height, 8]} />
              <meshStandardMaterial
                color={steelColor}
                metalness={0.8}
                roughness={0.35}
                transparent={isTransparent}
                opacity={opacity}
                depthWrite={depthWrite}
              />
            </mesh>
          );
        })
      )}

      {/* Horizontal & Diagonal Cross Bracing (X-truss) Per Section */}
      {Array.from({ length: sections }).map((_, secIdx) => {
        const secY = (secIdx + 0.5) * sectionHeight;
        const currentW = baseWidth - (secIdx / sections) * (baseWidth - topWidth);
        return (
          <group key={`sec-${secIdx}`} position={[0, secY, 0]}>
            {/* Horizontal Perimeter Framing */}
            {[-1, 1].map((hx) => (
              <mesh key={`h-x-${hx}`} position={[hx * currentW * 0.48, 0, 0]}>
                <boxGeometry args={[0.06, 0.06, currentW]} />
                <meshStandardMaterial color={steelColor} metalness={0.7} roughness={0.4} />
              </mesh>
            ))}
            {[-1, 1].map((hz) => (
              <mesh key={`h-z-${hz}`} position={[0, 0, hz * currentW * 0.48]}>
                <boxGeometry args={[currentW, 0.06, 0.06]} />
                <meshStandardMaterial color={steelColor} metalness={0.7} roughness={0.4} />
              </mesh>
            ))}
            {/* Diagonal X-struts */}
            <mesh rotation={[0, 0, 0.55]}>
              <boxGeometry args={[0.045, sectionHeight * 1.05, 0.045]} />
              <meshStandardMaterial color={steelColor} metalness={0.7} roughness={0.4} />
            </mesh>
            <mesh rotation={[0, 0, -0.55]}>
              <boxGeometry args={[0.045, sectionHeight * 1.05, 0.045]} />
              <meshStandardMaterial color={steelColor} metalness={0.7} roughness={0.4} />
            </mesh>
          </group>
        );
      })}

      {/* Top Work Platform with Grating & Railing */}
      <group position={[0, height, 0]}>
        <mesh>
          <boxGeometry args={[topWidth * 1.6, 0.1, topWidth * 1.6]} />
          <meshStandardMaterial color="#1e293b" metalness={0.8} roughness={0.3} />
        </mesh>
        {/* Platform Railing */}
        {[-1, 1].map((rx) => (
          <mesh key={`top-rail-${rx}`} position={[rx * topWidth * 0.75, 0.4, 0]}>
            <boxGeometry args={[0.05, 0.05, topWidth * 1.5]} />
            <meshStandardMaterial color="#f97316" metalness={0.6} />
          </mesh>
        ))}
      </group>

      {/* Meteorological Instruments & Omnidirectional Whip Antenna */}
      {hasMetGear && (
        <group position={[0, height + 0.1, 0]}>
          {/* Central Lightning Arrester / Whip Antenna Spire */}
          <mesh position={[0, 2.5, 0]} castShadow>
            <cylinderGeometry args={[0.03, 0.06, 5.0, 8]} />
            <meshStandardMaterial color="#cbd5e1" metalness={0.9} roughness={0.2} />
          </mesh>

          {/* Cross Meteorological Sensor Arm */}
          <mesh position={[0, 1.2, 0]}>
            <boxGeometry args={[1.8, 0.06, 0.06]} />
            <meshStandardMaterial color="#334155" metalness={0.8} />
          </mesh>

          {/* 3D Ultrasonic Anemometer Head */}
          <group position={[-0.85, 1.5, 0]}>
            <cylinderGeometry args={[0.08, 0.08, 0.4, 8]} />
            <meshStandardMaterial color="#e2e8f0" metalness={0.7} />
            <mesh position={[0, 0.25, 0]}>
              <sphereGeometry args={[0.12, 12, 8]} />
              <meshStandardMaterial color="#f97316" metalness={0.5} />
            </mesh>
          </group>

          {/* Wind Vane & Pyranometer Head */}
          <group position={[0.85, 1.5, 0]}>
            <mesh>
              <cylinderGeometry args={[0.06, 0.06, 0.4, 8]} />
              <meshStandardMaterial color="#e2e8f0" />
            </mesh>
            <mesh position={[0.15, 0.22, 0]} rotation={[0, 0, Math.PI / 2]}>
              <boxGeometry args={[0.04, 0.35, 0.15]} />
              <meshStandardMaterial color="#38bdf8" metalness={0.7} />
            </mesh>
          </group>
        </group>
      )}
    </group>
  );
};

// ============================================================================
// 6. SPACE-FRAME TRUSS STILTS WITH CROSS-BRACING (Arctic Permafrost Pilings)
// ============================================================================
export const StructuralTrussStilts = ({
  pilings = [],
  stiltHeight = 7.0,
  stiltY = -3.5,
  pilingRadius = 0.26,
  steelColor = '#242a35',
  footingColor = '#3a4454',
  opacity = 1.0,
  depthWrite = true
}) => {
  const isTransparent = opacity < 1.0;

  // Generate cross-bracing pairs between adjacent pilings
  const braces = useMemo(() => {
    const list = [];
    for (let i = 0; i < pilings.length; i++) {
      for (let j = i + 1; j < pilings.length; j++) {
        const [x1, z1] = pilings[i];
        const [x2, z2] = pilings[j];
        const dist = Math.hypot(x2 - x1, z2 - z1);
        // Only brace closely adjacent pilings (e.g. within 6 to 12 units)
        if (dist > 4.0 && dist < 12.0) {
          list.push({
            midX: (x1 + x2) / 2,
            midZ: (z1 + z2) / 2,
            dx: x2 - x1,
            dz: z2 - z1,
            dist,
            id: `br-${i}-${j}`
          });
        }
      }
    }
    return list;
  }, [pilings]);

  return (
    <group>
      {/* Heavy Vertical Pilings */}
      {pilings.map(([cx, cz], idx) => (
        <group key={`piling-${idx}`} position={[cx, stiltY, cz]}>
          {/* Main Round Steel Tube Piling */}
          <mesh castShadow>
            <cylinderGeometry args={[pilingRadius, pilingRadius, stiltHeight, 12]} />
            <meshStandardMaterial
              color={steelColor}
              metalness={0.75}
              roughness={0.4}
              transparent={isTransparent}
              opacity={opacity}
              depthWrite={depthWrite}
            />
          </mesh>

          {/* Top Hydraulic/Shim Mounting Flange to Building Underbelly */}
          <mesh position={[0, stiltHeight / 2 - 0.08, 0]}>
            <cylinderGeometry args={[pilingRadius * 2.2, pilingRadius * 2.2, 0.16, 12]} />
            <meshStandardMaterial
              color="#475569"
              metalness={0.8}
              roughness={0.3}
              transparent={isTransparent}
              opacity={opacity}
              depthWrite={depthWrite}
            />
          </mesh>

          {/* Heavy Concrete Footing Baseplate anchored into Permafrost Datum */}
          <mesh position={[0, -stiltHeight / 2 + 0.1, 0]} receiveShadow>
            <boxGeometry args={[1.2, 0.22, 1.2]} />
            <meshStandardMaterial
              color={footingColor}
              roughness={0.85}
              metalness={0.25}
              transparent={isTransparent}
              opacity={opacity}
              depthWrite={depthWrite}
            />
          </mesh>

          {/* Hex Nut / Anchor Bolt Stubs on baseplate */}
          {[-0.4, 0.4].map((bx) =>
            [-0.4, 0.4].map((bz) => (
              <mesh key={`bolt-${bx}-${bz}`} position={[bx, -stiltHeight / 2 + 0.24, bz]}>
                <cylinderGeometry args={[0.04, 0.04, 0.1, 6]} />
                <meshStandardMaterial color="#cbd5e1" metalness={0.9} />
              </mesh>
            ))
          )}
        </group>
      ))}

      {/* Diagonal Steel Cross-Bracing Struts (X-truss frames between pilings) */}
      {braces.map((b) => {
        const angleY = Math.atan2(b.dx, b.dz);
        const strutLen = Math.hypot(b.dist, stiltHeight * 0.7);
        const pitchAngle = Math.atan2(stiltHeight * 0.7, b.dist);

        return (
          <group key={b.id} position={[b.midX, stiltY, b.midZ]} rotation={[0, angleY, 0]}>
            {/* Diagonal Strut 1 */}
            <mesh rotation={[pitchAngle, 0, 0]}>
              <cylinderGeometry args={[0.075, 0.075, strutLen, 8]} />
              <meshStandardMaterial
                color={steelColor}
                metalness={0.7}
                roughness={0.4}
                transparent={isTransparent}
                opacity={opacity}
                depthWrite={depthWrite}
              />
            </mesh>
            {/* Diagonal Strut 2 (Crossing to make the X) */}
            <mesh rotation={[-pitchAngle, 0, 0]}>
              <cylinderGeometry args={[0.075, 0.075, strutLen, 8]} />
              <meshStandardMaterial
                color={steelColor}
                metalness={0.7}
                roughness={0.4}
                transparent={isTransparent}
                opacity={opacity}
                depthWrite={depthWrite}
              />
            </mesh>
            {/* Center Gusset Connection Plate */}
            <mesh>
              <cylinderGeometry args={[0.18, 0.18, 0.12, 8]} rotation={[0, 0, Math.PI / 2]} />
              <meshStandardMaterial color="#475569" metalness={0.8} />
            </mesh>
          </group>
        );
      })}
    </group>
  );
};

// ============================================================================
// 7. ROOF CONDUIT & CABLE TRAY SYSTEM (Yellow/Copper Interconnect Piping)
// ============================================================================
export const RooftopCableTrays = ({
  routes = [],
  opacity = 1.0,
  depthWrite = true
}) => {
  const isTransparent = opacity < 1.0;

  return (
    <group>
      {routes.map((r, i) => {
        const [x1, y1, z1] = r.from;
        const [x2, y2, z2] = r.to;
        const dx = x2 - x1;
        const dy = y2 - y1;
        const dz = z2 - z1;
        const len = Math.hypot(dx, dy, dz);
        const mid = [(x1 + x2) / 2, (y1 + y2) / 2, (z1 + z2) / 2];
        const rotY = Math.atan2(dx, dz);
        const rotX = -Math.atan2(dy, Math.hypot(dx, dz));

        return (
          <group key={`tray-${i}`} position={mid} rotation={[rotX, rotY, 0]}>
            {/* Galvanized Cable Tray Channel */}
            <mesh>
              <boxGeometry args={[0.26, 0.08, len]} />
              <meshStandardMaterial
                color="#64748b"
                metalness={0.75}
                roughness={0.35}
                transparent={isTransparent}
                opacity={opacity}
                depthWrite={depthWrite}
              />
            </mesh>
            {/* Yellow / Copper High-Voltage DC Solar Cable Bundle inside */}
            <mesh position={[0, 0.06, 0]}>
              <cylinderGeometry args={[0.05, 0.05, len * 0.98, 8]} rotation={[Math.PI / 2, 0, 0]} />
              <meshStandardMaterial
                color={r.cableColor || '#b45309'}
                metalness={0.6}
                roughness={0.3}
                transparent={isTransparent}
                opacity={opacity}
                depthWrite={depthWrite}
              />
            </mesh>
          </group>
        );
      })}
    </group>
  );
};
