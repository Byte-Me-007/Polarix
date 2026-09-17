import React, { useRef, useEffect } from 'react';
import { Canvas } from '@react-three/fiber';
import { OrbitControls } from '@react-three/drei';
import { StationModel } from './StationModel';
import { SensorMarker } from './SensorMarker';

// Elevated axonometric isometric overview framing the entire connected modular station footprint
const DEFAULT_CAMERA_POS = [26, 22, 28];
const DEFAULT_TARGET = [0, 1.4, -4.0];

export const DigitalTwinScene = ({
  station,
  sensors = [],
  selectedSensor,
  onSelectSensor,
  showSensors = true,
  showLabels = true,
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

  return (
    <Canvas
      camera={{ position: DEFAULT_CAMERA_POS, fov: 40 }}
      shadows
      style={{ width: '100%', height: '100%', background: '#f8f6f0' }}
    >
      {/* Soft Antarctic Daylight Lighting (Warm neutral, no blue/cyan neon) */}
      <ambientLight intensity={0.75} color="#fffcf5" />
      <directionalLight
        position={[30, 42, 25]}
        intensity={1.35}
        castShadow
        shadow-mapSize={[2048, 2048]}
        shadow-camera-left={-28}
        shadow-camera-right={28}
        shadow-camera-top={28}
        shadow-camera-bottom={-28}
        color="#fff9ec"
      />
      {/* Secondary fill light for soft shadows */}
      <directionalLight position={[-25, 20, -20]} intensity={0.45} color="#e6e1d6" />

      {/* OrbitControls with smooth damping and polar angle constraints */}
      <OrbitControls
        ref={controlsRef}
        target={DEFAULT_TARGET}
        enableDamping
        dampingFactor={0.06}
        minDistance={8}
        maxDistance={80}
        maxPolarAngle={Math.PI / 2 - 0.05} // Ground level floor limit
      />

      {/* Main Connected Modular Station Footprint */}
      <StationModel 
        station={station} 
        showLabels={showLabels} 
      />

      {/* Configuration-Driven 3D Sensor Markers */}
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
