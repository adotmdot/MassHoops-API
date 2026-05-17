import sqlite3

conn = sqlite3.connect("basketball.db")
cursor = conn.cursor()

# Create tables
cursor.execute("""
CREATE TABLE IF NOT EXISTS players (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT,
    team TEXT,
    position TEXT,
    points_per_game REAL,
    rebounds_per_game REAL,
    assists_per_game REAL
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS teams (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    team_name TEXT,
    conference TEXT,
    wins INTEGER,
    losses INTEGER
)
""")

# Insert players
cursor.executemany("""
INSERT INTO players (name, team, position, points_per_game, rebounds_per_game, assists_per_game)
VALUES (?, ?, ?, ?, ?, ?)
""", [
    ('LeBron James', 'Lakers', 'SF', 25.7, 7.3, 8.3),
    ('Stephen Curry', 'Warriors', 'PG', 29.4, 5.2, 6.1),
    ('Kevin Durant', 'Suns', 'SF', 27.1, 6.7, 5.0),
    ('Nikola Jokic', 'Nuggets', 'C', 26.4, 12.4, 9.0),
    ('Giannis Antetokounmpo', 'Bucks', 'PF', 30.1, 11.8, 5.7),
    ('Jayson Tatum', 'Celtics', 'SF', 26.9, 8.1, 4.9),
    ('Luka Doncic', 'Mavericks', 'PG', 33.9, 9.2, 9.8),
    ('Joel Embiid', '76ers', 'C', 30.6, 11.7, 4.2),
    ('Devin Booker', 'Suns', 'SG', 27.8, 4.5, 5.5),
    ('Ja Morant', 'Grizzlies', 'PG', 25.1, 5.6, 8.1)
])

# Insert teams
cursor.executemany("""
INSERT INTO teams (team_name, conference, wins, losses)
VALUES (?, ?, ?, ?)
""", [
    ('Lakers', 'West', 43, 39),
    ('Warriors', 'West', 46, 36),
    ('Suns', 'West', 49, 33),
    ('Nuggets', 'West', 53, 29),
    ('Bucks', 'East', 51, 31),
    ('Celtics', 'East', 57, 25),
    ('Mavericks', 'West', 38, 44),
    ('76ers', 'East', 54, 28),
    ('Grizzlies', 'West', 51, 31)
])

conn.commit()
conn.close()

print("Database setup complete!")


conn = sqlite3.connect("basketball.db")
cursor = conn.cursor()

cursor.execute("SELECT name, points_per_game FROM players ORDER BY points_per_game DESC")
print(cursor.fetchall())

conn.close()