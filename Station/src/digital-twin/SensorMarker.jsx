import React, { useState, useRef } from 'react';
import { useFrame } from '@react-three/fiber';
import { Html } from '@react-three/drei';

// ─────────────────────────────────────────────────────────────────────────────
// computeDisplayPos
// Returns the VISUAL position for the sensor marker.
// REAL sensor.x/y/z are untouched — they are backend data coordinates.
// Display position lifts the marker above the building roof so it is always
// visible and clickable from the camera perspective.
//
// Rule:
//   1. Find the zone this sensor belongs to.
//   2. World roof Y ≈ zone.position[1] + zone.size[1]  (py + sy)
//   3. If sensor.y ≤ roofY, raise displayY to roofY + ROOF_OFFSET
//   4. Otherwise keep sensor.y as-is.
//
// This guarantees every marker hovers ABOVE the building.
// ─────────────────────────────────────────────────────────────────────────────
const ROOF_OFFSET = 0.5; // units above roof surface

export const computeDisplayPos = (sensor, zones = []) => {
  const rawX = sensor.x ?? 0;
  const rawY = sensor.y ?? 0;
  const rawZ = sensor.z ?? 0;

  const zone = zones.find((z) => (z.code || z.id) === sensor.zone);
  if (!zone) {
    return { x: rawX, y: Math.max(rawY, 0.4), z: rawZ };
  }

  const [px, py, pz] = zone.position;
  const [sx, sy, sz] = zone.size;
  const roofY = py + sy; // approximate world-space roof elevation

  // Check if horizontally within zone footprint (with small tolerance margin)
  const insideFootprint =
    Math.abs(rawX - px) <= sx / 2 + 1.2 &&
    Math.abs(rawZ - pz) <= sz / 2 + 1.2;

  let displayY = rawY;
  if (insideFootprint) {
    // If inside building or on/below roof, elevate above roof
    if (rawY < roofY) {
      displayY = roofY + ROOF_OFFSET;
    } else {
      displayY = rawY + ROOF_OFFSET;
    }
  } else {
    // Outdoor sensor on permafrost / ground
    displayY = Math.max(rawY, 0.4);
  }

  return { x: rawX, y: displayY, z: rawZ };
};

// ─────────────────────────────────────────────────────────────────────────────
// Status color palette (POLARIS design system)
// ─────────────────────────────────────────────────────────────────────────────
const getStatusColor = (status) => {
  switch (status?.toUpperCase()) {
    case 'NORMAL':   return '#3f6e4a'; // Muted sage
    case 'WARNING':  return '#b26814'; // Restrained amber
    case 'CRITICAL': return '#b5382b'; // Restrained red
    case 'OFFLINE':  return '#5d6672'; // Neutral gray
    default:         return '#727b87';
  }
};

// ─────────────────────────────────────────────────────────────────────────────
// SensorMarker
// zones: array of zone objects from station.digitalTwin.zones
// sensor: sensor object from station.sensors
// ─────────────────────────────────────────────────────────────────────────────
export const SensorMarker = ({ sensor, isSelected, onSelect, zones = [], isHeatmap = false }) => {
  const [hovered, setHovered] = useState(false);
  const beaconRef  = useRef();
  const ringRef    = useRef();

  const color      = getStatusColor(sensor.status);
  const isCritical = sensor.status?.toUpperCase() === 'CRITICAL';

  // Subtle pulse animation for critical sensors / active selection
  useFrame(({ clock }) => {
    const t = clock.getElapsedTime();
    if (beaconRef.current && (isCritical || isSelected)) {
      const scale = 1 + Math.sin(t * 4.2) * (isCritical ? 0.22 : 0.15);
      beaconRef.current.scale.set(scale, scale, scale);
    }
    if (ringRef.current) {
      ringRef.current.rotation.z = t * 0.4;
    }
  });

  // ── Calculate display (visual) position ──────────────────────────────────
  const { x: dispX, y: dispY, z: dispZ } = computeDisplayPos(sensor, zones);

  // Stem connects display marker back toward the sensor's real data Y
  const rawY       = sensor.y ?? 0;
  const isElevated = dispY > rawY + 0.3;
  const stemHeight = Math.max(0.01, dispY - rawY - 0.2); // slight gap at sensor end

  const beaconRadius = isSelected
    ? 0.52
    : hovered
    ? 0.45
    : isHeatmap
    ? 0.26
    : 0.38;

  return (
    <group position={[dispX, dispY, dispZ]}>
      {/* ─────────────────────────────────────────────────────────────── */}
      {/* 1. VERTICAL INDICATOR STEM (connects marker → approximate real  */}
      {/*    mounting point below)                                        */}
      {/* ─────────────────────────────────────────────────────────────── */}
      {isElevated && (
        <>
          <mesh position={[0, -stemHeight / 2 - 0.2, 0]}>
            <cylinderGeometry args={[0.035, 0.035, stemHeight, 8]} />
            <meshBasicMaterial color="#2d333b" transparent opacity={isHeatmap ? 0.55 : 0.9} />
          </mesh>

          {/* Surface Mounting Foot Collar */}
          <mesh position={[0, -stemHeight - 0.2, 0]} rotation={[-Math.PI / 2, 0, 0]}>
            <ringGeometry args={[0.12, 0.26, 16]} />
            <meshBasicMaterial color="#383f4a" side={2} transparent opacity={isHeatmap ? 0.55 : 0.9} />
          </mesh>
        </>
      )}

      {/* ─────────────────────────────────────────────────────────────── */}
      {/* 2. CIRCULAR INSTRUMENTATION STATUS RING                        */}
      {/* ─────────────────────────────────────────────────────────────── */}
      <mesh ref={ringRef} rotation={[-Math.PI / 2, 0, 0]}>
        <ringGeometry args={[isHeatmap ? 0.38 : 0.52, isHeatmap ? 0.50 : 0.68, 28]} />
        <meshBasicMaterial color={color} side={2} transparent opacity={isHeatmap ? 0.65 : 0.88} />
      </mesh>

      {/* Outer Selected Ring */}
      {isSelected && (
        <mesh rotation={[-Math.PI / 2, 0, 0]}>
          <ringGeometry args={[0.72, 0.88, 32]} />
          <meshBasicMaterial color="#b65a1f" side={2} />
        </mesh>
      )}

      {/* ─────────────────────────────────────────────────────────────── */}
      {/* 3. ILLUMINATED BEACON POINT (clickable instrument head)        */}
      {/* ─────────────────────────────────────────────────────────────── */}
      <mesh
        ref={beaconRef}
        onClick={(e) => {
          e.stopPropagation();
          onSelect(sensor); // passes pristine source sensor data
        }}
        onPointerDown={(e) => {
          e.stopPropagation(); // prevent camera rotation on click
        }}
        onPointerOver={(e) => {
          e.stopPropagation();
          setHovered(true);
          document.body.style.cursor = 'pointer';
        }}
        onPointerOut={(e) => {
          e.stopPropagation();
          setHovered(false);
          document.body.style.cursor = 'default';
        }}
      >
        <sphereGeometry args={[beaconRadius, 16, 16]} />
        <meshStandardMaterial
          color={color}
          emissive={color}
          emissiveIntensity={isSelected ? 0.95 : hovered ? 0.80 : isHeatmap ? 0.35 : 0.50}
          roughness={0.25}
          metalness={0.3}
          transparent={isHeatmap && !hovered && !isSelected}
          opacity={isHeatmap && !hovered && !isSelected ? 0.82 : 1.0}
        />
      </mesh>

      {/* ─────────────────────────────────────────────────────────────── */}
      {/* 4. SENSOR IDENTIFIER TAG (hover / selected / critical)         */}
      {/* ─────────────────────────────────────────────────────────────── */}
      {(hovered || isSelected || isCritical) && (
        <Html
          position={[0, 1.15, 0]}
          center
          distanceFactor={42}
          zIndexRange={[300, 0]}
        >
          <div
            onClick={(e) => {
              e.stopPropagation();
              onSelect(sensor);
            }}
            onPointerDown={(e) => {
              e.stopPropagation();
            }}
            style={{
              background: 'rgba(255, 255, 255, 0.98)',
              border: `1.5px solid ${isSelected ? '#b65a1f' : color}`,
              borderRadius: '4px',
              padding: '6px 10px',
              boxShadow: isSelected
                ? '0 6px 20px rgba(182, 90, 31, 0.40)'
                : '0 4px 14px rgba(0, 0, 0, 0.22)',
              fontFamily: 'JetBrains Mono, monospace',
              fontSize: '10px',
              whiteSpace: 'nowrap',
              pointerEvents: 'auto',
              cursor: 'pointer',
              display: 'flex',
              flexDirection: 'column',
              gap: '2px',
              minWidth: '135px',
              textAlign: 'left',
              lineHeight: 1.3,
              transform: isSelected ? 'scale(1.05)' : 'scale(1)',
              transition: 'transform 0.15s ease'
            }}
          >
            {/* SENSOR NAME */}
            <div
              style={{
                fontSize: '9px',
                fontWeight: 600,
                color: '#64748b',
                overflow: 'hidden',
                textOverflow: 'ellipsis',
                maxWidth: '190px'
              }}
            >
              {sensor.name || 'SENSOR'}
            </div>

            {/* SENSOR ID */}
            <div
              style={{
                fontWeight: 800,
                color: '#191c20',
                display: 'flex',
                alignItems: 'center',
                gap: '5px',
                letterSpacing: '0.04em'
              }}
            >
              <span
                style={{
                  width: '6px',
                  height: '6px',
                  borderRadius: '50%',
                  background: color,
                  flexShrink: 0
                }}
              />
              <span>{sensor.id}</span>
            </div>

            {/* CURRENT VALUE & UNIT */}
            <div
              style={{
                fontSize: '12px',
                fontWeight: 800,
                color: '#0f172a',
                paddingTop: '2px',
                paddingBottom: '2px'
              }}
            >
              {sensor.value ?? 'N/A'} <span style={{ fontSize: '10px', color: '#64748b' }}>{sensor.unit}</span>
            </div>

            {/* STATUS & TIMESTAMP */}
            <div
              style={{
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
                borderTop: '1px solid #e2e8f0',
                paddingTop: '3px',
                marginTop: '1px',
                fontSize: '8.5px'
              }}
            >
              <span style={{ fontWeight: 800, color }}>
                ● {sensor.status || 'NORMAL'}
              </span>
              <span style={{ color: '#94a3b8' }}>
                {sensor.lastUpdate || 'Just now'}
              </span>
            </div>
          </div>
        </Html>
      )}
    </group>
  );
};

export default SensorMarker;
