import React, { useMemo, useRef } from 'react';
import * as THREE from 'three';
import { useFrame } from '@react-three/fiber';

/**
 * High-resolution soft radial gradient texture with natural falloff.
 * Pure white with alpha attenuation; tinted dynamically via meshBasicMaterial.color
 * to enable zero-overhead 300-800ms smooth color & opacity interpolation.
 */
let cachedTexture = null;
const getRadialGradientTexture = () => {
  if (cachedTexture) return cachedTexture;

  const size = 256;
  const canvas = document.createElement('canvas');
  canvas.width = size;
  canvas.height = size;
  const ctx = canvas.getContext('2d');
  const cx = size / 2;

  const grad = ctx.createRadialGradient(cx, cx, 0, cx, cx, cx * 0.95);
  grad.addColorStop(0.00, 'rgba(255, 255, 255, 1.00)');
  grad.addColorStop(0.20, 'rgba(255, 255, 255, 0.82)');
  grad.addColorStop(0.48, 'rgba(255, 255, 255, 0.42)');
  grad.addColorStop(0.74, 'rgba(255, 255, 255, 0.14)');
  grad.addColorStop(0.92, 'rgba(255, 255, 255, 0.02)');
  grad.addColorStop(1.00, 'rgba(255, 255, 255, 0.00)');

  ctx.fillStyle = grad;
  ctx.fillRect(0, 0, size, size);

  cachedTexture = new THREE.CanvasTexture(canvas);
  cachedTexture.generateMipmaps = true;
  return cachedTexture;
};

// Restrained POLARIS color palette (NO neon, NO sci-fi glow)
const COLOR_CRITICAL = new THREE.Color('#c82a2a'); // Restrained red
const COLOR_WARNING  = new THREE.Color('#d9821a'); // Warm amber
const COLOR_NORMAL   = new THREE.Color('#3f6e4a'); // Subtle sage
const COLOR_NEUTRAL  = new THREE.Color('#727b87'); // Neutral gray
const COLOR_SELECTED = new THREE.Color('#b65a1f'); // Selected highlight amber

/**
 * Computes visual heatmap parameters according to the specification:
 * Telemetry -> Anomaly Score -> Anomaly Status -> Severity -> Opacity + Radius
 */
export const computeHeatmapParams = (sensor, isSelected = false, overlapAttenuation = 1.0) => {
  const rawStatus = (sensor.status || '').toUpperCase();
  const anomalyScore = typeof sensor.anomaly_score === 'number'
    ? sensor.anomaly_score
    : typeof sensor.anomalyScore === 'number'
      ? sensor.anomalyScore
      : null;

  // OFFLINE or UNKNOWN: no alarm heatmap
  if (rawStatus === 'OFFLINE' || rawStatus === 'UNKNOWN') {
    return {
      targetColor: COLOR_NEUTRAL,
      targetOpacity: 0.0,
      targetRadius: 1.0,
      hasAlarm: false,
      isCritical: false,
      isWarning: false
    };
  }

  let color = COLOR_NORMAL;
  let baseOpacity = 0.06;
  let baseRadius = 2.5;
  let hasAlarm = false;
  let isCritical = false;
  let isWarning = false;

  if (anomalyScore !== null) {
    // Anomaly score driving intensity and radius
    if (anomalyScore >= 0.75 || rawStatus === 'CRITICAL') {
      color = COLOR_CRITICAL;
      isCritical = true;
      hasAlarm = true;
      // 0.75 -> 0.42, 1.00 -> 0.58
      const t = Math.min(1, Math.max(0, (anomalyScore - 0.75) / 0.25));
      baseOpacity = 0.42 + t * 0.16;
      baseRadius = 7.5 + t * 2.0;
    } else if (anomalyScore >= 0.35 || rawStatus === 'WARNING') {
      color = COLOR_WARNING;
      isWarning = true;
      hasAlarm = true;
      // 0.35 -> 0.22, 0.75 -> 0.34
      const t = Math.min(1, Math.max(0, (anomalyScore - 0.35) / 0.40));
      baseOpacity = 0.22 + t * 0.12;
      baseRadius = 4.5 + t * 1.8;
    } else if (anomalyScore >= 0.10) {
      color = COLOR_NORMAL;
      baseOpacity = 0.06 + anomalyScore * 0.05;
      baseRadius = 2.4 + anomalyScore * 1.5;
    } else {
      color = COLOR_NORMAL;
      baseOpacity = 0.05;
      baseRadius = 2.0;
    }
  } else {
    // Data Fallback (Section 16): Use sensor status when anomaly_score is unavailable
    switch (rawStatus) {
      case 'CRITICAL':
        color = COLOR_CRITICAL;
        baseOpacity = 0.52;
        baseRadius = 8.0;
        hasAlarm = true;
        isCritical = true;
        break;
      case 'WARNING':
        color = COLOR_WARNING;
        baseOpacity = 0.28;
        baseRadius = 5.2;
        hasAlarm = true;
        isWarning = true;
        break;
      case 'NORMAL':
        color = COLOR_NORMAL;
        baseOpacity = 0.06;
        baseRadius = 2.5;
        break;
      default:
        color = COLOR_NEUTRAL;
        baseOpacity = 0.0;
        baseRadius = 1.0;
        break;
    }
  }

  // Intelligent multi-sensor zone overlap attenuation (Section 7)
  baseOpacity *= overlapAttenuation;

  // Selected sensor: intensify contribution (Section 10)
  if (isSelected) {
    baseOpacity = Math.min(0.85, baseOpacity * 1.30 + 0.12);
    baseRadius *= 1.15;
  }

  return {
    targetColor: color,
    targetOpacity: baseOpacity,
    targetRadius: baseRadius,
    hasAlarm,
    isCritical,
    isWarning
  };
};

/**
 * SensorHotspot: Renders individual localized condition pool with smooth Three.js transitions (300-800ms)
 */
const SensorHotspot = ({
  sensor,
  zone,
  isSelected = false,
  overlapAttenuation = 1.0,
  texture
}) => {
  const meshRef = useRef();
  const matRef = useRef();
  const ringRef = useRef();
  const ringMatRef = useRef();

  // Animated state refs for smooth Three.js interpolation
  const currentOpacity = useRef(0.0);
  const currentRadius = useRef(2.5);
  const currentColor = useRef(new THREE.Color('#3f6e4a'));
  const currentRingOpacity = useRef(0.0);

  const rawX = sensor.x ?? 0;
  const rawZ = sensor.z ?? 0;

  // Floor elevation: slightly above interior floor slab or ground
  const floorY = zone ? zone.position[1] + 0.18 : 0.12;

  const {
    targetColor,
    targetOpacity,
    targetRadius,
    hasAlarm
  } = useMemo(
    () => computeHeatmapParams(sensor, isSelected, overlapAttenuation),
    [sensor, isSelected, overlapAttenuation]
  );

  useFrame((_, delta) => {
    // 300–800ms smooth interpolation factor (approx 500ms exponential ease-out)
    const factor = Math.min(1.0, Math.max(0.01, delta * 5.5));

    currentOpacity.current += (targetOpacity - currentOpacity.current) * factor;
    currentRadius.current += (targetRadius - currentRadius.current) * factor;
    currentColor.current.lerp(targetColor, factor);

    if (matRef.current) {
      matRef.current.opacity = currentOpacity.current;
      matRef.current.color.copy(currentColor.current);
    }

    if (meshRef.current) {
      const r = Math.max(0.01, currentRadius.current);
      meshRef.current.scale.set(r, r, 1);
      meshRef.current.visible = currentOpacity.current > 0.005;
    }

    if (ringMatRef.current && ringRef.current) {
      const targetRingOpacity = isSelected ? 0.85 : hasAlarm ? 0.38 : 0.0;
      currentRingOpacity.current += (targetRingOpacity - currentRingOpacity.current) * factor;
      ringMatRef.current.opacity = currentRingOpacity.current;
      ringRef.current.visible = currentRingOpacity.current > 0.01;
      ringMatRef.current.color.copy(isSelected ? COLOR_SELECTED : currentColor.current);
    }
  });

  return (
    <group position={[rawX, floorY, rawZ]}>
      {/* 1. Localized spatial radial gradient condition wash on interior floor */}
      <mesh
        ref={meshRef}
        rotation={[-Math.PI / 2, 0, 0]}
        renderOrder={8}
        raycast={() => null}
      >
        <planeGeometry args={[2, 2]} />
        <meshBasicMaterial
          ref={matRef}
          map={texture}
          transparent
          opacity={0}
          depthWrite={false}
          side={THREE.DoubleSide}
        />
      </mesh>

      {/* 2. Concentric spatial focus ring around the sensor center */}
      <mesh
        ref={ringRef}
        position={[0, 0.02, 0]}
        rotation={[-Math.PI / 2, 0, 0]}
        renderOrder={9}
        raycast={() => null}
      >
        <ringGeometry args={[isSelected ? 0.65 : 0.42, isSelected ? 0.85 : 0.54, 32]} />
        <meshBasicMaterial
          ref={ringMatRef}
          transparent
          opacity={0}
          depthWrite={false}
          side={THREE.DoubleSide}
        />
      </mesh>
    </group>
  );
};

/**
 * SpatialHeatmap: Main container handling multi-sensor zone aggregation and live updates
 */
export const SpatialHeatmap = ({ sensors = [], zones = [], selectedSensor = null }) => {
  const texture = useMemo(() => getRadialGradientTexture(), []);

  // Multi-sensor zone aggregation to avoid ugly overlapping stacked blobs (Section 7)
  const sensorAttenuations = useMemo(() => {
    const map = {};
    const byZone = {};

    sensors.forEach((s) => {
      const z = s.zone || 'UNKNOWN';
      if (!byZone[z]) byZone[z] = [];
      byZone[z].push(s);
    });

    Object.entries(byZone).forEach(([_, zoneSensors]) => {
      zoneSensors.forEach((s) => {
        const st = (s.status || '').toUpperCase();
        const score = typeof s.anomaly_score === 'number' ? s.anomaly_score : (s.anomalyScore || 0);
        let mySev = 0;
        if (st === 'CRITICAL' || score >= 0.75) mySev = 3;
        else if (st === 'WARNING' || score >= 0.35) mySev = 2;
        else if (st === 'NORMAL') mySev = 1;

        let closeAlarms = 0;
        let hasHigherSevNeighbor = false;

        zoneSensors.forEach((other) => {
          if (other.id !== s.id) {
            const dx = (s.x ?? 0) - (other.x ?? 0);
            const dz = (s.z ?? 0) - (other.z ?? 0);
            const dist = Math.sqrt(dx * dx + dz * dz);
            if (dist < 8.0) {
              const otherSt = (other.status || '').toUpperCase();
              const otherScore = typeof other.anomaly_score === 'number' ? other.anomaly_score : (other.anomalyScore || 0);
              let otherSev = 0;
              if (otherSt === 'CRITICAL' || otherScore >= 0.75) otherSev = 3;
              else if (otherSt === 'WARNING' || otherScore >= 0.35) otherSev = 2;
              else if (otherSt === 'NORMAL') otherSev = 1;

              if (otherSev >= 2) closeAlarms++;
              if (otherSev > mySev) hasHigherSevNeighbor = true;
            }
          }
        });

        if (hasHigherSevNeighbor) {
          map[s.id] = 0.55; // Secondary sensor dampened in presence of higher severity neighbor
        } else if (closeAlarms > 0) {
          map[s.id] = 0.80; // Prevent additive saturation blowout
        } else {
          map[s.id] = 1.0;
        }
      });
    });

    return map;
  }, [sensors]);

  return (
    <group name="spatial-data-driven-heatmap">
      {sensors.map((sensor) => {
        const zone = zones.find((z) => (z.code || z.id) === sensor.zone);
        const isSelected = Boolean(selectedSensor && selectedSensor.id === sensor.id);
        const attenuation = sensorAttenuations[sensor.id] ?? 1.0;

        return (
          <SensorHotspot
            key={`heat-${sensor.id}`}
            sensor={sensor}
            zone={zone}
            isSelected={isSelected}
            overlapAttenuation={attenuation}
            texture={texture}
          />
        );
      })}
    </group>
  );
};

export default SpatialHeatmap;

