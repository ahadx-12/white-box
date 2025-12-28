"use client";

import { Canvas, useFrame } from "@react-three/fiber";
import { Stars } from "@react-three/drei";
import { useMemo, useRef } from "react";
import type { Mesh } from "three";

const statusColors: Record<string, string> = {
  idle: "#0f172a",
  verifying: "#6366f1",
  verified: "#22c55e",
  failed: "#ef4444",
};

function Orb({ status }: { status: keyof typeof statusColors }) {
  const meshRef = useRef<Mesh>(null);
  const color = statusColors[status];
  const baseScale = status === "verifying" ? 1.1 : 1.0;

  useFrame(({ clock }) => {
    if (!meshRef.current) return;
    const t = clock.getElapsedTime();
    meshRef.current.rotation.y = t * 0.15;
    meshRef.current.rotation.x = t * 0.1;
    meshRef.current.position.y = Math.sin(t * 0.4) * 0.3;
    meshRef.current.scale.setScalar(baseScale + Math.sin(t * 0.8) * 0.05);
  });

  return (
    <mesh ref={meshRef}>
      <sphereGeometry args={[1.1, 32, 32]} />
      <meshStandardMaterial color={color} emissive={color} emissiveIntensity={0.35} />
    </mesh>
  );
}

export default function ThreeBackground({
  status,
  reducedMotion,
}: {
  status: keyof typeof statusColors;
  reducedMotion: boolean;
}) {
  const background = useMemo(() => statusColors[status], [status]);
  if (reducedMotion) return null;

  return (
    <div className="pointer-events-none absolute inset-0 -z-10">
      <Canvas
        camera={{ position: [0, 0, 6] }}
        style={{ background }}
        dpr={[1, 1.5]}
      >
        <ambientLight intensity={0.5} />
        <directionalLight position={[2, 4, 2]} intensity={1} />
        <Stars radius={50} depth={20} count={1200} factor={3} fade speed={0.8} />
        <Orb status={status} />
      </Canvas>
    </div>
  );
}
