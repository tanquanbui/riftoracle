"""
RiftManager — Matchup database built from scraped pro games.

Reads the matches/picks/bans tables filled by the gol.gg scraper and
computes, per role, how each champion does against each lane opponent,
plus each champion's overall pick/ban presence and win rate.

Win rates are smoothed toward 50% (a few imaginary even games are added)
so a 2-0 record doesn't look like a guaranteed counter.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass, field

from sqlalchemy.orm import Session

from src.pipeline.models import Match
from src.sim.engine import Role

PRIOR_GAMES = 4  # Imaginary 50/50 games added to every record


def smoothed_win_rate(wins: int, games: int, prior: int = PRIOR_GAMES) -> float:
    return (wins + prior / 2) / (games + prior)


@dataclass
class ChampionRecord:
    champion: str
    games: int = 0
    wins: int = 0
    bans: int = 0
    roles: Counter[Role] = field(default_factory=Counter)

    @property
    def win_rate(self) -> float:
        return self.wins / self.games if self.games else 0.0


@dataclass
class MatchupRecord:
    role: Role
    champion: str
    opponent: str
    games: int = 0
    wins: int = 0

    @property
    def win_rate(self) -> float:
        return self.wins / self.games if self.games else 0.0

    @property
    def smoothed(self) -> float:
        return smoothed_win_rate(self.wins, self.games)

    @property
    def advantage(self) -> int:
        """Lane advantage on the engine's -30..+30 scale."""
        return int(max(-30, min(30, (self.smoothed - 0.5) * 60)))


class MatchupDatabase:
    """Champion and lane matchup stats from scraped games."""

    def __init__(self) -> None:
        self.games = 0
        self.champions: dict[str, ChampionRecord] = {}
        self.matchups: dict[tuple[Role, str, str], MatchupRecord] = {}

    @classmethod
    def from_session(
        cls, session: Session,
        tournament: str | None = None, patch: str | None = None,
    ) -> MatchupDatabase:
        """Build from the database. tournament: substring filter (e.g. "LCK");
        patch: prefix filter (e.g. "16.1" matches "v16.1x")."""
        db = cls()
        query = session.query(Match).filter(Match.winner != "")
        if tournament:
            query = query.filter(Match.tournament.contains(tournament))
        for m in query.all():
            if patch and not m.patch.lstrip("v").startswith(patch.lstrip("v")):
                continue
            db.add_match(m)
        return db

    def add_match(self, m: Match) -> None:
        self.games += 1
        winner = m.winner.lower()
        lanes: dict[tuple[str, Role], str] = {}
        for p in m.picks:
            rec = self.champions.setdefault(p.champion, ChampionRecord(p.champion))
            rec.games += 1
            rec.wins += p.side.lower() == winner
            try:
                role = Role(p.role)
            except ValueError:
                continue
            rec.roles[role] += 1
            lanes[(p.side.lower(), role)] = p.champion
        for b in m.bans:
            self.champions.setdefault(b.champion, ChampionRecord(b.champion)).bans += 1

        for role in Role:
            blue, red = lanes.get(("blue", role)), lanes.get(("red", role))
            if not (blue and red):
                continue
            for champ, opp, side in ((blue, red, "blue"), (red, blue, "red")):
                rec = self.matchups.setdefault((role, champ, opp), MatchupRecord(role, champ, opp))
                rec.games += 1
                rec.wins += side == winner

    # ── Queries ──

    def presence(self, champion: str) -> float:
        rec = self.champions.get(champion)
        return (rec.games + rec.bans) / self.games if rec and self.games else 0.0

    def meta_strength(self, champion: str) -> int:
        """0-100 meta rating from presence and smoothed win rate."""
        rec = self.champions.get(champion)
        if not rec:
            return 50
        wr = smoothed_win_rate(rec.wins, rec.games, prior=5)
        return int(max(30, min(80, 45 + self.presence(champion) * 25 + (wr - 0.5) * 60)))

    def counters(self, champion: str, role: Role | None = None, min_games: int = 1) -> list[MatchupRecord]:
        """Every lane opponent of champion, best matchups first."""
        rows = [r for (rl, c, _), r in self.matchups.items()
                if c == champion and (role is None or rl == role) and r.games >= min_games]
        return sorted(rows, key=lambda r: (r.smoothed, r.games), reverse=True)

    def most_favourable(self, role: Role | None = None, min_games: int = 3,
                        limit: int = 20) -> list[MatchupRecord]:
        """The most lopsided matchups (each pair listed once, from the winner's side)."""
        rows = [r for (rl, _, _), r in self.matchups.items()
                if (role is None or rl == role) and r.games >= min_games and r.smoothed > 0.5]
        return sorted(rows, key=lambda r: (r.smoothed, r.games), reverse=True)[:limit]

    def top_champions(self, role: Role | None = None, limit: int = 15) -> list[ChampionRecord]:
        rows = [r for r in self.champions.values()
                if role is None or r.roles.get(role, 0) > 0]
        return sorted(rows, key=lambda r: self.presence(r.champion), reverse=True)[:limit]
