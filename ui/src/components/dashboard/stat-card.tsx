"use client";

import { motion } from "framer-motion";

const COLORS = {
  accent: "var(--nova-cyan)",
  accent2: "var(--nova-violet)",
  green: "var(--nova-green)",
  red: "var(--nova-red)",
} as const;

interface StatCardProps {
  label: string;
  value: string;
  sub?: string;
  color?: keyof typeof COLORS;
  icon: string;
}

export default function StatCard({ label, value, sub, color = "accent", icon }: StatCardProps) {
  const c = COLORS[color];

  return (
    <motion.div
      className="glass flex items-center gap-3.5 px-[18px] py-4"
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
    >
      <div className="text-[22px]" style={{ color: c }}>
        {icon}
      </div>
      <div className="flex flex-col">
        <div className="font-heading text-[9px] uppercase tracking-[0.15em] text-nova-text-dim">{label}</div>
        <div className="my-0.5 font-heading text-xl font-bold" style={{ color: c }}>
          {value}
        </div>
        {sub && <div className="text-[11px] text-nova-text-dim">{sub}</div>}
      </div>
    </motion.div>
  );
}
