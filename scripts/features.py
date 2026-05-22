import pandas as pd
import numpy as np
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from season_utils import nba_season_end_year

# Load historical + current-season raw games
df_hist = pd.read_csv('data/nba_games_historical.csv')
df_raw = pd.read_csv('data/nba_games_raw.csv')
df_raw['date'] = pd.to_datetime(df_raw['date'], format='%a, %b %d, %Y', errors='coerce')
df_raw['season'] = df_raw['date'].apply(nba_season_end_year)
df_raw = df_raw.dropna(subset=['season'])
df_raw['season'] = df_raw['season'].astype(int)
df = pd.concat([df_hist, df_raw], ignore_index=True)

players = pd.read_csv('data/nba_player_stats_historical.csv')
team_stats = pd.read_csv('data/nba_team_stats.csv')

# Drop unplayed games
df = df[df['result'].isin(['W', 'L'])].copy()

# Convert types
df['pts_scored'] = pd.to_numeric(df['pts_scored'], errors='coerce')
df['pts_allowed'] = pd.to_numeric(df['pts_allowed'], errors='coerce')
df['wins'] = pd.to_numeric(df['wins'], errors='coerce')
df['losses'] = pd.to_numeric(df['losses'], errors='coerce')
df = df.dropna(subset=['pts_scored', 'pts_allowed'])

# Binary columns
df['result_binary'] = df['result'].apply(lambda x: 1 if x == 'W' else 0)
df['is_home'] = df['home_away'].apply(lambda x: 1 if x == 'home' else 0)

# Date and sorting (raw rows may already be parsed; historical uses B-Ref string format)
df['date'] = pd.to_datetime(df['date'], format='%a, %b %d, %Y', errors='coerce')
if df['date'].isna().any():
    df['date'] = pd.to_datetime(df['date'], errors='coerce')
df = df.dropna(subset=['date'])
df = df.sort_values(['team', 'date']).reset_index(drop=True)

# Base stats
df['point_diff'] = df['pts_scored'] - df['pts_allowed']
df['total_games'] = df['wins'] + df['losses']
df['win_pct'] = df['wins'] / df['total_games'].replace(0, 1)

# Rolling last 5
df['win_rate_last5'] = df.groupby('team')['result_binary'].transform(lambda x: x.shift(1).rolling(5, min_periods=1).mean())
df['avg_pts_last5'] = df.groupby('team')['pts_scored'].transform(lambda x: x.shift(1).rolling(5, min_periods=1).mean())
df['avg_pts_allowed_last5'] = df.groupby('team')['pts_allowed'].transform(lambda x: x.shift(1).rolling(5, min_periods=1).mean())
df['point_diff_last5'] = df.groupby('team')['point_diff'].transform(lambda x: x.shift(1).rolling(5, min_periods=1).mean())

# Rolling last 10
df['win_rate_last10'] = df.groupby('team')['result_binary'].transform(lambda x: x.shift(1).rolling(10, min_periods=1).mean())
df['avg_pts_last10'] = df.groupby('team')['pts_scored'].transform(lambda x: x.shift(1).rolling(10, min_periods=1).mean())
df['avg_pts_allowed_last10'] = df.groupby('team')['pts_allowed'].transform(lambda x: x.shift(1).rolling(10, min_periods=1).mean())
df['point_diff_last10'] = df.groupby('team')['point_diff'].transform(lambda x: x.shift(1).rolling(10, min_periods=1).mean())

# Net rating
df['net_rating'] = df['avg_pts_last10'] - df['avg_pts_allowed_last10']
df['net_rating_last5'] = df['avg_pts_last5'] - df['avg_pts_allowed_last5']

# Home/away win rates
df['is_home_result'] = df['result_binary'] * df['is_home']
df['is_away_result'] = df['result_binary'] * (1 - df['is_home'])
df['home_win_rate'] = df.groupby('team')['is_home_result'].transform(lambda x: x.shift(1).rolling(10, min_periods=1).mean())
df['away_win_rate'] = df.groupby('team')['is_away_result'].transform(lambda x: x.shift(1).rolling(10, min_periods=1).mean())

# Streak
def parse_streak(s):
    try:
        parts = str(s).strip().split()
        num = int(parts[1])
        return num if parts[0] == 'W' else -num
    except:
        return 0

df['streak_value'] = df['streak'].apply(parse_streak)
df['streak_entering_game'] = df.groupby('team')['streak_value'].shift(1).fillna(0)

# Days of rest
df['days_rest'] = df.groupby('team')['date'].diff().dt.days.fillna(3).clip(1, 7)

df = df.dropna(subset=['win_rate_last5', 'avg_pts_last5'])

# Team name mapping
abbrev_to_name = {
    'ATL': 'Atlanta Hawks', 'BOS': 'Boston Celtics', 'BRK': 'Brooklyn Nets',
    'CHO': 'Charlotte Hornets', 'CHI': 'Chicago Bulls', 'CLE': 'Cleveland Cavaliers',
    'DAL': 'Dallas Mavericks', 'DEN': 'Denver Nuggets', 'DET': 'Detroit Pistons',
    'GSW': 'Golden State Warriors', 'HOU': 'Houston Rockets', 'IND': 'Indiana Pacers',
    'LAC': 'Los Angeles Clippers', 'LAL': 'Los Angeles Lakers', 'MEM': 'Memphis Grizzlies',
    'MIA': 'Miami Heat', 'MIL': 'Milwaukee Bucks', 'MIN': 'Minnesota Timberwolves',
    'NOP': 'New Orleans Pelicans', 'NYK': 'New York Knicks', 'OKC': 'Oklahoma City Thunder',
    'ORL': 'Orlando Magic', 'PHI': 'Philadelphia 76ers', 'PHO': 'Phoenix Suns',
    'POR': 'Portland Trail Blazers', 'SAC': 'Sacramento Kings', 'SAS': 'San Antonio Spurs',
    'TOR': 'Toronto Raptors', 'UTA': 'Utah Jazz', 'WAS': 'Washington Wizards'
}
name_to_abbrev = {v: k for k, v in abbrev_to_name.items()}

# Multi-season ELO with regression
K = 20
INITIAL_ELO = 1500
REGRESSION = 0.33

all_teams = df['team'].unique()
elo_ratings = {team: INITIAL_ELO for team in all_teams}

df_sorted = df.sort_values('date').reset_index(drop=True)
home_games = df_sorted[df_sorted['is_home'] == 1][
    ['date', 'team', 'opponent', 'result_binary', 'season']
].copy()
home_games['opp_abbrev'] = home_games['opponent'].map(name_to_abbrev)
home_games = home_games.dropna(subset=['opp_abbrev'])

elo_before = {}
current_season = None

for _, row in home_games.iterrows():
    home_team = row['team']
    away_team = row['opp_abbrev']
    date = row['date']
    home_won = row['result_binary']
    season = row['season']

    if current_season is not None and season != current_season:
        for team in elo_ratings:
            elo_ratings[team] = elo_ratings[team] * (1 - REGRESSION) + INITIAL_ELO * REGRESSION

    current_season = season
    elo_before[(date, home_team)] = elo_ratings[home_team]
    elo_before[(date, away_team)] = elo_ratings[away_team]

    home_elo = elo_ratings[home_team]
    away_elo = elo_ratings[away_team]
    expected_home = 1 / (1 + 10 ** ((away_elo - home_elo) / 400))
    expected_away = 1 - expected_home

    if home_won:
        elo_ratings[home_team] += K * (1 - expected_home)
        elo_ratings[away_team] += K * (0 - expected_away)
    else:
        elo_ratings[home_team] += K * (0 - expected_home)
        elo_ratings[away_team] += K * (1 - expected_away)

df_sorted['elo'] = df_sorted.apply(
    lambda row: elo_before.get((row['date'], row['team']), INITIAL_ELO), axis=1
)

print("Final ELO top 5:")
final_elo = pd.DataFrame(list(elo_ratings.items()), columns=['team', 'final_elo'])
print(final_elo.sort_values('final_elo', ascending=False).head(5).to_string())

df = df.merge(df_sorted[['date', 'team', 'elo']], on=['date', 'team'], how='left')
df['elo'] = df['elo'].fillna(INITIAL_ELO)
df['opp_abbrev'] = df['opponent'].map(name_to_abbrev)

# Opponent ELO strength last 10
elo_lookup = df.set_index(['date', 'team'])['elo'].to_dict()
df['opp_elo_today'] = df.apply(
    lambda row: elo_lookup.get((row['date'], row['opp_abbrev']), INITIAL_ELO), axis=1
)
df['opp_strength_last10'] = df.groupby('team')['opp_elo_today'].transform(
    lambda x: x.shift(1).rolling(10, min_periods=1).mean()
)
df['opp_strength_last5'] = df.groupby('team')['opp_elo_today'].transform(
    lambda x: x.shift(1).rolling(5, min_periods=1).mean()
)

# Merge season player stats
df = df.merge(players, on=['team', 'season'], how='left')

# Merge season team stats (Pace, 3PT rate, TS%)
df = df.merge(team_stats, on=['team', 'season'], how='left')

# Build matchup rows
team_stats_cols = df[[
    'team', 'date',
    'win_pct', 'win_rate_last5', 'avg_pts_last5', 'avg_pts_allowed_last5', 'point_diff_last5',
    'win_rate_last10', 'avg_pts_last10', 'avg_pts_allowed_last10', 'point_diff_last10',
    'net_rating', 'net_rating_last5',
    'home_win_rate', 'away_win_rate',
    'streak_entering_game', 'days_rest', 'elo',
    'opp_strength_last10', 'opp_strength_last5',
    'three_pt_rate', 'three_pt_pct', 'Pace', 'TS%',
    'opp_three_pt_rate_allowed', 'opp_three_pt_pct_allowed',
    'ft_rate', 'tov_per_game'
]].copy()

matchups = df.merge(
    team_stats_cols.rename(columns={
        'team': 'opp_abbrev',
        'win_pct': 'opp_win_pct',
        'win_rate_last5': 'opp_win_rate_last5',
        'avg_pts_last5': 'opp_avg_pts_last5',
        'avg_pts_allowed_last5': 'opp_avg_pts_allowed_last5',
        'point_diff_last5': 'opp_point_diff_last5',
        'win_rate_last10': 'opp_win_rate_last10',
        'avg_pts_last10': 'opp_avg_pts_last10',
        'avg_pts_allowed_last10': 'opp_avg_pts_allowed_last10',
        'point_diff_last10': 'opp_point_diff_last10',
        'net_rating': 'opp_net_rating',
        'net_rating_last5': 'opp_net_rating_last5',
        'home_win_rate': 'opp_home_win_rate',
        'away_win_rate': 'opp_away_win_rate',
        'streak_entering_game': 'opp_streak_entering_game',
        'days_rest': 'opp_days_rest',
        'elo': 'opp_elo',
        'opp_strength_last10': 'opp_opp_strength_last10',
        'opp_strength_last5': 'opp_opp_strength_last5',
        'three_pt_rate': 'opp_three_pt_rate',
        'three_pt_pct': 'opp_three_pt_pct',
        'Pace': 'opp_Pace',
        'TS%': 'opp_TS%',
        'opp_three_pt_rate_allowed': 'opp_opp_three_pt_rate_allowed',
        'opp_three_pt_pct_allowed': 'opp_opp_three_pt_pct_allowed',
        'ft_rate': 'opp_ft_rate',
        'tov_per_game': 'opp_tov_per_game'
    }),
    on=['opp_abbrev', 'date'], how='inner'
)

# Merge opponent player stats
players_opp = players.rename(columns={'team': 'opp_abbrev'})
players_opp.columns = [
    c if c in ['opp_abbrev', 'season'] else f'opp_{c}'
    for c in players_opp.columns
]
matchups = matchups.merge(players_opp, on=['opp_abbrev', 'season'], how='left')

avail = pd.read_csv('data/nba_player_availability.csv')
avail['date'] = pd.to_datetime(avail['date'])

matchups = matchups.merge(
    avail[['team', 'date', 'season', 'star1_absent', 'star2_absent', 'stars_available']],
    on=['team', 'date', 'season'],
    how='left',
)

avail_opp = avail.rename(columns={
    'team': 'opp_abbrev',
    'star1_absent': 'opp_star1_absent',
    'star2_absent': 'opp_star2_absent',
    'stars_available': 'opp_stars_available',
})
matchups = matchups.merge(
    avail_opp[
        ['opp_abbrev', 'date', 'season', 'opp_star1_absent', 'opp_star2_absent', 'opp_stars_available']
    ],
    on=['opp_abbrev', 'date', 'season'],
    how='left',
)

matchups['star_advantage'] = (
    (matchups['opp_star1_absent'] + matchups['opp_star2_absent'])
    - (matchups['star1_absent'] + matchups['star2_absent'])
)

for col in [
    'star1_absent',
    'star2_absent',
    'opp_star1_absent',
    'opp_star2_absent',
    'star_advantage',
]:
    matchups[col] = matchups[col].fillna(0)

# Head-to-head
matchups = matchups.sort_values('date').reset_index(drop=True)
h2h_wins = {}
h2h_games = {}
h2h_win_rate = []
for _, row in matchups.iterrows():
    key = (row['team'], row['opp_abbrev'], row['season'])
    wins = h2h_wins.get(key, 0)
    games = h2h_games.get(key, 0)
    rate = wins / games if games > 0 else 0.5
    h2h_win_rate.append(rate)
    h2h_wins[key] = wins + row['result_binary']
    h2h_games[key] = games + 1
matchups['h2h_win_rate'] = h2h_win_rate

# All difference features
matchups['win_pct_diff'] = matchups['win_pct'] - matchups['opp_win_pct']
matchups['pts_diff_diff'] = matchups['point_diff_last5'] - matchups['opp_point_diff_last5']
matchups['win_rate_diff'] = matchups['win_rate_last5'] - matchups['opp_win_rate_last5']
matchups['pts_diff_diff10'] = matchups['point_diff_last10'] - matchups['opp_point_diff_last10']
matchups['win_rate_diff10'] = matchups['win_rate_last10'] - matchups['opp_win_rate_last10']
matchups['streak_diff'] = matchups['streak_entering_game'] - matchups['opp_streak_entering_game']
matchups['rest_diff'] = matchups['days_rest'] - matchups['opp_days_rest']
matchups['top_pts_diff'] = matchups['top_combined_pts'] - matchups['opp_top_combined_pts']
matchups['top_ast_diff'] = matchups['top_combined_ast'] - matchups['opp_top_combined_ast']
matchups['top_reb_diff'] = matchups['top_combined_reb'] - matchups['opp_top_combined_reb']
matchups['star1_pts_diff'] = matchups['star1_PTS'] - matchups['opp_star1_PTS']
matchups['elo_diff'] = matchups['elo'] - matchups['opp_elo']
matchups['avg_pts_last5_diff'] = matchups['avg_pts_last5'] - matchups['opp_avg_pts_last5']
matchups['avg_pts_last10_diff'] = matchups['avg_pts_last10'] - matchups['opp_avg_pts_last10']
matchups['avg_pts_allowed_last5_diff'] = matchups['avg_pts_allowed_last5'] - matchups['opp_avg_pts_allowed_last5']
matchups['avg_pts_allowed_last10_diff'] = matchups['avg_pts_allowed_last10'] - matchups['opp_avg_pts_allowed_last10']
matchups['net_rating_diff'] = matchups['net_rating'] - matchups['opp_net_rating']

# New feature diffs
matchups['opp_strength_diff'] = matchups['opp_strength_last10'] - matchups['opp_opp_strength_last10']
matchups['pace_diff'] = matchups['Pace'] - matchups['opp_Pace']
matchups['three_pt_rate_diff'] = matchups['three_pt_rate'] - matchups['opp_three_pt_rate']
matchups['ts_pct_diff'] = matchups['TS%'] - matchups['opp_TS%']
matchups['three_pt_matchup'] = matchups['three_pt_rate'] - matchups['opp_opp_three_pt_rate_allowed']

output_path = os.path.join('data', 'nba_games_features.csv')
matchups.to_csv(output_path, index=False)
print(f"\nDone! {len(matchups)} rows, {len(matchups.columns)} columns.")
print(f"\nRows per season:")
print(matchups.groupby('season').size())
print(f"\nNew features: opp_strength_last10, pace_diff, three_pt_rate_diff, ts_pct_diff, three_pt_matchup")