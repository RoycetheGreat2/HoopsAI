import { useState, useMemo } from 'react';
import { WeekDateCarousel } from './components/hoops/WeekDateCarousel';
import { GameCard } from './components/hoops/GameCard';
import { RightSidebar } from './components/hoops/RightSidebar';
import { PerformancePanel } from './components/hoops/PerformancePanel';
import {
  useWeeklyPredictions,
  useHealth,
  buildGamesForDate,
  resolvedTimeZone,
  localYmd,
  clampYmd,
  compareYmd,
} from './hooks/useApi';
import { TRACKING_SINCE } from './config';
import { Loader2, AlertTriangle, RefreshCw } from 'lucide-react';

const HERO_IMAGE = '/images/court-hero.jpg';

function initialWeekStart(): string {
  const today = localYmd();
  return clampYmd(today, TRACKING_SINCE, today);
}

export default function App() {
  const today = localYmd();
  const [viewWeekStart, setViewWeekStart] = useState(initialWeekStart);
  const [selectedDate, setSelectedDate] = useState(() =>
    clampYmd(today, TRACKING_SINCE, today)
  );
  const [activeTab, setActiveTab] = useState<'games' | 'statistics'>('games');

  const userTimeZone = useMemo(() => resolvedTimeZone(), []);
  const { phase: apiPhase } = useHealth();
  const { loading, error, data: payload, retry } = useWeeklyPredictions(
    viewWeekStart
  );

  const { upcoming, finished } = useMemo(
    () => buildGamesForDate(payload, selectedDate, userTimeZone),
    [payload, selectedDate, userTimeZone]
  );

  const allGames = [...finished, ...upcoming];
  const apiOnline = apiPhase === 'ok' && !error;

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
          <div
            className={`mb-6 inline-flex items-center gap-2 rounded-full border px-4 py-2 backdrop-blur-sm ${
              apiOnline
                ? 'border-white/20 bg-white/10'
                : 'border-amber-400/40 bg-amber-500/20'
            }`}
          >
            <span
              className={`h-2 w-2 rounded-full ${
                apiOnline ? 'animate-pulse bg-green-400' : 'bg-amber-400'
              }`}
            />
            <span className="text-sm font-medium text-white/90">
              {apiOnline ? 'Live predictions active' : 'Start the API to load games'}
            </span>
          </div>
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
            setSelectedDate(clampYmd(d, TRACKING_SINCE, today))
          }
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
