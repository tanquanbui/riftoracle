"""
RiftManager — Match Simulation Engine.

Simulates a League of Legends professional match given two teams,
their champion picks/bans, and player ratings derived from real data.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class Role(Enum):
    TOP = "top"
    JUNGLE = "jgl"
    MID = "mid"
    BOT = "bot"
    SUPPORT = "sup"


class Side(Enum):
    BLUE = "blue"
    RED = "red"


# ── Core data structures ───────────────────────────────────────


@dataclass
class Player:
    """A professional player with ratings."""

    name: str
    team: str = ""
    primary_role: Role = Role.MID
    # Core ratings (0-100 scale, ~85 = elite pro)
    mechanics: int = 70
    game_sense: int = 70
    consistency: int = 70
    champion_pool: list[str] = field(default_factory=list)
    # Champion mastery: champ_name → proficiency (0-100)
    champion_mastery: dict[str, int] = field(default_factory=dict)
    # Form modifier (-20 to +20)
    form: int = 0
    # Experience / clutch factor
    experience: int = 50

    @property
    def overall(self) -> int:
        """Overall rating out of 100."""
        base = (self.mechanics * 0.35 + self.game_sense * 0.35 +
                self.consistency * 0.20 + self.experience * 0.10)
        return max(0, min(100, int(base + self.form)))

    def champion_proficiency(self, champion: str) -> int:
        """How well this player performs on a given champion (0-100)."""
        if champion in self.champion_mastery:
            return self.champion_mastery[champion]
        # Default: slight penalty for off-meta picks
        return max(0, self.overall - 15)


@dataclass
class Team:
    """A team with five players and management attributes."""

    name: str
    tag: str = ""
    players: dict[Role, Player] = field(default_factory=dict)
    # Team-level attributes
    synergy: int = 70  # 0-100
    coaching: int = 70  # Affects draft quality and adaptation

    @property
    def overall(self) -> int:
        if not self.players:
            return 50
        player_avg = sum(p.overall for p in self.players.values()) / len(self.players)
        return int(player_avg * 0.7 + self.synergy * 0.2 + self.coaching * 0.1)


@dataclass
class Champion:
    """Champion data with meta strength."""

    name: str
    primary_role: Role
    # Base strength in current meta (0-100)
    meta_strength: int = 50
    # Matchup modifiers: opposing champion → advantage (-30 to +30)
    matchups: dict[str, int] = field(default_factory=dict)
    # Synergy with allies
    synergies: dict[str, int] = field(default_factory=dict)

    def matchup_advantage(self, opponent: str) -> int:
        """How favorable this champion is vs opponent (-30 to +30)."""
        return self.matchups.get(opponent, 0)


@dataclass
class TeamDraft:
    """A team's draft for a match."""

    picks: dict[Role, str] = field(default_factory=dict)
    bans: list[str] = field(default_factory=list)


@dataclass
class MatchConfig:
    """Configuration for a match simulation."""

    blue_team: Team
    red_team: Team
    blue_draft: TeamDraft
    red_draft: TeamDraft
    patch: str = "16.14"
    best_of: int = 1  # 1, 3, or 5


# ── Match state ─────────────────────────────────────────────────


@dataclass
class GameEvent:
    """An event that occurs during a simulated game."""

    minute: int
    description: str
    side: Optional[Side] = None
    gold_swing: int = 0


@dataclass
class GameResult:
    """The result of a simulated game."""

    winner: Side
    duration_minutes: int
    blue_kills: int
    red_kills: int
    blue_gold: int
    red_gold: int
    blue_towers: int
    red_towers: int
    blue_dragons: int
    red_dragons: int
    blue_barons: int
    red_barons: int
    events: list[GameEvent] = field(default_factory=list)
    mvp: str = ""  # Player name

    @property
    def winner_name(self) -> str:
        return "Blue" if self.winner == Side.BLUE else "Red"


# ── Simulation Engine ───────────────────────────────────────────


class MatchSimulator:
    """Simulates a League of Legends match."""

    # Constants
    BASE_GAME_DURATION = 30  # minutes
    DURATION_VARIANCE = 12   # ± minutes

    def __init__(self, seed: int | None = None, champions: dict[str, Champion] | None = None):
        self.rng = random.Random(seed)
        # Optional champion data (meta strength, matchups). Without it the
        # engine falls back to the built-in counter list and ignores meta.
        self.champions = champions or {}

    def simulate_game(
        self, blue: Team, red: Team, blue_draft: TeamDraft, red_draft: TeamDraft
    ) -> GameResult:
        """Simulate a single game and return the result."""

        # ── Calculate team strengths ──
        blue_power = self._calculate_team_power(blue, blue_draft, red_draft, Side.BLUE)
        red_power = self._calculate_team_power(red, red_draft, blue_draft, Side.RED)

        # Add randomness (upset potential)
        blue_power += self.rng.gauss(0, 8)
        red_power += self.rng.gauss(0, 8)

        # ── Determine winner ──
        power_diff = blue_power - red_power
        # Convert power diff to win probability using sigmoid
        win_prob_blue = 1.0 / (1.0 + pow(10, -power_diff / 25))

        blue_wins = self.rng.random() < win_prob_blue
        winner = Side.BLUE if blue_wins else Side.RED

        # ── Generate game stats ──
        dominance = abs(power_diff) / 50  # How one-sided (0-1)
        duration = int(self.rng.gauss(
            self.BASE_GAME_DURATION - dominance * 10,
            self.DURATION_VARIANCE * (1 - dominance * 0.5)
        ))
        duration = max(18, min(55, duration))

        # Winner's stats scale with dominance
        loser = red if blue_wins else blue
        winner_team = blue if blue_wins else red

        total_kills = int(self.rng.gauss(22 + dominance * 10, 6))
        total_kills = max(8, total_kills)

        winner_kill_pct = 0.52 + dominance * 0.18  # 52-70% of kills
        w_kills = int(total_kills * winner_kill_pct)
        l_kills = total_kills - w_kills

        w_towers = int(7 + dominance * 4)
        l_towers = int(3 - dominance * 3)
        w_towers = min(11, max(2, w_towers))
        l_towers = max(0, min(9, l_towers))

        w_dragons = int(2 + dominance * 1.5)
        l_dragons = int(2 - dominance * 1.5)
        w_dragons = max(1, min(4, w_dragons))
        l_dragons = max(0, min(3, l_dragons))

        w_barons = 1 if dominance > 0.3 or self.rng.random() < 0.6 else 0
        l_barons = 1 if dominance < 0.15 and self.rng.random() < 0.2 else 0

        # Gold
        base_gold = 50000
        gold_diff = int(dominance * 20000 + self.rng.gauss(0, 3000))
        w_gold = base_gold + gold_diff
        l_gold = base_gold - gold_diff

        # ── Generate events ──
        events = self._generate_events(
            blue, red, winner, duration, dominance, w_kills, l_kills
        )

        # ── Determine MVP ──
        mvp = self._pick_mvp(winner_team, blue_draft if blue_wins else red_draft)

        if blue_wins:
            return GameResult(
                winner=Side.BLUE,
                duration_minutes=duration,
                blue_kills=w_kills, red_kills=l_kills,
                blue_gold=w_gold, red_gold=l_gold,
                blue_towers=w_towers, red_towers=l_towers,
                blue_dragons=w_dragons, red_dragons=l_dragons,
                blue_barons=w_barons, red_barons=l_barons,
                events=events, mvp=mvp,
            )
        else:
            return GameResult(
                winner=Side.RED,
                duration_minutes=duration,
                blue_kills=l_kills, red_kills=w_kills,
                blue_gold=l_gold, red_gold=w_gold,
                blue_towers=l_towers, red_towers=w_towers,
                blue_dragons=l_dragons, red_dragons=w_dragons,
                blue_barons=l_barons, red_barons=w_barons,
                events=events, mvp=mvp,
            )

    def _calculate_team_power(
        self, team: Team, draft: TeamDraft, enemy_draft: TeamDraft, side: Side
    ) -> float:
        """Calculate a team's power rating (0-100) including draft effects."""
        power = 0.0

        for role in Role:
            player = team.players.get(role)
            if not player:
                continue

            champion = draft.picks.get(role, "")
            enemy_champ = enemy_draft.picks.get(role, "")

            # Player skill on this champion
            champ_prof = player.champion_proficiency(champion)
            player_power = player.overall * 0.4 + champ_prof * 0.6

            # Champion strength in the current meta
            if champion in self.champions:
                player_power += (self.champions[champion].meta_strength - 50) * 0.15

            # Champion matchup advantage
            matchup_bonus = 0
            if champion and enemy_champ:
                # Check if this player's champ counters the enemy's
                matchup_bonus += self._get_matchup(champion, enemy_champ) * 0.3

            # Role-specific weighting (mid/jgl have more carry potential)
            role_weight = {
                Role.TOP: 0.18, Role.JUNGLE: 0.22,
                Role.MID: 0.24, Role.BOT: 0.22, Role.SUPPORT: 0.14,
            }

            power += (player_power + matchup_bonus) * role_weight[role]

        # Team synergy and side advantage
        power += team.synergy * 0.1
        power += team.coaching * 0.05

        # Blue side advantage (first pick, map asymmetry)
        if side == Side.BLUE:
            power += 1.5

        return power

    def _get_matchup(self, champ: str, enemy: str) -> float:
        """Get matchup advantage of champ vs enemy (-30 to +30).
        
        Uses known counter relationships. In production, this would
        come from real win rate data."""
        if champ in self.champions and enemy in self.champions[champ].matchups:
            return float(self.champions[champ].matchups[enemy])
        if enemy in self.champions and champ in self.champions[enemy].matchups:
            return -float(self.champions[enemy].matchups[champ])

        # Simple counters (can be expanded with real data)
        counters: dict[str, list[str]] = {
            "KSante": ["Jayce", "Gnar"],
            "Renekton": ["KSante", "Ambessa"],
            "Lee Sin": ["Xin Zhao"],
            "Vi": ["Lee Sin", "Jarvan IV"],
            "Ahri": ["Syndra", "Orianna"],
            "Orianna": ["Ahri"],
            "Syndra": ["Orianna", "Taliyah"],
            "Ezreal": ["Kaisa"],
            "Kaisa": ["Ezreal", "Cassiopeia"],
            "Cassiopeia": ["Kaisa"],
            "Rell": ["Nautilus"],
            "Nautilus": ["Rell", "Shen"],
            "Shen": ["Rell", "Camille"],
            "Ambessa": ["Renekton"],
            "Olaf": ["Ambessa"],
            "Xin Zhao": ["Vi"],
            "Aurora": ["Orianna"],
        }
        if champ in counters and enemy in counters[champ]:
            return 12.0
        if enemy in counters and champ in counters[enemy]:
            return -12.0
        return 0.0

    def _generate_events(
        self, blue: Team, red: Team, winner: Side,
        duration: int, dominance: float,
        w_kills: int, l_kills: int,
    ) -> list[GameEvent]:
        """Generate narrative events for the game."""
        events: list[GameEvent] = []
        winner_team = blue if winner == Side.BLUE else red
        loser_team = red if winner == Side.BLUE else blue

        # First Blood
        fb_minute = self.rng.randint(2, 8)
        fb_side = winner if self.rng.random() < 0.55 else (Side.RED if winner == Side.BLUE else Side.BLUE)
        events.append(GameEvent(fb_minute, "First Blood!", fb_side))

        # Early game events
        for m in [5, 10, 15]:
            if m < duration:
                gold_lead = int(abs(dominance * m * 300 + self.rng.gauss(0, 500)))
                leader = winner.name if self.rng.random() < (0.5 + dominance * 0.3) else "Even"
                if leader != "Even":
                    events.append(GameEvent(
                        m, f"{gold_lead} gold lead for {winner_team.name}",
                        winner, gold_lead
                    ))

        # Dragon takes
        for m in [8, 16, 24, 32]:
            if m < duration and self.rng.random() < 0.7:
                dragon_side = winner if self.rng.random() < 0.5 + dominance * 0.3 else (
                    Side.RED if winner == Side.BLUE else Side.BLUE
                )
                dragons = ["Cloud", "Ocean", "Infernal", "Mountain", "Chemtech", "Hextech"]
                dragon = self.rng.choice(dragons)
                events.append(GameEvent(m, f"{dragon} Drake secured!", dragon_side))

        # Baron takes
        for m in [24, 30, 36]:
            if m < duration and self.rng.random() < 0.5:
                events.append(GameEvent(m, "Baron Nashor slain!", winner))

        # Game-ending event
        events.append(GameEvent(
            duration,
            f"{winner_team.name} wins! {winner_team.name} destroy the Nexus after {duration} minutes."
        ))

        return sorted(events, key=lambda e: e.minute)

    def _pick_mvp(self, team: Team, draft: TeamDraft) -> str:
        """Pick an MVP from the winning team."""
        # Weight mid and jungle higher (carry roles)
        weights = {
            Role.TOP: 1.0, Role.JUNGLE: 1.4,
            Role.MID: 1.5, Role.BOT: 1.3, Role.SUPPORT: 0.8,
        }
        candidates = []
        for role, player in team.players.items():
            if role in draft.picks and player:
                candidates.append((player, weights.get(role, 1.0)))

        if not candidates:
            return "Unknown"

        # Weighted random selection
        total_weight = sum(w for _, w in candidates)
        r = self.rng.uniform(0, total_weight)
        cumulative = 0
        for player, weight in candidates:
            cumulative += weight
            if r <= cumulative:
                return player.name

        return candidates[0][0].name
