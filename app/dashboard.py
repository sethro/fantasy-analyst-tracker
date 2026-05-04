import streamlit as st
import sqlite3
import pandas as pd
import numpy as np

# ── PAGE CONFIG ───────────────────────────────────────────────────────────────
# This must be the first Streamlit command in the file
st.set_page_config(
    page_title="Fantasy Analyst Tracker",
    page_icon="🏈",
    layout="wide",          # Use full browser width
    initial_sidebar_state="expanded"
)

# ── LOAD DATA ─────────────────────────────────────────────────────────────────
# @st.cache_data tells Streamlit: "cache this function's result"
# That means the database is only read once, not every time the user
# clicks something. Makes the app feel instant.
st.cache_data
@st.cache_data
def load_data():
    base = "data/"
    
    accuracy_weekly  = pd.read_csv(base + "accuracy_weekly.csv")
    accuracy_season  = pd.read_csv(base + "accuracy_season.csv")
    bias_positional  = pd.read_csv(base + "bias_positional.csv")
    bias_directional = pd.read_csv(base + "bias_directional.csv")
    bias_consistency = pd.read_csv(base + "bias_consistency.csv")
    actuals          = pd.read_csv(base + "actuals_export.csv")
    bias_team        = pd.read_csv(base + "bias_team.csv")
    bias_player      = pd.read_csv(base + "bias_player.csv")

    return (accuracy_weekly, accuracy_season, bias_positional,
            bias_directional, bias_consistency, actuals,
            bias_team, bias_player)

(accuracy_weekly, accuracy_season, bias_positional,
 bias_directional, bias_consistency, actuals,
 bias_team, bias_player) = load_data()

# ── SIDEBAR ───────────────────────────────────────────────────────────────────
st.sidebar.image("https://www.fantasypros.com/images/logos/fantasypros-logo.png",
                 width=200)
st.sidebar.title("🏈 Fantasy Analyst Tracker")
st.sidebar.markdown("---")

# Navigation
page = st.sidebar.radio(
    "Navigate",
    ["📋 Leaderboard", "🎯 Accuracy by Position",
     "🧠 Bias Profiles", "📈 Week by Week",
     "🏈 Team Bias", "🐂 Player Bias"]
)

st.sidebar.markdown("---")
st.sidebar.markdown("**Season:** 2024")
st.sidebar.markdown("**Analysts:** 10")
st.sidebar.markdown("**Positions:** QB · RB · WR · TE · DST")
st.sidebar.markdown("**Weeks scored:** 18")

# ════════════════════════════════════════════════════════════════════════════
# PAGE 1: LEADERBOARD
# ════════════════════════════════════════════════════════════════════════════
if page == "📋 Leaderboard":
    st.title("📋 Analyst Leaderboard")
    st.markdown("Overall accuracy rankings for the 2024 NFL season. "
                "**Lower MAE = more accurate.** "
                "Spearman measures rank order accuracy (higher = better).")

    # Build overall leaderboard from accuracy_weekly
    leaderboard = (
        accuracy_weekly
        .groupby("analyst")
        .agg(
            avg_mae      = ("mae",      "mean"),
            avg_spearman = ("spearman", "mean"),
            weeks_scored = ("week",     "count"),
        )
        .reset_index()
        .sort_values("avg_mae")
        .round(3)
    )
    leaderboard.insert(0, "Rank", range(1, len(leaderboard) + 1))

    # ── KEY METRICS ROW ───────────────────────────────────────────────────
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("🥇 Most Accurate", leaderboard.iloc[0]["analyst"])
    with col2:
        st.metric("Best MAE", f"{leaderboard.iloc[0]['avg_mae']:.3f}")
    with col3:
        st.metric("Most Consistent",
                  bias_consistency.sort_values("std_mae").iloc[0]["analyst"])
    with col4:
        st.metric("Total Predictions",
                  f"{len(accuracy_weekly):,}")

    st.markdown("---")

    # ── LEADERBOARD TABLE ─────────────────────────────────────────────────
    st.subheader("Overall Rankings")

    # Color the MAE column — lower is greener
    def color_mae(val):
        min_mae = leaderboard["avg_mae"].min()
        max_mae = leaderboard["avg_mae"].max()
        ratio = (val - min_mae) / (max_mae - min_mae) if max_mae != min_mae else 0
        r = int(255 * ratio)
        g = int(255 * (1 - ratio))
        return f"background-color: rgb({r},{g},80); color: black"

    styled = leaderboard.style.map(
        color_mae, subset=["avg_mae"]
    ).format({
        "avg_mae": "{:.3f}",
        "avg_spearman": "{:.3f}",
    })

    st.dataframe(styled, use_container_width=True, hide_index=True)

    st.markdown("---")

    # ── BAR CHART ─────────────────────────────────────────────────────────
    st.subheader("MAE by Analyst (lower = better)")
    chart_data = leaderboard.set_index("analyst")["avg_mae"]
    st.bar_chart(chart_data)

# ════════════════════════════════════════════════════════════════════════════
# PAGE 2: ACCURACY BY POSITION
# ════════════════════════════════════════════════════════════════════════════
elif page == "🎯 Accuracy by Position":
    st.title("🎯 Accuracy by Position")
    st.markdown("Which analysts are best at ranking each position? "
                "Select a position to see the breakdown.")

    # Position selector
    position = st.selectbox(
        "Select Position",
        ["QB", "RB", "WR", "TE", "DST"]
    )

    pos_data = (
        accuracy_season[accuracy_season["position"] == position]
        .sort_values("avg_mae")
        .reset_index(drop=True)
    )
    pos_data.insert(0, "Rank", range(1, len(pos_data) + 1))

    # ── METRICS ───────────────────────────────────────────────────────────
    col1, col2, col3 = st.columns(3)
    with col1:
        best = pos_data.iloc[0]
        st.metric(f"Best {position} Analyst", best["analyst"],
                  delta=f"MAE: {best['avg_mae']:.3f}")
    with col2:
        worst = pos_data.iloc[-1]
        st.metric(f"Worst {position} Analyst", worst["analyst"],
                  delta=f"MAE: {worst['avg_mae']:.3f}", delta_color="inverse")
    with col3:
        avg = pos_data["avg_mae"].mean()
        st.metric("Position Avg MAE", f"{avg:.3f}")

    st.markdown("---")

    # ── TABLE ─────────────────────────────────────────────────────────────
    st.subheader(f"{position} Analyst Rankings")
    st.dataframe(
        pos_data[["Rank", "analyst", "avg_mae", "avg_spearman", "weeks_scored"]]
        .rename(columns={
            "analyst":      "Analyst",
            "avg_mae":      "Avg MAE",
            "avg_spearman": "Avg Spearman",
            "weeks_scored": "Weeks",
        })
        .style.format({"Avg MAE": "{:.3f}", "Avg Spearman": "{:.3f}"}),
        use_container_width=True,
        hide_index=True
    )

    st.markdown("---")

    # ── POSITION HEATMAP (all analysts × all positions) ───────────────────
    st.subheader("Full Position Accuracy Heatmap")
    st.markdown("Each cell = average MAE for that analyst at that position. "
                "Greener = more accurate.")

    heatmap_data = accuracy_season.pivot(
        index="analyst",
        columns="position",
        values="avg_mae"
    )[["QB", "RB", "WR", "TE", "DST"]].round(3)

    st.dataframe(
        heatmap_data.style.background_gradient(
            cmap="RdYlGn_r",   # Red = bad (high MAE), Green = good (low MAE)
            axis=None           # Normalize across entire table
        ).format("{:.3f}"),
        use_container_width=True
    )

# ════════════════════════════════════════════════════════════════════════════
# PAGE 3: BIAS PROFILES
# ════════════════════════════════════════════════════════════════════════════
elif page == "🧠 Bias Profiles":
    st.title("🧠 Analyst Bias Profiles")
    st.markdown(
        "Bias measures *how* analysts are wrong, not just *how much*. "
        "**Positive bias = tends to overrate.** "
        "**Negative bias = tends to underrate.**"
    )

    # ── ANALYST SELECTOR ──────────────────────────────────────────────────
    analyst = st.selectbox(
        "Select Analyst",
        sorted(bias_directional["analyst"].unique())
    )

    # Get this analyst's data
    dir_row  = bias_directional[bias_directional["analyst"] == analyst].iloc[0]
    cons_row = bias_consistency[bias_consistency["analyst"] == analyst].iloc[0]
    pos_rows = bias_positional[bias_positional["analyst"] == analyst]
    # ── PROFILE METRICS ───────────────────────────────────────────────────
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        bias_val = dir_row["overall_bias"]
        bias_label = "Optimist" if bias_val > 0.3 else \
                     "Pessimist" if bias_val < -0.3 else "Neutral"
        st.metric("Overall Tendency", bias_label,
                  delta=f"{bias_val:+.3f} avg pts")
    with col2:
        st.metric("% Predictions Overrated",
                  f"{dir_row['pct_overrated']:.1f}%")
    with col3:
        st.metric("Week-to-Week Volatility",
                  f"{cons_row['std_mae']:.3f}")
    with col4:
        st.metric("Best → Worst Week MAE",
                  f"{cons_row['best_week']:.2f} → {cons_row['worst_week']:.2f}")

    st.markdown("---")

    st.subheader(f"{analyst} — Positional Bias")
    st.markdown("How much does this analyst over or underrate each position?")
    pos_chart = pos_rows.set_index("position")[["bias"]].reindex(
        ["QB", "RB", "WR", "TE", "DST"]
    )
    st.bar_chart(pos_chart)

    st.markdown("---")

    st.subheader("Positional Bias Detail")
    st.dataframe(
        pos_rows[["position", "bias", "volatility", "sample_size"]]
        .rename(columns={
            "position":    "Position",
            "bias":        "Avg Signed Error",
            "volatility":  "Volatility",
            "sample_size": "Sample Size",
        })
        .sort_values("Position")
        .style.format({
            "Avg Signed Error": "{:+.3f}",
            "Volatility": "{:.3f}",
        })
        .background_gradient(subset=["Avg Signed Error"],
                             cmap="RdYlGn_r", axis=0),
        use_container_width=True,
        hide_index=True
    )

    st.markdown("---")

    st.subheader("All Analyst Bias Comparison")
    all_bias = bias_directional.sort_values("overall_bias", ascending=False)
    st.dataframe(
        all_bias.rename(columns={
            "analyst":       "Analyst",
            "overall_bias":  "Overall Bias",
            "volatility":    "Volatility",
            "pct_overrated": "% Overrated",
        })
        .style.format({
            "Overall Bias":  "{:+.3f}",
            "Volatility":    "{:.3f}",
            "% Overrated":   "{:.1f}%",
        })
        .background_gradient(subset=["Overall Bias"],
                             cmap="RdYlGn_r", axis=0),
        use_container_width=True,
        hide_index=True
    )

elif page == "📈 Week by Week":
    st.title("📈 Week-by-Week Performance")
    st.markdown("Track how analyst accuracy changes across the season.")

    col1, col2 = st.columns(2)
    with col1:
        selected_analysts = st.multiselect(
            "Select Analysts (leave empty for all)",
            sorted(accuracy_weekly["analyst"].unique()),
            default=[]
        )
    with col2:
        selected_position = st.selectbox(
            "Filter by Position",
            ["All"] + ["QB", "RB", "WR", "TE", "DST"]
        )

    wk = accuracy_weekly.copy()
    if selected_analysts:
        wk = wk[wk["analyst"].isin(selected_analysts)]
    if selected_position != "All":
        wk = wk[wk["position"] == selected_position]

    st.subheader("Weekly MAE by Analyst")
    weekly_avg = (
        wk.groupby(["analyst", "week"])["mae"]
        .mean()
        .reset_index()
        .pivot(index="week", columns="analyst", values="mae")
    )
    st.line_chart(weekly_avg)

    st.markdown("---")

    st.subheader("Weekly Detail")
    week_filter = st.slider(
        "Select Week",
        min_value=int(accuracy_weekly["week"].min()),
        max_value=int(accuracy_weekly["week"].max()),
        value=1
    )

    week_data = (
        accuracy_weekly[accuracy_weekly["week"] == week_filter]
        .groupby("analyst")
        .agg(avg_mae=("mae", "mean"), avg_spearman=("spearman", "mean"))
        .reset_index()
        .sort_values("avg_mae")
        .round(3)
    )
    week_data.insert(0, "Rank", range(1, len(week_data) + 1))

    st.dataframe(
        week_data.rename(columns={
            "analyst":      "Analyst",
            "avg_mae":      "Avg MAE",
            "avg_spearman": "Spearman",
        })
        .style.format({"Avg MAE": "{:.3f}", "Spearman": "{:.3f}"})
        .background_gradient(subset=["Avg MAE"], cmap="RdYlGn_r", axis=0),
        use_container_width=True,
        hide_index=True
    )

    st.markdown("---")
    st.subheader("Actual Fantasy Results Explorer")
    st.markdown("See what players actually scored each week.")

    col1, col2 = st.columns(2)
    with col1:
        exp_week = st.selectbox("Week", sorted(actuals["week"].unique()))
    with col2:
        exp_pos  = st.selectbox("Position", ["QB", "RB", "WR", "TE", "DST"])

    actual_view = (
        actuals[
            (actuals["week"] == exp_week) &
            (actuals["position"] == exp_pos)
        ]
        .sort_values("actual_rank")
        [["actual_rank", "player", "fantasy_points"]]
        .rename(columns={
            "actual_rank":    "Rank",
            "player":         "Player",
            "fantasy_points": "Fantasy Pts",
        })
        .head(20)
    )
    st.dataframe(actual_view, use_container_width=True, hide_index=True)
# ════════════════════════════════════════════════════════════════════════════
# PAGE 5: TEAM BIAS
# ════════════════════════════════════════════════════════════════════════════
elif page == "🏈 Team Bias":
    st.title("🏈 Team Bias")
    st.markdown(
        "Does an analyst systematically over or underrate players from "
        "specific NFL teams? **Positive = overrates that team's players. "
        "Negative = underrates them.**"
    )

    col1, col2 = st.columns(2)
    with col1:
        selected_analyst = st.selectbox(
            "Select Analyst",
            ["All Analysts"] + sorted(bias_team["analyst"].unique())
        )
    with col2:
        min_sample = st.slider(
            "Minimum sample size (weeks × players)",
            min_value=5, max_value=30, value=8
        )

    filtered = bias_team[bias_team["sample_size"] >= min_sample].copy()

    if selected_analyst != "All Analysts":
        filtered = filtered[filtered["analyst"] == selected_analyst]

    st.markdown("---")

    # ── TOP OVERRATED / UNDERRATED TEAMS ──────────────────────────────────
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Most Overrated Teams")
        overrated = (
            filtered.sort_values("bias", ascending=False)
            .head(10)
            [["analyst", "team", "bias", "sample_size"]]
            .rename(columns={
                "analyst":     "Analyst",
                "team":        "Team",
                "bias":        "Avg Bias",
                "sample_size": "Sample",
            })
        )
        st.dataframe(
            overrated.style.format({"Avg Bias": "{:+.3f}"})
            .background_gradient(subset=["Avg Bias"],
                                 cmap="RdYlGn_r", axis=0),
            use_container_width=True,
            hide_index=True
        )

    with col2:
        st.subheader("Most Underrated Teams")
        underrated = (
            filtered.sort_values("bias", ascending=True)
            .head(10)
            [["analyst", "team", "bias", "sample_size"]]
            .rename(columns={
                "analyst":     "Analyst",
                "team":        "Team",
                "bias":        "Avg Bias",
                "sample_size": "Sample",
            })
        )
        st.dataframe(
            underrated.style.format({"Avg Bias": "{:+.3f}"})
            .background_gradient(subset=["Avg Bias"],
                                 cmap="RdYlGn", axis=0),
            use_container_width=True,
            hide_index=True
        )

    st.markdown("---")

    # ── FULL TEAM BIAS HEATMAP ─────────────────────────────────────────────
    if selected_analyst == "All Analysts":
        st.subheader("Team Bias Heatmap — All Analysts")
        st.markdown("Each cell = average signed error for that analyst "
                    "ranking that team's players.")

        pivot = filtered.pivot_table(
            index="analyst",
            columns="team",
            values="bias",
            aggfunc="mean"
        ).round(3)

        st.dataframe(
            pivot.style.background_gradient(
                cmap="RdYlGn_r", axis=None
            ).format("{:+.2f}"),
            use_container_width=True
        )
    else:
        # Single analyst — show bar chart of all their team biases
        st.subheader(f"{selected_analyst} — Bias by Team")
        analyst_teams = (
            filtered.sort_values("bias", ascending=False)
            .set_index("team")[["bias"]]
        )
        st.bar_chart(analyst_teams)

# ════════════════════════════════════════════════════════════════════════════
# PAGE 6: PLAYER BIAS
# ════════════════════════════════════════════════════════════════════════════
elif page == "🐂 Player Bias":
    st.title("🐂🐻 Player Bias")
    st.markdown(
        "Which players does each analyst persistently over or underrate "
        "compared to the consensus? "
        "**Bulls** rank a player consistently higher than peers. "
        "**Bears** rank them consistently lower."
    )

    # ── FILTERS ───────────────────────────────────────────────────────────
    col1, col2, col3 = st.columns(3)
    with col1:
        pb_analyst = st.selectbox(
            "Analyst",
            ["All Analysts"] + sorted(bias_player["analyst"].unique())
        )
    with col2:
        pb_position = st.selectbox(
            "Position",
            ["All"] + ["QB", "RB", "WR", "TE", "DST"]
        )
    with col3:
        pb_min_weeks = st.slider(
            "Min weeks ranked", 
            min_value=3, max_value=18, value=8
        )

    # Filter
    pb = bias_player[bias_player["weeks_ranked"] >= pb_min_weeks].copy()
    if pb_analyst != "All Analysts":
        pb = pb[pb["analyst"] == pb_analyst]
    if pb_position != "All":
        pb = pb[pb["position"] == pb_position]

    bulls = pb[pb["avg_deviation"] >  1.0].sort_values(
        "avg_deviation", ascending=False)
    bears = pb[pb["avg_deviation"] < -1.0].sort_values(
        "avg_deviation", ascending=True)

    st.markdown("---")

    # ── METRICS ───────────────────────────────────────────────────────────
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("🐂 Bulls Detected", len(bulls))
    with col2:
        st.metric("🐻 Bears Detected", len(bears))
    with col3:
        if len(pb) > 0:
            most_biased = pb.loc[pb["avg_deviation"].abs().idxmax()]
            direction = "🐂" if most_biased["avg_deviation"] > 0 else "🐻"
            st.metric("Strongest Opinion",
                      f"{direction} {most_biased['player']}",
                      delta=f"{most_biased['avg_deviation']:+.2f} spots")

    st.markdown("---")

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("🐂 Top Bulls")
        st.markdown("Consistently ranked *higher* than consensus")
        bull_display = bulls.head(15)[
            ["analyst", "player", "position", "avg_deviation", "weeks_ranked"]
        ].rename(columns={
            "analyst":       "Analyst",
            "player":        "Player",
            "position":      "Pos",
            "avg_deviation": "Spots Above Consensus",
            "weeks_ranked":  "Weeks",
        })
        st.dataframe(
            bull_display.style.format({"Spots Above Consensus": "+{:.2f}"})
            .background_gradient(subset=["Spots Above Consensus"],
                                 cmap="Greens", axis=0),
            use_container_width=True,
            hide_index=True
        )

    with col2:
        st.subheader("🐻 Top Bears")
        st.markdown("Consistently ranked *lower* than consensus")
        bear_display = bears.head(15)[
            ["analyst", "player", "position", "avg_deviation", "weeks_ranked"]
        ].rename(columns={
            "analyst":       "Analyst",
            "player":        "Player",
            "position":      "Pos",
            "avg_deviation": "Spots Below Consensus",
            "weeks_ranked":  "Weeks",
        })
        st.dataframe(
            bear_display.style.format({"Spots Below Consensus": "{:.2f}"})
            .background_gradient(subset=["Spots Below Consensus"],
                                 cmap="Reds_r", axis=0),
            use_container_width=True,
            hide_index=True
        )

    st.markdown("---")

    # ── PLAYER SEARCH ─────────────────────────────────────────────────────
    st.subheader("🔍 Search by Player")
    st.markdown("See how every analyst feels about a specific player.")

    all_players = sorted(bias_player["player"].unique())
    selected_player = st.selectbox("Select Player", all_players)

    player_view = (
        bias_player[bias_player["player"] == selected_player]
        .sort_values("avg_deviation", ascending=False)
        [["analyst", "position", "avg_deviation", "weeks_ranked"]]
        .rename(columns={
            "analyst":       "Analyst",
            "position":      "Position",
            "avg_deviation": "Avg Deviation from Consensus",
            "weeks_ranked":  "Weeks Ranked",
        })
    )

    if len(player_view) > 0:
        st.dataframe(
            player_view.style.format(
                {"Avg Deviation from Consensus": "{:+.2f}"}
            ).background_gradient(
                subset=["Avg Deviation from Consensus"],
                cmap="RdYlGn", axis=0
            ),
            use_container_width=True,
            hide_index=True
        )

        # Bar chart showing analyst spread on this player
        st.bar_chart(
            player_view.set_index("Analyst")["Avg Deviation from Consensus"]
        )
    else:
        st.info("No data found for this player with current filters.")
st.sidebar.markdown("---")
st.sidebar.markdown(
    "Built with Python · Streamlit · SQLite\n\n"
    "Data: nfl-data-py · FantasyPros (simulated)"
)
