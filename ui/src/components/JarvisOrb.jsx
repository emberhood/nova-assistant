import { motion } from 'framer-motion'
import './JarvisOrb.css'

export default function JarvisOrb({ state = 'idle' }) {
  const isListening = state === 'listening'
  const isSpeaking  = state === 'speaking'

  return (
    <div className="orb-wrap">
      {/* outer rings */}
      {[0, 1, 2].map(i => (
        <motion.div
          key={i}
          className="orb-ring"
          style={{ '--i': i }}
          animate={{
            scale: isListening ? [1, 1.08, 1] : isSpeaking ? [1, 1.12, 1] : [1, 1.02, 1],
            opacity: isListening ? 0.7 : isSpeaking ? 0.9 : 0.25,
          }}
          transition={{
            duration: isListening ? 0.8 : isSpeaking ? 0.5 : 3,
            repeat: Infinity,
            delay: i * 0.18,
            ease: 'easeInOut',
          }}
        />
      ))}

      {/* rotating arc */}
      <motion.div
        className="orb-arc"
        animate={{ rotate: 360 }}
        transition={{ duration: isSpeaking ? 1.5 : isListening ? 2.5 : 8, repeat: Infinity, ease: 'linear' }}
      />
      <motion.div
        className="orb-arc orb-arc-2"
        animate={{ rotate: -360 }}
        transition={{ duration: isSpeaking ? 2 : isListening ? 3.5 : 12, repeat: Infinity, ease: 'linear' }}
      />

      {/* core */}
      <motion.div
        className="orb-core"
        animate={{
          boxShadow: isListening
            ? ['0 0 20px var(--green), 0 0 60px rgba(0,255,157,0.3)', '0 0 40px var(--green), 0 0 100px rgba(0,255,157,0.5)', '0 0 20px var(--green), 0 0 60px rgba(0,255,157,0.3)']
            : isSpeaking
            ? ['0 0 20px var(--accent), 0 0 60px var(--glow-c)', '0 0 50px var(--accent), 0 0 120px var(--glow-c)', '0 0 20px var(--accent), 0 0 60px var(--glow-c)']
            : ['0 0 10px var(--accent), 0 0 30px var(--glow-c)', '0 0 15px var(--accent), 0 0 40px var(--glow-c)', '0 0 10px var(--accent), 0 0 30px var(--glow-c)'],
          backgroundColor: isListening ? 'rgba(0,255,157,0.15)' : 'rgba(0,212,255,0.1)',
        }}
        transition={{ duration: isListening ? 0.6 : isSpeaking ? 0.4 : 2.5, repeat: Infinity, ease: 'easeInOut' }}
      >
        <div className="orb-inner-ring" />
        <span className="orb-letter">J</span>
      </motion.div>

      {/* waveform bars when speaking */}
      {isSpeaking && (
        <div className="orb-wave">
          {Array.from({ length: 7 }).map((_, i) => (
            <motion.div
              key={i}
              className="wave-bar"
              animate={{ scaleY: [0.3, 1, 0.3] }}
              transition={{ duration: 0.5, repeat: Infinity, delay: i * 0.07, ease: 'easeInOut' }}
            />
          ))}
        </div>
      )}
    </div>
  )
}
