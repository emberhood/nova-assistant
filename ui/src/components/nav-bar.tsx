"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { motion } from "framer-motion";
import { useNovaStore } from "@/lib/store";
import { useSelectUser } from "@/hooks/use-select-user";
import type { NovaState, UserId } from "@/lib/types";

const NAV_ITEMS = [
  { href: "/", label: "Dashboard", icon: "⬡" },
  { href: "/calendar", label: "Calendar", icon: "◫" },
  { href: "/budget", label: "Budget", icon: "◈" },
] as const;

const STATE_COLORS: Record<NovaState, string> = {
  idle: "var(--nova-text-dim)",
  listening: "var(--nova-green)",
  speaking: "var(--nova-cyan)",
  processing: "var(--nova-violet)",
};

const STATE_LABELS: Record<NovaState, string> = {
  idle: "STANDBY",
  listening: "LISTENING",
  speaking: "SPEAKING",
  processing: "PROCESSING",
};

const USERS: { id: UserId; label: string; initial: string; color: string }[] = [
  { id: "owner", label: "Marios", initial: "J", color: "#00d4ff" },
  { id: "andriana", label: "Andriana", initial: "A", color: "#f472b6" },
  { id: "shared", label: "Shared", initial: "♡", color: "#fbbf24" },
];

export default function NavBar() {
  const pathname = usePathname();
  const novaState = useNovaStore((s) => s.novaState);
  const activeUser = useNovaStore((s) => s.activeUser);
  const selectUser = useSelectUser();

  return (
    <nav className="glass-strong relative z-10 flex h-[58px] flex-shrink-0 items-center gap-6 rounded-none border-0 border-b border-nova-border px-6">
      <div className="flex flex-shrink-0 items-baseline gap-0.5 font-heading">
        <span
          className="text-[22px] font-black text-nova-cyan"
          style={{ textShadow: "0 0 20px var(--nova-cyan)" }}
        >
          N
        </span>
        <span className="text-base font-bold tracking-[0.15em] text-nova-text">OVA</span>
        <span className="ml-1.5 text-[9px] font-normal tracking-[0.1em] text-nova-text-dim">
          v1.0
        </span>
      </div>

      <div className="flex flex-1 items-center gap-1">
        {NAV_ITEMS.map((item) => {
          // Hide Budget on the shared view (no shared budget)
          if (item.href === "/budget" && activeUser === "shared") return null;
          const active = pathname === item.href;
          return (
            <Link
              key={item.href}
              href={item.href}
              className={`relative flex items-center gap-1.5 rounded-md px-4 py-1.5 font-heading text-[11px] font-medium uppercase tracking-[0.12em] transition-colors ${
                active ? "text-nova-cyan" : "text-nova-text-dim hover:text-nova-text-mid"
              }`}
            >
              <span className="text-[13px]">{item.icon}</span>
              <span>{item.label}</span>
              {active && (
                <motion.div
                  className="absolute -bottom-px left-4 right-4 h-0.5 rounded-sm bg-nova-cyan"
                  style={{ boxShadow: "0 0 8px var(--nova-cyan)" }}
                  layoutId="nav-indicator"
                  transition={{ type: "spring", stiffness: 400, damping: 35 }}
                />
              )}
            </Link>
          );
        })}
      </div>

      <div className="flex flex-shrink-0 items-center gap-1.5">
        {USERS.map((u) => {
          const active = activeUser === u.id;
          return (
            <button
              key={u.id}
              onClick={() => selectUser(u.id)}
              title={u.label}
              className="flex items-center gap-1.5 rounded-full border py-1 pr-2.5 pl-1 font-heading text-[9px] uppercase tracking-[0.1em] transition-all"
              style={{
                borderColor: active ? u.color : "rgba(255,255,255,0.08)",
                background: active
                  ? `color-mix(in srgb, ${u.color} 15%, transparent)`
                  : "rgba(255,255,255,0.04)",
                color: active ? u.color : "var(--nova-text-dim)",
                boxShadow: active ? `0 0 12px color-mix(in srgb, ${u.color} 30%, transparent)` : "none",
              }}
            >
              <span
                className="flex h-5 w-5 items-center justify-center rounded-full border text-[10px] font-bold"
                style={{
                  background: `color-mix(in srgb, ${u.color} 20%, transparent)`,
                  borderColor: `color-mix(in srgb, ${u.color} 50%, transparent)`,
                  color: u.color,
                }}
              >
                {u.initial}
              </span>
              <span className="leading-none">{u.label}</span>
            </button>
          );
        })}
      </div>

      <div className="flex flex-shrink-0 items-center gap-2">
        <motion.div
          className="h-[7px] w-[7px] rounded-full"
          animate={{
            backgroundColor: STATE_COLORS[novaState],
            boxShadow: `0 0 8px ${STATE_COLORS[novaState]}`,
          }}
          transition={{ duration: 0.3 }}
        />
        <span
          className="font-heading text-[10px] font-medium tracking-[0.15em] transition-colors"
          style={{ color: STATE_COLORS[novaState] }}
        >
          {STATE_LABELS[novaState] ?? "STANDBY"}
        </span>
      </div>
    </nav>
  );
}
