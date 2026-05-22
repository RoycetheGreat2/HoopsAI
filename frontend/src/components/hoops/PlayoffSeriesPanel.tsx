import { Trophy, CheckCircle2, XCircle, Loader2 } from 'lucide-react';
import { usePlayoffStats } from '@/hooks/useApi';

interface PlayoffSeriesPanelProps {
  refreshKey?: string;
}

export function PlayoffSeriesPanel({ refreshKey }: PlayoffSeriesPanelProps) {
  const { data, error } = usePlayoffStats(refreshKey);

  if (error) {
    return (
      <section className="card-professional p-6">
        <p className="text-sm text-destructive">{error}</p>
      </section>
    );
  }

  if (!data) {
    return (
      <section className="card-professional p-6" aria-busy="true">
        <div className="flex items-center gap-3 text-muted-foreground">
          <Loader2 className="h-5 w-5 animate-spin" />
          Loading playoff tracker…
        </div>
      </section>
    );
  }

  if (!data.is_active) {
    return (
      <section className="card-professional p-6">
        <p className="text-muted-foreground">
          Playoff tracker activates when playoff games appear in the weekly
          schedule.
        </p>
      </section>
    );
  }

  const accPct = data.accuracy == null ? null : data.accuracy * 100;
  const seriesList = Array.isArray(data.by_series) ? data.by_series : [];

  return (
    <section className="card-professional p-6">
      <div className="mb-6 flex flex-wrap items-center gap-3">
        <Trophy className="h-6 w-6 text-accent" />
        <h2 className="text-2xl font-bold text-foreground">
          Playoff prediction tracker
        </h2>
        {data.season && (
          <span className="rounded-full bg-muted px-3 py-1 text-xs font-medium text-muted-foreground">
            {data.season}
          </span>
        )}
      </div>

      <div className="mb-6 rounded-lg border border-border bg-muted/30 p-4">
        <p className="text-sm text-foreground">
          <strong>{data.total_games ?? 0}</strong> games tracked ·{' '}
          <strong>{data.correct ?? 0}</strong> correct
          {accPct != null && (
            <>
              {' '}
              ·{' '}
              <span className="font-semibold text-primary">
                {accPct.toFixed(1)}% accuracy
              </span>
            </>
          )}
        </p>
        <p className="mt-2 text-xs text-muted-foreground">
          Trained mainly on regular-season patterns; playoff accuracy is often
          lower than forward validation on 2025 regular season games.
        </p>
      </div>

      <div className="space-y-4">
        {seriesList.map((s) => {
          const sap =
            s.accuracy == null ? null : (s.accuracy * 100).toFixed(1);
          return (
            <div
              key={s.series}
              className="rounded-lg border border-border bg-muted/20 p-4"
            >
              <div className="mb-2 flex flex-wrap items-center justify-between gap-2">
                <p className="font-semibold text-foreground">
                  {s.team_a} vs {s.team_b}
                </p>
                <p className="text-sm text-muted-foreground">
                  {s.games_correct ?? 0}/{s.games_played ?? 0} correct
                  {sap != null && ` · ${sap}%`}
                </p>
              </div>
              <ul className="space-y-2">
                {(s.games ?? []).map((g, idx) => (
                  <li
                    key={`${g.date}-${idx}`}
                    className="flex items-center gap-2 text-sm text-muted-foreground"
                  >
                    {g.correct ? (
                      <CheckCircle2 className="h-4 w-4 shrink-0 text-secondary" />
                    ) : (
                      <XCircle className="h-4 w-4 shrink-0 text-destructive" />
                    )}
                    <span>
                      {g.date}: predicted {g.predicted_winner}, actual{' '}
                      {g.actual_winner}
                    </span>
                  </li>
                ))}
              </ul>
            </div>
          );
        })}
      </div>
    </section>
  );
}
