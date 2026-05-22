
import { CheckCircle, XCircle } from 'lucide-react';

interface MatchResultData {
  id: string;
  team1: string;
  team2: string;
  team1Score: number;
  team2Score: number;
  prediction: 'team1' | 'team2';
  correct: boolean;
}

interface MatchResultProps {
  matches: MatchResultData[];
}

export function MatchResult({ matches }: MatchResultProps) {
  return (
    <div className="space-y-4">
      {matches.map((match) => {
        const predictedWinner = match.prediction === 'team1' ? match.team1 : match.team2;
        const actualWinner = match.team1Score > match.team2Score ? match.team1 : match.team2;

        return (
          <div key={match.id} className="card-professional p-6">
            <div className="flex items-center justify-between mb-4">
              <div>
                <h3 className="font-semibold text-foreground">{match.team1} vs {match.team2}</h3>
                <p className="text-sm text-muted-foreground mt-1">
                  {match.team1Score} - {match.team2Score}
                </p>
              </div>
              <div className="flex items-center gap-2">
                {match.correct ? (
                  <>
                    <CheckCircle className="w-5 h-5 text-secondary" />
                    <span className="text-sm font-semibold text-secondary">Correct</span>
                  </>
                ) : (
                  <>
                    <XCircle className="w-5 h-5 text-destructive" />
                    <span className="text-sm font-semibold text-destructive">Incorrect</span>
                  </>
                )}
              </div>
            </div>
            <div className="bg-muted/30 rounded-lg p-3 text-sm text-muted-foreground">
              <p>Predicted: <span className="font-medium text-foreground">{predictedWinner}</span></p>
            </div>
          </div>
        );
      })}
    </div>
  );
}
