"""Tests for the fearless draft series simulator."""

import pytest

from demo_lck_season import build_all_lck_teams
from src.draft.data import ChampionCatalog
from src.draft.fearless import (
    DRAFT_ORDER, PICK, FearlessMode, FearlessSeriesSimulator, SeriesConfig, SeriesStart,
)
from src.sim.engine import Role, Side


@pytest.fixture(scope="module")
def teams():
    return {t.tag: t for t in build_all_lck_teams()}


def make_sim(teams, mode=FearlessMode.HARD, best_of=5, seed=1, catalog=None):
    return FearlessSeriesSimulator(
        teams["HLE"], teams["DK"],
        config=SeriesConfig(best_of=best_of, mode=mode), catalog=catalog, seed=seed,
    )


def all_picks(game):
    return list(game.draft.blue.picks.values()) + list(game.draft.red.picks.values())


class TestDraftRules:
    def test_every_game_follows_tournament_order(self, teams):
        series = make_sim(teams).play_series()
        for g in series.games:
            assert [(a.side, a.action) for a in g.draft.actions] == DRAFT_ORDER
            assert set(g.draft.blue.picks) == set(Role)
            assert set(g.draft.red.picks) == set(Role)

    def test_no_champion_used_twice_within_a_game(self, teams):
        for seed in range(10):
            for g in make_sim(teams, seed=seed).play_series().games:
                taken = all_picks(g) + g.draft.blue.bans + g.draft.red.bans
                assert len(taken) == len(set(taken))

    def test_hard_fearless_never_repeats_a_pick(self, teams):
        for seed in range(20):
            series = make_sim(teams, seed=seed).play_series()
            picks = [c for g in series.games for c in all_picks(g)]
            assert len(picks) == len(set(picks))

    def test_soft_fearless_only_locks_own_picks(self, teams):
        for seed in range(20):
            series = make_sim(teams, mode=FearlessMode.SOFT, seed=seed).play_series()
            for tag in ("HLE", "DK"):
                own = []
                for g in series.games:
                    side = g.draft.blue if g.blue_tag == tag else g.draft.red
                    own += side.picks.values()
                assert len(own) == len(set(own))


class TestSeries:
    def test_series_ends_when_a_team_reaches_majority(self, teams):
        for best_of in (1, 3, 5):
            series = make_sim(teams, best_of=best_of).play_series()
            needed = best_of // 2 + 1
            assert max(series.score) == needed
            assert len(series.games) == sum(series.score)

    def test_loser_takes_blue_next_game(self, teams):
        for seed in range(10):
            games = make_sim(teams, seed=seed).play_series().games
            for prev, nxt in zip(games, games[1:]):
                loser = prev.red_tag if prev.winner_tag == prev.blue_tag else prev.blue_tag
                assert nxt.blue_tag == loser

    def test_same_seed_same_series(self, teams):
        a = make_sim(teams, seed=5).play_series()
        b = make_sim(teams, seed=5).play_series()
        assert a.path == b.path
        assert [all_picks(g) for g in a.games] == [all_picks(g) for g in b.games]

    def test_start_mid_series_respects_burned_champions(self, teams):
        start = SeriesStart(wins_a=1, wins_b=1, picked_by_a=["Ahri", "Vi"], picked_by_b=["Orianna"])
        for seed in range(10):
            series = make_sim(teams, seed=seed).play_series(start=start)
            assert series.games[0].number == 3
            for g in series.games:
                assert not {"Ahri", "Vi", "Orianna"} & set(all_picks(g))

    def test_forced_pick_is_used(self, teams):
        series = make_sim(teams).play_series(forced={1: {7: "Orianna"}})
        first_pick = series.games[0].draft.actions[6]
        assert first_pick.action == PICK and first_pick.champion == "Orianna"
        assert first_pick.side == Side.BLUE

    def test_forcing_an_unavailable_champion_fails(self, teams):
        with pytest.raises(ValueError):
            make_sim(teams).play_series(forced={1: {1: "Ahri", 2: "Ahri"}})

    def test_exhausted_role_pools_still_draft(self, teams):
        # Tiny catalog: fearless runs out of role champions by game 2-3
        tiny = ChampionCatalog()
        for i, role in enumerate(Role):
            for j in range(6):
                tiny.roles[f"{role.value}{j}"] = {role}
        for seed in range(5):
            series = make_sim(teams, seed=seed, catalog=tiny).play_series()
            picks = [c for g in series.games for c in all_picks(g)]
            assert len(picks) == len(set(picks))


class TestReport:
    def test_report_probabilities_add_up(self, teams):
        report = make_sim(teams, best_of=3).run(200)
        assert report.n == 200
        assert report.win_probability("HLE") + report.win_probability("DK") == pytest.approx(1.0)
        assert sum(report.scores.values()) == 200
        assert report.games_played[1] == report.games_played[2] == 200
        assert "Series win" in report.format()

    def test_fearless_drains_comfort_over_a_series(self, teams):
        report = make_sim(teams).run(300)
        for tag in ("HLE", "DK"):
            g1 = sum(report.comfort[1][tag]) / len(report.comfort[1][tag])
            g3 = sum(report.comfort[3][tag]) / len(report.comfort[3][tag])
            assert g3 < g1
