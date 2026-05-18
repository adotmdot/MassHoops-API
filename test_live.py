from nba_live import get_team_roster

players = get_team_roster("Lakers")

for player in players:
    print(player)
    