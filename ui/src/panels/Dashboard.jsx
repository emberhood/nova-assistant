import { useState, useEffect, useCallback } from 'react'
import { motion } from 'framer-motion'
import JarvisOrb from '../components/JarvisOrb.jsx'
import './Dashboard.css'

function useClock() {
  const [now, setNow] = useState(new Date())
  useEffect(() => {
    const t = setInterval(() => setNow(new Date()), 1000)
    return () => clearInterval(t)
  }, [])
  return now
}

const DAY_NAMES = ['Sunday','Monday','Tuesday','Wednesday','Thursday','Friday','Saturday']
const MONTH_NAMES = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec']

function pad(n) { return String(n).padStart(2, '0') }

function StatCard({ label, value, sub, color = 'accent', icon }) {
  return (
    <motion.div
      className="stat-card glass"
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
    >
      <div className="stat-icon" style={{ color: `var(--${color})` }}>{icon}</div>
      <div className="stat-body">
        <div className="stat-label">{label}</div>
        <div className="stat-value" style={{ color: `var(--${color})` }}>{value}</div>
        {sub && <div className="stat-sub">{sub}</div>}
      </div>
    </motion.div>
  )
}

function useEnrollStatus() {
  const [status, setStatus] = useState(null)
  useEffect(() => {
    fetch('/api/voice/enroll/status')
      .then(r => r.json())
      .then(setStatus)
      .catch(() => {})
  }, [])
  return status
}

const USER_LABELS = { owner: 'My', andriana: "Andriana's" }

export default function Dashboard({ jarvisState, budgetData, calData, lastHeard, lastResponse, activeUser = 'owner' }) {
  const userLabel = USER_LABELS[activeUser] || 'My'
  const now = useClock()
  const enrollStatus = useEnrollStatus()
  const [enrolling, setEnrolling] = useState(false)

  const startEnroll = useCallback(() => {
    setEnrolling(true)
    fetch('/api/voice/enroll', { method: 'POST' })
      .then(() => setTimeout(() => setEnrolling(false), 14000))
      .catch(() => setEnrolling(false))
  }, [])
  const hh = pad(now.getHours())
  const mm = pad(now.getMinutes())
  const ss = pad(now.getSeconds())
  const dayName  = DAY_NAMES[now.getDay()]
  const dateStr  = `${now.getDate()} ${MONTH_NAMES[now.getMonth()]} ${now.getFullYear()}`

  // next event from calendar
  const todayStr = now.toISOString().slice(0, 10)
  const todayEvents = calData?.weeks?.flat().filter(d => d.date === todayStr) ?? []

  const balance = budgetData?.available ? budgetData.totalBalance.toFixed(2) : '—'
  const monthExp = budgetData?.available ? Math.abs(budgetData.monthExpenses).toFixed(2) : '—'
  const monthInc = budgetData?.available ? budgetData.monthIncome.toFixed(2) : '—'

  return (
    <div className="panel dashboard">
      {/* top row: clock + orb */}
      <div className="dash-hero glass-strong">
        <div className="dash-clock-area">
          <div className="clock-time">
            <span className="clock-hm">{hh}<span className="clock-colon">:</span>{mm}</span>
            <span className="clock-ss">{ss}</span>
          </div>
          <div className="clock-date">
            <span className="clock-dayname">{dayName}</span>
            <span className="clock-datestr">{dateStr}</span>
          </div>
          <div className="clock-divider" />
          <div className="system-tags">
            <span className="tag tag-cyan">SYS ONLINE</span>
            <span className="tag tag-green">AI READY</span>
          </div>
        </div>

        <div className="dash-orb-area">
          <JarvisOrb state={jarvisState} />
          <div className="orb-state-label">
            {jarvisState === 'idle'       && (lastResponse || 'Πες "Hey Jarvis"')}
            {jarvisState === 'listening'  && 'Ακούω...'}
            {jarvisState === 'processing' && 'Επεξεργάζομαι...'}
            {jarvisState === 'speaking'   && 'Μιλάω...'}
          </div>
          {lastHeard && jarvisState === 'idle' && (
            <div className="orb-heard">"{lastHeard}"</div>
          )}
          <button
            className="trigger-btn"
            title="Trigger manually (backend must be running)"
            onClick={() => fetch('/api/voice/trigger', { method: 'POST' }).catch(() => {})}
          >
            ▶ Test trigger
          </button>
        </div>

        <div className="dash-info-area">
          <p className="section-title">System</p>
          <div className="info-rows">
            <InfoRow label="Mode"    value="Active" />
            <InfoRow label="Voice"   value="Whisper" />
            <InfoRow label="AI"      value="Haiku" />
            <InfoRow label="Budget"  value={budgetData?.available ? 'Connected' : 'Offline'} valueColor={budgetData?.available ? 'green' : 'red'} />
            {enrollStatus?.available && (
              <InfoRow
                label="Speaker"
                value={enrollStatus.enrolled ? 'Enrolled' : 'Not enrolled'}
                valueColor={enrollStatus.enrolled ? 'green' : 'accent2'}
              />
            )}
          </div>
          {enrollStatus?.available && (
            <button
              className="trigger-btn"
              style={{ marginTop: 10, width: '100%', opacity: enrolling ? 0.5 : 1 }}
              disabled={enrolling}
              onClick={startEnroll}
              title="Record 12 seconds of your voice to enroll"
            >
              {enrolling ? '● Recording 12s...' : enrollStatus.enrolled ? '↺ Re-enroll voice' : '+ Enroll my voice'}
            </button>
          )}
        </div>
      </div>

      {/* stat cards */}
      <div className="dash-stats">
        <StatCard label={`${userLabel} Balance`}  value={`€${balance}`}   icon="◈" color="accent" />
        <StatCard label="Month Income"           value={`€${monthInc}`}  icon="▲" color="green"  sub="this month" />
        <StatCard label="Month Expenses"         value={`€${monthExp}`}  icon="▼" color="red"    sub="this month" />
        <StatCard label="Upcoming"               value="No events"       icon="◫" color="accent2" sub="today" />
      </div>

      {/* recent activity */}
      {budgetData?.available && budgetData.recentExpenses?.length > 0 && (
        <div className="dash-recent glass">
          <p className="section-title">Recent Transactions</p>
          <div className="recent-list">
            {budgetData.recentExpenses.map((e, i) => (
              <motion.div
                key={i}
                className="recent-row"
                initial={{ opacity: 0, x: -10 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: i * 0.05 }}
              >
                <span className="recent-cat tag tag-cyan">{e.category || 'Other'}</span>
                <span className="recent-notes">{e.notes || '—'}</span>
                <span className="recent-date">{e.date?.slice(0, 10)}</span>
                <span className="recent-amount" style={{ color: e.amount < 0 ? 'var(--red)' : 'var(--green)' }}>
                  {e.amount < 0 ? '-' : '+'}€{Math.abs(e.amount).toFixed(2)}
                </span>
              </motion.div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}

function InfoRow({ label, value, valueColor = 'text' }) {
  return (
    <div className="info-row">
      <span className="info-label">{label}</span>
      <span className="info-value" style={{ color: `var(--${valueColor})` }}>{value}</span>
    </div>
  )
}
