import { useMemo } from 'react';
import { TrendingUp, Target } from 'lucide-react';
import {
  usePredictionAccuracy,
  type WeeklyPredictions,
  type GamePrediction,
} from '@/hooks/useApi';

interface RightSidebarProps {
  predictions: WeeklyPredictions | null;
}

function confidencePct(g: GamePrediction): number {
  return Math.max(g.away_win_probability, g.home_win_probability) * 100;
}

export function RightSidebar({ predictions }: RightSidebarProps) {
  const { data: accuracy } = usePredictionAccuracy();

  const { gameCount, topConfidence } = useMemo(() => {
    const games: GamePrediction[] = [];
    for (const day of predictions?.days ?? []) {
      for (const g of day.games ?? []) {
        games.push(g);
      }
    }
    const sorted = [...games].sort(
      (a, b) => confidencePct(b) - confidencePct(a)
    );
    return {
      gameCount: games.length,
      topConfidence: sorted.slice(0, 3),
    };
  }, [predictions]);

  const weekAcc = accuracy?.week;
  const weekLabel =
    weekAcc && weekAcc.total > 0 && weekAcc.accuracy != null
      ? `${(weekAcc.accuracy * 100).toFixed(1)}% (${weekAcc.correct}/${weekAcc.total})`
      : '—';

  return (
    <div className="space-y-6">
      <div className="rounded-lg border border-border bg-white p-6">
        <h3 className="mb-4 flex items-center gap-2 text-sm font-semibold text-foreground">
          <TrendingUp className="h-4 w-4 text-accent" />
          HIGHEST CONFIDENCE THIS WEEK
        </h3>
        {topConfidence.length === 0 ? (
          <p className="text-sm text-muted-foreground">No games loaded yet.</p>
        ) : (
          <div className="space-y-4">
            {topConfidence.map((g, i) => (
              <div
                key={`${g.away}-${g.home}-${i}`}
                className="border-b border-muted pb-4 last:border-0 last:pb-0"
              >
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm font-medium text-foreground">
                      {g.away} @ {g.home}
                    </p>
                    <p className="text-xs text-muted-foreground">
                      Pick: {g.predicted_winner}
                    </p>
                  </div>
                  <span className="text-sm font-semibold text-secondary">
                    {confidencePct(g).toFixed(1)}%
                  </span>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      <div className="rounded-lg border border-border bg-white p-6">
        <h3 className="mb-4 text-sm font-semibold text-foreground">THIS WEEK</h3>
        <div className="space-y-4">
          <SidebarStat icon={Target} label="Games loaded" value={String(gameCount)} />
          <SidebarStat
            icon={TrendingUp}
            label="Correct (7 days)"
            value={weekLabel}
          />
        </div>
      </div>
    </div>
  );
}

function SidebarStat({
  icon: Icon,
  label,
  value,
}: {
  icon: typeof Target;
  label: string;
  value: string;
}) {
  return (
    <div className="flex items-center gap-3">
      <div className="rounded-lg bg-primary/10 p-2">
        <Icon className="h-4 w-4 text-primary" />
      </div>
      <div>
        <p className="text-xs text-muted-foreground">{label}</p>
        <p className="text-lg font-bold text-foreground">{value}</p>
      </div>
    </div>
  );
}
