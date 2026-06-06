# Blood Warriors Backend

The Blood Warriors backend is an AI-powered blood donor-patient matching network. It uses FastAPI for the core API, PostgreSQL for data storage, Celery for asynchronous processing, SciPy for optimization (ILP), and AWS Bedrock (via Anthropic) for NLU intent parsing.

## Setup & Running Locally

1. **Configure Environment variables:**
   Copy the example config and fill in your Anthropic proxy details:
   ```bash
   cp .env.example .env
   ```

2. **Start the Stack (Docker):**
   ```bash
   docker compose up -d --build
   ```

3. **Run Database Migrations:**
   ```bash
   docker compose exec api alembic upgrade head
   ```

## API Documentation

FastAPI automatically generates an interactive Swagger UI. Once the app is running, you can access the full documentation at:
- **Swagger UI:** `http://localhost:8000/docs`

---

### 1. Import Data & Trigger Optimization

This endpoint takes a CSV file containing Donors and/or Patients. When Patients are uploaded, it will automatically kick off a background Celery task to run the SciPy ILP optimization engine to match patients with available donors based on spatial proximity (Haversine formula) and urgency rules.

- **Endpoint:** `POST /api/v1/admin/import`
- **Content-Type:** `multipart/form-data`
- **Request Body:** 
  - `file`: The CSV file containing the dataset.

**Example Request (cURL):**
```bash
curl -X POST "http://localhost:8000/api/v1/admin/import" \
  -H "accept: application/json" \
  -H "Content-Type: multipart/form-data" \
  -F "file=@donors.csv"
```

**Expected Response (200 OK):**
```json
{
  "message": "Successfully imported 8 rows",
  "donors_added": 8,
  "patients_added": 0
}
```

---

### 2. Donor Text Reply Webhook (NLU)

When a donor replies to an SMS or message (e.g., "I'm sick this week" or "I can come in tomorrow"), this webhook is called. It sends the message to AWS Bedrock to extract the donor's structured intent and automatically updates the match status in the database.

- **Endpoint:** `POST /api/v1/webhooks/text-reply`
- **Content-Type:** `application/json`

**Example Request:**
```json
{
  "phone": "555-0101",
  "message": "I am traveling and cannot donate today."
}
```

**Expected Response (200 OK):**
```json
{
  "status": "processed",
  "intent": "decline",
  "reason": "travel"
}
```

**Example cURL:**
```bash
curl -X POST "http://localhost:8000/api/v1/webhooks/text-reply" \
  -H "accept: application/json" \
  -H "Content-Type: application/json" \
  -d '{"phone":"555-0101","message":"I am traveling and cannot donate today."}'
```
