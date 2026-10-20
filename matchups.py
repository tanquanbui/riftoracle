"""Build and query your own matchup database from gol.gg.

  # 1. Scrape games into data/riftoracle.db
  python matchups.py scrape --recent              # games on the gol.gg homepage
  python matchups.py scrape --ids 65000-65500     # backfill a range of game IDs

  # 2. Ask it questions
  python matchups.py report                       # most favourable matchups, all roles
  python matchups.py report --role mid --min-games 5
  python matchups.py report --champion Ahri       # Ahri's best and worst lanes
  python matchups.py report --tournament LCK --patch 16.1
"""

from __future__ import annotations

import argparse
import logging
import time
from pathlib import Path

import httpx
from sqlalchemy.orm import Session

from src.draft.matchups import MatchupDatabase
from src.pipeline.models import Base, get_engine
from src.pipeline.storage import match_exists, save_match_detail
from src.scrapers.golgg import _create_client, fetch_match_detail, fetch_match_summaries
from src.sim.engine import Role

DEFAULT_DB = "sqlite:///data/riftoracle.db"


def open_session(db_url: str) -> Session:
    if db_url.startswith("sqlite:///"):
        Path(db_url.removeprefix("sqlite:///")).parent.mkdir(parents=True, exist_ok=True)
    engine = get_engine(db_url)
    Base.metadata.create_all(engine)
    return Session(engine)


def parse_ids(spec: str) -> list[int]:
    ids: list[int] = []
    for part in spec.split(","):
        if "-" in part:
            lo, hi = part.split("-")
            ids.extend(range(int(lo), int(hi) + 1))
        else:
            ids.append(int(part))
    return ids


def cmd_scrape(args) -> None:
    session = open_session(args.db)
    client = _create_client()
    ids: list[int] = []
    if args.recent:
        try:
            ids += [s.game_id for s in fetch_match_summaries(client)]
        except httpx.HTTPError as e:
            raise SystemExit(f"Could not reach gol.gg ({e}). Check your network access.")
    if args.ids:
        ids += parse_ids(args.ids)
    if not ids:
        raise SystemExit("Nothing to scrape: pass --recent and/or --ids")

    saved = skipped = failed = 0
    for i, game_id in enumerate(ids, 1):
        if match_exists(game_id, session):
            skipped += 1
            continue
        try:
            detail = fetch_match_detail(game_id, client)
        except httpx.HTTPError as e:
            print(f"  {game_id}: request failed ({e})")
            failed += 1
            continue
        if not detail or not detail.winner or not detail.blue_comp.mid:
            failed += 1  # Missing page or unparseable draft
        else:
            save_match_detail(detail, session)
            saved += 1
            print(f"  [{i}/{len(ids)}] {game_id}: {detail.blue_team} vs {detail.red_team} "
                  f"({detail.tournament}, {detail.patch})")
        time.sleep(args.delay)  # Be polite to gol.gg

    client.close()
    print(f"\nSaved {saved}, already had {skipped}, failed/empty {failed}.")


def cmd_report(args) -> None:
    session = open_session(args.db)
    db = MatchupDatabase.from_session(session, tournament=args.tournament, patch=args.patch)
    print(f"Games analysed: {db.games}"
          + (f" (tournament ~ '{args.tournament}')" if args.tournament else "")
          + (f" (patch {args.patch})" if args.patch else ""))
    if not db.games:
        print("No games yet — run `python matchups.py scrape --recent` first.")
        return
    role = Role(args.role) if args.role else None

    if args.champion:
        rows = db.counters(args.champion, role, min_games=args.min_games)
        if not rows:
            print(f"No lane data for {args.champion} with ≥{args.min_games} games.")
            return
        print(f"\n{args.champion} lane matchups (best first):")
        print_rows(rows, show_champion=False)
        return

    print(f"\nMost favourable matchups{' — ' + role.value if role else ''} "
          f"(≥{args.min_games} games):")
    print_rows(db.most_favourable(role, args.min_games, args.limit))

    print(f"\nHighest presence (picked + banned){' — ' + role.value if role else ''}:")
    print(f"  {'Champion':<14} {'Games':>5} {'Bans':>5} {'Presence':>9} {'Win%':>6}")
    for rec in db.top_champions(role, args.limit):
        print(f"  {rec.champion:<14} {rec.games:>5} {rec.bans:>5} "
              f"{db.presence(rec.champion):>9.0%} {rec.win_rate:>6.0%}")


def print_rows(rows, show_champion: bool = True) -> None:
    head = f"  {'Role':<5}" + (f"{'Champion':<14}" if show_champion else "")
    print(head + f"{'vs':<14} {'Games':>5} {'W-L':>7} {'Win%':>6} {'Adj%':>6}")
    for r in rows:
        line = f"  {r.role.value:<5}" + (f"{r.champion:<14}" if show_champion else "")
        print(line + f"{r.opponent:<14} {r.games:>5} {f'{r.wins}-{r.games - r.wins}':>7} "
              f"{r.win_rate:>6.0%} {r.smoothed:>6.0%}")
    print("  (Adj% = win rate smoothed toward 50% so tiny samples don't dominate)")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--db", default=DEFAULT_DB)
    sub = parser.add_subparsers(dest="command", required=True)

    s = sub.add_parser("scrape", help="Scrape gol.gg games into the database")
    s.add_argument("--recent", action="store_true", help="Games listed on the gol.gg homepage")
    s.add_argument("--ids", help="Game IDs, e.g. 65000-65500 or 65001,65007")
    s.add_argument("--delay", type=float, default=1.0, help="Seconds between requests")
    s.set_defaults(func=cmd_scrape)

    r = sub.add_parser("report", help="Show matchup stats")
    r.add_argument("--role", choices=[x.value for x in Role])
    r.add_argument("--champion")
    r.add_argument("--min-games", type=int, default=3)
    r.add_argument("--limit", type=int, default=15)
    r.add_argument("--tournament")
    r.add_argument("--patch")
    r.set_defaults(func=cmd_report)

    args = parser.parse_args()
    logging.basicConfig(level=logging.WARNING)
    args.func(args)


if __name__ == "__main__":
    main()
