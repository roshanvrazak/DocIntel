import os
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession


DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://docintel:docintel@localhost:5432/docintel")

# Handle asyncpg driver
if DATABASE_URL.startswith("postgresql://"):
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://", 1)


engine = create_async_engine(DATABASE_URL, echo=True)
async_session = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


async def get_session() -> AsyncSession:
    async with async_session() as session:
        yield session
