import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from app.models import Base

DATABASE_URL = "postgresql+asyncpg://postgres:senha123@localhost:5432/mangadb"
engine = create_async_engine(DATABASE_URL, echo=True)

async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        
asyncio.run(init_db())

