import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession


DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://docintel:docintel@localhost:5432/docintel")
DEBUG_DB = os.getenv("DEBUG_DB", "False").lower() == "true"

# Handle asyncpg driver for different environment prefixes
ASYNC_DATABASE_URL = DATABASE_URL
if ASYNC_DATABASE_URL.startswith("postgresql://"):
    ASYNC_DATABASE_URL = ASYNC_DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://", 1)
elif ASYNC_DATABASE_URL.startswith("postgres://"):
    ASYNC_DATABASE_URL = ASYNC_DATABASE_URL.replace("postgres://", "postgresql+asyncpg://", 1)


engine = create_async_engine(ASYNC_DATABASE_URL, echo=DEBUG_DB)
async_session = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


async def get_session() -> AsyncSession:
    async with async_session() as session:
        yield session

# Synchronous engine for Celery
sync_engine = create_engine(DATABASE_URL, echo=DEBUG_DB)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=sync_engine)

from contextlib import contextmanager

@contextmanager
def get_sync_session():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
