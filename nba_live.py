from nba_api.stats.endpoints import leagueleaders
from nba_api.stats.static import players
from nba_api.stats.endpoints import playercareerstats
from nba_api.stats.endpoints import leaguestandings
from nba_api.stats.endpoints import scoreboardv2
from nba_api.stats.endpoints import commonteamroster
from nba_api.stats.static import teams
from nba_api.stats.library.http import NBAStatsHTTP

from datetime import datetime

import requests
import time

from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


# =====================================================
# GLOBAL HEADERS
# =====================================================

HEADERS = {
    "Host": "stats.nba.com",
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
    "Referer": "https://www.nba.com/",
    "Origin": "https://www.nba.com",
}


# =====================================================
# REQUEST SESSION
# =====================================================

session = requests.Session()

retry_strategy = Retry(
    total=2,
    backoff_factor=1,
    status_forcelist=[429, 500, 502, 503, 504],
)

adapter = HTTPAdapter(max_retries=retry_strategy)

session.mount("https://", adapter)
session.mount("http://", adapter)

session.headers.update(HEADERS)

NBAStatsHTTP.headers = HEADERS
NBAStatsHTTP._session = session


# =====================================================
# RETRY WRAPPER
# =====================================================

def retry_nba_api(api_call, retries=2, delay=2):

    for attempt in range(retries):

        try:
            return api_call()

        except Exception as e:

            if attempt < retries - 1:

                print(f"[WARN] NBA API failed: {e}")
                print(
                    f"[WARN] Retrying {attempt + 1}/{retries} "
                    f"in {delay} seconds..."
                )

                time.sleep(delay)

            else:

                print(
                    f"[ERROR] NBA API failed after "
                    f"{retries} attempts."
                )

                raise


# =====================================================
# CURRENT SEASON
# =====================================================

def get_current_season():

    now = datetime.now()

    if now.month >= 10:
        start_year = now.year
    else:
        start_year = now.year - 1

    end_year = str(start_year + 1)[-2:]

    return f"{start_year}-{end_year}"


# =====================================================
# LEAGUE LEADERS
# =====================================================

def get_league_leaders(
    stat="PTS",
    limit=10,
    per_mode="PerGame"
):

    leaders = retry_nba_api(
        lambda: leagueleaders.LeagueLeaders(
            season=get_current_season(),
            season_type_all_star="Regular Season",
            stat_category_abbreviation=stat,
            per_mode48=per_mode,
            timeout=15,
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


# =====================================================
# PLAYER STATS
# =====================================================

def get_player_stats(player_name: str):

    matches = players.find_players_by_full_name(player_name)

    if not matches:
        return None

    player_id = matches[0]["id"]

    career = retry_nba_api(
        lambda: playercareerstats.PlayerCareerStats(
            player_id=player_id,
            timeout=15
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


# =====================================================
# STANDINGS
# =====================================================

def get_nba_standings(limit=30):

    standings = retry_nba_api(
        lambda: leaguestandings.LeagueStandings(
            timeout=15
        )
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


# =====================================================
# TEAM RECORD
# =====================================================

def get_team_record(team_name: str):

    standings = get_nba_standings(30)

    for team in standings:

        if team_name.lower() in team["team"].lower():
            return team

    return None


# =====================================================
# GAMES TODAY
# =====================================================

def get_games_today():

    today = datetime.now().strftime("%m/%d/%Y")

    scoreboard = retry_nba_api(
        lambda: scoreboardv2.ScoreboardV2(
            game_date=today,
            timeout=15
        )
    )

    games_df = scoreboard.get_data_frames()[0]
    teams_df = scoreboard.get_data_frames()[1]

    games = []

    for _, game in games_df.iterrows():

        game_id = game["GAME_ID"]

        game_teams = teams_df[
            teams_df["GAME_ID"] == game_id
        ]

        if len(game_teams) >= 2:

            away_team = game_teams.iloc[0][
                "TEAM_ABBREVIATION"
            ]

            home_team = game_teams.iloc[1][
                "TEAM_ABBREVIATION"
            ]

            games.append({
                "away": away_team,
                "home": home_team,
            })

    return games


# =====================================================
# TEAM ROSTER
# =====================================================

def get_team_roster(team_name: str):

    nba_teams = teams.get_teams()

    match = None

    for team in nba_teams:

        if (
            team_name.lower() in team["full_name"].lower()
            or
            team_name.lower() in team["nickname"].lower()
        ):
            match = team
            break

    if not match:
        return []

    roster = retry_nba_api(
        lambda: commonteamroster.CommonTeamRoster(
            team_id=match["id"],
            timeout=15
        )
    )

    df = roster.get_data_frames()[0]

    return df["PLAYER"].tolist()


# =====================================================
# TEAM LEADER
# =====================================================

def get_team_leader(team_name: str, stat: str = "PTS"):

    nba_teams = teams.get_teams()

    matching_team = None

    for team in nba_teams:

        if (
            team_name.lower() in team["full_name"].lower()
            or
            team_name.lower() in team["nickname"].lower()
        ):
            matching_team = team
            break

    if not matching_team:
        return None

    roster = retry_nba_api(
        lambda: commonteamroster.CommonTeamRoster(
            team_id=matching_team["id"],
            timeout=15
        )
    )

    roster_df = roster.get_data_frames()[0]

    best_player = None
    best_value = -1

    for _, row in roster_df.iterrows():

        player_name = row["PLAYER"]

        stats = get_player_stats(player_name)

        if not stats:
            continue

        if stat == "PTS":
            value = stats["points"]

        elif stat == "REB":
            value = stats["rebounds"]

        elif stat == "AST":
            value = stats["assists"]

        else:
            return None

        if value > best_value:

            best_value = value

            best_player = {
                "player": player_name,
                "team": matching_team["nickname"],
                "stat": stat,
                "value": value
            }

    return best_player


# =====================================================
# PLAYER COMPARISON
# =====================================================

def compare_players(player1: str, player2: str):

    stats1 = get_player_stats(player1)
    stats2 = get_player_stats(player2)

    if not stats1 or not stats2:
        return None

    return {
        "player1": stats1,
        "player2": stats2,
    }