import { AnimatePresence, motion } from 'framer-motion'
import JarvisOrb from './JarvisOrb.jsx'
import './JarvisOverlay.css'

const STATE_LABEL = {
  listening:  'Ακούω...',
  processing: 'Επεξεργάζομαι...',
  speaking:   'Μιλάω...',
}

export default function JarvisOverlay({ jarvisState, lastHeard, lastResponse }) {
  const active = jarvisState !== 'idle'

  return (
    <AnimatePresence>
      {active && (
        <motion.div
          className="jarvis-overlay-badge"
          initial={{ opacity: 0, x: 40 }}
          animate={{ opacity: 1, x: 0 }}
          exit={{    opacity: 0, x: 40 }}
          transition={{ duration: 0.22, ease: [0.4, 0, 0.2, 1] }}
        >
          <div className="badge-orb">
            <JarvisOrb state={jarvisState} />
          </div>

          <div className="badge-text">
            <span className="badge-state">{STATE_LABEL[jarvisState]}</span>
            <AnimatePresence mode="wait">
              {jarvisState === 'speaking' && lastResponse && (
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
              {jarvisState === 'processing' && lastHeard && (
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
