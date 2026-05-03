import requests
from bs4 import BeautifulSoup
import pandas as pd
from io import StringIO
import time
import os

# Get player list and URLs
print("Fetching player list...")
url = 'https://www.basketball-reference.com/leagues/NBA_2025_per_game.html'
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

print(f"Found {len(player_links)} player URLs")

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
print(f"Top 3 players identified for all 30 teams — {len(top3)} players total")

# Scrape full game log for each player
def scrape_full_gamelog(player_name, href):
    gamelog_url = f"https://www.basketball-reference.com{href.replace('.html', '')}/gamelog/2025/"

    try:
        resp = requests.get(gamelog_url, headers={'User-Agent': 'Mozilla/5.0'})
        if resp.status_code != 200:
            return None

        soup = BeautifulSoup(resp.content, 'lxml')
        table = soup.find('table', {'id': 'player_game_log_reg'})
        if not table:
            return None

        g = pd.read_html(StringIO(str(table)))[0]

        # Drop totals row and non-game rows
        g = g[g['Rk'].apply(lambda x: str(x).strip().isdigit())]

        # Drop inactive/did not play rows
        g = g[g['PTS'].apply(lambda x: str(x).strip().isdigit())]

        # Convert stats
        g['PTS'] = pd.to_numeric(g['PTS'], errors='coerce')
        g['TRB'] = pd.to_numeric(g['TRB'], errors='coerce')
        g['AST'] = pd.to_numeric(g['AST'], errors='coerce')
        g['Date'] = pd.to_datetime(g['Date'], errors='coerce')

        g = g.dropna(subset=['PTS', 'Date'])
        g = g.sort_values('Date').reset_index(drop=True)

        return g[['Date', 'PTS', 'TRB', 'AST']]

    except Exception as e:
        return None

# Scrape all 90 players and save full game logs
all_logs = []
total = len(top3)

for _, row in top3.iterrows():
    player = row['Player']
    team = row['team']
    rank = row['player_rank']

    print(f"[{len(all_logs)+1}/{total}] {team} star{rank}: {player}")

    if player in player_links:
        gamelog = scrape_full_gamelog(player, player_links[player])
        if gamelog is not None and len(gamelog) > 0:
            gamelog['player'] = player
            gamelog['team'] = team
            gamelog['player_rank'] = rank
            all_logs.append(gamelog)
            print(f"    ✅ {len(gamelog)} games scraped")
        else:
            print(f"    ⚠️ No data found")
    else:
        print(f"    ⚠️ No URL found")

    time.sleep(4)

# Combine all game logs
final = pd.concat(all_logs, ignore_index=True)
final = final.sort_values(['team', 'player_rank', 'Date']).reset_index(drop=True)

output_path = os.path.join('data', 'nba_player_gamelogs.csv')
final.to_csv(output_path, index=False)

print(f"\nDone! {len(final)} total player-game rows saved.")
print(f"Saved to: {output_path}")
print(f"\nSample:")
print(final.head(8).to_string())