from datetime import datetime
from sqlalchemy import String, Float, Integer, DateTime, Boolean, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .database import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    email: Mapped[str] = mapped_column(String(180), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    trust_score: Mapped[float] = mapped_column(Float, default=100.0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    transactions = relationship(
        "Transaction",
        back_populates="user",
        cascade="all, delete-orphan"
    )


class Transaction(Base):
    __tablename__ = "transactions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    txn_date: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
    description: Mapped[str] = mapped_column(String(255))
    merchant: Mapped[str] = mapped_column(String(120), default="Unknown")
    category: Mapped[str] = mapped_column(String(80), default="Other")
    amount: Mapped[float] = mapped_column(Float)
    txn_type: Mapped[str] = mapped_column(String(20), default="debit")
    source: Mapped[str] = mapped_column(String(30), default="manual")
    latitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    longitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    city: Mapped[str | None] = mapped_column(String(100), nullable=True)
    country: Mapped[str | None] = mapped_column(String(100), nullable=True)
    risk_score: Mapped[float] = mapped_column(Float, default=0.0)
    is_fraud: Mapped[bool] = mapped_column(Boolean, default=False)
    fraud_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    fingerprint: Mapped[str] = mapped_column(String(64), unique=True, index=True)

    user = relationship("User", back_populates="transactions")


class UserLocation(Base):
    __tablename__ = "user_locations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    latitude: Mapped[float] = mapped_column(Float)
    longitude: Mapped[float] = mapped_column(Float)
    accuracy: Mapped[float | None] = mapped_column(Float, nullable=True)
    captured_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)


class Alert(Base):
    __tablename__ = "alerts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    transaction_id: Mapped[int | None] = mapped_column(
        ForeignKey("transactions.id"),
        nullable=True
    )
    alert_type: Mapped[str] = mapped_column(String(80))
    severity: Mapped[str] = mapped_column(String(20), default="medium")
    message: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    resolved: Mapped[bool] = mapped_column(Boolean, default=False)


class BehaviorEvent(Base):
    __tablename__ = "behavior_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)

    typing_speed_wpm: Mapped[float] = mapped_column(Float, default=0.0)
    avg_key_interval_ms: Mapped[float] = mapped_column(Float, default=0.0)
    mouse_speed_px_s: Mapped[float] = mapped_column(Float, default=0.0)
    click_rate_per_min: Mapped[float] = mapped_column(Float, default=0.0)
    session_duration_s: Mapped[float] = mapped_column(Float, default=0.0)

    risk_score: Mapped[float] = mapped_column(Float, default=0.0)
    is_anomaly: Mapped[bool] = mapped_column(Boolean, default=False)
    reason: Mapped[str] = mapped_column(Text, default="Building behavioral baseline")
    captured_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
