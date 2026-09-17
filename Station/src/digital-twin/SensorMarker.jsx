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
export const SensorMarker = ({ sensor, isSelected, onSelect, zones = [] }) => {
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

  return (
    <group position={[dispX, dispY, dispZ]}>
      {/* ─────────────────────────────────────────────────────────────── */}
      {/* 1. VERTICAL INDICATOR STEM (connects marker → approximate real  */}
      {/*    mounting point below)                                        */}
      {/* ─────────────────────────────────────────────────────────────── */}
      {isElevated && (
        <>
          <mesh position={[0, -stemHeight / 2 - 0.2, 0]}>
            <cylinderGeometry args={[0.04, 0.04, stemHeight, 8]} />
            <meshBasicMaterial color="#2d333b" />
          </mesh>

          {/* Surface Mounting Foot Collar */}
          <mesh position={[0, -stemHeight - 0.2, 0]} rotation={[-Math.PI / 2, 0, 0]}>
            <ringGeometry args={[0.14, 0.30, 16]} />
            <meshBasicMaterial color="#383f4a" side={2} />
          </mesh>
        </>
      )}

      {/* ─────────────────────────────────────────────────────────────── */}
      {/* 2. CIRCULAR INSTRUMENTATION STATUS RING                        */}
      {/* ─────────────────────────────────────────────────────────────── */}
      <mesh ref={ringRef} rotation={[-Math.PI / 2, 0, 0]}>
        <ringGeometry args={[0.52, 0.68, 28]} />
        <meshBasicMaterial color={color} side={2} transparent opacity={0.88} />
      </mesh>

      {/* Outer Selected Ring */}
      {isSelected && (
        <mesh rotation={[-Math.PI / 2, 0, 0]}>
          <ringGeometry args={[0.82, 0.98, 32]} />
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
        <sphereGeometry args={[isSelected ? 0.55 : hovered ? 0.48 : 0.38, 16, 16]} />
        <meshStandardMaterial
          color={color}
          emissive={color}
          emissiveIntensity={isSelected ? 0.95 : hovered ? 0.80 : 0.50}
          roughness={0.25}
          metalness={0.3}
        />
      </mesh>

      {/* ─────────────────────────────────────────────────────────────── */}
      {/* 4. SENSOR IDENTIFIER TAG (hover / selected / critical)         */}
      {/* ─────────────────────────────────────────────────────────────── */}
      {(hovered || isSelected || isCritical) && (
        <Html
          position={[0, 0.95, 0]}
          center
          distanceFactor={45}
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
              background: '#ffffff',
              border: `1.5px solid ${isSelected ? '#b65a1f' : color}`,
              borderRadius: '3px',
              padding: isSelected ? '4px 9px' : '3px 8px',
              boxShadow: isSelected
                ? '0 6px 18px rgba(182, 90, 31, 0.35)'
                : '0 4px 12px rgba(0,0,0,0.18)',
              fontFamily: 'JetBrains Mono, monospace',
              fontSize: '11px',
              whiteSpace: 'nowrap',
              pointerEvents: 'auto',
              cursor: 'pointer',
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
              lineHeight: 1.25,
              transform: isSelected ? 'scale(1.08)' : 'scale(1)',
              transition: 'transform 0.15s ease'
            }}
          >
            <div
              style={{
                fontWeight: isSelected ? 800 : 700,
                color: '#191c20',
                display: 'flex',
                alignItems: 'center',
                gap: '5px',
                letterSpacing: '0.04em'
              }}
            >
              <span
                style={{
                  width: isSelected ? '7px' : '6px',
                  height: isSelected ? '7px' : '6px',
                  borderRadius: '50%',
                  background: color
                }}
              />
              <span>{sensor.id}</span>
            </div>
            <div style={{ fontSize: '10px', color: '#4b525d', fontWeight: 600 }}>
              {sensor.value} {sensor.unit}
            </div>
          </div>
        </Html>
      )}
    </group>
  );
};

export default SensorMarker;
