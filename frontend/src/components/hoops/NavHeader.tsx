import { useHealth } from '@/hooks/useApi';
import { Activity, AlertCircle, Loader2 } from 'lucide-react';

export function NavHeader() {
  const { phase, message } = useHealth();

  return (
    <header className="sticky top-0 z-40 border-b border-border bg-white shadow-sm">
      <div className="mx-auto flex max-w-7xl items-center justify-between px-4 py-3 sm:px-6 lg:px-8">
        <div>
          <p className="text-lg font-bold tracking-tight text-foreground">
            HoopsAI
          </p>
          <p className="text-xs text-muted-foreground">NBA Win Predictor</p>
        </div>

        <div
          className={`flex items-center gap-2 rounded-full px-3 py-1.5 text-sm font-medium ${
            phase === 'ok'
              ? 'bg-secondary/10 text-secondary'
              : phase === 'loading'
                ? 'bg-muted text-muted-foreground'
                : 'bg-destructive/10 text-destructive'
          }`}
          aria-live="polite"
        >
          {phase === 'loading' && (
            <Loader2 className="h-4 w-4 animate-spin" aria-hidden />
          )}
          {phase === 'ok' && <Activity className="h-4 w-4" aria-hidden />}
          {phase === 'error' && <AlertCircle className="h-4 w-4" aria-hidden />}
          {message}
        </div>
      </div>
    </header>
  );
}
