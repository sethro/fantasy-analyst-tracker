#!/bin/bash
# ── FANTASY ANALYST TRACKER — WEEKLY UPDATE SCRIPT ───────────────────────────
# Run this every Tuesday after NFL games conclude (Week concludes Monday night)
# Cowork triggers this script, then reads the output to generate a report

# Navigate to project directory
cd ~/Desktop/fantasy-analyst-tracker

# Activate virtual environment
source venv/bin/activate

echo "============================================"
echo "FANTASY ANALYST TRACKER — WEEKLY UPDATE"
echo "Started: $(date)"
echo "============================================"

# Step 1: Fetch latest actual results
echo ""
echo "Step 1/3: Fetching actual NFL results..."
python3 scraper/fetch_actuals.py
if [ $? -ne 0 ]; then
    echo "ERROR: fetch_actuals.py failed"
    exit 1
fi

# Step 2: Score accuracy
echo ""
echo "Step 2/3: Scoring analyst accuracy..."
python3 analysis/score_accuracy.py
if [ $? -ne 0 ]; then
    echo "ERROR: score_accuracy.py failed"
    exit 1
fi

# Step 3: Run bias analysis
echo ""
echo "Step 3/3: Running bias analysis..."
python3 analysis/bias_analysis.py
if [ $? -ne 0 ]; then
    echo "ERROR: bias_analysis.py failed"
    exit 1
fi

echo ""
echo "============================================"
echo "UPDATE COMPLETE: $(date)"
echo "============================================"
echo ""
echo "Output files updated:"
echo "  data/accuracy_weekly.csv"
echo "  data/accuracy_season.csv"
echo "  data/bias_positional.csv"
echo "  data/bias_directional.csv"
echo "  data/bias_team.csv"
echo "  data/bias_player.csv"
echo ""
echo "Dashboard: streamlit run app/dashboard.py"