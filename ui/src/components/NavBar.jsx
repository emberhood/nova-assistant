import { motion } from 'framer-motion'
import './NavBar.css'

const NAV_ITEMS = [
  { id: 'dashboard', label: 'Dashboard', icon: '⬡' },
  { id: 'calendar',  label: 'Calendar',  icon: '◫' },
  { id: 'budget',    label: 'Budget',    icon: '◈' },
]

const STATE_COLORS = {
  idle:      'var(--text-dim)',
  listening: 'var(--green)',
  speaking:  'var(--accent)',
  processing:'var(--accent2)',
}

const STATE_LABELS = {
  idle:       'STANDBY',
  listening:  'LISTENING',
  speaking:   'SPEAKING',
  processing: 'PROCESSING',
}

const USERS = [
  { id: 'owner',    label: 'Marios',       initial: 'J', color: '#00d4ff' },
  { id: 'andriana', label: 'Andriana', initial: 'A', color: '#f472b6' },
  { id: 'shared',   label: 'Shared',   initial: '♡', color: '#fbbf24' },
]

export default function NavBar({ active, navigate, jarvisState, activeUser, setActiveUser }) {
  return (
    <nav className="navbar glass-strong">
      <div className="navbar-brand">
        <span className="brand-j">J</span>
        <span className="brand-rest">ARVIS</span>
        <span className="brand-ver">v1.0</span>
      </div>

      <div className="navbar-items">
        {NAV_ITEMS.map(item => {
          // hide Budget on shared view (no shared budget)
          if (item.id === 'budget' && activeUser === 'shared') return null
          return (
            <button
              key={item.id}
              className={`nav-item ${active === item.id ? 'active' : ''}`}
              onClick={() => navigate(item.id)}
            >
              <span className="nav-icon">{item.icon}</span>
              <span className="nav-label">{item.label}</span>
              {active === item.id && (
                <motion.div
                  className="nav-indicator"
                  layoutId="nav-indicator"
                  transition={{ type: 'spring', stiffness: 400, damping: 35 }}
                />
              )}
            </button>
          )
        })}
      </div>

      {/* User switcher */}
      <div className="user-switcher">
        {USERS.map(u => (
          <button
            key={u.id}
            className={`user-pill ${activeUser === u.id ? 'active' : ''}`}
            style={{ '--pill-color': u.color }}
            onClick={() => setActiveUser(u.id)}
            title={u.label}
          >
            <span className="user-initial">{u.initial}</span>
            <span className="user-name">{u.label}</span>
          </button>
        ))}
      </div>

      <div className="navbar-status">
        <motion.div
          className="status-dot"
          animate={{ backgroundColor: STATE_COLORS[jarvisState], boxShadow: `0 0 8px ${STATE_COLORS[jarvisState]}` }}
          transition={{ duration: 0.3 }}
        />
        <span className="status-label" style={{ color: STATE_COLORS[jarvisState] }}>
          {STATE_LABELS[jarvisState] || 'STANDBY'}
        </span>
      </div>
    </nav>
  )
}
