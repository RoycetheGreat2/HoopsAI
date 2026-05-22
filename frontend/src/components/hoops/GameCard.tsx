import { CheckCircle2, XCircle, MinusCircle } from 'lucide-react';
import type { GamePrediction } from '@/hooks/useApi';
import { formatTipoff, isGameCorrect } from '@/hooks/useApi';
import { ProbabilityBar } from './ProbabilityBar';

interface GameCardProps {
  game: GamePrediction;
  timeZone: string;
}

function TeamLogo({ url, abbrev }: { url: string; abbrev: string }) {
  if (url) {
    return (
      <img
        src={url}
        alt={`${abbrev} logo`}
        className="h-12 w-12 object-contain"
      />
    );
  }
  return (
    <div className="flex h-12 w-12 items-center justify-center rounded-full bg-muted text-xs font-bold text-muted-foreground">
      {abbrev}
    </div>
  );
}

function statusLabel(status: string, tip: string | null): string {
  if (status === 'post') return 'Final';
  if (status === 'in') return tip ? `Live · ${tip}` : 'Live';
  return tip ? tip : 'Scheduled';
}

export function GameCard({ game, timeZone }: GameCardProps) {
  const isFinished = game.status === 'post';
  const tip = formatTipoff(game.utc_time, timeZone);
  const awayPct = (game.away_win_probability * 100).toFixed(1);
  const homePct = (game.home_win_probability * 100).toFixed(1);
  const pickAway = game.predicted_winner === game.away;
  const pickHome = game.predicted_winner === game.home;

  const result = isGameCorrect(game);
  const awayScore = Number(game.away_score) || 0;
  const homeScore = Number(game.home_score) || 0;
  const showScores = isFinished;

  return (
    <div className="overflow-hidden rounded-lg border border-border bg-white">
      {isFinished && (
        <ResultBanner result={result} actual={game.actual_winner} pick={game.predicted_winner} />
      )}

      <div className="border-b border-border p-6">
        <p className="mb-4 text-sm font-medium text-muted-foreground">
          {isFinished ? 'Finished match' : 'Upcoming match'} ·{' '}
          {statusLabel(game.status, tip)}
        </p>

        <div className="flex items-center justify-between gap-4">
          <div
            className={`flex-1 text-center ${pickAway ? '' : 'opacity-70'}`}
          >
            <div className="mb-3 flex justify-center">
              <TeamLogo url={game.away_logo} abbrev={game.away} />
            </div>
            <p
              className={`text-sm font-medium ${
                pickAway ? 'text-primary' : 'text-foreground'
              }`}
            >
              {game.away}
            </p>
            {pickAway && !isFinished && (
              <span className="mt-1 inline-block text-xs font-semibold text-primary">
                Predicted winner
              </span>
            )}
            {isFinished && game.actual_winner === game.away && (
              <span className="mt-1 inline-block text-xs font-semibold text-secondary">
                Won
              </span>
            )}
          </div>

          <div className="flex flex-col items-center gap-2">
            {showScores ? (
              <div className="flex items-end gap-2">
                <span className="text-4xl font-bold text-foreground">
                  {awayScore}
                </span>
                <span className="mb-1 text-2xl font-bold text-muted-foreground">
                  –
                </span>
                <span className="text-4xl font-bold text-foreground">
                  {homeScore}
                </span>
              </div>
            ) : (
              <span className="text-lg font-semibold text-muted-foreground">
                @
              </span>
            )}
            <span className="text-xs font-semibold uppercase text-muted-foreground">
              {statusLabel(game.status, tip)}
            </span>
          </div>

          <div
            className={`flex-1 text-center ${pickHome ? '' : 'opacity-70'}`}
          >
            <div className="mb-3 flex justify-center">
              <TeamLogo url={game.home_logo} abbrev={game.home} />
            </div>
            <p
              className={`text-sm font-medium ${
                pickHome ? 'text-primary' : 'text-foreground'
              }`}
            >
              {game.home}
            </p>
            {pickHome && !isFinished && (
              <span className="mt-1 inline-block text-xs font-semibold text-primary">
                Predicted winner
              </span>
            )}
            {isFinished && game.actual_winner === game.home && (
              <span className="mt-1 inline-block text-xs font-semibold text-secondary">
                Won
              </span>
            )}
          </div>
        </div>
      </div>

      <div className="p-6">
        <ProbabilityBar
          team1={game.away}
          team2={game.home}
          team1Prob={parseFloat(awayPct)}
          team2Prob={parseFloat(homePct)}
        />
      </div>
    </div>
  );
}

function ResultBanner({
  result,
  actual,
  pick,
}: {
  result: boolean | null;
  actual: string | null;
  pick: string;
}) {
  if (result === true) {
    return (
      <div
        className="flex items-center justify-center gap-2 bg-secondary px-4 py-3 text-center font-semibold text-white"
        role="status"
      >
        <CheckCircle2 className="h-5 w-5 shrink-0" aria-hidden />
        <span>Correct — model picked {pick}, winner was {actual}</span>
      </div>
    );
  }
  if (result === false) {
    return (
      <div
        className="flex items-center justify-center gap-2 bg-destructive px-4 py-3 text-center font-semibold text-white"
        role="status"
      >
        <XCircle className="h-5 w-5 shrink-0" aria-hidden />
        <span>Incorrect — model picked {pick}, winner was {actual}</span>
      </div>
    );
  }
  return (
    <div
      className="flex items-center justify-center gap-2 bg-muted px-4 py-3 text-center text-sm font-medium text-muted-foreground"
      role="status"
    >
      <MinusCircle className="h-5 w-5 shrink-0" aria-hidden />
      Final score recorded — winner not available yet
    </div>
  );
}
