# RiftManager

**Football Manager meets League of Legends esports.**

Take control of a professional LoL team. Draft players, manage rosters, navigate the meta, and lead your squad through seasons of competitive play. Every pick, ban, and signing matters.

Powered by real match data scraped from competitive play.

## Features (in progress)

- **Match Simulation Engine** — Realistic game simulation with champion matchups, player proficiency, team synergy, and upset potential
- **Real Player Data** — Rosters and stats scraped from [gol.gg](https://gol.gg)
- **Fearless Draft Series Sim** — Bo3/Bo5 under hard/soft fearless rules, full 20-step tournament draft, Monte Carlo over thousands of series
- **Matchup Database** — Build your own lane matchup stats from scraped gol.gg games
- **Season Mode** — Full league schedule → playoffs → championship (coming soon)
- **Roster Management** — Sign, trade, develop players (coming soon)

## Quick Demo

```bash
python demo_hle_dk.py
```

Simulates the real LCK HLE vs DK match with actual rosters and drafts.

## Fearless Draft Simulator

```bash
python demo_fearless.py HLE DK                 # Bo5, hard fearless, 1000 series
python demo_fearless.py T1 GEN --bo 3 -n 3000
python demo_fearless.py HLE DK --show-series   # print one full series, every ban/pick
python demo_fearless.py HLE DK --start 1-1 --burned-a Ahri,Vi --burned-b Orianna
python demo_fearless.py HLE DK --force 1:7:Orianna   # game 1, step 7 = blue first pick
python demo_fearless.py HLE DK --use-db        # use your scraped matchup data
```

Each draft is played step by step by a draft AI weighing player comfort, meta
strength, lane counters, and fearless resource management (denying the enemy's
comfort picks vs. saving your own). The report shows series odds, score and
path probabilities, how each team's comfort drains game by game, the most
picked/banned champions per game, and what each player ends up playing.

## Matchup Database

```bash
python matchups.py scrape --recent             # games on the gol.gg homepage
python matchups.py scrape --ids 65000-65500    # backfill a range of game IDs
python matchups.py report --role mid --min-games 5
python matchups.py report --champion Ahri      # best and worst lanes for Ahri
python matchups.py report --tournament LCK --patch 16.14
```

Win rates are smoothed toward 50% so small samples don't look like hard counters.
Once games are scraped, `--use-db` feeds real meta strength and matchups into
the draft AI and match engine.

## Architecture

```
src/
  sim/          # Match simulation engine
  draft/        # Fearless draft AI, series sim, matchup database
  scrapers/     # gol.gg data scraping
  pipeline/     # Database storage (SQLAlchemy + SQLite)
  api/          # FastAPI backend (coming soon)
tests/          # Test suite
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
