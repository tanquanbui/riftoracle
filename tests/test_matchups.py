"""Tests for the matchup database built from stored games."""

from datetime import date

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from src.draft.data import ChampionCatalog
from src.draft.matchups import MatchupDatabase
from src.pipeline.models import Base
from src.pipeline.storage import save_match_detail
from src.scrapers.golgg import MatchDetail, TeamComp
from src.sim.engine import Role


@pytest.fixture
def session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    s = Session(engine)
    yield s
    s.close()


def add_game(session, game_id, blue_mid, red_mid, winner, tournament="LCK 2026 Summer",
             patch="v16.14", blue_bans=("Azir",), red_bans=("Syndra",)):
    save_match_detail(MatchDetail(
        game_id=game_id, game_date=date(2026, 7, 1), tournament=tournament, patch=patch,
        blue_team="T1", red_team="GEN", winner=winner,
        blue_bans=list(blue_bans), red_bans=list(red_bans),
        blue_comp=TeamComp(top="KSante", jungle="Vi", mid=blue_mid, bot="Ezreal", support="Rell"),
        red_comp=TeamComp(top="Gnar", jungle="Lee Sin", mid=red_mid, bot="Kaisa", support="Nautilus"),
    ), session)


@pytest.fixture
def populated(session):
    # Ahri beats Orianna 4 of 5 in mid; blue wins 4 of 6 overall
    add_game(session, 1, "Ahri", "Orianna", "blue")
    add_game(session, 2, "Ahri", "Orianna", "blue")
    add_game(session, 3, "Orianna", "Ahri", "red")
    add_game(session, 4, "Orianna", "Ahri", "red")
    add_game(session, 5, "Ahri", "Orianna", "red")
    add_game(session, 6, "Syndra", "Azir", "blue", tournament="LEC 2026 Summer", patch="v16.13",
             blue_bans=("Jayce",))
    return session


def test_lane_records(populated):
    db = MatchupDatabase.from_session(populated)
    assert db.games == 6
    ahri = db.matchups[(Role.MID, "Ahri", "Orianna")]
    ori = db.matchups[(Role.MID, "Orianna", "Ahri")]
    assert (ahri.games, ahri.wins) == (5, 4)
    assert (ori.games, ori.wins) == (5, 1)
    # Smoothing pulls 80% toward 50%: (4 + 2) / (5 + 4)
    assert ahri.smoothed == pytest.approx(6 / 9)
    assert ahri.advantage > 0 > ori.advantage


def test_champion_presence_and_roles(populated):
    db = MatchupDatabase.from_session(populated)
    assert db.champions["Ahri"].roles[Role.MID] == 5
    # Azir: banned 5 times by blue, picked once
    assert db.champions["Azir"].bans == 5
    assert db.presence("Azir") == pytest.approx(6 / 6)


def test_most_favourable_and_counters(populated):
    db = MatchupDatabase.from_session(populated)
    best = db.most_favourable(role=Role.MID, min_games=3)
    assert (best[0].champion, best[0].opponent) == ("Ahri", "Orianna")
    assert all(r.smoothed > 0.5 for r in best)
    ori = db.counters("Orianna", Role.MID)
    assert ori[0].opponent == "Ahri" and ori[0].wins == 1


def test_filters(populated):
    assert MatchupDatabase.from_session(populated, tournament="LEC").games == 1
    assert MatchupDatabase.from_session(populated, patch="16.14").games == 5


def test_catalog_uses_scraped_matchups(populated):
    catalog = ChampionCatalog.from_database(populated, min_matchup_games=3)
    assert catalog.source == "scraped pro games"
    assert catalog.games_analysed == 6
    assert catalog.matchup("Ahri", "Orianna") > 0
    assert catalog.matchup("Orianna", "Ahri") < 0
    # Fewer than 3 games: not trusted
    assert catalog.matchup("Syndra", "Azir") is None


def test_empty_database_falls_back_to_defaults(session):
    catalog = ChampionCatalog.from_database(session)
    assert catalog.source == "hand-written defaults"
    assert "Ahri" in catalog.champions_for(Role.MID)
