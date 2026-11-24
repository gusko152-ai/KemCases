from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import DeclarativeBase
from .config import settings

url = settings.database_url
if url.startswith("postgres://"):
    url = url.replace("postgres://", "postgresql+asyncpg://", 1)
elif url.startswith("postgresql://") and "+asyncpg" not in url:
    url = url.replace("postgresql://", "postgresql+asyncpg://", 1)

engine = create_async_engine(url, pool_pre_ping=True)
Session = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

class Base(DeclarativeBase):
    pass

async def init_db():
    from . import models  # noqa: F401
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
