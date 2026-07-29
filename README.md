# RiftOracle

**League of Legends esports match prediction engine.**

Predicts professional LoL match outcomes using machine learning trained on historical match data, champion statistics, patch notes, and player performance metrics. Inspired by AWS's live Win Probability model used in LCS/LEC/Worlds broadcasts.

## Data Sources

| Source | Purpose | Method |
|---|---|---|
| [gol.gg](https://gol.gg) | Historical match data (champs, players, builds, KDA, objectives, timeline) | Web scraping |
| [LoL Esports API](https://esports-api.lolesports.com) | Live schedule, team rosters, league standings | REST API |
| Riot Games Data Dragon | Champion/base stats, item data, patch notes | Static data + scraping |

## Architecture

```
data/               # All data (gitignored except schemas)
  raw/              # Raw scraped data
  processed/        # Cleaned, feature-engineered datasets
models/             # Trained model artifacts
features/           # Feature engineering pipelines
notebooks/          # Exploratory analysis
src/
  scrapers/         # gol.gg + patch note scrapers
  pipeline/         # ETL orchestration
  models/           # Training + inference
  features/         # Feature transforms
  api/              # Prediction API server
  utils/            # Shared utilities
tests/              # Test suite
docs/               # Documentation
```

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Usage

*Coming soon.*
