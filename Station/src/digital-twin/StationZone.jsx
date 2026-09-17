import React, { useMemo, useRef } from 'react';
import * as THREE from 'three';
import { useFrame } from '@react-three/fiber';
import { Html } from '@react-three/drei';

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
  hasSelectedZone = false
}) => {
  const [px, py, pz] = zone.position;
  const [sx, sy, sz] = zone.size;
  const code = zone.code || zone.id;

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

  const radialTexture = useMemo(() => getRadialHeatmapTexture(meta.rgb), [meta.rgb]);

  // When a sensor is selected, its zone heatmap becomes more prominent while others are subdued
  const effectiveFloorOpacity = hasSelectedZone
    ? isSelectedZone
      ? Math.min(0.95, meta.floorOpacity * 1.45)
      : meta.floorOpacity * 0.40
    : meta.floorOpacity;

  const effectiveGlowOpacity = hasSelectedZone
    ? isSelectedZone
      ? 1.0
      : meta.glowOpacity * 0.40
    : meta.glowOpacity;

  // Pulsing animation for critical alert zone or active selection
  const pulseRef = useRef();
  useFrame(({ clock }) => {
    if (pulseRef.current && (zoneStatus === 'CRITICAL' || isSelectedZone)) {
      const s = 1 + Math.sin(clock.getElapsedTime() * 4.0) * 0.08;
      pulseRef.current.scale.set(s, 1, s);
    }
  });

  // Material settings:
  // In normal mode: 100% opaque realistic buildings.
  // In heatmap mode: Roof is 92% transparent (8% opacity), walls are 32% opacity, equipment 18% opacity.
  const wallOpacity   = showHeatmap ? 0.32 : 1.0;
  const wallDepthWrite = !showHeatmap;

  const roofOpacity   = showHeatmap ? 0.08 : 1.0;
  const roofColor     = showHeatmap ? '#f4efe6' : '#323944';
  const roofDepthWrite = !showHeatmap;

  const equipOpacity  = showHeatmap ? 0.18 : 1.0;
  const equipDepthWrite = !showHeatmap;

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
          <mesh castShadow>
            <cylinderGeometry args={[stiltRadius, stiltRadius, stiltHeight, 8]} />
            <meshStandardMaterial color="#2d333b" roughness={0.7} metalness={0.5} />
          </mesh>
          <mesh position={[0, -stiltHeight / 2 + 0.06, 0]}>
            <boxGeometry args={[0.75, 0.14, 0.75]} />
            <meshStandardMaterial color="#3d444e" roughness={0.8} metalness={0.3} />
          </mesh>
        </group>
      ))}

      {/* ------------------------------------------------------------- */}
      {/* 2. INTERIOR SPATIAL CONDITION HEATMAP (Inspection Mode)       */}
      {/* Shown inside each building volume above floor level           */}
      {/* ------------------------------------------------------------- */}
      {showHeatmap && (
        <group position={[0, 0, 0]}>
          {/* A. Base Illuminated Interior Floor Plate */}
          <mesh
            position={[0, 0.12, 0]}
            rotation={[-Math.PI / 2, 0, 0]}
            renderOrder={5}
            raycast={() => null}
          >
            <planeGeometry args={[sx * 0.94, sz * 0.94]} />
            <meshBasicMaterial
              color={meta.hex}
              transparent
              opacity={effectiveFloorOpacity}
              depthWrite={false}
              side={THREE.DoubleSide}
            />
          </mesh>

          {/* B. High-Contrast Soft Radial Gradient Condition Wash */}
          <mesh
            position={[0, 0.18, 0]}
            rotation={[-Math.PI / 2, 0, 0]}
            renderOrder={6}
            raycast={() => null}
          >
            <planeGeometry args={[sx * 0.90, sz * 0.90]} />
            <meshBasicMaterial
              map={radialTexture}
              transparent
              opacity={effectiveGlowOpacity}
              depthWrite={false}
              side={THREE.DoubleSide}
            />
          </mesh>

          {/* C. Selected Zone Prominence Highlight Ring */}
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

          {/* D. Critical Zone Pulsating Alert Ring */}
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

          {/* E. Warning Zone Alert Ring */}
          {zoneStatus === 'WARNING' && !isSelectedZone && (
            <mesh
              position={[0, 0.24, 0]}
              rotation={[-Math.PI / 2, 0, 0]}
              renderOrder={7}
              raycast={() => null}
            >
              <ringGeometry
                args={[
                  Math.min(sx, sz) * 0.32,
                  Math.min(sx, sz) * 0.38,
                  36
                ]}
              />
              <meshBasicMaterial
                color="#faad14"
                transparent
                opacity={0.80}
                depthWrite={false}
                side={THREE.DoubleSide}
              />
            </mesh>
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

      {/* === A. MAIN BUILDING (Central Anchor & Primary Habitat Hub) === */}
      {code === 'MAIN' && (
        <group>
          {/* Lower Habitat Tier */}
          <mesh castShadow receiveShadow position={[0, sy * 0.28, 0]} renderOrder={8}>
            <boxGeometry args={[sx, sy * 0.56, sz]} />
            <meshStandardMaterial
              color="#eae5dd"
              roughness={0.6}
              metalness={0.15}
              transparent={true}
              opacity={wallOpacity}
              depthWrite={wallDepthWrite}
            />
          </mesh>

          {/* Upper Habitat Tier */}
          <mesh castShadow receiveShadow position={[0, sy * 0.78, 0]} renderOrder={9}>
            <boxGeometry args={[sx * 0.96, sy * 0.44, sz * 0.94]} />
            <meshStandardMaterial
              color="#e4ded5"
              roughness={0.55}
              metalness={0.2}
              transparent={true}
              opacity={wallOpacity}
              depthWrite={wallDepthWrite}
            />
          </mesh>

          {/* Mid-level Structural Belt Line Trim */}
          <mesh position={[0, sy * 0.56, 0]} renderOrder={10}>
            <boxGeometry args={[sx + 0.15, 0.2, sz + 0.15]} />
            <meshStandardMaterial
              color="#383f4a"
              roughness={0.7}
              metalness={0.4}
              transparent={true}
              opacity={showHeatmap ? 0.30 : 1.0}
              depthWrite={wallDepthWrite}
            />
          </mesh>

          {/* Transparent Roof Observation Canopy (or Solid Opaque Roof when Heatmap OFF) */}
          <mesh position={[0, sy + 0.1, 0]} renderOrder={12}>
            <boxGeometry args={[sx * 0.98, 0.22, sz * 0.96]} />
            <meshStandardMaterial
              color={roofColor}
              roughness={0.4}
              metalness={0.3}
              transparent={true}
              opacity={roofOpacity}
              depthWrite={roofDepthWrite}
            />
          </mesh>

          {/* Roof Parapet Architectural Edge Frame */}
          {showHeatmap && (
            <mesh position={[0, sy + 0.12, 0]} renderOrder={14}>
              <boxGeometry args={[sx + 0.15, 0.14, sz + 0.15]} />
              <meshStandardMaterial
                color="#2d333b"
                roughness={0.6}
                metalness={0.4}
                transparent={true}
                opacity={0.25}
                depthWrite={false}
              />
            </mesh>
          )}

          {/* South Facade Ribbon Windows */}
          <mesh position={[0, sy * 0.35, sz / 2 + 0.03]}>
            <boxGeometry args={[sx * 0.75, 0.8, 0.05]} />
            <meshStandardMaterial color="#1a2028" roughness={0.1} metalness={0.85} transparent={true} opacity={wallOpacity} />
          </mesh>
          <mesh position={[0, sy * 0.75, sz * 0.47 + 0.03]}>
            <boxGeometry args={[sx * 0.70, 0.7, 0.05]} />
            <meshStandardMaterial color="#1a2028" roughness={0.1} metalness={0.85} transparent={true} opacity={wallOpacity} />
          </mesh>

          {/* North Facade Ribbon Windows */}
          <mesh position={[0, sy * 0.35, -sz / 2 - 0.03]}>
            <boxGeometry args={[sx * 0.75, 0.8, 0.05]} />
            <meshStandardMaterial color="#1a2028" roughness={0.1} metalness={0.85} transparent={true} opacity={wallOpacity} />
          </mesh>

          {/* South Entry Airlock Portal & Vestibule */}
          <group position={[0, sy * 0.25, sz / 2 + 1.2]}>
            <mesh castShadow>
              <boxGeometry args={[4.4, sy * 0.5, 2.4]} />
              <meshStandardMaterial color="#dcd5cb" roughness={0.6} metalness={0.2} transparent={true} opacity={wallOpacity} />
            </mesh>
            <mesh position={[0, 0, 1.22]}>
              <boxGeometry args={[2.4, sy * 0.42, 0.06]} />
              <meshStandardMaterial color="#b65a1f" roughness={0.4} metalness={0.5} transparent={true} opacity={wallOpacity} />
            </mesh>
          </group>

          {/* Central Rooftop HVAC & Environmental Control Plant */}
          <group position={[0, sy + 0.7, 0]}>
            <mesh castShadow position={[0, 0, 0]}>
              <boxGeometry args={[6.0, 1.2, 4.5]} />
              <meshStandardMaterial
                color="#c2bbb0"
                roughness={0.6}
                metalness={0.3}
                transparent={true}
                opacity={equipOpacity}
                depthWrite={equipDepthWrite}
              />
            </mesh>
            {[-2.0, 2.0].map((lx, i) => (
              <mesh key={`hvac-louver-${i}`} position={[lx, 0.1, 2.27]}>
                <boxGeometry args={[1.5, 0.8, 0.06]} />
                <meshStandardMaterial
                  color="#2d333b"
                  roughness={0.9}
                  transparent={true}
                  opacity={equipOpacity}
                  depthWrite={equipDepthWrite}
                />
              </mesh>
            ))}
          </group>
        </group>
      )}

      {/* === B. RESEARCH BUILDING (Specialized Scientific Laboratory) === */}
      {code === 'RESEARCH' && (
        <group>
          {/* Main Laboratory Body */}
          <mesh castShadow receiveShadow position={[0, sy / 2, 0]} renderOrder={8}>
            <boxGeometry args={[sx, sy, sz]} />
            <meshStandardMaterial
              color="#e5ded4"
              roughness={0.55}
              metalness={0.2}
              transparent={true}
              opacity={wallOpacity}
              depthWrite={wallDepthWrite}
            />
          </mesh>

          {/* Transparent Roof Observation Canopy (or Solid Opaque Roof when Heatmap OFF) */}
          <mesh position={[0, sy + 0.1, 0]} renderOrder={12}>
            <boxGeometry args={[sx + 0.15, 0.2, sz + 0.15]} />
            <meshStandardMaterial
              color={roofColor}
              roughness={0.5}
              metalness={0.3}
              transparent={true}
              opacity={roofOpacity}
              depthWrite={roofDepthWrite}
            />
          </mesh>

          {/* Roof Parapet Architectural Edge Frame */}
          {showHeatmap && (
            <mesh position={[0, sy + 0.12, 0]} renderOrder={14}>
              <boxGeometry args={[sx + 0.2, 0.14, sz + 0.2]} />
              <meshStandardMaterial
                color="#2d333b"
                roughness={0.6}
                metalness={0.4}
                transparent={true}
                opacity={0.25}
                depthWrite={false}
              />
            </mesh>
          )}

          {/* Laboratory Observation Ribbon Windows (South & East) */}
          <mesh position={[0, sy * 0.55, sz / 2 + 0.03]}>
            <boxGeometry args={[sx * 0.8, 0.85, 0.05]} />
            <meshStandardMaterial color="#1a2028" roughness={0.1} metalness={0.85} transparent={true} opacity={wallOpacity} />
          </mesh>
          <mesh position={[sx / 2 + 0.03, sy * 0.55, 0]} rotation={[0, Math.PI / 2, 0]}>
            <boxGeometry args={[sz * 0.7, 0.85, 0.05]} />
            <meshStandardMaterial color="#1a2028" roughness={0.1} metalness={0.85} transparent={true} opacity={wallOpacity} />
          </mesh>

          {/* Rooftop Scientific Optical / Lidar Observation Dome */}
          <group position={[-2.5, sy + 0.2, 1.5]}>
            <mesh position={[0, 0.4, 0]}>
              <cylinderGeometry args={[2.2, 2.4, 0.8, 24]} />
              <meshStandardMaterial
                color="#3a424e"
                roughness={0.5}
                metalness={0.4}
                transparent={true}
                opacity={equipOpacity}
                depthWrite={equipDepthWrite}
              />
            </mesh>
            <mesh castShadow position={[0, 0.8, 0]}>
              <sphereGeometry args={[2.2, 24, 16, 0, Math.PI * 2, 0, Math.PI * 0.5]} />
              <meshStandardMaterial
                color="#f8f6f0"
                roughness={0.2}
                metalness={0.2}
                transparent={true}
                opacity={equipOpacity}
                depthWrite={equipDepthWrite}
              />
            </mesh>
            <mesh position={[0, 1.9, 0.9]}>
              <boxGeometry args={[0.5, 2.0, 0.3]} />
              <meshStandardMaterial color="#15181c" roughness={0.2} metalness={0.8} transparent={true} opacity={equipOpacity} />
            </mesh>
          </group>

          {/* Rooftop Atmospheric Chemistry Sampling Mast & Met Arm */}
          <group position={[3.5, sy + 1.6, -2.0]}>
            <mesh castShadow>
              <cylinderGeometry args={[0.12, 0.16, 3.2, 8]} />
              <meshStandardMaterial
                color="#2d333b"
                roughness={0.5}
                metalness={0.7}
                transparent={true}
                opacity={equipOpacity}
                depthWrite={equipDepthWrite}
              />
            </mesh>
            <mesh position={[0, 1.2, 0]}>
              <boxGeometry args={[1.8, 0.08, 0.08]} />
              <meshStandardMaterial
                color="#b65a1f"
                roughness={0.4}
                metalness={0.6}
                transparent={true}
                opacity={equipOpacity}
                depthWrite={equipDepthWrite}
              />
            </mesh>
          </group>

          {/* Cleanroom Air Filtration Duct Unit (East wall) */}
          <group position={[sx / 2 + 0.5, sy * 0.5, -2.0]}>
            <mesh castShadow>
              <boxGeometry args={[1.0, sy * 0.7, 3.0]} />
              <meshStandardMaterial
                color="#c0b8ac"
                roughness={0.6}
                metalness={0.3}
                transparent={true}
                opacity={wallOpacity}
                depthWrite={wallDepthWrite}
              />
            </mesh>
          </group>
        </group>
      )}

      {/* === C. ENERGY / POWER (Power Infrastructure & Substation) === */}
      {code === 'ENERGY' && (
        <group>
          {/* Main Power Module Body */}
          <mesh castShadow receiveShadow position={[0, sy / 2, 0]} renderOrder={8}>
            <boxGeometry args={[sx, sy, sz]} />
            <meshStandardMaterial
              color="#ded7cc"
              roughness={0.6}
              metalness={0.2}
              transparent={true}
              opacity={wallOpacity}
              depthWrite={wallDepthWrite}
            />
          </mesh>

          {/* Transparent Roof Observation Canopy (or Solid Opaque Roof when Heatmap OFF) */}
          <mesh position={[0, sy + 0.1, 0]} renderOrder={12}>
            <boxGeometry args={[sx + 0.15, 0.2, sz + 0.15]} />
            <meshStandardMaterial
              color={roofColor}
              roughness={0.6}
              metalness={0.4}
              transparent={true}
              opacity={roofOpacity}
              depthWrite={roofDepthWrite}
            />
          </mesh>

          {/* Roof Parapet Architectural Edge Frame */}
          {showHeatmap && (
            <mesh position={[0, sy + 0.12, 0]} renderOrder={14}>
              <boxGeometry args={[sx + 0.2, 0.14, sz + 0.2]} />
              <meshStandardMaterial
                color="#2d333b"
                roughness={0.6}
                metalness={0.4}
                transparent={true}
                opacity={0.25}
                depthWrite={false}
              />
            </mesh>
          )}

          {/* Dual Angled Photovoltaic Solar Array Test Racks on Roof */}
          <group position={[-2.5, sy + 0.7, 0]}>
            {[-2.5, 2.5].map((zOffset, i) => (
              <group key={`pv-rack-${i}`} position={[0, 0, zOffset]} rotation={[0.35, 0, 0]}>
                <mesh castShadow>
                  <boxGeometry args={[7.0, 0.12, 3.2]} />
                  <meshStandardMaterial
                    color="#182333"
                    roughness={0.2}
                    metalness={0.85}
                    transparent={true}
                    opacity={equipOpacity}
                    depthWrite={equipDepthWrite}
                  />
                </mesh>
                <mesh position={[0, 0.07, 0]}>
                  <boxGeometry args={[6.8, 0.02, 3.0]} />
                  <meshStandardMaterial
                    color="#2d4059"
                    roughness={0.3}
                    metalness={0.7}
                    transparent={true}
                    opacity={equipOpacity}
                    depthWrite={equipDepthWrite}
                  />
                </mesh>
              </group>
            ))}
          </group>

          {/* High-Voltage Exterior Transformer Yard (East roof) */}
          <group position={[4.8, sy + 0.8, 0]}>
            <mesh castShadow position={[0, 0, 0]}>
              <boxGeometry args={[3.6, 1.4, 4.0]} />
              <meshStandardMaterial
                color="#4a5360"
                roughness={0.5}
                metalness={0.5}
                transparent={true}
                opacity={equipOpacity}
                depthWrite={equipDepthWrite}
              />
            </mesh>
            {[-1.8, 1.8].map((fx, i) => (
              <mesh key={`xfr-fin-${i}`} position={[fx, 0, 0]}>
                <boxGeometry args={[0.1, 1.2, 3.6]} />
                <meshStandardMaterial
                  color="#2d333b"
                  roughness={0.8}
                  metalness={0.4}
                  transparent={true}
                  opacity={equipOpacity}
                  depthWrite={equipDepthWrite}
                />
              </mesh>
            ))}
          </group>

          {/* Outdoor Battery Storage Bank Enclosure Cabinets (North facade) */}
          <group position={[0, sy * 0.45, -sz / 2 - 0.7]}>
            <mesh castShadow>
              <boxGeometry args={[sx * 0.7, sy * 0.8, 1.3]} />
              <meshStandardMaterial
                color="#b26814"
                roughness={0.5}
                metalness={0.3}
                transparent={true}
                opacity={wallOpacity}
                depthWrite={wallDepthWrite}
              />
            </mesh>
            {[-3.0, 0, 3.0].map((vx, i) => (
              <mesh key={`bat-vent-${i}`} position={[vx, 0.3, -0.67]}>
                <boxGeometry args={[1.2, 0.8, 0.05]} />
                <meshStandardMaterial color="#1a1d22" roughness={0.9} transparent={true} opacity={wallOpacity} />
              </mesh>
            ))}
          </group>
        </group>
      )}

      {/* === D. GENERATOR (Industrial Power Plant Facility) === */}
      {code === 'GENERATOR' && (
        <group>
          {/* Main Industrial Housing Body */}
          <mesh castShadow receiveShadow position={[0, sy / 2, 0]} renderOrder={8}>
            <boxGeometry args={[sx, sy, sz]} />
            <meshStandardMaterial
              color="#d4ccc0"
              roughness={0.7}
              metalness={0.2}
              transparent={true}
              opacity={wallOpacity}
              depthWrite={wallDepthWrite}
            />
          </mesh>

          {/* Transparent Roof Observation Canopy (or Solid Opaque Roof when Heatmap OFF) */}
          <mesh position={[0, sy + 0.1, 0]} renderOrder={12}>
            <boxGeometry args={[sx + 0.15, 0.2, sz + 0.15]} />
            <meshStandardMaterial
              color={roofColor}
              roughness={0.7}
              metalness={0.4}
              transparent={true}
              opacity={roofOpacity}
              depthWrite={roofDepthWrite}
            />
          </mesh>

          {/* Roof Parapet Architectural Edge Frame */}
          {showHeatmap && (
            <mesh position={[0, sy + 0.12, 0]} renderOrder={14}>
              <boxGeometry args={[sx + 0.2, 0.14, sz + 0.2]} />
              <meshStandardMaterial
                color="#2d333b"
                roughness={0.6}
                metalness={0.4}
                transparent={true}
                opacity={0.25}
                depthWrite={false}
              />
            </mesh>
          )}

          {/* Prominent Twin Diesel Exhaust Stacks with Rain Caps */}
          {[-2.2, 2.2].map((offX, i) => (
            <group key={`gen-exhaust-${i}`} position={[offX, sy + 2.4, -sz * 0.2]}>
              <mesh castShadow>
                <cylinderGeometry args={[0.35, 0.42, 4.8, 16]} />
                <meshStandardMaterial
                  color="#3d444e"
                  roughness={0.6}
                  metalness={0.6}
                  transparent={true}
                  opacity={equipOpacity}
                  depthWrite={equipDepthWrite}
                />
              </mesh>
              <mesh position={[0, 2.5, 0]}>
                <coneGeometry args={[0.65, 0.45, 16]} />
                <meshStandardMaterial
                  color="#22262c"
                  roughness={0.5}
                  metalness={0.5}
                  transparent={true}
                  opacity={equipOpacity}
                  depthWrite={equipDepthWrite}
                />
              </mesh>
            </group>
          ))}

          {/* Massive Western Cooling Radiator & Ventilation Louver Bank */}
          <group position={[-sx / 2 - 0.6, sy * 0.5, 0]}>
            <mesh castShadow>
              <boxGeometry args={[1.2, sy * 0.8, sz * 0.75]} />
              <meshStandardMaterial
                color="#373d47"
                roughness={0.8}
                metalness={0.4}
                transparent={true}
                opacity={wallOpacity}
                depthWrite={wallDepthWrite}
              />
            </mesh>
            <mesh position={[-0.62, 0, 0]}>
              <boxGeometry args={[0.06, sy * 0.7, sz * 0.68]} />
              <meshStandardMaterial color="#1a1d22" roughness={0.9} transparent={true} opacity={wallOpacity} />
            </mesh>
          </group>

          {/* Cylindrical Fuel Day-Tank (South facade) */}
          <group position={[0, sy * 0.4, sz / 2 + 1.2]} rotation={[0, 0, Math.PI / 2]}>
            <mesh castShadow>
              <cylinderGeometry args={[1.0, 1.0, 6.5, 20]} />
              <meshStandardMaterial
                color="#7a7062"
                roughness={0.5}
                metalness={0.5}
                transparent={true}
                opacity={wallOpacity}
                depthWrite={wallDepthWrite}
              />
            </mesh>
            <mesh position={[0, 3.3, 0]}>
              <sphereGeometry args={[1.0, 20, 10, 0, Math.PI * 2, 0, Math.PI / 2]} />
              <meshStandardMaterial color="#63594c" roughness={0.5} metalness={0.5} transparent={true} opacity={wallOpacity} />
            </mesh>
            <mesh position={[0, -3.3, 0]} rotation={[Math.PI, 0, 0]}>
              <sphereGeometry args={[1.0, 20, 10, 0, Math.PI * 2, 0, Math.PI / 2]} />
              <meshStandardMaterial color="#63594c" roughness={0.5} metalness={0.5} transparent={true} opacity={wallOpacity} />
            </mesh>
          </group>
        </group>
      )}

      {/* === E. STORAGE (Logistics Warehouse & Cold Provisions Bay) === */}
      {code === 'STORAGE' && (
        <group>
          {/* Main Warehouse Enclosure */}
          <mesh castShadow receiveShadow position={[0, sy / 2, 0]} renderOrder={8}>
            <boxGeometry args={[sx, sy, sz]} />
            <meshStandardMaterial
              color="#cfc7b9"
              roughness={0.65}
              metalness={0.2}
              transparent={true}
              opacity={wallOpacity}
              depthWrite={wallDepthWrite}
            />
          </mesh>

          {/* Transparent Roof Observation Canopy (or Solid Opaque Roof when Heatmap OFF) */}
          <mesh position={[0, sy + 0.1, 0]} renderOrder={12}>
            <boxGeometry args={[sx + 0.15, 0.2, sz + 0.15]} />
            <meshStandardMaterial
              color={roofColor}
              roughness={0.7}
              metalness={0.3}
              transparent={true}
              opacity={roofOpacity}
              depthWrite={roofDepthWrite}
            />
          </mesh>

          {/* Roof Parapet Architectural Edge Frame */}
          {showHeatmap && (
            <mesh position={[0, sy + 0.12, 0]} renderOrder={14}>
              <boxGeometry args={[sx + 0.2, 0.14, sz + 0.2]} />
              <meshStandardMaterial
                color="#2d333b"
                roughness={0.6}
                metalness={0.4}
                transparent={true}
                opacity={0.25}
                depthWrite={false}
              />
            </mesh>
          )}

          {/* Horizontal Polar Container Ribbing Lines */}
          {[-1.2, -0.4, 0.4, 1.2].map((yOff, i) => (
            <mesh key={`stor-rib-${i}`} position={[0, sy / 2 + yOff, sz / 2 + 0.04]}>
              <boxGeometry args={[sx * 0.94, 0.2, 0.06]} />
              <meshStandardMaterial color="#b5ad9e" roughness={0.6} metalness={0.3} transparent={true} opacity={wallOpacity} />
            </mesh>
          ))}

          {/* Overhead Cargo Door (East facade) */}
          <group position={[sx / 2 + 0.04, sy * 0.45, 0]}>
            <mesh>
              <boxGeometry args={[0.06, sy * 0.75, sz * 0.65]} />
              <meshStandardMaterial color="#2d333b" roughness={0.8} metalness={0.4} transparent={true} opacity={wallOpacity} />
            </mesh>
            <mesh position={[0.04, 0, 0]}>
              <boxGeometry args={[0.02, sy * 0.78, sz * 0.68]} />
              <meshStandardMaterial color="#b65a1f" roughness={0.4} metalness={0.6} transparent={true} opacity={wallOpacity} />
            </mesh>
          </group>

          {/* Exterior Cargo Staging Platform with Supply Pallet & Drums */}
          <group position={[sx / 2 + 2.0, 0.4, 0]}>
            <mesh receiveShadow>
              <boxGeometry args={[3.2, 0.3, 5.5]} />
              <meshStandardMaterial color="#4a4237" roughness={0.9} transparent={true} opacity={wallOpacity} />
            </mesh>
            <mesh castShadow position={[0, 0.85, 0]}>
              <boxGeometry args={[2.0, 1.4, 3.5]} />
              <meshStandardMaterial color="#887967" roughness={0.7} transparent={true} opacity={wallOpacity} />
            </mesh>
          </group>
        </group>
      )}

      {/* === F. COMMS (Telecommunications Facility, Mast & Dish) === */}
      {code === 'COMMS' && (
        <group>
          {/* Base RF Telemetry Operations Shelter */}
          <mesh castShadow receiveShadow position={[0, sy / 2, 0]} renderOrder={8}>
            <boxGeometry args={[sx, sy, sz]} />
            <meshStandardMaterial
              color="#dcd5c9"
              roughness={0.6}
              metalness={0.2}
              transparent={true}
              opacity={wallOpacity}
              depthWrite={wallDepthWrite}
            />
          </mesh>

          {/* Transparent Roof Observation Canopy (or Solid Opaque Roof when Heatmap OFF) */}
          <mesh position={[0, sy + 0.08, 0]} renderOrder={12}>
            <boxGeometry args={[sx + 0.12, 0.16, sz + 0.12]} />
            <meshStandardMaterial
              color={roofColor}
              roughness={0.6}
              metalness={0.5}
              transparent={true}
              opacity={roofOpacity}
              depthWrite={roofDepthWrite}
            />
          </mesh>

          {/* Roof Parapet Architectural Edge Frame */}
          {showHeatmap && (
            <mesh position={[0, sy + 0.10, 0]} renderOrder={14}>
              <boxGeometry args={[sx + 0.18, 0.12, sz + 0.18]} />
              <meshStandardMaterial
                color="#2d333b"
                roughness={0.6}
                metalness={0.4}
                transparent={true}
                opacity={0.25}
                depthWrite={false}
              />
            </mesh>
          )}

          {/* Heavy Steel Mast Pedestal Collar */}
          <mesh position={[0, sy + 0.35, 0]}>
            <cylinderGeometry args={[2.0, 2.5, 0.5, 16]} />
            <meshStandardMaterial
              color="#2b313b"
              roughness={0.6}
              metalness={0.6}
              transparent={true}
              opacity={equipOpacity}
              depthWrite={equipDepthWrite}
            />
          </mesh>

          {/* Open-Truss Structural Communications Mast */}
          <group position={[0, sy + 6.0, 0]}>
            <mesh castShadow>
              <cylinderGeometry args={[0.35, 0.6, 11.0, 8]} />
              <meshStandardMaterial
                color="#3e4652"
                roughness={0.5}
                metalness={0.7}
                transparent={true}
                opacity={equipOpacity}
                depthWrite={equipDepthWrite}
              />
            </mesh>
            {[
              [-1.0, -1.0],
              [1.0, -1.0],
              [-1.0, 1.0],
              [1.0, 1.0]
            ].map(([tx, tz], i) => (
              <mesh key={`comms-chord-${i}`} position={[tx, 0, tz]}>
                <cylinderGeometry args={[0.08, 0.1, 11.0, 6]} />
                <meshStandardMaterial
                  color="#2d333b"
                  roughness={0.6}
                  metalness={0.6}
                  transparent={true}
                  opacity={equipOpacity}
                  depthWrite={equipDepthWrite}
                />
              </mesh>
            ))}
          </group>

          {/* Large Parabolic Ku-Band Satellite Tracking Dish */}
          <group position={[0, sy + 7.5, 1.2]} rotation={[0.42, 0, 0]}>
            <mesh castShadow>
              <sphereGeometry args={[2.2, 24, 16, 0, Math.PI * 2, 0, Math.PI * 0.42]} />
              <meshStandardMaterial
                color="#ede8df"
                roughness={0.3}
                metalness={0.3}
                side={2}
                transparent={true}
                opacity={equipOpacity}
                depthWrite={equipDepthWrite}
              />
            </mesh>
            <mesh position={[0, 0, 1.1]} rotation={[Math.PI / 2, 0, 0]}>
              <cylinderGeometry args={[0.12, 0.16, 1.0, 8]} />
              <meshStandardMaterial color="#b65a1f" roughness={0.3} metalness={0.7} transparent={true} opacity={equipOpacity} />
            </mesh>
            <mesh position={[0, -0.6, -0.4]}>
              <boxGeometry args={[1.2, 1.0, 1.0]} />
              <meshStandardMaterial color="#282d36" roughness={0.6} metalness={0.6} transparent={true} opacity={equipOpacity} />
            </mesh>
          </group>

          {/* High-Altitude VHF/UHF Omnidirectional Dipole Spire */}
          <mesh castShadow position={[0, sy + 13.0, -0.8]}>
            <cylinderGeometry args={[0.05, 0.08, 5.0, 8]} />
            <meshStandardMaterial
              color="#22262e"
              roughness={0.4}
              metalness={0.8}
              transparent={true}
              opacity={equipOpacity}
              depthWrite={equipDepthWrite}
            />
          </mesh>
        </group>
      )}

      {/* ------------------------------------------------------------- */}
      {/* 4. 3D MODULE IDENTIFIER BADGE                                 */}
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
                background: zoneStatus === 'CRITICAL' ? '#e03131' : zoneStatus === 'WARNING' ? '#f59f00' : code === 'MAIN' ? '#b65a1f' : '#8c95a3'
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
