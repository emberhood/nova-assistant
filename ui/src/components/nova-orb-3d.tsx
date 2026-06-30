"use client";

import dynamic from "next/dynamic";
import { motion } from "framer-motion";
import type { NovaState } from "@/lib/types";

const NovaOrbCanvas = dynamic(() => import("./nova-orb-3d-canvas"), { ssr: false });

const BASE = 220; // reference size the orb proportions are designed at

interface NovaOrbProps {
  state?: NovaState;
  size?: number;
}

export default function NovaOrb({ state = "idle", size = BASE }: NovaOrbProps) {
  const isSpeaking = state === "speaking";
  const scale = size / BASE;

  return (
    <div
      className="relative flex flex-shrink-0 items-center justify-center"
      style={{ width: size, height: size }}
    >
      <div className="absolute inset-0">
        <NovaOrbCanvas state={state} />
      </div>

      <span
        className="pointer-events-none relative z-[2] font-heading font-black leading-none text-nova-cyan"
        style={{ fontSize: 32 * scale, textShadow: "0 0 20px var(--nova-cyan)" }}
      >
        N
      </span>

      {isSpeaking && (
        <div className="pointer-events-none absolute flex items-center gap-1" style={{ bottom: -36 * scale }}>
          {Array.from({ length: 7 }).map((_, i) => (
            <motion.div
              key={i}
              className="origin-center rounded-sm bg-nova-cyan"
              style={{ width: Math.max(2, 3 * scale), height: 28 * scale, boxShadow: "0 0 6px var(--nova-cyan)" }}
              animate={{ scaleY: [0.3, 1, 0.3] }}
              transition={{ duration: 0.5, repeat: Infinity, delay: i * 0.07, ease: "easeInOut" }}
            />
          ))}
        </div>
      )}
    </div>
  );
}
