# 🎓 Campus Events API Documentation

## Overview
This API provides endpoints for managing campus events, user authentication, organizations, and digital tickets with QR code generation.

## Base URL
```
http://localhost:8000
```

## Authentication
All API endpoints (except registration and login) require JWT authentication. Include the token in the Authorization header:
```
Authorization: Bearer <your_jwt_token>
```

---

## 🔐 Authentication Endpoints

### Register User
**POST** `/api/register/`

Register a new user account.

**Request Body:**
```json
{
  "email": "user@example.com",
  "password": "securepassword",
  "first_name": "John",
  "last_name": "Doe",
  "role": "student",
  "student_id": "12345678",
  "phone_number": "+1234567890",
  "date_of_birth": "2000-01-01"
}
```

**Response (201):**
```json
{
  "refresh": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
  "access": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
  "user": {
    "id": 1,
    "email": "user@example.com",
    "first_name": "John",
    "last_name": "Doe",
    "role": "student",
    "is_verified": false
  }
}
```

### Login
**POST** `/api/auth/login/`

Authenticate user and get JWT tokens.

**Request Body:**
```json
{
  "email": "user@example.com",
  "password": "securepassword"
}
```

**Response (200):**
```json
{
  "refresh": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
  "access": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
  "user": {
    "id": 1,
    "email": "user@example.com",
    "first_name": "John",
    "last_name": "Doe",
    "role": "student",
    "is_verified": false
  }
}
```

### Refresh Token
**POST** `/api/auth/refresh/`

Get new access token using refresh token.

**Request Body:**
```json
{
  "refresh": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..."
}
```

### Logout
**POST** `/api/logout/`

Blacklist the refresh token.

**Request Body:**
```json
{
  "refresh": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..."
}
```

---

## 👤 User Endpoints

### Get User Profile
**GET** `/api/profile/`

Get current user's profile information.

**Response (200):**
```json
{
  "id": 1,
  "email": "user@example.com",
  "first_name": "John",
  "last_name": "Doe",
  "role": "student",
  "student_id": "12345678",
  "phone_number": "+1234567890",
  "date_of_birth": "2000-01-01",
  "is_verified": false,
  "is_active": true,
  "created_at": "2024-01-01T00:00:00Z"
}
```

### Update User Profile
**PATCH** `/api/profile/`

Update current user's profile.

**Request Body:**
```json
{
  "first_name": "Jane",
  "phone_number": "+1987654321"
}
```

---

## 🏢 Organization Endpoints

### List Organizations
**GET** `/api/organizations/`

Get all organizations.

**Response (200):**
```json
[
  {
    "id": 1,
    "name": "Computer Science Club",
    "description": "Student organization for CS students",
    "approved": true
  }
]
```

### Create Organization
**POST** `/api/organizations/`

Create a new organization (Admin only).

**Request Body:**
```json
{
  "name": "New Club",
  "description": "Description of the new club"
}
```

---

## 🎉 Event Endpoints

### List Events
**GET** `/api/events/`

Get all events with search, filtering, and pagination.

**Query Parameters:**
- `search`: Search in title and description
- `category`: Filter by category
- `status`: Filter by status (draft, pending, approved, rejected, cancelled)
- `org`: Filter by organization ID
- `start_date`: Filter events after this date
- `end_date`: Filter events before this date
- `ordering`: Sort by field (start_at, -start_at, capacity, -capacity)
- `page`: Page number for pagination

**Response (200):**
```json
{
  "count": 10,
  "next": "http://localhost:8000/api/events/?page=2",
  "previous": null,
  "results": [
    {
      "id": 1,
      "title": "Tech Conference 2024",
      "description": "Annual technology conference",
      "category": "Technology",
      "location": "Main Hall",
      "start_at": "2024-06-15T09:00:00Z",
      "end_at": "2024-06-15T17:00:00Z",
      "capacity": 100,
      "remaining_capacity": 75,
      "ticket_type": "free",
      "status": "approved",
      "org": 1,
      "org_name": "Computer Science Club",
      "created_by": 1,
      "created_by_name": "John Doe"
    }
  ]
}
```

### Create Event
**POST** `/api/events/`

Create a new event (Organizer/Admin only).

**Request Body:**
```json
{
  "title": "New Event",
  "description": "Event description",
  "category": "Technology",
  "location": "Room 101",
  "start_at": "2024-06-15T09:00:00Z",
  "end_at": "2024-06-15T17:00:00Z",
  "capacity": 50,
  "ticket_type": "free",
  "org": 1
}
```

### Get Event Details
**GET** `/api/events/{id}/`

Get detailed information about a specific event.

**Response (200):**
```json
{
  "id": 1,
  "title": "Tech Conference 2024",
  "description": "Annual technology conference",
  "category": "Technology",
  "location": "Main Hall",
  "start_at": "2024-06-15T09:00:00Z",
  "end_at": "2024-06-15T17:00:00Z",
  "capacity": 100,
  "remaining_capacity": 75,
  "ticket_type": "free",
  "status": "approved",
  "org": 1,
  "org_name": "Computer Science Club",
  "created_by": 1,
  "created_by_name": "John Doe"
}
```

### Update Event
**PUT** `/api/events/{id}/`

Update an event (Owner/Organizer/Admin only).

### Delete Event
**DELETE** `/api/events/{id}/`

Delete an event (Owner/Admin only).

---

## 🎫 Ticket Endpoints

### Issue Ticket
**POST** `/api/tickets/issue/`

Issue a ticket for an event.

**Request Body:**
```json
{
  "event_id": 1,
  "seat_number": "A12",
  "notes": "Special dietary requirements",
  "expires_at": "2024-06-15T17:00:00Z"
}
```

**Response (201):**
```json
{
  "id": 1,
  "ticket_id": "TKT-ABC123DEF456",
  "event": 1,
  "event_title": "Tech Conference 2024",
  "user": 1,
  "user_name": "John Doe",
  "status": "issued",
  "qr_code": "/media/qr_codes/ticket_TKT-ABC123DEF456.png",
  "qr_code_url": "/media/qr_codes/ticket_TKT-ABC123DEF456.png",
  "qr_code_data": "{\"ticket_id\":\"TKT-ABC123DEF456\",\"event_id\":1,\"user_id\":1,\"event_title\":\"Tech Conference 2024\",\"user_name\":\"John Doe\",\"issued_at\":\"2024-01-01T00:00:00Z\"}",
  "issued_at": "2024-01-01T00:00:00Z",
  "used_at": null,
  "expires_at": "2024-06-15T17:00:00Z",
  "seat_number": "A12",
  "notes": "Special dietary requirements",
  "is_valid": true
}
```

### Validate Ticket
**POST** `/api/tickets/validate/`

Validate a ticket by ticket ID (Organizer/Admin only).

**Request Body:**
```json
{
  "ticket_id": "TKT-ABC123DEF456"
}
```

**Response (200):**
```json
{
  "valid": true,
  "ticket": {
    "id": 1,
    "ticket_id": "TKT-ABC123DEF456",
    "event": 1,
    "event_title": "Tech Conference 2024",
    "user": 1,
    "user_name": "John Doe",
    "status": "used",
    "qr_code": "/media/qr_codes/ticket_TKT-ABC123DEF456.png",
    "issued_at": "2024-01-01T00:00:00Z",
    "used_at": "2024-01-01T12:00:00Z",
    "is_valid": false
  },
  "message": "Ticket validated and marked as used"
}
```

### Get My Tickets
**GET** `/api/tickets/my-tickets/`

Get all tickets for the current user.

**Response (200):**
```json
[
  {
    "id": 1,
    "ticket_id": "TKT-ABC123DEF456",
    "event": 1,
    "event_title": "Tech Conference 2024",
    "user": 1,
    "user_name": "John Doe",
    "status": "issued",
    "qr_code": "/media/qr_codes/ticket_TKT-ABC123DEF456.png",
    "issued_at": "2024-01-01T00:00:00Z",
    "is_valid": true
  }
]
```

### Get Ticket Details
**GET** `/api/tickets/{id}/`

Get detailed information about a specific ticket.

### Cancel Ticket
**DELETE** `/api/tickets/{id}/`

Cancel a ticket (Ticket owner or Admin only).

---

## 🔒 Role-Based Permissions

### Student Role
- Can register and login
- Can view events and organizations
- Can issue tickets for approved events
- Can view and cancel their own tickets
- Cannot create events or organizations

### Organizer Role
- All Student permissions
- Can create events
- Can update events they created
- Can validate tickets for their events
- Cannot create organizations

### Admin Role
- All Organizer permissions
- Can create organizations
- Can update/delete any event
- Can validate any ticket
- Can view all tickets

### List Pending Organizer Accounts
**GET** `/api/admin/pending-organizers/`

Retrieve organizers awaiting approval. Requires admin authentication.

**Query Parameters:**
- `page` *(optional)* — page number (default: 1)
- `page_size` *(optional)* — results per page (default: 10)
- `search` *(optional)* — filter by organizer email, first name, or last name

**Response (200):**
```json
{
  "count": 2,
  "next": null,
  "previous": null,
  "results": [
    {
      "id": 12,
      "email": "organizer@example.com",
      "first_name": "Alex",
      "last_name": "Doe",
      "role": "organizer",
      "student_id": "",
      "phone_number": "",
      "date_of_birth": null,
      "is_verified": false,
      "is_active": true,
      "is_staff": false,
      "is_superuser": false,
      "created_at": "2024-03-10T15:45:00Z",
      "updated_at": "2024-03-10T15:45:00Z",
      "last_login": null,
      "status": "pending"
    }
  ]
}
```

<<<<<<< HEAD
### Moderate Events
**GET** `/api/admin/events/`

Browse all events (any status) for moderation. Requires admin authentication.

**Query Parameters:**
- `page` *(optional)* — page number (default: 1)
- `page_size` *(optional)* — results per page (default: 10)
- `status` *(optional)* — filter by event status (`draft`, `pending`, `approved`, `rejected`)
- `organization` *(optional)* — case-insensitive match on organization name
- `category` *(optional)* — case-insensitive match on event category
- `search` *(optional)* — search in title, description, location, or creator email

**Response (200):**
```json
{
  "count": 12,
  "next": "http://127.0.0.1:8000/api/admin/events/?page=2",
  "previous": null,
  "results": [
    {
      "id": 48,
      "title": "Tech Career Fair",
      "description": "Company booths and networking",
      "category": "Career",
      "location": "Hall H",
      "start_at": "2025-11-03T16:00:00Z",
      "end_at": "2025-11-03T20:00:00Z",
      "capacity": 300,
      "remaining_capacity": 125,
      "ticket_type": "free",
      "status": "pending",
      "admin_comment": null,
      "org": 5,
      "org_name": "Engineering Society",
      "created_by": 9,
      "created_by_name": "Alex Organizer",
      "created_by_email": "alex@example.com",
      "created_at": "2025-10-20T14:22:10Z"
    }
  ]
}
```

=======
>>>>>>> 4a62580423ab393a6eea665b11199dd95af7be4f
---

## 📊 HTTP Status Codes

- **200 OK**: Request successful
- **201 Created**: Resource created successfully
- **400 Bad Request**: Invalid request data
- **401 Unauthorized**: Authentication required
- **403 Forbidden**: Insufficient permissions
- **404 Not Found**: Resource not found
- **500 Internal Server Error**: Server error

---

## 🛠️ Error Response Format

```json
{
  "error": "Error message description",
  "details": "Additional error details (optional)"
}
```

---

## 📝 Example Usage

### 1. Register and Login
```bash
# Register
curl -X POST http://localhost:8000/api/register/ \
  -H "Content-Type: application/json" \
  -d '{"email":"user@example.com","password":"password123","first_name":"John","last_name":"Doe","role":"student"}'

# Login
curl -X POST http://localhost:8000/api/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{"email":"user@example.com","password":"password123"}'
```

### 2. Issue a Ticket
```bash
curl -X POST http://localhost:8000/api/tickets/issue/ \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"event_id":1,"seat_number":"A12"}'
```

### 3. Validate a Ticket
```bash
curl -X POST http://localhost:8000/api/tickets/validate/ \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"ticket_id":"TKT-ABC123DEF456"}'
```

---

## 🔧 Development Setup

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Run migrations:
```bash
python manage.py migrate
```

3. Create superuser:
```bash
python manage.py createsuperuser
```

4. Start development server:
```bash
python manage.py runserver
```

5. Access admin interface:
```
http://localhost:8000/admin/
```

---

## 📱 Frontend Integration

### JWT Token Storage
Store JWT tokens securely in your frontend application:
```javascript
// Store tokens
localStorage.setItem('access_token', response.data.access);
localStorage.setItem('refresh_token', response.data.refresh);

// Include in API requests
const token = localStorage.getItem('access_token');
fetch('/api/events/', {
  headers: {
    'Authorization': `Bearer ${token}`,
    'Content-Type': 'application/json'
  }
});
```

### QR Code Display
QR codes are automatically generated and stored as images. Use the `qr_code_url` field to display the QR code in your frontend:

```html
<img src="{{ qr_code_url }}" alt="Event Ticket QR Code" />
```

---

## 🚀 Production Considerations

1. **Environment Variables**: Use environment variables for sensitive settings
2. **HTTPS**: Always use HTTPS in production
3. **Token Expiration**: Configure appropriate token lifetimes
4. **Rate Limiting**: Implement rate limiting for API endpoints
5. **CORS**: Configure CORS settings for your frontend domain
6. **Database**: Use PostgreSQL for production instead of SQLite
7. **Media Files**: Configure proper media file serving
8. **Logging**: Implement comprehensive logging for monitoring
