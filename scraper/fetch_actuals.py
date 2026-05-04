import ssl
import certifi
ssl._create_default_https_context = ssl._create_unverified_context

import nfl_data_py as nfl
import pandas as pd
import sqlite3

# ── CONFIGURATION ─────────────────────────────────────────────────────────────
SEASON = 2024
SCORING = {
    # Passing
    "passing_yards":        0.04,
    "passing_tds":          4.0,
    "interceptions":       -2.0,
    # Rushing
    "rushing_yards":        0.1,
    "rushing_tds":          6.0,
    # Receiving (Half PPR = 0.5 per reception)
    "receptions":           0.5,
    "receiving_yards":      0.1,
    "receiving_tds":        6.0,
    # Misc
    "rushing_fumbles_lost": -2.0,
    "receiving_fumbles_lost": -2.0,
    "sack_fumbles_lost":    -2.0,
}

# Position groups — maps NFL roster positions to our 5 fantasy positions
POSITION_MAP = {
    "QB":  ["QB"],
    "RB":  ["RB", "FB"],
    "WR":  ["WR"],
    "TE":  ["TE"],
}
# Note: DST is handled separately below — it uses team-level data, not player stats

# ── FETCH WEEKLY PLAYER STATS ─────────────────────────────────────────────────
print(f"📥 Fetching {SEASON} weekly player stats...")
# nfl.import_weekly_data() pulls official NFL stats for every player, every week
# This is the same data the NFL publishes — passing yards, rushing yards, etc.
weekly = nfl.import_weekly_data([SEASON])
print(f"   Got {len(weekly)} rows, {weekly['week'].nunique()} weeks")

# ── FILTER TO REGULAR SEASON ONLY ────────────────────────────────────────────
# season_type "REG" = regular season. We exclude playoffs for fantasy purposes.
weekly = weekly[weekly["season_type"] == "REG"].copy()
print(f"   After filtering to regular season: {len(weekly)} rows")

# ── CALCULATE FANTASY POINTS ──────────────────────────────────────────────────
print("\n⚙️  Calculating fantasy points...")

def calculate_fantasy_points(row):
    """
    Takes one row of player stats and returns their fantasy point total.
    We loop through our SCORING dict and multiply each stat by its point value.
    """
    total = 0.0
    for stat, multiplier in SCORING.items():
        # .get(stat, 0) means: get this column's value, or 0 if it doesn't exist
        total += row.get(stat, 0) * multiplier
    return round(total, 2)

# Apply our function to every row in the dataframe
# axis=1 means "apply this function row by row" (vs column by column)
weekly["fantasy_points"] = weekly.apply(calculate_fantasy_points, axis=1)

# ── PROCESS OFFENSIVE POSITIONS ───────────────────────────────────────────────
print("\n📊 Processing offensive positions (QB, RB, WR, TE)...")

offensive_rows = []

for fantasy_pos, nfl_positions in POSITION_MAP.items():
    # Filter to players at this position
    pos_df = weekly[weekly["position"].isin(nfl_positions)].copy()

    # For each week, rank players by fantasy points (rank 1 = most points)
    # We only keep players who actually played (fantasy_points > 0)
    for week_num in sorted(pos_df["week"].unique()):
        week_df = pos_df[pos_df["week"] == week_num].copy()

        # Filter to players who scored meaningful points
        # This removes players who were inactive or didn't touch the ball
        week_df = week_df[week_df["fantasy_points"] > 0].copy()

        # Rank by fantasy points, highest first
        # method="min" means tied players get the same rank
        week_df["actual_rank"] = week_df["fantasy_points"].rank(
            ascending=False, method="min"
        ).astype(int)

        # Keep only what we need
        for _, row in week_df.iterrows():
            offensive_rows.append({
                "season":         SEASON,
                "week":           week_num,
                "position":       fantasy_pos,
                "player":         row["player_display_name"],
                "fantasy_points": row["fantasy_points"],
                "actual_rank":    row["actual_rank"],
            })

offensive_df = pd.DataFrame(offensive_rows)
print(f"   Offensive rows: {len(offensive_df)}")

# ── PROCESS DST ───────────────────────────────────────────────────────────────
# DST scoring uses team-level stats, not individual player stats
# We need: points allowed, sacks, turnovers, TDs scored by defense/ST
print("\n📊 Processing DST...")

dst_rows = []

try:
    # import_schedules gives us game-level data including scores
    schedules = nfl.import_schedules([SEASON])
    schedules = schedules[schedules["game_type"] == "REG"].copy()

    # We need both home and away team perspectives
    # Each game appears once in schedules, but each team needs its own DST score
    for _, game in schedules.iterrows():
        week_num = game["week"]
        if pd.isna(week_num) or pd.isna(game.get("home_score")):
            continue

        week_num = int(week_num)
        home_score = int(game["home_score"])
        away_score = int(game["away_score"])
        home_team = game["home_team"]
        away_team = game["away_team"]

        def dst_points(points_allowed):
            """
            Standard fantasy DST scoring based on points allowed.
            This is the most common DST scoring system.
            """
            if points_allowed == 0:    return 10
            elif points_allowed <= 6:  return 7
            elif points_allowed <= 13: return 4
            elif points_allowed <= 20: return 1
            elif points_allowed <= 27: return 0
            elif points_allowed <= 34: return -1
            else:                      return -4

        # Home team DST (they allowed away_score points)
        dst_rows.append({
            "season":         SEASON,
            "week":           week_num,
            "position":       "DST",
            "player":         f"{home_team} DST",
            "fantasy_points": dst_points(away_score),
            "actual_rank":    0,  # We'll rank these after
        })

        # Away team DST (they allowed home_score points)
        dst_rows.append({
            "season":         SEASON,
            "week":           week_num,
            "position":       "DST",
            "player":         f"{away_team} DST",
            "fantasy_points": dst_points(home_score),
            "actual_rank":    0,
        })

    # Now rank DST by week
    dst_df = pd.DataFrame(dst_rows)
    for week_num in dst_df["week"].unique():
        mask = dst_df["week"] == week_num
        dst_df.loc[mask, "actual_rank"] = dst_df.loc[mask, "fantasy_points"].rank(
            ascending=False, method="min"
        ).astype(int)

    print(f"   DST rows: {len(dst_df)}")

except Exception as e:
    print(f"   ⚠️  DST fetch failed: {e}")
    print(f"   Continuing without DST data...")
    dst_df = pd.DataFrame()

# ── COMBINE AND SAVE ──────────────────────────────────────────────────────────
if len(dst_df) > 0:
    actuals_df = pd.concat([offensive_df, dst_df], ignore_index=True)
else:
    actuals_df = offensive_df

print(f"\n💾 Saving {len(actuals_df)} rows to database...")

conn = sqlite3.connect("data/rankings.db")

# Clear existing actuals so we can re-run this script cleanly
conn.execute("DELETE FROM actuals")

actuals_df.to_sql("actuals", conn, if_exists="append", index=False)

conn.commit()

# ── VERIFY ────────────────────────────────────────────────────────────────────
cursor = conn.cursor()

cursor.execute("SELECT COUNT(*) FROM actuals")
print(f"✅ Rows in actuals table: {cursor.fetchone()[0]}")

cursor.execute("SELECT DISTINCT position FROM actuals ORDER BY position")
print(f"   Positions: {[r[0] for r in cursor.fetchall()]}")

cursor.execute("SELECT MIN(week), MAX(week) FROM actuals")
min_w, max_w = cursor.fetchone()
print(f"   Weeks: {min_w} through {max_w}")

# Show top 5 TEs from Week 1 as a sanity check
print("\n🏈 Top 5 TEs, Week 1 (actual results):")
cursor.execute("""
    SELECT actual_rank, player, fantasy_points
    FROM actuals
    WHERE position = 'TE' AND week = 1
    ORDER BY actual_rank
    LIMIT 5
""")
for row in cursor.fetchall():
    print(f"   #{row[0]} {row[1]:<25} {row[2]} pts")

conn.close()
print("\n✅ Module 4 complete — actuals table populated")