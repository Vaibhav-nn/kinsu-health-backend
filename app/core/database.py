"""SQLAlchemy database engine, session factory, and declarative base.

Supports both async (PostgreSQL via asyncpg) and sync (SQLite) databases.
Configure via DATABASE_URL in your .env file.
"""

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


# ── Engine ────────────────────────────────────────────────
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=False,
)

# ── Session ───────────────────────────────────────────────
async_session_factory = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


# ── Declarative Base ──────────────────────────────────────
class Base(DeclarativeBase):
    """Base class for all ORM models."""
    pass


# ── Dependency ────────────────────────────────────────────
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency that yields a database session.

    Usage:
        @app.get("/items")
        async def read_items(db: AsyncSession = Depends(get_db)):
            ...
    """
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
            logger.debug("Database session committed successfully")
        except Exception as e:
            await session.rollback()
            logger.error(
                "Database session rolled back due to error",
                extra={"extra_fields": {"error": str(e)}},
            )
            raise
        finally:
            await session.close()


# ── Database Initialization ───────────────────────────────
async def init_db() -> None:
    """Initialize database tables (for development only).
    
    In production, use Alembic migrations instead.
    """
    logger.info("Initializing database tables")
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("Database tables initialized successfully")
    except Exception as e:
        logger.exception(
            "Failed to initialize database",
            extra={"extra_fields": {"error": str(e)}},
        )
        raise
