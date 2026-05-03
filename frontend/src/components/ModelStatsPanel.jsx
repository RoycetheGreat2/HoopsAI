import { useEffect, useState } from 'react'
import axios from 'axios'
import './ModelStatsPanel.css'

export default function ModelStatsPanel() {
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [data, setData] = useState(null)

  useEffect(() => {
    let cancelled = false
    ;(async () => {
      setLoading(true)
      setError(null)
      try {
        const res = await axios.get('/api/model-stats', { timeout: 12000 })
        if (!cancelled) setData(res.data)
      } catch (e) {
        if (!cancelled) {
          setError(
            e?.response?.data?.error ||
              e?.message ||
              'Could not load model statistics.',
          )
        }
      } finally {
        if (!cancelled) setLoading(false)
      }
    })()
    return () => {
      cancelled = true
    }
  }, [])

  if (loading) {
    return (
      <section className="model-panel" aria-busy="true">
        <h2>Model performance</h2>
        <p className="model-panel__intro">
          How well the AI model has scored on recent historical games (not
          today&apos;s results).
        </p>
        <div className="model-panel__status">Loading model stats…</div>
      </section>
    )
  }

  if (error) {
    return (
      <section className="model-panel">
        <h2>Model performance</h2>
        <p className="model-panel__intro">
          How well the AI model has scored on recent historical games.
        </p>
        <div className="model-panel__status model-panel__status--error">
          {error}
        </div>
      </section>
    )
  }

  const accPct =
    typeof data.forward_validation_accuracy_pct === 'number'
      ? data.forward_validation_accuracy_pct
      : typeof data.accuracy === 'number'
        ? data.accuracy * 100
        : null

  const top = Array.isArray(data.top_features) ? data.top_features : []

  return (
    <section className="model-panel">
      <h2>Model performance</h2>
      <p className="model-panel__intro">
        These numbers summarize how accurately the model predicted winners on
        held-out recent seasons before going live. They describe past
        validation, not tonight&apos;s outcomes.
      </p>

      <div className="model-panel__grid">
        <div>
          <span className="model-panel__metric-label">
            Forward validation accuracy
          </span>
          <span className="model-panel__metric-value">
            {accPct != null ? `${accPct.toFixed(1)}%` : '—'}
          </span>
        </div>
        <div>
          <span className="model-panel__metric-label">AUC-ROC</span>
          <span className="model-panel__metric-value">
            {typeof data.auc_roc === 'number' ? data.auc_roc.toFixed(3) : '—'}
          </span>
        </div>
        <div>
          <span className="model-panel__metric-label">Brier score</span>
          <span className="model-panel__metric-value">
            {typeof data.brier_score === 'number'
              ? data.brier_score.toFixed(4)
              : '—'}
          </span>
        </div>
        <div>
          <span className="model-panel__metric-label">Number of inputs</span>
          <span className="model-panel__metric-value">
            {typeof data.num_features === 'number' ? data.num_features : '—'}{' '}
            features
          </span>
        </div>
      </div>

      <h3 className="model-panel__top-title">Top 5 most important features</h3>
      <p className="model-panel__intro" style={{ marginTop: '-0.25rem' }}>
        The model leans on these signals the most when estimating win
        probability.
      </p>
      <ol className="model-panel__top-list">
        {top.map((item) => (
          <li key={item.rank} className="model-panel__top-item">
            <span className="model-panel__top-rank">{item.rank}.</span>
            <span className="model-panel__top-name">{item.feature}</span>
            <span className="model-panel__top-score">
              {typeof item.importance === 'number'
                ? item.importance.toFixed(2)
                : ''}
            </span>
          </li>
        ))}
      </ol>
    </section>
  )
}
