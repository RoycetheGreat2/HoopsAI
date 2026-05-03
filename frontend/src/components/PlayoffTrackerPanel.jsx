import { useEffect, useState } from 'react'
import axios from 'axios'
import './PlayoffTrackerPanel.css'

function accuracyTier(pct) {
  if (pct == null || Number.isNaN(pct)) return 'playoff-tracker__acc--neutral'
  if (pct > 60) return 'playoff-tracker__acc--high'
  if (pct < 55) return 'playoff-tracker__acc--low'
  return 'playoff-tracker__acc--mid'
}

function AccuracyRing({ pct }) {
  const p = pct == null || Number.isNaN(pct) ? 0 : Math.min(100, Math.max(0, pct))
  const r = 20
  const c = 2 * Math.PI * r
  const offset = c * (1 - p / 100)
  const tier = accuracyTier(p)
  return (
    <svg
      className={`playoff-tracker__ring ${tier}`}
      width="52"
      height="52"
      viewBox="0 0 52 52"
      aria-hidden="true"
    >
      <circle
        className="playoff-tracker__ring-bg"
        cx="26"
        cy="26"
        r={r}
        fill="none"
      />
      <circle
        className="playoff-tracker__ring-fg"
        cx="26"
        cy="26"
        r={r}
        fill="none"
        strokeDasharray={`${c}`}
        strokeDashoffset={offset}
        transform="rotate(-90 26 26)"
      />
    </svg>
  )
}

export default function PlayoffTrackerPanel({ refreshKey }) {
  const [data, setData] = useState(null)
  const [err, setErr] = useState(null)

  useEffect(() => {
    let cancelled = false
    ;(async () => {
      setErr(null)
      try {
        const res = await axios.get('/api/playoff-stats', { timeout: 15000 })
        if (!cancelled) setData(res.data)
      } catch (e) {
        if (!cancelled) {
          setErr(e?.message || 'Failed to load playoff stats')
          setData(null)
        }
      }
    })()
    return () => {
      cancelled = true
    }
  }, [refreshKey])

  if (err || !data || !data.is_active) {
    return null
  }

  const total = data.total_games ?? 0
  const correct = data.correct ?? 0
  const acc = data.accuracy
  const accPct = acc == null ? null : acc * 100
  const seriesList = Array.isArray(data.by_series) ? data.by_series : []

  return (
    <section
      className="playoff-tracker"
      aria-labelledby="playoff-tracker-heading"
    >
      <h2 id="playoff-tracker-heading" className="playoff-tracker__title">
        Playoff Prediction Tracker
        <span className="playoff-tracker__season">{data.season}</span>
      </h2>

      <div className="playoff-tracker__summary">
        <div className="playoff-tracker__summary-main">
          <AccuracyRing pct={accPct} />
          <div className="playoff-tracker__summary-text">
            <p className="playoff-tracker__summary-line">
              <strong>{total}</strong> games tracked ·{' '}
              <strong>{correct}</strong> correct
            </p>
            <p className="playoff-tracker__summary-acc">
              Overall accuracy:{' '}
              <span className={accuracyTier(accPct)}>
                {accPct == null ? '—' : `${accPct.toFixed(1)}%`}
              </span>
            </p>
          </div>
        </div>
        <p className="playoff-tracker__note">
          This model was trained primarily on regular-season patterns; playoff
          matchups often behave differently, so expect accuracy to be lower than
          validation on past regular seasons.
        </p>
      </div>

      <div className="playoff-tracker__series-list">
        {seriesList.map((s) => {
          const played = s.games_played ?? 0
          const gc = s.games_correct ?? 0
          const wrong = played - gc
          const sa = s.accuracy
          const sap = sa == null ? null : sa * 100
          return (
            <div key={s.series} className="playoff-series">
              <div className="playoff-series__head">
                <div className="playoff-series__matchup">
                  <span className="playoff-series__team">{s.team_a}</span>
                  <span className="playoff-series__vs">vs</span>
                  <span className="playoff-series__team">{s.team_b}</span>
                </div>
                <div className="playoff-series__meta">
                  <span className="playoff-series__record">
                    Model: {gc}-{wrong}
                  </span>
                  <span className={`playoff-series__acc ${accuracyTier(sap)}`}>
                    {sap == null ? '—' : `${sap.toFixed(1)}%`}
                  </span>
                </div>
              </div>

              <details className="playoff-series__details">
                <summary className="playoff-series__summary">Game log</summary>
                <ul className="playoff-series__log">
                  {(s.games || []).map((g, gi) => (
                    <li
                      key={`${s.series}-${g.date}-${gi}`}
                      className="playoff-series__row"
                    >
                      <span className="playoff-series__date">{g.date}</span>
                      <span className="playoff-series__pred">
                        Pick {g.predicted_winner}
                      </span>
                      <span className="playoff-series__act">
                        Final {g.actual_winner}
                      </span>
                      <span className="playoff-series__prob">
                        {((g.away_win_probability ?? 0) * 100).toFixed(1)}% /{' '}
                        {((g.home_win_probability ?? 0) * 100).toFixed(1)}%
                      </span>
                      {g.correct ? (
                        <span className="playoff-series__badge playoff-series__badge--ok">
                          ✓ Correct
                        </span>
                      ) : (
                        <span className="playoff-series__badge playoff-series__badge--bad">
                          ✗ Incorrect
                        </span>
                      )}
                    </li>
                  ))}
                </ul>
              </details>
            </div>
          )
        })}
      </div>
    </section>
  )
}
