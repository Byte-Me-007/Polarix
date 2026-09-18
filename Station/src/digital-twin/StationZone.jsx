import React, { useMemo, useRef } from 'react';
import * as THREE from 'three';
import { useFrame } from '@react-three/fiber';
import { Html } from '@react-three/drei';
import { InternalAssetMarker } from './InternalAssetMarker';
import { ZONE_INTERNAL_ASSETS, resolveAssetStatus, getAssociatedAssetIdForSensor } from './stationAssets';
import {
  SolarPanelArray,
  RooftopHVACUnit,
  AirlockEntranceModule,
  ParabolicDishAssembly,
  LatticeTower,
  StructuralTrussStilts,
  RooftopCableTrays
} from './InfrastructureComponents';

// Cache radial textures to prevent recreation
const textureCache = {};
const getRadialHeatmapTexture = (rgb) => {
  if (textureCache[rgb]) return textureCache[rgb];
  const size = 256;
  const canvas = document.createElement('canvas');
  canvas.width = size;
  canvas.height = size;
  const ctx = canvas.getContext('2d');
  const cx = size / 2;

  const grad = ctx.createRadialGradient(cx, cx, 0, cx, cx, cx * 0.96);
  grad.addColorStop(0,    `rgba(${rgb}, 0.98)`);
  grad.addColorStop(0.28, `rgba(${rgb}, 0.82)`);
  grad.addColorStop(0.55, `rgba(${rgb}, 0.45)`);
  grad.addColorStop(0.82, `rgba(${rgb}, 0.12)`);
  grad.addColorStop(1.00, `rgba(${rgb}, 0)`);

  ctx.fillStyle = grad;
  ctx.fillRect(0, 0, size, size);

  const tex = new THREE.CanvasTexture(canvas);
  textureCache[rgb] = tex;
  return tex;
};

export const StationZone = ({
  zone,
  showLabels = true,
  showHeatmap = false,
  zoneStatus = 'NORMAL',
  statusMeta,
  isSelectedZone = false,
  hasSelectedZone = false,
  twinMode = 'NORMAL',
  isHighlighted = false,
  sensors = [],
  telemetry = {},
  onSelectAsset,
  selectedAssetId = null,
  selectedSensor = null
}) => {
  const [px, py, pz] = zone.position;
  const [sx, sy, sz] = zone.size;
  const code = zone.code || zone.id;

  // Resolve whether an internal asset in this zone is associated with the selected sensor
  const associatedAssetId = useMemo(() => {
    if (!selectedSensor) return null;
    const targetId = getAssociatedAssetIdForSensor(selectedSensor);
    return targetId?.startsWith(`${code}-`) ? targetId : null;
  }, [selectedSensor, code]);

  // Resolved status metadata for vivid heatmap coloring
  const meta = useMemo(() => {
    if (statusMeta) return statusMeta;
    switch (zoneStatus?.toUpperCase()) {
      case 'CRITICAL':
        return { hex: '#e03131', rgb: '224, 49, 49', floorOpacity: 0.65, glowOpacity: 0.95 };
      case 'WARNING':
        return { hex: '#f59f00', rgb: '245, 159, 0', floorOpacity: 0.55, glowOpacity: 0.88 };
      case 'OFFLINE':
        return { hex: '#868e96', rgb: '134, 142, 150', floorOpacity: 0.22, glowOpacity: 0.35 };
      default:
        return { hex: '#2b8a3e', rgb: '43, 138, 62', floorOpacity: 0.35, glowOpacity: 0.60 };
    }
  }, [zoneStatus, statusMeta]);

  // Pulsing animation for critical alert zone or active selection
  const pulseRef = useRef();
  useFrame(({ clock }) => {
    if (pulseRef.current && (zoneStatus === 'CRITICAL' || isSelectedZone)) {
      const s = 1 + Math.sin(clock.getElapsedTime() * 4.0) * 0.08;
      pulseRef.current.scale.set(s, 1, s);
    }
  });

  // Material settings:
  // NORMAL mode:  100% opaque realistic buildings.
  // HEATMAP mode: Roof 8% transparent, walls 32%, equipment 18%.
  // XRAY mode:    Roof 5% transparent, walls 20%, equipment 14%.
  // SYSTEM mode:  Same as XRAY for building shell.
  const isXray   = twinMode === 'XRAY';
  const isSystem = twinMode === 'SYSTEM';
  const isSemiTransparent = showHeatmap || isXray || isSystem;

  const wallOpacity     = showHeatmap ? 0.32 : (isXray || isSystem) ? 0.20 : 1.0;
  const wallDepthWrite  = !isSemiTransparent;

  const roofOpacity     = showHeatmap ? 0.08 : (isXray || isSystem) ? 0.04 : 1.0;
  const roofColor       = isSemiTransparent ? '#f4efe6' : '#1e242d';
  const roofDepthWrite  = !isSemiTransparent;

  const parapetOpacity  = isSemiTransparent ? 0.04 : 1.0;
  const parapetColor    = isSemiTransparent ? '#e2e8f0' : '#334155';

  const equipOpacity    = showHeatmap ? 0.18 : (isXray || isSystem) ? 0.06 : 1.0;
  const equipDepthWrite = !isSemiTransparent;

  // Primary architectural cladding color palette (clean off-white polar insulated panels)
  const wallColor = useMemo(() => {
    switch (code) {
      case 'MAIN':      return '#edf2f7'; // crisp polar off-white
      case 'RESEARCH':  return '#f1f5f9'; // scientific cleanroom white
      case 'ENERGY':    return '#e2e8f0'; // industrial microgrid light gray
      case 'STORAGE':   return '#dbe4ee'; // cold logistics container panel
      case 'GENERATOR': return '#cbd5e1'; // heavy mechanical facility
      case 'COMMS':     return '#e2e8f0';
      default:          return '#edf2f7';
    }
  }, [code]);

  // When in X-RAY, SYSTEM, or HEATMAP mode, disable raycasting on the outer building shell so internal assets receive all clicks
  const shellRaycast = isSemiTransparent ? () => null : undefined;

  // Internal assets (revealed in XRAY, SYSTEM, or HEATMAP modes, or when an asset is selected)
  const internalAssets = useMemo(() => {
    if (!isXray && !isSystem && !showHeatmap && !selectedAssetId) return [];
    const zoneDefs = ZONE_INTERNAL_ASSETS[code] || [];
    return zoneDefs.map(assetDef => ({
      ...assetDef,
      fullId: `${code}-${assetDef.id}`,
      worldPos: [
        px + assetDef.relPos[0],
        py + assetDef.relPos[1],
        pz + assetDef.relPos[2]
      ],
      status: resolveAssetStatus(assetDef, code, sensors, telemetry)
    }));
  }, [isXray, isSystem, showHeatmap, selectedAssetId, code, sensors, telemetry, px, py, pz]);

  // Stilt footing calculations - polar foundation elevated above ground y=0
  const stiltRadius = 0.26;
  const stiltHeight = py + 0.2;
  const stiltY = -py / 2;

  // Calculate robust grid of structural pilings based on module dimensions
  const numStiltsX = Math.max(3, Math.round(sx / 4.8));
  const numStiltsZ = Math.max(2, Math.round(sz / 5.5));
  const stilts = useMemo(() => {
    const list = [];
    for (let ix = 0; ix < numStiltsX; ix++) {
      for (let iz = 0; iz < numStiltsZ; iz++) {
        const cx = -sx * 0.44 + (ix / (numStiltsX - 1)) * sx * 0.88;
        const cz = -sz * 0.44 + (iz / (numStiltsZ - 1)) * sz * 0.88;
        list.push([cx, cz]);
      }
    }
    return list;
  }, [numStiltsX, numStiltsZ, sx, sz]);

  return (
    <group position={[px, py, pz]}>
      {/* ------------------------------------------------------------- */}
      {/* 1. STRUCTURAL STEEL SPACE-FRAME TRUSS STILTS & FOOTINGS       */}
      {/* Elevates facility above drifting snow pack with X-bracing     */}
      {/* ------------------------------------------------------------- */}
      {code !== 'COMMS' && (
        <StructuralTrussStilts
          pilings={stilts}
          stiltHeight={stiltHeight}
          stiltY={stiltY}
          pilingRadius={stiltRadius}
          opacity={isXray ? 0.10 : isSemiTransparent ? 0.35 : 1.0}
          steelColor={isXray ? '#94a3b8' : isSemiTransparent ? '#475569' : '#242a35'}
          footingColor={isXray ? '#cbd5e1' : isSemiTransparent ? '#475569' : '#3a4454'}
          depthWrite={!isSemiTransparent}
          castShadow={!isXray}
          raycast={shellRaycast}
        />
      )}

      {/* ------------------------------------------------------------- */}
      {/* 2. INTERIOR ARCHITECTURAL INSPECTION FLOOR (Heatmap Mode)     */}
      {/* ------------------------------------------------------------- */}
      {showHeatmap && (
        <group position={[0, 0, 0]}>
          <mesh
            position={[0, 0.10, 0]}
            rotation={[-Math.PI / 2, 0, 0]}
            renderOrder={5}
            raycast={() => null}
          >
            <planeGeometry args={[sx * 0.94, sz * 0.94]} />
            <meshBasicMaterial
              color="#dcd5c9"
              transparent
              opacity={0.35}
              depthWrite={false}
              side={THREE.DoubleSide}
            />
          </mesh>

          {/* Selected Zone Prominence Highlight Ring */}
          {isSelectedZone && (
            <group ref={pulseRef}>
              <mesh
                position={[0, 0.22, 0]}
                rotation={[-Math.PI / 2, 0, 0]}
                renderOrder={7}
                raycast={() => null}
              >
                <ringGeometry
                  args={[
                    Math.min(sx, sz) * 0.40,
                    Math.min(sx, sz) * 0.46,
                    40
                  ]}
                />
                <meshBasicMaterial
                  color="#b65a1f"
                  transparent
                  opacity={0.95}
                  depthWrite={false}
                  side={THREE.DoubleSide}
                />
              </mesh>
            </group>
          )}

          {/* Alert Rings */}
          {zoneStatus === 'CRITICAL' && !isSelectedZone && (
            <group ref={pulseRef}>
              <mesh
                position={[0, 0.24, 0]}
                rotation={[-Math.PI / 2, 0, 0]}
                renderOrder={7}
                raycast={() => null}
              >
                <ringGeometry
                  args={[
                    Math.min(sx, sz) * 0.32,
                    Math.min(sx, sz) * 0.40,
                    36
                  ]}
                />
                <meshBasicMaterial
                  color="#ff4d4f"
                  transparent
                  opacity={0.90}
                  depthWrite={false}
                  side={THREE.DoubleSide}
                />
              </mesh>
            </group>
          )}
        </group>
      )}

      {/* Selected zone subtle exterior highlight frame in normal mode */}
      {!showHeatmap && isSelectedZone && (
        <mesh position={[0, sy + 0.14, 0]} renderOrder={15} raycast={() => null}>
          <boxGeometry args={[sx + 0.24, 0.16, sz + 0.24]} />
          <meshStandardMaterial
            color="#b65a1f"
            roughness={0.4}
            metalness={0.6}
            transparent
            opacity={0.75}
            depthWrite={false}
          />
        </mesh>
      )}

      {/* ------------------------------------------------------------- */}
      {/* 3. ZONE-SPECIFIC ARCHITECTURAL STRUCTURES                     */}
      {/* ------------------------------------------------------------- */}

      {/* ============================================================= */}
      {/* A. MAIN BUILDING (Central Multi-deck Research & Habitat Hub)  */}
      {/* ============================================================= */}
      {code === 'MAIN' && (
        <group>
          {/* Main Architectural Building Body */}
          <mesh raycast={shellRaycast} castShadow receiveShadow position={[0, sy / 2, 0]} renderOrder={8}>
            <boxGeometry args={[sx, sy, sz]} />
            <meshStandardMaterial
              color={wallColor}
              roughness={0.35}
              metalness={0.15}
              transparent={true}
              opacity={wallOpacity}
              depthWrite={wallDepthWrite}
            />
          </mesh>

          {/* Horizontal Architectural Cladding Seam Lines (Floors 1 & 2 reveals) */}
          {!isSemiTransparent && [sy * 0.35, sy * 0.70].map((ly, li) => (
            <mesh key={`main-reveal-${li}`} position={[0, ly, 0]} raycast={() => null}>
              <boxGeometry args={[sx + 0.08, 0.08, sz + 0.08]} />
              <meshStandardMaterial
                color="#1e293b"
                roughness={0.7}
                metalness={0.4}
                transparent={true}
                opacity={wallOpacity}
              />
            </mesh>
          ))}

          {/* Roof Parapet Architectural Edge Frame / Coping */}
          <mesh raycast={shellRaycast} position={[0, sy + 0.15, 0]} renderOrder={12}>
            <boxGeometry args={[sx + 0.25, 0.3, sz + 0.25]} />
            <meshStandardMaterial
              color={parapetColor}
              roughness={0.6}
              metalness={0.4}
              transparent={true}
              opacity={parapetOpacity}
              depthWrite={roofDepthWrite}
            />
          </mesh>

          {/* Slate Charcoal Roof Deck Membrane */}
          <mesh raycast={shellRaycast} position={[0, sy + 0.05, 0]} renderOrder={11}>
            <boxGeometry args={[sx * 0.98, 0.1, sz * 0.98]} />
            <meshStandardMaterial
              color={roofColor}
              roughness={0.5}
              metalness={0.25}
              transparent={true}
              opacity={roofOpacity}
              depthWrite={roofDepthWrite}
            />
          </mesh>

          {/* South Facade Ribbon Windows (Lower & Upper Deck) */}
          {[-1, 1].map((tier, ti) => {
            const wy = ti === 0 ? sy * 0.36 : sy * 0.72;
            const ww = sx * 0.82;
            return (
              <group key={`win-south-${ti}`} position={[0, wy, sz / 2 + 0.04]}>
                {/* Window Glass */}
                <mesh raycast={shellRaycast}>
                  <boxGeometry args={[ww, 0.9, 0.08]} />
                  <meshStandardMaterial
                    color={isSemiTransparent ? '#cbd5e1' : '#0f172a'}
                    roughness={0.08}
                    metalness={isSemiTransparent ? 0.1 : 0.92}
                    transparent={true}
                    opacity={isSemiTransparent ? 0.04 : wallOpacity}
                  />
                </mesh>
                {/* Aluminum Mullion Dividers */}
                {!isSemiTransparent && [-10, -5, 0, 5, 10].map((mx, mi) => (
                  <mesh key={`mull-${mi}`} position={[mx, 0, 0.02]} raycast={() => null}>
                    <boxGeometry args={[0.08, 0.92, 0.08]} />
                    <meshStandardMaterial color="#475569" metalness={0.8} roughness={0.3} />
                  </mesh>
                ))}
              </group>
            );
          })}

          {/* North Facade Ribbon Windows */}
          <mesh raycast={shellRaycast} position={[0, sy * 0.55, -sz / 2 - 0.04]}>
            <boxGeometry args={[sx * 0.78, 0.9, 0.08]} />
            <meshStandardMaterial
              color={isSemiTransparent ? '#cbd5e1' : '#0f172a'}
              roughness={0.08}
              metalness={isSemiTransparent ? 0.1 : 0.92}
              transparent={true}
              opacity={isSemiTransparent ? 0.04 : wallOpacity}
            />
          </mesh>

          {/* South Expedition Airlock Entrance Module with Sealed Door & Stairs */}
          <AirlockEntranceModule
            position={[0, 0, sz / 2]}
            width={5.8}
            height={sy * 0.52}
            depth={2.8}
            stairElevation={stiltHeight}
            opacity={wallOpacity}
            depthWrite={wallDepthWrite}
          />

          {/* Left Roof: Photovoltaic Solar Panel Array (3 rows x 4 cols, tilted) */}
          <SolarPanelArray
            position={[-8.5, sy + 0.1, 0]}
            rows={3}
            cols={4}
            panelWidth={2.1}
            panelHeight={2.8}
            tiltAngle={0.35}
            opacity={equipOpacity}
            depthWrite={equipDepthWrite}
          />

          {/* Right Roof: Commercial Dual-Fan Rooftop HVAC Unit */}
          <RooftopHVACUnit
            position={[7.2, sy + 0.1, 2.5]}
            fans={2}
            width={5.2}
            height={1.8}
            depth={3.2}
            opacity={equipOpacity}
            depthWrite={equipDepthWrite}
          />

          {/* Auxiliary Single-Fan HVAC Unit */}
          <RooftopHVACUnit
            position={[9.4, sy + 0.1, -5.2]}
            fans={1}
            width={3.2}
            height={1.5}
            depth={2.6}
            opacity={equipOpacity}
            depthWrite={equipDepthWrite}
          />

          {/* Central Utility Penthouse / Stair Bulkhead */}
          <group position={[0, sy + 0.8, 0]}>
            <mesh castShadow={!isSemiTransparent}>
              <boxGeometry args={[5.8, 1.6, 4.4]} />
              <meshStandardMaterial
                color="#64748b"
                roughness={0.5}
                metalness={0.35}
                transparent={true}
                opacity={equipOpacity}
                depthWrite={equipDepthWrite}
              />
            </mesh>
            {/* Louver Panels */}
            {[-1.8, 1.8].map((lx, i) => (
              <mesh key={`pen-louver-${i}`} position={[lx, 0.1, 2.22]}>
                <boxGeometry args={[1.5, 0.9, 0.04]} />
                <meshStandardMaterial
                  color={isSemiTransparent ? '#cbd5e1' : '#1e293b'}
                  roughness={0.8}
                  transparent={isSemiTransparent}
                  opacity={equipOpacity}
                />
              </mesh>
            ))}
          </group>

          {/* Rooftop Interconnect Cable & Pipe Trays */}
          <RooftopCableTrays
            routes={[
              { from: [-4.0, sy + 0.15, -1.0], to: [-2.9, sy + 0.4, 0], cableColor: '#f59e0b' },
              { from: [4.6, sy + 0.15, 2.5],   to: [2.9, sy + 0.4, 0],  cableColor: '#b45309' }
            ]}
            opacity={equipOpacity}
            depthWrite={equipDepthWrite}
          />
        </group>
      )}

      {/* ============================================================= */}
      {/* B. RESEARCH BUILDING (Scientific Laboratory & Optical Hub)    */}
      {/* ============================================================= */}
      {code === 'RESEARCH' && (
        <group>
          {/* Main Laboratory Body */}
          <mesh raycast={shellRaycast} castShadow receiveShadow position={[0, sy / 2, 0]} renderOrder={8}>
            <boxGeometry args={[sx, sy, sz]} />
            <meshStandardMaterial
              color={wallColor}
              roughness={0.35}
              metalness={0.15}
              transparent={true}
              opacity={wallOpacity}
              depthWrite={wallDepthWrite}
            />
          </mesh>

          {/* Cladding Seam Lines */}
          {!isSemiTransparent && [sy * 0.48].map((ly, li) => (
            <mesh key={`res-reveal-${li}`} position={[0, ly, 0]} raycast={() => null}>
              <boxGeometry args={[sx + 0.08, 0.08, sz + 0.08]} />
              <meshStandardMaterial color="#1e293b" roughness={0.7} metalness={0.4} />
            </mesh>
          ))}

          {/* Roof Parapet Frame & Deck */}
          <mesh raycast={shellRaycast} position={[0, sy + 0.15, 0]} renderOrder={12}>
            <boxGeometry args={[sx + 0.25, 0.3, sz + 0.25]} />
            <meshStandardMaterial
              color={parapetColor}
              roughness={0.6}
              metalness={0.4}
              transparent={true}
              opacity={parapetOpacity}
              depthWrite={roofDepthWrite}
            />
          </mesh>
          <mesh raycast={shellRaycast} position={[0, sy + 0.05, 0]} renderOrder={11}>
            <boxGeometry args={[sx * 0.98, 0.1, sz * 0.98]} />
            <meshStandardMaterial
              color={roofColor}
              roughness={0.5}
              metalness={0.25}
              transparent={true}
              opacity={roofOpacity}
              depthWrite={roofDepthWrite}
            />
          </mesh>

          {/* South Facade Ribbon Windows */}
          <mesh raycast={shellRaycast} position={[0, sy * 0.55, sz / 2 + 0.04]}>
            <boxGeometry args={[sx * 0.82, 0.9, 0.08]} />
            <meshStandardMaterial
              color={isSemiTransparent ? '#cbd5e1' : '#0f172a'}
              roughness={0.08}
              metalness={isSemiTransparent ? 0.1 : 0.92}
              transparent={true}
              opacity={isSemiTransparent ? 0.04 : wallOpacity}
            />
          </mesh>

          {/* East Facade Ribbon Windows */}
          <mesh raycast={shellRaycast} position={[sx / 2 + 0.04, sy * 0.55, 0]} rotation={[0, Math.PI / 2, 0]}>
            <boxGeometry args={[sz * 0.72, 0.9, 0.08]} />
            <meshStandardMaterial
              color={isSemiTransparent ? '#cbd5e1' : '#0f172a'}
              roughness={0.08}
              metalness={isSemiTransparent ? 0.1 : 0.92}
              transparent={true}
              opacity={isSemiTransparent ? 0.04 : wallOpacity}
            />
          </mesh>

          {/* Optical & Astrophotometry Geodesic Radome (Center-Right Roof) */}
          <group position={[2.8, sy + 0.1, 2.2]}>
            {/* Raised Cylindrical Coaming Base */}
            <mesh position={[0, 0.45, 0]} raycast={shellRaycast}>
              <cylinderGeometry args={[2.4, 2.6, 0.9, 24]} />
              <meshStandardMaterial
                color={isSemiTransparent ? '#cbd5e1' : '#334155'}
                roughness={0.5}
                metalness={isSemiTransparent ? 0.1 : 0.5}
                transparent={true}
                opacity={equipOpacity}
                depthWrite={equipDepthWrite}
              />
            </mesh>
            {/* Clean White Observation Hemisphere */}
            <mesh position={[0, 0.9, 0]} castShadow={!isSemiTransparent} raycast={shellRaycast}>
              <sphereGeometry args={[2.4, 28, 16, 0, Math.PI * 2, 0, Math.PI * 0.5]} />
              <meshStandardMaterial
                color="#ffffff"
                roughness={0.2}
                metalness={0.15}
                transparent={true}
                opacity={equipOpacity}
                depthWrite={equipDepthWrite}
              />
            </mesh>
            {/* Optical Viewing Slit Hatch */}
            <mesh position={[0, 2.0, 1.1]} raycast={() => null}>
              <boxGeometry args={[0.55, 2.1, 0.25]} />
              <meshStandardMaterial
                color={isSemiTransparent ? '#cbd5e1' : '#0f172a'}
                metalness={isSemiTransparent ? 0.1 : 0.8}
                transparent={isSemiTransparent}
                opacity={equipOpacity}
              />
            </mesh>
          </group>

          {/* Parabolic Satellite Tracking Dish (Left Front Roof) */}
          <ParabolicDishAssembly
            position={[-4.5, sy + 0.1, 3.2]}
            radius={2.3}
            azimuth={0.35}
            elevation={0.48}
            opacity={equipOpacity}
            depthWrite={equipDepthWrite}
          />

          {/* Secondary Tracking Dish (Rear Left Roof) */}
          <ParabolicDishAssembly
            position={[-6.2, sy + 0.1, -3.8]}
            radius={1.7}
            azimuth={-0.6}
            elevation={0.38}
            opacity={equipOpacity}
            depthWrite={equipDepthWrite}
          />

          {/* Open Steel Communications & Met Lattice Tower (Rear Right Roof) */}
          <LatticeTower
            position={[6.5, sy + 0.1, -3.8]}
            height={9.2}
            baseWidth={2.4}
            topWidth={1.0}
            sections={4}
            hasMetGear={true}
            opacity={equipOpacity}
            depthWrite={equipDepthWrite}
          />

          {/* Tilted Solar Panel Array on West Roof */}
          <SolarPanelArray
            position={[-4.8, sy + 0.1, -0.6]}
            rows={1}
            cols={3}
            panelWidth={2.2}
            panelHeight={3.2}
            tiltAngle={0.35}
            opacity={equipOpacity}
            depthWrite={equipDepthWrite}
          />
        </group>
      )}

      {/* ============================================================= */}
      {/* C. ENERGY / POWER (Microgrid, Substation & Battery Storage)   */}
      {/* ============================================================= */}
      {code === 'ENERGY' && (
        <group>
          {/* Main Power Module Body */}
          <mesh raycast={shellRaycast} castShadow receiveShadow position={[0, sy / 2, 0]} renderOrder={8}>
            <boxGeometry args={[sx, sy, sz]} />
            <meshStandardMaterial
              color={wallColor}
              roughness={0.4}
              metalness={0.2}
              transparent={true}
              opacity={wallOpacity}
              depthWrite={wallDepthWrite}
            />
          </mesh>

          {/* Roof Parapet Frame & Deck */}
          <mesh raycast={shellRaycast} position={[0, sy + 0.15, 0]} renderOrder={12}>
            <boxGeometry args={[sx + 0.25, 0.3, sz + 0.25]} />
            <meshStandardMaterial
              color={parapetColor}
              roughness={0.6}
              metalness={0.4}
              transparent={true}
              opacity={parapetOpacity}
              depthWrite={roofDepthWrite}
            />
          </mesh>
          <mesh raycast={shellRaycast} position={[0, sy + 0.05, 0]} renderOrder={11}>
            <boxGeometry args={[sx * 0.98, 0.1, sz * 0.98]} />
            <meshStandardMaterial
              color={roofColor}
              roughness={0.5}
              metalness={0.25}
              transparent={true}
              opacity={roofOpacity}
              depthWrite={roofDepthWrite}
            />
          </mesh>

          {/* Extensive Solar Farm Across Left & Center Roof (3 rows x 4 cols) */}
          <SolarPanelArray
            position={[-4.5, sy + 0.1, 0]}
            rows={3}
            cols={4}
            panelWidth={2.3}
            panelHeight={3.2}
            tiltAngle={0.35}
            opacity={equipOpacity}
            depthWrite={equipDepthWrite}
          />

          {/* High-Voltage Substation Transformer Yard (East Roof) */}
          <group position={[7.0, sy + 0.1, 0]}>
            {/* Heavy Transformer Main Tank */}
            <mesh position={[0, 0.9, 0]} castShadow>
              <boxGeometry args={[3.8, 1.8, 4.4]} />
              <meshStandardMaterial
                color="#334155"
                roughness={0.5}
                metalness={0.6}
                transparent={true}
                opacity={equipOpacity}
                depthWrite={equipDepthWrite}
              />
            </mesh>

            {/* Cooling Fin Radiator Banks */}
            {[-2.0, 2.0].map((fx, fi) => (
              <mesh key={`xfr-fin-${fi}`} position={[fx, 0.9, 0]}>
                <boxGeometry args={[0.15, 1.5, 4.0]} />
                <meshStandardMaterial
                  color={isSemiTransparent ? '#cbd5e1' : '#1e293b'}
                  metalness={isSemiTransparent ? 0.1 : 0.7}
                  roughness={0.4}
                  transparent={isSemiTransparent}
                  opacity={equipOpacity}
                />
              </mesh>
            ))}

            {/* High-Voltage Ceramic Insulator Bushings (3 Phase Bushings) */}
            {[-1.0, 0, 1.0].map((bx, bi) => (
              <group key={`bush-${bi}`} position={[bx, 1.9, 0.8]}>
                <mesh>
                  <cylinderGeometry args={[0.12, 0.16, 0.9, 12]} />
                  <meshStandardMaterial
                    color={isSemiTransparent ? '#cbd5e1' : '#8b5cf6'}
                    roughness={0.3}
                    metalness={isSemiTransparent ? 0.1 : 0.4}
                    transparent={isSemiTransparent}
                    opacity={equipOpacity}
                  />
                </mesh>
                {/* Ceramic sheds / rings */}
                {[0.1, 0.25, 0.4].map((syVal, si) => (
                  <mesh key={`shed-${si}`} position={[0, syVal, 0]}>
                    <cylinderGeometry args={[0.22, 0.22, 0.05, 12]} />
                    <meshStandardMaterial
                      color={isSemiTransparent ? '#cbd5e1' : '#7c3aed'}
                      roughness={0.3}
                      transparent={isSemiTransparent}
                      opacity={equipOpacity}
                    />
                  </mesh>
                ))}
              </group>
            ))}

            {/* Microgrid Inverter Control Cabinet */}
            <mesh position={[0, 0.8, -2.6]} castShadow={!isSemiTransparent}>
              <boxGeometry args={[2.8, 1.6, 1.2]} />
              <meshStandardMaterial
                color={isSemiTransparent ? '#cbd5e1' : '#475569'}
                metalness={isSemiTransparent ? 0.1 : 0.5}
                roughness={0.4}
                transparent={isSemiTransparent}
                opacity={equipOpacity}
              />
            </mesh>
          </group>

          {/* Outdoor Battery Storage Bank Enclosures (North facade) */}
          <group position={[0, sy * 0.45, -sz / 2 - 0.7]}>
            <mesh castShadow={!isSemiTransparent}>
              <boxGeometry args={[sx * 0.72, sy * 0.8, 1.4]} />
              <meshStandardMaterial
                color={isSemiTransparent ? '#cbd5e1' : '#b45309'}
                roughness={0.4}
                metalness={isSemiTransparent ? 0.1 : 0.5}
                transparent={true}
                opacity={wallOpacity}
                depthWrite={wallDepthWrite}
              />
            </mesh>
            {[-4.5, -1.5, 1.5, 4.5].map((vx, i) => (
              <mesh key={`bat-vent-${i}`} position={[vx, 0.3, -0.72]}>
                <boxGeometry args={[1.4, 0.9, 0.05]} />
                <meshStandardMaterial
                  color={isSemiTransparent ? '#cbd5e1' : '#1e293b'}
                  roughness={0.9}
                  transparent={isSemiTransparent}
                  opacity={wallOpacity}
                />
              </mesh>
            ))}
          </group>
        </group>
      )}

      {/* ============================================================= */}
      {/* D. GENERATOR (Industrial Power Facility & Fuel Reserves)       */}
      {/* ============================================================= */}
      {code === 'GENERATOR' && (
        <group>
          {/* Main Industrial Housing Body */}
          <mesh raycast={shellRaycast} castShadow receiveShadow position={[0, sy / 2, 0]} renderOrder={8}>
            <boxGeometry args={[sx, sy, sz]} />
            <meshStandardMaterial
              color={wallColor}
              roughness={0.45}
              metalness={0.25}
              transparent={true}
              opacity={wallOpacity}
              depthWrite={wallDepthWrite}
            />
          </mesh>

          {/* Roof Parapet Frame & Deck */}
          <mesh raycast={shellRaycast} position={[0, sy + 0.15, 0]} renderOrder={12}>
            <boxGeometry args={[sx + 0.25, 0.3, sz + 0.25]} />
            <meshStandardMaterial
              color={parapetColor}
              roughness={0.6}
              metalness={0.4}
              transparent={true}
              opacity={parapetOpacity}
              depthWrite={roofDepthWrite}
            />
          </mesh>
          <mesh raycast={shellRaycast} position={[0, sy + 0.05, 0]} renderOrder={11}>
            <boxGeometry args={[sx * 0.98, 0.1, sz * 0.98]} />
            <meshStandardMaterial
              color={roofColor}
              roughness={0.5}
              metalness={0.25}
              transparent={true}
              opacity={roofOpacity}
              depthWrite={roofDepthWrite}
            />
          </mesh>

          {/* Twin Tall Industrial Diesel Generator Exhaust Stacks */}
          {[-2.6, 2.6].map((offX, i) => (
            <group key={`gen-exhaust-${i}`} position={[offX, sy + 2.8, -sz * 0.2]}>
              {/* Vertical Flue Pipe */}
              <mesh castShadow raycast={shellRaycast}>
                <cylinderGeometry args={[0.38, 0.44, 5.6, 16]} />
                <meshStandardMaterial
                  color="#334155"
                  roughness={0.5}
                  metalness={0.7}
                  transparent={true}
                  opacity={equipOpacity}
                  depthWrite={equipDepthWrite}
                />
              </mesh>
              {/* Thermal Heat Wrap Insulation Bands */}
              {[-1.2, 0, 1.2].map((by, bi) => (
                <mesh key={`band-${bi}`} position={[0, by, 0]} raycast={() => null}>
                  <cylinderGeometry args={[0.42, 0.42, 0.2, 16]} />
                  <meshStandardMaterial
                    color={isSemiTransparent ? '#cbd5e1' : '#64748b'}
                    metalness={isSemiTransparent ? 0.1 : 0.8}
                    transparent={isSemiTransparent}
                    opacity={equipOpacity}
                  />
                </mesh>
              ))}
              {/* Conical Rain Cowl */}
              <mesh position={[0, 2.9, 0]} raycast={() => null}>
                <coneGeometry args={[0.75, 0.5, 16]} />
                <meshStandardMaterial
                  color={isSemiTransparent ? '#cbd5e1' : '#1e293b'}
                  roughness={0.4}
                  metalness={isSemiTransparent ? 0.1 : 0.6}
                  transparent={isSemiTransparent}
                  opacity={equipOpacity}
                />
              </mesh>
            </group>
          ))}

          {/* Large Western Cooling Radiator & Ventilation Louver Bank */}
          <group position={[-sx / 2 - 0.7, sy * 0.5, 0]}>
            <mesh castShadow={!isSemiTransparent} raycast={shellRaycast}>
              <boxGeometry args={[1.4, sy * 0.8, sz * 0.75]} />
              <meshStandardMaterial
                color={isSemiTransparent ? '#cbd5e1' : '#334155'}
                roughness={0.7}
                metalness={isSemiTransparent ? 0.1 : 0.4}
                transparent={true}
                opacity={wallOpacity}
                depthWrite={wallDepthWrite}
              />
            </mesh>
            {/* Dual Radiator Fans */}
            {[-3.0, 3.0].map((fz, fi) => (
              <mesh key={`rad-fan-${fi}`} position={[-0.72, 0, fz]} rotation={[0, 0, Math.PI / 2]} raycast={() => null}>
                <cylinderGeometry args={[1.4, 1.4, 0.08, 20]} />
                <meshStandardMaterial
                  color={isSemiTransparent ? '#cbd5e1' : '#0f172a'}
                  roughness={0.3}
                  metalness={isSemiTransparent ? 0.1 : 0.8}
                  transparent={isSemiTransparent}
                  opacity={wallOpacity}
                />
              </mesh>
            ))}
          </group>

          {/* Horizontal Cylindrical Fuel Reserve / Day-Tank on South Facade */}
          <group position={[0, sy * 0.42, sz / 2 + 1.4]} rotation={[0, 0, Math.PI / 2]}>
            {/* Main Tank Barrel */}
            <mesh castShadow={!isSemiTransparent} raycast={shellRaycast}>
              <cylinderGeometry args={[1.2, 1.2, 8.0, 24]} />
              <meshStandardMaterial
                color={isSemiTransparent ? '#cbd5e1' : '#475569'}
                roughness={0.4}
                metalness={isSemiTransparent ? 0.1 : 0.6}
                transparent={true}
                opacity={wallOpacity}
                depthWrite={wallDepthWrite}
              />
            </mesh>
            {/* Dished End Caps */}
            <mesh position={[0, 4.0, 0]} raycast={() => null}>
              <sphereGeometry args={[1.2, 24, 12, 0, Math.PI * 2, 0, Math.PI / 2]} />
              <meshStandardMaterial
                color={isSemiTransparent ? '#cbd5e1' : '#334155'}
                roughness={0.4}
                metalness={isSemiTransparent ? 0.1 : 0.6}
                transparent={isSemiTransparent}
                opacity={wallOpacity}
              />
            </mesh>
            <mesh position={[0, -4.0, 0]} rotation={[Math.PI, 0, 0]} raycast={() => null}>
              <sphereGeometry args={[1.2, 24, 12, 0, Math.PI * 2, 0, Math.PI / 2]} />
              <meshStandardMaterial
                color={isSemiTransparent ? '#cbd5e1' : '#334155'}
                roughness={0.4}
                metalness={isSemiTransparent ? 0.1 : 0.6}
                transparent={isSemiTransparent}
                opacity={wallOpacity}
              />
            </mesh>
            {/* Heavy Steel Saddle Support Mounts */}
            {[-2.5, 2.5].map((my, mi) => (
              <mesh key={`saddle-${mi}`} position={[0, my, -1.0]} rotation={[0, 0, -Math.PI / 2]} raycast={() => null}>
                <boxGeometry args={[0.5, 1.4, 1.6]} />
                <meshStandardMaterial
                  color={isSemiTransparent ? '#cbd5e1' : '#1e293b'}
                  metalness={isSemiTransparent ? 0.1 : 0.8}
                  transparent={isSemiTransparent}
                  opacity={wallOpacity}
                />
              </mesh>
            ))}
          </group>
        </group>
      )}

      {/* ============================================================= */}
      {/* E. STORAGE (Logistics Warehouse & Cold Provisions Bay)        */}
      {/* ============================================================= */}
      {code === 'STORAGE' && (
        <group>
          {/* Main Warehouse Enclosure */}
          <mesh raycast={shellRaycast} castShadow receiveShadow position={[0, sy / 2, 0]} renderOrder={8}>
            <boxGeometry args={[sx, sy, sz]} />
            <meshStandardMaterial
              color={wallColor}
              roughness={0.45}
              metalness={0.2}
              transparent={true}
              opacity={wallOpacity}
              depthWrite={wallDepthWrite}
            />
          </mesh>

          {/* Roof Parapet Frame & Deck */}
          <mesh raycast={shellRaycast} position={[0, sy + 0.15, 0]} renderOrder={12}>
            <boxGeometry args={[sx + 0.25, 0.3, sz + 0.25]} />
            <meshStandardMaterial
              color={parapetColor}
              roughness={0.6}
              metalness={0.4}
              transparent={true}
              opacity={parapetOpacity}
              depthWrite={roofDepthWrite}
            />
          </mesh>
          <mesh raycast={shellRaycast} position={[0, sy + 0.05, 0]} renderOrder={11}>
            <boxGeometry args={[sx * 0.98, 0.1, sz * 0.98]} />
            <meshStandardMaterial
              color={roofColor}
              roughness={0.5}
              metalness={0.25}
              transparent={true}
              opacity={roofOpacity}
              depthWrite={roofDepthWrite}
            />
          </mesh>

          {/* Horizontal Polar Container Corrugation / Ribbing Lines */}
          {[-2.2, -1.1, 0, 1.1, 2.2].map((yOff, i) => (
            <mesh key={`stor-rib-${i}`} position={[0, sy / 2 + yOff, sz / 2 + 0.04]} raycast={() => null}>
              <boxGeometry args={[sx * 0.92, 0.16, 0.06]} />
              <meshStandardMaterial
                color={isSemiTransparent ? '#cbd5e1' : '#94a3b8'}
                roughness={0.6}
                metalness={0.3}
                transparent={isSemiTransparent}
                opacity={wallOpacity}
              />
            </mesh>
          ))}

          {/* Heavy Overhead Industrial Cargo Loading Door (East facade) */}
          <group position={[sx / 2 + 0.05, sy * 0.45, 0]}>
            <mesh raycast={shellRaycast}>
              <boxGeometry args={[0.08, sy * 0.75, sz * 0.65]} />
              <meshStandardMaterial
                color={isSemiTransparent ? '#cbd5e1' : '#1e293b'}
                roughness={0.8}
                metalness={isSemiTransparent ? 0.1 : 0.5}
                transparent={isSemiTransparent}
                opacity={wallOpacity}
              />
            </mesh>
            {/* Safety Hazard Yellow/Orange Perimeter Frame */}
            <mesh position={[0.04, 0, 0]} raycast={() => null}>
              <boxGeometry args={[0.04, sy * 0.8, sz * 0.7]} />
              <meshStandardMaterial
                color={isSemiTransparent ? '#cbd5e1' : '#f59e0b'}
                metalness={isSemiTransparent ? 0.1 : 0.6}
                roughness={0.4}
                transparent={isSemiTransparent}
                opacity={wallOpacity}
              />
            </mesh>
          </group>

          {/* Rooftop Solar Array (3 rows x 3 cols) */}
          <SolarPanelArray
            position={[-1.5, sy + 0.1, 1.5]}
            rows={3}
            cols={3}
            panelWidth={2.3}
            panelHeight={2.8}
            tiltAngle={0.35}
            opacity={equipOpacity}
            depthWrite={equipDepthWrite}
          />

          {/* Communications Repeater Mast (Rear Corner) */}
          <LatticeTower
            position={[5.5, sy + 0.1, -5.5]}
            height={7.5}
            baseWidth={1.8}
            topWidth={0.8}
            sections={3}
            hasMetGear={false}
            opacity={equipOpacity}
            depthWrite={equipDepthWrite}
          />
        </group>
      )}

      {/* ============================================================= */}
      {/* F. COMMS (Telecommunications Shelter, Mast & Ku-Band Dish)    */}
      {/* ============================================================= */}
      {code === 'COMMS' && (
        <group>
          {/* Base RF Operations Shelter */}
          <mesh raycast={shellRaycast} castShadow receiveShadow position={[0, sy / 2, 0]} renderOrder={8}>
            <boxGeometry args={[sx, sy, sz]} />
            <meshStandardMaterial
              color={wallColor}
              roughness={0.35}
              metalness={0.2}
              transparent={true}
              opacity={wallOpacity}
              depthWrite={wallDepthWrite}
            />
          </mesh>

          {/* Roof Parapet */}
          <mesh raycast={shellRaycast} position={[0, sy + 0.1, 0]} renderOrder={12}>
            <boxGeometry args={[sx + 0.2, 0.2, sz + 0.2]} />
            <meshStandardMaterial
              color={parapetColor}
              roughness={0.6}
              metalness={0.4}
              transparent={true}
              opacity={parapetOpacity}
              depthWrite={roofDepthWrite}
            />
          </mesh>

          {/* Heavy Structural Steel Pedestal Collar */}
          <mesh position={[0, sy + 0.4, 0]}>
            <cylinderGeometry args={[2.2, 2.8, 0.6, 16]} />
            <meshStandardMaterial
              color={isSemiTransparent ? '#cbd5e1' : '#1e293b'}
              roughness={0.6}
              metalness={isSemiTransparent ? 0.1 : 0.7}
              transparent={isSemiTransparent}
              opacity={equipOpacity}
            />
          </mesh>

          {/* Multi-stage High-Altitude Open Lattice Steel Communications Tower */}
          <LatticeTower
            position={[0, sy + 0.7, 0]}
            height={15.0}
            baseWidth={3.2}
            topWidth={1.2}
            sections={6}
            hasMetGear={true}
            opacity={equipOpacity}
            depthWrite={equipDepthWrite}
          />

          {/* Primary High-Gain Parabolic Ku-Band Satellite Tracking Dish */}
          <ParabolicDishAssembly
            position={[0, sy + 7.8, 1.8]}
            radius={2.6}
            azimuth={0.4}
            elevation={0.52}
            dishColor="#ffffff"
            feedColor="#f97316"
            opacity={equipOpacity}
            depthWrite={equipDepthWrite}
          />
        </group>
      )}

      {/* ------------------------------------------------------------- */}
      {/* 4. 3D MODULE IDENTIFIER BADGE                                 */}
      {/* ------------------------------------------------------------- */}
      {showLabels && (
        <Html
          position={[0, sy + (code === 'COMMS' ? 12.0 : 2.6), 0]}
          center
          distanceFactor={46}
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
                background: zoneStatus === 'CRITICAL' ? '#e03131' : zoneStatus === 'WARNING' ? '#f59f00' : code === 'MAIN' ? '#b65a1f' : '#8c95a3'
              }}
            />
            <span>{zone.name}</span>
          </div>
        </Html>
      )}

      {/* ------------------------------------------------------------- */}
      {/* 5. INTERNAL ASSET MARKERS (X-RAY and SYSTEM modes)             */}
      {/* ------------------------------------------------------------- */}
      {internalAssets.map((asset) => {
        const isAssociated = associatedAssetId === asset.fullId;
        return (
          <InternalAssetMarker
            key={asset.fullId}
            id={asset.fullId}
            type={asset.type}
            label={asset.label}
            position={[
              asset.worldPos[0] - px,
              asset.worldPos[1] - py,
              asset.worldPos[2] - pz
            ]}
            status={asset.status}
            isHighlighted={isHighlighted || selectedAssetId === asset.fullId || isAssociated}
            isSelected={selectedAssetId === asset.fullId || isAssociated}
            isPrimary={asset.isPrimary !== false}
            labelY={asset.labelY || 3.2}
            isAssociated={isAssociated}
            selectedSensorId={isAssociated ? selectedSensor?.id : null}
            showLabel={true}
            onClick={(id) => onSelectAsset && onSelectAsset({ id, type: asset.type, label: asset.label, zone: code, status: asset.status })}
          />
        );
      })}

      {/* ------------------------------------------------------------- */}
      {/* 6. CROSS-MODULE HIGHLIGHT RING                                 */}
      {/* ------------------------------------------------------------- */}
      {isHighlighted && (
        <mesh
          position={[0, 0.28, 0]}
          rotation={[-Math.PI / 2, 0, 0]}
          renderOrder={40}
          raycast={() => null}
        >
          <ringGeometry args={[Math.min(sx, sz) * 0.48, Math.min(sx, sz) * 0.52, 48]} />
          <meshBasicMaterial
            color="#b65a1f"
            transparent
            opacity={0.80}
            depthWrite={false}
            side={THREE.DoubleSide}
          />
        </mesh>
      )}
    </group>
  );
};

export default StationZone;
