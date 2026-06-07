import { useState, useEffect, useMemo } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import './CalendarPanel.css'

const DAY_GR = ['Κυριακή','Δευτέρα','Τρίτη','Τετάρτη','Πέμπτη','Παρασκευή','Σάββατο']
const MON_GR = ['Ιανουάριος','Φεβρουάριος','Μάρτιος','Απρίλιος','Μάιος','Ιούνιος',
                'Ιούλιος','Αύγουστος','Σεπτέμβριος','Οκτώβριος','Νοέμβριος','Δεκέμβριος']

function isoToday() {
  return new Date().toISOString().slice(0, 10)
}

function addDays(isoDate, n) {
  const d = new Date(isoDate + 'T12:00:00')
  d.setDate(d.getDate() + n)
  return d.toISOString().slice(0, 10)
}

function dayLabel(isoDate) {
  const d = new Date(isoDate + 'T12:00:00')
  const today = isoToday()
  const tomorrow = addDays(today, 1)
  if (isoDate === today)    return 'Σήμερα'
  if (isoDate === tomorrow) return 'Αύριο'
  return `${DAY_GR[d.getDay()]} ${d.getDate()} ${MON_GR[d.getMonth()]}`
}

function sortEvents(evs) {
  return [...evs].sort((a, b) =>
    a.time === 'all day' ? -1 : b.time === 'all day' ? 1 : a.time.localeCompare(b.time)
  )
}

function EventRow({ ev, accent }) {
  return (
    <div className="agenda-ev" style={{ '--ev-accent': accent }}>
      <span className="agenda-ev-time">
        {ev.time === 'all day' ? 'Ολοήμερο' : ev.time}
      </span>
      <span className="agenda-ev-title">{ev.title}</span>
    </div>
  )
}

export default function CalendarPanel({ calData, setCalData, activeUser }) {
  const [loading, setLoading] = useState(false)
  const [extraData, setExtraData] = useState(null) // next month if needed

  const today = isoToday()

  // Build a flat map: { "YYYY-MM-DD": [{title, time}, ...] }
  const eventMap = useMemo(() => {
    const map = {}
    const addFrom = (data) => {
      if (!data?.weeks) return
      for (const week of data.weeks)
        for (const day of week)
          if (day.events?.length) map[day.date] = (map[day.date] || []).concat(day.events)
    }
    addFrom(calData)
    addFrom(extraData)
    return map
  }, [calData, extraData])

  // Next 14 days starting from today
  const days = useMemo(() =>
    Array.from({ length: 14 }, (_, i) => addDays(today, i)), [today])

  // Fetch next month if the 14-day window crosses a month boundary
  useEffect(() => {
    const lastDay = days[13]
    const lastMonth = parseInt(lastDay.slice(5, 7))
    const todayMonth = parseInt(today.slice(5, 7))
    if (lastMonth !== todayMonth && !extraData) {
      const y = parseInt(lastDay.slice(0, 4))
      const m = lastMonth
      fetch(`/api/calendar/month?year=${y}&month=${m}&user=${activeUser}`)
        .then(r => r.json())
        .then(setExtraData)
        .catch(() => {})
    }
  }, [days, activeUser])

  const refresh = async () => {
    setLoading(true)
    setExtraData(null)
    const t = new Date()
    try {
      const r = await fetch(`/api/calendar/month?year=${t.getFullYear()}&month=${t.getMonth()+1}&user=${activeUser}`)
      setCalData(await r.json())
    } catch {}
    setLoading(false)
  }

  const hasData = !!calData?.weeks?.length

  return (
    <div className="panel cal-panel">

      {/* Header */}
      <div className="cal-header glass-strong">
        <div className="cal-title-area">
          <span className="cal-month-name">Πρόγραμμα</span>
          <span className="cal-year">επόμενες 2 εβδομάδες</span>
          {!hasData && <span className="cal-offline-badge">iCloud offline</span>}
        </div>
        <button className="cal-nav-btn cal-refresh-btn" onClick={refresh}
          title="Sync" disabled={loading}>
          {loading ? '…' : '↻'}
        </button>
      </div>

      {/* Agenda list */}
      <div className="agenda-scroll glass-strong">
        {days.map((iso, i) => {
          const evs = eventMap[iso] || []
          const isToday = iso === today
          const d = new Date(iso + 'T12:00:00')
          const isWeekend = d.getDay() === 0 || d.getDay() === 6

          return (
            <motion.div
              key={iso}
              className={['agenda-day', isToday ? 'is-today' : '', isWeekend ? 'is-weekend' : ''].join(' ')}
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: i * 0.03, duration: 0.25 }}
            >
              {/* Day label row */}
              <div className="agenda-day-header">
                <div className="agenda-day-label">
                  {isToday && <span className="today-dot" />}
                  <span className="agenda-day-name">{dayLabel(iso)}</span>
                  {isToday && <span className="today-badge">TODAY</span>}
                </div>
                {evs.length > 0 && (
                  <span className="agenda-ev-count">{evs.length} event{evs.length > 1 ? 's' : ''}</span>
                )}
              </div>

              {/* Events — today always expanded, others always visible */}
              {evs.length > 0 ? (
                <div className="agenda-ev-list">
                  {sortEvents(evs).map((ev, ei) => (
                    <EventRow key={ei} ev={ev}
                      accent={isToday ? 'var(--accent)' : isWeekend ? 'var(--accent2)' : 'var(--text-dim)'}
                    />
                  ))}
                </div>
              ) : (
                <div className="agenda-empty">—</div>
              )}
            </motion.div>
          )
        })}
      </div>
    </div>
  )
}
