import { motion } from 'framer-motion'
import './BudgetPanel.css'

function fmt(n) {
  if (n == null) return '—'
  return `€${Math.abs(n).toLocaleString('el-GR', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
}

function MetricCard({ label, value, color, icon, delay = 0 }) {
  return (
    <motion.div
      className="metric-card glass"
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay }}
    >
      <div className="metric-icon" style={{ color: `var(--${color})` }}>{icon}</div>
      <div className="metric-label">{label}</div>
      <div className="metric-value" style={{ color: `var(--${color})`, textShadow: `0 0 20px var(--${color})` }}>
        {value}
      </div>
    </motion.div>
  )
}

const MOCK_DATA = {
  available: true,
  totalBalance: 0,
  monthIncome: 0,
  monthExpenses: 0,
  accounts: [{ name: 'Main', balance: 0 }],
  recentExpenses: [],
  _isMock: true,
}

export default function BudgetPanel({ data }) {
  const raw = data ?? MOCK_DATA
  const display = {
    ...MOCK_DATA,
    ...raw,
    accounts: raw.accounts ?? [],
    recentExpenses: raw.recentExpenses ?? [],
  }

  if (!display.available) {
    return (
      <div className="panel budget-panel">
        <div className="glass budget-offline">
          <span style={{ color: 'var(--red)' }}>◈ Budget database offline</span>
          <p>Start the Vibe-Budgeting server and ensure the database path is configured.</p>
        </div>
      </div>
    )
  }

  const netMonth = display.monthIncome + display.monthExpenses
  const savingsRate = display.monthIncome > 0
    ? ((netMonth / display.monthIncome) * 100).toFixed(1)
    : null

  return (
    <div className="panel budget-panel">
      {display._isMock && (
        <div className="budget-notice">
          <span>◈ Backend offline — start the Jarvis backend to connect Vibe-Budgeting</span>
        </div>
      )}
      {/* Header metrics */}
      <div className="budget-metrics">
        <MetricCard label="Total Balance"    value={fmt(display.totalBalance)}  color="accent"  icon="◈" delay={0} />
        <MetricCard label="Month Income"     value={fmt(display.monthIncome)}   color="green"   icon="▲" delay={0.05} />
        <MetricCard label="Month Expenses"   value={fmt(display.monthExpenses)} color="red"     icon="▼" delay={0.1} />
        <MetricCard
          label="Net this month"
          value={fmt(netMonth)}
          color={netMonth >= 0 ? 'green' : 'red'}
          icon={netMonth >= 0 ? '◆' : '◇'}
          delay={0.15}
        />
      </div>

      <div className="budget-row">
        {/* Accounts */}
        <motion.div
          className="glass budget-accounts"
          initial={{ opacity: 0, x: -16 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ delay: 0.2 }}
        >
          <p className="section-title">Accounts</p>
          <div className="accounts-list">
            {display.accounts.map((a, i) => (
              <div key={i} className="account-row">
                <div className="account-dot" />
                <span className="account-name">{a.name}</span>
                <span className="account-balance" style={{ color: a.balance >= 0 ? 'var(--green)' : 'var(--red)' }}>
                  {fmt(a.balance)}
                </span>
              </div>
            ))}
          </div>
          {savingsRate !== null && (
            <div className="savings-bar-wrap">
              <div className="savings-bar-label">
                <span>Savings rate</span>
                <span style={{ color: savingsRate >= 0 ? 'var(--green)' : 'var(--red)' }}>
                  {savingsRate}%
                </span>
              </div>
              <div className="savings-bar-track">
                <motion.div
                  className="savings-bar-fill"
                  style={{ background: savingsRate >= 0 ? 'var(--green)' : 'var(--red)' }}
                  initial={{ width: 0 }}
                  animate={{ width: `${Math.min(100, Math.max(0, Math.abs(savingsRate)))}%` }}
                  transition={{ delay: 0.4, duration: 0.8, ease: 'easeOut' }}
                />
              </div>
            </div>
          )}
        </motion.div>

        {/* Recent transactions */}
        <motion.div
          className="glass budget-recent"
          initial={{ opacity: 0, x: 16 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ delay: 0.25 }}
        >
          <p className="section-title">Recent Expenses</p>
          {display.recentExpenses?.length === 0 && (
            <p className="no-data">No expenses recorded yet.</p>
          )}
          <div className="txn-list">
            {display.recentExpenses?.map((e, i) => (
              <motion.div
                key={i}
                className="txn-row"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={{ delay: 0.3 + i * 0.05 }}
              >
                <div className="txn-left">
                  <span className="txn-cat tag tag-cyan">{e.category || 'Other'}</span>
                  <span className="txn-notes">{e.notes || '—'}</span>
                </div>
                <div className="txn-right">
                  <span className="txn-date">{e.date?.slice(0, 10)}</span>
                  <span className="txn-amount" style={{ color: e.amount < 0 ? 'var(--red)' : 'var(--green)' }}>
                    {e.amount < 0 ? '-' : '+'}€{Math.abs(e.amount).toFixed(2)}
                  </span>
                </div>
              </motion.div>
            ))}
          </div>
        </motion.div>
      </div>

      <div className="budget-link glass">
        <span style={{ color: 'var(--text-dim)', fontSize: 11 }}>
          Data from Vibe-Budgeting ·
        </span>
        <a
          href="http://localhost:5000"
          target="_blank"
          rel="noreferrer"
          className="budget-open-link"
        >
          Open full app ↗
        </a>
      </div>
    </div>
  )
}
