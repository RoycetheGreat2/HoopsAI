import requests
from bs4 import BeautifulSoup
import pandas as pd
from io import StringIO
import os

SEASONS = [2023, 2024]  # We already have 2025

def scrape_player_stats(season):
    url = f'https://www.basketball-reference.com/leagues/NBA_{season}_per_game.html'
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

    # Top 3 per team
    top3 = df.groupby('team').head(3).copy()
    top3['player_rank'] = top3.groupby('team').cumcount() + 1

    top3 = top3[['team', 'player_rank', 'Player', 'MP', 'PTS', 'TRB', 'AST',
                  'STL', 'BLK', 'eFG%', 'TOV']]

    # Pivot to one row per team
    pivoted = top3.pivot(index='team', columns='player_rank',
                         values=['Player', 'MP', 'PTS', 'TRB', 'AST', 'STL', 'BLK', 'eFG%', 'TOV'])
    pivoted.columns = [f'star{col[1]}_{col[0]}' for col in pivoted.columns]
    pivoted = pivoted.reset_index()

    # Combined features
    pivoted['top_combined_pts'] = pivoted['star1_PTS'] + pivoted['star2_PTS'] + pivoted['star3_PTS']
    pivoted['top_combined_ast'] = pivoted['star1_AST'] + pivoted['star2_AST'] + pivoted['star3_AST']
    pivoted['top_combined_reb'] = pivoted['star1_TRB'] + pivoted['star2_TRB'] + pivoted['star3_TRB']
    pivoted['star1_dominance'] = pivoted['star1_PTS'] / pivoted['top_combined_pts']
    pivoted['season'] = season

    return pivoted

all_seasons = []

for season in SEASONS:
    print(f"Scraping player stats for {season-1}-{str(season)[2:]}...")
    df = scrape_player_stats(season)
    all_seasons.append(df)
    print(f"  Done! {len(df)} teams")

# Also load 2025
players_2025 = pd.read_csv('data/nba_player_stats.csv')
players_2025['season'] = 2025
all_seasons.append(players_2025)

# Combine all seasons
final = pd.concat(all_seasons, ignore_index=True)

output_path = os.path.join('data', 'nba_player_stats_historical.csv')
final.to_csv(output_path, index=False)

print(f"\nDone! Player stats for {len(final)} team-seasons saved.")
print(f"Saved to: {output_path}")
print(f"\nRows per season:")
print(final.groupby('season').size())
print(f"\nSample 2023 season:")
print(final[final['season']==2023][['team', 'season', 'star1_Player', 'star1_PTS']].head(5).to_string())