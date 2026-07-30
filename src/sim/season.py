"""
RiftManager — Season Engine.

Handles league schedule generation, standings tracking, and
multi-match simulation across a full competitive season.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from datetime import date, timedelta
from enum import Enum
from typing import Optional

from src.sim.engine import (
    GameResult,
    MatchSimulator,
    Player,
    Role,
    Side,
    Team,
    TeamDraft,
)


class MatchStatus(Enum):
    UNSCHEDULED = "unscheduled"
    SCHEDULED = "scheduled"
    COMPLETED = "completed"


@dataclass
class ScheduledMatch:
    """A match on the league schedule."""

    blue_team: Team
    red_team: Team
    match_date: date
    status: MatchStatus = MatchStatus.SCHEDULED
    blue_draft: Optional[TeamDraft] = None
    red_draft: Optional[TeamDraft] = None
    result: Optional[GameResult] = None

    @property
    def winner(self) -> Optional[Team]:
        if not self.result:
            return None
        return self.blue_team if self.result.winner == Side.BLUE else self.red_team

    @property
    def loser(self) -> Optional[Team]:
        if not self.result:
            return None
        return self.red_team if self.result.winner == Side.BLUE else self.blue_team


@dataclass
class TeamStanding:
    """A team's standing in the league."""

    team: Team
    matches_played: int = 0
    series_wins: int = 0
    series_losses: int = 0
    game_wins: int = 0  # Individual game wins (for Bo3/Bo5)
    game_losses: int = 0
    streak: int = 0  # Positive = win streak, negative = loss streak
    points: int = 0  # May differ from wins in some formats

    @property
    def win_rate(self) -> float:
        if self.matches_played == 0:
            return 0.0
        return self.series_wins / self.matches_played

    @property
    def game_win_rate(self) -> float:
        total = self.game_wins + self.game_losses
        if total == 0:
            return 0.0
        return self.game_wins / total


@dataclass
class SeasonConfig:
    """Configuration for a season."""

    name: str = "LCK 2026 Summer"
    teams: list[Team] = field(default_factory=list)
    start_date: date = field(default_factory=lambda: date(2026, 6, 1))
    matches_per_week: int = 10  # LCK: 2 matches/day, 5 days/week
    best_of: int = 3  # Regular season: Bo3
    playoff_teams: int = 6  # Top 6 make playoffs
    rounds: int = 2  # Double round robin


@dataclass
class SeasonState:
    """The current state of a season."""

    config: SeasonConfig
    current_week: int = 1
    current_matchday: int = 1
    schedule: list[ScheduledMatch] = field(default_factory=list)
    standings: dict[str, TeamStanding] = field(default_factory=dict)
    completed_matches: list[ScheduledMatch] = field(default_factory=list)


class SeasonEngine:
    """Manages a full competitive season."""

    def __init__(self, config: SeasonConfig, seed: int | None = None):
        self.config = config
        self.simulator = MatchSimulator(seed=seed)
        self.rng = random.Random(seed)
        self._schedule: list[ScheduledMatch] = []
        self.completed_matches: list[ScheduledMatch] = []

        # Initialize standings
        self.standings: dict[str, TeamStanding] = {
            team.tag: TeamStanding(team=team) for team in config.teams
        }

    def generate_schedule(self) -> list[ScheduledMatch]:
        """Generate a double round-robin schedule."""
        teams = self.config.teams
        n = len(teams)
        schedule: list[ScheduledMatch] = []

        current_date = self.config.start_date
        match_count = 0
        days_per_round = n - 1  # Each round has n-1 match days

        for round_num in range(self.config.rounds):
            # Use circle method for round-robin
            if n % 2 == 1:
                # Odd number of teams — add a bye
                rotated = teams + [None]
            else:
                rotated = list(teams)

            for day in range(len(rotated) - 1):
                for i in range(len(rotated) // 2):
                    team_a = rotated[i]
                    team_b = rotated[-(i + 1)]

                    if team_a is None or team_b is None:
                        continue  # Bye

                    # Alternate blue/red sides
                    if (round_num + day + i) % 2 == 0:
                        blue, red = team_a, team_b
                    else:
                        blue, red = team_b, team_a

                    schedule.append(ScheduledMatch(
                        blue_team=blue,
                        red_team=red,
                        match_date=current_date,
                    ))
                    match_count += 1

                    # Progress date every few matches
                    if match_count % (self.config.matches_per_week // 2) == 0:
                        current_date += timedelta(days=1)

                # Rotate: fix first, shift others
                rotated = [rotated[0]] + [rotated[-1]] + rotated[1:-1]

        self._schedule = schedule
        return schedule

    def simulate_match(self, match: ScheduledMatch) -> ScheduledMatch:
        """Simulate a single match (Bo1/Bo3/Bo5) and return the updated match."""
        best_of = self.config.best_of

        # Auto-generate drafts if not provided
        blue_draft = match.blue_draft or self._auto_draft(match.blue_team, match.red_team)
        red_draft = match.red_draft or self._auto_draft(match.red_team, match.blue_team)
        match.blue_draft = blue_draft
        match.red_draft = red_draft

        blue_game_wins = 0
        red_game_wins = 0
        games_needed = (best_of // 2) + 1
        game_results: list[GameResult] = []

        for _ in range(best_of):
            result = self.simulator.simulate_game(
                match.blue_team, match.red_team, blue_draft, red_draft
            )
            game_results.append(result)

            if result.winner == Side.BLUE:
                blue_game_wins += 1
            else:
                red_game_wins += 1

            if blue_game_wins >= games_needed or red_game_wins >= games_needed:
                break

        # The final result is the match winner
        final = game_results[-1]
        final.blue_kills = sum(g.blue_kills for g in game_results)
        final.red_kills = sum(g.red_kills for g in game_results)
        match.result = final
        match.status = MatchStatus.COMPLETED

        # Update standings
        winner = match.winner
        loser = match.loser
        if winner and loser:
            w_standing = self.standings[winner.tag]
            l_standing = self.standings[loser.tag]

            w_standing.series_wins += 1
            w_standing.matches_played += 1
            w_standing.game_wins += blue_game_wins if winner == match.blue_team else red_game_wins
            w_standing.game_losses += red_game_wins if winner == match.blue_team else blue_game_wins

            l_standing.series_losses += 1
            l_standing.matches_played += 1
            l_standing.game_wins += red_game_wins if winner == match.blue_team else blue_game_wins
            l_standing.game_losses += blue_game_wins if winner == match.blue_team else red_game_wins

            # Streaks
            if w_standing.streak >= 0:
                w_standing.streak += 1
            else:
                w_standing.streak = 1
            if l_standing.streak <= 0:
                l_standing.streak -= 1
            else:
                l_standing.streak = -1

        self.completed_matches.append(match)
        return match

    def simulate_week(self, week_number: int) -> list[ScheduledMatch]:
        """Simulate all matches for a given week."""
        week_matches = [
            m for m in self._schedule
            if m.status == MatchStatus.SCHEDULED
        ][:self.config.matches_per_week]

        results = []
        for match in week_matches:
            result = self.simulate_match(match)
            results.append(result)

        return results

    def simulate_full_season(self) -> SeasonState:
        """Simulate the entire regular season."""
        schedule = self._schedule if hasattr(self, '_schedule') else self.generate_schedule()

        for match in schedule:
            if match.status == MatchStatus.SCHEDULED:
                self.simulate_match(match)

        return SeasonState(
            config=self.config,
            schedule=schedule,
            standings=self.standings,
            completed_matches=self.completed_matches,
        )

    def get_sorted_standings(self) -> list[TeamStanding]:
        """Return standings sorted by wins (then game differential)."""
        return sorted(
            self.standings.values(),
            key=lambda s: (
                s.series_wins,
                s.game_wins - s.game_losses,
                s.game_win_rate,
            ),
            reverse=True,
        )

    def get_playoff_teams(self) -> list[Team]:
        """Return the top N teams that qualify for playoffs."""
        sorted_standings = self.get_sorted_standings()
        return [s.team for s in sorted_standings[:self.config.playoff_teams]]

    def _auto_draft(self, team: Team, opponent: Team) -> TeamDraft:
        """Auto-generate a draft for a team based on player champion pools."""
        draft = TeamDraft()
        for role in Role:
            player = team.players.get(role)
            if player and player.champion_pool:
                # Pick player's best champion from their pool
                best_champ = max(
                    player.champion_pool,
                    key=lambda c: player.champion_proficiency(c)
                )
                draft.picks[role] = best_champ
            elif player:
                draft.picks[role] = "Unknown"

        # Auto-ban opponent's best champions
        bans = []
        for role in Role:
            opp_player = opponent.players.get(role)
            if opp_player and opp_player.champion_pool:
                best = max(opp_player.champion_pool,
                          key=lambda c: opp_player.champion_proficiency(c))
                if best not in bans:
                    bans.append(best)
                if len(bans) >= 5:
                    break
        draft.bans = bans

        return draft
