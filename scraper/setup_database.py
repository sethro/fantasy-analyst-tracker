import sqlite3
import pandas as pd

# ── CONNECT TO DATABASE ───────────────────────────────────────────────────────
# This creates the file 'rankings.db' inside your data/ folder if it doesn't
# exist yet. If it does exist, it just opens it. Think of it like opening a
# spreadsheet file.
conn = sqlite3.connect("data/rankings.db")

# A "cursor" is your tool for sending commands to the database.
# Think of it as the thing that actually types your SQL commands.
cursor = conn.cursor()

# ── CREATE TABLES ─────────────────────────────────────────────────────────────
# We're creating two tables:
#   1. 'rankings'  — analyst predictions (what we just simulated)
#   2. 'actuals'   — real fantasy points scored (we'll populate this in Module 4)

# DROP TABLE IF EXISTS means: if we run this script again, start fresh.
# During development this is useful — we don't want duplicate data.
cursor.execute("DROP TABLE IF EXISTS rankings")
cursor.execute("DROP TABLE IF EXISTS actuals")

cursor.execute("""
    CREATE TABLE rankings (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        season      INTEGER NOT NULL,
        week        INTEGER NOT NULL,
        analyst     TEXT    NOT NULL,
        position    TEXT    NOT NULL,
        player      TEXT    NOT NULL,
        rank        INTEGER NOT NULL
    )
""")
# What each column means:
# id       — a unique number automatically assigned to each row
# season   — the NFL season year (2025)
# week     — week number 1-18
# analyst  — analyst name
# position — QB, RB, WR, TE, or DST
# player   — player name
# rank     — where the analyst ranked them (1 = best)

cursor.execute("""
    CREATE TABLE actuals (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        season          INTEGER NOT NULL,
        week            INTEGER NOT NULL,
        position        TEXT    NOT NULL,
        player          TEXT    NOT NULL,
        fantasy_points  REAL    NOT NULL,
        actual_rank     INTEGER NOT NULL
    )
""")
# fantasy_points — how many points the player actually scored
# actual_rank    — their rank among all players at that position that week

print("✅ Tables created")

# ── LOAD SIMULATION DATA ──────────────────────────────────────────────────────
# Read the CSV we made in Module 2
df = pd.read_csv("data/rankings_simulated.csv")

# Write every row into the rankings table
# if_exists="append" means: add to existing data (don't overwrite)
# index=False means: don't write the pandas row numbers as a column
df.to_sql("rankings", conn, if_exists="append", index=False)

print(f"✅ Loaded {len(df)} rows into rankings table")

# ── VERIFY IT WORKED ──────────────────────────────────────────────────────────
# Ask the database a few questions to confirm everything loaded correctly

# Question 1: How many rows total?
cursor.execute("SELECT COUNT(*) FROM rankings")
count = cursor.fetchone()[0]
print(f"\n📊 Total rows in rankings: {count}")

# Question 2: Which analysts are in there?
cursor.execute("SELECT DISTINCT analyst FROM rankings ORDER BY analyst")
analysts = cursor.fetchall()
print(f"\n👤 Analysts loaded:")
for a in analysts:
    print(f"   {a[0]}")

# Question 3: Show me Justin Boone's TE rankings for Week 1
print(f"\n🏈 Justin Boone's TE rankings, Week 1:")
cursor.execute("""
    SELECT rank, player
    FROM rankings
    WHERE analyst = 'Justin Boone'
      AND position = 'TE'
      AND week = 1
    ORDER BY rank
""")
rows = cursor.fetchall()
for row in rows:
    print(f"   #{row[0]} {row[1]}")

# ── SAVE AND CLOSE ────────────────────────────────────────────────────────────
# IMPORTANT: Always commit and close. 
# commit() = save changes permanently to the file
# close()  = release the file so other scripts can use it
conn.commit()
conn.close()

print("\n✅ Database saved and closed: data/rankings.db")