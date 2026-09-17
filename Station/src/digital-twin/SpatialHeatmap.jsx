import React, { useMemo } from 'react';
import * as THREE from 'three';

// Soft radial texture for localized sensor hotspot
const createSpotTexture = (rgbColor) => {
  const size = 128;
  const canvas = document.createElement('canvas');
  canvas.width  = size;
  canvas.height = size;
  const ctx = canvas.getContext('2d');
  const cx = size / 2;

  const gradient = ctx.createRadialGradient(cx, cx, 0, cx, cx, cx * 0.92);
  gradient.addColorStop(0,    `rgba(${rgbColor}, 0.90)`);
  gradient.addColorStop(0.35, `rgba(${rgbColor}, 0.60)`);
  gradient.addColorStop(0.70, `rgba(${rgbColor}, 0.20)`);
  gradient.addColorStop(1.00, `rgba(${rgbColor}, 0)`);

  ctx.fillStyle = gradient;
  ctx.fillRect(0, 0, size, size);

  const texture = new THREE.CanvasTexture(canvas);
  return texture;
};

export const SpatialHeatmap = ({ sensors = [], zones = [] }) => {
  const textures = useMemo(() => ({
    CRITICAL: createSpotTexture('224, 49, 49'),
    WARNING:  createSpotTexture('245, 159, 0'),
  }), []);

  // Only render localized alarm highlights for CRITICAL and WARNING sensors
  const alarmSensors = useMemo(() => {
    return sensors.filter((s) => {
      const st = (s.status || '').toUpperCase();
      return st === 'CRITICAL' || st === 'WARNING';
    });
  }, [sensors]);

  return (
    <group name="spatial-sensor-alarm-spots">
      {alarmSensors.map((sensor) => {
        const isCritical = (sensor.status || '').toUpperCase() === 'CRITICAL';
        const texture = isCritical ? textures.CRITICAL : textures.WARNING;
        const colorHex = isCritical ? '#ff4d4f' : '#faad14';

        const rawX = sensor.x ?? 0;
        const rawZ = sensor.z ?? 0;

        // Find zone origin to determine floor height
        const zone = zones.find((z) => (z.code || z.id) === sensor.zone);
        const floorY = zone ? zone.position[1] + 0.25 : 0.25;
        const spotRadius = isCritical ? 5.5 : 4.5;

        return (
          <group key={`alarm-spot-${sensor.id}`}>
            {/* Soft localized sensor condition radial pool on interior floor */}
            <mesh
              position={[rawX, floorY, rawZ]}
              rotation={[-Math.PI / 2, 0, 0]}
              renderOrder={7}
              raycast={() => null}
            >
              <planeGeometry args={[spotRadius * 2, spotRadius * 2]} />
              <meshBasicMaterial
                map={texture}
                transparent
                opacity={isCritical ? 0.85 : 0.70}
                depthWrite={false}
                side={THREE.DoubleSide}
              />
            </mesh>

            {/* Subtle inner focus ring */}
            <mesh
              position={[rawX, floorY + 0.02, rawZ]}
              rotation={[-Math.PI / 2, 0, 0]}
              renderOrder={7}
              raycast={() => null}
            >
              <ringGeometry args={[spotRadius * 0.35, spotRadius * 0.45, 32]} />
              <meshBasicMaterial
                color={colorHex}
                transparent
                opacity={0.65}
                depthWrite={false}
                side={THREE.DoubleSide}
              />
            </mesh>
          </group>
        );
      })}
    </group>
  );
};

export default SpatialHeatmap;
