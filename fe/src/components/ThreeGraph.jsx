import React, { useRef } from 'react';
import { Canvas, useFrame } from '@react-three/fiber';
import { OrbitControls, Text, Float } from '@react-three/drei';
import * as THREE from 'three';

function BloodDrop({ position, color, label, value }) {
  const groupRef = useRef();
  
  useFrame((state) => {
    groupRef.current.rotation.y = Math.sin(state.clock.elapsedTime * 0.5) * 0.2;
  });

  return (
    <Float speed={2} rotationIntensity={0.2} floatIntensity={0.5} position={position}>
      <group ref={groupRef}>
        {/* Drop Shape */}
        <mesh position={[0, 0, 0]} castShadow>
          <sphereGeometry args={[1, 32, 32]} />
          <meshStandardMaterial color={color} roughness={0.1} metalness={0.3} />
        </mesh>
        <mesh position={[0, 0.8, 0]} castShadow>
          <coneGeometry args={[0.98, 1.6, 32]} />
          <meshStandardMaterial color={color} roughness={0.1} metalness={0.3} />
        </mesh>

        {/* Label */}
        <Text
          position={[0, -1.8, 0]}
          fontSize={0.5}
          color="#1a1a1a"
          anchorX="center"
          anchorY="middle"
          fontWeight="bold"
        >
          {label}
        </Text>
        <Text
          position={[0, -2.4, 0]}
          fontSize={0.4}
          color="#666666"
          anchorX="center"
          anchorY="middle"
        >
          {value} Units
        </Text>
      </group>
    </Float>
  );
}

export function ThreeGraph({ stats }) {
  const topGroups = Object.entries(stats || {}).slice(0, 4);
  const colors = ['#ef4444', '#f97316', '#eab308', '#3b82f6']; // Red, Orange, Yellow, Blue
  
  return (
    <div className="w-full h-full min-h-[300px] bg-transparent rounded-xl relative cursor-grab active:cursor-grabbing">
      <Canvas shadows={{ type: THREE.PCFShadowMap }} camera={{ position: [0, 1, 12], fov: 45 }}>
        <ambientLight intensity={0.6} />
        <directionalLight position={[10, 10, 5]} intensity={1.5} castShadow />
        <pointLight position={[-10, -10, -5]} intensity={0.5} />
        
        {topGroups.length === 0 ? (
           <Text position={[0,0,0]} fontSize={1} color="#666">No Data</Text>
        ) : (
          topGroups.map(([group, count], idx) => (
            <BloodDrop 
              key={group} 
              position={[(idx - 1.5) * 3, 0.5, 0]} 
              color={colors[idx % colors.length]} 
              label={group}
              value={count}
            />
          ))
        )}
        <OrbitControls enableZoom={false} minPolarAngle={Math.PI/4} maxPolarAngle={Math.PI/2} />
      </Canvas>
    </div>
  );
}
