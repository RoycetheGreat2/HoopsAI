import requests
from bs4 import BeautifulSoup
import pandas as pd
from io import StringIO
import os
import time

SEASONS = [2023, 2024, 2025]

name_to_abbrev = {
    'Atlanta Hawks': 'ATL', 'Boston Celtics': 'BOS', 'Brooklyn Nets': 'BRK',
    'Charlotte Hornets': 'CHO', 'Chicago Bulls': 'CHI', 'Cleveland Cavaliers': 'CLE',
    'Dallas Mavericks': 'DAL', 'Denver Nuggets': 'DEN', 'Detroit Pistons': 'DET',
    'Golden State Warriors': 'GSW', 'Houston Rockets': 'HOU', 'Indiana Pacers': 'IND',
    'Los Angeles Clippers': 'LAC', 'Los Angeles Lakers': 'LAL', 'Memphis Grizzlies': 'MEM',
    'Miami Heat': 'MIA', 'Milwaukee Bucks': 'MIL', 'Minnesota Timberwolves': 'MIN',
    'New Orleans Pelicans': 'NOP', 'New York Knicks': 'NYK', 'Oklahoma City Thunder': 'OKC',
    'Orlando Magic': 'ORL', 'Philadelphia 76ers': 'PHI', 'Phoenix Suns': 'PHO',
    'Portland Trail Blazers': 'POR', 'Sacramento Kings': 'SAC', 'San Antonio Spurs': 'SAS',
    'Toronto Raptors': 'TOR', 'Utah Jazz': 'UTA', 'Washington Wizards': 'WAS'
}

all_seasons = []

for season in SEASONS:
    print(f"\nScraping {season-1}-{str(season)[2:]} season...")
    url = f'https://www.basketball-reference.com/leagues/NBA_{season}.html'
    headers = {'User-Agent': 'Mozilla/5.0'}
    soup = BeautifulSoup(requests.get(url, headers=headers).content, 'lxml')

    # --- Per game stats (3PT rate) ---
    pg_table = soup.find('table', {'id': 'per_game-team'})
    pg_df = pd.read_html(StringIO(str(pg_table)))[0]
    pg_df = pg_df[pg_df['Rk'].apply(lambda x: str(x).replace('.','').isdigit())]
    pg_df['Team'] = pg_df['Team'].str.replace('*', '', regex=False).str.strip()
    pg_df['team'] = pg_df['Team'].map(name_to_abbrev)
    pg_df = pg_df.dropna(subset=['team'])

    for col in ['3P', '3PA', '3P%', 'TOV', 'FG%', 'FT', 'FTA']:
        pg_df[col] = pd.to_numeric(pg_df[col], errors='coerce')

    # 3PT rate = 3PA per game / FGA per game
    pg_df['FGA'] = pd.to_numeric(pg_df['FGA'], errors='coerce')
    pg_df['three_pt_rate'] = pg_df['3PA'] / pg_df['FGA']
    pg_df['three_pt_pct'] = pg_df['3P%']
    pg_df['ft_rate'] = pg_df['FTA'] / pg_df['FGA']
    pg_df['tov_per_game'] = pg_df['TOV']

    pg_stats = pg_df[['team', 'three_pt_rate', 'three_pt_pct', 'ft_rate', 'tov_per_game']].copy()

    # --- Advanced stats (Pace, TS%) ---
    adv_table = soup.find('table', {'id': 'advanced-team'})
    adv_df = pd.read_html(StringIO(str(adv_table)))[0]
    adv_df.columns = [
        b if 'Unnamed' in str(a) else f"{a}_{b}"
        for a, b in adv_df.columns
    ]
    adv_df = adv_df[adv_df['Rk'].apply(lambda x: str(x).replace('.','').isdigit())]
    adv_df['Team'] = adv_df['Team'].str.replace('*', '', regex=False).str.strip()
    adv_df['team'] = adv_df['Team'].map(name_to_abbrev)
    adv_df = adv_df.dropna(subset=['team'])

    for col in ['Pace', 'TS%']:
        adv_df[col] = pd.to_numeric(adv_df[col], errors='coerce')

    adv_stats = adv_df[['team', 'Pace', 'TS%']].copy()

    # --- Opponent per game (defensive 3PT allowed) ---
    opp_table = soup.find('table', {'id': 'per_game-opponent'})
    opp_df = pd.read_html(StringIO(str(opp_table)))[0]
    opp_df = opp_df[opp_df['Rk'].apply(lambda x: str(x).replace('.','').isdigit())]
    opp_df['Team'] = opp_df['Team'].str.replace('*', '', regex=False).str.strip()
    opp_df['team'] = opp_df['Team'].map(name_to_abbrev)
    opp_df = opp_df.dropna(subset=['team'])

    opp_df['FGA'] = pd.to_numeric(opp_df['FGA'], errors='coerce')
    opp_df['3PA'] = pd.to_numeric(opp_df['3PA'], errors='coerce')
    opp_df['3P%'] = pd.to_numeric(opp_df['3P%'], errors='coerce')
    opp_df['opp_three_pt_rate_allowed'] = opp_df['3PA'] / opp_df['FGA']
    opp_df['opp_three_pt_pct_allowed'] = opp_df['3P%']

    opp_stats = opp_df[['team', 'opp_three_pt_rate_allowed', 'opp_three_pt_pct_allowed']].copy()

    # Merge all
    season_df = pg_stats.merge(adv_stats, on='team', how='left')
    season_df = season_df.merge(opp_stats, on='team', how='left')
    season_df['season'] = season

    all_seasons.append(season_df)
    print(f"  Done! {len(season_df)} teams")
    print(f"  Sample: {season_df[['team', 'three_pt_rate', 'Pace', 'TS%']].head(3).to_string()}")
    time.sleep(3)

final = pd.concat(all_seasons, ignore_index=True)
output_path = os.path.join('data', 'nba_team_stats.csv')
final.to_csv(output_path, index=False)

print(f"\nDone! {len(final)} team-season rows saved.")
print(f"Saved to: {output_path}")
print(f"\nColumns: {final.columns.tolist()}")