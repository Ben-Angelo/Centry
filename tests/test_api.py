import os
import unittest

os.environ["DATABASE_URL"] = "sqlite://"

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.database import Base, get_db
from backend.main import app
from backend.models import TransactionRecord

TEST_ENGINE = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestSession = sessionmaker(bind=TEST_ENGINE, autoflush=False, expire_on_commit=False)


def override_get_db():
    db = TestSession()
    try:
        yield db
    finally:
        db.close()


class TransactionApiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        Base.metadata.create_all(bind=TEST_ENGINE)
        app.dependency_overrides[get_db] = override_get_db
        cls.client = TestClient(app)

    @classmethod
    def tearDownClass(cls):
        cls.client.close()
        app.dependency_overrides.clear()
        Base.metadata.drop_all(bind=TEST_ENGINE)

    def setUp(self):
        with TestSession() as db:
            db.query(TransactionRecord).delete()
            db.commit()

    def test_health_reports_database_connection(self):
        response = self.client.get("/health")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "ok", "database": "connected"})

    def test_simulate_saves_assessment_and_history_returns_it(self):
        with self.assertLogs("sentry.transactions", level="INFO") as captured:
            response = self.client.post(
                "/transactions/simulate",
                json={
                    "transaction_id": "api-test-1",
                    "amount": 500000,
                    "currency": "NGN",
                    "history_avg_amount": 50000,
                    "device_trusted": False,
                    "location": {"latitude": 6.5244, "longitude": 3.3792},
                    "usual_location": {"latitude": 9.0765, "longitude": 7.3986},
                    "recent_transaction_count": 6,
                    "new_payee": True,
                    "failed_attempt_count": 3,
                },
            )
        self.assertEqual(response.status_code, 201)
        self.assertTrue(any("Assessment saved" in line for line in captured.output))
        result = response.json()
        self.assertEqual(result["risk_level"], "high")
        self.assertEqual(result["risk_score"], 100)
        self.assertEqual(result["suggested_action"]["code"], "authorization_review")

        history = self.client.get("/transactions")
        self.assertEqual(history.status_code, 200)
        self.assertEqual(len(history.json()), 1)
        self.assertEqual(history.json()[0]["transaction_id"], "api-test-1")
        self.assertEqual(history.json()[0]["transaction"]["amount"], 500000)

    def test_duplicate_transaction_id_returns_conflict(self):
        payload = {"transaction_id": "duplicate-test", "amount": 1000}
        self.assertEqual(self.client.post("/transactions/simulate", json=payload).status_code, 201)
        duplicate = self.client.post("/transactions/simulate", json=payload)
        self.assertEqual(duplicate.status_code, 409)

    def test_invalid_transaction_is_rejected(self):
        response = self.client.post(
            "/transactions/simulate",
            json={"amount": -10, "currency": "NGN"},
        )
        self.assertEqual(response.status_code, 422)


if __name__ == "__main__":
    unittest.main()
