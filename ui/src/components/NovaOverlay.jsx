import { AnimatePresence, motion } from 'framer-motion'
import NovaOrb from './NovaOrb.jsx'
import './NovaOverlay.css'

const STATE_LABEL = {
  listening:  'Ακούω...',
  processing: 'Επεξεργάζομαι...',
  speaking:   'Μιλάω...',
}

export default function NovaOverlay({ novaState, lastHeard, lastResponse }) {
  const active = novaState !== 'idle'

  return (
    <AnimatePresence>
      {active && (
        <motion.div
          className="nova-overlay-badge"
          initial={{ opacity: 0, x: 40 }}
          animate={{ opacity: 1, x: 0 }}
          exit={{    opacity: 0, x: 40 }}
          transition={{ duration: 0.22, ease: [0.4, 0, 0.2, 1] }}
        >
          <div className="badge-orb">
            <NovaOrb state={novaState} />
          </div>

          <div className="badge-text">
            <span className="badge-state">{STATE_LABEL[novaState]}</span>
            <AnimatePresence mode="wait">
              {novaState === 'speaking' && lastResponse && (
                <motion.span
                  key="resp"
                  className="badge-detail"
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  exit={{    opacity: 0 }}
                >
                  {lastResponse}
                </motion.span>
              )}
              {novaState === 'processing' && lastHeard && (
                <motion.span
                  key="heard"
                  className="badge-detail"
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  exit={{    opacity: 0 }}
                >
                  "{lastHeard}"
                </motion.span>
              )}
            </AnimatePresence>
          </div>
        </motion.div>
      )}
    </AnimatePresence>
  )
}
