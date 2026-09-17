import React, { useRef, useEffect } from 'react';
import { Canvas } from '@react-three/fiber';
import { OrbitControls } from '@react-three/drei';
import { StationModel } from './StationModel';
import { SensorMarker } from './SensorMarker';

const DEFAULT_CAMERA_POS = [20, 16, 24];
const DEFAULT_TARGET = [0, 1.5, 0];

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
      camera={{ position: DEFAULT_CAMERA_POS, fov: 42 }}
      shadows
      style={{ width: '100%', height: '100%', background: '#f8f6f0' }}
    >
      {/* Soft Antarctic Daylight Lighting (Warm neutral, no neon/blue) */}
      <ambientLight intensity={0.7} color="#fffcf5" />
      <directionalLight
        position={[25, 35, 20]}
        intensity={1.2}
        castShadow
        shadow-mapSize={[1024, 1024]}
        shadow-camera-left={-25}
        shadow-camera-right={25}
        shadow-camera-top={25}
        shadow-camera-bottom={-25}
        color="#fff9ec"
      />
      <directionalLight position={[-20, 15, -15]} intensity={0.4} color="#e5e0d5" />

      {/* OrbitControls with smooth damping and reasonable constraints */}
      <OrbitControls
        ref={controlsRef}
        target={DEFAULT_TARGET}
        enableDamping
        dampingFactor={0.06}
        minDistance={8}
        maxDistance={65}
        maxPolarAngle={Math.PI / 2 - 0.05} // Do not go below ground
      />

      {/* Main Structural Station Geometry (6 required zones) */}
      <StationModel 
        station={station} 
        showLabels={showLabels} 
      />

      {/* Sensor Markers from Configuration */}
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
