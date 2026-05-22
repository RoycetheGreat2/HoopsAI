
interface ProbabilityBarProps {
  team1: string;
  team2: string;
  team1Prob: number;
  team2Prob: number;
}

export function ProbabilityBar({ team1, team2, team1Prob, team2Prob }: ProbabilityBarProps) {
  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <span className="text-sm font-medium text-foreground">{team1}</span>
        <span className="text-sm font-semibold text-accent">{team1Prob}%</span>
      </div>
      <div className="relative h-2 w-full overflow-hidden rounded-full bg-muted">
        <div
          className="h-full bg-accent transition-all duration-500"
          style={{ width: `${team1Prob}%` }}
        />
      </div>
      <div className="flex items-center justify-between">
        <span className="text-sm font-medium text-foreground">{team2}</span>
        <span className="text-sm font-semibold text-primary">{team2Prob}%</span>
      </div>
      <div className="relative h-2 w-full overflow-hidden rounded-full bg-muted">
        <div
          className="h-full bg-primary transition-all duration-500"
          style={{ width: `${team2Prob}%` }}
        />
      </div>
    </div>
  );
}
