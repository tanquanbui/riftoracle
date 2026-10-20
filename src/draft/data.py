"""
RiftManager — Champion draft data.

A ChampionCatalog holds what the draft needs to know about champions:
which roles they're played in, how strong they are in the current meta,
and lane matchup advantages. It starts from a hand-written baseline and
can be overridden with real numbers computed from scraped pro games.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from src.sim.engine import Champion, Role

# ── Hand-written baseline ──────────────────────────────────────
# meta strength 0-100 (50 = average). Used until real data is loaded.
# Fearless burns up to 10 champions per role in a Bo5, so each role
# needs a deep list.

DEFAULT_ROLE_POOLS: dict[Role, dict[str, int]] = {
    Role.TOP: {
        "KSante": 66, "Gnar": 64, "Renekton": 62, "Ambessa": 65, "Jayce": 60,
        "Ornn": 58, "Rumble": 61, "Aatrox": 57, "Jax": 59, "Camille": 56,
        "Sion": 55, "Gragas": 54, "Olaf": 58, "Gwen": 53, "Kennen": 52,
        "Yone": 54,
    },
    Role.JUNGLE: {
        "Lee Sin": 62, "Vi": 63, "Jarvan IV": 61, "Xin Zhao": 64, "Nocturne": 58,
        "Maokai": 60, "Sejuani": 59, "Skarner": 61, "Wukong": 57, "Pantheon": 56,
        "Viego": 58, "Poppy": 57, "RekSai": 55, "Trundle": 53, "Nidalee": 54,
        "Kindred": 52,
    },
    Role.MID: {
        "Aurora": 63, "Ahri": 62, "Syndra": 61, "Orianna": 64, "Akali": 58,
        "Azir": 63, "Taliyah": 60, "Viktor": 59, "Yone": 57, "Sylas": 58,
        "Galio": 56, "Hwei": 57, "Corki": 58, "Cassiopeia": 55, "Ziggs": 54,
        "Ryze": 56, "Tristana": 53,
    },
    Role.BOT: {
        "Ezreal": 62, "Kaisa": 63, "Jhin": 58, "Ashe": 59, "Ziggs": 57,
        "Varus": 61, "Xayah": 60, "Zeri": 57, "Kalista": 59, "Corki": 58,
        "Smolder": 56, "Caitlyn": 55, "Jinx": 54, "Aphelios": 56, "Sivir": 55,
        "Lucian": 54, "Cassiopeia": 53,
    },
    Role.SUPPORT: {
        "Rell": 63, "Nautilus": 60, "Shen": 59, "Bard": 58, "Alistar": 61,
        "Renata": 57, "Rakan": 60, "Leona": 56, "Braum": 57, "Poppy": 58,
        "Neeko": 56, "Lulu": 55, "Karma": 56, "Thresh": 54, "Pyke": 53,
        "Camille": 55,
    },
}


@dataclass
class ChampionCatalog:
    """Champion roles, meta strength, and matchups for the draft."""

    roles: dict[str, set[Role]] = field(default_factory=dict)
    meta: dict[str, int] = field(default_factory=dict)
    # (champion, opponent) → advantage for champion (-30 to +30)
    matchups: dict[tuple[str, str], int] = field(default_factory=dict)
    source: str = "hand-written defaults"
    games_analysed: int = 0
    _by_role: dict[Role, list[str]] | None = field(default=None, repr=False, compare=False)

    @classmethod
    def default(cls) -> ChampionCatalog:
        catalog = cls()
        for role, pool in DEFAULT_ROLE_POOLS.items():
            for champ, strength in pool.items():
                catalog.roles.setdefault(champ, set()).add(role)
                catalog.meta[champ] = max(catalog.meta.get(champ, 0), strength)
        return catalog

    def champions_for(self, role: Role) -> list[str]:
        if self._by_role is None:
            self._by_role = {r: [c for c, roles in self.roles.items() if r in roles] for r in Role}
        return self._by_role[role]

    def meta_strength(self, champion: str) -> int:
        return self.meta.get(champion, 50)

    def matchup(self, champion: str, opponent: str) -> int | None:
        """Lane advantage of champion vs opponent, or None if unknown."""
        if (champion, opponent) in self.matchups:
            return self.matchups[(champion, opponent)]
        if (opponent, champion) in self.matchups:
            return -self.matchups[(opponent, champion)]
        return None

    def as_engine_champions(self) -> dict[str, Champion]:
        """Convert to the engine's Champion objects."""
        champions: dict[str, Champion] = {}
        for name, roles in self.roles.items():
            champions[name] = Champion(
                name=name,
                primary_role=next(iter(roles)),
                meta_strength=self.meta_strength(name),
            )
        for (a, b), adv in self.matchups.items():
            if a in champions:
                champions[a].matchups[b] = adv
        return champions

    # ── Real data ──

    @classmethod
    def from_database(
        cls, session, min_matchup_games: int = 3,
        tournament: str | None = None, patch: str | None = None,
    ) -> ChampionCatalog:
        """Build a catalog from scraped pro games, layered over the defaults.

        Meta strength comes from presence (pick + ban rate) and a smoothed
        win rate. Matchups come from same-role lane opponents.
        """
        from src.draft.matchups import MatchupDatabase

        db = MatchupDatabase.from_session(session, tournament=tournament, patch=patch)
        return cls.from_matchup_db(db, min_matchup_games)

    @classmethod
    def from_matchup_db(cls, db, min_matchup_games: int = 3) -> ChampionCatalog:
        catalog = cls.default()
        if not db.games:
            return catalog

        for champ, rec in db.champions.items():
            if not rec.games:
                continue
            catalog.meta[champ] = db.meta_strength(champ)
            threshold = max(1, 0.15 * sum(rec.roles.values()))
            roles = {r for r, c in rec.roles.items() if c >= threshold}
            if roles:
                catalog.roles[champ] = roles

        for (_, a, b), rec in db.matchups.items():
            if rec.games >= min_matchup_games and (b, a) not in catalog.matchups:
                catalog.matchups[(a, b)] = rec.advantage

        catalog._by_role = None
        catalog.source = "scraped pro games"
        catalog.games_analysed = db.games
        return catalog
