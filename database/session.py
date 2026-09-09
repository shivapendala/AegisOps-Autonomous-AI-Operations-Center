"""
SQLAlchemy Database Engine and Session Configuration.
Supports PostgreSQL as primary production datastore, with automatic
SQLite fallback for isolated unit testing and zero-friction local development.
"""

import logging
import os
from typing import Generator
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker, Session

logger = logging.getLogger("aegisops.database.session")

Base = declarative_base()

# Retrieve database connection string from environment
PRIMARY_DB_URL = os.getenv(
    "DATABASE_URL_SYNC",
    os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/aegisops"),
)

# Convert asyncpg prefix to psycopg2 for sync operations if needed
if PRIMARY_DB_URL.startswith("postgresql+asyncpg://"):
    PRIMARY_DB_URL = PRIMARY_DB_URL.replace("postgresql+asyncpg://", "postgresql://")

FALLBACK_SQLITE_URL = "sqlite:///./aegisops_local.db"


def _build_engine():
    """Initializes SQLAlchemy engine with PostgreSQL, falling back to SQLite if unreachable."""
    try:
        engine = create_engine(
            PRIMARY_DB_URL,
            pool_pre_ping=True,
            echo=False,
        )
        # Verify connection
        with engine.connect() as conn:
            pass
        logger.info("Connected successfully to database: %s", PRIMARY_DB_URL.split("@")[-1] if "@" in PRIMARY_DB_URL else PRIMARY_DB_URL)
        return engine
    except Exception as exc:
        logger.warning(
            "Primary database at '%s' is unavailable (%s). Falling back to SQLite local storage.",
            PRIMARY_DB_URL,
            exc,
        )
        sqlite_engine = create_engine(
            FALLBACK_SQLITE_URL,
            connect_args={"check_same_thread": False},
            echo=False,
        )
        return sqlite_engine


engine = _build_engine()
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_sync_db() -> Generator[Session, None, None]:
    """Dependency for FastAPI route handlers requesting a SQLAlchemy Session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_db_session() -> Generator[Session, None, None]:
    """Alias for get_sync_db for backwards and dependency compatibility."""
    return get_sync_db()


def init_database() -> None:
    """Creates all registered database tables in the configured database."""
    # Ensure all models are imported before creating tables
    import database.models  # noqa: F401
    Base.metadata.create_all(bind=engine)
    logger.info("Database schema synchronized successfully")
