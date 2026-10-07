import os
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from sqlalchemy import BigInteger, CheckConstraint, DateTime, String, create_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker
from sqlalchemy.types import TypeDecorator

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+psycopg://diary:diary@localhost:5432/diary")
APP_TZ = ZoneInfo(os.getenv("APP_TZ", "Asia/Almaty"))  # defines where a "day" starts and ends

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(engine, expire_on_commit=False)


class UTCDateTime(TypeDecorator):
    """Stores UTC, always returns aware datetimes (SQLite would drop the tzinfo)."""

    impl = DateTime(timezone=True)
    cache_ok = True

    def process_bind_param(self, value, dialect):
        return value.astimezone(timezone.utc) if value is not None else None

    def process_result_value(self, value, dialect):
        if value is not None and value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value


class Base(DeclarativeBase):
    pass


class Trip(Base):
    __tablename__ = "trips"
    __table_args__ = (
        CheckConstraint(
            "amount > 0 AND ended_at > started_at AND commission BETWEEN 0 AND amount",
            name="ck_trips_valid",
        ),
    )

    id: Mapped[str] = mapped_column(String(64), primary_key=True)  # client id = idempotency key
    start: Mapped[datetime] = mapped_column("started_at", UTCDateTime, index=True)
    end: Mapped[datetime] = mapped_column("ended_at", UTCDateTime)
    amount: Mapped[int] = mapped_column(BigInteger)
    payment: Mapped[str] = mapped_column(String(4))
    commission: Mapped[int] = mapped_column(BigInteger)
