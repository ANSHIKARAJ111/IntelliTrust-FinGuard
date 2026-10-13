# IntelliTrust FinGuard — Consolidated 50% Implementation

This is the single consolidated project folder containing the completed first 50% prototype.

## Implemented
- React.js fintech/security dashboard
- FastAPI backend
- PostgreSQL + SQLAlchemy
- Register/Login with JWT
- bcrypt/Passlib password hashing
- CSV bulk transaction import
- Duplicate transaction detection
- Transaction simulator
- Transaction categorization
- Dynamic trust score
- Fraud alerts
- Live browser geolocation
- Geographic risk analysis using Haversine distance
- Behavioral monitoring (typing timing, mouse movement, click frequency, session activity)
- Scikit-learn Isolation Forest anomaly detection
- Scikit-learn Linear Regression expense prediction
- Real PostgreSQL month-wise spending graph
- Explainable fraud reasons
- ML transparency (training months and R²)

## Important
The `.env` file with your real PostgreSQL password is intentionally NOT included.
Create it locally from `.env.example`.

Example:

```env
DATABASE_URL=postgresql+psycopg://postgres:YOUR_URL_ENCODED_PASSWORD@localhost:5432/finguard
JWT_SECRET=replace-with-a-strong-local-secret
FRONTEND_ORIGIN=http://localhost:5173
```

If a password contains `#`, encode it as `%23` inside DATABASE_URL.

## Backend

```cmd
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Swagger:
`http://127.0.0.1:8000/docs`

## Frontend

```cmd
cd frontend
npm install
npm run dev
```

Open:
`http://localhost:5173`

## PostgreSQL

Create the database once:

```sql
CREATE DATABASE finguard;
```

## Demo data

Use:
- `demo_data/sample_statement.csv`
- `demo_data/historical_spending.csv`

The historical file provides multiple completed months so the Linear Regression model can demonstrate forecasting.

## Main demo flow

Login → import historical transactions → dashboard → simulate transaction → Isolation Forest + rule/geo analysis → fraud alert → trust score update → behavior monitoring → explainability/model-transparency section.
