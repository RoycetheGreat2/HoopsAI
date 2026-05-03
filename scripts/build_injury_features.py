import pandas as pd
import os

# Load all player gamelogs
gamelogs = pd.read_csv('data/nba_player_gamelogs_all.csv')
gamelogs['Date'] = pd.to_datetime(gamelogs['Date'])

# Load all game dates per team per season
df_2025 = pd.read_csv('data/nba_games_raw.csv')
df_2025['season'] = 2025
df_hist = pd.read_csv('data/nba_games_historical.csv')
df_all = pd.concat([df_hist, df_2025], ignore_index=True)
df_all = df_all[df_all['result'].isin(['W', 'L'])].copy()
df_all['date'] = pd.to_datetime(df_all['date'], format='%a, %b %d, %Y')

print(f"Gamelogs: {len(gamelogs)} rows")
print(f"Team games: {len(df_all)} rows")

# Build set of dates each player actually played
player_played = set(
    zip(gamelogs['player'], gamelogs['team'],
        gamelogs['season'], gamelogs['Date'].dt.date)
)
print(f"Player-game appearances: {len(player_played)}")

# Load historical player stats to know who star1/2/3 is per team per season
players = pd.read_csv('data/nba_player_stats_historical.csv')

# For each team game, check if each star played
results = []

for _, row in df_all.iterrows():
    team = row['team']
    date = row['date'].date()
    season = row['season']

    # Get star players for this team this season
    team_players = players[
        (players['team'] == team) & (players['season'] == season)
    ]

    if len(team_players) == 0:
        continue

    tp = team_players.iloc[0]

    # Check each star
    star1_name = tp.get('star1_Player', None)
    star2_name = tp.get('star2_Player', None)
    star3_name = tp.get('star3_Player', None)

    star1_played = 1 if (star1_name, team, season, date) in player_played else 0
    star2_played = 1 if (star2_name, team, season, date) in player_played else 0
    star3_played = 1 if (star3_name, team, season, date) in player_played else 0

    results.append({
        'team': team,
        'date': row['date'],
        'season': season,
        'star1_played': star1_played,
        'star2_played': star2_played,
        'star3_played': star3_played,
        'stars_available': star1_played + star2_played + star3_played,
        'star1_absent': 1 - star1_played,
        'star2_absent': 1 - star2_played,
    })

availability_df = pd.DataFrame(results)

# Sanity check — show some absences
print(f"\nTotal team-game rows: {len(availability_df)}")
print(f"Games where star1 was absent: {availability_df['star1_absent'].sum()}")
print(f"Games where star2 was absent: {availability_df['star2_absent'].sum()}")
print(f"Games where all 3 played: {(availability_df['stars_available']==3).sum()}")

print(f"\nSample absences (star1 out):")
absent = availability_df[availability_df['star1_absent'] == 1].head(10)
print(absent[['team', 'date', 'season', 'star1_played', 'star2_played', 'star3_played']].to_string())

output_path = os.path.join('data', 'nba_player_availability.csv')
availability_df.to_csv(output_path, index=False)
print(f"\nSaved to: {output_path}")