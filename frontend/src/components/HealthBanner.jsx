import { useCallback, useEffect, useState } from 'react'
import axios from 'axios'
import './HealthBanner.css'

const POLL_MS = 30_000

export default function HealthBanner() {
  const [phase, setPhase] = useState('loading')
  const [message, setMessage] = useState('Checking API…')

  const check = useCallback(async () => {
    try {
      const { data } = await axios.get('/api/health', { timeout: 8000 })
      if (data && data.status === 'ok') {
        setPhase('ok')
        setMessage('API Connected')
      } else {
        setPhase('error')
        setMessage('API Offline')
      }
    } catch {
      setPhase('error')
      setMessage('API Offline')
    }
  }, [])

  useEffect(() => {
    check()
    const id = window.setInterval(check, POLL_MS)
    return () => window.clearInterval(id)
  }, [check])

  const cls =
    phase === 'ok'
      ? 'health-banner health-banner--ok'
      : phase === 'error'
        ? 'health-banner health-banner--error'
        : 'health-banner health-banner--loading'

  return (
    <div className={cls} role="status" aria-live="polite">
      <span className="health-banner__dot" aria-hidden="true" />
      <span className="health-banner__text">{message}</span>
    </div>
  )
}
