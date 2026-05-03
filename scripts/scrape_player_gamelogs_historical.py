import requests
from bs4 import BeautifulSoup
import pandas as pd
from io import StringIO
import time
import os

# We need to scrape gamelogs for 2023 and 2024 seasons
# 2025 already exists in nba_player_gamelogs.csv

SEASONS_TO_SCRAPE = [2023, 2024]

def get_player_list(season):
    url = f'https://www.basketball-reference.com/leagues/NBA_{season}_per_game.html'
    headers = {'User-Agent': 'Mozilla/5.0'}
    response = requests.get(url, headers=headers)
    soup = BeautifulSoup(response.content, 'lxml')
    table = soup.find('table', {'id': 'per_game_stats'})
    df = pd.read_html(StringIO(str(table)))[0]

    # Get player URLs
    player_links = {}
    for row in table.find_all('tr'):
        td = row.find('td', {'data-stat': 'name_display'})
        if td and td.find('a'):
            name = td.find('a').text.strip()
            href = td.find('a')['href']
            player_links[name] = href

    # Clean dataframe
    df = df[df['Rk'].apply(lambda x: str(x).replace('.','').isdigit())]
    for col in ['MP', 'PTS', 'TRB', 'AST', 'G']:
        df[col] = pd.to_numeric(df[col], errors='coerce')
    df = df.drop_duplicates(subset='Player', keep='last')

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
    df = df[df['G'] >= 20]
    df = df.sort_values(['team', 'MP'], ascending=[True, False])

    top3 = df.groupby('team').head(3).copy()
    top3['player_rank'] = top3.groupby('team').cumcount() + 1
    return top3, player_links

def scrape_gamelog(player_name, href, season):
    gamelog_url = f"https://www.basketball-reference.com{href.replace('.html','')}/gamelog/{season}/"
    try:
        resp = requests.get(gamelog_url, headers={'User-Agent': 'Mozilla/5.0'})
        if resp.status_code != 200:
            return None
        soup = BeautifulSoup(resp.content, 'lxml')
        table = soup.find('table', {'id': 'player_game_log_reg'})
        if not table:
            return None
        g = pd.read_html(StringIO(str(table)))[0]
        g = g[g['Rk'].apply(lambda x: str(x).strip().isdigit())]
        g = g[g['PTS'].apply(lambda x: str(x).strip().isdigit())]
        g['PTS'] = pd.to_numeric(g['PTS'], errors='coerce')
        g['TRB'] = pd.to_numeric(g['TRB'], errors='coerce')
        g['AST'] = pd.to_numeric(g['AST'], errors='coerce')
        g['Date'] = pd.to_datetime(g['Date'], errors='coerce')
        g = g.dropna(subset=['PTS', 'Date'])
        g = g.sort_values('Date').reset_index(drop=True)
        return g[['Date', 'PTS', 'TRB', 'AST']]
    except:
        return None

all_logs = []

for season in SEASONS_TO_SCRAPE:
    print(f"\nScraping {season-1}-{str(season)[2:]} season player gamelogs...")
    top3, player_links = get_player_list(season)
    print(f"  Found {len(top3)} player-team combinations")
    time.sleep(4)  # Pause after fetching the list

    total = len(top3)
    for idx, (_, row) in enumerate(top3.iterrows()):
        player = row['Player']
        team = row['team']
        rank = row['player_rank']
        print(f"  [{idx+1}/{total}] {team} star{rank}: {player}", end='')

        if player in player_links:
            gamelog = scrape_gamelog(player, player_links[player], season)
            if gamelog is not None and len(gamelog) > 0:
                gamelog['player'] = player
                gamelog['team'] = team
                gamelog['player_rank'] = rank
                gamelog['season'] = season
                all_logs.append(gamelog)
                print(f" ✅ {len(gamelog)} games")
            else:
                print(f" ⚠️ No data")
        else:
            print(f" ⚠️ No URL")
        time.sleep(4)

# Combine with existing 2025 data
print("\nLoading existing 2025 gamelogs...")
df_2025 = pd.read_csv('data/nba_player_gamelogs.csv')
df_2025['season'] = 2025
df_2025['Date'] = pd.to_datetime(df_2025['Date'])

# Combine all seasons
if all_logs:
    hist_df = pd.concat(all_logs, ignore_index=True)
    final = pd.concat([hist_df, df_2025], ignore_index=True)
else:
    final = df_2025

output_path = os.path.join('data', 'nba_player_gamelogs_all.csv')
final.to_csv(output_path, index=False)

print(f"\nDone! {len(final)} total player-game rows")
print(f"Saved to: {output_path}")
print(f"\nRows per season:")
print(final.groupby('season').size())
print(f"\nSample:")
print(final.head(5).to_string())