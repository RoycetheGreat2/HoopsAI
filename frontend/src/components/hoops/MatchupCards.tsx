
import { ProbabilityBar } from './ProbabilityBar';
import { TrendingUp } from 'lucide-react';

interface MatchupData {
  id: string;
  date: string;
  team1: string;
  team2: string;
  team1Prob: number;
  team2Prob: number;
  confidence: number;
}

interface MatchupCardsProps {
  matchups: MatchupData[];
}

export function MatchupCards({ matchups }: MatchupCardsProps) {
  return (
    <div className="space-y-4">
      {matchups.map((matchup) => (
        <div key={matchup.id} className="card-professional p-6">
          <div className="mb-5 flex items-center justify-between">
            <div>
              <p className="text-xs text-muted-foreground">{matchup.date}</p>
              <h3 className="font-semibold text-foreground">{matchup.team1} vs {matchup.team2}</h3>
            </div>
            <div className="flex items-center gap-2 rounded-lg bg-secondary/10 px-3 py-2">
              <TrendingUp className="h-4 w-4 text-secondary" />
              <span className="text-xs font-semibold text-secondary">{matchup.confidence}%</span>
            </div>
          </div>
          <ProbabilityBar
            team1={matchup.team1}
            team2={matchup.team2}
            team1Prob={matchup.team1Prob}
            team2Prob={matchup.team2Prob}
          />
        </div>
      ))}
    </div>
  );
}
