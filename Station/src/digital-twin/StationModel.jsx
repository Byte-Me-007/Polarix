import React from 'react';
import { StationZone } from './StationZone';
import { SystemFlowOverlay } from './SystemFlowOverlay';

// New station layout (all zones scaled ~1.75x from original):
//   MAIN:      pos [0, 3.5, 0],    size [34, 7, 22]   → X: -17..+17   Z: -11..+11
//   RESEARCH:  pos [38, 3.2, 0],   size [22, 6.4, 18] → X: +27..+49   Z: -9..+9
//   ENERGY:    pos [0, 3.0, -30],  size [26, 6, 18]   → X: -13..+13   Z: -39..-21
//   GENERATOR: pos [-30, 2.8, -30],size [20, 5.6, 18] → X: -40..-20   Z: -39..-21
//   STORAGE:   pos [32, 2.8, -30], size [20, 5.6, 18] → X: +22..+42   Z: -39..-21
//   COMMS:     pos [0, 2.6, -54],  size [14, 5.2, 14] → X: -7..+7     Z: -61..-47
//
// Gap analysis (all comfortable, 6-10 unit service clearance):
//   MAIN ↔ RESEARCH (x gap):   17 → 27  = 10 units  → Corridor at x=22
//   MAIN ↔ ENERGY (z gap):     -11 → -21 = 10 units  → Corridor at z=-16
//   ENERGY ↔ GENERATOR (x gap):-13 → -20 = 7 units   → Corridor at x=-16.5
//   ENERGY ↔ STORAGE (x gap):  +13 → +22 = 9 units   → Corridor at x=+17.5
//   ENERGY ↔ COMMS (z gap):    -39 → -47 = 8 units   → Corridor at z=-43

export const ZONE_STATUS_CONFIG = {
  CRITICAL: {
    hex: '#e03131',
    rgb: '224, 49, 49',
    name: 'CRITICAL',
    floorOpacity: 0.65,
    glowOpacity: 0.95
  },
  WARNING: {
    hex: '#f59f00',
    rgb: '245, 159, 0',
    name: 'WARNING',
    floorOpacity: 0.55,
    glowOpacity: 0.88
  },
  NORMAL: {
    hex: '#2b8a3e',
    rgb: '43, 138, 62',
    name: 'NORMAL',
    floorOpacity: 0.35,
    glowOpacity: 0.60
  },
  OFFLINE: {
    hex: '#868e96',
    rgb: '134, 142, 150',
    name: 'OFFLINE',
    floorOpacity: 0.22,
    glowOpacity: 0.35
  }
};

export const StationModel = ({
  station,
  sensors = [],
  showLabels = true,
  showHeatmap = false,
  selectedZone = null,
  twinMode = 'NORMAL',
  focusZone = null,
  telemetry = {},
  onSelectAsset,
  selectedAssetId = null
}) => {
  const zones = station?.digitalTwin?.zones || [];

  // Compute dominant health status per zone from sensors
  const zoneHealth = React.useMemo(() => {
    const map = {};
    zones.forEach((z) => {
      const code = z.code || z.id;
      const zoneSensors = sensors.filter((s) => s.zone === code);
      let maxSev = -1;
      let dominant = 'NORMAL';
      zoneSensors.forEach((s) => {
        const stat = (s.status || 'NORMAL').toUpperCase();
        let sev = 0;
        if (stat === 'CRITICAL') sev = 3;
        else if (stat === 'WARNING') sev = 2;
        else if (stat === 'OFFLINE') sev = 1;
        else sev = 0;

        if (sev > maxSev) {
          maxSev = sev;
          dominant = stat;
        }
      });
      map[code] = dominant;
    });
    return map;
  }, [sensors, zones]);

  return (
    <group name="station-model-root">
      {/* ------------------------------------------------------------- */}
      {/* 1. ANTARCTIC PERMAFROST & SNOWFIELD TERRAIN                   */}
      {/* ------------------------------------------------------------- */}
      {/* Smooth Antarctic Packed Snow Plane */}
      <mesh receiveShadow rotation={[-Math.PI / 2, 0, 0]} position={[4, -0.05, -24]}>
        <planeGeometry args={[300, 300, 1, 1]} />
        <meshStandardMaterial color="#f2efe6" roughness={0.92} metalness={0.04} />
      </mesh>

      {/* Coordinate Survey Grid on Snow Surface */}
      <gridHelper
        args={[240, 48, '#ddd8cc', '#e8e3d8']}
        position={[4, 0.01, -24]}
      />

      {/* ------------------------------------------------------------- */}
      {/* 2. SPATIAL STATION FACILITIES (6 Required Modules)            */}
      {/* ------------------------------------------------------------- */}
      {zones.map((zone) => {
        const code = zone.code || zone.id;
        const status = zoneHealth[code] || 'NORMAL';
        const meta = ZONE_STATUS_CONFIG[status] || ZONE_STATUS_CONFIG.NORMAL;
        const isSelectedZone = Boolean(selectedZone && (code === selectedZone));
        return (
          <StationZone
            key={zone.id}
            zone={zone}
            showLabels={showLabels}
            showHeatmap={showHeatmap}
            zoneStatus={status}
            statusMeta={meta}
            isSelectedZone={isSelectedZone}
            hasSelectedZone={Boolean(selectedZone)}
            twinMode={twinMode}
            isHighlighted={Boolean(focusZone && code === focusZone)}
            sensors={sensors}
            telemetry={telemetry}
            onSelectAsset={onSelectAsset}
            selectedAssetId={selectedAssetId}
          />
        );
      })}

      {/* System Mode Energy Flow Overlay */}
      {twinMode === 'SYSTEM' && (
        <SystemFlowOverlay telemetry={telemetry} />
      )}

      {/* ------------------------------------------------------------- */}
      {/* 3. ENCLOSED CONNECTING CORRIDORS & UTILITY BRIDGES             */}
      {/* Insulated arctic umbilical corridors connecting facilities     */}
      {/* ------------------------------------------------------------- */}

      {/* Corridor 1: MAIN ↔ RESEARCH (East Habitat Connector) */}
      <group position={[22, 6.0, 0]}>
        <mesh castShadow receiveShadow>
          <boxGeometry args={[8.0, 7.6, 5.2]} />
          <meshStandardMaterial color="#e2e8f0" roughness={0.4} metalness={0.2} />
        </mesh>
        {/* Parapet Coping */}
        <mesh position={[0, 3.9, 0]}>
          <boxGeometry args={[8.2, 0.24, 5.4]} />
          <meshStandardMaterial color="#334155" roughness={0.6} metalness={0.4} />
        </mesh>
        {/* Continuous Ribbon Windows */}
        {[-2.65, 2.65].map((wz, wi) => (
          <mesh key={`c1-win-${wi}`} position={[0, 0.4, wz]}>
            <boxGeometry args={[6.2, 1.4, 0.08]} />
            <meshStandardMaterial color="#0f172a" roughness={0.08} metalness={0.92} />
          </mesh>
        ))}
        {/* Roof Utility Conduit Tray */}
        <mesh position={[0, 4.15, 0]}>
          <boxGeometry args={[8.0, 0.12, 0.5]} />
          <meshStandardMaterial color="#b45309" metalness={0.6} roughness={0.4} />
        </mesh>
        {/* Heavy Steel Support Stilts with Cross-brace */}
        {[-2.5, 2.5].map((stX, i) => (
          <group key={i} position={[stX, -5.5, 0]}>
            <mesh castShadow>
              <cylinderGeometry args={[0.24, 0.24, 6.0, 8]} />
              <meshStandardMaterial color="#242a35" roughness={0.7} metalness={0.5} />
            </mesh>
            <mesh position={[0, -2.9, 0]}>
              <boxGeometry args={[0.9, 0.18, 0.9]} />
              <meshStandardMaterial color="#3a4454" roughness={0.8} />
            </mesh>
          </group>
        ))}
      </group>

      {/* Corridor 2: MAIN ↔ ENERGY (South Spine Connector) */}
      <group position={[0, 6.0, -16]}>
        <mesh castShadow receiveShadow>
          <boxGeometry args={[5.2, 7.6, 8.0]} />
          <meshStandardMaterial color="#e2e8f0" roughness={0.4} metalness={0.2} />
        </mesh>
        <mesh position={[0, 3.9, 0]}>
          <boxGeometry args={[5.4, 0.24, 8.2]} />
          <meshStandardMaterial color="#334155" roughness={0.6} metalness={0.4} />
        </mesh>
        {/* Side Ribbon Windows */}
        {[-2.65, 2.65].map((wx, wi) => (
          <mesh key={`c2-win-${wi}`} position={[wx, 0.4, 0]} rotation={[0, Math.PI / 2, 0]}>
            <boxGeometry args={[6.2, 1.4, 0.08]} />
            <meshStandardMaterial color="#0f172a" roughness={0.08} metalness={0.92} />
          </mesh>
        ))}
        {/* High-Voltage Copper Busway on Corridor Roof */}
        <mesh position={[0, 4.15, 0]}>
          <boxGeometry args={[0.6, 0.15, 8.0]} />
          <meshStandardMaterial color="#f59e0b" metalness={0.7} roughness={0.3} />
        </mesh>
        {/* Steel Pilings */}
        {[-1.8, 1.8].map((stX, i) => (
          <group key={i} position={[stX, -5.2, 0]}>
            <mesh castShadow>
              <cylinderGeometry args={[0.24, 0.24, 6.0, 8]} />
              <meshStandardMaterial color="#242a35" roughness={0.7} metalness={0.5} />
            </mesh>
            <mesh position={[0, -2.9, 0]}>
              <boxGeometry args={[0.9, 0.18, 0.9]} />
              <meshStandardMaterial color="#3a4454" roughness={0.8} />
            </mesh>
          </group>
        ))}
      </group>

      {/* Corridor 3: ENERGY ↔ GENERATOR (West Utility Breezeway) */}
      <group position={[-16.5, 5.5, -30]}>
        <mesh castShadow receiveShadow>
          <boxGeometry args={[5.5, 6.5, 4.5]} />
          <meshStandardMaterial color="#cbd5e1" roughness={0.45} metalness={0.25} />
        </mesh>
        <mesh position={[0, 3.4, 0]}>
          <boxGeometry args={[5.6, 0.24, 4.6]} />
          <meshStandardMaterial color="#334155" roughness={0.6} metalness={0.4} />
        </mesh>
        {/* Roof Fuel/Coolant Manifold Pipes */}
        {[-0.8, 0.8].map((pyOff, pi) => (
          <mesh key={`c3-pipe-${pi}`} position={[0, 3.65, pyOff]} rotation={[0, 0, Math.PI / 2]}>
            <cylinderGeometry args={[0.12, 0.12, 5.5, 8]} />
            <meshStandardMaterial color={pi === 0 ? '#b45309' : '#475569'} metalness={0.7} />
          </mesh>
        ))}
        <group position={[0, -4.5, 0]}>
          <mesh castShadow>
            <cylinderGeometry args={[0.24, 0.24, 5.0, 8]} />
            <meshStandardMaterial color="#242a35" roughness={0.7} metalness={0.5} />
          </mesh>
          <mesh position={[0, -2.4, 0]}>
            <boxGeometry args={[0.85, 0.16, 0.85]} />
            <meshStandardMaterial color="#3a4454" roughness={0.8} />
          </mesh>
        </group>
      </group>

      {/* Corridor 4: ENERGY ↔ STORAGE (East Logistics Connector) */}
      <group position={[17.5, 5.5, -30]}>
        <mesh castShadow receiveShadow>
          <boxGeometry args={[5.5, 6.5, 4.5]} />
          <meshStandardMaterial color="#cbd5e1" roughness={0.45} metalness={0.25} />
        </mesh>
        <mesh position={[0, 3.4, 0]}>
          <boxGeometry args={[5.6, 0.24, 4.6]} />
          <meshStandardMaterial color="#334155" roughness={0.6} metalness={0.4} />
        </mesh>
        <group position={[0, -4.5, 0]}>
          <mesh castShadow>
            <cylinderGeometry args={[0.24, 0.24, 5.0, 8]} />
            <meshStandardMaterial color="#242a35" roughness={0.7} metalness={0.5} />
          </mesh>
          <mesh position={[0, -2.4, 0]}>
            <boxGeometry args={[0.85, 0.16, 0.85]} />
            <meshStandardMaterial color="#3a4454" roughness={0.8} />
          </mesh>
        </group>
      </group>

      {/* Corridor 5: ENERGY ↔ COMMS (South Covered Utility Corridor) */}
      <group position={[0, 4.5, -43]}>
        <mesh castShadow receiveShadow>
          <boxGeometry args={[3.5, 6.0, 6.0]} />
          <meshStandardMaterial color="#334155" roughness={0.7} metalness={0.3} />
        </mesh>
        {[-1.8, 1.8].map((cx, i) => (
          <mesh key={i} position={[cx, 0, 0]} rotation={[Math.PI / 2, 0, 0]}>
            <cylinderGeometry args={[0.12, 0.12, 6.0, 8]} />
            <meshStandardMaterial color="#1e293b" roughness={0.5} />
          </mesh>
        ))}
        <group position={[0, -4.2, 0]}>
          <mesh castShadow>
            <cylinderGeometry args={[0.22, 0.22, 4.5, 8]} />
            <meshStandardMaterial color="#242a35" roughness={0.7} metalness={0.5} />
          </mesh>
          <mesh position={[0, -2.1, 0]}>
            <boxGeometry args={[0.8, 0.14, 0.8]} />
            <meshStandardMaterial color="#3a4454" roughness={0.8} />
          </mesh>
        </group>
      </group>

      {/* ------------------------------------------------------------- */}
      {/* 4. UTILITY PIPELINE RACK (Generator ↔ Main Building)          */}
      {/* ------------------------------------------------------------- */}
      {/* Heavy insulated pipe manifold running diagonally from Generator region toward Main */}
      <group position={[-22, 1.0, -15]}>
        {/* Insulated Twin Main Pipes */}
        <mesh position={[0, 0, 0]} rotation={[Math.PI / 2, 0, 0]}>
          <cylinderGeometry args={[0.18, 0.18, 14.0, 12]} />
          <meshStandardMaterial color="#64748b" roughness={0.4} metalness={0.6} />
        </mesh>
        <mesh position={[0.5, 0, 0]} rotation={[Math.PI / 2, 0, 0]}>
          <cylinderGeometry args={[0.12, 0.12, 14.0, 12]} />
          <meshStandardMaterial color="#b45309" roughness={0.4} metalness={0.6} />
        </mesh>
        {/* Pipeline Support Saddles */}
        {[-4.5, -1.5, 1.5, 4.5].map((pz, i) => (
          <mesh key={`pipe-saddle-${i}`} position={[0.25, -0.6, pz]}>
            <boxGeometry args={[1.1, 0.8, 0.4]} />
            <meshStandardMaterial color="#242a35" roughness={0.8} />
          </mesh>
        ))}
      </group>

      {/* ------------------------------------------------------------- */}
      {/* 6. POLAR BOUNDARY SURVEY STAKES & HIGH-VISIBILITY MARKERS     */}
      {/* Placed at the 4 outer corners of the full station footprint   */}
      {/* Footprint: X -44..+52, Z -64..+20                            */}
      {/* ------------------------------------------------------------- */}
      {[
        [-46.0, 1.2, -64.0],
        [ 54.0, 1.2, -64.0],
        [-46.0, 1.2,  20.0],
        [ 54.0, 1.2,  20.0],
        [  4.0, 1.2, -64.0],
        [  4.0, 1.2,  20.0],
      ].map(([fx, fy, fz], idx) => (
        <group key={`survey-flag-${idx}`} position={[fx, fy, fz]}>
          <mesh>
            <cylinderGeometry args={[0.08, 0.08, 3.0, 6]} />
            <meshStandardMaterial color="#2d333b" roughness={0.7} />
          </mesh>
          <mesh position={[0.32, 1.1, 0]}>
            <boxGeometry args={[0.65, 0.42, 0.04]} />
            <meshStandardMaterial color="#b65a1f" roughness={0.5} />
          </mesh>
        </group>
      ))}
    </group>
  );
};

export default StationModel;
