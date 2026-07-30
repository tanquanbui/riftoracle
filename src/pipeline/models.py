"""SQLAlchemy models for RiftOracle match data."""

from datetime import date, datetime
from typing import Optional

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    create_engine,
)
from sqlalchemy.orm import (
    DeclarativeBase,
    Mapped,
    Session,
    mapped_column,
    relationship,
    sessionmaker,
)

DATABASE_URL = "sqlite:///data/riftoracle.db"


class Base(DeclarativeBase):
    pass


def get_engine(db_url: str = DATABASE_URL):
    return create_engine(db_url, echo=False)


def get_session(engine=None) -> Session:
    if engine is None:
        engine = get_engine()
    return Session(engine)


def init_db(db_url: str = DATABASE_URL) -> None:
    """Create all tables if they don't exist."""
    engine = get_engine(db_url)
    Base.metadata.create_all(engine)


# ── Models ──────────────────────────────────────────────────────


class Match(Base):
    """A single professional LoL match."""

    __tablename__ = "matches"

    id: Mapped[int] = mapped_column(primary_key=True)
    game_id: Mapped[int] = mapped_column(Integer, unique=True, index=True)
    game_date: Mapped[date] = mapped_column(Date, index=True)
    tournament: Mapped[str] = mapped_column(String(256), default="")
    patch: Mapped[str] = mapped_column(String(16), default="")
    game_time: Mapped[str] = mapped_column(String(16), default="")
    game_name: Mapped[Optional[str]] = mapped_column(String(128))
    blue_team: Mapped[str] = mapped_column(String(128), index=True)
    red_team: Mapped[str] = mapped_column(String(128), index=True)
    winner: Mapped[str] = mapped_column(String(8), default="")

    # Objectives
    blue_kills: Mapped[int] = mapped_column(Integer, default=0)
    red_kills: Mapped[int] = mapped_column(Integer, default=0)
    blue_towers: Mapped[int] = mapped_column(Integer, default=0)
    red_towers: Mapped[int] = mapped_column(Integer, default=0)
    blue_dragons: Mapped[int] = mapped_column(Integer, default=0)
    red_dragons: Mapped[int] = mapped_column(Integer, default=0)
    blue_barons: Mapped[int] = mapped_column(Integer, default=0)
    red_barons: Mapped[int] = mapped_column(Integer, default=0)
    blue_gold: Mapped[int] = mapped_column(Integer, default=0)
    red_gold: Mapped[int] = mapped_column(Integer, default=0)
    blue_first_blood: Mapped[bool] = mapped_column(Boolean, default=False)
    red_first_blood: Mapped[bool] = mapped_column(Boolean, default=False)
    blue_first_tower: Mapped[bool] = mapped_column(Boolean, default=False)
    red_first_tower: Mapped[bool] = mapped_column(Boolean, default=False)

    # Dragon types stored as comma-separated strings
    blue_dragon_types: Mapped[Optional[str]] = mapped_column(Text)
    red_dragon_types: Mapped[Optional[str]] = mapped_column(Text)

    # Relationships
    bans: Mapped[list["Ban"]] = relationship(back_populates="match", cascade="all, delete-orphan")
    picks: Mapped[list["Pick"]] = relationship(back_populates="match", cascade="all, delete-orphan")
    player_stats: Mapped[list["PlayerStat"]] = relationship(back_populates="match", cascade="all, delete-orphan")

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    def __repr__(self) -> str:
        return f"<Match {self.game_id}: {self.blue_team} vs {self.red_team}>"


class Ban(Base):
    """A champion ban in a match."""

    __tablename__ = "bans"

    id: Mapped[int] = mapped_column(primary_key=True)
    match_id: Mapped[int] = mapped_column(ForeignKey("matches.id"), index=True)
    champion: Mapped[str] = mapped_column(String(64))
    side: Mapped[str] = mapped_column(String(8))  # "blue" or "red"
    slot: Mapped[int] = mapped_column(Integer)  # 0-4

    match: Mapped["Match"] = relationship(back_populates="bans")

    __table_args__ = (UniqueConstraint("match_id", "side", "slot"),)

    def __repr__(self) -> str:
        return f"<Ban {self.side}[{self.slot}]: {self.champion}>"


class Pick(Base):
    """A champion pick in a match."""

    __tablename__ = "picks"

    id: Mapped[int] = mapped_column(primary_key=True)
    match_id: Mapped[int] = mapped_column(ForeignKey("matches.id"), index=True)
    champion: Mapped[str] = mapped_column(String(64))
    side: Mapped[str] = mapped_column(String(8))
    role: Mapped[str] = mapped_column(String(16))  # top, jgl, mid, bot, sup

    match: Mapped["Match"] = relationship(back_populates="picks")

    __table_args__ = (UniqueConstraint("match_id", "side", "role"),)

    def __repr__(self) -> str:
        return f"<Pick {self.side} {self.role}: {self.champion}>"


class PlayerStat(Base):
    """A single player's stats for a match."""

    __tablename__ = "player_stats"

    id: Mapped[int] = mapped_column(primary_key=True)
    match_id: Mapped[int] = mapped_column(ForeignKey("matches.id"), index=True)
    summoner_name: Mapped[str] = mapped_column(String(128), index=True)
    champion: Mapped[str] = mapped_column(String(64))
    side: Mapped[str] = mapped_column(String(8))
    role: Mapped[str] = mapped_column(String(16))
    kills: Mapped[int] = mapped_column(Integer, default=0)
    deaths: Mapped[int] = mapped_column(Integer, default=0)
    assists: Mapped[int] = mapped_column(Integer, default=0)
    cs: Mapped[int] = mapped_column(Integer, default=0)
    kda: Mapped[float] = mapped_column(Float, default=0.0)

    match: Mapped["Match"] = relationship(back_populates="player_stats")

    __table_args__ = (UniqueConstraint("match_id", "summoner_name"),)

    def __repr__(self) -> str:
        return f"<PlayerStat {self.summoner_name} ({self.champion}): {self.kills}/{self.deaths}/{self.assists}>"


class ScrapeLog(Base):
    """Track what we've scraped and when."""

    __tablename__ = "scrape_logs"

    id: Mapped[int] = mapped_column(primary_key=True)
    game_id: Mapped[int] = mapped_column(Integer, unique=True, index=True)
    scraped_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    success: Mapped[bool] = mapped_column(Boolean, default=True)
    error: Mapped[Optional[str]] = mapped_column(Text)

    def __repr__(self) -> str:
        return f"<ScrapeLog {self.game_id}: {'✓' if self.success else '✗'}>"
