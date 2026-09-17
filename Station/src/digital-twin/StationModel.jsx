import React from 'react';
import { StationZone } from './StationZone';

export const StationModel = ({ station, showLabels = true }) => {
  const zones = station?.digitalTwin?.zones || [];

  return (
    <group name="station-model-root">
      {/* Ground Permafrost & Snowfield Datum */}
      <mesh receiveShadow rotation={[-Math.PI / 2, 0, 0]} position={[0, -0.05, 0]}>
        <planeGeometry args={[70, 70, 1, 1]} />
        <meshStandardMaterial 
          color="#f4f1ea" 
          roughness={0.9} 
          metalness={0.05} 
        />
      </mesh>

      {/* Subtle Coordinate Grid on Ice Surface */}
      <gridHelper 
        args={[60, 30, '#d5cfc2', '#e8e4dc']} 
        position={[0, 0.01, 0]} 
      />

      {/* Main Structural Modules (6 Required Areas) */}
      {zones.map((zone) => (
        <StationZone 
          key={zone.id} 
          zone={zone} 
          showLabels={showLabels} 
        />
      ))}

      {/* Inter-module Enclosed Tubular Walkways */}
      {/* Walkway 1: Main building to Energy room */}
      <mesh position={[-4.5, 1.8, -0.8]}>
        <boxGeometry args={[3.2, 1.2, 1.2]} />
        <meshStandardMaterial color="#d6cfc3" roughness={0.7} metalness={0.2} />
      </mesh>

      {/* Walkway 2: Main building to Research room */}
      <mesh position={[4.5, 1.8, -0.8]}>
        <boxGeometry args={[3.2, 1.2, 1.2]} />
        <meshStandardMaterial color="#d6cfc3" roughness={0.7} metalness={0.2} />
      </mesh>

      {/* Walkway 3: Main building to Storage */}
      <mesh position={[0, 1.6, -3.8]}>
        <boxGeometry args={[1.4, 1.2, 2.2]} />
        <meshStandardMaterial color="#d6cfc3" roughness={0.7} metalness={0.2} />
      </mesh>

      {/* Walkway 4: Generator area fuel corridor */}
      <mesh position={[-4.2, 1.5, 4.0]}>
        <boxGeometry args={[1.2, 1.0, 3.2]} />
        <meshStandardMaterial color="#c8c0b2" roughness={0.7} metalness={0.2} />
      </mesh>
    </group>
  );
};

export default StationModel;
