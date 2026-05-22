
import { MatchupCards } from './MatchupCards';
import { Calendar } from 'lucide-react';

const mockMatchups = [
  {
    id: '1',
    date: 'Today, 7:30 PM',
    team1: 'Lakers',
    team2: 'Celtics',
    team1Prob: 45,
    team2Prob: 55,
    confidence: 87,
  },
  {
    id: '2',
    date: 'Today, 9:00 PM',
    team1: 'Nuggets',
    team2: 'Warriors',
    team1Prob: 62,
    team2Prob: 38,
    confidence: 91,
  },
  {
    id: '3',
    date: 'Tomorrow, 6:00 PM',
    team1: 'Heat',
    team2: 'Suns',
    team1Prob: 48,
    team2Prob: 52,
    confidence: 84,
  },
];

export function MatchupsSection() {
  return (
    <section>
      <div className="mb-6 flex items-center gap-3">
        <Calendar className="h-6 w-6 text-accent" />
        <h2 className="text-2xl font-bold text-foreground">Upcoming Matchups</h2>
      </div>
      <MatchupCards matchups={mockMatchups} />
    </section>
  );
}
