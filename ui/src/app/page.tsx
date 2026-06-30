"use client";

import { useCallback, useState } from "react";
import { motion } from "framer-motion";
import { useNovaStore } from "@/lib/store";
import { useClock } from "@/hooks/use-clock";
import { useEnrollStatus } from "@/hooks/use-enroll-status";
import { triggerVoice, startEnroll } from "@/lib/api";
import NovaOrb from "@/components/nova-orb-3d";
import StatCard from "@/components/dashboard/stat-card";
import InfoRow from "@/components/dashboard/info-row";
import type { UserId } from "@/lib/types";

const DAY_NAMES = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"];
const MONTH_NAMES = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];

function pad(n: number) {
  return String(n).padStart(2, "0");
}

const USER_LABELS: Partial<Record<UserId, string>> = {
  owner: "My",
  andriana: "Andriana's",
};

export default function DashboardPage() {
  const novaState = useNovaStore((s) => s.novaState);
  const budgetData = useNovaStore((s) => s.budgetData);
  const calData = useNovaStore((s) => s.calData);
  const lastHeard = useNovaStore((s) => s.lastHeard);
  const lastResponse = useNovaStore((s) => s.lastResponse);
  const activeUser = useNovaStore((s) => s.activeUser);

  const userLabel = USER_LABELS[activeUser] ?? "My";
  const now = useClock();
  const enrollStatus = useEnrollStatus();
  const [enrolling, setEnrolling] = useState(false);

  const handleEnroll = useCallback(() => {
    setEnrolling(true);
    startEnroll()
      .then(() => setTimeout(() => setEnrolling(false), 14000))
      .catch(() => setEnrolling(false));
  }, []);

  const hh = now ? pad(now.getHours()) : "--";
  const mm = now ? pad(now.getMinutes()) : "--";
  const ss = now ? pad(now.getSeconds()) : "--";
  const dayName = now ? DAY_NAMES[now.getDay()] : "";
  const dateStr = now ? `${now.getDate()} ${MONTH_NAMES[now.getMonth()]} ${now.getFullYear()}` : "";

  const todayStr = now ? now.toISOString().slice(0, 10) : "";
  const todayEvents = calData?.weeks?.flat().filter((d) => d.date === todayStr) ?? [];

  const balance = budgetData?.available ? budgetData.totalBalance.toFixed(2) : "—";
  const monthExp = budgetData?.available ? Math.abs(budgetData.monthExpenses).toFixed(2) : "—";
  const monthInc = budgetData?.available ? budgetData.monthIncome.toFixed(2) : "—";

  return (
    <div className="panel gap-[18px]">
      {/* top row: clock + orb */}
      <div className="glass-strong grid min-h-[260px] grid-cols-[1fr_auto_1fr] items-center gap-8 px-9 py-7">
        <div className="flex flex-col gap-3">
          <div className="flex items-baseline gap-1.5 font-heading">
            <span
              className="text-[64px] font-black tracking-[-0.02em] text-nova-text"
              style={{ textShadow: "0 0 30px var(--nova-glow-1)" }}
            >
              {hh}
              <span className="animate-[blink_1s_step-end_infinite]">:</span>
              {mm}
            </span>
            <span className="mb-2 self-end text-[28px] font-normal text-nova-text-mid">{ss}</span>
          </div>
          <div className="flex flex-col gap-[3px] font-heading">
            <span className="text-sm font-bold uppercase tracking-[0.15em] text-nova-cyan">{dayName}</span>
            <span className="text-xs tracking-[0.1em] text-nova-text-mid">{dateStr}</span>
          </div>
          <div className="my-1 h-px w-12" style={{ background: "linear-gradient(90deg, var(--nova-cyan), transparent)" }} />
          <div className="flex gap-2">
            <span className="tag tag-cyan">SYS ONLINE</span>
            <span className="tag tag-green">AI READY</span>
          </div>
        </div>

        <div className="flex flex-col items-center gap-12">
          <NovaOrb state={novaState} />
          <div className="-mt-5 max-w-[200px] truncate text-center font-heading text-[11px] tracking-[0.15em] text-nova-text-mid">
            {novaState === "idle" && (lastResponse || 'Πες "Hey Jarvis"')}
            {novaState === "listening" && "Ακούω..."}
            {novaState === "processing" && "Επεξεργάζομαι..."}
            {novaState === "speaking" && "Μιλάω..."}
          </div>
          {lastHeard && novaState === "idle" && (
            <div className="max-w-[200px] truncate text-center text-[11px] italic text-nova-text-dim">
              &quot;{lastHeard}&quot;
            </div>
          )}
          <button
            className="rounded-sm border border-nova-cyan/20 bg-nova-cyan/[0.07] px-3.5 py-1.5 font-heading text-[10px] tracking-[0.1em] text-nova-text-dim transition-colors hover:border-nova-cyan hover:bg-nova-cyan/[0.12] hover:text-nova-cyan"
            title="Trigger manually (backend must be running)"
            onClick={() => {
              triggerVoice().catch(() => {});
            }}
          >
            ▶ Test trigger
          </button>
        </div>

        <div className="flex flex-col items-end">
          <p className="section-title">System</p>
          <div className="flex w-full flex-col items-end gap-2">
            <InfoRow label="Mode" value="Active" />
            <InfoRow label="Voice" value="Whisper" />
            <InfoRow label="AI" value="Haiku" />
            <InfoRow
              label="Budget"
              value={budgetData?.available ? "Connected" : "Offline"}
              valueColor={budgetData?.available ? "green" : "red"}
            />
            {enrollStatus?.available && (
              <InfoRow
                label="Speaker"
                value={enrollStatus.enrolled ? "Enrolled" : "Not enrolled"}
                valueColor={enrollStatus.enrolled ? "green" : "accent2"}
              />
            )}
          </div>
          {enrollStatus?.available && (
            <button
              className="mt-2.5 w-full rounded-sm border border-nova-cyan/20 bg-nova-cyan/[0.07] px-3.5 py-1.5 font-heading text-[10px] tracking-[0.1em] text-nova-text-dim transition-colors hover:border-nova-cyan hover:bg-nova-cyan/[0.12] hover:text-nova-cyan disabled:cursor-not-allowed"
              style={{ opacity: enrolling ? 0.5 : 1 }}
              disabled={enrolling}
              onClick={handleEnroll}
              title="Record 12 seconds of your voice to enroll"
            >
              {enrolling ? "● Recording 12s..." : enrollStatus.enrolled ? "↺ Re-enroll voice" : "+ Enroll my voice"}
            </button>
          )}
        </div>
      </div>

      {/* stat cards */}
      <div className="grid grid-cols-4 gap-3.5">
        <StatCard label={`${userLabel} Balance`} value={`€${balance}`} icon="◈" color="accent" />
        <StatCard label="Month Income" value={`€${monthInc}`} icon="▲" color="green" sub="this month" />
        <StatCard label="Month Expenses" value={`€${monthExp}`} icon="▼" color="red" sub="this month" />
        <StatCard
          label="Upcoming"
          value={`${todayEvents.length}`}
          icon="◫"
          color="accent2"
          sub={todayEvents.length === 1 ? "event today" : "events today"}
        />
      </div>

      {/* recent activity */}
      {budgetData?.available && budgetData.recentExpenses?.length > 0 && (
        <div className="glass px-[22px] py-5">
          <p className="section-title">Recent Transactions</p>
          <div className="flex flex-col gap-2">
            {budgetData.recentExpenses.map((e, i) => (
              <motion.div
                key={i}
                className="grid grid-cols-[90px_1fr_90px_80px] items-center gap-3 rounded-sm border border-transparent bg-nova-cyan/[0.03] px-2.5 py-2 transition-colors hover:border-nova-border hover:bg-nova-cyan/[0.06]"
                initial={{ opacity: 0, x: -10 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: i * 0.05 }}
              >
                <span className="tag tag-cyan">{e.category || "Other"}</span>
                <span className="text-[13px] text-nova-text-mid">{e.notes || "—"}</span>
                <span className="text-right font-heading text-[11px] text-nova-text-dim">{e.date.slice(0, 10)}</span>
                <span
                  className="text-right font-heading text-[13px] font-semibold"
                  style={{ color: e.amount < 0 ? "var(--nova-red)" : "var(--nova-green)" }}
                >
                  {e.amount < 0 ? "-" : "+"}€{Math.abs(e.amount).toFixed(2)}
                </span>
              </motion.div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
