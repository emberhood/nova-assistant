"use client";

import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import { useNovaStore } from "@/lib/store";
import { fetchCalendarMonth } from "@/lib/api";
import type { CalendarDay, CalendarEvent, CalendarMonth, CalendarWeek } from "@/lib/types";

const MONTH_NAMES = [
  "January", "February", "March", "April", "May", "June",
  "July", "August", "September", "October", "November", "December",
];
const DAY_NAMES = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];

function buildLocalCalendar(year: number, month: number): CalendarMonth {
  const today = new Date();
  const todayStr = today.toISOString().slice(0, 10);
  const firstDay = new Date(year, month - 1, 1).getDay();
  const offset = (firstDay + 6) % 7;
  const daysInMonth = new Date(year, month, 0).getDate();
  const prevDays = new Date(year, month - 1, 0).getDate();
  const cells: CalendarDay[] = [];

  for (let i = offset - 1; i >= 0; i--) {
    const d = prevDays - i;
    const pm = month - 1 === 0 ? 12 : month - 1;
    const py = month - 1 === 0 ? year - 1 : year;
    const dateStr = `${py}-${String(pm).padStart(2, "0")}-${String(d).padStart(2, "0")}`;
    cells.push({ date: dateStr, day: d, month: pm, year: py, isCurrentMonth: false, isToday: false, isWeekend: false, events: [] });
  }
  for (let d = 1; d <= daysInMonth; d++) {
    const dateStr = `${year}-${String(month).padStart(2, "0")}-${String(d).padStart(2, "0")}`;
    const wd = new Date(year, month - 1, d).getDay();
    cells.push({ date: dateStr, day: d, month, year, isCurrentMonth: true, isToday: dateStr === todayStr, isWeekend: wd === 0 || wd === 6, events: [] });
  }
  while (cells.length % 7 !== 0) {
    const nm = month === 12 ? 1 : month + 1;
    const ny = month === 12 ? year + 1 : year;
    const d = cells.length - (offset + daysInMonth) + 1;
    const dateStr = `${ny}-${String(nm).padStart(2, "0")}-${String(d).padStart(2, "0")}`;
    cells.push({ date: dateStr, day: d, month: nm, year: ny, isCurrentMonth: false, isToday: false, isWeekend: false, events: [] });
  }

  const weeks: CalendarWeek[] = [];
  for (let i = 0; i < cells.length; i += 7) weeks.push(cells.slice(i, i + 7));

  return { weeks, monthName: MONTH_NAMES[month - 1], year, month, today: todayStr, user: "shared" };
}

interface UpcomingEvent extends CalendarEvent {
  date: string;
}

export default function SharedCalendar() {
  const calData = useNovaStore((s) => s.calData);
  const setCalData = useNovaStore((s) => s.setCalData);

  const today = new Date();
  const [year, setYear] = useState(today.getFullYear());
  const [month, setMonth] = useState(today.getMonth() + 1);
  const [selected, setSelected] = useState<string | null>(null);

  // Fetch only when navigating to a different month (current month comes from prop/cache)
  useEffect(() => {
    const now = new Date();
    const isCurrentMonth = year === now.getFullYear() && month === now.getMonth() + 1;
    if (isCurrentMonth) return;

    fetchCalendarMonth(year, month, "shared")
      .then((d) => setCalData(d, "shared"))
      .catch(() => setCalData(buildLocalCalendar(year, month), "shared"));
  }, [year, month, setCalData]);

  const prevMonth = () => {
    const nm = month === 1 ? 12 : month - 1;
    const ny = month === 1 ? year - 1 : year;
    setYear(ny);
    setMonth(nm);
    setSelected(null);
  };
  const nextMonth = () => {
    const nm = month === 12 ? 1 : month + 1;
    const ny = month === 12 ? year + 1 : year;
    setYear(ny);
    setMonth(nm);
    setSelected(null);
  };

  const data = calData ?? buildLocalCalendar(year, month);
  const weeks = data.weeks;
  const todayStr = today.toISOString().slice(0, 10);

  // collect upcoming shared events (next 14 days)
  const upcoming: UpcomingEvent[] = [];
  if (calData) {
    for (const week of calData.weeks) {
      for (const d of week) {
        if (d.date >= todayStr && d.events.length > 0) {
          for (const ev of d.events) upcoming.push({ ...ev, date: d.date });
        }
      }
    }
  }
  upcoming.sort((a, b) => a.date.localeCompare(b.date));

  return (
    <div className="panel gap-4 overflow-hidden">
      {/* Header */}
      <div className="glass-strong flex items-center justify-between px-7 py-5">
        <div className="flex items-center gap-3.5">
          <span
            className="animate-[heartbeat_2s_ease-in-out_infinite] text-[32px] text-nova-cyan"
            style={{ textShadow: "0 0 20px var(--nova-glow-1)" }}
          >
            ♡
          </span>
          <div>
            <div className="font-heading text-base font-bold tracking-[0.1em] text-nova-cyan">Shared Calendar</div>
            <div className="mt-0.5 text-[11px] tracking-[0.05em] text-nova-text-dim">Events you plan together</div>
          </div>
        </div>

        <div className="flex items-center gap-4">
          <button
            className="flex h-[30px] w-[30px] items-center justify-center rounded-full border border-nova-border bg-white/[0.04] text-lg text-nova-text-mid transition-colors hover:border-nova-cyan hover:text-nova-cyan"
            onClick={prevMonth}
          >
            ‹
          </button>
          <span className="min-w-[160px] text-center font-heading text-[13px] font-bold tracking-[0.1em] text-nova-text">
            {data.monthName || MONTH_NAMES[month - 1]} {year}
          </span>
          <button
            className="flex h-[30px] w-[30px] items-center justify-center rounded-full border border-nova-border bg-white/[0.04] text-lg text-nova-text-mid transition-colors hover:border-nova-cyan hover:text-nova-cyan"
            onClick={nextMonth}
          >
            ›
          </button>
        </div>
      </div>

      <div className="grid min-h-0 flex-1 grid-cols-[1fr_260px] gap-4 overflow-hidden">
        {/* Calendar grid */}
        <div className="glass flex flex-col gap-2 p-[18px]">
          <div className="mb-1 grid grid-cols-7 gap-1">
            {DAY_NAMES.map((d) => (
              <div key={d} className="text-center font-heading text-[9px] uppercase tracking-[0.12em] text-nova-text-dim">
                {d}
              </div>
            ))}
          </div>
          <div className="grid flex-1 grid-cols-7 gap-1">
            {weeks.map((week, wi) =>
              week.map((day, di) => {
                const isSelected = selected === day.date;
                const hasEvents = day.events.length > 0;

                let stateClasses: string;
                if (isSelected) {
                  stateClasses = "z-10 border-nova-violet bg-nova-violet/12";
                } else if (day.isToday) {
                  stateClasses =
                    "border-nova-cyan shadow-[0_0_12px_var(--nova-glow-1),inset_0_0_12px_var(--nova-glow-1)]";
                } else if (hasEvents) {
                  stateClasses = "border-nova-cyan/20 bg-nova-cyan/8";
                } else {
                  stateClasses = "border-transparent hover:border-nova-border hover:bg-white/[0.04]";
                }

                const numColorClass = day.isToday
                  ? "text-nova-cyan"
                  : day.isWeekend
                    ? "text-nova-violet"
                    : "text-nova-text";

                return (
                  <motion.div
                    key={day.date}
                    className={`relative flex aspect-square cursor-pointer flex-col items-center justify-start overflow-visible rounded-sm border pt-1.5 transition-all ${stateClasses}`}
                    onClick={() => setSelected(isSelected ? null : day.date)}
                    initial={{ opacity: 0, scale: 0.9 }}
                    animate={{ opacity: 1, scale: 1 }}
                    transition={{ delay: (wi * 7 + di) * 0.008 }}
                  >
                    <span
                      className={`font-heading text-[11px] font-semibold ${numColorClass} ${
                        day.isCurrentMonth ? "" : "opacity-20"
                      }`}
                      style={day.isToday ? { textShadow: "0 0 8px var(--nova-cyan)" } : undefined}
                    >
                      {day.day}
                    </span>
                    {hasEvents && (
                      <div className="mt-[3px] flex gap-0.5">
                        {day.events.slice(0, 3).map((_, i) => (
                          <span key={i} className="h-1 w-1 rounded-full bg-nova-cyan shadow-[0_0_4px_var(--nova-cyan)]" />
                        ))}
                      </div>
                    )}
                    {isSelected && hasEvents && (
                      <div className="absolute left-1/2 top-[calc(100%+4px)] z-20 min-w-[140px] max-w-[200px] -translate-x-1/2 rounded-sm border border-nova-cyan bg-nova-bg-2 px-2 py-1.5 shadow-[0_4px_20px_rgba(0,0,0,0.6)]">
                        {day.events.map((ev, i) => (
                          <div key={i} className="flex items-baseline gap-1.5 py-0.5 text-[10px]">
                            <span className="flex-shrink-0 font-heading text-[9px] text-nova-cyan">{ev.time}</span>
                            <span className="text-nova-text">{ev.title}</span>
                          </div>
                        ))}
                      </div>
                    )}
                  </motion.div>
                );
              }),
            )}
          </div>
        </div>

        {/* Upcoming events sidebar */}
        <div className="glass flex flex-col gap-3 overflow-y-auto p-[18px]">
          <p className="section-title">Upcoming Together</p>
          {upcoming.length === 0 ? (
            <div className="flex flex-1 items-center justify-center text-xs italic text-nova-text-dim">
              <span>No upcoming shared events</span>
            </div>
          ) : (
            <div className="flex flex-col gap-2">
              {upcoming.slice(0, 8).map((ev, i) => {
                const d = new Date(`${ev.date}T00:00:00`);
                const isToday = ev.date === todayStr;
                return (
                  <motion.div
                    key={i}
                    className={`flex items-center gap-2.5 rounded-sm border px-2.5 py-2.5 transition-colors ${
                      isToday
                        ? "border-nova-cyan bg-nova-cyan/8"
                        : "border-nova-border bg-white/[0.03] hover:border-nova-cyan/30 hover:bg-white/[0.05]"
                    }`}
                    initial={{ opacity: 0, x: 10 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ delay: i * 0.06 }}
                  >
                    <div className="flex min-w-[32px] flex-col items-center">
                      <span className="font-heading text-[8px] uppercase tracking-[0.12em] text-nova-text-dim">
                        {d.toLocaleDateString("en", { weekday: "short" })}
                      </span>
                      <span className="font-heading text-lg font-bold leading-[1.1] text-nova-cyan">{d.getDate()}</span>
                    </div>
                    <div className="min-w-0 flex-1">
                      <div className="truncate text-xs text-nova-text">{ev.title}</div>
                      {ev.time !== "all day" && (
                        <div className="mt-0.5 font-heading text-[9px] text-nova-text-dim">{ev.time}</div>
                      )}
                    </div>
                    {isToday && (
                      <span className="tag border border-nova-cyan/40 bg-nova-cyan/15 text-nova-cyan">TODAY</span>
                    )}
                  </motion.div>
                );
              })}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
