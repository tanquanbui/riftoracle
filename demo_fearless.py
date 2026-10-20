"""Simulate a fearless draft series between two LCK teams.

  python demo_fearless.py                        # HLE vs DK, Bo5, 1000 series
  python demo_fearless.py T1 GEN --bo 3 -n 3000
  python demo_fearless.py HLE DK --mode soft     # soft fearless (own picks only)
  python demo_fearless.py HLE DK --show-series   # print one full series draft
  python demo_fearless.py HLE DK --start 1-1 --burned-a Ahri,Vi --burned-b Orianna,Xin\\ Zhao
  python demo_fearless.py HLE DK --force 1:7:Orianna   # game 1, step 7 (blue first pick)
  python demo_fearless.py HLE DK --use-db        # champion data from scraped games
"""

from __future__ import annotations

import argparse

from demo_lck_season import build_all_lck_teams
from src.draft.data import ChampionCatalog
from src.draft.fearless import (
    FearlessMode, FearlessSeriesSimulator, SeriesConfig, SeriesStart, format_series,
)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("team_a", nargs="?", default="HLE")
    parser.add_argument("team_b", nargs="?", default="DK")
    parser.add_argument("--bo", type=int, default=5, choices=[1, 3, 5])
    parser.add_argument("-n", type=int, default=1000, help="Number of series to simulate")
    parser.add_argument("--mode", default="hard", choices=[m.value for m in FearlessMode])
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--show-series", action="store_true", help="Print one full series")
    parser.add_argument("--start", help="Current score, team_a-team_b, e.g. 1-1")
    parser.add_argument("--burned-a", default="", help="Champions team_a already played")
    parser.add_argument("--burned-b", default="", help="Champions team_b already played")
    parser.add_argument("--b-on-blue", action="store_true", help="team_b on blue for the next game")
    parser.add_argument("--force", action="append", default=[],
                        help="game:step:champion — force a ban/pick (steps 1-20)")
    parser.add_argument("--use-db", action="store_true", help="Use scraped data/riftoracle.db")
    args = parser.parse_args()

    teams = {t.tag: t for t in build_all_lck_teams()}
    try:
        team_a, team_b = teams[args.team_a.upper()], teams[args.team_b.upper()]
    except KeyError as e:
        raise SystemExit(f"Unknown team {e}. Choose from: {', '.join(teams)}")

    catalog = None
    if args.use_db:
        from matchups import DEFAULT_DB, open_session
        catalog = ChampionCatalog.from_database(open_session(DEFAULT_DB))

    start = None
    if args.start or args.burned_a or args.burned_b:
        wa, wb = (int(x) for x in (args.start or "0-0").split("-"))
        start = SeriesStart(
            wins_a=wa, wins_b=wb,
            picked_by_a=[c.strip() for c in args.burned_a.split(",") if c.strip()],
            picked_by_b=[c.strip() for c in args.burned_b.split(",") if c.strip()],
            a_on_blue=not args.b_on_blue,
        )

    forced: dict[int, dict[int, str]] = {}
    for spec in args.force:
        game, step, champ = spec.split(":", 2)
        forced.setdefault(int(game), {})[int(step)] = champ

    sim = FearlessSeriesSimulator(
        team_a, team_b,
        config=SeriesConfig(best_of=args.bo, mode=FearlessMode(args.mode)),
        catalog=catalog, seed=args.seed,
    )
    report = sim.run(args.n, start=start, forced=forced)
    print(report.format())
    if args.show_series and report.sample:
        print("\n" + "=" * 64 + "\n  One sample series, full draft\n" + "=" * 64)
        print(format_series(report.sample))


if __name__ == "__main__":
    main()
