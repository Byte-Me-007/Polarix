import React, { useRef, useEffect } from 'react';
import { Canvas } from '@react-three/fiber';
import { OrbitControls } from '@react-three/drei';
import { StationModel } from './StationModel';
import { SensorMarker } from './SensorMarker';
import { SpatialHeatmap } from './SpatialHeatmap';

// Elevated overview framing — complete station footprint visible (all 6 zones).
// Camera at [16,60,20] provides a clean 45° isometric overview with ~20% margin on all sides.
// Target at station centroid [2,2,-8] ensures even spatial framing.
const DEFAULT_CAMERA_POS = [16, 60, 20];
const DEFAULT_TARGET = [2, 2, -8];

export const DigitalTwinScene = ({
  station,
  sensors = [],
  selectedSensor,
  onSelectSensor,
  showSensors = true,
  showLabels = true,
  showHeatmap = false,
  resetTrigger = 0
}) => {
  const controlsRef = useRef();

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
      controlsRef.current.target.set(
        selectedSensor.x || 0,
        (selectedSensor.y || 0) + 1.2,
        selectedSensor.z || 0
      );
      controlsRef.current.update();
    }
  }, [selectedSensor]);

  return (
    <Canvas
      camera={{ position: DEFAULT_CAMERA_POS, fov: 52 }}
      shadows
      style={{ width: '100%', height: '100%', background: '#f8f6f0' }}
    >
      {/* Soft Antarctic Daylight Lighting (Warm neutral, no neon/blue) */}
      <ambientLight intensity={0.78} color="#fffcf5" />
      <directionalLight
        position={[45, 65, 35]}
        intensity={1.4}
        castShadow
        shadow-mapSize={[2048, 2048]}
        shadow-camera-left={-55}
        shadow-camera-right={55}
        shadow-camera-top={55}
        shadow-camera-bottom={-55}
        color="#fff9ec"
      />
      {/* Secondary fill light for soft dimensional shadows */}
      <directionalLight position={[-40, 30, -35]} intensity={0.45} color="#e8e3d8" />

      {/* OrbitControls with smooth damping and reasonable constraints */}
      <OrbitControls
        ref={controlsRef}
        target={DEFAULT_TARGET}
        enableDamping
        dampingFactor={0.06}
        minDistance={8}
        maxDistance={120}
        maxPolarAngle={Math.PI / 2 - 0.04} // Ground level floor limit
      />

      {/* Main Connected Modular Station Footprint */}
      <StationModel 
        station={station} 
        showLabels={showLabels} 
      />

      {/* Spatial Sensor Condition Heatmap Overlay */}
      {showHeatmap && (
        <SpatialHeatmap 
          sensors={sensors} 
          zones={station?.digitalTwin?.zones || []} 
        />
      )}

      {/* Configuration-Driven 3D Sensor Markers across all facilities */}
      {showSensors &&
        sensors.map((sensor) => (
          <SensorMarker
            key={sensor.id}
            sensor={sensor}
            isSelected={selectedSensor?.id === sensor.id}
            onSelect={onSelectSensor}
          />
        ))}
    </Canvas>
  );
};

export default DigitalTwinScene;
