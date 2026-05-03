import requests
from bs4 import BeautifulSoup
import pandas as pd
import time
import os
from io import StringIO

TEAMS = [
    'ATL', 'BOS', 'BRK', 'CHO', 'CHI', 'CLE', 'DAL', 'DEN', 'DET', 'GSW',
    'HOU', 'IND', 'LAC', 'LAL', 'MEM', 'MIA', 'MIL', 'MIN', 'NOP', 'NYK',
    'OKC', 'ORL', 'PHI', 'PHO', 'POR', 'SAC', 'SAS', 'TOR', 'UTA', 'WAS'
]

SEASON = 2025

def scrape_team(team):
    url = f"https://www.basketball-reference.com/teams/{team}/{SEASON}_games.html"
    headers = {"User-Agent": "Mozilla/5.0"}

    response = requests.get(url, headers=headers)
    if response.status_code != 200:
        print(f"  Failed to fetch {team}: status {response.status_code}")
        return None

    soup = BeautifulSoup(response.content, 'lxml')
    table = soup.find('table', {'id': 'games'})
    if not table:
        print(f"  No table found for {team}")
        return None

    df = pd.read_html(StringIO(str(table)))[0]

    # Drop header rows repeated inside the table
    df = df[df['G'].apply(lambda x: str(x).isdigit())]

    # Rename the columns we need
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

    # Keep only the columns we need
    keep = ['game_num', 'date', 'home_away', 'opponent', 'result',
            'pts_scored', 'pts_allowed', 'wins', 'losses', 'streak']
    df = df[keep]

    # home_away: @ = away, blank = home
    df['home_away'] = df['home_away'].apply(lambda x: 'away' if x == '@' else 'home')

    df['team'] = team
    return df

all_games = []

for team in TEAMS:
    print(f"Scraping {team}...")
    df = scrape_team(team)
    if df is not None:
        all_games.append(df)
    time.sleep(4)

final_df = pd.concat(all_games, ignore_index=True)

output_path = os.path.join('data', 'nba_games_raw.csv')
final_df.to_csv(output_path, index=False)

print(f"\nDone! Scraped {len(final_df)} rows.")
print(f"Saved to: {output_path}")