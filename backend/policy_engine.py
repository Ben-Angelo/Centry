from __future__ import annotations

from typing import Any


def recommend_action(risk_level: str) -> dict[str, Any]:
    """Map an assessment level to a reversible, advisory bank action."""
    recommendations = {
        "low": {
            "code": "normal_processing",
            "label": "Normal processing",
            "description": "No additional Sentry step is recommended.",
            "notify_fraud_team": False,
        },
        "medium": {
            "code": "additional_verification",
            "label": "Additional verification",
            "description": "The bank may request an extra verification step.",
            "notify_fraud_team": False,
        },
        "high": {
            "code": "authorization_review",
            "label": "Authorization review",
            "description": (
                "Refer for human review and alert the simulated fraud team. "
                "This recommendation does not decline the transaction."
            ),
            "notify_fraud_team": True,
        },
    }
    try:
        return recommendations[risk_level]
    except KeyError as exc:
        raise ValueError(f"Unsupported risk level: {risk_level}") from exc
