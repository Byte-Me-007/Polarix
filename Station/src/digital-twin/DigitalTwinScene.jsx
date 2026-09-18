import React, { useRef, useEffect } from 'react';
import { Canvas } from '@react-three/fiber';
import { OrbitControls } from '@react-three/drei';
import { StationModel } from './StationModel';
import { SensorMarker, computeDisplayPos } from './SensorMarker';
import { SpatialHeatmap } from './SpatialHeatmap';

// Elevated perspective overview — calibrated to match authentic station angle
const DEFAULT_CAMERA_POS = [18, 65, 75];
const DEFAULT_TARGET = [3, 8, -16];

// Zone focus positions — calibrated for taller buildings
const ZONE_FOCUS = {
  MAIN:      { pos: [30,  55, 40],   target: [0,   7.0, 0]   },
  RESEARCH:  { pos: [72,  55, 30],   target: [38,  6.5, 0]   },
  ENERGY:    { pos: [28,  52, 5],    target: [0,   6.5, -30] },
  GENERATOR: { pos: [-14, 52, 5],    target: [-30, 5.5, -30] },
  STORAGE:   { pos: [60,  52, 5],    target: [32,  5.5, -30] },
  COMMS:     { pos: [25,  48, -30],  target: [0,   5.0, -54] }
};

export const DigitalTwinScene = ({
  station,
  sensors = [],
  telemetry = {},
  selectedSensor,
  onSelectSensor,
  showSensors = true,
  showLabels = true,
  showHeatmap = false,
  resetTrigger = 0,
  twinMode = 'NORMAL',
  focusZone = null,
  onSelectAsset,
  selectedAssetId = null
}) => {
  const controlsRef = useRef();
  const zones = station?.digitalTwin?.zones || [];

  // Reset camera view whenever resetTrigger increments
  useEffect(() => {
    if (controlsRef.current && resetTrigger > 0) {
      controlsRef.current.reset();
      controlsRef.current.object.position.set(...DEFAULT_CAMERA_POS);
      controlsRef.current.target.set(...DEFAULT_TARGET);
      controlsRef.current.update();
    }
  }, [resetTrigger]);

  // Smooth camera target focus when a sensor is selected
  useEffect(() => {
    if (controlsRef.current && selectedSensor) {
      const disp = computeDisplayPos(selectedSensor, zones);
      controlsRef.current.target.set(
        disp.x,
        disp.y + 0.5,
        disp.z
      );
      controlsRef.current.update();
    }
  }, [selectedSensor?.id]);

  // Smooth camera focus when a zone is targeted from cross-module navigation
  useEffect(() => {
    if (!controlsRef.current || !focusZone) return;
    const focus = ZONE_FOCUS[focusZone] || ZONE_FOCUS.MAIN;
    controlsRef.current.object.position.set(...focus.pos);
    controlsRef.current.target.set(...focus.target);
    controlsRef.current.update();
  }, [focusZone]);

  // Determine effective heatmap: HEATMAP mode always shows it; others use prop
  const effectiveHeatmap = twinMode === 'HEATMAP' ? true : (twinMode === 'NORMAL' ? false : showHeatmap);

  return (
    <Canvas
      camera={{ position: DEFAULT_CAMERA_POS, fov: 50 }}
      shadows
      style={{ width: '100%', height: '100%', background: '#f8f6f0' }}
    >
      {/* Soft Antarctic Daylight Lighting (Warm neutral, no neon/blue) */}
      <ambientLight intensity={0.78} color="#fffcf5" />
      <directionalLight
        position={[60, 80, 50]}
        intensity={1.4}
        castShadow
        shadow-mapSize={[2048, 2048]}
        shadow-camera-left={-100}
        shadow-camera-right={100}
        shadow-camera-top={100}
        shadow-camera-bottom={-100}
        color="#fff9ec"
      />
      {/* Secondary fill light for soft dimensional shadows */}
      <directionalLight position={[-55, 40, -50]} intensity={0.45} color="#e8e3d8" />

      {/* OrbitControls with smooth damping and reasonable constraints */}
      <OrbitControls
        ref={controlsRef}
        target={DEFAULT_TARGET}
        enableDamping
        dampingFactor={0.06}
        minDistance={12}
        maxDistance={200}
        maxPolarAngle={Math.PI / 2 - 0.04}
      />

      {/* Main Connected Modular Station Footprint */}
      <StationModel
        station={station}
        sensors={sensors}
        showLabels={showLabels}
        showHeatmap={twinMode === 'HEATMAP'}
        selectedZone={selectedSensor?.zone}
        selectedSensor={selectedSensor}
        twinMode={twinMode}
        focusZone={focusZone}
        telemetry={telemetry}
        onSelectAsset={onSelectAsset}
        selectedAssetId={selectedAssetId}
      />

      {/* Spatial Sensor Condition Heatmap Overlay (HEATMAP mode only) */}
      {twinMode === 'HEATMAP' && (
        <SpatialHeatmap
          sensors={sensors}
          zones={zones}
          selectedSensor={selectedSensor}
        />
      )}

      {/* Configuration-Driven 3D Sensor Markers across all facilities */}
      {showSensors &&
        sensors.map((sensor) => (
          <SensorMarker
            key={sensor.id}
            sensor={sensor}
            zones={zones}
            isSelected={selectedSensor?.id === sensor.id}
            onSelect={onSelectSensor}
          />
        ))}
    </Canvas>
  );
};

export default DigitalTwinScene;
