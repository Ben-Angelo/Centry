from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from backend.database import Base, engine, get_db
from backend.models import TransactionRecord
from backend.policy_engine import recommend_action
from backend.risk_engine import assess_transaction
from backend.schemas import HealthResponse, TransactionAssessment, TransactionInput

FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend"
logger = logging.getLogger("sentry.transactions")
if not logger.handlers:
    log_handler = logging.StreamHandler()
    log_handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
    logger.addHandler(log_handler)
logger.setLevel(logging.INFO)
logger.propagate = False


@asynccontextmanager
async def lifespan(_app: FastAPI):
    Base.metadata.create_all(bind=engine)
    logger.info("Sentry started; database dialect=%s", engine.dialect.name)
    yield


app = FastAPI(
    title="Sentry Transaction Simulator",
    description=(
        "Synthetic transaction assessments with explainable signals and advisory "
        "bank actions. A risk score is not proof of coercion."
    ),
    version="1.0.0",
    lifespan=lifespan,
)
app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")


def serialize_record(record: TransactionRecord) -> dict[str, Any]:
    return {
        "transaction_id": record.transaction_id,
        "transaction": record.transaction_data,
        "risk_score": record.risk_score,
        "risk_level": record.risk_level,
        "detected_signals": record.detected_signals,
        "suggested_action": record.suggested_action,
        "notice": record.notice,
        "created_at": record.created_at,
    }


@app.get("/", include_in_schema=False)
def dashboard() -> FileResponse:
    return FileResponse(FRONTEND_DIR / "index.html")


@app.get("/health", response_model=HealthResponse)
def health(db: Session = Depends(get_db)) -> HealthResponse:
    try:
        db.execute(text("SELECT 1"))
    except SQLAlchemyError as exc:
        raise HTTPException(status_code=503, detail="Database is unavailable") from exc
    return HealthResponse(status="ok", database="connected")


@app.post("/transactions/simulate", response_model=TransactionAssessment, status_code=201)
def simulate_transaction(
    transaction: TransactionInput,
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    transaction_data = transaction.model_dump(mode="json")
    assessment = assess_transaction(transaction.model_dump(mode="python"))
    action = recommend_action(assessment["risk_level"])
    record = TransactionRecord(
        transaction_id=transaction.transaction_id,
        transaction_data=transaction_data,
        risk_score=assessment["risk_score"],
        risk_level=assessment["risk_level"],
        detected_signals=assessment["detected_signals"],
        suggested_action=action,
        notice=assessment["notice"],
        created_at=datetime.now(timezone.utc),
    )
    try:
        db.add(record)
        db.commit()
        db.refresh(record)
    except IntegrityError as exc:
        db.rollback()
        logger.warning("Transaction ID conflict: transaction_id=%s", transaction.transaction_id)
        raise HTTPException(
            status_code=409,
            detail="Transaction ID already exists; submit a new transaction ID.",
        ) from exc
    except SQLAlchemyError as exc:
        db.rollback()
        logger.exception(
            "Could not save assessment: transaction_id=%s",
            transaction.transaction_id,
        )
        raise HTTPException(status_code=503, detail="Could not save transaction") from exc
    logger.info(
        "Assessment saved: transaction_id=%s risk_score=%d risk_level=%s action=%s",
        record.transaction_id,
        record.risk_score,
        record.risk_level,
        record.suggested_action["code"],
    )
    return serialize_record(record)


@app.get("/transactions", response_model=list[TransactionAssessment])
def list_transactions(
    limit: int = Query(default=50, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
) -> list[dict[str, Any]]:
    records = db.scalars(
        select(TransactionRecord)
        .order_by(TransactionRecord.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    serialized_records = [serialize_record(record) for record in records]
    logger.info(
        "Transaction log retrieved: count=%d limit=%d offset=%d",
        len(serialized_records),
        limit,
        offset,
    )
    return serialized_records
