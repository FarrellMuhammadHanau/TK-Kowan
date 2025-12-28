# Kowan Attendance System - Complete API Documentation

**Version:** 1.0  
**Last Updated:** December 28, 2025

## Deployed Services

| Service | Base URL |
|---------|----------|
| Auth Service | `http://13.223.192.142:8000` |
| Attendee Service | `http://18.214.134.23:8000` |
| Room Service | `http://54.162.202.203:8000` |
| Class Service | `http://3.225.88.17:8000` |
| Schedule Service | `http://35.171.134.244:8000` |
| Attendance Service | `http://100.28.146.147:8000` |

## Test Credentials

### Institution Login
```json
{
  "name": "Fasilkom Universitas Indonesia",
  "password": "123"
}
```

### Test Students
```json
[
  {
    "name": "Farrell Muhammad Hanau",
    "code": "2206081566",
    "secret": "TVVJ7JXT"
  },
  {
    "name": "Maulana Seto",
    "code": "2206081471",
    "secret": "8UVA2TOU"
  },
  {
    "name": "Arya Lesmana",
    "code": "2206081603",
    "secret": "HXXN63XZ"
  },
  {
    "name": "Mariano Gerardus Senduk",
    "code": "2206814236",
    "secret": "MK3BMAI4"
  },
  {
    "name": "Cyrilus Yodha Maheswara",
    "code": "2206083722",
    "secret": "QIMOL30S"
  }
]
```

---

## Authentication & Authorization

The system uses JWT (JSON Web Tokens) with two distinct roles:

### Token Types

#### 1. Admin Token (`jwt_admin`)
- **Purpose:** Full administrative access to all services
- **Issued By:** Auth Service (`POST /login`)
- **Payload:**
  ```json
  {
    "sub": "institution_id",
    "role": "admin"
  }
  ```
- **Usage:** Required for all CRUD operations across services

#### 2. Attendance Token (`jwt_attendance`)
- **Purpose:** Limited access for attendance submission only
- **Issued By:** Attendance Service (`POST /attendance/attendance-credential`)
- **Payload:**
  ```json
  {
    "sub": "institution_id",
    "role": "attendee",
    "room": "room_id"
  }
  ```
- **Usage:** Used by tapping machines/kiosks to submit attendance
- **Security:** Each token is bound to a specific room. Token issued for Room A cannot be used to submit attendance for Room B.

### Authorization Header Format
```
Authorization: Bearer <token>
```

---

## A. Auth Service

Base URL: `http://13.223.192.142:8000`

### 1. Register Institution

**Endpoint:** `POST /register`

**Description:** Register a new institution/tenant in the system.

**Request Body:**
```json
{
  "name": "string",
  "password": "string"
}
```

**Response:** `200 OK`
```json
{
  "message": "registered"
}
```

**Error Responses:**
- `400 Bad Request` - Institution already exists
```json
{
  "detail": "Institution already exists"
}
```

**Example:**
```bash
curl -X POST http://13.223.192.142:8000/register \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Fasilkom Universitas Indonesia",
    "password": "123"
  }'
```

---

### 2. Login Institution

**Endpoint:** `POST /login`

**Description:** Authenticate and receive an admin JWT token.

**Request Body:**
```json
{
  "name": "string",
  "password": "string"
}
```

**Response:** `200 OK`
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}
```

**Error Responses:**
- `401 Unauthorized` - Invalid credentials
```json
{
  "detail": "invalid credentials"
}
```

**Example:**
```bash
curl -X POST http://13.223.192.142:8000/login \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Fasilkom Universitas Indonesia",
    "password": "123"
  }'
```

---

## B. Attendee Service

Base URL: `http://18.214.134.23:8000`

### 1. Create Attendees (Bulk)

**Endpoint:** `POST /attendees`

**Authorization:** `Bearer jwt_admin`

**Description:** Create one or more students. System automatically generates a unique secret (password) for each student.

**Request Body:**
```json
{
  "attendees": [
    {
      "code": "string",
      "name": "string"
    }
  ]
}
```

**Response:** `200 OK`
```json
[
  {
    "code": "2206083722",
    "secret": "QIMOL30S"
  }
]
```

**Notes:**
- `code` is typically the student ID/NPM
- `secret` is auto-generated (8 characters, uppercase alphanumeric)
- The secret should be provided to students for attendance tapping

**Error Responses:**
- `400 Bad Request` - Attendee code already exists
- `401 Unauthorized` - Invalid or missing token
- `403 Forbidden` - Token does not have admin role

**Example:**
```bash
curl -X POST http://18.214.134.23:8000/attendees \
  -H "Authorization: Bearer YOUR_ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "attendees": [
      {
        "code": "2206083722",
        "name": "Cyrilus Yodha Maheswara"
      }
    ]
  }'
```

---

### 2. Get All Attendees

**Endpoint:** `GET /attendees`

**Authorization:** `Bearer jwt_admin`

**Description:** Retrieve all students for the authenticated institution.

**Response:** `200 OK`
```json
[
  {
    "code": "2206083722",
    "name": "Cyrilus Yodha Maheswara"
  },
  {
    "code": "2206081566",
    "name": "Farrell Muhammad Hanau"
  }
]
```

**Notes:**
- Secrets are NOT returned for security reasons
- Returns only attendees belonging to the authenticated institution

**Example:**
```bash
curl -X GET http://18.214.134.23:8000/attendees \
  -H "Authorization: Bearer YOUR_ADMIN_TOKEN"
```

---

### 3. Validate Attendee Existence (Batch)

**Endpoint:** `POST /attendees/validate-existence`

**Authorization:** `Bearer jwt_admin`

**Description:** Verify if one or more student codes exist. Used by Class Service when enrolling students.

**Request Body:**
```json
{
  "attendees": [
    {
      "code": "string"
    }
  ]
}
```

**Response:** `200 OK`
```json
{
  "valid": true,
  "attendees": [
    {
      "code": "2206083722",
      "name": "Cyrilus Yodha Maheswara"
    }
  ]
}
```

**Notes:**
- `valid: true` only if ALL provided codes exist
- Returns details of found attendees when valid

**Invalid Response:**
```json
{
  "valid": false
}
```

**Example:**
```bash
curl -X POST http://18.214.134.23:8000/attendees/validate-existence \
  -H "Authorization: Bearer YOUR_ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "attendees": [
      {"code": "2206083722"},
      {"code": "2206081566"}
    ]
  }'
```

---

### 4. Validate Attendee Secret

**Endpoint:** `POST /attendees/validate-secret`

**Authorization:** `Bearer jwt_admin`

**Description:** Verify student credentials (code + secret). Used by Attendance Service during tap-in.

**Request Body:**
```json
{
  "code": "string",
  "secret": "string"
}
```

**Response (Valid):** `200 OK`
```json
{
  "valid": true,
  "code": "2206083722",
  "name": "Cyrilus Yodha Maheswara"
}
```

**Response (Invalid):** `200 OK`
```json
{
  "valid": false
}
```

**Example:**
```bash
curl -X POST http://18.214.134.23:8000/attendees/validate-secret \
  -H "Authorization: Bearer YOUR_ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "code": "2206083722",
    "secret": "QIMOL30S"
  }'
```

---

## C. Room Service

Base URL: `http://54.162.202.203:8000`

### 1. Create Rooms (Bulk)

**Endpoint:** `POST /rooms`

**Authorization:** `Bearer jwt_admin`

**Description:** Create one or more rooms/classrooms.

**Request Body:**
```json
{
  "rooms": [
    {
      "name": "string"
    }
  ]
}
```

**Response:** `200 OK`
```json
{
  "message": "successful"
}
```

**Example:**
```bash
curl -X POST http://54.162.202.203:8000/rooms \
  -H "Authorization: Bearer YOUR_ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "rooms": [
      {"name": "Lab 1201"},
      {"name": "Lecture Hall A"}
    ]
  }'
```

---

### 2. Get All Rooms

**Endpoint:** `GET /rooms`

**Authorization:** `Bearer jwt_admin`

**Description:** Retrieve all rooms for the authenticated institution.

**Response:** `200 OK`
```json
[
  {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "name": "Lab 1201"
  },
  {
    "id": "650e8400-e29b-41d4-a716-446655440001",
    "name": "Lecture Hall A"
  }
]
```

**Example:**
```bash
curl -X GET http://54.162.202.203:8000/rooms \
  -H "Authorization: Bearer YOUR_ADMIN_TOKEN"
```

---

### 3. Validate Room Existence (Batch)

**Endpoint:** `POST /rooms/validate-existence`

**Authorization:** `Bearer jwt_admin`

**Description:** Verify if one or more room IDs exist. Used by Schedule Service when creating schedules.

**Request Body:**
```json
{
  "rooms": [
    {
      "id": "string"
    }
  ]
}
```

**Response (Valid):** `200 OK`
```json
{
  "valid": true,
  "rooms": [
    {
      "id": "550e8400-e29b-41d4-a716-446655440000",
      "name": "Lab 1201"
    }
  ]
}
```

**Response (Invalid):** `200 OK`
```json
{
  "valid": false,
  "rooms": []
}
```

**Example:**
```bash
curl -X POST http://54.162.202.203:8000/rooms/validate-existence \
  -H "Authorization: Bearer YOUR_ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "rooms": [
      {"id": "550e8400-e29b-41d4-a716-446655440000"}
    ]
  }'
```

---

## D. Class Service

Base URL: `http://3.225.88.17:8000`

### 1. Create Classes (Bulk)

**Endpoint:** `POST /classes/create`

**Authorization:** `Bearer jwt_admin`

**Description:** Create one or more classes/courses.

**Request Body:**
```json
{
  "classes": [
    {
      "code": "string",
      "name": "string"
    }
  ]
}
```

**Response:** `200 OK`
```json
{
  "message": "successful"
}
```

**Notes:**
- `code` is typically the course code (e.g., "CS101", "CSGE602022")
- Duplicate codes within the same institution are skipped

**Example:**
```bash
curl -X POST http://3.225.88.17:8000/classes/create \
  -H "Authorization: Bearer YOUR_ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "classes": [
      {
        "code": "CSGE602022",
        "name": "Computer Networks"
      }
    ]
  }'
```

---

### 2. Get All Classes

**Endpoint:** `GET /classes`

**Authorization:** `Bearer jwt_admin`

**Description:** Retrieve all classes for the authenticated institution.

**Response:** `200 OK`
```json
[
  {
    "id": "750e8400-e29b-41d4-a716-446655440000",
    "code": "CSGE602022",
    "name": "Computer Networks"
  }
]
```

**Example:**
```bash
curl -X GET http://3.225.88.17:8000/classes \
  -H "Authorization: Bearer YOUR_ADMIN_TOKEN"
```

---

### 3. Add Attendees to Class (Enrollment)

**Endpoint:** `POST /classes/add-attendees`

**Authorization:** `Bearer jwt_admin`

**Description:** Enroll one or more students into a class. Validates student existence via Attendee Service.

**Request Body:**
```json
{
  "class_id": "string",
  "attendees": [
    {
      "code": "string"
    }
  ]
}
```

**Response:** `200 OK`
```json
{
  "message": "successful"
}
```

**Error Responses:**
- `404 Not Found` - Class not found
- `400 Bad Request` - One or more attendees invalid
- `503 Service Unavailable` - Attendee service unavailable

**Notes:**
- Internally calls Attendee Service to validate all student codes
- Duplicate enrollments are skipped automatically

**Example:**
```bash
curl -X POST http://3.225.88.17:8000/classes/add-attendees \
  -H "Authorization: Bearer YOUR_ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "class_id": "750e8400-e29b-41d4-a716-446655440000",
    "attendees": [
      {"code": "2206083722"},
      {"code": "2206081566"}
    ]
  }'
```

---

### 4. Get Class Attendees

**Endpoint:** `GET /classes/{class_id}/attendees`

**Authorization:** `Bearer jwt_admin`

**Description:** Retrieve the list of all students enrolled in a specific class. Fetches student details from Attendee Service.

**Path Parameters:**
- `class_id` (string) - The UUID of the class

**Response:** `200 OK`
```json
{
  "attendees": [
    {
      "code": "2206083722",
      "name": "Cyrilus Yodha Maheswara"
    },
    {
      "code": "2206081566",
      "name": "Farrell Muhammad Hanau"
    }
  ]
}
```

**Error Responses:**
- `404 Not Found` - Class not found
```json
{
  "detail": "Class not found"
}
```

**Notes:**
- Returns empty list if no attendees enrolled
- Calls Attendee Service internally to get student names
- Falls back to using codes as names if Attendee Service unavailable

**Example:**
```bash
curl -X GET http://3.225.88.17:8000/classes/750e8400-e29b-41d4-a716-446655440000/attendees \
  -H "Authorization: Bearer YOUR_ADMIN_TOKEN"
```

---

### 5. Validate Attendee in Class

**Endpoint:** `POST /classes/validate-attendee`

**Authorization:** `Bearer jwt_admin`

**Description:** Check if a specific student is enrolled in a class. Used by Attendance Service.

**Request Body:**
```json
{
  "class_id": "string",
  "attendee_code": "string"
}
```

**Response (Valid):** `200 OK`
```json
{
  "valid": true,
  "class_attendee_id": "850e8400-e29b-41d4-a716-446655440000",
  "class_name": "Computer Networks"
}
```

**Response (Invalid):** `200 OK`
```json
{
  "valid": false
}
```

**Notes:**
- Returns `class_attendee_id` (enrollment record ID) for attendance tracking
- Returns `class_name` for display purposes

**Example:**
```bash
curl -X POST http://3.225.88.17:8000/classes/validate-attendee \
  -H "Authorization: Bearer YOUR_ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "class_id": "750e8400-e29b-41d4-a716-446655440000",
    "attendee_code": "2206083722"
  }'
```

---

### 5. Validate Class Existence (Batch)

**Endpoint:** `POST /classes/validate-existence`

**Authorization:** `Bearer jwt_admin`

**Description:** Verify if one or more class IDs exist. Used by Schedule Service.

**Request Body:**
```json
{
  "classes": [
    {
      "id": "string"
    }
  ]
}
```

**Response (Valid):** `200 OK`
```json
{
  "valid": true,
  "classes": [
    {
      "id": "750e8400-e29b-41d4-a716-446655440000",
      "name": "Computer Networks"
    }
  ]
}
```

**Response (Invalid):** `200 OK`
```json
{
  "valid": false,
  "classes": []
}
```

**Example:**
```bash
curl -X POST http://3.225.88.17:8000/classes/validate-existence \
  -H "Authorization: Bearer YOUR_ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "classes": [
      {"id": "750e8400-e29b-41d4-a716-446655440000"}
    ]
  }'
```

---

## E. Schedule Service

Base URL: `http://35.171.134.244:8000`

### 1. Create Schedules (Bulk)

**Endpoint:** `POST /schedules/create`

**Authorization:** `Bearer jwt_admin`

**Description:** Create one or more class schedules. Validates rooms and classes, checks for conflicts.

**Request Body:**
```json
{
  "schedules": [
    {
      "room_id": "string",
      "class_id": "string",
      "day": 1,
      "start_time": 800,
      "end_time": 1000
    }
  ]
}
```

**Field Specifications:**
- `day`: Integer (1-7, where 1 = Monday, 7 = Sunday)
- `start_time`: Integer in HHMM format (e.g., 800 = 08:00, 1330 = 13:30)
- `end_time`: Integer in HHMM format

**Response:** `200 OK`
```json
{
  "message": "successful"
}
```

**Error Responses:**
- `400 Bad Request` - Invalid room or class ID
```json
{
  "detail": "Invalid Room ID: <room_id>"
}
```
- `409 Conflict` - Time conflict detected
```json
{
  "detail": "Room Lab 1201 is already booked on Day 1 between 800-1000"
}
```

**Notes:**
- Internally calls Room Service and Class Service to validate IDs
- Caches room_name and class_name for performance
- Prevents double-booking of rooms at the same time

**Example:**
```bash
curl -X POST http://35.171.134.244:8000/schedules/create \
  -H "Authorization: Bearer YOUR_ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "schedules": [
      {
        "room_id": "550e8400-e29b-41d4-a716-446655440000",
        "class_id": "750e8400-e29b-41d4-a716-446655440000",
        "day": 1,
        "start_time": 800,
        "end_time": 1000
      }
    ]
  }'
```

---

### 2. Get All Schedules

**Endpoint:** `GET /schedules`

**Authorization:** `Bearer jwt_admin`

**Description:** Retrieve all schedules for the authenticated institution.

**Response:** `200 OK`
```json
{
  "schedules": [
    {
      "id": "950e8400-e29b-41d4-a716-446655440000",
      "room_id": "550e8400-e29b-41d4-a716-446655440000",
      "room_name": "Lab 1201",
      "class_id": "750e8400-e29b-41d4-a716-446655440000",
      "class_name": "Computer Networks",
      "day": 1,
      "start_time": 800,
      "end_time": 1000
    }
  ]
}
```

**Notes:**
- Includes both IDs and cached names for convenience
- `day`: 1 = Monday, 2 = Tuesday, ..., 7 = Sunday
- Times are in HHMM integer format

**Example:**
```bash
curl -X GET http://35.171.134.244:8000/schedules \
  -H "Authorization: Bearer YOUR_ADMIN_TOKEN"
```

---

### 3. Validate Schedule Availability

**Endpoint:** `POST /schedules/validate-availability`

**Authorization:** `Bearer jwt_admin`

**Description:** Check if rooms are available at specified times. Returns conflicts if any exist.

**Request Body:**
```json
{
  "schedules": [
    {
      "room_id": "string",
      "day": 1,
      "start_time": 800,
      "end_time": 1000
    }
  ]
}
```

**Response (Available):** `200 OK`
```json
{
  "valid": true,
  "conflicts": []
}
```

**Response (Conflicts Found):** `200 OK`
```json
{
  "valid": false,
  "conflicts": [
    {
      "room_id": "550e8400-e29b-41d4-a716-446655440000",
      "conflict_with_class": "Computer Networks"
    }
  ]
}
```

**Notes:**
- Useful for checking availability before creating schedules
- Detects overlapping time ranges using overlap logic: `(StartA < EndB) AND (EndA > StartB)`

**Example:**
```bash
curl -X POST http://35.171.134.244:8000/schedules/validate-availability \
  -H "Authorization: Bearer YOUR_ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "schedules": [
      {
        "room_id": "550e8400-e29b-41d4-a716-446655440000",
        "day": 1,
        "start_time": 900,
        "end_time": 1100
      }
    ]
  }'
```

---

## F. Attendance Service

Base URL: `http://100.28.146.147:8000`

### 1. Get Attendance Credential

**Endpoint:** `POST /attendance/attendance-credential`

**Authorization:** `Bearer jwt_admin`

**Description:** Generate a room-specific attendance token for tapping machines/kiosks. Each token is cryptographically bound to a specific room. Admin-only endpoint.

**Request Body:**
```json
{
  "room_id": "string"
}
```

**Response:** `200 OK`
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}
```

**Error Responses:**
- `403 Forbidden` - Not an admin token
```json
{
  "detail": "Admin access required"
}
```

**Notes:**
- The returned token has role `attendee` with room binding (limited permissions)
- Each tapping machine/kiosk gets a unique token for its specific room
- Token includes `room` claim in JWT payload, preventing cross-room usage
- This token should be hardcoded into tapping machines during deployment
- Cannot be used for administrative operations
- If a token is compromised, only the specific room is affected

**Example:**
```bash
curl -X POST http://100.28.146.147:8000/attendance/attendance-credential \
  -H "Authorization: Bearer YOUR_ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"room_id": "550e8400-e29b-41d4-a716-446655440000"}'
```

---

### 2. Submit Presence (Tap In)

**Endpoint:** `POST /attendance/presence`

**Authorization:** `Bearer jwt_attendance` (or `jwt_admin`)

**Description:** Record student attendance. This is the main orchestrator endpoint that validates credentials, schedule, and enrollment before recording attendance. The room is determined from the JWT token, not the request body.

**Request Body:**
```json
{
  "attendee_code": "string",
  "attendee_secret": "string"
}
```

**Response:** `200 OK`
```json
{
  "message": "successful",
  "student_name": "Cyrilus Yodha Maheswara",
  "class_name": "Computer Networks"
}
```

**Error Responses:**
- `400 Bad Request` - Token missing room information
```json
{
  "detail": "Token does not contain room information"
}
```
- `400 Bad Request` - Invalid secret/code
```json
{
  "detail": "Invalid attendee secret or code"
}
```
- `400 Bad Request` - No class scheduled
```json
{
  "detail": "No class scheduled in this room right now"
}
```
- `400 Bad Request` - Not enrolled
```json
{
  "detail": "Student is not enrolled in this class"
}
```
- `403 Forbidden` - Invalid token role
```json
{
  "detail": "Invalid role for submission"
}
```
- `503 Service Unavailable` - External service failure

**Orchestration Flow:**
1. **Extract Room from Token** → Room ID is extracted from JWT payload (cryptographically verified)
2. **Validate Student Credentials** → Calls Attendee Service `/attendees/validate-secret`
3. **Find Active Schedule** → Calls Schedule Service `/schedules` and filters by current time/room
4. **Verify Enrollment** → Calls Class Service `/classes/validate-attendee`
5. **Record Attendance** → Saves to database with timestamp

**Notes:**
- Room ID is extracted from the JWT token, not the request body
- Each kiosk token is bound to a specific room (security measure)
- Automatically detects current day/time using server clock
- Day detection: 1 = Monday (ISO 8601 weekday)
- Time detection: Current time in HHMM format
- Attendance is recorded with the exact timestamp
- Returns student and class names for display on kiosk
- Student doesn't need to know which room they're in

**Example:**
```bash
curl -X POST http://100.28.146.147:8000/attendance/presence \
  -H "Authorization: Bearer YOUR_ATTENDANCE_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "attendee_code": "2206083722",
    "attendee_secret": "QIMOL30S"
  }'
```

---

## Common Error Responses

All services may return the following standard error responses:

### 401 Unauthorized
```json
{
  "detail": "Invalid token"
}
```
**Cause:** Missing, expired, or malformed JWT token

### 403 Forbidden
```json
{
  "detail": "Admin access required"
}
```
**Cause:** Token does not have required role (e.g., using attendance token for admin endpoint)

### 422 Unprocessable Entity
```json
{
  "detail": [
    {
      "loc": ["body", "field_name"],
      "msg": "field required",
      "type": "value_error.missing"
    }
  ]
}
```
**Cause:** Request body validation failed (missing or invalid fields)

### 500 Internal Server Error
```json
{
  "detail": "Internal server error"
}
```
**Cause:** Unexpected server-side error

---

## Database Schema Reference

### Auth Service
**Table: Institution**
- `id` (UUID, PK)
- `name` (String, Unique)
- `password_hash` (String)

### Attendee Service
**Table: Attendee**
- `institution_id` (UUID, PK - Composite)
- `code` (String, PK - Composite)
- `name` (String)
- `secret_hash` (String)

### Room Service
**Table: Room**
- `id` (UUID, PK)
- `institution_id` (UUID)
- `room_name` (String)

### Class Service
**Table: Class**
- `id` (UUID, PK)
- `institution_id` (UUID)
- `code` (String)
- `name` (String)

**Table: ClassAttendee**
- `id` (UUID, PK)
- `institution_id` (UUID)
- `class_id` (UUID, FK → Class.id)
- `attendee_code` (String)

### Schedule Service
**Table: Schedule**
- `id` (UUID, PK)
- `institution_id` (UUID)
- `room_id` (UUID)
- `room_name` (String, cached)
- `class_id` (UUID)
- `class_name` (String, cached)
- `day` (Integer, 1-7)
- `start_time` (Integer, HHMM format)
- `end_time` (Integer, HHMM format)

### Attendance Service
**Table: Attendance**
- `id` (UUID, PK)
- `institution_id` (UUID)
- `class_attendee_id` (UUID)
- `schedule_id` (UUID)
- `class_name` (String, cached)
- `room_name` (String, cached)
- `created_at` (Timestamp, auto-generated)

---

## Workflow Examples

### Complete Setup Flow

#### Step 1: Register & Login
```bash
# Register institution
curl -X POST http://13.223.192.142:8000/register \
  -H "Content-Type: application/json" \
  -d '{"name": "My University", "password": "secure123"}'

# Login and get admin token
TOKEN=$(curl -X POST http://13.223.192.142:8000/login \
  -H "Content-Type: application/json" \
  -d '{"name": "My University", "password": "secure123"}' \
  | jq -r '.access_token')
```

#### Step 2: Create Students
```bash
curl -X POST http://18.214.134.23:8000/attendees \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "attendees": [
      {"code": "12345", "name": "John Doe"},
      {"code": "67890", "name": "Jane Smith"}
    ]
  }'
# Save the returned secrets!
```

#### Step 3: Create Rooms
```bash
ROOM_RESPONSE=$(curl -X POST http://54.162.202.203:8000/rooms \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"rooms": [{"name": "Room 101"}]}')

# Get room ID
ROOM_ID=$(curl -X GET http://54.162.202.203:8000/rooms \
  -H "Authorization: Bearer $TOKEN" \
  | jq -r '.[0].id')
```

#### Step 4: Create Classes
```bash
curl -X POST http://3.225.88.17:8000/classes/create \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "classes": [
      {"code": "CS101", "name": "Introduction to Programming"}
    ]
  }'

# Get class ID
CLASS_ID=$(curl -X GET http://3.225.88.17:8000/classes \
  -H "Authorization: Bearer $TOKEN" \
  | jq -r '.[0].id')
```

#### Step 5: Enroll Students
```bash
curl -X POST http://3.225.88.17:8000/classes/add-attendees \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d "{
    \"class_id\": \"$CLASS_ID\",
    \"attendees\": [
      {\"code\": \"12345\"},
      {\"code\": \"67890\"}
    ]
  }"
```

#### Step 6: Create Schedule
```bash
# Monday (day=1) from 08:00 to 10:00
curl -X POST http://35.171.134.244:8000/schedules/create \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d "{
    \"schedules\": [{
      \"room_id\": \"$ROOM_ID\",
      \"class_id\": \"$CLASS_ID\",
      \"day\": 1,
      \"start_time\": 800,
      \"end_time\": 1000
    }]
  }"
```

#### Step 7: Get Attendance Token for Kiosk
```bash
# Get room-specific token for the kiosk in Room 101
ATTENDANCE_TOKEN=$(curl -X POST http://100.28.146.147:8000/attendance/attendance-credential \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d "{\"room_id\": \"$ROOM_ID\"}" \
  | jq -r '.access_token')

# This token is now bound to $ROOM_ID and should be hardcoded in that room's kiosk
```

#### Step 8: Student Taps In
```bash
# Student with code "12345" and secret (from Step 2) taps in
# Note: No room_id needed - it's in the token!
curl -X POST http://100.28.146.147:8000/attendance/presence \
  -H "Authorization: Bearer $ATTENDANCE_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "attendee_code": "12345",
    "attendee_secret": "ABC12XYZ"
  }'
```

---

## Security Considerations

1. **JWT Secret:** All services share the same JWT secret (`EfEmEitch123` by default). In production, use a strong, randomly generated secret via environment variable `JWT_SECRET`.

2. **Password Hashing:** Passwords and secrets are hashed using SHA-256 before storage.

3. **Token Expiration:** Current implementation does not include token expiration. Consider adding `exp` claim in production.

4. **HTTPS:** Production deployments should use HTTPS/TLS for all communications.

5. **Rate Limiting:** Consider implementing rate limiting on authentication and attendance endpoints.

6. **Secret Distribution:** Student secrets should be distributed securely (e.g., via email, student portal).

---

## Performance Optimizations

1. **Denormalization:** Schedule Service caches `room_name` and `class_name` to avoid repeated cross-service calls.

2. **Batch Operations:** Most create endpoints support bulk operations to reduce network overhead.

3. **Connection Pooling:** Services use SQLAlchemy async sessions with connection pooling.

---

## Development & Testing

### Environment Variables

Each service supports the following environment variables:

```bash
# JWT Configuration
JWT_SECRET=EfEmEitch123
JWT_ALGORITHM=HS256

# Database Configuration (per service)
DATABASE_URL=postgresql+asyncpg://user:pass@host:port/dbname

# Service URLs (for inter-service communication)
ATTENDEE_SERVICE_URL=http://18.214.134.23:8000
ROOM_SERVICE_URL=http://54.162.202.203:8000
CLASS_SERVICE_URL=http://3.225.88.17:8000
SCHEDULE_SERVICE_URL=http://35.171.134.244:8000
```

---

## Changelog

### Version 1.0 (December 28, 2025)
- Initial API documentation based on current implementation
- All 6 microservices documented
- Added complete workflow examples
- Included security and deployment notes
