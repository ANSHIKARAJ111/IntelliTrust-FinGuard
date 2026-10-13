from datetime import datetime, timedelta
from statistics import median

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..auth import current_user
from ..database import get_db
from ..models import Alert, BehaviorEvent, User
from ..schemas import BehaviorIn, BehaviorOut


router = APIRouter(prefix="/api/behavior", tags=["behavior"])


METRICS = (
    ("typing_speed_wpm", "Typing speed", 5.0),
    ("avg_key_interval_ms", "Key timing", 20.0),
    ("mouse_speed_px_s", "Mouse movement", 5.0),
    ("click_rate_per_min", "Click frequency", 1.0),
)


def relative_deviation(current: float, baseline: float, floor: float) -> float:
    return abs(current - baseline) / max(abs(baseline), floor)


def evaluate_behavior(body: BehaviorIn, history: list[BehaviorEvent]):
    # The first few observations form a personal baseline.
    if len(history) < 3:
        return 10.0, False, "Building behavioral baseline"

    baselines = {}
    for field, _, _ in METRICS:
        values = [float(getattr(event, field)) for event in history]
        baselines[field] = median(values)

    major = []
    moderate = []

    for field, label, floor in METRICS:
        current = float(getattr(body, field))
        baseline = float(baselines[field])
        deviation = relative_deviation(current, baseline, floor)

        if deviation >= 0.75:
            major.append(label)
        elif deviation >= 0.40:
            moderate.append(label)

    risk = 10.0 + (30.0 * len(major)) + (10.0 * len(moderate))

    # Very extreme automation-like values are suspicious even with a noisy baseline.
    if body.typing_speed_wpm >= 180 or (
        0 < body.avg_key_interval_ms <= 45
        and body.typing_speed_wpm >= 90
    ):
        risk += 25.0
        if "Typing speed" not in major:
            major.append("Typing speed")

    if body.click_rate_per_min >= 180:
        risk += 25.0
        if "Click frequency" not in major:
            major.append("Click frequency")

    risk = min(risk, 99.0)
    is_anomaly = risk >= 70.0 or len(major) >= 2

    if is_anomaly:
        changed = major + moderate
        reason = "Behavior mismatch detected: " + ", ".join(dict.fromkeys(changed))
    elif moderate or major:
        reason = "Minor behavior variation: " + ", ".join(dict.fromkeys(major + moderate))
    else:
        reason = "Behavior is consistent with the current user baseline"

    return risk, is_anomaly, reason


@router.post("", response_model=BehaviorOut)
def save_behavior(
    body: BehaviorIn,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    history = list(
        db.scalars(
            select(BehaviorEvent)
            .where(BehaviorEvent.user_id == user.id)
            .order_by(BehaviorEvent.captured_at.desc())
            .limit(10)
        )
    )

    risk, is_anomaly, reason = evaluate_behavior(body, history)

    event = BehaviorEvent(
        user_id=user.id,
        typing_speed_wpm=body.typing_speed_wpm,
        avg_key_interval_ms=body.avg_key_interval_ms,
        mouse_speed_px_s=body.mouse_speed_px_s,
        click_rate_per_min=body.click_rate_per_min,
        session_duration_s=body.session_duration_s,
        risk_score=risk,
        is_anomaly=is_anomaly,
        reason=reason,
    )
    db.add(event)

    # Avoid repeatedly punishing the same anomalous session every reporting interval.
    if is_anomaly:
        recent_cutoff = datetime.utcnow() - timedelta(minutes=2)
        recent_alert = db.scalar(
            select(Alert.id)
            .where(
                Alert.user_id == user.id,
                Alert.alert_type == "behavior",
                Alert.resolved == False,
                Alert.created_at >= recent_cutoff,
            )
            .limit(1)
        )

        if recent_alert is None:
            current_trust = user.trust_score if user.trust_score is not None else 100.0
            user.trust_score = max(0.0, current_trust - 5.0)
            db.add(
                Alert(
                    user_id=user.id,
                    transaction_id=None,
                    alert_type="behavior",
                    severity="high" if risk < 90 else "critical",
                    message=reason,
                )
            )

    db.commit()
    db.refresh(event)

    return BehaviorOut(
        risk_score=round(event.risk_score, 1),
        is_anomaly=event.is_anomaly,
        status=(
            "Building baseline"
            if len(history) < 3
            else "Anomaly"
            if event.is_anomaly
            else "Normal"
        ),
        reason=event.reason,
        baseline_samples=min(len(history) + 1, 10),
        trust_score=round(user.trust_score, 1),
    )


@router.get("/status")
def behavior_status(
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    latest = db.scalar(
        select(BehaviorEvent)
        .where(BehaviorEvent.user_id == user.id)
        .order_by(BehaviorEvent.captured_at.desc())
    )

    count = len(
        list(
            db.scalars(
                select(BehaviorEvent.id)
                .where(BehaviorEvent.user_id == user.id)
                .limit(10)
            )
        )
    )

    if latest is None:
        return {
            "status": "Waiting for activity",
            "risk_score": 0.0,
            "reason": "No behavioral samples captured yet",
            "baseline_samples": 0,
        }

    if count < 3:
        status = "Building baseline"
    else:
        status = "Anomaly" if latest.is_anomaly else "Normal"

    return {
        "status": status,
        "risk_score": round(latest.risk_score, 1),
        "reason": latest.reason,
        "baseline_samples": count,
    }
