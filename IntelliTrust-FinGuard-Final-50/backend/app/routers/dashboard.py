from datetime import datetime

from fastapi import APIRouter, Depends
from sqlalchemy import select, func
from sqlalchemy.orm import Session

from ..auth import current_user
from ..database import get_db
from ..models import Alert, BehaviorEvent, Transaction, User
from ..services.ml_expense import (
    build_monthly_spending_trend,
    predict_next_month_spending,
)


router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


@router.get("")
def dashboard(
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    rows = list(
        db.scalars(
            select(Transaction)
            .where(Transaction.user_id == user.id)
        )
    )

    total_income = sum(
        t.amount
        for t in rows
        if t.txn_type == "credit"
    )

    total_debits = sum(
        t.amount
        for t in rows
        if t.txn_type != "credit"
    )

    balance = total_income - total_debits

    now = datetime.utcnow()

    current_month_rows = [
        t
        for t in rows
        if (
            t.txn_date.year == now.year
            and t.txn_date.month == now.month
        )
    ]

    current_month_expense = sum(
        t.amount
        for t in current_month_rows
        if t.txn_type != "credit"
    )

    forecast = predict_next_month_spending(rows)
    monthly_trend = build_monthly_spending_trend(rows)

    active_alerts = db.scalar(
        select(func.count(Alert.id))
        .where(
            Alert.user_id == user.id,
            Alert.resolved == False,
        )
    ) or 0

    latest_behavior = db.scalar(
        select(BehaviorEvent)
        .where(BehaviorEvent.user_id == user.id)
        .order_by(BehaviorEvent.captured_at.desc())
    )

    behavior_count = db.scalar(
        select(func.count(BehaviorEvent.id))
        .where(BehaviorEvent.user_id == user.id)
    ) or 0

    if latest_behavior is None:
        behavior_status = "Waiting"
        behavior_risk = 0.0
        behavior_reason = "Waiting for user activity"
    elif behavior_count < 3:
        behavior_status = "Learning"
        behavior_risk = latest_behavior.risk_score
        behavior_reason = latest_behavior.reason
    else:
        behavior_status = (
            "Alert"
            if latest_behavior.is_anomaly
            else "Normal"
        )
        behavior_risk = latest_behavior.risk_score
        behavior_reason = latest_behavior.reason

    categories = {}

    for transaction in current_month_rows:
        if transaction.txn_type != "credit":
            categories[transaction.category] = (
                categories.get(transaction.category, 0)
                + transaction.amount
            )


    # Latest explainable fraud decision for the dashboard.
    latest_fraud_tx = db.scalar(
        select(Transaction)
        .where(
            Transaction.user_id == user.id,
            Transaction.is_fraud == True,
        )
        .order_by(Transaction.txn_date.desc())
    )

    latest_fraud_explanation = None

    if latest_fraud_tx is not None:
        reasons = [
            reason.strip()
            for reason in (latest_fraud_tx.fraud_reason or "").split(";")
            if reason.strip()
        ]

        latest_fraud_explanation = {
            "transaction_id": latest_fraud_tx.id,
            "merchant": latest_fraud_tx.merchant,
            "amount": round(float(latest_fraud_tx.amount), 2),
            "risk_score": round(float(latest_fraud_tx.risk_score), 1),
            "city": latest_fraud_tx.city,
            "country": latest_fraud_tx.country,
            "date": latest_fraud_tx.txn_date.isoformat(),
            "reasons": reasons,
        }

    recent = sorted(
        rows,
        key=lambda x: x.txn_date,
        reverse=True,
    )[:6]

    return {
        "balance": round(balance, 2),
        "income": round(total_income, 2),
        "expense": round(current_month_expense, 2),

        "predicted_spending": forecast["prediction"],
        "forecast_ready": forecast["ready"],
        "forecast_method": forecast["method"],
        "forecast_training_months": forecast["training_months"],
        "forecast_r2": forecast["r2"],
        "forecast_reason": forecast["reason"],

        "monthly_trend": monthly_trend,

        "latest_fraud_explanation": latest_fraud_explanation,

        "trust_score": round(
            user.trust_score
            if user.trust_score is not None
            else 100.0,
            1,
        ),
        "active_alerts": active_alerts,

        "behavior_status": behavior_status,
        "behavior_risk": round(behavior_risk, 1),
        "behavior_reason": behavior_reason,

        "categories": [
            {
                "name": key,
                "value": round(value, 2),
            }
            for key, value in sorted(
                categories.items(),
                key=lambda item: item[1],
                reverse=True,
            )
        ],

        "recent": [
            {
                "id": transaction.id,
                "merchant": transaction.merchant,
                "amount": transaction.amount,
                "category": transaction.category,
                "txn_type": transaction.txn_type,
                "risk_score": transaction.risk_score,
                "is_fraud": transaction.is_fraud,
                "date": transaction.txn_date.isoformat(),
            }
            for transaction in recent
        ],
    }
