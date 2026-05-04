import sqlite3
import pandas as pd
import numpy as np
from scipy import stats

# ── CONNECT ───────────────────────────────────────────────────────────────────
conn = sqlite3.connect("data/rankings.db")

# ── LOAD BOTH TABLES ──────────────────────────────────────────────────────────
# We load everything into pandas DataFrames for analysis
# This is the pandas way of saying "read this entire SQL table"
print("📥 Loading data...")
rankings_df = pd.read_sql("SELECT * FROM rankings", conn)
actuals_df  = pd.read_sql("SELECT * FROM actuals",  conn)

print(f"   Rankings rows: {len(rankings_df)}")
print(f"   Actuals rows:  {len(actuals_df)}")

# ── BUILD EXPECTED POINTS LOOKUP ───────────────────────────────────────────────
# This is the key insight: convert ranks → expected points
#
# If an analyst ranks a player #3 at TE, they're predicting that player
# will score what the average #3 TE scores. We calculate that average
# across all weeks to create a lookup table.
#
# Example output: {("TE", 1): 18.4, ("TE", 2): 12.1, ("TE", 3): 9.2, ...}

print("\n⚙️  Building expected points lookup...")

# For each position and actual rank, calculate average fantasy points
# This tells us "on average, what does the #N player at position X score?"
expected_pts = (
    actuals_df
    .groupby(["position", "actual_rank"])["fantasy_points"]
    .mean()
    .reset_index()
    .rename(columns={"fantasy_points": "expected_points"})
)

# ── JOIN RANKINGS TO ACTUALS ──────────────────────────────────────────────────
# This is the core join — matching analyst predictions to real results
#
# We're asking: "For each player an analyst ranked, what did that player
# actually score that week?"
print("🔗 Joining rankings to actuals...")

# Merge rankings with actuals on week + position + player name
# how="inner" means only keep rows where the player appears in BOTH tables
# (i.e. players the analyst ranked AND who actually played)
merged = rankings_df.merge(
    actuals_df[["season", "week", "position", "player", 
                "fantasy_points", "actual_rank"]],
    on=["season", "week", "position", "player"],
    how="inner"
)

print(f"   Matched rows: {len(merged)}")

# Rename analyst rank column to avoid confusion with actual_rank
merged = merged.rename(columns={"rank": "analyst_rank"})

# Now add expected points based on analyst rank
expected_pts = expected_pts.rename(columns={"actual_rank": "analyst_rank"})
merged = merged.merge(
    expected_pts,
    on=["position", "analyst_rank"],
    how="left"
)
# ── CALCULATE ERROR ───────────────────────────────────────────────────────────
# For each row: how wrong was this analyst about this player this week?
#
# error = |expected_points_for_their_rank - actual_points_scored|
merged["error"] = (
    merged["expected_points"] - merged["fantasy_points"]
).abs()

print(f"   Average error across all predictions: {merged['error'].mean():.2f} pts")

# ── SCORE BY ANALYST + POSITION + WEEK ───────────────────────────────────────
print("\n📊 Calculating accuracy scores...")

results = []

for (analyst, position, week), group in merged.groupby(["analyst", "position", "week"]):
    if len(group) < 3:  # Need at least 3 players to calculate correlation
        continue

    # Mean Absolute Error — lower is better
    mae = group["error"].mean()

    # Spearman Rank Correlation — higher is better (max 1.0)
    # Compares analyst's rank ORDER to actual rank ORDER
    if group["analyst_rank"].nunique() > 1 and group["actual_rank"].nunique() > 1:
        spearman, p_value = stats.spearmanr(
            group["analyst_rank"],        # analyst's predicted ranks
            group["actual_rank"]  # actual ranks based on real points
        )
    else:
        spearman = 0.0
        p_value = 1.0

    results.append({
        "analyst":   analyst,
        "position":  position,
        "week":      week,
        "mae":       round(mae, 3),
        "spearman":  round(spearman, 3),
        "p_value":   round(p_value, 3),
        "n_players": len(group),
    })

results_df = pd.DataFrame(results)
print(f"   Calculated {len(results_df)} analyst-position-week scores")

# ── SEASON SUMMARY BY ANALYST + POSITION ─────────────────────────────────────
# Average across all weeks to get season-level accuracy per analyst per position
print("\n🏆 Season accuracy summary (lower MAE = more accurate):")

season_summary = (
    results_df
    .groupby(["analyst", "position"])
    .agg(
        avg_mae      = ("mae",      "mean"),
        avg_spearman = ("spearman", "mean"),
        weeks_scored = ("week",     "count"),
    )
    .reset_index()
    .round(3)
)

# ── OVERALL ANALYST LEADERBOARD ───────────────────────────────────────────────
overall = (
    results_df
    .groupby("analyst")
    .agg(
        avg_mae      = ("mae",      "mean"),
        avg_spearman = ("spearman", "mean"),
        total_weeks  = ("week",     "count"),
    )
    .reset_index()
    .sort_values("avg_mae")  # Sort best (lowest) to worst (highest)
    .round(3)
)

print("\n📋 Overall Analyst Leaderboard (by MAE, lower = better):")
print(f"{'Rank':<6}{'Analyst':<22}{'Avg MAE':<12}{'Spearman':<12}{'Weeks'}")
print("-" * 60)
for i, row in overall.iterrows():
    rank = overall.index.get_loc(i) + 1
    print(f"{rank:<6}{row['analyst']:<22}{row['avg_mae']:<12}{row['avg_spearman']:<12}{int(row['total_weeks'])}")

# ── BEST ANALYST PER POSITION ─────────────────────────────────────────────────
print("\n🎯 Best analyst per position:")
for position in ["QB", "RB", "WR", "TE", "DST"]:
    pos_df = season_summary[season_summary["position"] == position]
    if len(pos_df) == 0:
        continue
    best = pos_df.loc[pos_df["avg_mae"].idxmin()]
    print(f"   {position}: {best['analyst']:<22} MAE={best['avg_mae']:.3f}  Spearman={best['avg_spearman']:.3f}")

# ── SAVE RESULTS TO DATABASE ──────────────────────────────────────────────────
print("\n💾 Saving results to database...")

# Create accuracy results tables
cursor = conn.cursor()
cursor.execute("DROP TABLE IF EXISTS accuracy_weekly")
cursor.execute("DROP TABLE IF EXISTS accuracy_season")

results_df.to_sql("accuracy_weekly",  conn, if_exists="append", index=False)
season_summary.to_sql("accuracy_season", conn, if_exists="append", index=False)

conn.commit()
conn.close()

# ── SAVE CSV EXPORTS ──────────────────────────────────────────────────────────
results_df.to_csv("data/accuracy_weekly.csv",  index=False)
season_summary.to_csv("data/accuracy_season.csv", index=False)

print("✅ Saved to database and CSV")
print("\n✅ Module 5 complete — accuracy engine built")