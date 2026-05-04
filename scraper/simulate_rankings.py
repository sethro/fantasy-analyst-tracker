import pandas as pd
import random

# ── SEED ──────────────────────────────────────────────────────────────────────
# Setting a seed means our "random" data is actually the same every time we run
# this script. That makes testing consistent.
random.seed(42)

# ── ANALYSTS ──────────────────────────────────────────────────────────────────
# These are real FantasyPros analysts from the 2025 season
ANALYSTS = [
    "Justin Boone",
    "Dave Richard",
    "Sal Vetri",
    "Jake Ciely",
    "Heath Cummings",
    "Scott Pianowski",
    "Jamey Eisenberg",
    "Michael Fabiano",
    "Andy Behrens",
    "Adam Rank",
]

# ── PLAYERS BY POSITION ───────────────────────────────────────────────────────
# Real 2025 NFL players, organized by position
PLAYERS = {
    "QB": [
        "Lamar Jackson", "Josh Allen", "Jalen Hurts", "Joe Burrow",
        "Justin Herbert", "Dak Prescott", "Jordan Love", "Kyler Murray",
        "Tua Tagovailoa", "Brock Purdy", "Anthony Richardson", "Trevor Lawrence",
    ],
    "RB": [
        "Christian McCaffrey", "Breece Hall", "Bijan Robinson", "De'Von Achane",
        "Saquon Barkley", "Jonathan Taylor", "Tony Pollard", "Derrick Henry",
        "James Cook", "Josh Jacobs", "Rhamondre Stevenson", "Travis Etienne",
        "Najee Harris", "David Montgomery", "Kyren Williams", "Aaron Jones",
    ],
    "WR": [
        "Tyreek Hill", "CeeDee Lamb", "Justin Jefferson", "Ja'Marr Chase",
        "Stefon Diggs", "Puka Nacua", "Amon-Ra St. Brown", "Davante Adams",
        "DeVonta Smith", "Keenan Allen", "Garrett Wilson", "DK Metcalf",
        "Tee Higgins", "Michael Pittman", "Chris Olave", "Drake London",
    ],
    "TE": [
        "Sam LaPorta", "Brock Bowers", "Mark Andrews", "Travis Kelce",
        "Cole Kmet", "David Njoku", "Dallas Goedert", "George Kittle",
        "Jake Ferguson", "Pat Freiermuth", "Isaiah Likely", "Foster Moreau",
    ],
    "DST": [
        "SF DST", "DAL DST", "NE DST",
        "BAL DST", "PIT DST", "BUF DST",
        "CLE DST", "MIA DST", "KC DST",
        "PHI DST",
    ],
}

# ── ANALYST BIASES ────────────────────────────────────────────────────────────
# This is the interesting part. Each analyst has a positional bias score.
# Positive = they tend to rank this position's players HIGHER than consensus
# Negative = they tend to rank this position's players LOWER than consensus
# This simulates the real phenomenon we're trying to detect
ANALYST_BIASES = {
    "Justin Boone":    {"QB": -1, "RB":  2, "WR":  0, "TE": -1, "DST":  0},
    "Dave Richard":    {"QB":  0, "RB": -1, "WR":  2, "TE":  1, "DST": -1},
    "Sal Vetri":       {"QB":  2, "RB":  0, "WR": -1, "TE":  0, "DST":  1},
    "Jake Ciely":      {"QB":  1, "RB":  1, "WR": -1, "TE": -2, "DST":  0},
    "Heath Cummings":  {"QB": -1, "RB":  0, "WR":  1, "TE":  2, "DST": -1},
    "Scott Pianowski": {"QB":  0, "RB": -2, "WR":  1, "TE":  0, "DST":  2},
    "Jamey Eisenberg": {"QB":  1, "RB":  0, "WR": -2, "TE":  1, "DST":  0},
    "Michael Fabiano": {"QB": -1, "RB":  1, "WR":  0, "TE": -1, "DST":  2},
    "Andy Behrens":    {"QB":  0, "RB": -1, "WR":  2, "TE":  0, "DST": -1},
    "Adam Rank":       {"QB":  2, "RB":  0, "WR": -1, "TE":  1, "DST": -2},
}

# ── GENERATE RANKINGS ─────────────────────────────────────────────────────────
rows = []  # This will hold every row of our table

for week in range(1, 19):          # Weeks 1 through 18
    for analyst in ANALYSTS:
        for position in PLAYERS:
            players = PLAYERS[position].copy()  # Get the player list for this position
            bias = ANALYST_BIASES[analyst][position]  # Get this analyst's bias

            # Shuffle the players randomly, then apply the bias
            # bias > 0 = push some players up (lower rank number = better)
            # We simulate this by slightly reordering the shuffle
            random.shuffle(players)

            # Apply bias: shift ranking slightly based on analyst tendency
            # A bias of +2 means this analyst is 2 spots more optimistic on average
            biased_players = players[:]
            shift = abs(bias)
            if bias > 0 and len(biased_players) > shift:
                # Move the top player up (more bullish on this position overall)
                top = biased_players.pop(0)
                biased_players.insert(max(0, shift - 1), top)
            elif bias < 0 and len(biased_players) > shift:
                # Push a top player down (more bearish on this position)
                top = biased_players.pop(0)
                biased_players.insert(min(len(biased_players), shift + 1), top)

            # Now record each player's rank
            for rank, player in enumerate(biased_players, start=1):
                rows.append({
                    "week": week,
                    "season": 2024,
                    "analyst": analyst,
                    "position": position,
                    "player": player,
                    "rank": rank,
                })

# ── SAVE TO CSV ───────────────────────────────────────────────────────────────
df = pd.DataFrame(rows)  # Convert our list of rows into a pandas DataFrame
df.to_csv("data/rankings_simulated.csv", index=False)  # Save it

print(f"✅ Generated {len(df)} rows")
print(f"   Weeks: {df['week'].nunique()}")
print(f"   Analysts: {df['analyst'].nunique()}")
print(f"   Positions: {df['position'].unique()}")
print("\nFirst 5 rows:")
print(df.head())