"use client";

import { useRef } from "react";
import { Canvas, useFrame } from "@react-three/fiber";
import { MeshDistortMaterial } from "@react-three/drei";
import { EffectComposer, Bloom } from "@react-three/postprocessing";
import type { Mesh } from "three";
import type { NovaState } from "@/lib/types";

const STATE_CONFIG: Record<NovaState, { color: string; distort: number; speed: number; spin: number }> = {
  idle: { color: "#00d4ff", distort: 0.25, speed: 1.2, spin: 0.4 },
  listening: { color: "#00ff9d", distort: 0.45, speed: 3, spin: 1.2 },
  processing: { color: "#7b2fff", distort: 0.5, speed: 4, spin: 1.6 },
  speaking: { color: "#00d4ff", distort: 0.6, speed: 5, spin: 2 },
};

function OrbCore({ state }: { state: NovaState }) {
  const meshRef = useRef<Mesh>(null);
  const cfg = STATE_CONFIG[state];

  useFrame((_, delta) => {
    if (!meshRef.current) return;
    meshRef.current.rotation.y += delta * cfg.spin * 0.3;
    meshRef.current.rotation.x += delta * cfg.spin * 0.15;
  });

  return (
    <mesh ref={meshRef}>
      <sphereGeometry args={[1, 64, 64]} />
      <MeshDistortMaterial
        color={cfg.color}
        distort={cfg.distort}
        speed={cfg.speed}
        roughness={0.15}
        metalness={0.6}
        emissive={cfg.color}
        emissiveIntensity={0.5}
      />
    </mesh>
  );
}

function OrbRings({ state }: { state: NovaState }) {
  const ring1 = useRef<Mesh>(null);
  const ring2 = useRef<Mesh>(null);
  const cfg = STATE_CONFIG[state];

  useFrame((_, delta) => {
    if (ring1.current) ring1.current.rotation.z += delta * cfg.spin * 0.4;
    if (ring2.current) ring2.current.rotation.z -= delta * cfg.spin * 0.25;
  });

  return (
    <>
      <mesh ref={ring1} rotation={[Math.PI / 2.4, 0, 0]}>
        <torusGeometry args={[1.6, 0.015, 16, 100]} />
        <meshBasicMaterial color="#00d4ff" transparent opacity={0.5} />
      </mesh>
      <mesh ref={ring2} rotation={[Math.PI / 1.8, 0.4, 0]}>
        <torusGeometry args={[1.35, 0.012, 16, 100]} />
        <meshBasicMaterial color="#7b2fff" transparent opacity={0.4} />
      </mesh>
    </>
  );
}

export default function NovaOrb3DCanvas({ state }: { state: NovaState }) {
  const cfg = STATE_CONFIG[state];

  return (
    <Canvas
      camera={{ position: [0, 0, 4], fov: 40 }}
      gl={{ antialias: true, alpha: true }}
      dpr={[1, 2]}
    >
      <ambientLight intensity={0.4} />
      <pointLight position={[3, 3, 3]} intensity={1.2} color={cfg.color} />
      <OrbCore state={state} />
      <OrbRings state={state} />
      <EffectComposer>
        <Bloom intensity={1.2} luminanceThreshold={0.2} luminanceSmoothing={0.9} mipmapBlur />
      </EffectComposer>
    </Canvas>
  );
}
