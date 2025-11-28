import os
from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import sessionmaker, declarative_base
from typing import AsyncGenerator, Generator, Optional

from src.config.Settings import settings

Base = declarative_base()

# Lazy engine initialization - only create when actually needed
_engine = None
_async_engine = None
_SessionLocal = None
_AsyncSessionLocal = None


def _is_testing() -> bool:
    """Check if running in test environment"""
    return os.environ.get("TESTING", "").lower() == "true"


def get_engine():
    """Get or create the sync engine"""
    global _engine
    if _engine is None and not _is_testing():
        _engine = create_engine(
            settings.DATABASE_URL_SYNC,
            echo=settings.DEBUG,
            pool_pre_ping=True
        )
    return _engine


def get_async_engine():
    """Get or create the async engine"""
    global _async_engine
    if _async_engine is None and not _is_testing():
        _async_engine = create_async_engine(
            settings.DATABASE_URL,
            echo=settings.DEBUG,
            pool_pre_ping=True
        )
    return _async_engine


def get_session_local():
    """Get or create the sync session factory"""
    global _SessionLocal
    if _SessionLocal is None:
        engine = get_engine()
        if engine:
            _SessionLocal = sessionmaker(
                bind=engine,
                autocommit=False,
                autoflush=False
            )
    return _SessionLocal


def get_async_session_local():
    """Get or create the async session factory"""
    global _AsyncSessionLocal
    if _AsyncSessionLocal is None:
        async_engine = get_async_engine()
        if async_engine:
            _AsyncSessionLocal = async_sessionmaker(
                bind=async_engine,
                class_=AsyncSession,
                autocommit=False,
                autoflush=False,
                expire_on_commit=False
            )
    return _AsyncSessionLocal


# Backwards compatibility - these are now functions/properties
@property
def engine():
    return get_engine()


@property
def async_engine():
    return get_async_engine()


# Create lazy proxies for session factories
class LazySessionLocal:
    def __call__(self):
        factory = get_session_local()
        if factory:
            return factory()
        raise RuntimeError("Database not configured for testing. Set TESTING=true or configure database.")


class LazyAsyncSessionLocal:
    def __call__(self):
        factory = get_async_session_local()
        if factory:
            return factory()
        raise RuntimeError("Database not configured for testing. Set TESTING=true or configure database.")


SessionLocal = LazySessionLocal()
AsyncSessionLocal = LazyAsyncSessionLocal()


def get_db() -> Generator:
    """Dependency para obtener sesión sincrónica de DB"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


async def get_async_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency para obtener sesión asíncrona de DB"""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


async def init_db() -> None:
    """Inicializa la base de datos creando todas las tablas"""
    engine = get_async_engine()
    if engine:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
