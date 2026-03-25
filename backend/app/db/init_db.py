import asyncio
import sys
import os

# Add project root to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

from sqlalchemy import text
from backend.app.db.base import Base
from backend.app.db.session import engine
# Import models to register them with Base.metadata
from backend.app.models.document import Document, Chunk


async def init_db():
    try:
        async with engine.begin() as conn:
            # Enable pgvector extension
            print("Enabling pgvector extension...")
            await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector;"))

            # Create all tables
            print("Creating tables...")
            await conn.run_sync(Base.metadata.create_all)

        print("Database initialization complete.")
    except Exception as e:
        print(f"Error initializing database: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(init_db())
