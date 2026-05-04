import sqlite3
import pandas as pd
import numpy as np

# ── CONNECT AND LOAD ──────────────────────────────────────────────────────────
conn = sqlite3.connect("data/rankings.db")

print("📥 Loading data...")
rankings_df = pd.read_sql("SELECT * FROM rankings", conn)
actuals_df  = pd.read_sql("SELECT * FROM actuals",  conn)

# ── REBUILD EXPECTED POINTS LOOKUP ────────────────────────────────────────────
# Same as Module 5 — what does the average #N player score at each position?
expected_pts = (
    actuals_df
    .groupby(["position", "actual_rank"])["fantasy_points"]
    .mean()
    .reset_index()
    .rename(columns={
        "fantasy_points": "expected_points",
        "actual_rank":    "analyst_rank"
    })
)

# ── JOIN EVERYTHING TOGETHER ──────────────────────────────────────────────────
print("🔗 Building analysis dataset...")

merged = rankings_df.merge(
    actuals_df[["season", "week", "position", "player",
                "fantasy_points", "actual_rank"]],
    on=["season", "week", "position", "player"],
    how="inner"
)

merged = merged.rename(columns={"rank": "analyst_rank"})

merged = merged.merge(
    expected_pts,
    on=["position", "analyst_rank"],
    how="left"
)

# ── SIGNED ERROR (direction matters here) ─────────────────────────────────────
# Positive = analyst overrated the player (expected more than they scored)
# Negative = analyst underrated the player (expected less than they scored)
merged["signed_error"] = merged["expected_points"] - merged["fantasy_points"]
merged["abs_error"]    = merged["signed_error"].abs()

print(f"   Total predictions analyzed: {len(merged)}")

# ════════════════════════════════════════════════════════════════════════════
# BIAS ANALYSIS 1: POSITIONAL BIAS
# For each analyst, at each position — are they systematically off?
# ════════════════════════════════════════════════════════════════════════════
print("\n" + "═"*60)
print("BIAS ANALYSIS 1: POSITIONAL BIAS")
print("═"*60)
print("Positive = overrates position  |  Negative = underrates position")
print()

positional_bias = (
    merged
    .groupby(["analyst", "position"])["signed_error"]
    .agg(
        bias        = "mean",    # Average signed error = directional bias
        volatility  = "std",     # How consistent is this bias?
        sample_size = "count",
    )
    .reset_index()
    .round(3)
)

# Pivot to a readable table: analysts as rows, positions as columns
bias_pivot = positional_bias.pivot(
    index="analyst",
    columns="position",
    values="bias"
).round(3)

# Reorder columns logically
col_order = [c for c in ["QB", "RB", "WR", "TE", "DST"] 
             if c in bias_pivot.columns]
bias_pivot = bias_pivot[col_order]

print(bias_pivot.to_string())

# ════════════════════════════════════════════════════════════════════════════
# BIAS ANALYSIS 2: DIRECTIONAL BIAS (Overall optimist vs pessimist)
# ════════════════════════════════════════════════════════════════════════════
print("\n" + "═"*60)
print("BIAS ANALYSIS 2: OVERALL DIRECTIONAL BIAS")
print("═"*60)
print("Positive = tends to overrate  |  Negative = tends to underrate")
print()

directional = (
    merged
    .groupby("analyst")["signed_error"]
    .agg(
        overall_bias = "mean",
        volatility   = "std",
        pct_overrated = lambda x: (x > 0).mean() * 100,  # % of predictions that overrated
    )
    .reset_index()
    .sort_values("overall_bias", ascending=False)
    .round(3)
)

print(f"{'Analyst':<22}{'Bias':>10}{'Volatility':>12}{'% Overrated':>14}")
print("-" * 60)
for _, row in directional.iterrows():
    bias_label = "▲ optimist" if row["overall_bias"] > 0.3 else \
                 "▼ pessimist" if row["overall_bias"] < -0.3 else \
                 "  neutral"
    print(f"{row['analyst']:<22}{row['overall_bias']:>10}{row['volatility']:>12}"
          f"{row['pct_overrated']:>13.1f}%  {bias_label}")

# ════════════════════════════════════════════════════════════════════════════
# BIAS ANALYSIS 3: CONSISTENCY OVER THE SEASON
# Does accuracy improve or degrade as the season progresses?
# ════════════════════════════════════════════════════════════════════════════
print("\n" + "═"*60)
print("BIAS ANALYSIS 3: CONSISTENCY ACROSS THE SEASON")
print("═"*60)

weekly_analyst = (
    merged
    .groupby(["analyst", "week"])["abs_error"]
    .mean()
    .reset_index()
    .rename(columns={"abs_error": "weekly_mae"})
)

# Calculate each analyst's week-over-week consistency (std of weekly MAE)
# Low std = consistent analyst  |  High std = volatile analyst
consistency = (
    weekly_analyst
    .groupby("analyst")["weekly_mae"]
    .agg(
        avg_mae    = "mean",
        std_mae    = "std",       # Volatility
        best_week  = "min",
        worst_week = "max",
    )
    .reset_index()
    .sort_values("std_mae")       # Most consistent first
    .round(3)
)

print(f"\n{'Analyst':<22}{'Avg MAE':>10}{'Volatility':>12}{'Best Wk':>10}{'Worst Wk':>10}")
print("-" * 66)
for _, row in consistency.iterrows():
    print(f"{row['analyst']:<22}{row['avg_mae']:>10}{row['std_mae']:>12}"
          f"{row['best_week']:>10}{row['worst_week']:>10}")

# ════════════════════════════════════════════════════════════════════════════
# BIAS ANALYSIS 4: ANALYST PROFILES
# Combine everything into a single profile per analyst
# ════════════════════════════════════════════════════════════════════════════
print("\n" + "═"*60)
print("ANALYST PROFILES — FULL SUMMARY")
print("═"*60)

# Find each analyst's strongest and weakest position
best_pos  = positional_bias.loc[
    positional_bias.groupby("analyst")["bias"].apply(lambda x: x.abs().idxmin())
][["analyst", "position", "bias"]].rename(
    columns={"position": "best_position", "bias": "best_pos_bias"}
)

worst_pos = positional_bias.loc[
    positional_bias.groupby("analyst")["bias"].apply(lambda x: x.abs().idxmax())
][["analyst", "position", "bias"]].rename(
    columns={"position": "worst_position", "bias": "worst_pos_bias"}
)

profiles = (
    directional[["analyst", "overall_bias", "volatility"]]
    .merge(consistency[["analyst", "std_mae"]], on="analyst")
    .merge(best_pos,  on="analyst")
    .merge(worst_pos, on="analyst")
)

for _, row in profiles.iterrows():
    bias_type = "OPTIMIST" if row["overall_bias"] > 0.3 else \
                "PESSIMIST" if row["overall_bias"] < -0.3 else "NEUTRAL"
    print(f"\n  {row['analyst']}")
    print(f"    Overall bias:    {row['overall_bias']:+.3f} ({bias_type})")
    print(f"    Consistency:     {row['std_mae']:.3f} week-to-week volatility")
    print(f"    Strongest at:    {row['best_position']} (bias {row['best_pos_bias']:+.3f})")
    print(f"    Weakest at:      {row['worst_position']} (bias {row['worst_pos_bias']:+.3f})")

# ── SAVE RESULTS ──────────────────────────────────────────────────────────────
print("\n\n💾 Saving bias results...")

cursor = conn.cursor()
cursor.execute("DROP TABLE IF EXISTS bias_positional")
cursor.execute("DROP TABLE IF EXISTS bias_directional")
cursor.execute("DROP TABLE IF EXISTS bias_consistency")

positional_bias.to_sql("bias_positional",  conn, if_exists="append", index=False)
directional.to_sql("bias_directional",     conn, if_exists="append", index=False)
consistency.to_sql("bias_consistency",     conn, if_exists="append", index=False)

conn.commit()
conn.close()

positional_bias.to_csv("data/bias_positional.csv",  index=False)
directional.to_csv("data/bias_directional.csv",     index=False)
consistency.to_csv("data/bias_consistency.csv",     index=False)

print("✅ Saved to database and CSV")
print("\n✅ Module 6 complete — bias profiles built")
# ════════════════════════════════════════════════════════════════════════════
# BIAS ANALYSIS 5: TEAM BIAS
# Does an analyst systematically over/underrate players from specific teams?
# ════════════════════════════════════════════════════════════════════════════
print("\n" + "═"*60)
print("BIAS ANALYSIS 5: TEAM BIAS")
print("═"*60)

# We need team data — pull it from nfl-data-py
import ssl
ssl._create_default_https_context = ssl._create_unverified_context
import nfl_data_py as nfl

print("📥 Fetching team roster data...")
rosters = nfl.import_weekly_data([2024])
rosters = rosters[rosters["season_type"] == "REG"]

# Build a player → team lookup
# A player might change teams mid-season, so we take their most common team
player_team = (
    rosters
    .groupby("player_display_name")["recent_team"]
    .agg(lambda x: x.mode()[0])  # Most frequent team for this player
    .reset_index()
    .rename(columns={
        "player_display_name": "player",
        "recent_team":         "team"
    })
)

print(f"   Built team lookup for {len(player_team)} players")

# Join team info onto our merged predictions dataset
merged_teams = merged.merge(player_team, on="player", how="left")
merged_teams = merged_teams.dropna(subset=["team"])

print(f"   Matched {len(merged_teams)} predictions to teams")

# Calculate average signed error per analyst per team
team_bias = (
    merged_teams
    .groupby(["analyst", "team"])["signed_error"]
    .agg(
        bias        = "mean",
        sample_size = "count",
    )
    .reset_index()
    .round(3)
)

# Only keep teams with enough sample size to be meaningful
team_bias = team_bias[team_bias["sample_size"] >= 5]

# Find each analyst's most biased teams (top 3 over and under)
print("\n🏈 Strongest team biases detected:")
for analyst_name in sorted(team_bias["analyst"].unique()):
    analyst_teams = team_bias[team_bias["analyst"] == analyst_name].copy()
    analyst_teams = analyst_teams.sort_values("bias")

    most_underrated = analyst_teams.head(2)  # Most negative = underrates
    most_overrated  = analyst_teams.tail(2)  # Most positive = overrates

    print(f"\n  {analyst_name}:")
    for _, row in most_overrated.iterrows():
        print(f"    ▲ Overrates  {row['team']:<5} bias={row['bias']:+.3f} "
              f"(n={int(row['sample_size'])})")
    for _, row in most_underrated.iterrows():
        print(f"    ▼ Underrates {row['team']:<5} bias={row['bias']:+.3f} "
              f"(n={int(row['sample_size'])})")

# ════════════════════════════════════════════════════════════════════════════
# BIAS ANALYSIS 6: PLAYER BIAS
# Does an analyst persistently over/underrate specific players vs consensus?
# ════════════════════════════════════════════════════════════════════════════
print("\n" + "═"*60)
print("BIAS ANALYSIS 6: PLAYER BIAS")
print("═"*60)

# Step 1: Calculate consensus rank for each player each week
# Consensus = average rank across ALL analysts for that player that week
consensus = (
    rankings_df
    .groupby(["season", "week", "position", "player"])["rank"]
    .mean()
    .reset_index()
    .rename(columns={"rank": "consensus_rank"})
)

# Step 2: Join each analyst's rank against consensus
player_bias_df = rankings_df.rename(columns={"rank": "analyst_rank"}).merge(
    consensus,
    on=["season", "week", "position", "player"],
    how="left"
)

# Step 3: Calculate rank deviation from consensus
# Positive = analyst ranks player HIGHER than consensus (bull)
# Negative = analyst ranks player LOWER than consensus (bear)
player_bias_df["rank_deviation"] = (
    player_bias_df["consensus_rank"] - player_bias_df["analyst_rank"]
)

# Step 4: Average deviation per analyst per player across all weeks
player_bias = (
    player_bias_df
    .groupby(["analyst", "position", "player"])["rank_deviation"]
    .agg(
        avg_deviation = "mean",
        consistency   = "std",    # Low std = consistently biased
        weeks_ranked  = "count",
    )
    .reset_index()
    .round(3)
)

# Only meaningful if ranked enough weeks
player_bias = player_bias[player_bias["weeks_ranked"] >= 6]

# Fill NaN consistency (only ranked in 1 week) with 0
player_bias["consistency"] = player_bias["consistency"].fillna(0)

# Flag strong bulls and bears (deviation > 1.5 spots consistently)
bulls = player_bias[player_bias["avg_deviation"] >  1.5].copy()
bears = player_bias[player_bias["avg_deviation"] < -1.5].copy()

print(f"\n   Strong bulls detected: {len(bulls)}")
print(f"   Strong bears detected: {len(bears)}")

print("\n🐂 Top Bulls (analysts who consistently rank a player much higher than peers):")
top_bulls = bulls.sort_values("avg_deviation", ascending=False).head(15)
for _, row in top_bulls.iterrows():
    print(f"   {row['analyst']:<22} {row['player']:<25} "
          f"+{row['avg_deviation']:.2f} spots above consensus  "
          f"({int(row['weeks_ranked'])} weeks)")

print("\n🐻 Top Bears (analysts who consistently rank a player much lower than peers):")
top_bears = bears.sort_values("avg_deviation").head(15)
for _, row in top_bears.iterrows():
    print(f"   {row['analyst']:<22} {row['player']:<25} "
          f"{row['avg_deviation']:.2f} spots below consensus  "
          f"({int(row['weeks_ranked'])} weeks)")

# ── SAVE NEW BIAS TABLES ──────────────────────────────────────────────────────
print("\n💾 Saving team and player bias results...")

conn2 = sqlite3.connect("data/rankings.db")
cursor2 = conn2.cursor()

cursor2.execute("DROP TABLE IF EXISTS bias_team")
cursor2.execute("DROP TABLE IF EXISTS bias_player")

team_bias.to_sql("bias_team",     conn2, if_exists="append", index=False)
player_bias.to_sql("bias_player", conn2, if_exists="append", index=False)

conn2.commit()
conn2.close()

team_bias.to_csv("data/bias_team.csv",     index=False)
player_bias.to_csv("data/bias_player.csv", index=False)

print("✅ Team and player bias saved")
print("\n✅ Module 6 extended — team and player bias complete")