import React, { useMemo, useEffect, useRef } from 'react';
import * as THREE from 'three';
import { useFrame } from '@react-three/fiber';

/**
 * SpatialHeatmap — Continuous Scientific Telemetry Intensity Field
 *
 * Implements a physically continuous, smoothly interpolated heat field
 * driven directly by actual sensor telemetry, respecting physical 3D coordinates,
 * configured min/max thresholds, and domain-specific metric filters.
 *
 * Color Scale (Restrained Scientific Scale):
 *   0.00 - 0.33: Cool / muted blue (rgb: 43, 92, 143)
 *   0.33 - 0.66: Cyan / neutral transition (rgb: 56, 142, 142)
 *   0.66 - 0.85: Warm amber (rgb: 217, 130, 26)
 *   0.85 - 1.00: Restrained deep red (rgb: 200, 42, 42)
 */

// Restrained color ramp interpolation
export const getScientificColorRGB = (t) => {
  t = Math.max(0, Math.min(1, t));
  if (t < 0.33) {
    const f = t / 0.33;
    const r = Math.round(43 + (56 - 43) * f);
    const g = Math.round(92 + (142 - 92) * f);
    const b = Math.round(143 + (142 - 143) * f);
    return [r, g, b];
  } else if (t < 0.66) {
    const f = (t - 0.33) / 0.33;
    const r = Math.round(56 + (217 - 56) * f);
    const g = Math.round(142 + (130 - 142) * f);
    const b = Math.round(142 + (26 - 142) * f);
    return [r, g, b];
  } else {
    const f = (t - 0.66) / 0.34;
    const r = Math.round(217 + (200 - 217) * f);
    const g = Math.round(130 + (42 - 130) * f);
    const b = Math.round(26 + (42 - 26) * f);
    return [r, g, b];
  }
};

/**
 * Normalizes sensor value strictly using configured minValue / maxValue
 */
export const normalizeSensorValue = (sensor) => {
  if (!sensor) return null;
  const status = (sensor.status || '').toUpperCase();
  if (status === 'OFFLINE' || status === 'UNKNOWN') return null;

  const rawVal = sensor.value ?? sensor.current_value;
  if (rawVal === null || rawVal === undefined || rawVal === '') return null;
  const val = Number(rawVal);
  if (isNaN(val)) return null;

  const min = sensor.minimum_value ?? sensor.minValue;
  const max = sensor.maximum_value ?? sensor.maxValue;

  if (typeof min === 'number' && typeof max === 'number' && max > min) {
    const clamped = Math.max(min, Math.min(max, val));
    let norm = (clamped - min) / (max - min);

    // Reflect severe operational alert condition if flagged
    if (status === 'CRITICAL') {
      norm = Math.max(norm, 0.88);
    } else if (status === 'WARNING') {
      norm = Math.max(norm, 0.60);
    }
    return norm;
  }

  // Fallback if min/max not present: check anomaly score
  const anomaly = sensor.anomaly_score ?? sensor.anomalyScore;
  if (typeof anomaly === 'number' && !isNaN(anomaly)) {
    return Math.max(0, Math.min(1, anomaly));
  }

  if (status === 'CRITICAL') return 0.95;
  if (status === 'WARNING') return 0.65;
  return 0.25;
};

/**
 * Validates whether a sensor matches the selected domain / metric filter
 */
export const isSensorMatchingMetric = (sensor, metric) => {
  if (!metric || metric === 'ALL') return true;

  const domain = (sensor.domain || '').toUpperCase();
  const type = (sensor.type || '').toUpperCase();
  const name = (sensor.name || '').toUpperCase();
  const unit = (sensor.unit || '').toUpperCase();

  switch (metric) {
    case 'TEMPERATURE':
      return (
        type === 'TEMPERATURE' ||
        unit.includes('°C') ||
        unit.includes('K') ||
        name.includes('TEMP') ||
        name.includes('RTD') ||
        name.includes('THERM')
      );
    case 'WIND':
      return (
        type === 'WIND_SPEED' ||
        type === 'WIND' ||
        unit.includes('KM/H') ||
        unit.includes('M/S') ||
        name.includes('ANEMOMETER') ||
        name.includes('WIND')
      );
    case 'POWER':
      return (
        domain === 'ENERGY' ||
        type === 'POWER' ||
        type === 'IRRADIANCE' ||
        type === 'VOLTAGE' ||
        type === 'CURRENT' ||
        type === 'VIBRATION' ||
        unit.includes('KW') ||
        unit.includes('W/M²') ||
        unit.includes('V') ||
        unit.includes('A') ||
        name.includes('GENERATOR') ||
        name.includes('SOLAR') ||
        name.includes('BATTERY')
      );
    case 'STRUCTURAL':
      return (
        domain === 'STRUCTURE' ||
        type === 'STRAIN' ||
        type === 'DISPLACEMENT' ||
        type === 'LOAD' ||
        type === 'TILT' ||
        unit.includes('ME') ||
        unit.includes('MM') ||
        unit.includes('KN') ||
        name.includes('STRAIN') ||
        name.includes('DISPLACEMENT') ||
        name.includes('STILT')
      );
    case 'FUEL':
      return (
        domain === 'LOGISTICS' ||
        type === 'LEVEL' ||
        type === 'FLOW' ||
        name.includes('FUEL') ||
        name.includes('TANK') ||
        name.includes('RESERVE') ||
        unit.includes('L') ||
        unit.includes('L/MIN')
      );
    default:
      return true;
  }
};

// Station world space bounds for complete ground coverage
const BOUNDS = {
  minX: -80,
  maxX: 80,
  minZ: -80,
  maxZ: 50,
  width: 160,
  depth: 130,
  centerZ: -15
};

/**
 * SensorDatumRing: Renders a clean localized spatial focus ring at the sensor coordinates
 */
const SensorDatumRing = ({ sensor, norm, isSelected }) => {
  const [r, g, b] = getScientificColorRGB(norm);
  const colorStr = `rgb(${r}, ${g}, ${b})`;
  const pulseRef = useRef();

  useFrame(({ clock }) => {
    if (pulseRef.current && (isSelected || norm >= 0.75)) {
      const s = 1 + Math.sin(clock.getElapsedTime() * 3.5) * 0.15;
      pulseRef.current.scale.set(s, s, 1);
    }
  });

  const rawX = sensor.location_x ?? sensor.x ?? 0;
  const rawZ = sensor.location_z ?? sensor.z ?? 0;
  const rawY = Math.max(sensor.location_y ?? sensor.y ?? 0.2, 0.22);

  return (
    <group position={[rawX, rawY, rawZ]}>
      {/* Base datum anchor circle */}
      <mesh rotation={[-Math.PI / 2, 0, 0]} renderOrder={10}>
        <ringGeometry args={[0.32, 0.58, 32]} />
        <meshBasicMaterial
          color={colorStr}
          transparent
          opacity={0.78}
          depthWrite={false}
          side={THREE.DoubleSide}
        />
      </mesh>

      {/* Outer focus halo ring */}
      <mesh ref={pulseRef} rotation={[-Math.PI / 2, 0, 0]} renderOrder={11}>
        <ringGeometry args={[isSelected ? 0.85 : 0.68, isSelected ? 1.15 : 0.86, 32]} />
        <meshBasicMaterial
          color={isSelected ? '#b65a1f' : colorStr}
          transparent
          opacity={isSelected ? 0.90 : 0.40}
          depthWrite={false}
          side={THREE.DoubleSide}
        />
      </mesh>
    </group>
  );
};

export const SpatialHeatmap = ({
  sensors = [],
  zones = [],
  selectedSensor = null,
  heatmapMetric = 'TEMPERATURE',
  activeStation = 'MAITRI'
}) => {
  const canvasRef = useRef(document.createElement('canvas'));
  const textureRef = useRef(null);
  const materialRef = useRef(null);

  // 1. Filter sensors by the selected metric & exclude offline/null sensors
  const activeSensors = useMemo(() => {
    if (!sensors || sensors.length === 0) return [];

    return sensors
      .filter((s) => isSensorMatchingMetric(s, heatmapMetric))
      .map((s) => ({
        sensor: s,
        norm: normalizeSensorValue(s)
      }))
      .filter(({ norm }) => norm !== null);
  }, [sensors, heatmapMetric]);

  // 2. Initialize Canvas Texture with linear filtering
  const texture = useMemo(() => {
    const canvas = canvasRef.current;
    canvas.width = 256;
    canvas.height = 256;
    const tex = new THREE.CanvasTexture(canvas);
    tex.generateMipmaps = true;
    tex.minFilter = THREE.LinearFilter;
    tex.magFilter = THREE.LinearFilter;
    textureRef.current = tex;
    return tex;
  }, []);

  // 3. Render continuous spatial interpolation field to canvas
  useEffect(() => {
    const canvas = canvasRef.current;
    const ctx = canvas.getContext('2d');
    const width = 256;
    const height = 256;

    if (canvas.width !== width || canvas.height !== height) {
      canvas.width = width;
      canvas.height = height;
    }

    if (activeSensors.length === 0) {
      ctx.clearRect(0, 0, width, height);
      if (textureRef.current) textureRef.current.needsUpdate = true;
      return;
    }

    const imgData = ctx.createImageData(width, height);
    const data = imgData.data;

    const sensorData = activeSensors.map(({ sensor, norm }) => ({
      x: sensor.location_x ?? sensor.x ?? 0,
      z: sensor.location_z ?? sensor.z ?? 0,
      v: norm
    }));

    const sigma = 18.0; // Spatial influence radius
    const twoSigmaSq = 2 * sigma * sigma;
    const maxInfluenceDist = 48.0; // Outer limit of field decay

    for (let py = 0; py < height; py++) {
      // With plane rotated [-PI/2, 0, 0] and flipY=true:
      // py = 0 -> world minZ; py = height - 1 -> world maxZ
      const worldZ = BOUNDS.minZ + (py / (height - 1)) * BOUNDS.depth;

      for (let px = 0; px < width; px++) {
        const worldX = BOUNDS.minX + (px / (width - 1)) * BOUNDS.width;

        let totalWeight = 0;
        let weightedSum = 0;
        let minDistSq = Infinity;

        for (let i = 0; i < sensorData.length; i++) {
          const s = sensorData[i];
          const dx = worldX - s.x;
          const dz = worldZ - s.z;
          const distSq = dx * dx + dz * dz;

          if (distSq < minDistSq) {
            minDistSq = distSq;
          }

          if (distSq < maxInfluenceDist * maxInfluenceDist) {
            const w = Math.exp(-distSq / twoSigmaSq);
            totalWeight += w;
            weightedSum += w * s.v;
          }
        }

        const idx = (py * width + px) * 4;

        if (totalWeight > 1e-4) {
          const t = weightedSum / totalWeight;
          const [r, g, b] = getScientificColorRGB(t);

          const minDist = Math.sqrt(minDistSq);
          let alpha = 0.84;
          if (minDist > 22) {
            const f = (minDist - 22) / (48 - 22);
            alpha = Math.max(0, 0.84 * (1 - f * f));
          }

          data[idx] = r;
          data[idx + 1] = g;
          data[idx + 2] = b;
          data[idx + 3] = Math.round(alpha * 255);
        } else {
          data[idx] = 0;
          data[idx + 1] = 0;
          data[idx + 2] = 0;
          data[idx + 3] = 0;
        }
      }
    }

    ctx.putImageData(imgData, 0, 0);

    if (textureRef.current) {
      textureRef.current.needsUpdate = true;
    }
  }, [activeSensors]);

  // Elevation: Maitri snow ground is at y = -0.05 (grid y=0.01), Bharati rock is at y = -0.08 (snow patches y=0.02)
  const planeY = activeStation === 'BHARATI' ? 0.12 : 0.08;

  return (
    <group name="spatial-continuous-heatmap">
      {/* Continuous scientific heat field overlaid on terrain and across facilities */}
      <mesh
        position={[0, planeY, BOUNDS.centerZ]}
        rotation={[-Math.PI / 2, 0, 0]}
        renderOrder={6}
        raycast={() => null}
      >
        <planeGeometry args={[BOUNDS.width, BOUNDS.depth]} />
        <meshBasicMaterial
          ref={materialRef}
          map={texture}
          transparent
          opacity={0.88}
          depthWrite={false}
          side={THREE.DoubleSide}
        />
      </mesh>

      {/* Discrete sensor measurement datum rings */}
      {activeSensors.map(({ sensor, norm }) => (
        <SensorDatumRing
          key={`ring-${sensor.id}`}
          sensor={sensor}
          norm={norm}
          isSelected={Boolean(selectedSensor && selectedSensor.id === sensor.id)}
        />
      ))}
    </group>
  );
};

export default SpatialHeatmap;
