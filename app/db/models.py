from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    tg_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    notifications_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    quiet_hours: Mapped[str] = mapped_column(String(32), default="23:00-07:00")
    polling_interval: Mapped[int] = mapped_column(Integer, default=60)
    match_threshold: Mapped[int] = mapped_column(Integer, default=3)
    hourly_limit: Mapped[int | None] = mapped_column(Integer, nullable=True, default=None)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    subscriptions: Mapped[list[Subscription]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )


class Subscription(Base):
    __tablename__ = "subscriptions"
    __table_args__ = (UniqueConstraint("tg_id", "ticker", name="uq_subscription"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    tg_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.tg_id"), index=True)
    ticker: Mapped[str] = mapped_column(String(16), index=True)

    user: Mapped[User] = relationship(back_populates="subscriptions")


class FeedSource(Base):
    __tablename__ = "feed_sources"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(255))
    url: Mapped[str] = mapped_column(String(2048), unique=True)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)


class FeedState(Base):
    __tablename__ = "feed_state"

    source_id: Mapped[int] = mapped_column(Integer, ForeignKey("feed_sources.id"), primary_key=True)
    etag: Mapped[str | None] = mapped_column(String(255), nullable=True)
    last_modified: Mapped[str | None] = mapped_column(String(255), nullable=True)
    last_checked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_item_ts: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class NewsItem(Base):
    __tablename__ = "news_items"
    __table_args__ = (UniqueConstraint("canonical_hash", name="uq_news_hash"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    canonical_hash: Mapped[str] = mapped_column(String(64), index=True)
    title: Mapped[str] = mapped_column(String(512))
    url: Mapped[str] = mapped_column(String(2048))
    published_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    source_id: Mapped[int] = mapped_column(Integer, ForeignKey("feed_sources.id"))
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    raw: Mapped[str | None] = mapped_column(Text, nullable=True)


class NewsMention(Base):
    __tablename__ = "news_mentions"
    __table_args__ = (UniqueConstraint("news_id", "ticker", name="uq_news_mention"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    news_id: Mapped[int] = mapped_column(Integer, ForeignKey("news_items.id"), index=True)
    ticker: Mapped[str] = mapped_column(String(16), index=True)
    score: Mapped[int] = mapped_column(Integer, default=0)


class Delivery(Base):
    __tablename__ = "deliveries"
    __table_args__ = (UniqueConstraint("news_id", "tg_id", name="uq_delivery"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    news_id: Mapped[int] = mapped_column(Integer, ForeignKey("news_items.id"))
    tg_id: Mapped[int] = mapped_column(Integer, index=True)
    delivered_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
