from nba_api.stats.endpoints import leagueleaders
from nba_api.stats.static import players
from nba_api.stats.endpoints import playercareerstats
from nba_api.stats.endpoints import leaguestandings


def get_top_scorers(limit=10):
    leaders = leagueleaders.LeagueLeaders(
        season="2024-25",
        season_type_all_star="Regular Season",
        stat_category_abbreviation="PTS",
        per_mode48="PerGame"
    )

    df = leaders.get_data_frames()[0]

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
        season="2024-25",
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
        season="2024-25",
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

    career = playercareerstats.PlayerCareerStats(player_id=player_id)
    df = career.get_data_frames()[0]

    if df.empty:
        return None

    latest = df.iloc[-1]

    gp = int(latest["GP"])

    if gp == 0:
        return None

    return {
        "player": player_name.title(),
        "season": latest["SEASON_ID"],
        "team": latest["TEAM_ABBREVIATION"],
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
    standings = leaguestandings.LeagueStandings()
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