"""Storage layer — saves scraped MatchDetail objects to SQLite."""

from datetime import datetime

from sqlalchemy.orm import Session

from src.pipeline.models import (
    Ban,
    Match,
    Pick,
    PlayerStat,
    ScrapeLog,
    init_db,
    get_engine,
    get_session,
)
from src.scrapers.golgg import MatchDetail, MatchSummary


def save_match_detail(detail: MatchDetail, session: Session | None = None) -> Match:
    """Persist a single MatchDetail to the database.

    If a match with the same game_id already exists, it is skipped.
    Returns the Match ORM object (new or existing).
    """
    own_session = session is None
    if own_session:
        session = get_session()

    try:
        # Check for existing
        existing = session.query(Match).filter_by(game_id=detail.game_id).first()
        if existing:
            return existing

        match = Match(
            game_id=detail.game_id,
            game_date=detail.game_date,
            tournament=detail.tournament,
            patch=detail.patch,
            game_time=detail.game_time,
            game_name=f"{detail.blue_team} vs {detail.red_team}",
            blue_team=detail.blue_team,
            red_team=detail.red_team,
            winner=detail.winner,
            blue_kills=detail.blue_kills,
            red_kills=detail.red_kills,
            blue_towers=detail.blue_towers,
            red_towers=detail.red_towers,
            blue_dragons=detail.blue_dragons,
            red_dragons=detail.red_dragons,
            blue_barons=detail.blue_barons,
            red_barons=detail.red_barons,
            blue_gold=detail.blue_gold,
            red_gold=detail.red_gold,
            blue_first_blood=detail.blue_first_blood,
            red_first_blood=detail.red_first_blood,
            blue_first_tower=detail.blue_first_tower,
            red_first_tower=detail.red_first_tower,
            blue_dragon_types=",".join(detail.blue_dragon_types) if detail.blue_dragon_types else None,
            red_dragon_types=",".join(detail.red_dragon_types) if detail.red_dragon_types else None,
        )
        session.add(match)
        session.flush()  # Get match.id

        # Bans
        for i, champ in enumerate(detail.blue_bans):
            session.add(Ban(match_id=match.id, champion=champ, side="blue", slot=i))
        for i, champ in enumerate(detail.red_bans):
            session.add(Ban(match_id=match.id, champion=champ, side="red", slot=i))

        # Picks
        for role, champ in [
            ("top", detail.blue_comp.top),
            ("jgl", detail.blue_comp.jungle),
            ("mid", detail.blue_comp.mid),
            ("bot", detail.blue_comp.bot),
            ("sup", detail.blue_comp.support),
        ]:
            if champ:
                session.add(Pick(match_id=match.id, champion=champ, side="blue", role=role))
        for role, champ in [
            ("top", detail.red_comp.top),
            ("jgl", detail.red_comp.jungle),
            ("mid", detail.red_comp.mid),
            ("bot", detail.red_comp.bot),
            ("sup", detail.red_comp.support),
        ]:
            if champ:
                session.add(Pick(match_id=match.id, champion=champ, side="red", role=role))

        # Player stats
        for player in detail.blue_players + detail.red_players:
            session.add(PlayerStat(
                match_id=match.id,
                summoner_name=player.summoner_name,
                champion=player.champion,
                side=player.side,
                role=player.role,
                kills=player.kills,
                deaths=player.deaths,
                assists=player.assists,
                cs=player.cs,
                kda=player.kda,
            ))

        # Scrape log
        session.add(ScrapeLog(game_id=detail.game_id, success=True))

        session.commit()
        return match

    except Exception:
        session.rollback()
        # Log the failure
        try:
            session.add(ScrapeLog(
                game_id=detail.game_id,
                success=False,
                error=str(Exception),
            ))
            session.commit()
        except Exception:
            pass
        raise

    finally:
        if own_session:
            session.close()


def match_exists(game_id: int, session: Session | None = None) -> bool:
    """Check if a match has already been scraped."""
    own_session = session is None
    if own_session:
        session = get_session()
    try:
        return session.query(Match).filter_by(game_id=game_id).first() is not None
    finally:
        if own_session:
            session.close()


def get_match_count(session: Session | None = None) -> int:
    """Return total number of matches in the database."""
    own_session = session is None
    if own_session:
        session = get_session()
    try:
        return session.query(Match).count()
    finally:
        if own_session:
            session.close()


def get_unscraped_summaries(
    summaries: list[MatchSummary], session: Session | None = None
) -> list[MatchSummary]:
    """Filter a list of MatchSummary objects to only those not yet scraped."""
    own_session = session is None
    if own_session:
        session = get_session()
    try:
        existing_ids = {
            row[0] for row in session.query(Match.game_id).all()
        }
        return [s for s in summaries if s.game_id not in existing_ids]
    finally:
        if own_session:
            session.close()
