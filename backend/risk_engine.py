from __future__ import annotations

from math import atan2, cos, radians, sin, sqrt
from typing import Any


def distance_km(first: dict[str, float], second: dict[str, float]) -> float:
    """Calculate the great-circle distance between two supplied coordinates."""
    earth_radius_km = 6371.0
    latitude_1 = radians(first["latitude"])
    latitude_2 = radians(second["latitude"])
    latitude_delta = latitude_2 - latitude_1
    longitude_delta = radians(second["longitude"] - first["longitude"])
    haversine = (
        sin(latitude_delta / 2) ** 2
        + cos(latitude_1) * cos(latitude_2) * sin(longitude_delta / 2) ** 2
    )
    return earth_radius_km * 2 * atan2(sqrt(haversine), sqrt(1 - haversine))


def _signal(
    name: str,
    points: int,
    reason: str,
    severity: str,
) -> dict[str, Any]:
    return {
        "name": name,
        "points": points,
        "reason": reason,
        "severity": severity,
    }


def assess_transaction(transaction: dict[str, Any]) -> dict[str, Any]:
    """Return an explainable risk score and detected signals for a transaction."""
    signals: list[dict[str, Any]] = []

    amount = float(transaction["amount"])
    history_average = transaction.get("history_avg_amount")
    if history_average is None or history_average <= 0:
        signals.append(
            _signal(
                "Amount history unavailable",
                0,
                "No usable transaction average was provided.",
                "info",
            )
        )
    else:
        ratio = amount / float(history_average)
        if ratio >= 5:
            signals.append(
                _signal(
                    "Much larger than usual",
                    25,
                    f"Amount is {ratio:.1f}x the supplied average.",
                    "high",
                )
            )
        elif ratio >= 2:
            signals.append(
                _signal(
                    "Larger than usual",
                    15,
                    f"Amount is {ratio:.1f}x the supplied average.",
                    "medium",
                )
            )
        else:
            signals.append(
                _signal(
                    "Amount near usual range",
                    0,
                    f"Amount is {ratio:.1f}x the supplied average.",
                    "info",
                )
            )

    device_trusted = transaction.get("device_trusted")
    if device_trusted is False:
        signals.append(
            _signal(
                "Unfamiliar device",
                25,
                "This device is not marked as familiar.",
                "high",
            )
        )
    elif device_trusted is True:
        signals.append(
            _signal(
                "Familiar device",
                0,
                "This device is marked as familiar.",
                "info",
            )
        )
    else:
        signals.append(
            _signal(
                "Device information unavailable",
                0,
                "Device familiarity was not supplied.",
                "info",
            )
        )

    current_location = transaction.get("location")
    usual_location = transaction.get("usual_location")
    if current_location is None or usual_location is None:
        signals.append(
            _signal(
                "Location context unavailable",
                0,
                "Current and usual locations are both needed for comparison.",
                "info",
            )
        )
    else:
        separation = distance_km(current_location, usual_location)
        if separation >= 50:
            signals.append(
                _signal(
                    "Unusual location",
                    25,
                    f"Current location is approximately {separation:.0f} km "
                    "from the supplied usual location.",
                    "high",
                )
            )
        elif separation >= 20:
            signals.append(
                _signal(
                    "Location differs from usual",
                    15,
                    f"Current location is approximately {separation:.0f} km "
                    "from the supplied usual location.",
                    "medium",
                )
            )
        else:
            signals.append(
                _signal(
                    "Location near usual",
                    0,
                    f"Current location is approximately {separation:.0f} km "
                    "from the supplied usual location.",
                    "info",
                )
            )

    recent_count = transaction.get("recent_transaction_count")
    if recent_count is None:
        signals.append(
            _signal(
                "Recent activity unavailable",
                0,
                "No recent transaction count was supplied.",
                "info",
            )
        )
    elif recent_count >= 5:
        signals.append(
            _signal(
                "Rapid recent activity",
                15,
                f"{recent_count} recent transactions were reported.",
                "high",
            )
        )
    elif recent_count >= 3:
        signals.append(
            _signal(
                "Elevated recent activity",
                8,
                f"{recent_count} recent transactions were reported.",
                "medium",
            )
        )
    else:
        signals.append(
            _signal(
                "Recent activity within range",
                0,
                f"{recent_count} recent transactions were reported.",
                "info",
            )
        )

    new_payee = transaction.get("new_payee")
    if new_payee is True:
        signals.append(
            _signal(
                "New payee",
                10,
                "The recipient is marked as new for this customer.",
                "medium",
            )
        )
    elif new_payee is None:
        signals.append(
            _signal("Payee history unavailable", 0, "Payee history was not supplied.", "info")
        )

    failed_attempts = transaction.get("failed_attempt_count")
    if failed_attempts is None:
        signals.append(
            _signal(
                "Attempt history unavailable",
                0,
                "No failed-attempt count was supplied.",
                "info",
            )
        )
    elif failed_attempts >= 3:
        signals.append(
            _signal(
                "Repeated failed attempts",
                10,
                f"{failed_attempts} failed attempts were reported.",
                "medium",
            )
        )
    else:
        signals.append(
            _signal(
                "No repeated failed attempts",
                0,
                f"{failed_attempts} failed attempts were reported.",
                "info",
            )
        )

    score = min(100, sum(signal["points"] for signal in signals))
    level = "high" if score >= 50 else "medium" if score >= 25 else "low"
    return {
        "risk_score": score,
        "risk_level": level,
        "detected_signals": signals,
        "notice": (
            "Signals are reasons for further assessment only. They do not prove "
            "coercion, fraud, or absence of customer consent."
        ),
    }
