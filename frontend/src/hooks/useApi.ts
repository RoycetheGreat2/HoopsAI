import { useState, useEffect, useCallback } from 'react';

/* ------------------------------------------------------------------ */
/*  Types matching Flask API responses from app.py                    */
/* ------------------------------------------------------------------ */

export interface GamePrediction {
  away: string;
  home: string;
  away_logo: string;
  home_logo: string;
  away_win_probability: number;
  home_win_probability: number;
  predicted_winner: string;
  status: string; // 'pre' | 'in' | 'post'
  home_score: number;
  away_score: number;
  actual_winner: string | null;
  season_type: number;
  utc_time?: string;
}

export interface DayData {
  date: string;
  games: GamePrediction[];
}

export interface WeeklyPredictions {
  week_start: string;
  week_end: string;
  tracking_since?: string;
  days: DayData[];
}

export interface AccuracyWindow {
  start: string;
  end: string;
  correct: number;
  total: number;
  accuracy: number | null;
}

export interface PredictionAccuracy {
  tracking_since: string;
  week: AccuracyWindow;
  month: AccuracyWindow;
}

export interface TopFeature {
  rank: number;
  feature: string;
  importance: number;
}

export interface ModelStats {
  accuracy: number;
  forward_validation_accuracy_pct: number;
  auc_roc: number;
  brier_score: number;
  num_features: number;
  top_features: TopFeature[];
}

export interface SeriesGame {
  date: string;
  predicted_winner: string;
  actual_winner: string;
  home_win_probability: number;
  away_win_probability: number;
  correct: boolean;
}

export interface PlayoffSeries {
  series: string;
  team_a: string;
  team_b: string;
  games_played: number;
  games_correct: number;
  accuracy: number | null;
  games: SeriesGame[];
}

export interface PlayoffStats {
  season: string;
  total_games: number;
  correct: number;
  accuracy: number | null;
  by_series: PlayoffSeries[];
  is_active: boolean;
}

export interface HealthStatus {
  status: string;
  timestamp: string;
}

/* ------------------------------------------------------------------ */
/*  API base URL (production: set VITE_API_URL at build time)         */
/* ------------------------------------------------------------------ */

const API_BASE = (import.meta.env.VITE_API_URL ?? '').replace(/\/$/, '');

function apiUrl(path: string): string {
  const normalized = path.startsWith('/') ? path : `/${path}`;
  return API_BASE ? `${API_BASE}${normalized}` : normalized;
}

/* ------------------------------------------------------------------ */
/*  Generic fetch helper                                              */
/* ------------------------------------------------------------------ */

async function apiFetch<T>(url: string, timeoutMs = 30000): Promise<T> {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);
  try {
    const res = await fetch(apiUrl(url), { signal: controller.signal });
    if (!res.ok) {
      const body = await res.json().catch(() => ({}));
      throw new Error(
        (body as Record<string, string>).error ||
          (body as Record<string, string>).detail ||
          `HTTP ${res.status}`
      );
    }
    return (await res.json()) as T;
  } finally {
    clearTimeout(timer);
  }
}

/* ------------------------------------------------------------------ */
/*  Hooks                                                             */
/* ------------------------------------------------------------------ */

export function useHealth(pollMs = 30_000) {
  const [phase, setPhase] = useState<'loading' | 'ok' | 'error'>('loading');
  const [message, setMessage] = useState('Checking API…');

  const check = useCallback(async () => {
    try {
      const data = await apiFetch<HealthStatus>('/api/health', 8000);
      if (data?.status === 'ok') {
        setPhase('ok');
        setMessage('API Connected');
      } else {
        setPhase('error');
        setMessage('API Offline');
      }
    } catch {
      setPhase('error');
      setMessage('API Offline');
    }
  }, []);

  useEffect(() => {
    check();
    const id = setInterval(check, pollMs);
    return () => clearInterval(id);
  }, [check, pollMs]);

  return { phase, message };
}

export function useWeeklyPredictions(weekStart?: string) {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [data, setData] = useState<WeeklyPredictions | null>(null);
  const [retryKey, setRetryKey] = useState(0);

  const retry = useCallback(() => setRetryKey((k) => k + 1), []);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      setLoading(true);
      setError(null);
      setData(null);
      try {
        const qs = weekStart ? `?start=${encodeURIComponent(weekStart)}` : '';
        const res = await apiFetch<WeeklyPredictions>(
          `/api/weekly-predictions${qs}`,
          60000
        );
        if (!cancelled) setData(res);
      } catch (e: unknown) {
        if (!cancelled) {
          setError(
            e instanceof Error ? e.message : 'Something went wrong loading this week.'
          );
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [retryKey, weekStart]);

  return { loading, error, data, retry };
}

export function usePredictionAccuracy() {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [data, setData] = useState<PredictionAccuracy | null>(null);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      setLoading(true);
      setError(null);
      try {
        const res = await apiFetch<PredictionAccuracy>(
          '/api/prediction-accuracy',
          12000
        );
        if (!cancelled) setData(res);
      } catch (e: unknown) {
        if (!cancelled) {
          setError(
            e instanceof Error
              ? e.message
              : 'Could not load prediction accuracy.'
          );
          setData(null);
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  return { loading, error, data };
}

export function useModelStats() {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [data, setData] = useState<ModelStats | null>(null);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      setLoading(true);
      setError(null);
      try {
        const res = await apiFetch<ModelStats>('/api/model-stats', 12000);
        if (!cancelled) setData(res);
      } catch (e: unknown) {
        if (!cancelled) {
          setError(
            e instanceof Error ? e.message : 'Could not load model statistics.'
          );
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  return { loading, error, data };
}

export function usePlayoffStats(refreshKey?: string) {
  const [data, setData] = useState<PlayoffStats | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      setError(null);
      try {
        const res = await apiFetch<PlayoffStats>('/api/playoff-stats', 15000);
        if (!cancelled) setData(res);
      } catch (e: unknown) {
        if (!cancelled) {
          setError(e instanceof Error ? e.message : 'Failed to load playoff stats');
          setData(null);
        }
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [refreshKey]);

  return { data, error };
}

/* ------------------------------------------------------------------ */
/*  Date helpers (ported from old App.jsx)                            */
/* ------------------------------------------------------------------ */

export function localYmd(d: Date = new Date()): string {
  const p = (x: number) => String(x).padStart(2, '0');
  return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())}`;
}

export function parseYmd(ymd: string): Date {
  const [y, m, d] = ymd.split('-').map(Number);
  return new Date(y, m - 1, d, 12, 0, 0, 0);
}

export function addDaysYmd(ymd: string, days: number): string {
  const d = parseYmd(ymd);
  d.setDate(d.getDate() + days);
  return localYmd(d);
}

export function compareYmd(a: string, b: string): number {
  return a.localeCompare(b);
}

/** Clamp date to [since, maxYmd] (maxYmd defaults to today). */
export function clampYmd(ymd: string, since: string, maxYmd?: string): string {
  const t = maxYmd ?? localYmd();
  if (compareYmd(ymd, since) < 0) return since;
  if (compareYmd(ymd, t) > 0) return t;
  return ymd;
}

/** First day of the 7-day strip containing `ymd` (anchor = ymd). */
export function weekAnchorFrom(ymd: string): string {
  return ymd;
}

export function isGameCorrect(g: GamePrediction): boolean | null {
  if (g.status !== 'post' || g.actual_winner == null) return null;
  return g.predicted_winner === g.actual_winner;
}

export function iterateFinishedGames(
  payload: WeeklyPredictions | null,
  timeZone: string,
  since: string
): Array<GamePrediction & { localDate: string }> {
  const out: Array<GamePrediction & { localDate: string }> = [];
  if (!payload?.days) return out;
  for (const day of payload.days) {
    for (const g of day.games || []) {
      let ymd = localYmdFromUtcIso(g.utc_time, timeZone);
      if (!ymd) ymd = day.date?.slice(0, 10) ?? '';
      if (!ymd || compareYmd(ymd, since) < 0) continue;
      if (g.status === 'post' && g.actual_winner != null) {
        out.push({ ...g, localDate: ymd });
      }
    }
  }
  return out;
}

export function resolvedTimeZone(): string {
  try {
    return Intl.DateTimeFormat().resolvedOptions().timeZone || 'UTC';
  } catch {
    return 'UTC';
  }
}

export function localYmdFromUtcIso(
  iso: string | undefined,
  timeZone: string
): string | null {
  if (!iso || typeof iso !== 'string') return null;
  const t = Date.parse(iso);
  if (Number.isNaN(t)) return null;
  return new Intl.DateTimeFormat('en-CA', {
    timeZone,
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
  }).format(new Date(t));
}

export function formatLocalDayHeading(ymd: string): string {
  const [y, m, d] = ymd.split('-').map(Number);
  const dt = new Date(y, m - 1, d, 12, 0, 0, 0);
  const weekday = dt.toLocaleDateString('en-US', { weekday: 'long' });
  const rest = dt.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
  return `${weekday} · ${rest}`;
}

/**
 * Group all games from the weekly payload by viewer-local date,
 * and partition each day into upcoming / finished.
 */
export function buildGamesForDate(
  payload: WeeklyPredictions | null,
  dateKey: string,
  timeZone: string
): { upcoming: GamePrediction[]; finished: GamePrediction[] } {
  const upcoming: GamePrediction[] = [];
  const finished: GamePrediction[] = [];

  if (!payload?.days) return { upcoming, finished };

  for (const day of payload.days) {
    for (const g of day.games || []) {
      // Determine the viewer-local date for this game
      let ymd = localYmdFromUtcIso(g.utc_time, timeZone);
      if (!ymd) ymd = day.date?.slice(0, 10) ?? '';

      if (compareYmd(ymd, dateKey) !== 0) continue;

      if (g.status === 'post') {
        finished.push(g);
      } else {
        upcoming.push(g);
      }
    }
  }

  return { upcoming, finished };
}

/**
 * Get all unique viewer-local dates from the payload.
 */
export function getAvailableDates(
  payload: WeeklyPredictions | null,
  timeZone: string
): string[] {
  const dateSet = new Set<string>();
  if (!payload?.days) return [];

  for (const day of payload.days) {
    for (const g of day.games || []) {
      let ymd = localYmdFromUtcIso(g.utc_time, timeZone);
      if (!ymd) ymd = day.date?.slice(0, 10) ?? '';
      if (ymd) dateSet.add(ymd);
    }
  }

  return [...dateSet].sort();
}

/**
 * Format a tip-off time from a UTC ISO string in the viewer's timezone.
 */
export function formatTipoff(
  utcTime: string | undefined,
  timeZone: string
): string | null {
  if (!utcTime) return null;
  const t = Date.parse(utcTime);
  if (Number.isNaN(t)) return null;
  return new Intl.DateTimeFormat(undefined, {
    timeZone,
    hour: 'numeric',
    minute: '2-digit',
  }).format(new Date(t));
}
