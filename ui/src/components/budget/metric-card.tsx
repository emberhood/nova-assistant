"use client";

import { motion } from "framer-motion";

const COLORS = {
  accent: "var(--nova-cyan)",
  green: "var(--nova-green)",
  red: "var(--nova-red)",
} as const;

interface MetricCardProps {
  label: string;
  value: string;
  color?: keyof typeof COLORS;
  icon: string;
  delay?: number;
}

export default function MetricCard({ label, value, color = "accent", icon, delay = 0 }: MetricCardProps) {
  const c = COLORS[color];

  return (
    <motion.div
      className="glass flex flex-col items-center gap-2 px-3.5 py-5 text-center"
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay }}
    >
      <div className="text-2xl" style={{ color: c }}>
        {icon}
      </div>
      <div className="font-heading text-[9px] uppercase tracking-[0.18em] text-nova-text-dim">{label}</div>
      <div className="font-heading text-[22px] font-bold" style={{ color: c, textShadow: `0 0 20px ${c}` }}>
        {value}
      </div>
    </motion.div>
  );
}
