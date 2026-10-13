from collections import defaultdict
from datetime import datetime
from statistics import median

import numpy as np
from sklearn.linear_model import LinearRegression

from ..models import Transaction


MIN_TRAINING_MONTHS = 3


def _month_ordinal(year: int, month: int) -> int:
    return year * 12 + (month - 1)


def robust_upper_limit(amounts: list[float]) -> float:
    """
    Robust outlier threshold using Median + MAD.
    This is independent of fraud labels so false-positive fraud flags do not
    erase legitimate financial history from forecasting or charts.
    """
    if not amounts:
        return 0.0

    med = median(amounts)
    deviations = [abs(value - med) for value in amounts]
    mad = median(deviations)

    if mad == 0:
        return max(med * 4, med + 1000)

    return max(
        med + (6 * mad),
        med * 4,
    )


def build_monthly_spending_trend(
    transactions: list[Transaction],
    months_limit: int = 7,
) -> list[dict]:
    """
    Build a real month-wise spending series from PostgreSQL transaction rows.

    - debit transactions only
    - robustly removes extreme transaction amounts
    - does NOT depend on is_fraud because the fraud engine may intentionally
      flag prototype/history rows during testing
    """

    debit_rows = [
        tx for tx in transactions
        if tx.txn_type == "debit"
    ]

    if not debit_rows:
        return []

    amounts = [float(tx.amount) for tx in debit_rows]
    upper = robust_upper_limit(amounts)

    clean_rows = [
        tx for tx in debit_rows
        if float(tx.amount) <= upper
    ]

    monthly_totals: dict[tuple[int, int], float] = defaultdict(float)

    for tx in clean_rows:
        key = (tx.txn_date.year, tx.txn_date.month)
        monthly_totals[key] += float(tx.amount)

    ordered = sorted(monthly_totals)[-months_limit:]

    month_names = [
        "Jan", "Feb", "Mar", "Apr", "May", "Jun",
        "Jul", "Aug", "Sep", "Oct", "Nov", "Dec",
    ]

    return [
        {
            "m": month_names[month - 1],
            "v": round(monthly_totals[(year, month)], 2),
            "year": year,
        }
        for year, month in ordered
    ]


def predict_next_month_spending(
    transactions: list[Transaction],
) -> dict:
    """
    Forecast next calendar month's spending using Scikit-learn LinearRegression.

    - debit transactions only
    - current incomplete month excluded
    - robustly removes extreme transaction amounts
    - trains on completed monthly totals
    """

    now = datetime.utcnow()
    current_month = (now.year, now.month)

    completed_debits = []

    for tx in transactions:
        if tx.txn_type != "debit":
            continue

        key = (tx.txn_date.year, tx.txn_date.month)

        if key == current_month:
            continue

        completed_debits.append(tx)

    if not completed_debits:
        return {
            "prediction": 0.0,
            "ready": False,
            "method": "Linear Regression",
            "training_months": 0,
            "minimum_months": MIN_TRAINING_MONTHS,
            "r2": None,
            "filtered_transactions": 0,
            "reason": (
                f"Linear Regression is learning: "
                f"0/{MIN_TRAINING_MONTHS} completed months available"
            ),
        }

    historical_amounts = [
        float(tx.amount)
        for tx in completed_debits
    ]

    upper_limit = robust_upper_limit(historical_amounts)

    clean_history = [
        tx
        for tx in completed_debits
        if float(tx.amount) <= upper_limit
    ]

    filtered_count = len(completed_debits) - len(clean_history)

    monthly_totals: dict[tuple[int, int], float] = defaultdict(float)

    for tx in clean_history:
        key = (tx.txn_date.year, tx.txn_date.month)
        monthly_totals[key] += float(tx.amount)

    ordered_months = sorted(monthly_totals)

    if len(ordered_months) < MIN_TRAINING_MONTHS:
        return {
            "prediction": 0.0,
            "ready": False,
            "method": "Linear Regression",
            "training_months": len(ordered_months),
            "minimum_months": MIN_TRAINING_MONTHS,
            "r2": None,
            "filtered_transactions": filtered_count,
            "reason": (
                f"Linear Regression is learning: "
                f"{len(ordered_months)}/{MIN_TRAINING_MONTHS} "
                "completed months available"
            ),
        }

    x_values = np.array(
        [
            [_month_ordinal(year, month)]
            for year, month in ordered_months
        ],
        dtype=float,
    )

    y_values = np.array(
        [
            monthly_totals[key]
            for key in ordered_months
        ],
        dtype=float,
    )

    model = LinearRegression()
    model.fit(x_values, y_values)

    if now.month == 12:
        next_year = now.year + 1
        next_month = 1
    else:
        next_year = now.year
        next_month = now.month + 1

    target_x = np.array(
        [[_month_ordinal(next_year, next_month)]],
        dtype=float,
    )

    prediction = max(
        0.0,
        float(model.predict(target_x)[0]),
    )

    r2 = float(model.score(x_values, y_values))

    return {
        "prediction": round(prediction, 2),
        "ready": True,
        "method": "Linear Regression",
        "training_months": len(ordered_months),
        "minimum_months": MIN_TRAINING_MONTHS,
        "r2": round(r2, 3),
        "filtered_transactions": filtered_count,
        "reason": (
            f"Linear Regression forecast trained on "
            f"{len(ordered_months)} completed months; "
            f"{filtered_count} extreme historical transaction(s) "
            "excluded from forecasting"
        ),
    }
