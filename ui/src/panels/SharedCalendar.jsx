import { useState, useEffect } from 'react'
import { motion } from 'framer-motion'
import './SharedCalendar.css'

const MONTH_NAMES = ['January','February','March','April','May','June',
                     'July','August','September','October','November','December']
const DAY_NAMES = ['Mon','Tue','Wed','Thu','Fri','Sat','Sun']

function buildLocalCalendar(year, month) {
  const today = new Date()
  const todayStr = today.toISOString().slice(0, 10)
  const firstDay = new Date(year, month - 1, 1).getDay()
  const offset = (firstDay + 6) % 7
  const daysInMonth = new Date(year, month, 0).getDate()
  const prevDays = new Date(year, month - 1, 0).getDate()
  const cells = []
  for (let i = offset - 1; i >= 0; i--) {
    const d = prevDays - i
    const pm = month - 1 === 0 ? 12 : month - 1
    const py = month - 1 === 0 ? year - 1 : year
    const dateStr = `${py}-${String(pm).padStart(2,'0')}-${String(d).padStart(2,'0')}`
    cells.push({ date: dateStr, day: d, isCurrentMonth: false, isToday: false, isWeekend: false, events: [] })
  }
  for (let d = 1; d <= daysInMonth; d++) {
    const dateStr = `${year}-${String(month).padStart(2,'0')}-${String(d).padStart(2,'0')}`
    const wd = new Date(year, month - 1, d).getDay()
    cells.push({ date: dateStr, day: d, isCurrentMonth: true, isToday: dateStr === todayStr, isWeekend: wd === 0 || wd === 6, events: [] })
  }
  while (cells.length % 7 !== 0) {
    const nm = month === 12 ? 1 : month + 1
    const ny = month === 12 ? year + 1 : year
    const d = cells.length - (offset + daysInMonth) + 1
    const dateStr = `${ny}-${String(nm).padStart(2,'0')}-${String(d).padStart(2,'0')}`
    cells.push({ date: dateStr, day: d, isCurrentMonth: false, isToday: false, isWeekend: false, events: [] })
  }
  const weeks = []
  for (let i = 0; i < cells.length; i += 7) weeks.push(cells.slice(i, i + 7))
  return { weeks, monthName: MONTH_NAMES[month - 1], year, month }
}

function chunkWeeks(cells) {
  const weeks = []
  for (let i = 0; i < cells.length; i += 7) weeks.push(cells.slice(i, i + 7))
  return weeks
}

export default function SharedCalendar({ calData, setCalData }) {
  const today = new Date()
  const [year, setYear]   = useState(today.getFullYear())
  const [month, setMonth] = useState(today.getMonth() + 1)
  const [selected, setSelected] = useState(null)

  const fetchMonth = (y, m) => {
    fetch(`/api/calendar/month?year=${y}&month=${m}&user=shared`)
      .then(r => r.json())
      .then(d => setCalData?.(d))
      .catch(() => setCalData?.(buildLocalCalendar(y, m)))
  }

  // Fetch only when navigating to a different month (current month comes from prop/cache)
  useEffect(() => {
    const isCurrentMonth = year === today.getFullYear() && month === today.getMonth() + 1
    if (!isCurrentMonth) fetchMonth(year, month)
  }, [year, month])

  const prevMonth = () => {
    const nm = month === 1 ? 12 : month - 1
    const ny = month === 1 ? year - 1 : year
    setYear(ny); setMonth(nm); setSelected(null)
  }
  const nextMonth = () => {
    const nm = month === 12 ? 1 : month + 1
    const ny = month === 12 ? year + 1 : year
    setYear(ny); setMonth(nm); setSelected(null)
  }

  const data = calData || buildLocalCalendar(year, month)
  const weeks = data.weeks || chunkWeeks(data.cells || [])
  const todayStr = today.toISOString().slice(0, 10)

  // collect upcoming shared events (next 14 days)
  const upcoming = []
  if (calData?.weeks) {
    for (const week of calData.weeks) {
      for (const d of week) {
        if (d.date >= todayStr && d.events?.length > 0) {
          d.events.forEach(ev => upcoming.push({ ...ev, date: d.date }))
        }
      }
    }
  }
  upcoming.sort((a, b) => a.date.localeCompare(b.date))

  return (
    <div className="panel shared-cal">

      {/* Header */}
      <div className="shared-header glass-strong">
        <div className="shared-title-area">
          <span className="shared-heart">♡</span>
          <div>
            <div className="shared-title">Shared Calendar</div>
            <div className="shared-sub">Events you plan together</div>
          </div>
        </div>

        <div className="cal-nav">
          <button className="cal-nav-btn" onClick={prevMonth}>‹</button>
          <span className="cal-month-label">{data.monthName || MONTH_NAMES[month-1]} {year}</span>
          <button className="cal-nav-btn" onClick={nextMonth}>›</button>
        </div>
      </div>

      <div className="shared-body">
        {/* Calendar grid */}
        <div className="shared-grid-wrap glass">
          <div className="cal-weekdays">
            {DAY_NAMES.map(d => <div key={d} className="cal-weekday">{d}</div>)}
          </div>
          <div className="cal-grid">
            {weeks.map((week, wi) =>
              week.map((day, di) => {
                const isSelected = selected === day.date
                const hasEvents = day.events?.length > 0
                return (
                  <motion.div
                    key={day.date}
                    className={[
                      'cal-day',
                      day.isToday      ? 'today'       : '',
                      !day.isCurrentMonth ? 'other-month' : '',
                      day.isWeekend    ? 'weekend'     : '',
                      isSelected       ? 'selected'    : '',
                      hasEvents        ? 'has-events'  : '',
                    ].join(' ')}
                    onClick={() => setSelected(isSelected ? null : day.date)}
                    initial={{ opacity: 0, scale: 0.9 }}
                    animate={{ opacity: 1, scale: 1 }}
                    transition={{ delay: (wi * 7 + di) * 0.008 }}
                  >
                    <span className="cal-day-num">{day.day}</span>
                    {hasEvents && (
                      <div className="shared-event-dots">
                        {day.events.slice(0, 3).map((_, i) => (
                          <span key={i} className="shared-dot" />
                        ))}
                      </div>
                    )}
                    {isSelected && hasEvents && (
                      <div className="day-events-popup">
                        {day.events.map((ev, i) => (
                          <div key={i} className="day-event-item">
                            <span className="day-event-time">{ev.time}</span>
                            <span className="day-event-title">{ev.title}</span>
                          </div>
                        ))}
                      </div>
                    )}
                  </motion.div>
                )
              })
            )}
          </div>
        </div>

        {/* Upcoming events sidebar */}
        <div className="shared-upcoming glass">
          <p className="section-title">Upcoming Together</p>
          {upcoming.length === 0 ? (
            <div className="shared-empty">
              <span>No upcoming shared events</span>
            </div>
          ) : (
            <div className="upcoming-list">
              {upcoming.slice(0, 8).map((ev, i) => {
                const d = new Date(ev.date + 'T00:00:00')
                const isToday = ev.date === todayStr
                return (
                  <motion.div
                    key={i}
                    className={`upcoming-item ${isToday ? 'today' : ''}`}
                    initial={{ opacity: 0, x: 10 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ delay: i * 0.06 }}
                  >
                    <div className="upcoming-date-col">
                      <span className="upcoming-day">{d.toLocaleDateString('en', { weekday: 'short' })}</span>
                      <span className="upcoming-num">{d.getDate()}</span>
                    </div>
                    <div className="upcoming-info">
                      <div className="upcoming-title">{ev.title}</div>
                      {ev.time !== 'all day' && (
                        <div className="upcoming-time">{ev.time}</div>
                      )}
                    </div>
                    {isToday && <span className="tag tag-shared">TODAY</span>}
                  </motion.div>
                )
              })}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
