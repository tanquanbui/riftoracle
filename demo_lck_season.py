"""Demo: simulate a full LCK season with all 10 teams."""

from datetime import date

from demo_hle_dk import build_lck_teams
from src.sim.engine import Player, Role, Team
from src.sim.season import SeasonConfig, SeasonEngine


def build_all_lck_teams() -> list[Team]:
    """Build all 10 LCK teams for a full season simulation."""
    hle, dk = build_lck_teams()

    # T1
    t1 = Team(
        name="T1", tag="T1", synergy=85, coaching=88,
        players={
            Role.TOP: Player("Doran", "T1", Role.TOP, 88, 85, 82, champion_pool=["KSante", "Gnar", "Renekton", "Ambessa", "Jayce"], champion_mastery={"KSante": 92, "Gnar": 88, "Ambessa": 82}, experience=88),
            Role.JUNGLE: Player("Oner", "T1", Role.JUNGLE, 92, 88, 84, champion_pool=["Lee Sin", "Vi", "Jarvan IV", "Xin Zhao", "Nocturne"], champion_mastery={"Lee Sin": 95, "Vi": 88, "Jarvan IV": 85}, experience=85),
            Role.MID: Player("Faker", "T1", Role.MID, 94, 98, 90, champion_pool=["Ahri", "Orianna", "Azir", "Syndra", "Taliyah"], champion_mastery={"Ahri": 96, "Orianna": 94, "Azir": 92}, experience=100, form=3),
            Role.BOT: Player("Gumayusi", "T1", Role.BOT, 90, 84, 86, champion_pool=["Ezreal", "Kaisa", "Jhin", "Ashe", "Cassiopeia"], champion_mastery={"Ezreal": 92, "Kaisa": 90, "Jhin": 85}, experience=82),
            Role.SUPPORT: Player("Keria", "T1", Role.SUPPORT, 94, 95, 88, champion_pool=["Rell", "Nautilus", "Shen", "Bard", "Renata"], champion_mastery={"Rell": 95, "Shen": 92, "Nautilus": 90}, experience=86),
        },
    )

    # Gen.G
    gen = Team(
        name="Gen.G", tag="GEN", synergy=88, coaching=90,
        players={
            Role.TOP: Player("Kiin", "GEN", Role.TOP, 92, 90, 88, champion_pool=["KSante", "Gnar", "Renekton", "Ambessa", "Ornn"], champion_mastery={"KSante": 94, "Gnar": 90, "Ambessa": 85}, experience=92),
            Role.JUNGLE: Player("Canyon", "GEN", Role.JUNGLE, 96, 94, 88, champion_pool=["Lee Sin", "Vi", "Jarvan IV", "Xin Zhao", "Nocturne"], champion_mastery={"Lee Sin": 96, "Vi": 90, "Jarvan IV": 88}, experience=88, form=5),
            Role.MID: Player("Chovy", "GEN", Role.MID, 96, 94, 92, champion_pool=["Ahri", "Orianna", "Syndra", "Azir", "Taliyah"], champion_mastery={"Ahri": 94, "Orianna": 95, "Syndra": 92}, experience=86, form=8),
            Role.BOT: Player("Peyz", "GEN", Role.BOT, 88, 86, 88, champion_pool=["Ezreal", "Kaisa", "Jhin", "Ziggs", "Ashe"], champion_mastery={"Ezreal": 90, "Kaisa": 92, "Jhin": 85}, experience=72, form=2),
            Role.SUPPORT: Player("Lehends", "GEN", Role.SUPPORT, 88, 90, 86, champion_pool=["Rell", "Nautilus", "Shen", "Alistar", "Bard"], champion_mastery={"Rell": 90, "Nautilus": 88, "Alistar": 85}, experience=92, form=0),
        },
    )

    # KT Rolster
    kt = Team(
        name="KT Rolster", tag="KT", synergy=78, coaching=80,
        players={
            Role.TOP: Player("PerfecT", "KT", Role.TOP, 82, 78, 76, champion_pool=["KSante", "Gnar", "Renekton", "Jayce", "Ambessa"], champion_mastery={"KSante": 84, "Gnar": 80, "Renekton": 82}, experience=65),
            Role.JUNGLE: Player("Cuzz", "KT", Role.JUNGLE, 86, 84, 82, champion_pool=["Lee Sin", "Vi", "Jarvan IV", "Xin Zhao", "Nocturne"], champion_mastery={"Lee Sin": 88, "Vi": 85, "Xin Zhao": 84}, experience=85),
            Role.MID: Player("Bdd", "KT", Role.MID, 88, 90, 86, champion_pool=["Ahri", "Orianna", "Syndra", "Azir", "Taliyah"], champion_mastery={"Ahri": 88, "Orianna": 90, "Syndra": 86}, experience=88, form=-2),
            Role.BOT: Player("Deokdam", "KT", Role.BOT, 84, 82, 84, champion_pool=["Ezreal", "Kaisa", "Jhin", "Ziggs", "Ashe"], champion_mastery={"Ezreal": 85, "Kaisa": 86, "Jhin": 84}, experience=80),
            Role.SUPPORT: Player("BeryL", "KT", Role.SUPPORT, 84, 90, 78, champion_pool=["Rell", "Nautilus", "Shen", "Alistar", "Bard"], champion_mastery={"Rell": 84, "Nautilus": 82, "Alistar": 88}, experience=95, form=2),
        },
    )

    # BNK FearX
    bfx = Team(
        name="BNK FearX", tag="BFX", synergy=72, coaching=74,
        players={
            Role.TOP: Player("Clear", "BFX", Role.TOP, 80, 76, 75, champion_pool=["KSante", "Gnar", "Renekton", "Jayce", "Ambessa"], champion_mastery={"KSante": 82, "Gnar": 78, "Renekton": 80}, experience=62),
            Role.JUNGLE: Player("Willer", "BFX", Role.JUNGLE, 82, 78, 76, champion_pool=["Lee Sin", "Vi", "Jarvan IV", "Xin Zhao"], champion_mastery={"Lee Sin": 84, "Vi": 82, "Xin Zhao": 80}, experience=68),
            Role.MID: Player("VicLa", "BFX", Role.MID, 84, 80, 78, champion_pool=["Ahri", "Orianna", "Syndra", "Azir"], champion_mastery={"Ahri": 84, "Orianna": 82, "Syndra": 80}, experience=65, form=-3),
            Role.BOT: Player("Hena", "BFX", Role.BOT, 80, 78, 80, champion_pool=["Ezreal", "Kaisa", "Jhin", "Ziggs"], champion_mastery={"Ezreal": 82, "Kaisa": 80, "Jhin": 78}, experience=70),
            Role.SUPPORT: Player("Execute", "BFX", Role.SUPPORT, 78, 80, 76, champion_pool=["Rell", "Nautilus", "Shen", "Alistar"], champion_mastery={"Rell": 80, "Nautilus": 78, "Alistar": 76}, experience=55),
        },
    )

    # DN SOOPers (formerly DNS)
    dns = Team(
        name="DN SOOPers", tag="DNS", synergy=74, coaching=76,
        players={
            Role.TOP: Player("DuDu", "DNS", Role.TOP, 82, 78, 76, champion_pool=["KSante", "Gnar", "Renekton", "Ornn"], champion_mastery={"KSante": 84, "Gnar": 80, "Ornn": 82}, experience=72),
            Role.JUNGLE: Player("Pyosik", "DNS", Role.JUNGLE, 86, 80, 74, champion_pool=["Lee Sin", "Vi", "Jarvan IV", "Xin Zhao"], champion_mastery={"Lee Sin": 88, "Vi": 82, "Jarvan IV": 84}, experience=82, form=5),
            Role.MID: Player("BuLLDoG", "DNS", Role.MID, 82, 80, 78, champion_pool=["Ahri", "Orianna", "Syndra", "Azir"], champion_mastery={"Ahri": 82, "Orianna": 80, "Syndra": 78}, experience=62),
            Role.BOT: Player("Jiwoo", "DNS", Role.BOT, 80, 78, 80, champion_pool=["Ezreal", "Kaisa", "Jhin", "Ziggs"], champion_mastery={"Ezreal": 82, "Kaisa": 80, "Jhin": 78}, experience=58),
            Role.SUPPORT: Player("Pleata", "DNS", Role.SUPPORT, 76, 80, 78, champion_pool=["Rell", "Nautilus", "Shen"], champion_mastery={"Rell": 78, "Nautilus": 76, "Shen": 80}, experience=52),
        },
    )

    # Nongshim RedForce
    ns = Team(
        name="Nongshim RedForce", tag="NS", synergy=70, coaching=72,
        players={
            Role.TOP: Player("DnDn", "NS", Role.TOP, 78, 75, 74, champion_pool=["KSante", "Gnar", "Renekton"], champion_mastery={"KSante": 80, "Gnar": 76, "Renekton": 78}, experience=60),
            Role.JUNGLE: Player("Sylvie", "NS", Role.JUNGLE, 80, 76, 74, champion_pool=["Lee Sin", "Vi", "Jarvan IV"], champion_mastery={"Lee Sin": 82, "Vi": 80, "Jarvan IV": 78}, experience=55),
            Role.MID: Player("FIESTA", "NS", Role.MID, 80, 78, 76, champion_pool=["Ahri", "Orianna", "Syndra"], champion_mastery={"Ahri": 80, "Orianna": 78, "Syndra": 76}, experience=60),
            Role.BOT: Player("vital", "NS", Role.BOT, 78, 76, 78, champion_pool=["Ezreal", "Kaisa", "Jhin"], champion_mastery={"Ezreal": 80, "Kaisa": 78, "Jhin": 76}, experience=58),
            Role.SUPPORT: Player("Peter", "NS", Role.SUPPORT, 76, 78, 76, champion_pool=["Rell", "Nautilus"], champion_mastery={"Rell": 78, "Nautilus": 76}, experience=55),
        },
    )

    # BRION
    bro = Team(
        name="BRION", tag="BRO", synergy=68, coaching=70,
        players={
            Role.TOP: Player("Morgan", "BRO", Role.TOP, 78, 76, 74, champion_pool=["KSante", "Gnar", "Ornn"], champion_mastery={"KSante": 80, "Gnar": 76, "Ornn": 78}, experience=72),
            Role.JUNGLE: Player("HamBak", "BRO", Role.JUNGLE, 76, 74, 72, champion_pool=["Lee Sin", "Vi", "Jarvan IV"], champion_mastery={"Lee Sin": 78, "Vi": 76, "Jarvan IV": 74}, experience=50),
            Role.MID: Player("Karis", "BRO", Role.MID, 80, 76, 74, champion_pool=["Ahri", "Orianna", "Syndra"], champion_mastery={"Ahri": 80, "Orianna": 78, "Syndra": 76}, experience=62),
            Role.BOT: Player("Envyy", "BRO", Role.BOT, 76, 74, 76, champion_pool=["Ezreal", "Kaisa", "Jhin"], champion_mastery={"Ezreal": 78, "Kaisa": 76, "Jhin": 74}, experience=58),
            Role.SUPPORT: Player("Pollu", "BRO", Role.SUPPORT, 74, 76, 74, champion_pool=["Rell", "Nautilus"], champion_mastery={"Rell": 76, "Nautilus": 74}, experience=48),
        },
    )

    # Kwangdong Freecs
    krx = Team(
        name="Kwangdong Freecs", tag="KRX", synergy=76, coaching=78,
        players={
            Role.TOP: Player("Rooster", "KRX", Role.TOP, 84, 80, 78, champion_pool=["KSante", "Gnar", "Renekton", "Jayce"], champion_mastery={"KSante": 85, "Gnar": 82, "Jayce": 80}, experience=68),
            Role.JUNGLE: Player("YoungJae", "KRX", Role.JUNGLE, 84, 82, 80, champion_pool=["Lee Sin", "Vi", "Jarvan IV", "Xin Zhao"], champion_mastery={"Lee Sin": 85, "Vi": 82, "Jarvan IV": 84}, experience=70),
            Role.MID: Player("BuLLDoG", "KRX", Role.MID, 86, 82, 80, champion_pool=["Ahri", "Orianna", "Syndra", "Taliyah"], champion_mastery={"Ahri": 85, "Orianna": 84, "Taliyah": 82}, experience=68, form=3),
            Role.BOT: Player("Taeyoon", "KRX", Role.BOT, 82, 80, 82, champion_pool=["Ezreal", "Kaisa", "Jhin", "Ziggs"], champion_mastery={"Ezreal": 84, "Kaisa": 82, "Jhin": 80}, experience=65),
            Role.SUPPORT: Player("Andil", "KRX", Role.SUPPORT, 80, 82, 80, champion_pool=["Rell", "Nautilus", "Shen", "Bard"], champion_mastery={"Rell": 82, "Nautilus": 80, "Shen": 80}, experience=62),
        },
    )

    return [gen, t1, dk, hle, kt, krx, dns, bfx, ns, bro]


def main():
    teams = build_all_lck_teams()
    config = SeasonConfig(
        name="LCK 2026 Summer",
        teams=teams,
        start_date=date(2026, 6, 1),
        matches_per_week=10,
        best_of=3,
        playoff_teams=6,
        rounds=2,
    )

    engine = SeasonEngine(config, seed=42)
    print("Generating schedule...")
    engine.generate_schedule()
    print(f"Total matches: {len(engine._schedule)}")
    print()

    print("Simulating full season...")
    engine.simulate_full_season()
    print()

    # Standings
    standings = engine.get_sorted_standings()
    print("=" * 72)
    print("  LCK 2026 SUMMER — FINAL STANDINGS")
    print("=" * 72)
    print(f"{'#':>2} {'Team':22s} {'W':>2} {'L':>2} {'GW':>3} {'GL':>3} {'%':>5}  {'Streak':>6}  Rating")
    print("-" * 72)
    for i, s in enumerate(standings, 1):
        playoff = "★" if i <= 6 else " "
        streak_str = f"W{s.streak}" if s.streak > 0 else f"L{abs(s.streak)}" if s.streak < 0 else "-"
        print(f"{playoff}{i:>1} {s.team.name:22s} {s.series_wins:>2} {s.series_losses:>2} "
              f"{s.game_wins:>3} {s.game_losses:>3} {s.win_rate:>4.0%}  {streak_str:>6}  {s.team.overall:>3}")

    print("-" * 72)
    print("★ = Playoff qualification")
    print()

    # Playoff teams
    playoff_teams = engine.get_playoff_teams()
    print("Playoff teams:", ", ".join(t.tag for t in playoff_teams))
    print()

    # Season stats
    total_games = sum(s.game_wins + s.game_losses for s in standings)
    print(f"Total matches: {len(engine.completed_matches)}")
    print(f"Total games: {total_games}")
    print(f"Average game duration: {30:.0f} min (simulated)")

    # Find best/worst
    best = standings[0]
    worst = standings[-1]
    print(f"\nBest record: {best.team.name} ({best.series_wins}-{best.series_losses})")
    print(f"Worst record: {worst.team.name} ({worst.series_wins}-{worst.series_losses})")


if __name__ == "__main__":
    main()
