from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, DeclarativeBase, Mapped, mapped_column
from sqlalchemy import String, DateTime
import uuid
import os
from datetime import datetime

# Port 5437 will be used for local dev
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+asyncpg://postgres:postgres@localhost:5437/attendance_service_db"
)

engine = create_async_engine(DATABASE_URL, echo=True)
SessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

class Base(DeclarativeBase):
    pass

class Attendance(Base):
    __tablename__ = "attendances"
    
    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    institution_id: Mapped[str] = mapped_column(String, nullable=False)
    
    class_attendee_id: Mapped[str] = mapped_column(String, nullable=False)
    schedule_id: Mapped[str] = mapped_column(String, nullable=False)
    
    class_name: Mapped[str] = mapped_column(String, nullable=True)
    room_name: Mapped[str] = mapped_column(String, nullable=True)
    
    present_time: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
