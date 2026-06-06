# Blood Match API Documentation

This document describes the exact endpoints, request formats, and response schemas for the Blood Warriors matching system backend.

The base URL for all endpoints is `http://localhost:8000/api/v1`.

---

## 1. Admin

### `POST /admin/import`
Uploads a CSV dataset of donors and patients. Automatically maps columns and triggers the optimization pipeline in the background.

- **Content-Type**: `multipart/form-data`
- **Request Body**: Form field `file` containing the `.csv` file.

**Sample Request (cURL):**
```bash
curl -X 'POST' \
  'http://localhost:8000/api/v1/admin/import' \
  -H 'accept: application/json' \
  -H 'Content-Type: multipart/form-data' \
  -F 'file=@Dataset.csv;type=text/csv'
```

**Success Response (200 OK):**
```json
{
  "status": "success",
  "message": "Imported 152 donors and 48 requests. Triggered optimization pipeline."
}
```

---

## 2. Donors

### `POST /donors/`
Registers a new blood donor in the system.

- **Content-Type**: `application/json`

**Sample Request Body:**
```json
{
  "name": "Alice Smith",
  "phone": "555-0101",
  "blood_group": "A+",
  "latitude": 40.7128,
  "longitude": -74.0060
}
```

**Success Response (201 Created):**
```json
{
  "id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "name": "Alice Smith",
  "phone": "555-0101",
  "blood_group": "A_POS",
  "latitude": 40.7128,
  "longitude": -74.006,
  "is_available": true
}
```

### `PUT /donors/{donor_id}`
Updates an existing donor's information. All fields are optional.

- **Content-Type**: `application/json`

**Sample Request Body:**
```json
{
  "is_available": false,
  "phone": "555-0202"
}
```

**Success Response (200 OK):**
```json
{
  "id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "name": "Alice Smith",
  "phone": "555-0202",
  "blood_group": "A_POS",
  "latitude": 40.7128,
  "longitude": -74.006,
  "is_available": false
}
```

---

## 3. Patients (Blood Requests)

### `POST /patients/`
Creates a new blood request for a patient in need.

- **Content-Type**: `application/json`

**Sample Request Body:**
```json
{
  "name": "Bob Jones",
  "blood_group": "A+",
  "latitude": 40.7138,
  "longitude": -74.0070,
  "urgency": "CRITICAL",
  "units": 2,
  "hospital": "Central Hospital"
}
```
*Note: `urgency` can be `"ROUTINE"`, `"URGENT"`, or `"CRITICAL"`. Based on urgency, a deadline is automatically calculated in the backend.*

**Success Response (201 Created):**
```json
{
  "id": "db10d54d-fae5-4aec-b5df-098edfa798c1",
  "patient_name": "Bob Jones",
  "blood_group": "A_POS",
  "latitude": 40.7138,
  "longitude": -74.007,
  "urgency": "CRITICAL",
  "units_required": 2,
  "hospital_name": "Central Hospital",
  "status": "OPEN"
}
```

### `PUT /patients/{patient_id}`
Updates an existing blood request. All fields are optional.

- **Content-Type**: `application/json`

**Sample Request Body:**
```json
{
  "status": "FULFILLED",
  "units": 3
}
```

**Success Response (200 OK):**
```json
{
  "id": "db10d54d-fae5-4aec-b5df-098edfa798c1",
  "patient_name": "Bob Jones",
  "blood_group": "A_POS",
  "latitude": 40.7138,
  "longitude": -74.007,
  "urgency": "CRITICAL",
  "units_required": 3,
  "hospital_name": "Central Hospital",
  "status": "FULFILLED"
}
```

---

## 4. Matching

### `GET /patients/{patient_id}/matches`
Synchronously queries the database, calculates the Haversine distance for all available donors of the matching blood group, and applies the Integer Linear Programming (ILP) scoring penalty logic to return the best 10 candidates.

- **Parameters**: `patient_id` (UUID) in the path.

**Sample Request (cURL):**
```bash
curl -X 'GET' \
  'http://localhost:8000/api/v1/patients/0a96a780-adfb-4731-a773-33966d2afe69/matches' \
  -H 'accept: application/json'
```

**Success Response (200 OK):**
```json
[
  {
    "donor_id": "005f71b2-fbf5-4b71-be79-72ae8717b8d1",
    "donor_name": "User_452d",
    "donor_phone": "555-0000",
    "blood_group": "A_POS",
    "distance_km": 4.12
  },
  {
    "donor_id": "83b92f9a-1f7c-4c3d-b2a8-1b2c3d4e5f6a",
    "donor_name": "User_1079",
    "donor_phone": "555-0000",
    "blood_group": "A_POS",
    "distance_km": 12.85
  }
]
```

### `POST /matches/{match_id}/response`
Receives a donor's response (from SMS/NLU webhook or frontend). Updates match state, automatically decreases required units for the patient, and triggers orchestration lock.

- **Parameters**: `match_id` (UUID) in the path.
- **Content-Type**: `application/json`

**Sample Request Body:**
```json
{
  "status": "ACCEPTED"
}
```
*Note: `status` must be either `"ACCEPTED"` or `"DECLINED"`.*

**Success Response (200 OK):**
```json
{
  "message": "Response recorded successfully",
  "match_status": "ACCEPTED"
}
```

---

## 5. Dashboard & Dashboard Orchestration

### `GET /donors/`
Retrieves a paginated list of registered donors along with their extended CSV parameters. Used primarily for populating the admin dashboard tables.

- **Parameters**: `skip` (int, default=0), `limit` (int, default=100) as query parameters.

**Sample Request (cURL):**
```bash
curl -X 'GET' \
  'http://localhost:8000/api/v1/donors/?skip=0&limit=50' \
  -H 'accept: application/json'
```

**Success Response (200 OK):**
```json
[
  {
    "id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
    "name": "Alice Smith",
    "phone": "555-0101",
    "blood_group": "A_POS",
    "latitude": 40.7128,
    "longitude": -74.006,
    "is_available": true,
    "last_contacted_date": "2023-01-01T00:00:00Z",
    "donations_till_date": 5,
    "eligibility_status": "ELIGIBLE",
    "account_status": "ACTIVE"
  }
]
```

### `WebSocket /ws/events`
Real-time unidirectional stream of orchestration events. Connect via WebSocket to receive push updates when donors are found, matches expire, or donors respond.

- **Connection URL**: `ws://localhost:8000/api/v1/ws/events`

**Emitted Events (JSON payloads sent to client):**

1. **Match Found**: Background ILP successfully mapped a donor to a patient request.
```json
{
  "event": "MATCH_FOUND",
  "data": {
    "request_id": "db10d54d...",
    "donor_id": "3fa85f64...",
    "distance_km": 4.12,
    "reason": "LLM approved based on 5 past donations."
  }
}
```

2. **Match Expired**: A pending match hit its urgency-based timeout without a response. The backend will automatically map 2 new donors.
```json
{
  "event": "MATCH_EXPIRED",
  "data": {
    "match_id": "a1b2c3d4...",
    "request_id": "db10d54d...",
    "donor_id": "3fa85f64..."
  }
}
```

3. **Donor Accepted**: A donor replied "Yes". Request units_required decreases by 1.
```json
{
  "event": "DONOR_ACCEPTED",
  "data": {
    "match_id": "a1b2c3d4...",
    "request_id": "db10d54d...",
    "donor_name": "Alice Smith",
    "units_remaining": 1
  }
}
```

4. **Donor Declined**: A donor replied "No".
```json
{
  "event": "DONOR_DECLINED",
  "data": {
    "match_id": "a1b2c3d4...",
    "request_id": "db10d54d...",
    "donor_name": "Alice Smith"
  }
}
```
