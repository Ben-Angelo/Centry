# Sentry transaction simulator

A small, synthetic prototype that assesses simulated transactions, explains its risk signals, suggests a separate bank-policy action, and saves each assessment for history. It does not connect to banking systems or prove that coercion occurred. Suggested actions are advisory; high risk never automatically declines a transaction.

## Project layout

```text
backend/
  main.py            FastAPI routes
  risk_engine.py     Explainable risk scoring
  policy_engine.py   Separate suggested-action rules
  database.py        SQLAlchemy database configuration
  models.py          Persisted assessment model
  schemas.py         Request and response validation
frontend/
  index.html         Minimal transaction simulator
  app.js             API-backed form and history
  styles.css         Simple responsive styles
tests/
  test_risk_engine.py
  test_api.py
```

## Run locally

Python 3.10 or newer is required.

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m uvicorn backend.main:app --reload
```

Open <http://127.0.0.1:8000> for the dashboard and <http://127.0.0.1:8000/docs> for interactive API documentation.

The app uses a local SQLite database by default (`sentry.db`) so the full demo works without installing a database server. To use PostgreSQL, create a database, copy `.env.example` to `.env`, set `DATABASE_URL` to your PostgreSQL connection string, and restart the app. Tables are created at startup. Assessment records store the submitted transaction context, signals, score, risk level, and suggested action. Location is stored as coordinates; PostGIS/spatial queries are not part of this first version.

## API

- `POST /transactions/simulate` — validate, assess, recommend a policy action, persist, and return a simulated transaction.
- `GET /transactions` — return the most recent saved assessments (`limit` 1–500, `offset` 0 or greater).
- `GET /health` — check API and database connectivity.

The dashboard header shows whether the API and database are reachable. Its transaction log lists saved assessments; select **View** on a row to reopen that assessment and its signal explanations. The API writes assessment saves, duplicate IDs, persistence failures, and history reads to the server console without logging full transaction context.

The score combines unusual transaction amount, unfamiliar device, location distance from a supplied usual location, rapid recent activity, new payee, and repeated failed attempts. Each signal has an explanation. Missing information adds no risk points. The policy engine maps low to normal processing, medium to additional verification, and high to human authorization review plus a simulated fraud-team alert.

The bundled examples include a normal transaction, unusual contextual signals, and a high-risk ₦500,000 transfer. They are synthetic examples, not evidence of detection accuracy or real-world performance.

## Tests

```powershell
python -m pip install -r requirements-dev.txt
python -m unittest discover -s tests -v
```
