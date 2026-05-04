# Fantasy Analyst Tracker

A full-stack data pipeline that scores NFL fantasy analyst prediction accuracy 
and detects positional, team, and player bias.

## Built with
Python · Streamlit · SQLite · nfl-data-py · Playwright · Cowork

## Modules completed
1. Environment Setup
2. Simulation Data
3. SQLite Database
4. Real 2024 NFL Data (nfl-data-py)
5. Accuracy Scoring (MAE + Spearman)
6. Bias Analysis (positional + team + player)
7. 6-page Streamlit Dashboard
8. Cowork Integration
9. Streamlit Cloud Deployment

## September 2025 — To Do
- Build scraper/scrape_rankings.py (Playwright, live FantasyPros data)
- Add publication column for 150+ analyst filter layer
- Update SEASON = 2025 in fetch_actuals.py
- Run setup_database.py to reset for new season
- Add filter sidebar to dashboard

## Running locally
source venv/bin/activate
streamlit run app/dashboard.py

## Weekly update
./run_weekly_update.sh
