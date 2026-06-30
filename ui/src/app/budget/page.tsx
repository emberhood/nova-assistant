"use client";

import { motion } from "framer-motion";
import { useNovaStore } from "@/lib/store";
import MetricCard from "@/components/budget/metric-card";
import type { BudgetSummaryAvailable } from "@/lib/types";

const MOCK_DATA: BudgetSummaryAvailable = {
  available: true,
  totalBalance: 0,
  monthIncome: 0,
  monthExpenses: 0,
  accounts: [{ name: "Main", balance: 0 }],
  recentExpenses: [],
};

function fmt(n: number | null | undefined) {
  if (n == null) return "—";
  return `€${Math.abs(n).toLocaleString("el-GR", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}

export default function BudgetPage() {
  const budgetData = useNovaStore((s) => s.budgetData);

  if (budgetData && !budgetData.available) {
    return (
      <div className="panel gap-4">
        <div className="glass flex flex-1 flex-col items-center justify-center gap-4 p-[60px] text-center text-sm text-nova-text-mid">
          <span className="text-nova-red">◈ Budget database offline</span>
          <p>Start the Vibe-Budgeting server and ensure the database path is configured.</p>
        </div>
      </div>
    );
  }

  const isMock = budgetData === null;
  const display = budgetData?.available ? budgetData : MOCK_DATA;

  const netMonth = display.monthIncome + display.monthExpenses;
  const savingsRate = display.monthIncome > 0 ? (netMonth / display.monthIncome) * 100 : null;

  return (
    <div className="panel gap-4">
      {isMock && (
        <div className="rounded-sm border border-nova-orange/20 bg-nova-orange/8 px-4 py-2 font-heading text-[11px] tracking-[0.05em] text-nova-orange">
          <span>◈ Backend offline — start the Nova backend to connect Vibe-Budgeting</span>
        </div>
      )}

      {/* Header metrics */}
      <div className="grid grid-cols-4 gap-3.5">
        <MetricCard label="Total Balance" value={fmt(display.totalBalance)} color="accent" icon="◈" delay={0} />
        <MetricCard label="Month Income" value={fmt(display.monthIncome)} color="green" icon="▲" delay={0.05} />
        <MetricCard label="Month Expenses" value={fmt(display.monthExpenses)} color="red" icon="▼" delay={0.1} />
        <MetricCard
          label="Net this month"
          value={fmt(netMonth)}
          color={netMonth >= 0 ? "green" : "red"}
          icon={netMonth >= 0 ? "◆" : "◇"}
          delay={0.15}
        />
      </div>

      <div className="grid min-h-0 flex-1 grid-cols-[1fr_1.6fr] gap-3.5">
        {/* Accounts */}
        <motion.div
          className="glass flex flex-col gap-3 px-[22px] py-5"
          initial={{ opacity: 0, x: -16 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ delay: 0.2 }}
        >
          <p className="section-title">Accounts</p>
          <div className="flex flex-col gap-2">
            {display.accounts.map((a, i) => (
              <div
                key={i}
                className="flex items-center gap-2.5 rounded-sm border border-nova-border bg-nova-cyan/[0.04] px-3 py-2.5"
              >
                <div className="h-1.5 w-1.5 flex-shrink-0 rounded-full bg-nova-cyan" />
                <span className="flex-1 text-[13px] text-nova-text-mid">{a.name}</span>
                <span
                  className="font-heading text-[13px] font-semibold"
                  style={{ color: a.balance >= 0 ? "var(--nova-green)" : "var(--nova-red)" }}
                >
                  {fmt(a.balance)}
                </span>
              </div>
            ))}
          </div>
          {savingsRate !== null && (
            <div className="mt-1">
              <div className="mb-1.5 flex justify-between font-heading text-[11px] tracking-[0.05em] text-nova-text-dim">
                <span>Savings rate</span>
                <span style={{ color: savingsRate >= 0 ? "var(--nova-green)" : "var(--nova-red)" }}>
                  {savingsRate.toFixed(1)}%
                </span>
              </div>
              <div className="h-1 overflow-hidden rounded-full bg-white/5">
                <motion.div
                  className="h-full rounded-full opacity-80"
                  style={{ background: savingsRate >= 0 ? "var(--nova-green)" : "var(--nova-red)" }}
                  initial={{ width: 0 }}
                  animate={{ width: `${Math.min(100, Math.max(0, Math.abs(savingsRate)))}%` }}
                  transition={{ delay: 0.4, duration: 0.8, ease: "easeOut" }}
                />
              </div>
            </div>
          )}
        </motion.div>

        {/* Recent transactions */}
        <motion.div
          className="glass overflow-y-auto px-[22px] py-5"
          initial={{ opacity: 0, x: 16 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ delay: 0.25 }}
        >
          <p className="section-title">Recent Expenses</p>
          {display.recentExpenses.length === 0 && (
            <p className="text-[13px] text-nova-text-dim">No expenses recorded yet.</p>
          )}
          <div className="flex flex-col gap-[7px]">
            {display.recentExpenses.map((e, i) => (
              <motion.div
                key={i}
                className="flex items-center justify-between gap-3 rounded-sm border border-transparent bg-nova-cyan/3 px-3 py-2.5 transition-colors hover:border-nova-border hover:bg-nova-cyan/6"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={{ delay: 0.3 + i * 0.05 }}
              >
                <div className="flex min-w-0 flex-1 items-center gap-2.5">
                  <span className="tag tag-cyan">{e.category || "Other"}</span>
                  <span className="truncate text-[13px] text-nova-text-mid">{e.notes || "—"}</span>
                </div>
                <div className="flex flex-shrink-0 flex-col items-end gap-[3px]">
                  <span className="font-heading text-[10px] text-nova-text-dim">{e.date.slice(0, 10)}</span>
                  <span
                    className="font-heading text-[13px] font-semibold"
                    style={{ color: e.amount < 0 ? "var(--nova-red)" : "var(--nova-green)" }}
                  >
                    {e.amount < 0 ? "-" : "+"}€{Math.abs(e.amount).toFixed(2)}
                  </span>
                </div>
              </motion.div>
            ))}
          </div>
        </motion.div>
      </div>

      <div className="glass flex items-center gap-1.5 px-5 py-2.5">
        <span className="text-[11px] text-nova-text-dim">Data from Vibe-Budgeting ·</span>
        <a
          href="http://localhost:5000"
          target="_blank"
          rel="noreferrer"
          className="font-heading text-[11px] tracking-[0.05em] text-nova-cyan transition-all duration-200 hover:[text-shadow:0_0_10px_var(--nova-cyan)]"
        >
          Open full app ↗
        </a>
      </div>
    </div>
  );
}
