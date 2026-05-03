import { useEffect, useMemo, useState } from 'react'
import axios from 'axios'
import HealthBanner from './components/HealthBanner.jsx'
import ModelStatsPanel from './components/ModelStatsPanel.jsx'
import MatchupCard from './components/MatchupCard.jsx'
import PlayoffTrackerPanel from './components/PlayoffTrackerPanel.jsx'
import './App.css'

function partitionPredictions(list) {
  const upcoming = []
  const finished = []
  for (const g of list) {
    const st = g.status
    if (st === 'post') finished.push(g)
    else if (st === 'pre' || st === 'in') upcoming.push(g)
    else upcoming.push(g)
  }
  return { upcoming, finished }
}

function localYmd() {
  const n = new Date()
  const p = (x) => String(x).padStart(2, '0')
  return `${n.getFullYear()}-${p(n.getMonth() + 1)}-${p(n.getDate())}`
}

function resolvedTimeZone() {
  try {
    return Intl.DateTimeFormat().resolvedOptions().timeZone || 'UTC'
  } catch {
    return 'UTC'
  }
}

/** Local calendar YYYY-MM-DD for an instant, in the given IANA zone. */
function localYmdFromUtcIso(iso, timeZone) {
  if (!iso || typeof iso !== 'string') return null
  const t = Date.parse(iso)
  if (Number.isNaN(t)) return null
  return new Intl.DateTimeFormat('en-CA', {
    timeZone,
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
  }).format(new Date(t))
}

function formatLocalDayHeading(ymd) {
  const [y, m, d] = ymd.split('-').map(Number)
  const dt = new Date(y, m - 1, d, 12, 0, 0, 0)
  const weekday = dt.toLocaleDateString('en-US', { weekday: 'long' })
  const rest = dt.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
  return `${weekday} · ${rest}`
}

function formatWeekRange(startIso, endIso) {
  if (!startIso || !endIso) return ''
  const [ys, ms, ds] = startIso.split('-').map(Number)
  const [ye, me, de] = endIso.split('-').map(Number)
  const a = new Date(ys, ms - 1, ds, 12, 0, 0, 0)
  const b = new Date(ye, me - 1, de, 12, 0, 0, 0)
  const o = { month: 'short', day: 'numeric' }
  return `${a.toLocaleDateString('en-US', o)} – ${b.toLocaleDateString('en-US', o)}, ${ys}`
}

/**
 * Flatten server `days`, regroup by viewer-local date from `utc_time`,
 * sort with today first then ascending. Stagger indices follow card order.
 */
function buildLocalDayBlocks(payload, timeZone) {
  const flat = []
  for (const day of Array.isArray(payload?.days) ? payload.days : []) {
    for (const g of day.games || []) {
      flat.push({ ...g, _serverDay: day.date })
    }
  }

  if (flat.length === 0) {
    return []
  }

  const byDay = new Map()
  const addToDay = (ymd, g) => {
    if (!ymd) return
    const { _serverDay, ...rest } = g
    if (!byDay.has(ymd)) byDay.set(ymd, [])
    byDay.get(ymd).push(rest)
  }

  for (const g of flat) {
    let ymd = localYmdFromUtcIso(g.utc_time, timeZone)
    if (!ymd && g._serverDay) {
      ymd = String(g._serverDay).slice(0, 10)
    }
    addToDay(ymd, g)
  }

  if (byDay.size === 0 && flat.length > 0) {
    for (const g of flat) {
      if (!g._serverDay) continue
      const ymd = String(g._serverDay).slice(0, 10)
      addToDay(ymd, g)
    }
  }

  const todayYmd = localYmd()
  const allKeys = [...byDay.keys()].sort((a, b) => a.localeCompare(b))
  const restKeys = allKeys.filter((k) => k !== todayYmd)
  const orderedKeys = [todayYmd, ...restKeys]

  let stagger = 0
  return orderedKeys.map((dateKey) => {
    const gamesOnDay = byDay.get(dateKey) || []
    const { upcoming, finished } = partitionPredictions(gamesOnDay)
    const up = upcoming.map((game) => ({ game, stagger: stagger++ }))
    const fin = finished.map((game) => ({ game, stagger: stagger++ }))
    return { dateKey, up, fin }
  })
}

export default function App() {
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [payload, setPayload] = useState(null)
  const [retryKey, setRetryKey] = useState(0)

  const userTimeZone = useMemo(() => resolvedTimeZone(), [])

  useEffect(() => {
    let cancelled = false
    ;(async () => {
      setLoading(true)
      setError(null)
      setPayload(null)
      try {
        const res = await axios.get('/api/weekly-predictions', {
          timeout: 60000,
        })
        if (!cancelled) setPayload(res.data)
      } catch (e) {
        if (!cancelled) {
          setError(
            e?.response?.data?.error ||
              e?.response?.data?.detail ||
              e?.message ||
              'Something went wrong loading this week.',
          )
        }
      } finally {
        if (!cancelled) setLoading(false)
      }
    })()
    return () => {
      cancelled = true
    }
  }, [retryKey])

  const dayBlocks = useMemo(
    () => buildLocalDayBlocks(payload, userTimeZone),
    [payload, userTimeZone],
  )

  const todayYmd = localYmd()

  return (
    <>
      <HealthBanner />
      <div className="app">
        <header className="app-header">
          <h1 className="app-title">NBA Win Probability</h1>
          <p className="app-subtitle">
            Model-based win chances for the next seven days on the NBA schedule.
          </p>
        </header>

        {loading && (
          <div
            className="predictions-status predictions-status--loading"
            role="status"
          >
            Loading this week&apos;s schedule and predictions…
          </div>
        )}

        {!loading && error && (
          <div className="week-error">
            <h2 className="week-error__title">We couldn&apos;t load this week</h2>
            <p className="week-error__detail">{String(error)}</p>
            <button
              type="button"
              className="week-error__retry"
              onClick={() => setRetryKey((k) => k + 1)}
            >
              Retry
            </button>
          </div>
        )}

        {!loading && !error && (
          <section className="predictions-section" aria-label="Weekly predictions">
            {payload?.week_start && payload?.week_end && (
              <p className="app-subtitle" style={{ marginBottom: '1.5rem' }}>
                Week of{' '}
                <strong>
                  {formatWeekRange(payload.week_start, payload.week_end)}
                </strong>
              </p>
            )}

            {dayBlocks.length === 0 ? (
              <div className="predictions-status">
                No NBA games were found for the next seven days from the
                schedule we could reach. Check back later or confirm the API is
                online.
              </div>
            ) : (
              dayBlocks.map((block) => {
                const isToday = block.dateKey === todayYmd
                const hasUp = block.up.length > 0
                const hasFin = block.fin.length > 0
                return (
                  <section
                    key={block.dateKey}
                    className={
                      'day-section' +
                      (isToday ? ' day-section--today' : '')
                    }
                  >
                    <h2 className="day-section__heading">
                      {formatLocalDayHeading(block.dateKey)}
                    </h2>

                    {hasUp && (
                      <>
                        <h3 className="day-section__sub">Upcoming</h3>
                        <div className="predictions-list">
                          {block.up.map(({ game, stagger }, i) => (
                            <MatchupCard
                              key={`${block.dateKey}-up-${game.away}-${game.home}-${game.utc_time || i}`}
                              prediction={game}
                              staggerIndex={stagger}
                              timeZone={userTimeZone}
                            />
                          ))}
                        </div>
                      </>
                    )}

                    {!hasUp && hasFin && (
                      <p className="day-section__empty-note">
                        All of this day&apos;s games have finished — see results
                        below.
                      </p>
                    )}

                    {hasFin && (
                      <>
                        <h3 className="day-section__sub">Results</h3>
                        <div className="predictions-list">
                          {block.fin.map(({ game, stagger }, i) => (
                            <MatchupCard
                              key={`${block.dateKey}-fin-${game.away}-${game.home}-${game.utc_time || i}`}
                              prediction={game}
                              staggerIndex={stagger}
                              timeZone={userTimeZone}
                            />
                          ))}
                        </div>
                      </>
                    )}
                  </section>
                )
              })
            )}
          </section>
        )}

        {!loading && (
          <PlayoffTrackerPanel
            refreshKey={`${retryKey}-${payload?.week_start ?? ''}-${payload?.week_end ?? ''}`}
          />
        )}

        <section className="model-section" aria-labelledby="model-heading">
          <h2 id="model-heading" className="app-title">
            About the model
          </h2>
          <ModelStatsPanel />
        </section>
      </div>
    </>
  )
}
