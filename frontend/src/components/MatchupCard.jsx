import './MatchupCard.css'

function TeamLogo({ url, abbrev }) {
  const label = `${abbrev} team logo`
  if (url) {
    return (
      <div className="matchup-card__logo-wrap">
        <img className="matchup-card__logo" src={url} alt={label} />
      </div>
    )
  }
  return (
    <div
      className="matchup-card__logo-wrap"
      role="img"
      aria-label={`No logo available for ${abbrev}`}
    >
      <span className="matchup-card__logo-placeholder">{abbrev}</span>
    </div>
  )
}

export default function MatchupCard({ prediction: p, staggerIndex = 0, timeZone }) {
  const status = p.status
  const isFinished = status === 'post'
  const tz =
    timeZone ||
    (typeof Intl !== 'undefined' &&
      Intl.DateTimeFormat().resolvedOptions().timeZone) ||
    'UTC'

  const showTip =
    !isFinished &&
    p.utc_time &&
    typeof p.utc_time === 'string' &&
    (status === 'pre' || status === 'in')

  let tipLabel = null
  if (showTip) {
    const t = Date.parse(p.utc_time)
    if (!Number.isNaN(t)) {
      tipLabel = new Intl.DateTimeFormat(undefined, {
        timeZone: tz,
        hour: 'numeric',
        minute: '2-digit',
      }).format(new Date(t))
    }
  }

  const awayPct = (p.away_win_probability * 100).toFixed(1)
  const homePct = (p.home_win_probability * 100).toFixed(1)
  const awayW = p.away_win_probability * 100
  const homeW = p.home_win_probability * 100
  const pickAway = p.predicted_winner === p.away
  const pickHome = p.predicted_winner === p.home

  const actual = p.actual_winner
  const predictionCorrect =
    isFinished &&
    actual != null &&
    p.predicted_winner === actual
  const predictionWrong =
    isFinished &&
    actual != null &&
    p.predicted_winner !== actual

  const awayScore =
    typeof p.away_score === 'number' ? p.away_score : Number(p.away_score)
  const homeScore =
    typeof p.home_score === 'number' ? p.home_score : Number(p.home_score)
  const scoreLine =
    isFinished &&
    !Number.isNaN(awayScore) &&
    !Number.isNaN(homeScore)
      ? `${p.away} ${awayScore} — ${p.home} ${homeScore}`
      : null

  return (
    <article
      className="matchup-card matchup-card--enter"
      style={{ animationDelay: `${staggerIndex * 0.055}s` }}
    >
      {predictionCorrect && (
        <div
          className="matchup-card__result-badge matchup-card__result-badge--correct"
          role="status"
        >
          <span className="matchup-card__result-icon" aria-hidden="true">
            ✓
          </span>
          Correct
        </div>
      )}
      {predictionWrong && (
        <div
          className="matchup-card__result-badge matchup-card__result-badge--incorrect"
          role="status"
        >
          <span className="matchup-card__result-icon" aria-hidden="true">
            ✗
          </span>
          Incorrect
        </div>
      )}

      <div className="matchup-card__teams">
        <div
          className={
            'matchup-card__team-block' +
            (pickAway
              ? ' matchup-card__team-block--winner'
              : ' matchup-card__team-block--dim')
          }
        >
          <TeamLogo url={p.away_logo} abbrev={p.away} />
          <span className="matchup-card__abbr">{p.away}</span>
        </div>
        <span className="matchup-card__at" aria-hidden="true">
          @
        </span>
        <div
          className={
            'matchup-card__team-block' +
            (pickHome
              ? ' matchup-card__team-block--winner'
              : ' matchup-card__team-block--dim')
          }
        >
          <TeamLogo url={p.home_logo} abbrev={p.home} />
          <span className="matchup-card__abbr">{p.home}</span>
        </div>
      </div>

      {tipLabel && (
        <p className="matchup-card__tip" aria-label="Tip-off time">
          Tip-off · {tipLabel}
        </p>
      )}

      {scoreLine && (
        <p className="matchup-card__final-score" aria-label="Final score">
          {scoreLine}
        </p>
      )}

      <div className="matchup-card__probs">
        <div
          className={
            'matchup-card__prob-col matchup-card__prob-col--away' +
            (pickAway ? ' matchup-card__prob-col--winner' : '')
          }
        >
          <span className="matchup-card__prob-label">Away win chance</span>
          <span className="matchup-card__prob-value">{awayPct}%</span>
        </div>
        <div
          className={
            'matchup-card__prob-col matchup-card__prob-col--home' +
            (pickHome ? ' matchup-card__prob-col--winner' : '')
          }
        >
          <span className="matchup-card__prob-label">Home win chance</span>
          <span className="matchup-card__prob-value">{homePct}%</span>
        </div>
      </div>

      <div
        className="matchup-card__bar"
        role="img"
        aria-label={`Win probability bar: away ${awayPct} percent, home ${homePct} percent`}
      >
        <div
          className="matchup-card__bar-away"
          style={{ width: `${awayW}%` }}
        />
        <div
          className="matchup-card__bar-home"
          style={{ width: `${homeW}%` }}
        />
      </div>

      <p className="matchup-card__pick">
        Model pick: <strong>{p.predicted_winner}</strong>
      </p>
    </article>
  )
}
