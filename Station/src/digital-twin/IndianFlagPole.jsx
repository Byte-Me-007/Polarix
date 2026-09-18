import React, { useRef, useMemo } from 'react';
import * as THREE from 'three';
import { useFrame } from '@react-three/fiber';

/**
 * Procedurally generates a high-resolution 3:2 Indian national flag texture
 * featuring India Saffron, White, India Green, and the Navy Blue 24-spoke Ashoka Chakra.
 */
let cachedFlagTexture = null;

const getIndianFlagTexture = () => {
  if (cachedFlagTexture) return cachedFlagTexture;

  const width = 1024;
  const height = 683; // 3:2 ratio
  const canvas = document.createElement('canvas');
  canvas.width = width;
  canvas.height = height;
  const ctx = canvas.getContext('2d');

  const bandH = height / 3;

  // 1. Saffron Top Band
  ctx.fillStyle = '#FF671F';
  ctx.fillRect(0, 0, width, bandH);

  // 2. White Middle Band
  ctx.fillStyle = '#FFFFFF';
  ctx.fillRect(0, bandH, width, bandH);

  // 3. Green Bottom Band
  ctx.fillStyle = '#046A38';
  ctx.fillRect(0, bandH * 2, width, bandH);

  // 4. Navy Blue Ashoka Chakra in Center
  const cx = width / 2;
  const cy = height / 2;
  const outerRadius = (bandH * 0.78) / 2; // ~80px
  const innerHubRadius = outerRadius * 0.22;
  const navyColor = '#000080';

  ctx.strokeStyle = navyColor;
  ctx.fillStyle = navyColor;

  // Outer Ring
  ctx.lineWidth = 6;
  ctx.beginPath();
  ctx.arc(cx, cy, outerRadius, 0, Math.PI * 2);
  ctx.stroke();

  // 24 Spokes
  ctx.lineWidth = 2.8;
  for (let i = 0; i < 24; i++) {
    const angle = (i * Math.PI * 2) / 24;
    const xEnd = cx + Math.cos(angle) * outerRadius;
    const yEnd = cy + Math.sin(angle) * outerRadius;

    ctx.beginPath();
    ctx.moveTo(cx, cy);
    ctx.lineTo(xEnd, yEnd);
    ctx.stroke();

    // Subtle small outer triangle/dot between spokes on the rim
    const dotAngle = angle + (Math.PI / 24);
    const dotX = cx + Math.cos(dotAngle) * (outerRadius - 4);
    const dotY = cy + Math.sin(dotAngle) * (outerRadius - 4);
    ctx.beginPath();
    ctx.arc(dotX, dotY, 2.5, 0, Math.PI * 2);
    ctx.fill();
  }

  // Inner Hub
  ctx.beginPath();
  ctx.arc(cx, cy, innerHubRadius, 0, Math.PI * 2);
  ctx.fill();

  // Center white pinpoint
  ctx.fillStyle = '#FFFFFF';
  ctx.beginPath();
  ctx.arc(cx, cy, innerHubRadius * 0.45, 0, Math.PI * 2);
  ctx.fill();

  const texture = new THREE.CanvasTexture(canvas);
  texture.colorSpace = THREE.SRGBColorSpace;
  texture.wrapS = THREE.ClampToEdgeWrapping;
  texture.wrapT = THREE.ClampToEdgeWrapping;
  cachedFlagTexture = texture;
  return texture;
};

/**
 * IndianFlagPole
 * Grounded national flagpole positioned in the station forecourt.
 * Features realistic pole geometry, base foundation plate, brass finial,
 * and animated cloth flutter in the polar wind.
 */
export const IndianFlagPole = ({
  position = [-8.5, 0, 18.0],
  poleHeight = 10.5,
  flagWidth = 3.6,
  flagHeight = 2.4,
  twinMode = 'NORMAL'
}) => {
  const meshRef = useRef();

  // Flag texture
  const flagTexture = useMemo(() => getIndianFlagTexture(), []);

  // Subdivided plane geometry for smooth cloth wave simulation
  const flagGeometry = useMemo(() => {
    // 32 segments along width, 16 along height
    const geo = new THREE.PlaneGeometry(flagWidth, flagHeight, 32, 16);
    // Shift origin so x = 0 is at the left edge (mast attachment)
    geo.translate(flagWidth / 2, 0, 0);
    return geo;
  }, [flagWidth, flagHeight]);

  // Mode-sensitive opacity: full in NORMAL; softly subdued in technical modes
  const isTechnicalMode = twinMode === 'XRAY' || twinMode === 'SYSTEM' || twinMode === 'HEATMAP';
  const clothOpacity = isTechnicalMode ? 0.35 : 1.0;
  const poleOpacity = isTechnicalMode ? 0.40 : 1.0;
  const isTransparent = isTechnicalMode;

  // Natural polar wind cloth flutter animation
  useFrame(({ clock }) => {
    if (!meshRef.current) return;
    const geo = meshRef.current.geometry;
    const pos = geo.attributes.position;
    const t = clock.getElapsedTime();

    for (let i = 0; i < pos.count; i++) {
      const vx = pos.getX(i);
      const vy = pos.getY(i);

      // Distance ratio from mast (0 at pole attachment, 1 at fly tip)
      const ratio = vx / flagWidth;

      // Compound sine waves simulating Antarctic breeze flutter
      const waveZ =
        Math.sin(vx * 1.7 - t * 4.2) * 0.22 * ratio +
        Math.sin(vy * 2.4 + t * 2.8) * 0.06 * ratio +
        Math.cos(vx * 3.5 - t * 6.0) * 0.04 * ratio;

      pos.setZ(i, waveZ);
    }

    pos.needsUpdate = true;
    geo.computeVertexNormals();
  });

  const poleRadiusTop = 0.06;
  const poleRadiusBottom = 0.11;
  const flagTopY = poleHeight - 0.4;
  const flagCenterY = flagTopY - flagHeight / 2;

  return (
    <group position={position} name="indian-flagpole-assembly">
      {/* ───────────────────────────────────────────────────────────── */}
      {/* 1. PERMAFROST CONCRETE FOOTING & STEEL ANCHOR BASEPLATE        */}
      {/* ───────────────────────────────────────────────────────────── */}
      {/* Concrete Foundation Block on Snow */}
      <mesh position={[0, 0.12, 0]} receiveShadow>
        <boxGeometry args={[1.2, 0.24, 1.2]} />
        <meshStandardMaterial
          color="#3a4454"
          roughness={0.92}
          metalness={0.1}
          transparent={isTransparent}
          opacity={poleOpacity}
        />
      </mesh>

      {/* Galvanized Steel Base Flange Plate */}
      <mesh position={[0, 0.26, 0]} castShadow={!isTransparent}>
        <cylinderGeometry args={[0.38, 0.42, 0.08, 16]} />
        <meshStandardMaterial
          color="#cbd5e1"
          metalness={0.8}
          roughness={0.3}
          transparent={isTransparent}
          opacity={poleOpacity}
        />
      </mesh>

      {/* Anchor Studs on Baseplate */}
      {[-0.24, 0.24].map((bx, i) =>
        [-0.24, 0.24].map((bz, j) => (
          <mesh key={`stud-${i}-${j}`} position={[bx, 0.32, bz]}>
            <cylinderGeometry args={[0.025, 0.025, 0.08, 6]} />
            <meshStandardMaterial
              color="#475569"
              metalness={0.9}
              roughness={0.2}
              transparent={isTransparent}
              opacity={poleOpacity}
            />
          </mesh>
        ))
      )}

      {/* Mast Collar Mount */}
      <mesh position={[0, 0.45, 0]}>
        <cylinderGeometry args={[0.18, 0.24, 0.32, 16]} />
        <meshStandardMaterial
          color="#64748b"
          metalness={0.7}
          roughness={0.35}
          transparent={isTransparent}
          opacity={poleOpacity}
        />
      </mesh>

      {/* ───────────────────────────────────────────────────────────── */}
      {/* 2. TAPERED METALLIC FLAGPOLE (MAST)                           */}
      {/* ───────────────────────────────────────────────────────────── */}
      <mesh position={[0, poleHeight / 2 + 0.3, 0]} castShadow={!isTransparent}>
        <cylinderGeometry args={[poleRadiusTop, poleRadiusBottom, poleHeight, 16]} />
        <meshStandardMaterial
          color="#e2e8f0"
          metalness={0.85}
          roughness={0.25}
          transparent={isTransparent}
          opacity={poleOpacity}
        />
      </mesh>

      {/* Halyard Line / Cable along mast */}
      <mesh position={[poleRadiusTop + 0.025, poleHeight / 2 + 0.3, 0]}>
        <cylinderGeometry args={[0.008, 0.008, poleHeight * 0.96, 6]} />
        <meshStandardMaterial
          color="#1e293b"
          roughness={0.8}
          transparent={isTransparent}
          opacity={poleOpacity * 0.7}
        />
      </mesh>

      {/* Mast Cleat (lower rope tie-off point) */}
      <mesh position={[poleRadiusBottom + 0.05, 1.4, 0]} rotation={[0, 0, Math.PI / 2]}>
        <cylinderGeometry args={[0.02, 0.02, 0.18, 8]} />
        <meshStandardMaterial
          color="#475569"
          metalness={0.8}
          roughness={0.3}
          transparent={isTransparent}
          opacity={poleOpacity}
        />
      </mesh>

      {/* Top Truck Pulley Assembly */}
      <mesh position={[0, poleHeight + 0.32, 0]}>
        <cylinderGeometry args={[0.12, 0.10, 0.08, 16]} />
        <meshStandardMaterial
          color="#cbd5e1"
          metalness={0.85}
          roughness={0.25}
          transparent={isTransparent}
          opacity={poleOpacity}
        />
      </mesh>

      {/* Gold / Polished Brass Finial Ball */}
      <mesh position={[0, poleHeight + 0.48, 0]} castShadow={!isTransparent}>
        <sphereGeometry args={[0.16, 16, 16]} />
        <meshStandardMaterial
          color="#d4af37"
          metalness={0.9}
          roughness={0.18}
          transparent={isTransparent}
          opacity={poleOpacity}
        />
      </mesh>

      {/* ───────────────────────────────────────────────────────────── */}
      {/* 3. INDIAN TRICOLOR CLOTH WITH ASHOKA CHAKRA & WIND FLUTTER    */}
      {/* ───────────────────────────────────────────────────────────── */}
      <group position={[poleRadiusTop + 0.03, flagCenterY, 0]}>
        <mesh
          ref={meshRef}
          geometry={flagGeometry}
          castShadow={!isTransparent}
          receiveShadow={!isTransparent}
        >
          <meshStandardMaterial
            map={flagTexture}
            side={THREE.DoubleSide}
            roughness={0.72}
            metalness={0.06}
            transparent={isTransparent}
            opacity={clothOpacity}
            depthWrite={!isTransparent}
          />
        </mesh>

        {/* Top & Bottom Halyard Brass Grommet Clips */}
        {[flagHeight / 2 - 0.05, -flagHeight / 2 + 0.05].map((gy, gi) => (
          <mesh key={`clip-${gi}`} position={[-0.03, gy, 0]} rotation={[0, 0, Math.PI / 2]}>
            <torusGeometry args={[0.035, 0.012, 8, 12]} />
            <meshStandardMaterial
              color="#d4af37"
              metalness={0.85}
              roughness={0.3}
              transparent={isTransparent}
              opacity={poleOpacity}
            />
          </mesh>
        ))}
      </group>
    </group>
  );
};

export default IndianFlagPole;
