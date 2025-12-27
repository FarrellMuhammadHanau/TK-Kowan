from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, DeclarativeBase, Mapped, mapped_column
from sqlalchemy import String, Integer
import uuid
import os

# Use port 5434 by default for local development (we will add this to docker-compose)
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+asyncpg://postgres:postgres@localhost:5434/schedule_service_db"
)

engine = create_async_engine(DATABASE_URL, echo=True)
SessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

class Base(DeclarativeBase):
    pass

class Schedule(Base):
    __tablename__ = "schedules"
    
    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    institution_id: Mapped[str] = mapped_column(String, nullable=False)
    
    # External References
    room_id: Mapped[str] = mapped_column(String, nullable=False)
    room_name: Mapped[str] = mapped_column(String, nullable=True) # Cached
    
    class_id: Mapped[str] = mapped_column(String, nullable=False)
    class_name: Mapped[str] = mapped_column(String, nullable=True) # Cached
    
    # Timing
    day: Mapped[int] = mapped_column(Integer, nullable=False) # 1=Mon, 7=Sun
    start_time: Mapped[int] = mapped_column(Integer, nullable=False) # HHMM (e.g., 800)
    end_time: Mapped[int] = mapped_column(Integer, nullable=False)   # HHMM (e.g., 1000)

async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
