import requests
from bs4 import BeautifulSoup
import pandas as pd
from io import StringIO
import time
import os

TEAMS = [
    'ATL', 'BOS', 'BRK', 'CHO', 'CHI', 'CLE', 'DAL', 'DEN', 'DET', 'GSW',
    'HOU', 'IND', 'LAC', 'LAL', 'MEM', 'MIA', 'MIL', 'MIN', 'NOP', 'NYK',
    'OKC', 'ORL', 'PHI', 'PHO', 'POR', 'SAC', 'SAS', 'TOR', 'UTA', 'WAS'
]

SEASONS = [2023, 2024]  # We already have 2025

def scrape_team_season(team, season):
    url = f"https://www.basketball-reference.com/teams/{team}/{season}_games.html"
    headers = {"User-Agent": "Mozilla/5.0"}

    response = requests.get(url, headers=headers)
    if response.status_code != 200:
        print(f"    Failed {team} {season}: {response.status_code}")
        return None

    soup = BeautifulSoup(response.content, 'lxml')
    table = soup.find('table', {'id': 'games'})
    if not table:
        print(f"    No table for {team} {season}")
        return None

    df = pd.read_html(StringIO(str(table)))[0]
    df = df[df['G'].apply(lambda x: str(x).isdigit())]

    df = df.rename(columns={
        'G': 'game_num',
        'Date': 'date',
        'Unnamed: 5': 'home_away',
        'Opponent': 'opponent',
        'Unnamed: 7': 'result',
        'Tm': 'pts_scored',
        'Opp': 'pts_allowed',
        'W': 'wins',
        'L': 'losses',
        'Streak': 'streak'
    })

    keep = ['game_num', 'date', 'home_away', 'opponent', 'result',
            'pts_scored', 'pts_allowed', 'wins', 'losses', 'streak']
    available = [c for c in keep if c in df.columns]
    df = df[available]

    df['home_away'] = df['home_away'].apply(lambda x: 'away' if x == '@' else 'home')
    df['team'] = team
    df['season'] = season
    return df

all_games = []

for season in SEASONS:
    print(f"\nScraping {season-1}-{str(season)[2:]} season...")
    for team in TEAMS:
        print(f"  {team}...", end='', flush=True)
        df = scrape_team_season(team, season)
        if df is not None:
            all_games.append(df)
            print(f" {len(df)} games")
        time.sleep(4)

final_df = pd.concat(all_games, ignore_index=True)

# Only keep completed games
final_df = final_df[final_df['result'].isin(['W', 'L'])]

output_path = os.path.join('data', 'nba_games_historical.csv')
final_df.to_csv(output_path, index=False)

print(f"\nDone! Scraped {len(final_df)} historical game rows")
print(f"Saved to: {output_path}")
print(f"\nRows per season:")
print(final_df.groupby('season').size())