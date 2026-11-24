from datetime import datetime, timezone
from sqlalchemy import BigInteger, Integer, String, DateTime, ForeignKey, Boolean, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from .db import Base
def now():
    return datetime.now(timezone.utc)
class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    username: Mapped[str | None] = mapped_column(String(64), nullable=True)
    balance: Mapped[int] = mapped_column(Integer, default=0)
    referred_by: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
class Ledger(Base):
    __tablename__ = "ledger"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"), index=True)
    amount: Mapped[int] = mapped_column(Integer)
    reason: Mapped[str] = mapped_column(String(120))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
class Withdrawal(Base):
    __tablename__ = "withdrawals"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"), index=True)
    amount: Mapped[int] = mapped_column(Integer)
    destination: Mapped[str] = mapped_column(String(160))
    status: Mapped[str] = mapped_column(String(20), default="pending")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
class Video(Base):
    __tablename__ = "videos"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(120))
    url: Mapped[str] = mapped_column(String(500))
    duration_seconds: Mapped[int] = mapped_column(Integer, default=15)
    reward: Mapped[int] = mapped_column(Integer, default=10)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
class WatchSession(Base):
    __tablename__ = "watch_sessions"
    __table_args__ = (UniqueConstraint("session_token", name="uq_watch_session_token"),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_token: Mapped[str] = mapped_column(String(64), index=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"), index=True)
    video_id: Mapped[int] = mapped_column(Integer, ForeignKey("videos.id"))
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    rewarded: Mapped[bool] = mapped_column(Boolean, default=False)
