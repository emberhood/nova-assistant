import { useState, useEffect, useRef, Component } from 'react'

class ErrorBoundary extends Component {
  state = { error: null }
  static getDerivedStateFromError(e) { return { error: e } }
  render() {
    if (this.state.error) return (
      <div style={{ padding: 24, color: 'var(--red,#ff5555)', fontFamily: 'monospace', fontSize: 12 }}>
        Panel error: {this.state.error.message}
        <br /><button style={{ marginTop: 8, cursor: 'pointer' }} onClick={() => this.setState({ error: null })}>Retry</button>
      </div>
    )
    return this.props.children
  }
}
import { AnimatePresence, motion } from 'framer-motion'
import NavBar from './components/NavBar.jsx'
import NovaOverlay from './components/NovaOverlay.jsx'
import Dashboard from './panels/Dashboard.jsx'
import CalendarPanel from './panels/CalendarPanel.jsx'
import BudgetPanel from './panels/BudgetPanel.jsx'
import SharedCalendar from './panels/SharedCalendar.jsx'
import './App.css'

const PANELS = ['dashboard', 'calendar', 'budget']

const variants = {
  enter: (dir) => ({ opacity: 0, x: dir > 0 ? 60 : -60, scale: 0.97 }),
  center: { opacity: 1, x: 0, scale: 1 },
  exit: (dir) => ({ opacity: 0, x: dir < 0 ? 60 : -60, scale: 0.97 }),
}

export default function App() {
  const [panel, setPanel]             = useState('dashboard')
  const [activeUser, setActiveUserRaw] = useState('owner')
  const [novaState, setNovaState]  = useState('idle')
  const [lastHeard, setLastHeard]      = useState(null)
  const [lastResponse, setLastResponse]= useState(null)
  const [budgetData, setBudgetData]    = useState(null)
  const [calData, setCalData]          = useState(null)
  const wsRef    = useRef(null)
  const dirRef   = useRef(1)
  const cacheRef = useRef({})   // { owner: {budget, cal}, andriana: {budget, cal} }

  // Apply theme + fetch immediately (no blank frame waiting for useEffect)
  const setActiveUser = (uid) => {
    setActiveUserRaw(uid)
    document.documentElement.setAttribute('data-user', uid)
    if (uid === 'shared') setPanel('dashboard')
    fetchUserData(uid)
  }

  // Fetch user data — shows cached immediately, updates in background
  const fetchUserData = (user) => {
    // Show cached data instantly (no blank screen)
    const cached = cacheRef.current[user]
    if (cached?.budget) setBudgetData(cached.budget)
    if (cached?.cal)    setCalData(cached.cal)

    // shared has no budget
    if (user !== 'shared') {
      fetch(`/api/budget/summary?user=${user}`)
        .then(r => r.json())
        .then(d => {
          cacheRef.current[user] = { ...cacheRef.current[user], budget: d }
          setBudgetData(d)
        }).catch(() => {})
    } else {
      setBudgetData(null)
    }

    const today = new Date()
    fetch(`/api/calendar/month?year=${today.getFullYear()}&month=${today.getMonth()+1}&user=${user}`)
      .then(r => r.json())
      .then(d => {
        cacheRef.current[user] = { ...cacheRef.current[user], cal: d }
        setCalData(d)
      }).catch(() => {})
  }

  // Initial load only — subsequent user changes handled by setActiveUser directly
  useEffect(() => { fetchUserData(activeUser) }, [])

  // Auto-refresh every 30 minutes
  useEffect(() => {
    const id = setInterval(() => fetchUserData(activeUser), 30 * 60 * 1000)
    return () => clearInterval(id)
  }, [activeUser])

  // WebSocket for real-time Nova state
  useEffect(() => {
    const connect = () => {
      try {
        const ws = new WebSocket(`ws://${location.host}/ws`)
        ws.onmessage = (e) => {
          const msg = JSON.parse(e.data)
          if (msg.type === 'nova_state') {
            setNovaState(msg.payload)
            if (msg.heard) setLastHeard(msg.heard)
            if (msg.text)  setLastResponse(msg.text)
          } else if (msg.type === 'navigate') {
            navigate(msg.tab)
          } else if (msg.type === 'set_user') {
            setActiveUser(msg.user)
          } else if (msg.type === 'refresh_calendar') {
            cacheRef.current[activeUser] = { ...cacheRef.current[activeUser], cal: null }
            fetchUserData(activeUser)
          }
        }
        ws.onclose = () => setTimeout(connect, 3000)
        wsRef.current = ws
      } catch {}
    }
    connect()
    return () => wsRef.current?.close()
  }, [])

  const navigate = (next) => {
    const ci = PANELS.indexOf(panel)
    const ni = PANELS.indexOf(next)
    dirRef.current = ni >= ci ? 1 : -1
    setPanel(next)
  }

  // Shared view renders its own full-screen panel
  const isShared = activeUser === 'shared'

  return (
    <div className="app">
      <div className="app-bg">
        <div className="grid-overlay" />
        <div className="radial-glow glow-tl" />
        <div className="radial-glow glow-br" />
      </div>

      {panel !== 'dashboard' && (
        <NovaOverlay
          novaState={novaState}
          lastHeard={lastHeard}
          lastResponse={lastResponse}
        />
      )}

      <NavBar
        active={panel}
        navigate={navigate}
        novaState={novaState}
        activeUser={activeUser}
        setActiveUser={setActiveUser}
      />

      <main className="app-main">
        {isShared ? (
          <motion.div
            key="shared"
            className="panel-wrap"
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -20 }}
            transition={{ duration: 0.3 }}
          >
            <SharedCalendar
              calData={calData}
              setCalData={(d) => {
                setCalData(d)
                cacheRef.current['shared'] = { ...cacheRef.current['shared'], cal: d }
              }}
            />
          </motion.div>
        ) : (
          <AnimatePresence mode="wait" custom={dirRef.current}>
            <motion.div
              key={`${activeUser}-${panel}`}
              custom={dirRef.current}
              variants={variants}
              initial="enter"
              animate="center"
              exit="exit"
              transition={{ duration: 0.3, ease: [0.4, 0, 0.2, 1] }}
              className="panel-wrap"
            >
              {panel === 'dashboard' && (
                <Dashboard
                  novaState={novaState}
                  budgetData={budgetData}
                  calData={calData}
                  lastHeard={lastHeard}
                  lastResponse={lastResponse}
                  activeUser={activeUser}
                />
              )}
              {panel === 'calendar' && (
                <CalendarPanel
                  calData={calData}
                  setCalData={(d) => {
                    setCalData(d)
                    cacheRef.current[activeUser] = { ...cacheRef.current[activeUser], cal: d }
                  }}
                  activeUser={activeUser}
                />
              )}
              {panel === 'budget' && (
                <ErrorBoundary key={activeUser}>
                  <BudgetPanel data={budgetData} activeUser={activeUser} />
                </ErrorBoundary>
              )}
            </motion.div>
          </AnimatePresence>
        )}
      </main>
    </div>
  )
}
