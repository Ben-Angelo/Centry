import unittest

from backend.policy_engine import recommend_action
from backend.risk_engine import assess_transaction


def transaction(**updates):
    value = {
        "amount": 20000,
        "history_avg_amount": 20000,
        "device_trusted": True,
        "location": {"latitude": 6.5244, "longitude": 3.3792},
        "usual_location": {"latitude": 6.5244, "longitude": 3.3792},
        "recent_transaction_count": 1,
        "new_payee": False,
        "failed_attempt_count": 0,
    }
    value.update(updates)
    return value


class RiskEngineTests(unittest.TestCase):
    def test_normal_transaction_has_low_risk(self):
        result = assess_transaction(transaction())
        self.assertEqual(result["risk_score"], 0)
        self.assertEqual(result["risk_level"], "low")

    def test_combined_anomalies_recommend_high_risk(self):
        result = assess_transaction(
            transaction(
                amount=500000,
                history_avg_amount=50000,
                device_trusted=False,
                location={"latitude": 6.5244, "longitude": 3.3792},
                usual_location={"latitude": 9.0765, "longitude": 7.3986},
                recent_transaction_count=6,
                new_payee=True,
                failed_attempt_count=3,
            )
        )
        self.assertEqual(result["risk_score"], 100)
        self.assertEqual(result["risk_level"], "high")
        signal_names = {signal["name"] for signal in result["detected_signals"]}
        self.assertIn("Unfamiliar device", signal_names)
        self.assertIn("Unusual location", signal_names)
        self.assertIn("Rapid recent activity", signal_names)
        self.assertIn("do not prove", result["notice"])

    def test_missing_context_does_not_add_points(self):
        result = assess_transaction(
            transaction(
                history_avg_amount=None,
                device_trusted=None,
                location=None,
                usual_location=None,
                recent_transaction_count=None,
                new_payee=None,
                failed_attempt_count=None,
            )
        )
        self.assertEqual(result["risk_score"], 0)
        self.assertTrue(
            any("unavailable" in signal["name"].lower() for signal in result["detected_signals"])
        )

    def test_combined_anomalies_can_recommend_medium_risk(self):
        result = assess_transaction(
            transaction(
                amount=70000,
                history_avg_amount=50000,
                device_trusted=False,
                recent_transaction_count=3,
                new_payee=True,
            )
        )
        self.assertEqual(result["risk_score"], 43)
        self.assertEqual(result["risk_level"], "medium")
        self.assertEqual(
            recommend_action(result["risk_level"])["code"],
            "additional_verification",
        )

    def test_policy_is_separate_and_high_risk_is_not_declined(self):
        action = recommend_action("high")
        self.assertEqual(action["code"], "authorization_review")
        self.assertTrue(action["notify_fraud_team"])
        self.assertIn("does not decline", action["description"])


if __name__ == "__main__":
    unittest.main()
