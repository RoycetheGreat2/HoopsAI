import { useState, useMemo } from 'react';
import { WeekDateCarousel } from './components/hoops/WeekDateCarousel';
import { GameCard } from './components/hoops/GameCard';
import { RightSidebar } from './components/hoops/RightSidebar';
import { PerformancePanel } from './components/hoops/PerformancePanel';
import {
  useWeeklyPredictions,
  buildGamesForDate,
  resolvedTimeZone,
  localYmd,
  clampYmd,
  compareYmd,
  addDaysYmd,
  daysBetweenYmd,
} from './hooks/useApi';
import { TRACKING_SINCE } from './config';
import { Loader2, AlertTriangle, RefreshCw } from 'lucide-react';

const HERO_IMAGE = '/images/court-hero.jpg';

function maxSelectableDate(today: string): string {
  return addDaysYmd(today, 6);
}

/** First day of the 7-day strip — keeps launch day visible for two weeks after tracking starts. */
function initialWeekStart(today: string): string {
  const maxD = maxSelectableDate(today);
  const maxWeekStart = addDaysYmd(maxD, -6);
  if (daysBetweenYmd(TRACKING_SINCE, today) <= 13) {
    return clampYmd(TRACKING_SINCE, TRACKING_SINCE, maxWeekStart);
  }
  return clampYmd(addDaysYmd(today, -6), TRACKING_SINCE, maxWeekStart);
}

export default function App() {
  const today = localYmd();
  const maxDate = maxSelectableDate(today);
  const [viewWeekStart, setViewWeekStart] = useState(() => initialWeekStart(today));
  const [selectedDate, setSelectedDate] = useState(() =>
    clampYmd(today, TRACKING_SINCE, maxDate)
  );
  const [activeTab, setActiveTab] = useState<'games' | 'statistics'>('games');

  const userTimeZone = useMemo(() => resolvedTimeZone(), []);
  const { loading, error, data: payload, retry } = useWeeklyPredictions(
    viewWeekStart
  );

  const { upcoming, finished } = useMemo(
    () => buildGamesForDate(payload, selectedDate, userTimeZone),
    [payload, selectedDate, userTimeZone]
  );

  const allGames = [...finished, ...upcoming];

  return (
    <main className="min-h-screen bg-[#F8F9FA]">
      <section className="relative h-screen w-full overflow-hidden">
        <img
          src={HERO_IMAGE}
          alt=""
          className="absolute inset-0 h-full w-full object-cover"
        />
        <div className="absolute inset-0 bg-black/50" aria-hidden />
        <div className="absolute inset-0 flex flex-col items-center justify-center px-4 text-center">
          <h1 className="text-5xl font-bold tracking-tight text-white drop-shadow-lg md:text-7xl lg:text-8xl">
            Predict the Game
          </h1>
          <p className="mt-4 max-w-2xl text-lg text-white/85 md:text-2xl">
            AI-powered NBA match predictions with advanced analytics
          </p>
        </div>
      </section>

      <div className="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8">
        <WeekDateCarousel
          selectedDate={selectedDate}
          onDateChange={(d) =>
            setSelectedDate(clampYmd(d, TRACKING_SINCE, maxDate))
          }
          maxSelectableDate={maxDate}
          viewWeekStart={viewWeekStart}
          onViewWeekStartChange={setViewWeekStart}
        />

        <div className="mb-6 flex gap-8 border-b border-border">
          {(['games', 'statistics'] as const).map((tab) => (
            <button
              key={tab}
              type="button"
              onClick={() => setActiveTab(tab)}
              className={`relative pb-3 text-sm font-medium capitalize transition-colors ${
                activeTab === tab
                  ? 'text-primary'
                  : 'text-muted-foreground hover:text-foreground'
              }`}
            >
              {tab}
              {activeTab === tab && (
                <div className="absolute bottom-0 left-0 right-0 h-1 rounded-t-full bg-primary" />
              )}
            </button>
          ))}
        </div>

        <div className="grid grid-cols-1 gap-8 lg:grid-cols-3">
          <div className="lg:col-span-2">
            {activeTab === 'games' && (
              <div className="space-y-6">
                {compareYmd(selectedDate, TRACKING_SINCE) < 0 && (
                  <div className="rounded-lg border border-border bg-white p-8 text-center text-muted-foreground">
                    Data is only available from {TRACKING_SINCE} onward.
                  </div>
                )}

                {loading && compareYmd(selectedDate, TRACKING_SINCE) >= 0 && (
                  <div className="rounded-lg border border-border bg-white p-16 text-center">
                    <Loader2 className="mx-auto mb-4 h-8 w-8 animate-spin text-primary" />
                    <p className="text-lg text-muted-foreground">
                      Loading schedule and predictions…
                    </p>
                  </div>
                )}

                {!loading && error && (
                  <div className="rounded-lg border border-destructive/30 bg-white p-8 sm:p-12">
                    <div className="text-center">
                      <AlertTriangle className="mx-auto mb-4 h-8 w-8 text-destructive" />
                      <h3 className="mb-2 text-lg font-semibold text-foreground">
                        Could not reach the API
                      </h3>
                      <p className="mb-4 text-muted-foreground">{error}</p>
                      <button
                        type="button"
                        onClick={retry}
                        className="inline-flex items-center gap-2 rounded-lg bg-primary px-6 py-2 font-medium text-white hover:bg-primary/90"
                      >
                        <RefreshCw className="h-4 w-4" />
                        Retry
                      </button>
                    </div>
                    <ApiStartInstructions />
                  </div>
                )}

                {!loading &&
                  !error &&
                  compareYmd(selectedDate, TRACKING_SINCE) >= 0 &&
                  allGames.length > 0 &&
                  allGames.map((game, idx) => (
                    <GameCard
                      key={`${game.away}-${game.home}-${game.utc_time || idx}`}
                      game={game}
                      timeZone={userTimeZone}
                    />
                  ))}

                {!loading &&
                  !error &&
                  compareYmd(selectedDate, TRACKING_SINCE) >= 0 &&
                  allGames.length === 0 && (
                    <div className="rounded-lg border border-border bg-white p-12 text-center">
                      <p className="text-lg text-muted-foreground">
                        No games on this date
                      </p>
                      <p className="mt-2 text-sm text-muted-foreground">
                        Use the calendar or arrows to pick another day
                      </p>
                    </div>
                  )}
              </div>
            )}

            {activeTab === 'statistics' && <PerformancePanel />}
          </div>

          <div className="lg:col-span-1">
            <RightSidebar predictions={payload} />
          </div>
        </div>
      </div>

      <footer className="mt-16 border-t border-border bg-white">
        <div className="mx-auto max-w-7xl px-4 py-8 text-center text-sm text-muted-foreground sm:px-6 lg:px-8">
          <p className="mb-1 font-medium text-foreground">
            HoopsAI — NBA Win Predictor
          </p>
          <p>Tracking since {TRACKING_SINCE}</p>
        </div>
      </footer>
    </main>
  );
}

function ApiStartInstructions() {
  return (
    <div className="mt-8 rounded-lg border border-border bg-muted/40 p-5 text-left text-sm">
      <p className="mb-3 font-semibold text-foreground">Start the Flask API</p>
      <ol className="list-decimal space-y-2 pl-5 text-muted-foreground">
        <li>New PowerShell: <code className="text-foreground">cd C:\Users\Cinnamoroll\nba-win-predictor</code></li>
        <li><code className="text-foreground">.\venv\Scripts\activate</code></li>
        <li><code className="text-foreground">python app.py</code></li>
        <li>Keep it running, then Retry</li>
      </ol>
    </div>
  );
}
