"""Tests for gol.gg scraper."""

import httpx
import pytest

from src.scrapers.golgg import (
    fetch_match_summaries,
    fetch_match_detail,
    _extract_homepage_json,
    MatchSummary,
    MatchDetail,
)


class TestHomepageParsing:
    """Tests for homepage JSON extraction."""

    def test_extract_homepage_json_real(self):
        """Smoke test: homepage HTML parses without error and returns matches."""
        summaries = fetch_match_summaries()
        assert isinstance(summaries, list)
        assert len(summaries) > 0, "Expected at least one match on homepage"
        for s in summaries:
            assert isinstance(s, MatchSummary)
            assert s.game_id > 0
            assert s.game_date
            assert s.game_name
            assert " vs " in s.game_name
            assert s.tournament

    def test_extract_homepage_json_format(self):
        """Test the regex extraction with a minimal valid payload."""
        html = """<script>
        $('#lastgames_tab').html(formatData([
            {"game_id":"12345","game_date":"2026-07-29","game_name":"T1 vs GEN",
             "tournament":"LCK 2026 Summer",
             "bluetop_name":"KSante","bluetop_id":"162",
             "bluejgl_name":"Lee Sin","bluejgl_id":"47",
             "bluemid_name":"Ahri","bluemid_id":"2",
             "bluebot_name":"Ezreal","bluebot_id":"21",
             "bluesup_name":"Rell","bluesup_id":"153",
             "redtop_name":"Renekton","redtop_id":"72",
             "redjgl_name":"Jarvan IV","redjgl_id":"34",
             "redmid_name":"Orianna","redmid_id":"67",
             "redbot_name":"Kaisa","redbot_id":"140",
             "redsup_name":"Nautilus","redsup_id":"62"}
        ]));
        </script>"""
        data = _extract_homepage_json(html)
        assert len(data) == 1
        assert data[0]["game_id"] == "12345"
        assert data[0]["game_name"] == "T1 vs GEN"


class TestMatchDetail:
    """Tests for match detail page scraping."""

    def test_fetch_real_match_detail(self):
        """Smoke test: scrape a known match and verify structure."""
        # Use the LGG vs Arneb match (game 1 of the series)
        detail = fetch_match_detail(80433)
        assert detail is not None, "Expected to find match 80433"
        assert isinstance(detail, MatchDetail)
        assert detail.game_id == 80433
        assert detail.blue_team
        assert detail.red_team
        assert detail.winner in ("blue", "red", "")
        assert len(detail.blue_players) >= 1
        assert len(detail.red_players) >= 1

        # Verify player data
        for player in detail.blue_players + detail.red_players:
            assert player.summoner_name
            assert player.champion
            assert player.kills >= 0
            assert player.deaths >= 0
            assert player.assists >= 0
            assert player.side in ("blue", "red")

    def test_fetch_nonexistent_match(self):
        """Requesting a nonexistent game ID should return None."""
        detail = fetch_match_detail(99999999)
        assert detail is None
