# RiftManager

**Football Manager meets League of Legends esports.**

Take control of a professional LoL team. Draft players, manage rosters, navigate the meta, and lead your squad through seasons of competitive play. Every pick, ban, and signing matters.

Powered by real match data scraped from competitive play.

## Features (in progress)

- **Match Simulation Engine** — Realistic game simulation with champion matchups, player proficiency, team synergy, and upset potential
- **Real Player Data** — Rosters and stats scraped from [gol.gg](https://gol.gg)
- **Draft Phase** — Ban/pick strategy with champion counters and meta strength
- **Season Mode** — Full league schedule → playoffs → championship (coming soon)
- **Roster Management** — Sign, trade, develop players (coming soon)

## Quick Demo

```bash
python demo_hle_dk.py
```

Simulates the real LCK HLE vs DK match with actual rosters and drafts.

## Architecture

```
src/
  sim/          # Match simulation engine
  scrapers/     # gol.gg data scraping
  pipeline/     # Database storage (SQLAlchemy + SQLite)
  api/          # FastAPI backend (coming soon)
tests/          # Test suite (15 passing)
```

## Setup

```bash
pip install -e ".[dev]"
```

## Data Sources

| Source | Purpose |
|---|---|
| [gol.gg](https://gol.gg) | Match data, player stats, champion comps |
| [LoL Esports API](https://esports-api.lolesports.com) | Live schedule, team rosters |
