import { Target, Loader2, CalendarRange } from 'lucide-react';
import {
  usePredictionAccuracy,
  setAccuracyCache,
  type PredictionAccuracy,
} from '@/hooks/useApi';
import { TRACKING_SINCE } from '@/config';
import { useEffect } from 'react';

function formatAcc(acc: number | null, total: number): string {
  if (total === 0 || acc == null) return '—';
  return `${(acc * 100).toFixed(1)}%`;
}

function formatRange(start: string, end: string): string {
  const s = new Date(start + 'T12:00:00');
  const e = new Date(end + 'T12:00:00');
  const opts: Intl.DateTimeFormatOptions = { month: 'short', day: 'numeric' };
  return `${s.toLocaleDateString('en-US', opts)} – ${e.toLocaleDateString('en-US', { ...opts, year: 'numeric' })}`;
}

export function PerformancePanel({
  accuracySeed,
}: {
  accuracySeed?: PredictionAccuracy;
}) {
  useEffect(() => {
    if (accuracySeed) setAccuracyCache(accuracySeed);
  }, [accuracySeed]);

  const { loading, error, data } = usePredictionAccuracy();
  const stats = data ?? accuracySeed;

  if (loading && !stats) {
    return (
      <section className="card-professional p-6" aria-busy="true">
        <div className="flex items-center justify-center gap-3 py-12 text-muted-foreground">
          <Loader2 className="h-6 w-6 animate-spin text-primary" />
          Loading prediction results…
        </div>
      </section>
    );
  }

  if ((error && !stats) || !stats) {
    return (
      <section className="card-professional p-6">
        <p className="text-destructive">
          {error ?? 'Could not load prediction accuracy.'}
        </p>
      </section>
    );
  }

  const week = stats.week;
  const month = stats.month;

  return (
    <section className="card-professional p-6">
      <div className="mb-2 flex items-center gap-3">
        <Target className="h-6 w-6 text-primary" />
        <h2 className="text-2xl font-bold text-foreground">Prediction results</h2>
      </div>
      <p className="mb-8 text-sm text-muted-foreground">
        Finished games since {TRACKING_SINCE}. Only games with a recorded winner
        count toward these totals.
      </p>

      <div className="grid gap-6 md:grid-cols-2">
        <AccuracyCard
          title="Past 7 days"
          icon={CalendarRange}
          range={formatRange(week.start, week.end)}
          correct={week.correct}
          total={week.total}
          accuracy={week.accuracy}
        />
        <AccuracyCard
          title="Past 30 days"
          icon={CalendarRange}
          range={formatRange(month.start, month.end)}
          correct={month.correct}
          total={month.total}
          accuracy={month.accuracy}
        />
      </div>

      {week.total === 0 && month.total === 0 && (
        <p className="mt-6 rounded-lg border border-border bg-muted/30 p-4 text-sm text-muted-foreground">
          No finished games tracked yet. Results appear here after games end and
          the API syncs final scores.
        </p>
      )}
    </section>
  );
}

function AccuracyCard({
  title,
  icon: Icon,
  range,
  correct,
  total,
  accuracy,
}: {
  title: string;
  icon: typeof CalendarRange;
  range: string;
  correct: number;
  total: number;
  accuracy: number | null;
}) {
  return (
    <div className="rounded-lg border border-border bg-muted/20 p-6">
      <div className="mb-4 flex items-center gap-2">
        <Icon className="h-5 w-5 text-accent" />
        <h3 className="text-lg font-semibold text-foreground">{title}</h3>
      </div>
      <p className="mb-4 text-xs text-muted-foreground">{range}</p>
      <p className="text-4xl font-bold text-primary">
        {formatAcc(accuracy, total)}
      </p>
      <p className="mt-2 text-sm text-muted-foreground">
        <span className="font-semibold text-foreground">{correct}</span> correct
        out of <span className="font-semibold text-foreground">{total}</span>{' '}
        finished games
      </p>
    </div>
  );
}
