from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import sessionmaker, declarative_base
from typing import AsyncGenerator, Generator

from src.config.Settings import settings

Base = declarative_base()

# Sync engine (para migraciones con Alembic)
engine = create_engine(
    settings.DATABASE_URL_SYNC,
    echo=settings.DEBUG,
    pool_pre_ping=True
)

# Async engine (para la aplicación)
async_engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,
    pool_pre_ping=True
)

# Session factories
SessionLocal = sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False
)

AsyncSessionLocal = async_sessionmaker(
    bind=async_engine,
    class_=AsyncSession,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False
)


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
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
