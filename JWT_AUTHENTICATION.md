# JWT Authentication Implementation

This document describes the JWT authentication system implemented for the Campus Events API.

## Overview

The JWT authentication system provides secure token-based authentication with role-based permissions for the Campus Events application.

## Features Implemented

### ✅ JWT Tokens for Authentication
- Access tokens (1 hour expiration)
- Refresh tokens (7 days expiration)
- Token rotation on refresh
- Token blacklisting for security

### ✅ Token Refresh Mechanism
- Automatic token rotation
- Blacklist old refresh tokens
- Secure refresh endpoint

### ✅ Role-based Permissions
- Student role
- Organizer role
- Administrator role
- Custom permission classes for each role

### ✅ CORS Configuration
- Frontend integration support
- Development and production configurations
- Credential support

### ✅ Token Expiration Handling
- Configurable token lifetimes
- Automatic expiration
- Graceful handling of expired tokens

### ✅ Secure Token Storage Recommendations
- HTTP-only cookies (recommended)
- Local storage (development only)
- Secure storage guidelines

## API Endpoints

### Authentication Endpoints

#### Login
```
POST /api/auth/login/
Content-Type: application/json

{
    "email": "user@example.com",
    "password": "password123"
}
```

**Response:**
```json
{
    "access": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
    "refresh": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
    "user": {
        "id": 1,
        "email": "user@example.com",
        "first_name": "John",
        "last_name": "Doe",
        "role": "student",
        "is_verified": false,
        "student_id": "12345678"
    }
}
```

#### Refresh Token
```
POST /api/auth/refresh/
Content-Type: application/json

{
    "refresh": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..."
}
```

#### Verify Token
```
POST /api/auth/verify/
Content-Type: application/json

{
    "token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..."
}
```

#### Logout
```
POST /api/logout/
Authorization: Bearer <access_token>
Content-Type: application/json

{
    "refresh": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..."
}
```

### User Management Endpoints

#### Register User
```
POST /api/register/
Content-Type: application/json

{
    "email": "newuser@example.com",
    "password": "password123",
    "first_name": "Jane",
    "last_name": "Smith",
    "role": "student",
    "student_id": "87654321"
}
```

#### Get User Profile
```
GET /api/profile/
Authorization: Bearer <access_token>
```

#### Update User Profile
```
PATCH /api/profile/
Authorization: Bearer <access_token>
Content-Type: application/json

{
    "first_name": "Updated Name",
    "phone_number": "+1234567890"
}
```

### Event Management Endpoints

#### List Events
```
GET /api/events/
Authorization: Bearer <access_token>
```

#### Create Event (Organizers/Admins only)
```
POST /api/events/
Authorization: Bearer <access_token>
Content-Type: application/json

{
    "title": "Campus Event",
    "description": "Event description",
    "category": "Academic",
    "location": "Main Hall",
    "start_at": "2024-01-15T10:00:00Z",
    "end_at": "2024-01-15T12:00:00Z",
    "capacity": 100,
    "ticket_type": "free",
    "org": 1
}
```

#### Get Event Details
```
GET /api/events/{id}/
Authorization: Bearer <access_token>
```

#### Update Event (Owner/Organizer/Admin only)
```
PUT /api/events/{id}/
Authorization: Bearer <access_token>
Content-Type: application/json

{
    "title": "Updated Event Title",
    "description": "Updated description"
}
```

#### Delete Event (Owner/Admin only)
```
DELETE /api/events/{id}/
Authorization: Bearer <access_token>
```

### Organization Management Endpoints

#### List Organizations
```
GET /api/organizations/
Authorization: Bearer <access_token>
```

#### Create Organization (Admin only)
```
POST /api/organizations/
Authorization: Bearer <access_token>
Content-Type: application/json

{
    "name": "Student Council",
    "description": "Official student government"
}
```

## Role-based Permissions

### Student Role
- Can view events and organizations
- Can register for events
- Can update own profile
- Cannot create events or organizations

### Organizer Role
- All student permissions
- Can create and manage events
- Can update own events
- Cannot create organizations

### Administrator Role
- All organizer permissions
- Can create and manage organizations
- Can manage all events
- Can manage all users

## Security Features

### Token Security
- HS256 algorithm for signing
- Configurable token lifetimes
- Token rotation on refresh
- Blacklist support for logout

### CORS Configuration
- Development: Allows all origins
- Production: Restricted to specific domains
- Credential support for authentication

### Permission System
- Role-based access control
- Object-level permissions
- Custom permission classes

## Frontend Integration

### Recommended Token Storage

#### Option 1: HTTP-Only Cookies (Recommended)
```javascript
// Tokens are automatically included in requests
// No manual token management needed
fetch('/api/events/', {
    credentials: 'include'
});
```

#### Option 2: Local Storage (Development Only)
```javascript
// Store tokens in localStorage
localStorage.setItem('access_token', response.access);
localStorage.setItem('refresh_token', response.refresh);

// Include in requests
const token = localStorage.getItem('access_token');
fetch('/api/events/', {
    headers: {
        'Authorization': `Bearer ${token}`
    }
});
```

### Token Refresh Implementation
```javascript
// Automatic token refresh
const refreshToken = async () => {
    const refresh = localStorage.getItem('refresh_token');
    const response = await fetch('/api/auth/refresh/', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({ refresh })
    });
    
    if (response.ok) {
        const data = await response.json();
        localStorage.setItem('access_token', data.access);
        return data.access;
    } else {
        // Redirect to login
        window.location.href = '/login';
    }
};
```

## Configuration

### JWT Settings
```python
SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=60),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': True,
    'UPDATE_LAST_LOGIN': True,
    'ALGORITHM': 'HS256',
    'SIGNING_KEY': SECRET_KEY,
    'AUTH_HEADER_TYPES': ('Bearer',),
    'USER_ID_FIELD': 'id',
    'USER_ID_CLAIM': 'user_id',
}
```

### CORS Settings
```python
CORS_ALLOWED_ORIGINS = [
    "http://localhost:3000",    # React dev server
    "http://127.0.0.1:3000",
    "http://localhost:8080",    # Vue.js dev server
    "http://127.0.0.1:8080",
]

CORS_ALLOW_CREDENTIALS = True
CORS_ALLOW_ALL_ORIGINS = DEBUG  # Only in development
```

## Testing the Implementation

### 1. Start the Development Server
```bash
python manage.py runserver
```

### 2. Test Registration
```bash
curl -X POST http://127.0.0.1:8000/api/register/ \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "testpass123",
    "first_name": "Test",
    "last_name": "User",
    "role": "student"
  }'
```

### 3. Test Login
```bash
curl -X POST http://127.0.0.1:8000/api/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "testpass123"
  }'
```

### 4. Test Protected Endpoint
```bash
curl -X GET http://127.0.0.1:8000/api/profile/ \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

## Security Recommendations

### Production Settings
1. Use HTTPS only
2. Set secure cookie flags
3. Implement rate limiting
4. Use environment variables for secrets
5. Regular token cleanup
6. Monitor for suspicious activity

### Token Storage Best Practices
1. Use HTTP-only cookies when possible
2. Implement automatic token refresh
3. Clear tokens on logout
4. Never store tokens in plain text
5. Use secure storage mechanisms

## Troubleshooting

### Common Issues
1. **CORS errors**: Check CORS_ALLOWED_ORIGINS setting
2. **Token expired**: Implement automatic refresh
3. **Permission denied**: Check user role and permissions
4. **Invalid token**: Verify token format and signature

### Debug Mode
Set `DEBUG = True` in settings.py for detailed error messages during development.
