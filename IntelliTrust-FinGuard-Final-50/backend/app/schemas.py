from datetime import datetime
from pydantic import BaseModel, EmailStr, Field


class RegisterIn(BaseModel):
    name: str
    email: EmailStr
    password: str


class LoginIn(BaseModel):
    email: EmailStr
    password: str


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    name: str


class LocationIn(BaseModel):
    latitude: float
    longitude: float
    accuracy: float | None = None


class BehaviorIn(BaseModel):
    typing_speed_wpm: float = Field(ge=0, le=400)
    avg_key_interval_ms: float = Field(ge=0, le=10000)
    mouse_speed_px_s: float = Field(ge=0, le=20000)
    click_rate_per_min: float = Field(ge=0, le=1000)
    session_duration_s: float = Field(ge=0, le=86400)


class BehaviorOut(BaseModel):
    risk_score: float
    is_anomaly: bool
    status: str
    reason: str
    baseline_samples: int
    trust_score: float


class TransactionOut(BaseModel):
    id: int
    txn_date: datetime
    description: str
    merchant: str
    category: str
    amount: float
    txn_type: str
    source: str
    risk_score: float
    is_fraud: bool
    fraud_reason: str | None
    city: str | None
    country: str | None

    model_config = {"from_attributes": True}
