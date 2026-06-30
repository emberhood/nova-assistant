"use client";

import { useEffect, useMemo, useState } from "react";
import { motion } from "framer-motion";
import { useNovaStore } from "@/lib/store";
import { fetchCalendarMonth } from "@/lib/api";
import type { CalendarEvent, CalendarMonth } from "@/lib/types";

const DAY_GR = ["Κυριακή", "Δευτέρα", "Τρίτη", "Τετάρτη", "Πέμπτη", "Παρασκευή", "Σάββατο"];
const MON_GR = [
  "Ιανουάριος", "Φεβρουάριος", "Μάρτιος", "Απρίλιος", "Μάιος", "Ιούνιος",
  "Ιούλιος", "Αύγουστος", "Σεπτέμβριος", "Οκτώβριος", "Νοέμβριος", "Δεκέμβριος",
];

function isoToday() {
  return new Date().toISOString().slice(0, 10);
}

function addDays(isoDate: string, n: number) {
  const d = new Date(`${isoDate}T12:00:00`);
  d.setDate(d.getDate() + n);
  return d.toISOString().slice(0, 10);
}

function dayLabel(isoDate: string) {
  const d = new Date(`${isoDate}T12:00:00`);
  const today = isoToday();
  const tomorrow = addDays(today, 1);
  if (isoDate === today) return "Σήμερα";
  if (isoDate === tomorrow) return "Αύριο";
  return `${DAY_GR[d.getDay()]} ${d.getDate()} ${MON_GR[d.getMonth()]}`;
}

function sortEvents(evs: CalendarEvent[]) {
  return [...evs].sort((a, b) =>
    a.time === "all day" ? -1 : b.time === "all day" ? 1 : a.time.localeCompare(b.time),
  );
}

function EventRow({ ev, accent, isToday }: { ev: CalendarEvent; accent: string; isToday: boolean }) {
  return (
    <div
      className={`flex items-baseline gap-3.5 rounded-sm border px-3.5 py-2 ${
        isToday ? "border-nova-cyan/12 bg-nova-cyan/5" : "border-white/[0.06] bg-white/[0.03]"
      }`}
      style={{ borderLeftWidth: 2, borderLeftColor: accent }}
    >
      <span
        className="min-w-[68px] flex-shrink-0 whitespace-nowrap font-heading text-xs font-semibold"
        style={{ color: accent }}
      >
        {ev.time === "all day" ? "Ολοήμερο" : ev.time}
      </span>
      <span className="text-[13px] leading-snug text-nova-text">{ev.title}</span>
    </div>
  );
}

export default function CalendarPage() {
  const calData = useNovaStore((s) => s.calData);
  const setCalData = useNovaStore((s) => s.setCalData);
  const activeUser = useNovaStore((s) => s.activeUser);

  const [loading, setLoading] = useState(false);
  const [extraData, setExtraData] = useState<CalendarMonth | null>(null);

  const today = isoToday();

  // Build a flat map: { "YYYY-MM-DD": [{title, time}, ...] }
  const eventMap = useMemo(() => {
    const map: Record<string, CalendarEvent[]> = {};
    const addFrom = (data: CalendarMonth | null) => {
      if (!data) return;
      for (const week of data.weeks) {
        for (const day of week) {
          if (day.events.length) {
            map[day.date] = (map[day.date] || []).concat(day.events);
          }
        }
      }
    };
    addFrom(calData);
    addFrom(extraData);
    return map;
  }, [calData, extraData]);

  // Next 14 days starting from today
  const days = useMemo(() => Array.from({ length: 14 }, (_, i) => addDays(today, i)), [today]);

  // Fetch next month if the 14-day window crosses a month boundary
  useEffect(() => {
    const lastDay = days[13];
    const lastMonth = parseInt(lastDay.slice(5, 7), 10);
    const todayMonth = parseInt(today.slice(5, 7), 10);
    if (lastMonth !== todayMonth && !extraData) {
      const y = parseInt(lastDay.slice(0, 4), 10);
      fetchCalendarMonth(y, lastMonth, activeUser).then(setExtraData).catch(() => {});
    }
  }, [days, today, extraData, activeUser]);

  const refresh = async () => {
    setLoading(true);
    setExtraData(null);
    const t = new Date();
    try {
      const data = await fetchCalendarMonth(t.getFullYear(), t.getMonth() + 1, activeUser);
      setCalData(data, activeUser);
    } catch {
      // offline — keep showing whatever we have
    }
    setLoading(false);
  };

  const hasData = !!calData?.weeks?.length;

  return (
    <div className="panel gap-3.5">
      {/* Header */}
      <div className="glass-strong flex flex-shrink-0 items-center gap-3 px-6 py-4">
        <div className="flex flex-1 items-baseline gap-2.5">
          <span className="font-heading text-xl font-bold tracking-[0.05em] text-nova-text">Πρόγραμμα</span>
          <span className="font-heading text-xs tracking-[0.04em] text-nova-text-dim">επόμενες 2 εβδομάδες</span>
          {!hasData && (
            <span className="rounded-full border border-[rgba(255,80,80,0.3)] bg-[rgba(255,80,80,0.12)] px-2 py-0.5 text-[10px] tracking-[0.05em] text-[#ff5555]">
              iCloud offline
            </span>
          )}
        </div>
        <button
          className="flex h-[34px] w-[34px] items-center justify-center rounded-sm border border-nova-border text-base text-nova-text-mid transition-colors hover:border-nova-cyan hover:text-nova-cyan disabled:cursor-default disabled:opacity-40"
          onClick={() => {
            void refresh();
          }}
          title="Sync"
          disabled={loading}
        >
          {loading ? "…" : "↻"}
        </button>
      </div>

      {/* Agenda list */}
      <div className="glass-strong flex flex-1 flex-col overflow-y-auto py-2">
        {days.map((iso, i) => {
          const evs = eventMap[iso] || [];
          const isToday = iso === today;
          const d = new Date(`${iso}T12:00:00`);
          const isWeekend = d.getDay() === 0 || d.getDay() === 6;

          const rowClasses = [
            "border-b border-b-white/[0.04] px-6 py-3.5 transition-colors last:border-b-0",
            isWeekend ? "bg-nova-violet/3" : isToday ? "bg-nova-cyan/5" : "hover:bg-white/[0.01]",
            isToday ? "border-l-2 border-l-nova-cyan pl-[22px]" : "",
          ].join(" ");

          return (
            <motion.div
              key={iso}
              className={rowClasses}
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: i * 0.03, duration: 0.25 }}
            >
              {/* Day label row */}
              <div className="mb-2 flex items-center justify-between">
                <div className="flex items-center gap-2">
                  {isToday && (
                    <span className="h-2 w-2 flex-shrink-0 animate-pulse rounded-full bg-nova-cyan shadow-[0_0_8px_var(--nova-glow-1)]" />
                  )}
                  <span
                    className={`font-heading text-[13px] font-semibold tracking-[0.04em] ${
                      isToday ? "text-nova-cyan" : isWeekend ? "text-nova-violet/85" : "text-nova-text"
                    }`}
                  >
                    {dayLabel(iso)}
                  </span>
                  {isToday && (
                    <span className="rounded-full border border-nova-cyan/30 bg-nova-cyan/15 px-[7px] py-0.5 font-heading text-[9px] tracking-[0.12em] text-nova-cyan">
                      TODAY
                    </span>
                  )}
                </div>
                {evs.length > 0 && (
                  <span className="font-heading text-[10px] tracking-[0.05em] text-nova-text-dim">
                    {evs.length} event{evs.length > 1 ? "s" : ""}
                  </span>
                )}
              </div>

              {/* Events — today always expanded, others always visible */}
              {evs.length > 0 ? (
                <div className="flex flex-col gap-1.5">
                  {sortEvents(evs).map((ev, ei) => (
                    <EventRow
                      key={ei}
                      ev={ev}
                      isToday={isToday}
                      accent={isToday ? "var(--nova-cyan)" : isWeekend ? "var(--nova-violet)" : "var(--nova-text-dim)"}
                    />
                  ))}
                </div>
              ) : (
                <div className="pl-1 text-xs text-nova-text-dim opacity-35">—</div>
              )}
            </motion.div>
          );
        })}
      </div>
    </div>
  );
}
