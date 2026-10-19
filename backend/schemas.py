from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field


class Location(BaseModel):
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)


class TransactionInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    transaction_id: str = Field(default_factory=lambda: str(uuid4()), min_length=1, max_length=100)
    customer_id: str = Field(default="demo-customer-01", min_length=1, max_length=100)
    amount: float = Field(gt=0, le=1_000_000_000)
    currency: str = Field(default="NGN", pattern=r"^[A-Z]{3}$")
    merchant: str = Field(default="Synthetic recipient", min_length=1, max_length=200)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    device_trusted: bool | None = None
    location: Location | None = None
    usual_location: Location | None = None
    history_avg_amount: float | None = Field(default=None, ge=0)
    recent_transaction_count: int | None = Field(default=None, ge=0)
    new_payee: bool | None = None
    failed_attempt_count: int | None = Field(default=None, ge=0)


class DetectedSignal(BaseModel):
    name: str
    points: int
    reason: str
    severity: Literal["info", "medium", "high"]


class SuggestedAction(BaseModel):
    code: Literal[
        "normal_processing",
        "additional_verification",
        "authorization_review",
    ]
    label: str
    description: str
    notify_fraud_team: bool


class TransactionAssessment(BaseModel):
    transaction_id: str
    transaction: TransactionInput
    risk_score: int
    risk_level: Literal["low", "medium", "high"]
    detected_signals: list[DetectedSignal]
    suggested_action: SuggestedAction
    notice: str
    created_at: datetime


class HealthResponse(BaseModel):
    status: Literal["ok"]
    database: Literal["connected"]
