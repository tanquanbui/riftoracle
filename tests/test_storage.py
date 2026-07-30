"""Tests for storage layer."""

import tempfile
from datetime import date
from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from src.pipeline.models import Base, Match, Ban, Pick, PlayerStat, ScrapeLog
from src.pipeline.storage import (
    save_match_detail,
    match_exists,
    get_match_count,
    get_unscraped_summaries,
)
from src.scrapers.golgg import MatchDetail, MatchSummary, TeamComp, PlayerStats


@pytest.fixture
def db_session():
    """Create an in-memory SQLite database for testing."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session = Session(engine)
    yield session
    session.close()


def make_detail(game_id: int = 1, blue: str = "T1", red: str = "GEN") -> MatchDetail:
    """Factory for a realistic MatchDetail fixture."""
    return MatchDetail(
        game_id=game_id,
        game_date=date.today(),
        tournament="LCK 2026 Summer",
        patch="v16.14",
        game_time="32:15",
        blue_team=blue,
        red_team=red,
        winner="blue",
        blue_kills=18,
        red_kills=7,
        blue_towers=10,
        red_towers=2,
        blue_dragons=3,
        red_dragons=1,
        blue_dragon_types=["Cloud Drake", "Infernal Drake", "Ocean Drake"],
        red_dragon_types=["Mountain Drake"],
        blue_barons=1,
        red_barons=0,
        blue_gold=62000,
        red_gold=48000,
        blue_first_blood=True,
        blue_first_tower=True,
        blue_bans=["Nocturne", "Orianna", "Syndra", "Azir", "Renekton"],
        red_bans=["Kalista", "Ashe", "Vi", "Skarner", "Rumble"],
        blue_comp=TeamComp(
            top="KSante", jungle="Lee Sin", mid="Ahri", bot="Ezreal", support="Rell",
        ),
        red_comp=TeamComp(
            top="Gnar", jungle="Sejuani", mid="Taliyah", bot="Kaisa", support="Nautilus",
        ),
        blue_players=[
            PlayerStats("Zeus", "KSante", 4, 1, 8, 280, "blue", "top"),
            PlayerStats("Oner", "Lee Sin", 3, 2, 12, 210, "blue", "jgl"),
            PlayerStats("Faker", "Ahri", 6, 1, 7, 300, "blue", "mid"),
            PlayerStats("Gumayusi", "Ezreal", 4, 2, 9, 310, "blue", "bot"),
            PlayerStats("Keria", "Rell", 1, 1, 14, 35, "blue", "sup"),
        ],
        red_players=[
            PlayerStats("Kiin", "Gnar", 2, 4, 3, 260, "red", "top"),
            PlayerStats("Canyon", "Sejuani", 1, 3, 4, 180, "red", "jgl"),
            PlayerStats("Chovy", "Taliyah", 3, 4, 2, 290, "red", "mid"),
            PlayerStats("Peyz", "Kaisa", 1, 3, 3, 300, "red", "bot"),
            PlayerStats("Lehends", "Nautilus", 0, 4, 5, 32, "red", "sup"),
        ],
    )


class TestSaveMatchDetail:
    def test_save_new_match(self, db_session):
        detail = make_detail()
        match = save_match_detail(detail, db_session)
        assert match.id is not None
        assert match.game_id == 1
        assert match.blue_team == "T1"
        assert match.winner == "blue"

    def test_save_creates_bans(self, db_session):
        detail = make_detail()
        save_match_detail(detail, db_session)
        bans = db_session.query(Ban).all()
        assert len(bans) == 10
        blue_bans = [b for b in bans if b.side == "blue"]
        assert [b.champion for b in sorted(blue_bans, key=lambda b: b.slot)] == detail.blue_bans

    def test_save_creates_picks(self, db_session):
        detail = make_detail()
        save_match_detail(detail, db_session)
        picks = db_session.query(Pick).all()
        assert len(picks) == 10
        blue_picks = [p for p in picks if p.side == "blue"]
        assert len(blue_picks) == 5

    def test_save_creates_player_stats(self, db_session):
        detail = make_detail()
        save_match_detail(detail, db_session)
        stats = db_session.query(PlayerStat).all()
        assert len(stats) == 10
        faker = db_session.query(PlayerStat).filter_by(summoner_name="Faker").first()
        assert faker is not None
        assert faker.champion == "Ahri"
        assert faker.kills == 6

    def test_deduplicates_by_game_id(self, db_session):
        detail = make_detail(game_id=42)
        first = save_match_detail(detail, db_session)
        second = save_match_detail(detail, db_session)
        assert first.id == second.id
        assert db_session.query(Match).count() == 1

    def test_creates_scrape_log(self, db_session):
        detail = make_detail()
        save_match_detail(detail, db_session)
        log = db_session.query(ScrapeLog).filter_by(game_id=1).first()
        assert log is not None
        assert log.success is True


class TestMatchExists:
    def test_returns_false_for_new_match(self, db_session):
        assert not match_exists(99999, db_session)

    def test_returns_true_after_save(self, db_session):
        detail = make_detail(game_id=55)
        save_match_detail(detail, db_session)
        assert match_exists(55, db_session)


class TestGetMatchCount:
    def test_returns_zero_for_empty_db(self, db_session):
        assert get_match_count(db_session) == 0

    def test_returns_count_after_saves(self, db_session):
        for i in range(5):
            save_match_detail(make_detail(game_id=i), db_session)
        assert get_match_count(db_session) == 5


class TestGetUnscrapedSummaries:
    def test_filters_already_scraped(self, db_session):
        save_match_detail(make_detail(game_id=10), db_session)
        summaries = [
            MatchSummary(
                game_id=10, game_date=date.today(),
                game_name="T1 vs GEN", tournament="LCK",
            ),
            MatchSummary(
                game_id=20, game_date=date.today(),
                game_name="DK vs HLE", tournament="LCK",
            ),
        ]
        result = get_unscraped_summaries(summaries, db_session)
        assert len(result) == 1
        assert result[0].game_id == 20
