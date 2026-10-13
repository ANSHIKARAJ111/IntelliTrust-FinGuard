import math
from typing import Iterable

import numpy as np
from sklearn.ensemble import IsolationForest

from ..models import Transaction, UserLocation
from .risk import haversine_km


MIN_TRAINING_SAMPLES = 8


def _cyclic(value: float, period: float) -> tuple[float, float]:
    angle = 2.0 * math.pi * value / period
    return math.sin(angle), math.cos(angle)


def _features(
    tx: Transaction,
    live_location: UserLocation | None,
) -> list[float]:
    amount_log = math.log1p(max(float(tx.amount), 0.0))

    hour = float(tx.txn_date.hour)
    weekday = float(tx.txn_date.weekday())

    hour_sin, hour_cos = _cyclic(hour, 24.0)
    day_sin, day_cos = _cyclic(weekday, 7.0)

    geo_distance = 0.0
    has_geo = 0.0

    if (
        live_location is not None
        and tx.latitude is not None
        and tx.longitude is not None
    ):
        geo_distance = haversine_km(
            live_location.latitude,
            live_location.longitude,
            tx.latitude,
            tx.longitude,
        )
        has_geo = 1.0

    # log1p prevents a single huge distance from dominating the model.
    geo_log = math.log1p(max(geo_distance, 0.0))

    return [
        amount_log,
        hour_sin,
        hour_cos,
        day_sin,
        day_cos,
        geo_log,
        has_geo,
    ]


def isolation_forest_score(
    current_tx: Transaction,
    historical_transactions: Iterable[Transaction],
    live_location: UserLocation | None,
) -> tuple[float | None, bool, str]:
    """
    Train a per-user Isolation Forest on previous NORMAL debit transactions.

    Returns:
        ml_risk_score: 0-99, or None when there is not enough history
        is_anomaly: whether Isolation Forest marked the current transaction anomalous
        reason: human-readable explanation for the dashboard / alert
    """

    normal_history = [
        tx
        for tx in historical_transactions
        if tx.txn_type == "debit" and not tx.is_fraud
    ]

    if len(normal_history) < MIN_TRAINING_SAMPLES:
        return (
            None,
            False,
            f"Isolation Forest is learning: {len(normal_history)}/{MIN_TRAINING_SAMPLES} normal samples available",
        )

    training_matrix = np.array(
        [_features(tx, live_location) for tx in normal_history],
        dtype=float,
    )

    current_vector = np.array(
        [_features(current_tx, live_location)],
        dtype=float,
    )

    model = IsolationForest(
        n_estimators=160,
        contamination="auto",
        random_state=42,
    )

    model.fit(training_matrix)

    prediction = int(model.predict(current_vector)[0])
    decision = float(model.decision_function(current_vector)[0])

    is_anomaly = prediction == -1

    if is_anomaly:
        # Typical negative decision values are small in magnitude. Convert them to
        # an intuitive high risk score while keeping the result bounded.
        ml_risk = min(99.0, max(75.0, 75.0 + abs(decision) * 120.0))
        reason = (
            "Isolation Forest detected an anomalous transaction pattern "
            f"against {len(normal_history)} normal historical transactions"
        )
    else:
        ml_risk = min(45.0, max(5.0, 25.0 - decision * 80.0))
        reason = (
            "Isolation Forest considers the transaction consistent with the "
            f"user's learned pattern from {len(normal_history)} normal transactions"
        )

    return round(ml_risk, 1), is_anomaly, reason
