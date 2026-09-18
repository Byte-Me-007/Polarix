/**
 * IncidentGraph.jsx
 *
 * 3D spatial Cause → Impact visualization rendered inside the React Three Fiber Canvas.
 *
 * Renders:
 *  1. Subtle copper/amber directional path tubes between incident node positions
 *  2. Animated small directional dashes traveling along each path (same pattern
 *     as SystemFlowOverlay ConduitSegment — no new heavy effects)
 *  3. Incident node status rings (thin ring geometry) around affected asset positions
 *  4. Invisible clickable meshes at each node for interaction
 *
 * Color language (Polaris visual system):
 *  - WARNING paths:  amber  #d97706
 *  - CRITICAL paths: copper #b65a1f / restrained red #b5382b
 *  - Node rings:     amber / copper (NOT neon)
 *
 * Performance: reuses QuadraticBezierCurve3 + TubeGeometry (same as SystemFlowOverlay).
 * No extra lights, no particles, no post-processing.
 */

import React, { useRef, useMemo } from 'react';
import * as THREE from 'three';
import { useFrame } from '@react-three/fiber';
import { Html } from '@react-three/drei';

// ─────────────────────────────────────────────────────────────────────────────
// Helpers
// ─────────────────────────────────────────────────────────────────────────────

const SEV_COLOR = {
  CRITICAL: '#b65a1f',
  WARNING:  '#d97706',
  INFO:     '#64748b',
};

const SEV_RING_COLOR = {
  CRITICAL: '#b5382b',
  WARNING:  '#d97706',
  INFO:     '#94a3b8',
};

const makeBezierCurve = (from, to, archElevation = 0.5) => {
  const midY = Math.max(from[1], to[1]) + archElevation + 0.8;
  const midPoint = new THREE.Vector3(
    (from[0] + to[0]) / 2,
    midY,
    (from[2] + to[2]) / 2
  );
  return new THREE.QuadraticBezierCurve3(
    new THREE.Vector3(...from),
    midPoint,
    new THREE.Vector3(...to)
  );
};

// ─────────────────────────────────────────────────────────────────────────────
// Animated incident path segment
// ─────────────────────────────────────────────────────────────────────────────

const IncidentPathSegment = ({ from, to, severity = 'WARNING', isActive = true }) => {
  const color     = SEV_COLOR[severity] || SEV_COLOR.WARNING;
  const numPulses = 2;

  const curve    = useMemo(() => makeBezierCurve(from, to, 0.6), [from, to]);
  const geometry = useMemo(
    () => new THREE.TubeGeometry(curve, 28, 0.09, 6, false),
    [curve]
  );

  const pulseRefs = useMemo(
    () => Array.from({ length: numPulses }, () => React.createRef()),
    [numPulses]
  );

  useFrame((state) => {
    if (!isActive) return;
    const time = state.clock.elapsedTime;
    const speed = 0.28; // slow, purposeful — not flashy

    pulseRefs.forEach((ref, idx) => {
      if (!ref.current) return;
      const offset = idx / numPulses;
      const t = Math.max(0.02, Math.min(0.98, ((time * speed + offset) % 1.0)));
      const pt      = curve.getPoint(t);
      const tangent = curve.getTangent(t);
      ref.current.position.copy(pt);
      ref.current.quaternion.setFromUnitVectors(
        new THREE.Vector3(0, 1, 0),
        tangent
      );
    });
  });

  return (
    <group name={`incident-path-${from.join(',')}`}>
      {/* Path tube — subtle, semi-transparent */}
      <mesh geometry={geometry} renderOrder={25} raycast={() => null}>
        <meshStandardMaterial
          color={color}
          roughness={0.35}
          metalness={0.55}
          transparent
          opacity={0.55}
          depthWrite={false}
        />
      </mesh>

      {/* Directional amber dashes traveling along path */}
      {isActive && pulseRefs.map((ref, idx) => (
        <mesh
          key={idx}
          ref={ref}
          renderOrder={27}
          raycast={() => null}
        >
          <coneGeometry args={[0.14, 0.42, 6]} />
          <meshBasicMaterial
            color={color}
            transparent
            opacity={0.88}
            depthWrite={false}
          />
        </mesh>
      ))}
    </group>
  );
};

// ─────────────────────────────────────────────────────────────────────────────
// Incident node visual (status ring + clickable hitbox)
// ─────────────────────────────────────────────────────────────────────────────

const IncidentNodeMarker = ({ node, isSelected, onClick }) => {
  const ringRef = useRef();
  const ringColor = SEV_RING_COLOR[node.severity] || SEV_RING_COLOR.WARNING;

  // Very slow pulse scale on the ring — 5-8% oscillation only
  useFrame((state) => {
    if (!ringRef.current) return;
    const s = 1.0 + Math.sin(state.clock.elapsedTime * 1.2) * 0.06;
    ringRef.current.scale.setScalar(s);
  });

  const pos = node.position3d;
  const ringY = pos[1] - 1.8; // slightly below the node label, at building roof level

  return (
    <group name={`incident-node-${node.id}`}>
      {/* Status ring at roof level */}
      <mesh
        ref={ringRef}
        position={[pos[0], ringY, pos[2]]}
        rotation={[-Math.PI / 2, 0, 0]}
        renderOrder={26}
        raycast={() => null}
      >
        <ringGeometry args={[2.2, 2.7, 36]} />
        <meshBasicMaterial
          color={ringColor}
          transparent
          opacity={isSelected ? 0.85 : 0.50}
          depthWrite={false}
          side={THREE.DoubleSide}
        />
      </mesh>

      {/* Invisible clickable sphere at node position */}
      <mesh
        position={[pos[0], pos[1], pos[2]]}
        onClick={(e) => { e.stopPropagation(); if (onClick) onClick(node); }}
        onPointerOver={(e) => { e.stopPropagation(); document.body.style.cursor = 'pointer'; }}
        onPointerOut={(e)  => { e.stopPropagation(); document.body.style.cursor = 'default'; }}
      >
        <sphereGeometry args={[3.0, 8, 8]} />
        <meshBasicMaterial transparent opacity={0} depthWrite={false} />
      </mesh>

      {/* Compact floating label */}
      <Html
        position={[pos[0], pos[1] + 0.6, pos[2]]}
        center
        distanceFactor={38}
        zIndexRange={[80, 0]}
      >
        <IncidentNodeLabel node={node} isSelected={isSelected} onClick={() => onClick && onClick(node)} />
      </Html>
    </group>
  );
};

// ─────────────────────────────────────────────────────────────────────────────
// HTML label for an incident node
// ─────────────────────────────────────────────────────────────────────────────

const STATUS_STYLE = {
  CRITICAL:          { border: '#b5382b', bg: 'rgba(181,56,43,0.18)',  dot: '#e53e3e', text: 'CRITICAL' },
  'CRITICAL DISCHARGE': { border: '#b5382b', bg: 'rgba(181,56,43,0.18)', dot: '#e53e3e', text: 'CRIT DISCH' },
  DISCHARGING:       { border: '#d97706', bg: 'rgba(217,119,6,0.16)',  dot: '#d97706', text: 'DISCHARGE' },
  WARNING:           { border: '#d97706', bg: 'rgba(217,119,6,0.14)',  dot: '#d97706', text: 'WARNING'  },
  DEGRADED:          { border: '#b65a1f', bg: 'rgba(182,90,31,0.14)', dot: '#d97706', text: 'DEGRADED' },
  OFFLINE:           { border: '#64748b', bg: 'rgba(100,116,132,0.14)',dot: '#94a3b8', text: 'OFFLINE'  },
  REDUCED:           { border: '#d97706', bg: 'rgba(217,119,6,0.12)', dot: '#d97706', text: 'REDUCED'  },
  HIGH:              { border: '#d97706', bg: 'rgba(217,119,6,0.12)', dot: '#d97706', text: 'HIGH LOAD'},
  NOMINAL:           { border: '#4f6f52', bg: 'rgba(79,111,82,0.12)', dot: '#38a169', text: 'NOMINAL'  },
};

const IncidentNodeLabel = React.memo(({ node, isSelected, onClick }) => {
  const statusKey = (node.status || '').toUpperCase();
  const style = STATUS_STYLE[statusKey] || STATUS_STYLE.DEGRADED;
  const lines = node.label.split('\n');

  return (
    <div
      onClick={(e) => { e.stopPropagation(); onClick?.(); }}
      style={{
        background: 'rgba(18, 20, 26, 0.96)',
        border: `1.5px solid ${isSelected ? '#b65a1f' : style.border}`,
        borderRadius: '4px',
        padding: '3px 8px 4px',
        fontFamily: 'JetBrains Mono, monospace',
        fontSize: '8.5px',
        fontWeight: 700,
        letterSpacing: '0.05em',
        color: '#f0ece4',
        whiteSpace: 'nowrap',
        pointerEvents: 'auto',
        cursor: 'pointer',
        userSelect: 'none',
        boxShadow: isSelected
          ? `0 0 0 2px ${style.border}, 0 4px 16px rgba(0,0,0,0.5)`
          : '0 2px 10px rgba(0,0,0,0.45)',
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        gap: '2px',
        minWidth: '56px',
        maxWidth: '110px',
      }}
    >
      {/* Status pill */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
        <span style={{
          width: '5px', height: '5px', borderRadius: '50%',
          background: style.dot, flexShrink: 0
        }} />
        <span style={{ fontSize: '7px', color: style.border, fontWeight: 800, letterSpacing: '0.08em' }}>
          {style.text}
        </span>
      </div>
      {/* Node labels */}
      {lines.map((line, i) => (
        <div key={i} style={{
          fontSize: i === 0 ? '8.5px' : '7px',
          fontWeight: i === 0 ? 800 : 600,
          color: i === 0 ? '#f0ece4' : '#94a3b8',
          textAlign: 'center',
        }}>
          {line}
        </div>
      ))}
    </div>
  );
});

// ─────────────────────────────────────────────────────────────────────────────
// Main IncidentGraph 3D component
// ─────────────────────────────────────────────────────────────────────────────

export const IncidentGraph = ({
  incidentGraph,
  onSelectNode,
  selectedNodeId = null,
}) => {
  if (!incidentGraph?.isActive || incidentGraph.nodes.length === 0) return null;

  const { nodes, edges } = incidentGraph;

  // Build a lookup for edge rendering
  const nodeMap = useMemo(() => {
    const m = {};
    nodes.forEach(n => { m[n.id] = n; });
    return m;
  }, [nodes]);

  return (
    <group name="incident-graph-overlay">
      {/* Paths between nodes */}
      {edges.map(edge => {
        const fromNode = nodeMap[edge.fromNodeId];
        const toNode   = nodeMap[edge.toNodeId];
        if (!fromNode || !toNode) return null;
        return (
          <IncidentPathSegment
            key={edge.id}
            from={fromNode.position3d}
            to={toNode.position3d}
            severity={edge.severity}
            isActive
          />
        );
      })}

      {/* Node markers */}
      {nodes.map(node => (
        <IncidentNodeMarker
          key={node.id}
          node={node}
          isSelected={selectedNodeId === node.id}
          onClick={onSelectNode}
        />
      ))}
    </group>
  );
};

export default IncidentGraph;
