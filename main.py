from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base

DATABASE_URL = "postgresql+asyncpg://user:password@localhost:5432/mangadb"

# criar engine
engine = create_async_engine(DATABASE_URL, echo=True, future=True)

Base = declarative_base()

async_session = sessionmaker(
    engine, expire_on_commit=False, class_=AsyncSession
)