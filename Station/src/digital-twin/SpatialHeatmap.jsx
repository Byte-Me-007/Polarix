import React, { useMemo, useRef } from 'react';
import * as THREE from 'three';
import { useFrame } from '@react-three/fiber';

// Generates a procedural Gaussian radial gradient canvas texture
const createRadialTexture = (rgbColor, centerOpacity = 0.75) => {
  const canvas = document.createElement('canvas');
  canvas.width = 128;
  canvas.height = 128;
  const ctx = canvas.getContext('2d');

  const gradient = ctx.createRadialGradient(64, 64, 0, 64, 64, 64);
  gradient.addColorStop(0,    `rgba(${rgbColor}, ${centerOpacity})`);
  gradient.addColorStop(0.35, `rgba(${rgbColor}, ${centerOpacity * 0.70})`);
  gradient.addColorStop(0.65, `rgba(${rgbColor}, ${centerOpacity * 0.35})`);
  gradient.addColorStop(0.85, `rgba(${rgbColor}, ${centerOpacity * 0.10})`);
  gradient.addColorStop(1,    `rgba(${rgbColor}, 0)`);

  ctx.fillStyle = gradient;
  ctx.fillRect(0, 0, 128, 128);

  const texture = new THREE.CanvasTexture(canvas);
  texture.wrapS = THREE.ClampToEdgeWrapping;
  texture.wrapT = THREE.ClampToEdgeWrapping;
  return texture;
};

export const SpatialHeatmap = ({ sensors = [], zones = [] }) => {
  const pulseGroupRef = useRef();

  const statusColors = useMemo(() => ({
    NORMAL:  { hex: '#3f6e4a', rgb: '63, 110, 74',   centerOpacity: 0.55, severity: 0 },
    WARNING: { hex: '#b26814', rgb: '178, 104, 20',  centerOpacity: 0.75, severity: 1 },
    CRITICAL:{ hex: '#b5382b', rgb: '181, 56, 43',   centerOpacity: 0.85, severity: 2 },
    OFFLINE: { hex: '#5d6672', rgb: '93, 102, 114',  centerOpacity: 0.30, severity: 0 },
    UNKNOWN: { hex: '#727b87', rgb: '114, 123, 135', centerOpacity: 0.30, severity: 0 },
  }), []);

  const textures = useMemo(() => ({
    NORMAL:   createRadialTexture(statusColors.NORMAL.rgb,   statusColors.NORMAL.centerOpacity),
    WARNING:  createRadialTexture(statusColors.WARNING.rgb,  statusColors.WARNING.centerOpacity),
    CRITICAL: createRadialTexture(statusColors.CRITICAL.rgb, statusColors.CRITICAL.centerOpacity),
    OFFLINE:  createRadialTexture(statusColors.OFFLINE.rgb,  statusColors.OFFLINE.centerOpacity),
    UNKNOWN:  createRadialTexture(statusColors.UNKNOWN.rgb,  statusColors.UNKNOWN.centerOpacity),
  }), [statusColors]);

  useFrame(({ clock }) => {
    if (pulseGroupRef.current) {
      const t = clock.getElapsedTime();
      const scale = 1 + Math.sin(t * 3.2) * 0.12;
      pulseGroupRef.current.scale.set(scale, 1, scale);
    }
  });

  const zoneHealth = useMemo(() => {
    const healthMap = {};
    zones.forEach((z) => {
      const code = z.code || z.id;
      const zoneSensors = sensors.filter((s) => s.zone === code);
      let maxSev = -1;
      let dominantStatus = 'NORMAL';
      zoneSensors.forEach((s) => {
        const stat = (s.status || 'NORMAL').toUpperCase();
        const sev = statusColors[stat]?.severity ?? 0;
        if (sev > maxSev) { maxSev = sev; dominantStatus = stat; }
      });
      healthMap[code] = zoneSensors.length > 0 ? dominantStatus : 'NORMAL';
    });
    return healthMap;
  }, [sensors, zones, statusColors]);

  const GROUND_Y = 0.08;

  return (
    <group name="spatial-heatmap-root">
      {zones.map((zone) => {
        const code = zone.code || zone.id;
        const dominantStatus = zoneHealth[code] || 'NORMAL';
        const statusCfg = statusColors[dominantStatus] || statusColors.NORMAL;
        const texture = textures[dominantStatus] || textures.NORMAL;
        const [zx, , zz] = zone.position;
        const [sx, , sz] = zone.size;
        const isCritical = dominantStatus === 'CRITICAL';
        const isWarning  = dominantStatus === 'WARNING';
        const washW = sx * 1.35;
        const washD = sz * 1.35;

        return (
          <group key={`zone-heat-${zone.id}`}>
            <mesh position={[zx, GROUND_Y, zz]} rotation={[-Math.PI / 2, 0, 0]} raycast={() => null}>
              <planeGeometry args={[washW, washD]} />
              <meshBasicMaterial map={texture} transparent opacity={isCritical ? 0.90 : isWarning ? 0.80 : 0.65} depthWrite={false} side={THREE.DoubleSide} />
            </mesh>
            {(isCritical || isWarning) && (
              <mesh position={[zx, GROUND_Y + 0.02, zz]} rotation={[-Math.PI / 2, 0, 0]} raycast={() => null}>
                <ringGeometry args={[Math.min(washW, washD) * 0.44, Math.min(washW, washD) * 0.50, 40]} />
                <meshBasicMaterial color={statusCfg.hex} transparent opacity={isCritical ? 0.80 : 0.65} depthWrite={false} side={THREE.DoubleSide} />
              </mesh>
            )}
          </group>
        );
      })}

      {sensors.map((sensor) => {
        const status = (sensor.status || 'NORMAL').toUpperCase();
        const texture = textures[status] || textures.NORMAL;
        const statusCfg = statusColors[status] || statusColors.NORMAL;
        const isCritical = status === 'CRITICAL';
        const isWarning  = status === 'WARNING';
        const rawX = sensor.x || 0;
        const rawZ = sensor.z || 0;
        const diskR = isCritical ? 10 : isWarning ? 8 : 6;

        return (
          <group key={`heat-sensor-${sensor.id}`}>
            <mesh position={[rawX, GROUND_Y + 0.04, rawZ]} rotation={[-Math.PI / 2, 0, 0]} raycast={() => null}>
              <planeGeometry args={[diskR * 2, diskR * 2]} />
              <meshBasicMaterial map={texture} transparent opacity={isCritical ? 0.95 : isWarning ? 0.85 : 0.70} depthWrite={false} side={THREE.DoubleSide} />
            </mesh>
            {isCritical && (
              <group ref={pulseGroupRef}>
                <mesh position={[rawX, GROUND_Y + 0.06, rawZ]} rotation={[-Math.PI / 2, 0, 0]} raycast={() => null}>
                  <ringGeometry args={[diskR * 0.60, diskR * 0.70, 36]} />
                  <meshBasicMaterial color={statusCfg.hex} transparent opacity={0.80} depthWrite={false} side={THREE.DoubleSide} />
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
