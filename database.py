"""Shared SQLAlchemy persistence for local SQLite and hosted PostgreSQL."""

import os
from datetime import datetime, timezone, timedelta
from functools import lru_cache

from sqlalchemy import DateTime, Float, ForeignKey, Integer, JSON, String, Text, create_engine, inspect, text, event, select, delete
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert

from config import DATA_DIR, load_dotenv_file


class Base(DeclarativeBase):
    pass


class UserProfile(Base):
    __tablename__ = "users"

    email: Mapped[str] = mapped_column(String(320), primary_key=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    age: Mapped[int] = mapped_column(Integer, nullable=False)
    gender: Mapped[str] = mapped_column(String(30), nullable=False)
    profession: Mapped[str] = mapped_column(String(50), nullable=False)
    focus_area: Mapped[str] = mapped_column(String(300), nullable=False)
    joined_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    password_hash: Mapped[str | None] = mapped_column(String(512))
    privacy_consent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    privacy_notice_version: Mapped[str | None] = mapped_column(String(20))


class ChatHistory(Base):
    __tablename__ = "chat_histories"

    email: Mapped[str] = mapped_column(ForeignKey("users.email", ondelete="CASCADE"), primary_key=True)
    messages: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class MemoryFact(Base):
    __tablename__ = "memory_facts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    email: Mapped[str] = mapped_column(ForeignKey("users.email", ondelete="CASCADE"), index=True)
    fact: Mapped[str] = mapped_column(String(500), nullable=False)


class MoodLog(Base):
    __tablename__ = "mood_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    email: Mapped[str] = mapped_column(ForeignKey("users.email", ondelete="CASCADE"), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    sentiment_score: Mapped[float] = mapped_column(Float, nullable=False)
    snippet: Mapped[str] = mapped_column(Text, nullable=False)


class ScreeningState(Base):
    __tablename__ = "screening_states"

    email: Mapped[str] = mapped_column(ForeignKey("users.email", ondelete="CASCADE"), primary_key=True)
    state: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class RateLimitBucket(Base):
    __tablename__ = "rate_limit_buckets"

    bucket_key: Mapped[str] = mapped_column(String(128), primary_key=True)
    count: Mapped[int] = mapped_column(Integer, nullable=False)
    window_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


def bump_rate_limit(key, now):
    initialize_database()
    engine = get_engine()
    table = RateLimitBucket.__table__
    values = {"bucket_key": key, "count": 1, "window_start": now}
    if engine.dialect.name == "sqlite":
        statement = sqlite_insert(table).values(**values).on_conflict_do_update(
            index_elements=[table.c.bucket_key], set_={"count": table.c.count + 1})
    elif engine.dialect.name == "postgresql":
        statement = pg_insert(table).values(**values).on_conflict_do_update(
            index_elements=[table.c.bucket_key], set_={"count": table.c.count + 1})
    else:
        raise RuntimeError("Rate limiting requires SQLite or PostgreSQL.")
    with engine.begin() as connection:
        # Periodically remove expired, hashed buckets so the table stays bounded.
        if int(now.timestamp()) % 3600 < 3:
            connection.execute(delete(table).where(table.c.window_start < now - timedelta(days=2)))
        connection.execute(statement)
        return connection.execute(select(table.c.count).where(table.c.bucket_key == key)).scalar_one()


@lru_cache(maxsize=1)
def get_engine():
    load_dotenv_file()
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        database_url = f"sqlite:///{(DATA_DIR / 'uday.db').as_posix()}"
    if database_url.startswith("postgres://"):
        database_url = "postgresql+psycopg://" + database_url[len("postgres://") :]
    elif database_url.startswith("postgresql://"):
        database_url = "postgresql+psycopg://" + database_url[len("postgresql://") :]

    options = {"pool_pre_ping": True}
    if database_url.startswith("sqlite:"):
        options["connect_args"] = {"check_same_thread": False}
    engine = create_engine(database_url, **options)
    if database_url.startswith("sqlite:"):
        @event.listens_for(engine, "connect")
        def enable_sqlite_foreign_keys(connection, _record):
            cursor = connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()
    return engine


@lru_cache(maxsize=1)
def get_session_factory():
    return sessionmaker(bind=get_engine(), expire_on_commit=False)


@lru_cache(maxsize=1)
def initialize_database():
    """Apply idempotent, additive schema upgrades for SQLite and PostgreSQL."""
    engine = get_engine()
    Base.metadata.create_all(engine)
    # create_all does not update existing tables. Preserve old user data while
    # adding consent fields to installations created before this deployment.
    columns = {item["name"] for item in inspect(engine).get_columns("users")}
    with engine.begin() as connection:
        if "privacy_consent_at" not in columns:
            connection.execute(text("ALTER TABLE users ADD COLUMN privacy_consent_at TIMESTAMP NULL"))
        if "privacy_notice_version" not in columns:
            connection.execute(text("ALTER TABLE users ADD COLUMN privacy_notice_version VARCHAR(20) NULL"))
        connection.execute(text("CREATE TABLE IF NOT EXISTS schema_version (version INTEGER PRIMARY KEY)"))
        connection.execute(text("INSERT INTO schema_version(version) VALUES (1) ON CONFLICT DO NOTHING"))


def load_chat_history(email):
    initialize_database()
    with get_session_factory()() as session:
        record = session.get(ChatHistory, email)
        return record.messages if record and isinstance(record.messages, list) else []


def save_chat_history(email, messages):
    initialize_database()
    with get_session_factory()() as session, session.begin():
        record = session.get(ChatHistory, email)
        bounded_messages = messages[-500:]
        if record is None:
            record = ChatHistory(email=email, messages=bounded_messages, updated_at=datetime.now(timezone.utc))
            session.add(record)
        else:
            record.messages = bounded_messages
            record.updated_at = datetime.now(timezone.utc)


def add_mood_log(email, score, snippet):
    initialize_database()
    with get_session_factory()() as session, session.begin():
        session.add(
            MoodLog(
                email=email,
                created_at=datetime.now(timezone.utc),
                sentiment_score=score,
                snippet=snippet,
            )
        )
        # Retain at most one year of heuristic scores for each account.
        session.execute(delete(MoodLog).where(
            MoodLog.email == email.lower(),
            MoodLog.created_at < datetime.now(timezone.utc) - timedelta(days=365),
        ))


def get_screening_state(email):
    initialize_database()
    with get_session_factory()() as session:
        row = session.get(ScreeningState, email.lower())
        return dict(row.state) if row and isinstance(row.state, dict) else {}


def save_screening_state(email, state):
    initialize_database()
    with get_session_factory()() as session, session.begin():
        row = session.get(ScreeningState, email.lower())
        if row is None:
            session.add(ScreeningState(email=email.lower(), state=state, updated_at=datetime.now(timezone.utc)))
        else:
            row.state = state
            row.updated_at = datetime.now(timezone.utc)


def delete_user_data(email):
    initialize_database()
    with get_session_factory()() as session, session.begin():
        user = session.get(UserProfile, email.lower())
        if user:
            session.delete(user)


def get_mood_logs(email):
    initialize_database()
    with get_session_factory()() as session:
        rows = session.scalars(select(MoodLog).where(MoodLog.email == email.lower()).order_by(MoodLog.created_at.desc()).limit(100)).all()
        return [{"created_at": row.created_at.isoformat(), "sentiment_score": row.sentiment_score} for row in rows]


def delete_mood_logs(email):
    initialize_database()
    with get_session_factory()() as session, session.begin():
        session.execute(delete(MoodLog).where(MoodLog.email == email.lower()))
