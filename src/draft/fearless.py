"""
RiftManager — Fearless Draft Series Simulator.

Simulates Bo3/Bo5 series under fearless draft rules: every champion
picked in an earlier game of the series is locked for the rest of it
(hard fearless: locked for both teams; soft: only for the team that
played it). Bans reset each game.

Each draft is played out step by step in tournament order by a draft AI
that weighs player comfort, meta strength, lane counters, and fearless
resource management (denying the enemy's comfort picks vs. saving your
own). Drafting is stochastic, so running thousands of series explores
the space of possible drafts and series outcomes.
"""

from __future__ import annotations

import math
import random
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

from src.draft.data import ChampionCatalog
from src.sim.engine import GameResult, MatchSimulator, Player, Role, Side, Team, TeamDraft


class FearlessMode(Enum):
    HARD = "hard"  # Picks lock for both teams (LCK/LPL/LEC format)
    SOFT = "soft"  # Picks lock only for the team that played them
    NONE = "none"  # Standard draft, nothing carries over


class ActionType(Enum):
    BAN = "ban"
    PICK = "pick"


B, R = Side.BLUE, Side.RED
BAN, PICK = ActionType.BAN, ActionType.PICK

# Standard tournament draft order (20 steps)
DRAFT_ORDER: list[tuple[Side, ActionType]] = [
    (B, BAN), (R, BAN), (B, BAN), (R, BAN), (B, BAN), (R, BAN),    # Ban phase 1
    (B, PICK), (R, PICK), (R, PICK), (B, PICK), (B, PICK), (R, PICK),  # Pick phase 1
    (R, BAN), (B, BAN), (R, BAN), (B, BAN),                        # Ban phase 2
    (R, PICK), (B, PICK), (B, PICK), (R, PICK),                    # Pick phase 2
]


@dataclass
class DraftAction:
    step: int  # 1-20
    side: Side
    action: ActionType
    champion: Optional[str]  # None = no ban
    role: Optional[Role] = None


@dataclass
class GameDraft:
    blue: TeamDraft = field(default_factory=TeamDraft)
    red: TeamDraft = field(default_factory=TeamDraft)
    actions: list[DraftAction] = field(default_factory=list)

    def side(self, side: Side) -> TeamDraft:
        return self.blue if side == Side.BLUE else self.red

    def taken(self) -> set[str]:
        """Champions picked or banned so far this game."""
        return (set(self.blue.picks.values()) | set(self.red.picks.values())
                | set(self.blue.bans) | set(self.red.bans))


@dataclass
class DraftStyle:
    """How a team drafts. Tune per team to model different coaching staffs."""

    temperature: float = 2.5   # Higher = more varied (less greedy) drafts
    top_k: int = 4             # Only sample among the k best options
    comfort_weight: float = 1.0
    meta_weight: float = 0.6
    counter_weight: float = 0.8
    denial_weight: float = 0.4        # Fearless: take enemy comfort picks off the table
    conservation_weight: float = 0.3  # Fearless: reluctance to burn own comfort early


# ── Draft AI ────────────────────────────────────────────────────


class DraftAI:
    """Plays out a single game's draft, aware of the fearless series state."""

    def __init__(self, catalog: ChampionCatalog, simulator: MatchSimulator, rng: random.Random):
        self.catalog = catalog
        self.simulator = simulator
        self.rng = rng
        self._prof_cache: dict[tuple[int, str], int] = {}
        self._comfort_cache: dict[int, set[str]] = {}

    def _prof(self, player: Player, champ: str) -> int:
        key = (id(player), champ)
        if key not in self._prof_cache:
            self._prof_cache[key] = player.champion_proficiency(champ)
        return self._prof_cache[key]

    def draft_game(
        self,
        blue: Team, red: Team,
        locked: dict[Side, set[str]],
        future_factor: float,
        styles: dict[Side, DraftStyle],
        forced: dict[int, str] | None = None,
        denies: bool = True,
    ) -> GameDraft:
        """Run all 20 draft steps.

        locked: champions unavailable to each side due to fearless.
        future_factor: 0-1, how much of the series could still follow
            this game (drives denial/conservation).
        forced: step number → champion, to explore a specific scenario.
        """
        draft = GameDraft()
        teams = {Side.BLUE: blue, Side.RED: red}
        forced = forced or {}

        for step, (side, action) in enumerate(DRAFT_ORDER, start=1):
            # Keep champions forced for later steps off the table for the AI
            reserved = {c for st, c in forced.items() if st > step}
            enemy_side = Side.RED if side == Side.BLUE else Side.BLUE
            ctx = _Context(
                team=teams[side], enemy=teams[enemy_side],
                own=draft.side(side), opp=draft.side(enemy_side),
                taken=draft.taken() | reserved, locked=locked[side], enemy_locked=locked[enemy_side],
                future=future_factor, style=styles[side], denies=denies,
            )

            if action == BAN:
                options = self._ban_options(ctx)
            else:
                options = self._pick_options(ctx)

            if step in forced:
                choice = self._forced_choice(forced[step], action, ctx)
            else:
                choice = self._sample(options, ctx.style)

            champ, role = choice if choice else (None, None)
            if action == BAN:
                if champ:
                    draft.side(side).bans.append(champ)
            else:
                draft.side(side).picks[role] = champ
            draft.actions.append(DraftAction(step, side, action, champ, role))

        return draft

    # ── Option scoring ──

    def _pick_options(self, ctx: _Context) -> list[tuple[float, tuple[str, Role]]]:
        options = []
        unavailable = ctx.taken | ctx.locked
        for role in Role:
            if role in ctx.own.picks or role not in ctx.team.players:
                continue
            player = ctx.team.players[role]
            candidates = self._candidates(role, player, unavailable)
            # Best two remaining options per player, to price burning a champion
            own_top = self._top_two(player, candidates)
            enemy_player = ctx.enemy.players.get(role)
            enemy_top = (self._top_two(enemy_player, self._candidates(
                role, enemy_player, ctx.taken | ctx.enemy_locked))
                if enemy_player and ctx.denies else [])
            for champ in candidates:
                value = self._pick_value(ctx, role, champ, own_top, enemy_top)
                options.append((value, (champ, role)))
        return options

    def _pick_value(self, ctx: _Context, role: Role, champ: str,
                    own_top: list[tuple[int, str]], enemy_top: list[tuple[int, str]]) -> float:
        s = ctx.style
        player = ctx.team.players[role]
        prof = self._prof(player, champ)
        value = s.comfort_weight * prof
        value += s.meta_weight * (self.catalog.meta_strength(champ) - 50)

        # Counter (or get countered by) the enemy laner if already picked
        enemy_champ = ctx.opp.picks.get(role)
        if enemy_champ:
            value += s.counter_weight * self._matchup(champ, enemy_champ)

        if ctx.future > 0:
            # Burning a comfort pick costs you in later games...
            own_loss = prof - self._alternative(player, own_top, champ)
            value -= s.conservation_weight * ctx.future * max(0, own_loss)
            # ...but under hard fearless it also takes it from the enemy.
            enemy_player = ctx.enemy.players.get(role)
            if enemy_top and champ in self._comfort(enemy_player):
                enemy_loss = self._prof(enemy_player, champ) - self._alternative(
                    enemy_player, enemy_top, champ)
                value += s.denial_weight * ctx.future * max(0, enemy_loss)
        return value

    def _ban_options(self, ctx: _Context) -> list[tuple[float, tuple[str, Role]]]:
        """Ban whatever the enemy would most want, for their open roles."""
        best: dict[str, tuple[float, Role]] = {}
        unavailable = ctx.taken | ctx.enemy_locked
        for role in Role:
            if role in ctx.opp.picks or role not in ctx.enemy.players:
                continue
            player = ctx.enemy.players[role]
            for champ in self._candidates(role, player, unavailable):
                value = self._prof(player, champ) + 0.6 * (self.catalog.meta_strength(champ) - 50)
                # Bans that answer our own picks: deny their counter to us
                own_champ = ctx.own.picks.get(role)
                if own_champ:
                    value += 0.8 * self._matchup(champ, own_champ)
                if champ not in best or value > best[champ][0]:
                    best[champ] = (value, role)
        return [(v, (c, r)) for c, (v, r) in best.items()]

    def _forced_choice(self, champ: str, action: ActionType, ctx: _Context) -> tuple[str, Role]:
        if champ in ctx.taken or (action == PICK and champ in ctx.locked):
            raise ValueError(f"{champ} is not available at this point of the draft")
        if action == BAN:
            return champ, Role.MID  # Role unused for bans
        open_roles = [r for r in Role if r not in ctx.own.picks and r in ctx.team.players]
        fitting = [r for r in open_roles if r in self.catalog.roles.get(champ, set())
                   or champ in self._comfort(ctx.team.players[r])]
        role = max(fitting or open_roles,
                   key=lambda r: self._prof(ctx.team.players[r], champ))
        return champ, role

    def _sample(self, options, style: DraftStyle):
        if not options:
            return None
        options = sorted(options, key=lambda o: o[0], reverse=True)[:style.top_k]
        top = options[0][0]
        weights = [math.exp((v - top) / max(style.temperature, 1e-6)) for v, _ in options]
        return self.rng.choices([o for _, o in options], weights=weights)[0]

    # ── Helpers ──

    def _comfort(self, player: Player) -> set[str]:
        key = id(player)
        if key not in self._comfort_cache:
            self._comfort_cache[key] = set(player.champion_pool) | set(player.champion_mastery)
        return self._comfort_cache[key]

    def _candidates(self, role: Role, player: Player, unavailable: set[str]) -> list[str]:
        pool = set(self.catalog.champions_for(role)) | self._comfort(player)
        candidates = [c for c in pool if c not in unavailable]
        if not candidates:
            # Role pool exhausted (deep fearless series): play anything left
            candidates = [c for c in self.catalog.roles if c not in unavailable]
        return candidates

    def _top_two(self, player: Player, candidates: list[str]) -> list[tuple[int, str]]:
        return sorted(((self._prof(player, c), c) for c in candidates), reverse=True)[:2]

    def _alternative(self, player: Player, top: list[tuple[int, str]], exclude: str) -> int:
        """Best proficiency left for player if `exclude` is gone."""
        floor = max(0, player.overall - 15)  # Off-pool proficiency
        rest = [p for p, c in top if c != exclude]
        return max(rest[:1] + [floor])

    def _matchup(self, champ: str, enemy: str) -> float:
        known = self.catalog.matchup(champ, enemy)
        return float(known) if known is not None else self.simulator._get_matchup(champ, enemy)


@dataclass
class _Context:
    team: Team
    enemy: Team
    own: TeamDraft
    opp: TeamDraft
    taken: set[str]
    locked: set[str]
    enemy_locked: set[str]
    future: float
    style: DraftStyle
    denies: bool  # Does picking a champion lock it for the enemy too?


# ── Series ──────────────────────────────────────────────────────


@dataclass
class SeriesConfig:
    best_of: int = 5
    mode: FearlessMode = FearlessMode.HARD
    loser_side: Side = Side.BLUE  # Side the loser of the previous game chooses
    reset_final_game: bool = False  # Some formats clear the lock for a deciding game


@dataclass
class SeriesStart:
    """Start a series mid-way, e.g. from a real 1-1 with champions burned."""

    wins_a: int = 0
    wins_b: int = 0
    picked_by_a: list[str] = field(default_factory=list)
    picked_by_b: list[str] = field(default_factory=list)
    a_on_blue: bool = True  # Side for the next game


@dataclass
class GameRecord:
    number: int
    blue_tag: str
    red_tag: str
    draft: GameDraft
    result: GameResult
    winner_tag: str
    locked_before: int  # Champions already unavailable for the game


@dataclass
class SeriesResult:
    games: list[GameRecord]
    winner_tag: str
    score: tuple[int, int]  # (team_a wins, team_b wins)

    @property
    def path(self) -> str:
        return " ".join(g.winner_tag for g in self.games)


class FearlessSeriesSimulator:
    """Simulates fearless draft series between two teams."""

    def __init__(
        self,
        team_a: Team, team_b: Team,
        config: SeriesConfig | None = None,
        catalog: ChampionCatalog | None = None,
        style_a: DraftStyle | None = None,
        style_b: DraftStyle | None = None,
        seed: int | None = None,
    ):
        self.team_a, self.team_b = team_a, team_b
        self.config = config or SeriesConfig()
        self.catalog = catalog or ChampionCatalog.default()
        self.styles = {team_a.tag: style_a or DraftStyle(), team_b.tag: style_b or DraftStyle()}
        self.rng = random.Random(seed)
        self.simulator = MatchSimulator(seed=self.rng.randrange(2**32),
                                        champions=self.catalog.as_engine_champions())
        self.draft_ai = DraftAI(self.catalog, self.simulator, self.rng)

    def play_series(
        self,
        start: SeriesStart | None = None,
        forced: dict[int, dict[int, str]] | None = None,
    ) -> SeriesResult:
        """Play one series. forced: game number → {draft step → champion}."""
        start = start or SeriesStart()
        forced = forced or {}
        a, b = self.team_a, self.team_b
        needed = self.config.best_of // 2 + 1
        wins = {a.tag: start.wins_a, b.tag: start.wins_b}
        picked = {a.tag: set(start.picked_by_a), b.tag: set(start.picked_by_b)}
        blue, red = (a, b) if start.a_on_blue else (b, a)
        games: list[GameRecord] = []
        number = start.wins_a + start.wins_b

        while max(wins.values()) < needed:
            number += 1
            locked = self._locked(blue, red, picked, number)
            future = (self.config.best_of - number) / max(1, self.config.best_of - 1)
            if self.config.mode == FearlessMode.NONE:
                future = 0.0

            draft = self.draft_ai.draft_game(
                blue, red, locked, future,
                {Side.BLUE: self.styles[blue.tag], Side.RED: self.styles[red.tag]},
                forced.get(number),
                denies=self.config.mode == FearlessMode.HARD,
            )
            result = self.simulator.simulate_game(blue, red, draft.blue, draft.red)
            winner, loser = (blue, red) if result.winner == Side.BLUE else (red, blue)
            wins[winner.tag] += 1
            picked[blue.tag] |= set(draft.blue.picks.values())
            picked[red.tag] |= set(draft.red.picks.values())
            games.append(GameRecord(number, blue.tag, red.tag, draft, result, winner.tag,
                                    len(locked[Side.BLUE] | locked[Side.RED])))

            # Loser of the game chooses side for the next one
            blue, red = (loser, winner) if self.config.loser_side == Side.BLUE else (winner, loser)

        series_winner = a.tag if wins[a.tag] >= needed else b.tag
        return SeriesResult(games, series_winner, (wins[a.tag], wins[b.tag]))

    def _locked(self, blue: Team, red: Team, picked: dict[str, set[str]], number: int) -> dict[Side, set[str]]:
        mode = self.config.mode
        if mode == FearlessMode.NONE or (self.config.reset_final_game and number == self.config.best_of):
            return {Side.BLUE: set(), Side.RED: set()}
        if mode == FearlessMode.HARD:
            everything = picked[blue.tag] | picked[red.tag]
            return {Side.BLUE: set(everything), Side.RED: set(everything)}
        return {Side.BLUE: set(picked[blue.tag]), Side.RED: set(picked[red.tag])}

    def run(self, n: int = 1000, start: SeriesStart | None = None,
            forced: dict[int, dict[int, str]] | None = None) -> SeriesReport:
        """Monte Carlo: play n series and aggregate what happened."""
        report = SeriesReport(self.team_a, self.team_b, self.config, self.catalog)
        for _ in range(n):
            report.add(self.play_series(start, forced))
        return report


# ── Aggregated report ───────────────────────────────────────────


class SeriesReport:
    """Aggregates many simulated series into probabilities and trends."""

    def __init__(self, team_a: Team, team_b: Team, config: SeriesConfig, catalog: ChampionCatalog):
        self.team_a, self.team_b = team_a, team_b
        self.config = config
        self.catalog = catalog
        self.n = 0
        self.series_wins: Counter[str] = Counter()
        self.scores: Counter[tuple[int, int]] = Counter()
        self.paths: Counter[str] = Counter()
        self.games_played: Counter[int] = Counter()
        self.game_wins: dict[int, Counter[str]] = defaultdict(Counter)
        self.comfort: dict[int, dict[str, list[float]]] = defaultdict(lambda: defaultdict(list))
        self.picks_by_game: dict[int, Counter[str]] = defaultdict(Counter)
        self.bans: Counter[str] = Counter()
        self.first_picks: Counter[str] = Counter()
        self.player_champs: dict[str, Counter[str]] = defaultdict(Counter)
        self.sample: Optional[SeriesResult] = None

    def add(self, series: SeriesResult) -> None:
        self.n += 1
        self.sample = self.sample or series
        self.series_wins[series.winner_tag] += 1
        self.scores[series.score] += 1
        self.paths[series.path] += 1
        teams = {self.team_a.tag: self.team_a, self.team_b.tag: self.team_b}
        for g in series.games:
            self.games_played[g.number] += 1
            self.game_wins[g.number][g.winner_tag] += 1
            for side, tag in ((g.draft.blue, g.blue_tag), (g.draft.red, g.red_tag)):
                team = teams[tag]
                profs = []
                for role, champ in side.picks.items():
                    player = team.players[role]
                    profs.append(player.champion_proficiency(champ))
                    self.player_champs[player.name][champ] += 1
                    self.picks_by_game[g.number][champ] += 1
                self.comfort[g.number][tag].append(sum(profs) / len(profs))
                self.bans.update(side.bans)
            first = next(a for a in g.draft.actions if a.action == PICK)
            self.first_picks[first.champion] += 1

    def win_probability(self, tag: str) -> float:
        return self.series_wins[tag] / self.n if self.n else 0.0

    def format(self, top: int = 5) -> str:
        a, b = self.team_a.tag, self.team_b.tag
        lines = []
        bar = "=" * 64
        lines += [bar, f"  {a} vs {b} — Bo{self.config.best_of}, "
                       f"{self.config.mode.value} fearless — {self.n:,} simulated series", bar]
        lines.append(f"Champion data: {self.catalog.source}"
                     + (f" ({self.catalog.games_analysed} games)" if self.catalog.games_analysed else ""))
        lines.append("")
        lines.append(f"Series win:  {a} {self.win_probability(a):.1%}   {b} {self.win_probability(b):.1%}")

        lines.append("\nFinal score probabilities:")
        for (wa, wb), c in sorted(self.scores.items(), key=lambda kv: -kv[1]):
            lines.append(f"  {a} {wa}-{wb} {b}   {c / self.n:6.1%}")

        lines.append(f"\nMost likely series paths (game winners in order):")
        for path, c in self.paths.most_common(top):
            lines.append(f"  {path:24s} {c / self.n:6.1%}")

        lines.append("\nGame by game — win rate and average comfort (player proficiency on picks):")
        lines.append(f"  {'Game':<5} {'Played':>7}  {a + ' win':>8} {b + ' win':>8}  "
                     f"{a + ' comfort':>11} {b + ' comfort':>11}")
        for num in sorted(self.games_played):
            played = self.games_played[num]
            ca = self.comfort[num][a]
            cb = self.comfort[num][b]
            lines.append(
                f"  G{num:<4} {played / self.n:>7.0%}  {self.game_wins[num][a] / played:>8.0%} "
                f"{self.game_wins[num][b] / played:>8.0%}  "
                f"{sum(ca) / len(ca):>11.1f} {sum(cb) / len(cb):>11.1f}")

        lines.append("\nMost picked champions per game:")
        for num in sorted(self.picks_by_game):
            played = self.games_played[num]
            common = ", ".join(f"{c} {k / played:.0%}" for c, k in self.picks_by_game[num].most_common(top))
            lines.append(f"  G{num}: {common}")

        total_games = sum(self.games_played.values())
        lines.append("\nMost banned: " + ", ".join(
            f"{c} {k / total_games:.0%}" for c, k in self.bans.most_common(top)))
        lines.append("First picks: " + ", ".join(
            f"{c} {k / total_games:.0%}" for c, k in self.first_picks.most_common(top)))

        lines.append("\nWhat each player ends up playing (share of their games):")
        for team in (self.team_a, self.team_b):
            for role in Role:
                player = team.players.get(role)
                if not player:
                    continue
                counts = self.player_champs[player.name]
                total = sum(counts.values()) or 1
                champs = ", ".join(f"{c} {k / total:.0%}" for c, k in counts.most_common(4))
                lines.append(f"  {team.tag:<4} {role.value:<4} {player.name:<10} {champs}")
        return "\n".join(lines)


def format_series(series: SeriesResult) -> str:
    """Pretty-print one series with full draft order per game."""
    lines = []
    for g in series.games:
        lines.append(f"\n── Game {g.number}: {g.blue_tag} (blue) vs {g.red_tag} (red)"
                     f"  — {g.locked_before} champions locked by fearless")
        for act in g.draft.actions:
            tag = g.blue_tag if act.side == Side.BLUE else g.red_tag
            what = act.champion or "(no ban)"
            role = f" [{act.role.value}]" if act.action == PICK and act.role else ""
            lines.append(f"   {act.step:>2}. {tag:<4} {act.action.value:<4} {what}{role}")
        r = g.result
        lines.append(f"   → {g.winner_tag} wins in {r.duration_minutes} min "
                     f"({r.blue_kills}-{r.red_kills} kills), MVP {r.mvp}")
    a_wins, b_wins = series.score
    lines.append(f"\nSeries: {series.winner_tag} wins {max(a_wins, b_wins)}-{min(a_wins, b_wins)}")
    return "\n".join(lines)
