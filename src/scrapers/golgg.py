"""gol.gg match data scraper.

Homepage URL: https://gol.gg/esports/home/
Match detail URL: https://gol.gg/game/stats/{game_id}/page-game/
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field
from datetime import date
from typing import Optional

import httpx
from bs4 import BeautifulSoup, Tag

logger = logging.getLogger(__name__)

BASE_URL = "https://gol.gg"
HOME_URL = f"{BASE_URL}/esports/home/"
MATCH_DETAIL_URL = f"{BASE_URL}/game/stats/{{game_id}}/page-game/"

DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}

CHAMPION_ID_MAP: dict[int, str] = {}

DRAGON_IMG_MAP = {
    "cloud-dragon": "Cloud Drake",
    "fire-dragon": "Infernal Drake",
    "ocean-dragon": "Ocean Drake",
    "mountain-dragon": "Mountain Drake",
    "chemtech-dragon": "Chemtech Drake",
    "hextech-dragon": "Hextech Drake",
    "elder-dragon": "Elder Drake",
}


def _create_client() -> httpx.Client:
    return httpx.Client(headers=DEFAULT_HEADERS, timeout=30, follow_redirects=True)


# ── Data classes ────────────────────────────────────────────────


@dataclass
class TeamComp:
    top: str = ""
    jungle: str = ""
    mid: str = ""
    bot: str = ""
    support: str = ""


@dataclass
class MatchSummary:
    game_id: int
    game_date: date
    game_name: str
    tournament: str
    blue_comp: TeamComp = field(default_factory=TeamComp)
    red_comp: TeamComp = field(default_factory=TeamComp)

    @property
    def blue_team(self) -> str:
        return self.game_name.split(" vs ")[0].strip()

    @property
    def red_team(self) -> str:
        return self.game_name.split(" vs ")[1].strip()


@dataclass
class PlayerStats:
    summoner_name: str
    champion: str
    kills: int = 0
    deaths: int = 0
    assists: int = 0
    cs: int = 0
    side: str = ""
    role: str = ""

    @property
    def kda(self) -> float:
        if self.deaths == 0:
            return float(self.kills + self.assists)
        return (self.kills + self.assists) / self.deaths


@dataclass
class MatchDetail:
    game_id: int
    game_date: date
    tournament: str = ""
    patch: str = ""
    game_time: str = ""
    blue_team: str = ""
    red_team: str = ""
    winner: str = ""
    blue_kills: int = 0
    red_kills: int = 0
    blue_towers: int = 0
    red_towers: int = 0
    blue_dragons: int = 0
    red_dragons: int = 0
    blue_dragon_types: list[str] = field(default_factory=list)
    red_dragon_types: list[str] = field(default_factory=list)
    blue_barons: int = 0
    red_barons: int = 0
    blue_gold: int = 0
    red_gold: int = 0
    blue_first_blood: bool = False
    red_first_blood: bool = False
    blue_first_tower: bool = False
    red_first_tower: bool = False
    blue_bans: list[str] = field(default_factory=list)
    red_bans: list[str] = field(default_factory=list)
    blue_comp: TeamComp = field(default_factory=TeamComp)
    red_comp: TeamComp = field(default_factory=TeamComp)
    blue_players: list[PlayerStats] = field(default_factory=list)
    red_players: list[PlayerStats] = field(default_factory=list)


# ── Helpers ─────────────────────────────────────────────────────


def _parse_stat_number(text: str) -> int:
    text = text.strip().lower().replace(",", "")
    if text.endswith("k"):
        try:
            return int(float(text[:-1]) * 1000)
        except ValueError:
            return 0
    try:
        return int(text)
    except ValueError:
        return 0


def _set_comp_slot(comp: TeamComp, index: int, name: str) -> None:
    slots = ["top", "jungle", "mid", "bot", "support"]
    if index < len(slots):
        setattr(comp, slots[index], name)


# ── Homepage scraping ───────────────────────────────────────────


def _extract_homepage_json(html: str) -> list[dict]:
    match = re.search(
        r"\$\(['\"]#lastgames_tab['\"]\)\.html\(formatData\((\[[\s\S]*?\])\s*\)\s*\)\s*;",
        html,
    )
    if not match:
        logger.warning("Could not find formatData array in homepage HTML")
        return []
    raw_json = match.group(1)
    raw_json = re.sub(r'(?<=\{|,)\s*(\w+)\s*:', r'"\1":', raw_json)
    return json.loads(raw_json)


def fetch_match_summaries(client: httpx.Client | None = None) -> list[MatchSummary]:
    should_close = client is None
    if client is None:
        client = _create_client()
    try:
        resp = client.get(HOME_URL)
        resp.raise_for_status()
        data = _extract_homepage_json(resp.text)
        summaries = []
        for game in data:
            for key in (
                "bluetop_id", "bluejgl_id", "bluemid_id", "bluebot_id", "bluesup_id",
                "redtop_id", "redjgl_id", "redmid_id", "redbot_id", "redsup_id",
            ):
                if key in game:
                    CHAMPION_ID_MAP[int(game[key])] = game.get(
                        key.replace("_id", "_name"), ""
                    )
            try:
                summaries.append(MatchSummary(
                    game_id=int(game["game_id"]),
                    game_date=date.fromisoformat(game["game_date"]),
                    game_name=game["game_name"],
                    tournament=game["tournament"],
                    blue_comp=TeamComp(
                        top=game.get("bluetop_name", ""),
                        jungle=game.get("bluejgl_name", ""),
                        mid=game.get("bluemid_name", ""),
                        bot=game.get("bluebot_name", ""),
                        support=game.get("bluesup_name", ""),
                    ),
                    red_comp=TeamComp(
                        top=game.get("redtop_name", ""),
                        jungle=game.get("redjgl_name", ""),
                        mid=game.get("redmid_name", ""),
                        bot=game.get("redbot_name", ""),
                        support=game.get("redsup_name", ""),
                    ),
                ))
            except (KeyError, ValueError) as e:
                logger.warning("Skipping malformed game entry: %s — %s", e, game)
                continue
        logger.info("Fetched %d match summaries from homepage", len(summaries))
        return summaries
    finally:
        if should_close:
            client.close()


# ── Match detail scraping ───────────────────────────────────────


def fetch_match_detail(
    game_id: int, client: httpx.Client | None = None
) -> Optional[MatchDetail]:
    should_close = client is None
    if client is None:
        client = _create_client()
    try:
        url = MATCH_DETAIL_URL.format(game_id=game_id)
        resp = client.get(url)
        if resp.status_code == 404:
            logger.warning("Match detail not found for game_id=%d", game_id)
            return None
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "lxml")
        return _parse_match_detail(soup, game_id)
    finally:
        if should_close:
            client.close()


def _parse_match_detail(soup: BeautifulSoup, game_id: int) -> Optional[MatchDetail]:
    # --- Title ---
    title_h1 = soup.find("h1")
    if not title_h1:
        return None
    title_text = title_h1.get_text(strip=True)
    teams = title_text.split(" vs ")
    if len(teams) != 2:
        return None
    blue_team, red_team = teams[0].strip(), teams[1].strip()

    # Resolve full team names from the page (h1 may use abbreviations like "LGG")
    blue_full = blue_team
    red_full = red_team
    for a_tag in soup.find_all("a"):
        txt = a_tag.get_text(strip=True)
        parent_text = a_tag.find_parent().get_text(strip=True) if a_tag.find_parent() else ""
        if "WIN" in parent_text or "LOSS" in parent_text:
            if blue_team in txt or (len(blue_team) <= 3 and txt.startswith(blue_team[0])):
                blue_full = txt
            if red_team in txt or (len(red_team) <= 3 and txt.startswith(red_team[0])):
                red_full = txt

    # --- Tournament ---
    tournament = ""
    tournament_div = title_h1.find_next_sibling("div")
    if tournament_div:
        tourney_text = tournament_div.get_text(" ", strip=True)
        tourney_match = re.match(r"^(.+?)\s*\([A-Z]{2}\)", tourney_text)
        if tourney_match:
            tournament = tourney_match.group(1).strip()

    # --- Patch ---
    patch = ""
    for tag in soup.find_all(["span", "b", "div", "small"]):
        txt = tag.get_text(strip=True)
        if re.match(r"^v\d+\.\d+$", txt):
            patch = txt
            break

    # --- Game time ---
    game_time = ""
    for h in soup.find_all("h1"):
        txt = h.get_text(strip=True)
        if re.match(r"^\d{1,2}:\d{2}$", txt):
            game_time = txt
            break

    # --- Winner ---
    winner = ""
    for a_tag in soup.find_all("a"):
        txt = a_tag.get_text(strip=True)
        parent = a_tag.find_parent()
        parent_text = parent.get_text(strip=True) if parent else ""
        # The page uses full team names (e.g., "L Guide Gaming") while h1 may use "LGG"
        if ("WIN" in parent_text and (txt == blue_full or
                (len(txt) > 2 and txt in blue_full or blue_full in txt))):
            winner = "blue"
            break
        if ("WIN" in parent_text and (txt == red_full or
                (len(txt) > 2 and txt in red_full or red_full in txt))):
            winner = "red"
            break

    # If winner not found by link text, search for any element containing "- WIN" near team name
    if not winner:
        for tag in soup.find_all(string=lambda s: s and "- WIN" in s):
            parent_text = tag.find_parent().get_text(strip=True) if tag.find_parent() else ""
            if blue_full in parent_text or (len(blue_full) <= 3 and any(
                word in parent_text for word in blue_full.split())):
                winner = "blue"
                break
            if red_full in parent_text or (len(red_full) <= 3 and any(
                word in parent_text for word in red_full.split())):
                winner = "red"
                break

    detail = MatchDetail(
        game_id=game_id,
        game_date=date.today(),
        tournament=tournament,
        patch=patch,
        game_time=game_time,
        blue_team=blue_full,
        red_team=red_full,
        winner=winner,
    )

    # --- Score boxes (5 blue, then 5 red) ---
    score_boxes = soup.find_all("span", class_="score-box")
    _parse_score_boxes(score_boxes, detail)

    # --- First Blood / First Tower ---
    _parse_first_objectives(soup, detail)

    # --- Dragon types ---
    _parse_dragon_types(soup, detail)

    # --- Bans & Picks ---
    _parse_bans_picks(soup, detail)

    # --- Player tables ---
    _parse_player_tables(soup, detail)

    return detail


def _parse_score_boxes(score_boxes: list[Tag], detail: MatchDetail) -> None:
    """First 5 boxes = blue stats (kills, towers, dragons, barons, gold).
    Next 5 boxes = red stats."""
    alt_to_attr = {
        "kills": "kills", "towers": "towers", "dragons": "dragons",
        "nashor": "barons", "team gold": "gold",
    }
    for i, box in enumerate(score_boxes):
        img = box.find("img")
        if not img:
            continue
        alt = img.get("alt", "").strip().lower()
        if alt not in alt_to_attr:
            continue
        attr = alt_to_attr[alt]
        # Number is text after removing alt words
        num_text = box.get_text(strip=True)
        for w in alt.split():
            num_text = num_text.replace(w, "", 1)
        num = _parse_stat_number(num_text.strip())
        prefix = "blue_" if i < 5 else "red_"
        setattr(detail, f"{prefix}{attr}", num)


def _parse_first_objectives(soup: BeautifulSoup, detail: MatchDetail) -> None:
    """Detect First Blood / First Tower using team stat panels."""
    for img in soup.find_all("img"):
        alt = img.get("alt", "")
        if alt not in ("First Blood", "First Tower"):
            continue
        # Walk up to find the containing team stat panel
        panel = img
        panel_text = ""
        for _ in range(6):
            panel = panel.find_parent()
            if not panel:
                break
            panel_text = panel.get_text()
            # Check if the panel contains a team name
            if detail.blue_team:
                blue_words = detail.blue_team.split()
                if any(w in panel_text for w in blue_words):
                    if alt == "First Blood":
                        detail.blue_first_blood = True
                    else:
                        detail.blue_first_tower = True
                    break
            if detail.red_team:
                red_words = detail.red_team.split()
                if any(w in panel_text for w in red_words):
                    if alt == "First Blood":
                        detail.red_first_blood = True
                    else:
                        detail.red_first_tower = True
                    break


def _parse_dragon_types(soup: BeautifulSoup, detail: MatchDetail) -> None:
    """Extract dragon types by finding each team's stat panel and counting
    dragon icons within it."""
    # Find the two team stat panels (identified by team name links + WIN/LOSS)
    blue_panel: Tag | None = None
    red_panel: Tag | None = None

    for a_tag in soup.find_all("a"):
        parent = a_tag.find_parent()
        if not parent:
            continue
        parent_text = parent.get_text(strip=True)
        if "WIN" in parent_text:
            txt = a_tag.get_text(strip=True)
            # Find the stat panel — walk up to a row/container div
            panel = parent
            for _ in range(4):
                panel = panel.find_parent()
                if not panel:
                    break
                classes = str(panel.get("class", ""))
                if "row" in classes or "col" in classes:
                    # Found it; determine which team
                    panel_text = panel.get_text()
                    if detail.blue_team and any(
                        w in panel_text for w in detail.blue_team.split()
                    ):
                        blue_panel = panel
                    elif detail.red_team and any(
                        w in panel_text for w in detail.red_team.split()
                    ):
                        red_panel = panel
                    break

    # Fallback: find dragon icons by looking for ic_dragons headers
    if not blue_panel or not red_panel:
        _parse_dragon_types_fallback(soup, detail)
        return

    blue_dragons = _find_dragon_icons(blue_panel)
    red_dragons = _find_dragon_icons(red_panel)

    detail.blue_dragon_types = blue_dragons
    detail.red_dragon_types = red_dragons
    detail.blue_dragons = len(blue_dragons)
    detail.red_dragons = len(red_dragons)


def _find_dragon_icons(panel: Tag) -> list[str]:
    """Find all dragon-type image names within a panel."""
    dragons: list[str] = []
    for img in panel.find_all("img"):
        src = img.get("src", "")
        for filename, dragon_name in DRAGON_IMG_MAP.items():
            if filename in src:
                dragons.append(dragon_name)
                break
    return dragons


def _parse_dragon_types_fallback(soup: BeautifulSoup, detail: MatchDetail) -> None:
    """Fallback: split dragon images by ic_dragons headers."""
    all_imgs: list[tuple[str, Tag]] = []
    for img in soup.find_all("img"):
        src = img.get("src", "")
        for filename, dragon_name in DRAGON_IMG_MAP.items():
            if filename in src:
                all_imgs.append((dragon_name, img))
                break
    if len(all_imgs) < 2:
        return
    mid = len(all_imgs) // 2
    detail.blue_dragon_types = [n for n, _ in all_imgs[:mid]]
    detail.red_dragon_types = [n for n, _ in all_imgs[mid:]]
    detail.blue_dragons = len(detail.blue_dragon_types)
    detail.red_dragons = len(detail.red_dragon_types)


def _parse_bans_picks(soup: BeautifulSoup, detail: MatchDetail) -> None:
    """Extract bans and picks from champion image links.
    Page order: blue bans (5), blue picks (5), red bans (5), red picks (5),
    then player table champ icons (10)."""
    champ_links = soup.find_all("a", href=lambda h: h and "champion-stats" in h)
    champ_links = [a for a in champ_links if a.find("img")]
    names: list[str] = []
    for a in champ_links:
        img = a.find("img")
        name = (img.get("alt", "") or a.get("title", "")).strip()
        if name:
            names.append(name)
    if len(names) < 20:
        return
    detail.blue_bans = names[0:5]
    for i, name in enumerate(names[5:10]):
        _set_comp_slot(detail.blue_comp, i, name)
    detail.red_bans = names[10:15]
    for i, name in enumerate(names[15:20]):
        _set_comp_slot(detail.red_comp, i, name)


def _parse_player_tables(soup: BeautifulSoup, detail: MatchDetail) -> None:
    """Extract player stats from tables 0 (blue) and 6 (red).
    Each player row has 13 cells: cell[0]=champ+name, cell[11]=KDA, cell[12]=CS."""
    tables = soup.find_all("table")
    for t_idx, t in enumerate(tables):
        if t_idx not in (0, 6):
            continue
        side = "blue" if t_idx == 0 else "red"
        rows = t.find_all("tr")
        for row in rows:
            cells = row.find_all("td")
            if len(cells) < 13:
                continue
            links = cells[0].find_all("a")
            if len(links) < 2:
                continue
            champ_img = links[0].find("img")
            champion = champ_img.get("alt", "") if champ_img else ""
            if not champion:
                champion = links[0].get("title", "")
            summoner = links[1].get_text(strip=True)
            kda_text = cells[11].get_text(strip=True)
            kda_match = re.match(r"(\d+)/(\d+)/(\d+)", kda_text)
            if not kda_match:
                continue
            kills = int(kda_match.group(1))
            deaths = int(kda_match.group(2))
            assists = int(kda_match.group(3))
            try:
                cs = int(cells[12].get_text(strip=True))
            except ValueError:
                cs = 0
            current = detail.blue_players if side == "blue" else detail.red_players
            role_order = ["top", "jgl", "mid", "bot", "sup"]
            role = role_order[len(current)] if len(current) < 5 else ""
            player = PlayerStats(
                summoner_name=summoner, champion=champion,
                kills=kills, deaths=deaths, assists=assists, cs=cs,
                side=side, role=role,
            )
            if side == "blue":
                detail.blue_players.append(player)
            else:
                detail.red_players.append(player)
