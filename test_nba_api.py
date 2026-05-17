from nba_api.stats.endpoints import leagueleaders

leaders = leagueleaders.LeagueLeaders(
    season="2024-25",
    season_type_all_star="Regular Season",
    stat_category_abbreviation="PTS",
    per_mode48="PerGame"
)

df = leaders.get_data_frames()[0]

print(df[["PLAYER", "TEAM", "PTS"]].head(10))