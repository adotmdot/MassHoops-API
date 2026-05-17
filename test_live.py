from nba_live import get_nba_standings

standings = get_nba_standings(10)

for team in standings:
    print(team)