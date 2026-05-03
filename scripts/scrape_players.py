import requests
from bs4 import BeautifulSoup
import pandas as pd
from io import StringIO
import os

# Change this number to test different amounts — currently testing TOP 5
TOP_N = 3

url = 'https://www.basketball-reference.com/leagues/NBA_2025_per_game.html'
headers = {'User-Agent': 'Mozilla/5.0'}

response = requests.get(url, headers=headers)
soup = BeautifulSoup(response.content, 'lxml')
table = soup.find('table', {'id': 'per_game_stats'})
df = pd.read_html(StringIO(str(table)))[0]

# Drop header repeat rows
df = df[df['Rk'].apply(lambda x: str(x).replace('.','').isdigit())]

# Convert numeric columns
for col in ['MP', 'PTS', 'TRB', 'AST', 'STL', 'BLK', 'TOV', 'FG%', '3P%', 'eFG%', 'G']:
    df[col] = pd.to_numeric(df[col], errors='coerce')

# Keep most recent team for traded players
df = df.drop_duplicates(subset='Player', keep='last')

# Map abbreviations
br_to_our = {
    'ATL': 'ATL', 'BOS': 'BOS', 'BRK': 'BRK', 'CHO': 'CHO', 'CHI': 'CHI',
    'CLE': 'CLE', 'DAL': 'DAL', 'DEN': 'DEN', 'DET': 'DET', 'GSW': 'GSW',
    'HOU': 'HOU', 'IND': 'IND', 'LAC': 'LAC', 'LAL': 'LAL', 'MEM': 'MEM',
    'MIA': 'MIA', 'MIL': 'MIL', 'MIN': 'MIN', 'NOP': 'NOP', 'NYK': 'NYK',
    'OKC': 'OKC', 'ORL': 'ORL', 'PHI': 'PHI', 'PHO': 'PHO', 'POR': 'POR',
    'SAC': 'SAC', 'SAS': 'SAS', 'TOR': 'TOR', 'UTA': 'UTA', 'WAS': 'WAS'
}
df['team'] = df['Team'].map(br_to_our)
df = df.dropna(subset=['team'])

# Only players with 20+ games
df = df[df['G'] >= 20]

# Sort by team then minutes
df = df.sort_values(['team', 'MP'], ascending=[True, False])

# Get top N players per team
topN = df.groupby('team').head(TOP_N).copy()
topN['player_rank'] = topN.groupby('team').cumcount() + 1

# Keep stats we need
topN = topN[['team', 'player_rank', 'Player', 'MP', 'PTS', 'TRB', 'AST', 'STL', 'BLK', 'eFG%', 'TOV']]

# Pivot to one row per team
pivoted = topN.pivot(index='team', columns='player_rank', values=['Player', 'MP', 'PTS', 'TRB', 'AST', 'STL', 'BLK', 'eFG%', 'TOV'])
pivoted.columns = [f'star{col[1]}_{col[0]}' for col in pivoted.columns]
pivoted = pivoted.reset_index()

# Combined features across all top N players
pivoted['top_combined_pts'] = sum(pivoted[f'star{i}_PTS'] for i in range(1, TOP_N + 1))
pivoted['top_combined_ast'] = sum(pivoted[f'star{i}_AST'] for i in range(1, TOP_N + 1))
pivoted['top_combined_reb'] = sum(pivoted[f'star{i}_TRB'] for i in range(1, TOP_N + 1))
pivoted['star1_dominance'] = pivoted['star1_PTS'] / pivoted['top_combined_pts']

# Save
output_path = os.path.join('data', 'nba_player_stats.csv')
pivoted.to_csv(output_path, index=False)

print(f"Done! Top {TOP_N} player stats for {len(pivoted)} teams.")
print(f"Saved to: {output_path}")
print(f"\nSample:")
cols = ['team'] + [f'star{i}_Player' for i in range(1, TOP_N+1)] + ['top_combined_pts']
print(pivoted[cols].head(5).to_string())