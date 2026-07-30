"""Demo: simulate HLE vs DK using real data from scraper."""

from src.sim.engine import (
    Champion, GameEvent, MatchConfig, MatchSimulator, Player,
    Role, Side, Team, TeamDraft,
)


def build_lck_teams() -> tuple[Team, Team]:
    """Build HLE and DK teams with ratings derived from scraped data."""

    # ── Hanwha Life Esports ──
    hle = Team(
        name="Hanwha Life Esports", tag="HLE",
        synergy=78, coaching=82,
        players={
            Role.TOP: Player(
                name="Zeus", team="HLE", primary_role=Role.TOP,
                mechanics=94, game_sense=88, consistency=82,
                champion_pool=["KSante", "Ambessa", "Gnar", "Renekton", "Jayce"],
                champion_mastery={"Ambessa": 85, "KSante": 95, "Gnar": 90},
                experience=78, form=-5,
            ),
            Role.JUNGLE: Player(
                name="Kanavi", team="HLE", primary_role=Role.JUNGLE,
                mechanics=88, game_sense=85, consistency=75,
                champion_pool=["Vi", "Lee Sin", "Jarvan IV", "Xin Zhao", "Nocturne"],
                champion_mastery={"Vi": 82, "Lee Sin": 90, "Jarvan IV": 88},
                experience=85, form=-10,
            ),
            Role.MID: Player(
                name="Zeka", team="HLE", primary_role=Role.MID,
                mechanics=92, game_sense=86, consistency=84,
                champion_pool=["Aurora", "Ahri", "Syndra", "Orianna", "Akali"],
                champion_mastery={"Aurora": 80, "Ahri": 88, "Syndra": 85},
                experience=80, form=0,
            ),
            Role.BOT: Player(
                name="Gumayusi", team="HLE", primary_role=Role.BOT,
                mechanics=90, game_sense=84, consistency=86,
                champion_pool=["Ezreal", "Kaisa", "Cassiopeia", "Jhin", "Ashe"],
                champion_mastery={"Cassiopeia": 70, "Ezreal": 92, "Kaisa": 90},
                experience=82, form=-3,
            ),
            Role.SUPPORT: Player(
                name="Delight", team="HLE", primary_role=Role.SUPPORT,
                mechanics=82, game_sense=88, consistency=84,
                champion_pool=["Rell", "Nautilus", "Camille", "Shen", "Bard"],
                champion_mastery={"Camille": 72, "Rell": 88, "Nautilus": 85},
                experience=76, form=-8,
            ),
        },
    )

    # ── Dplus KIA ──
    dk = Team(
        name="Dplus KIA", tag="DK",
        synergy=82, coaching=84,
        players={
            Role.TOP: Player(
                name="Siwoo", team="DK", primary_role=Role.TOP,
                mechanics=85, game_sense=82, consistency=80,
                champion_pool=["Olaf", "KSante", "Gnar", "Renekton", "Ambessa"],
                champion_mastery={"Olaf": 85, "KSante": 88, "Gnar": 84},
                experience=68, form=5,
            ),
            Role.JUNGLE: Player(
                name="Lucid", team="DK", primary_role=Role.JUNGLE,
                mechanics=90, game_sense=86, consistency=80,
                champion_pool=["Xin Zhao", "Vi", "Lee Sin", "Jarvan IV", "Nocturne"],
                champion_mastery={"Xin Zhao": 88, "Vi": 85, "Lee Sin": 90},
                experience=70, form=8,
            ),
            Role.MID: Player(
                name="ShowMaker", team="DK", primary_role=Role.MID,
                mechanics=94, game_sense=94, consistency=88,
                champion_pool=["Orianna", "Syndra", "Azir", "Taliyah", "Ahri"],
                champion_mastery={"Orianna": 95, "Syndra": 92, "Azir": 90},
                experience=94, form=10,
            ),
            Role.BOT: Player(
                name="Smash", team="DK", primary_role=Role.BOT,
                mechanics=88, game_sense=84, consistency=85,
                champion_pool=["Ezreal", "Kaisa", "Jhin", "Ashe", "Ziggs"],
                champion_mastery={"Ezreal": 90, "Kaisa": 88, "Jhin": 85},
                experience=72, form=5,
            ),
            Role.SUPPORT: Player(
                name="Career", team="DK", primary_role=Role.SUPPORT,
                mechanics=80, game_sense=85, consistency=82,
                champion_pool=["Shen", "Rell", "Nautilus", "Bard", "Alistar"],
                champion_mastery={"Shen": 86, "Rell": 84, "Nautilus": 82},
                experience=65, form=3,
            ),
        },
    )

    return hle, dk


def main():
    hle, dk = build_lck_teams()

    # Real drafts from the match
    hle_draft = TeamDraft(
        picks={
            Role.TOP: "Ambessa",
            Role.JUNGLE: "Vi",
            Role.MID: "Aurora",
            Role.BOT: "Cassiopeia",
            Role.SUPPORT: "Camille",
        },
        bans=["Locke", "Jayce", "Bard", "Renekton", "Gnar"],
    )

    dk_draft = TeamDraft(
        picks={
            Role.TOP: "Olaf",
            Role.JUNGLE: "Xin Zhao",
            Role.MID: "Orianna",
            Role.BOT: "Ezreal",
            Role.SUPPORT: "Shen",
        },
        bans=["Nocturne", "Poppy", "Akali", "Ziggs", "Viktor"],
    )

    print("=" * 60)
    print("  RiftManager — HLE vs DK Simulation")
    print("=" * 60)
    print()
    print(f"{'HLE (Blue)':30s} {'DK (Red)'}")
    print(f"{'-'*30} {'-'*30}")
    for role in Role:
        hle_champ = hle_draft.picks.get(role, "?")
        dk_champ = dk_draft.picks.get(role, "?")
        hle_player = hle.players[role]
        dk_player = dk.players[role]
        print(f"{hle_champ:12s} ({hle_player.name:10s} {hle_player.overall:2d})  "
              f"vs  {dk_champ:12s} ({dk_player.name:10s} {dk_player.overall:2d})")

    print()
    print(f"HLE Bans: {', '.join(hle_draft.bans)}")
    print(f"DK Bans:  {', '.join(dk_draft.bans)}")
    print()

    # Build matchup data
    print(f"Team ratings: HLE={hle.overall}  DK={dk.overall}")
    print()

    # Simulate multiple times to show variance
    simulator = MatchSimulator(seed=42)
    results = []
    for _ in range(5):
        result = simulator.simulate_game(hle, dk, hle_draft, dk_draft)
        results.append(result)

    print("--- Simulation Results (5 runs) ---")
    hle_wins = sum(1 for r in results if r.winner == Side.BLUE)
    dk_wins = sum(1 for r in results if r.winner == Side.RED)
    print(f"HLE wins: {hle_wins}/5  |  DK wins: {dk_wins}/5")
    print()

    # Show a single detailed simulation
    result = results[0]
    print(f"=== Detailed Sim (Winner: {result.winner_name}) ===")
    print(f"Duration: {result.duration_minutes} min")
    print(f"HLE: {result.blue_kills} kills, {result.blue_towers} towers, "
          f"{result.blue_dragons} dragons, {result.blue_barons} barons, "
          f"{result.blue_gold:,} gold")
    print(f"DK:  {result.red_kills} kills, {result.red_towers} towers, "
          f"{result.red_dragons} dragons, {result.red_barons} barons, "
          f"{result.red_gold:,} gold")
    print(f"MVP: {result.mvp}")
    print()
    print("Timeline:")
    for event in result.events[:10]:
        side_tag = f"[{event.side.value.upper()}]" if event.side else "     "
        print(f"  {event.minute:2d}min {side_tag} {event.description}")

    print()
    print("--- Actual Result ---")
    print("DK won: 20-8 kills, 9-2 towers, 65.6k-53.9k gold, 30:54 duration")


if __name__ == "__main__":
    main()
