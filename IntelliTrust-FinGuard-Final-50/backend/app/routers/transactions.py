from io import BytesIO
from random import choice, randint, uniform
from datetime import datetime
import hashlib

from fastapi import APIRouter, Depends, File, UploadFile, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Transaction, UserLocation, Alert, User
from ..schemas import TransactionOut
from ..auth import current_user
from ..services.importer import parse_statement
from ..services.risk import score_transaction, haversine_km
from ..services.ml_fraud import isolation_forest_score


router = APIRouter(
    prefix="/api/transactions",
    tags=["transactions"]
)


SIMULATED_CITIES = [
    {"city": "Delhi", "country": "India", "latitude": 28.6139, "longitude": 77.2090},
    {"city": "Mumbai", "country": "India", "latitude": 19.0760, "longitude": 72.8777},
    {"city": "Bengaluru", "country": "India", "latitude": 12.9716, "longitude": 77.5946},
    {"city": "Kolkata", "country": "India", "latitude": 22.5726, "longitude": 88.3639},
    {"city": "Chennai", "country": "India", "latitude": 13.0827, "longitude": 80.2707},
    {"city": "Hyderabad", "country": "India", "latitude": 17.3850, "longitude": 78.4867},
]


def apply_risk(db: Session, user: User, tx: Transaction):
    # Credits such as salary are not fraud-scored in this prototype.
    if tx.txn_type != "debit":
        tx.risk_score = 0.0
        tx.is_fraud = False
        tx.fraud_reason = "Credit transaction"
        return

    # Keep enough history for the ML model while excluding the current transaction.
    history = list(
        db.scalars(
            select(Transaction)
            .where(
                Transaction.user_id == user.id,
                Transaction.txn_type == "debit",
                Transaction.id != tx.id,
            )
            .order_by(Transaction.txn_date.desc())
            .limit(120)
        )
    )

    prior_amounts = [historical_tx.amount for historical_tx in history[:30]]

    latest_loc = db.scalar(
        select(UserLocation)
        .where(UserLocation.user_id == user.id)
        .order_by(UserLocation.captured_at.desc())
    )

    geo_distance = None
    if latest_loc and tx.latitude is not None and tx.longitude is not None:
        geo_distance = haversine_km(
            latest_loc.latitude,
            latest_loc.longitude,
            tx.latitude,
            tx.longitude,
        )

    # 1) Explainable rule / geographic risk
    rule_score, rule_reasons = score_transaction(
        tx.amount,
        prior_amounts,
        geo_distance,
    )

    # 2) Actual Scikit-learn Isolation Forest anomaly detection
    ml_score, ml_anomaly, ml_reason = isolation_forest_score(
        tx,
        history,
        latest_loc,
    )

    if ml_score is None:
        final_score = rule_score
        is_fraud = rule_score >= 70
    else:
        # Strongest signal wins. This keeps explainable rules effective while
        # allowing the unsupervised ML model to independently flag anomalies.
        final_score = max(rule_score, ml_score)
        is_fraud = (rule_score >= 70) or (ml_anomaly and ml_score >= 75)

    reasons = list(rule_reasons)
    reasons.append(ml_reason)

    tx.risk_score = round(final_score, 1)
    tx.is_fraud = is_fraud
    tx.fraud_reason = "; ".join(reasons)

    current_trust = (
        user.trust_score
        if user.trust_score is not None
        else 100.0
    )

    if tx.is_fraud:
        if final_score >= 90:
            penalty = 12.0
            severity = "critical"
        else:
            penalty = 8.0
            severity = "high"

        user.trust_score = max(0.0, current_trust - penalty)

        db.add(
            Alert(
                user_id=user.id,
                transaction_id=tx.id,
                alert_type="fraud",
                severity=severity,
                message=tx.fraud_reason,
            )
        )
    else:
        user.trust_score = min(100.0, current_trust + 2.0)


@router.get("", response_model=list[TransactionOut])
def list_transactions(
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    return list(
        db.scalars(
            select(Transaction)
            .where(Transaction.user_id == user.id)
            .order_by(Transaction.txn_date.desc())
            .limit(100)
        )
    )


@router.post("/import")
def import_csv(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    filename = file.filename or ""

    if not filename.lower().endswith(".csv"):
        raise HTTPException(
            status_code=400,
            detail="Please upload a CSV file",
        )

    try:
        rows = parse_statement(BytesIO(file.file.read()))
    except Exception as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc

    imported = 0
    duplicates = 0
    frauds = 0

    for row in rows:
        existing = db.scalar(
            select(Transaction.id).where(
                Transaction.user_id == user.id,
                Transaction.fingerprint == row["fingerprint"],
            )
        )

        if existing:
            duplicates += 1
            continue

        tx = Transaction(
            user_id=user.id,
            source="csv",
            **row,
        )

        db.add(tx)
        db.flush()
        apply_risk(db, user, tx)

        imported += 1
        frauds += int(tx.is_fraud)

    db.commit()

    return {
        "imported": imported,
        "duplicates": duplicates,
        "fraud_flags": frauds,
    }


@router.post("/simulate", response_model=TransactionOut)
def simulate(
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    merchants = [
        ("Swiggy", "Food"),
        ("Amazon", "Shopping"),
        ("Uber", "Travel"),
        ("Airtel", "Bills"),
        ("Starbucks", "Food"),
    ]

    merchant, category = choice(merchants)
    amount = round(uniform(150, 2500), 2)

    latest_loc = db.scalar(
        select(UserLocation)
        .where(UserLocation.user_id == user.id)
        .order_by(UserLocation.captured_at.desc())
    )

    latitude = None
    longitude = None
    city = None
    country = None

    # Roughly 25% of simulated transactions are deliberately suspicious.
    suspicious = randint(1, 4) == 4

    if suspicious:
        amount = float(randint(45000, 95000))
        merchant = "Unknown Electronics"
        category = "Electronics"

        if latest_loc:
            farthest_city = max(
                SIMULATED_CITIES,
                key=lambda location: haversine_km(
                    latest_loc.latitude,
                    latest_loc.longitude,
                    location["latitude"],
                    location["longitude"],
                ),
            )

            latitude = farthest_city["latitude"]
            longitude = farthest_city["longitude"]
            city = farthest_city["city"]
            country = farthest_city["country"]
        else:
            latitude = 28.6139
            longitude = 77.2090
            city = "Delhi"
            country = "India"
    elif latest_loc:
        # Normal simulated purchase is placed very close to the live device.
        latitude = latest_loc.latitude + uniform(-0.003, 0.003)
        longitude = latest_loc.longitude + uniform(-0.003, 0.003)
        city = "Current Area"
        country = "India"

    now = datetime.utcnow()
    seed = f"{now.isoformat()}|{merchant}|{amount}|{latitude}|{longitude}"

    tx = Transaction(
        user_id=user.id,
        txn_date=now,
        description=merchant,
        merchant=merchant,
        category=category,
        amount=amount,
        txn_type="debit",
        source="simulator",
        fingerprint=hashlib.sha256(seed.encode()).hexdigest(),
        latitude=latitude,
        longitude=longitude,
        city=city,
        country=country,
    )

    db.add(tx)
    db.flush()
    apply_risk(db, user, tx)
    db.commit()
    db.refresh(tx)

    return TransactionOut.model_validate(tx)
