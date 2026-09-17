import React, { useMemo, useRef } from 'react';
import * as THREE from 'three';
import { useFrame } from '@react-three/fiber';

// Helper to determine the roof/surface elevation at any station coordinate (x, z)
// Ensures heatmap projection planes hug the building roofs and ground without z-fighting.
const getSurfaceElevation = (x, z) => {
  // Main Building footprint
  if (Math.abs(x) <= 11.5 && Math.abs(z) <= 7.5) return 5.8;
  // Research footprint
  if (x >= 15.5 && x <= 30.5 && Math.abs(z) <= 6.5) return 5.4;
  // Energy footprint
  if (Math.abs(x) <= 8.5 && z >= -24.5 && z <= -11.5) return 5.0;
  // Generator footprint
  if (x >= -25.0 && x <= -11.0 && z >= -24.5 && z <= -11.5) return 4.8;
  // Storage footprint
  if (x >= 10.5 && x <= 25.5 && z >= -24.5 && z <= -11.5) return 4.6;
  // Communications base shelter footprint
  if (Math.abs(x) <= 4.5 && z >= -36.5 && z <= -27.5) return 4.6;
  // Connecting corridors
  if (x >= 11.0 && x <= 16.0 && Math.abs(z) <= 2.0) return 4.2;
  if (Math.abs(x) <= 2.0 && z >= -12.0 && z <= -7.0) return 4.2;
  // Antarctic terrain datum
  return 0.05;
};

// Generates an ultra-lightweight (64x64) procedural Gaussian radial gradient canvas texture
const createRadialTexture = (rgbColor, maxOpacity = 0.55) => {
  const canvas = document.createElement('canvas');
  canvas.width = 64;
  canvas.height = 64;
  const ctx = canvas.getContext('2d');

  const gradient = ctx.createRadialGradient(32, 32, 0, 32, 32, 32);
  gradient.addColorStop(0, `rgba(${rgbColor}, ${maxOpacity})`);
  gradient.addColorStop(0.4, `rgba(${rgbColor}, ${maxOpacity * 0.55})`);
  gradient.addColorStop(0.75, `rgba(${rgbColor}, ${maxOpacity * 0.18})`);
  gradient.addColorStop(1, `rgba(${rgbColor}, 0)`);

  ctx.fillStyle = gradient;
  ctx.fillRect(0, 0, 64, 64);

  const texture = new THREE.CanvasTexture(canvas);
  texture.wrapS = THREE.ClampToEdgeWrapping;
  texture.wrapT = THREE.ClampToEdgeWrapping;
  return texture;
};

export const SpatialHeatmap = ({ sensors = [], zones = [] }) => {
  const pulseGroupRef = useRef();

  // Color mapping strictly adhering to POLARIS mission light aesthetic
  const statusColors = useMemo(() => ({
    NORMAL: { hex: '#3f6e4a', rgb: '63, 110, 74', opacity: 0.38, severity: 0 },
    WARNING: { hex: '#b26814', rgb: '178, 104, 20', opacity: 0.52, severity: 1 },
    CRITICAL: { hex: '#b5382b', rgb: '181, 56, 43', opacity: 0.68, severity: 2 },
    OFFLINE: { hex: '#5d6672', rgb: '93, 102, 114', opacity: 0.22, severity: 0 },
    UNKNOWN: { hex: '#727b87', rgb: '114, 123, 135', opacity: 0.22, severity: 0 }
  }), []);

  // Pre-generate cached canvas textures for each status state
  const textures = useMemo(() => ({
    NORMAL: createRadialTexture(statusColors.NORMAL.rgb, statusColors.NORMAL.opacity),
    WARNING: createRadialTexture(statusColors.WARNING.rgb, statusColors.WARNING.opacity),
    CRITICAL: createRadialTexture(statusColors.CRITICAL.rgb, statusColors.CRITICAL.opacity),
    OFFLINE: createRadialTexture(statusColors.OFFLINE.rgb, statusColors.OFFLINE.opacity),
    UNKNOWN: createRadialTexture(statusColors.UNKNOWN.rgb, statusColors.UNKNOWN.opacity)
  }), [statusColors]);

  // Gentle rhythmic pulse animation for high severity / critical areas
  useFrame(({ clock }) => {
    if (pulseGroupRef.current) {
      const t = clock.getElapsedTime();
      const scale = 1 + Math.sin(t * 3.5) * 0.08;
      pulseGroupRef.current.scale.set(scale, 1, scale);
    }
  });

  // Calculate aggregated severity per station zone
  // Severity hierarchy: CRITICAL (2) > WARNING (1) > NORMAL (0) / OFFLINE (0)
  const zoneHealth = useMemo(() => {
    const healthMap = {};
    zones.forEach((z) => {
      const code = z.code || z.id;
      // Filter sensors belonging to this zone
      const zoneSensors = sensors.filter((s) => s.zone === code);
      let maxSev = -1;
      let dominantStatus = 'NORMAL';

      zoneSensors.forEach((s) => {
        const stat = s.status?.toUpperCase() || 'NORMAL';
        const sev = statusColors[stat]?.severity || 0;
        if (sev > maxSev) {
          maxSev = sev;
          dominantStatus = stat;
        }
      });

      if (zoneSensors.length > 0 && maxSev >= 0) {
        healthMap[code] = dominantStatus;
      } else {
        healthMap[code] = z.status === 'WARNING' ? 'WARNING' : 'NORMAL';
      }
    });
    return healthMap;
  }, [sensors, zones, statusColors]);

  return (
    <group name="spatial-heatmap-root">
      {/* ------------------------------------------------------------- */}
      {/* 1. ZONE-LEVEL ARCHITECTURAL HEALTH HIGHLIGHTS                 */}
      {/* ------------------------------------------------------------- */}
      {zones.map((zone) => {
        const code = zone.code || zone.id;
        const dominantStatus = zoneHealth[code] || 'NORMAL';
        const statusCfg = statusColors[dominantStatus] || statusColors.NORMAL;
        const [zx, zy, zz] = zone.position;
        const [sx, sy, sz] = zone.size;

        const isCriticalZone = dominantStatus === 'CRITICAL';
        const isWarningZone = dominantStatus === 'WARNING';
        const roofElevation = zy + sy / 2 + 0.12;

        return (
          <group key={`zone-heat-${zone.id}`}>
            {/* Soft semi-translucent architectural roof wash */}
            <mesh
              position={[zx, roofElevation, zz]}
              rotation={[-Math.PI / 2, 0, 0]}
              raycast={() => null} // Passes clicks directly through to sensors & models
            >
              <planeGeometry args={[sx * 0.94, sz * 0.92]} />
              <meshBasicMaterial
                color={statusCfg.hex}
                transparent
                opacity={isCriticalZone ? 0.38 : isWarningZone ? 0.26 : 0.12}
                depthWrite={false}
                side={THREE.DoubleSide}
              />
            </mesh>

            {/* Perimeter Zone Contour Warning Ring for abnormal states */}
            {(isCriticalZone || isWarningZone) && (
              <mesh
                position={[zx, roofElevation + 0.02, zz]}
                rotation={[-Math.PI / 2, 0, 0]}
                raycast={() => null}
              >
                <ringGeometry args={[Math.min(sx, sz) * 0.45, Math.min(sx, sz) * 0.50, 32]} />
                <meshBasicMaterial
                  color={statusCfg.hex}
                  transparent
                  opacity={0.65}
                  depthWrite={false}
                  side={THREE.DoubleSide}
                />
              </mesh>
            )}
          </group>
        );
      })}

      {/* ------------------------------------------------------------- */}
      {/* 2. SENSOR-LEVEL RADIAL SPATIAL INFLUENCE DISKS                */}
      {/* ------------------------------------------------------------- */}
      {sensors.map((sensor) => {
        const status = sensor.status?.toUpperCase() || 'NORMAL';
        const texture = textures[status] || textures.NORMAL;
        const statusCfg = statusColors[status] || statusColors.NORMAL;
        const isCritical = status === 'CRITICAL';
        const isWarning = status === 'WARNING';

        const rawX = sensor.x || 0;
        const rawZ = sensor.z || 0;
        const surfaceY = getSurfaceElevation(rawX, rawZ);

        // Radial influence diameter sized appropriately for station scale
        const diskRadius = isCritical ? 9.0 : isWarning ? 7.5 : 6.0;

        return (
          <group key={`heat-sensor-${sensor.id}`}>
            {/* Smooth Gaussian Falloff Disk */}
            <mesh
              position={[rawX, surfaceY + 0.06, rawZ]}
              rotation={[-Math.PI / 2, 0, 0]}
              raycast={() => null} // Crucial: Never blocks pointer events or sensor clicks
            >
              <planeGeometry args={[diskRadius * 2, diskRadius * 2]} />
              <meshBasicMaterial
                map={texture}
                transparent
                opacity={statusCfg.opacity}
                depthWrite={false}
                side={THREE.DoubleSide}
              />
            </mesh>

            {/* High-severity concentric radiation boundary ring */}
            {isCritical && (
              <group ref={pulseGroupRef}>
                <mesh
                  position={[rawX, surfaceY + 0.08, rawZ]}
                  rotation={[-Math.PI / 2, 0, 0]}
                  raycast={() => null}
                >
                  <ringGeometry args={[diskRadius * 0.65, diskRadius * 0.72, 32]} />
                  <meshBasicMaterial
                    color={statusCfg.hex}
                    transparent
                    opacity={0.55}
                    depthWrite={false}
                    side={THREE.DoubleSide}
                  />
                </mesh>
              </group>
            )}
          </group>
        );
      })}
    </group>
  );
};

export default SpatialHeatmap;
