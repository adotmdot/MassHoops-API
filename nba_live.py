from nba_api.stats.endpoints import leagueleaders
from nba_api.stats.static import players
from nba_api.stats.endpoints import playercareerstats
from nba_api.stats.endpoints import leaguestandings
from nba_api.stats.endpoints import scoreboardv2
from nba_api.stats.endpoints import commonteamroster
from nba_api.stats.static import teams
from datetime import datetime
import time


def get_current_season():
    """
    Returns the current NBA season string.
    Example:
      Oct 2026 -> '2026-27'
      May 2026 -> '2025-26'
    NBA seasons begin in October.
    """
    now = datetime.now()

    if now.month >= 10:
        start_year = now.year
    else:
        start_year = now.year - 1

    end_year = str(start_year + 1)[-2:]
    return f"{start_year}-{end_year}"



def get_top_scorers(limit=10):
    leaders = retry_nba_api(
        lambda: leagueleaders.LeagueLeaders(
            season=get_current_season(),
            season_type_all_star="Regular Season",
            stat_category_abbreviation="PTS",
            per_mode48="PerGame",
            timeout=60
        )
    )

    df = leaders.get_data_frames()[0]
    
    print(f"[DEBUG] Using NBA season: {get_current_season()}")

    return [
        {
            "player": row["PLAYER"],
            "team": row["TEAM"],
            "value": float(row["PTS"])
        }
        for _, row in df.head(limit).iterrows()
    ]
    


def get_top_rebounders(limit=10):
    leaders = leagueleaders.LeagueLeaders(
        season=get_current_season(),
        season_type_all_star="Regular Season",
        stat_category_abbreviation="REB",
        per_mode48="PerGame"
    )

    df = leaders.get_data_frames()[0]

    return [
        {
            "player": row["PLAYER"],
            "team": row["TEAM"],
            "value": float(row["REB"])
        }
        for _, row in df.head(limit).iterrows()
    ]


def get_top_assist_leaders(limit=10):
    leaders = leagueleaders.LeagueLeaders(
        season=get_current_season(),
        season_type_all_star="Regular Season",
        stat_category_abbreviation="AST",
        per_mode48="PerGame"
    )

    df = leaders.get_data_frames()[0]

    return [
        {
            "player": row["PLAYER"],
            "team": row["TEAM"],
            "value": float(row["AST"])
        }
        for _, row in df.head(limit).iterrows()
    ]
    
    
def get_player_stats(player_name: str):
    """
    Returns the latest season per-game stats for a player.
    """
    matches = players.find_players_by_full_name(player_name)

    if not matches:
        return None

    player_id = matches[0]["id"]

    career = retry_nba_api(
        lambda: playercareerstats.PlayerCareerStats(
            player_id=player_id,
            timeout=60
        )
    )
    df = career.get_data_frames()[0]

    if df.empty:
        return None

    latest = df.iloc[-1]

    gp = int(latest["GP"])

    if gp == 0:
        return None

    return {
        "player_id": player_id,
        "player": player_name.title(),
        "season": latest["SEASON_ID"],
        "team": latest["TEAM_ABBREVIATION"],
        "team_id": int(latest["TEAM_ID"]),
        "games": gp,
        "points": round(float(latest["PTS"]) / gp, 1),
        "rebounds": round(float(latest["REB"]) / gp, 1),
        "assists": round(float(latest["AST"]) / gp, 1),
        "fg_pct": round(float(latest["FG_PCT"]) * 100, 1),
        "three_pct": round(float(latest["FG3_PCT"]) * 100, 1),
        "ft_pct": round(float(latest["FT_PCT"]) * 100, 1),
    }
    
    
def get_nba_standings(limit=30):
    """
    Returns current NBA standings.
    """
    standings = retry_nba_api(
        lambda: leaguestandings.LeagueStandings(timeout=120)
    )
    df = standings.get_data_frames()[0]

    return [
        {
            "team": row["TeamName"],
            "wins": int(row["WINS"]),
            "losses": int(row["LOSSES"]),
            "win_pct": round(float(row["WinPCT"]) * 100, 1),
            "conference": row["Conference"],
            "rank": int(row["PlayoffRank"]),
        }
        for _, row in df.head(limit).iterrows()
    ] 
    
    
def get_team_record(team_name: str):
    """
    Returns the current record for a given NBA team.
    """
    standings = get_nba_standings(30)

    team_name_lower = team_name.lower()

    # Common aliases
    aliases = {
        "lakers": "Lakers",
        "celtics": "Celtics",
        "knicks": "Knicks",
        "thunder": "Thunder",
        "nuggets": "Nuggets",
        "warriors": "Warriors",
        "heat": "Heat",
        "bulls": "Bulls",
        "spurs": "Spurs",
        "rockets": "Rockets",
        "cavaliers": "Cavaliers",
        "pistons": "Pistons",
        "raptors": "Raptors",
        "bucks": "Bucks",
        "suns": "Suns",
        "mavericks": "Mavericks",
        "clippers": "Clippers",
        "hawks": "Hawks",
        "magic": "Magic",
        "kings": "Kings",
        "grizzlies": "Grizzlies",
        "pelicans": "Pelicans",
        "nets": "Nets",
        "hornets": "Hornets",
        "jazz": "Jazz",
        "blazers": "Trail Blazers",
        "trail blazers": "Trail Blazers",
        "timberwolves": "Timberwolves",
        "wolves": "Timberwolves",
        "76ers": "76ers",
        "sixers": "76ers",
        "pacers": "Pacers",
        "wizards": "Wizards",
    }

    search_term = aliases.get(team_name_lower, team_name)

    for team in standings:
        if search_term.lower() in team["team"].lower():
            return team

    return None   


def get_games_today():
    """
    Returns today's NBA games.
    """
    today = datetime.now().strftime("%m/%d/%Y")

    scoreboard = scoreboardv2.ScoreboardV2(game_date=today)

    games_df = scoreboard.get_data_frames()[0]
    teams_df = scoreboard.get_data_frames()[1]

    games = []

    for _, game in games_df.iterrows():
        game_id = game["GAME_ID"]

        game_teams = teams_df[teams_df["GAME_ID"] == game_id]

        if len(game_teams) >= 2:
            away_team = game_teams.iloc[0]["TEAM_ABBREVIATION"]
            home_team = game_teams.iloc[1]["TEAM_ABBREVIATION"]

            games.append({
                "away": away_team,
                "home": home_team,
            })

    return games


def get_scoreboard():
    today = datetime.today().strftime("%m/%d/%Y")

    scoreboard = scoreboardv2.ScoreboardV2(game_date=today)

    # Game Header table
    game_header = scoreboard.get_data_frames()[0]

    # Line Score table
    line_score = scoreboard.get_data_frames()[1]

    results = []

    for _, game in game_header.iterrows():
        game_id = game["GAME_ID"]
        status = game["GAME_STATUS_TEXT"]

        teams = line_score[line_score["GAME_ID"] == game_id]

        if len(teams) >= 2:
            away = teams.iloc[0]["TEAM_ABBREVIATION"]
            home = teams.iloc[1]["TEAM_ABBREVIATION"]

            results.append({
                "away": away,
                "home": home,
                "status": status
            })

    return results


def get_team_roster(team_name: str):
    """
    Returns the active roster for a given NBA team.
    """
    nba_teams = teams.get_teams()

    match = None
    for team in nba_teams:
        if team_name.lower() in team["full_name"].lower() or \
           team_name.lower() in team["nickname"].lower():
            match = team
            break

    if not match:
        return []

    roster = retry_nba_api(
        lambda: commonteamroster.CommonTeamRoster(
            team_id=match["id"],
            timeout=60
        )
    )
    df = roster.get_data_frames()[0]

    return df["PLAYER"].tolist()


def get_team_leader(team_name: str, stat: str = "PTS"):
    """
    Returns the team leader for a specific stat.
    Supported stats:
    - PTS = Points
    - REB = Rebounds
    - AST = Assists
    """

    # Find team
    nba_teams = teams.get_teams()
    matching_team = None

    for team in nba_teams:
        if team_name.lower() in team["full_name"].lower() or \
           team_name.lower() in team["nickname"].lower():
            matching_team = team
            break

    if not matching_team:
        return None

    team_id = matching_team["id"]

    # Get roster
    roster = commonteamroster.CommonTeamRoster(team_id=team_id)
    roster_df = roster.get_data_frames()[0]

    best_player = None
    best_value = -1

    for _, row in roster_df.iterrows():
        player_name = row["PLAYER"]

        stats = get_player_stats(player_name)
        if not stats:
            continue

        stat_key = stat.lower()

        if stat_key == "pts":
            value = stats["points"]
        elif stat_key == "reb":
            value = stats["rebounds"]
        elif stat_key == "ast":
            value = stats["assists"]
        else:
            return None

        if value > best_value:
            best_value = value
            best_player = {
                "player": player_name,
                "team": matching_team["nickname"],
                "stat": stat.upper(),
                "value": value
            }

    return best_player


def compare_players(player1: str, player2: str):
    """
    Compare two NBA players using current season averages.
    """
    stats1 = get_player_stats(player1)
    stats2 = get_player_stats(player2)

    if not stats1 or not stats2:
        return None

    return {
        "player1": stats1,
        "player2": stats2,
    }
    
    
def retry_nba_api(api_call, retries=5, delay=4):
    """
    Retry nba_api calls if stats.nba.com times out.
    """
    for attempt in range(retries):
        try:
            return api_call()
        except Exception as e:
            if attempt < retries - 1:
                print(f"[WARN] NBA API failed: {e}")
                print(f"[WARN] Retrying {attempt + 1}/{retries} in {delay} seconds...")
                time.sleep(delay)
            else:
                print(f"[ERROR] NBA API failed after {retries} attempts.")
                raise   
  
  
  
  
def get_league_leaders(stat="PTS", limit=10, per_mode="PerGame"):
    """
    Dynamically returns NBA league leaders for any supported stat.
    Examples: PTS, REB, AST, STL, BLK, TOV, EFF
    """

    leaders = retry_nba_api(
        lambda: leagueleaders.LeagueLeaders(
            season=get_current_season(),
            season_type_all_star="Regular Season",
            stat_category_abbreviation=stat,
            per_mode48=per_mode,
            timeout=60
        )
    )

    df = leaders.get_data_frames()[0]

    if df.empty:
        return []

    if stat not in df.columns:
        return []

    return [
        {
            "player": row["PLAYER"],
            "team": row["TEAM"],
            "stat": stat,
            "value": float(row[stat])
        }
        for _, row in df.head(limit).iterrows()
    ]  