from math import radians, sin, cos, asin, sqrt
from statistics import median


def haversine_km(lat1, lon1, lat2, lon2):
    earth_radius = 6371.0

    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)

    a = (
        sin(dlat / 2) ** 2
        + cos(radians(lat1))
        * cos(radians(lat2))
        * sin(dlon / 2) ** 2
    )

    return 2 * earth_radius * asin(sqrt(a))


def score_transaction(
    amount: float,
    prior_amounts: list[float],
    geo_distance_km: float | None = None,
):
    score = 5.0
    reasons = []

    # Median is more robust than mean when historical data already contains outliers.
    if prior_amounts:
        normal_amount = median(prior_amounts[-30:])
    else:
        normal_amount = max(amount, 1)

    normal_amount = max(normal_amount, 1)
    ratio = amount / normal_amount

    if ratio >= 10:
        score += 85
        reasons.append(
            f"Transaction amount is {ratio:.1f}x above normal spending"
        )
    elif ratio >= 6:
        score += 75
        reasons.append(
            f"Transaction amount is {ratio:.1f}x above normal spending"
        )
    elif ratio >= 4:
        score += 60
        reasons.append(
            f"Transaction amount is {ratio:.1f}x above normal spending"
        )
    elif ratio >= 2.5:
        score += 30
        reasons.append("Transaction amount is unusually high")

    if amount >= 50000:
        score += 20
        reasons.append("High-value transaction detected")

    if geo_distance_km is not None:
        if geo_distance_km > 1000:
            score += 35
            reasons.append(
                f"Transaction location differs by approximately "
                f"{geo_distance_km:.0f} km from current user location"
            )
        elif geo_distance_km > 500:
            score += 25
            reasons.append(
                f"Transaction location differs by approximately "
                f"{geo_distance_km:.0f} km from current user location"
            )

    score = min(score, 99.0)

    if not reasons:
        reasons.append("Transaction is within normal spending behaviour")

    return score, reasons
