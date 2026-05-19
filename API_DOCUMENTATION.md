# API Documentation

## Base URL
```
http://localhost:5000
```

## Authentication

### Login
**Endpoint:** `POST /auth/login`

**Request:**
```json
{
  "email": "user@example.com",
  "password": "password123",
  "remember": true
}
```

**Response (Success):**
```json
{
  "success": true,
  "message": "Login successful",
  "user": {
    "id": "user_id",
    "username": "username",
    "email": "user@example.com",
    "role": "user"
  }
}
```

**Response (Error):**
```json
{
  "success": false,
  "error": "Invalid email or password"
}
```

### Signup
**Endpoint:** `POST /auth/signup`

**Request:**
```json
{
  "username": "newuser",
  "email": "newuser@example.com",
  "password": "password123",
  "confirm_password": "password123"
}
```

**Response (Success):**
```json
{
  "success": true,
  "message": "Account created successfully"
}
```

### Logout
**Endpoint:** `GET /auth/logout`

**Response:**
```json
{
  "success": true,
  "message": "Logged out successfully"
}
```

---

## Dashboard API

### Get Equipment List
**Endpoint:** `GET /dashboard/api/equipment`

**Response:**
```json
{
  "success": true,
  "data": [
    {
      "equipment_id": "EQ-001",
      "name": "Pump A",
      "machine_type": "Centrifugal Pump",
      "status": "online",
      "health_score": 85.5,
      "sensors": {
        "Temperature": 75.3,
        "Vibration": 12.4,
        "Pressure": 6.2,
        "Humidity": 45.0,
        "RuntimeHours": 1250
      }
    }
  ]
}
```

### Get Equipment List (Pagination)
**Endpoint:** `GET /dashboard/api/equipment-list?page=1&limit=10`

**Parameters:**
- `page`: Page number (default: 1)
- `limit`: Items per page (default: 10)

**Response:**
```json
{
  "success": true,
  "data": [...],
  "pagination": {
    "page": 1,
    "limit": 10,
    "total": 50
  }
}
```

### Get Real-time Sensor Data
**Endpoint:** `GET /dashboard/api/realtime`

**Response:**
```json
{
  "success": true,
  "data": {
    "timestamp": "2024-01-15T10:30:45Z",
    "equipment": [
      {
        "equipment_id": "EQ-001",
        "Temperature": 75.3,
        "Vibration": 12.4,
        "Pressure": 6.2,
        "Humidity": 45.0
      }
    ]
  }
}
```

### Run Prediction
**Endpoint:** `POST /dashboard/api/sensor-data/<equipment_id>`

**Request:**
```json
{
  "is_failure": false
}
```

**Response:**
```json
{
  "success": true,
  "equipment_id": "EQ-001",
  "prediction": "Normal",
  "failure_probability": 0.15,
  "confidence": 0.85,
  "risk_level": "Low",
  "health_score": 85.5,
  "health_status": "Healthy",
  "sensors": {
    "Temperature": 75.3,
    "Vibration": 12.4,
    "Pressure": 6.2,
    "Humidity": 45.0,
    "RuntimeHours": 1250
  },
  "recommendations": [
    {
      "message": "Continue regular maintenance schedule",
      "action": "Schedule routine check-up in 2 weeks",
      "priority": "Low"
    }
  ],
  "timestamp": "2024-01-15T10:30:45Z"
}
```

### Get Active Alerts
**Endpoint:** `GET /dashboard/api/alerts`

**Response:**
```json
{
  "success": true,
  "data": [
    {
      "alert_id": "ALERT-001",
      "equipment_id": "EQ-001",
      "message": "Vibration levels elevated",
      "severity": "Warning",
      "timestamp": "2024-01-15T10:25:00Z",
      "acknowledged": false
    }
  ]
}
```

---

## Admin API

### Get All Users
**Endpoint:** `GET /admin/api/users`

**Headers:**
- Requires admin authentication

**Response:**
```json
{
  "success": true,
  "data": [
    {
      "id": "user_id",
      "username": "john_doe",
      "email": "john@example.com",
      "role": "user",
      "created_at": "2024-01-10T10:00:00Z"
    }
  ]
}
```

### Get User Details
**Endpoint:** `GET /admin/api/user/<user_id>`

**Response:**
```json
{
  "success": true,
  "data": {
    "id": "user_id",
    "username": "john_doe",
    "email": "john@example.com",
    "role": "user",
    "created_at": "2024-01-10T10:00:00Z",
    "last_login": "2024-01-15T09:30:00Z"
  }
}
```

### Update User
**Endpoint:** `POST /admin/api/user/<user_id>`

**Request:**
```json
{
  "role": "technician"
}
```

**Response:**
```json
{
  "success": true,
  "message": "User updated successfully"
}
```

### Delete User
**Endpoint:** `POST /admin/api/user/<user_id>/delete`

**Response:**
```json
{
  "success": true,
  "message": "User deleted successfully"
}
```

### Get System Analytics
**Endpoint:** `GET /admin/api/analytics`

**Response:**
```json
{
  "success": true,
  "data": {
    "total_users": 25,
    "total_equipment": 15,
    "total_predictions": 450,
    "total_alerts": 12,
    "equipment_healthy": 10,
    "equipment_caution": 4,
    "equipment_critical": 1,
    "uptime": "99.9%",
    "accuracy": "98.5%"
  }
}
```

### Get System Health Check
**Endpoint:** `GET /admin/api/health-check`

**Response:**
```json
{
  "success": true,
  "data": {
    "database_status": "OK",
    "api_status": "OK",
    "model_status": "OK",
    "email_status": "OK",
    "cache_status": "OK"
  }
}
```

### Get System Settings
**Endpoint:** `GET /admin/api/settings`

**Response:**
```json
{
  "success": true,
  "data": {
    "prediction_threshold": 0.7,
    "alert_email": "admin@example.com",
    "maintenance_interval": 30,
    "session_timeout": 3600
  }
}
```

### Update System Settings
**Endpoint:** `POST /admin/api/settings`

**Request:**
```json
{
  "prediction_threshold": 0.75,
  "alert_email": "newalert@example.com",
  "maintenance_interval": 30
}
```

**Response:**
```json
{
  "success": true,
  "message": "Settings updated successfully"
}
```

### Create Backup
**Endpoint:** `POST /admin/api/backup`

**Response:**
```json
{
  "success": true,
  "message": "Backup completed successfully",
  "backup_file": "backup_2024_01_15_103045.zip"
}
```

### Clear Cache
**Endpoint:** `POST /admin/api/clear-cache`

**Response:**
```json
{
  "success": true,
  "message": "Cache cleared successfully"
}
```

### Export Data
**Endpoint:** `GET /admin/api/export`

**Parameters:**
- `format`: "csv" or "json" (default: csv)
- `date_from`: Start date (optional)
- `date_to`: End date (optional)

**Response:** CSV or JSON file download

---

## Error Responses

### 400 Bad Request
```json
{
  "success": false,
  "error": "Invalid request parameters",
  "details": "Field 'equipment_id' is required"
}
```

### 401 Unauthorized
```json
{
  "success": false,
  "error": "Unauthorized",
  "message": "Please log in to access this resource"
}
```

### 403 Forbidden
```json
{
  "success": false,
  "error": "Forbidden",
  "message": "You don't have permission to access this resource"
}
```

### 404 Not Found
```json
{
  "success": false,
  "error": "Not found",
  "message": "Equipment with ID 'EQ-999' not found"
}
```

### 500 Internal Server Error
```json
{
  "success": false,
  "error": "Internal server error",
  "message": "An unexpected error occurred. Please try again later."
}
```

---

## Rate Limiting

- Default rate limit: 100 requests per minute per IP
- Admin endpoints: 500 requests per minute per user

---

## Pagination

For endpoints returning lists, pagination is available:

**Query Parameters:**
- `page`: Page number (default: 1)
- `limit`: Items per page (default: 10, max: 100)

**Response includes:**
```json
{
  "success": true,
  "data": [...],
  "pagination": {
    "page": 1,
    "limit": 10,
    "total": 50,
    "pages": 5
  }
}
```

---

## Data Types

### Timestamp Format
All timestamps are in ISO 8601 format: `2024-01-15T10:30:45Z`

### Equipment Status
- `online`: Equipment is operating normally
- `warning`: Equipment showing signs of wear
- `critical`: Equipment requires immediate attention

### User Roles
- `user`: Standard user - can view dashboard and own predictions
- `technician`: Can manage equipment and view all predictions
- `admin`: Full system access - can manage users and settings

---

## Sensor Data Ranges

| Sensor | Unit | Min | Max |
|--------|------|-----|-----|
| Temperature | °C | 0 | 100 |
| Vibration | Hz | 0 | 50 |
| Pressure | bar | 0 | 10 |
| Humidity | % | 0 | 100 |
| Runtime Hours | h | 0 | ∞ |

---

## Usage Examples

### Example 1: Complete Prediction Workflow

```python
import requests

BASE_URL = "http://localhost:5000"

# Login
login_response = requests.post(f"{BASE_URL}/auth/login", json={
    "email": "user@example.com",
    "password": "password123"
})

# Get equipment list
equipment_response = requests.get(f"{BASE_URL}/dashboard/api/equipment")
equipment_list = equipment_response.json()['data']

# Run prediction for first equipment
equipment_id = equipment_list[0]['equipment_id']
prediction_response = requests.post(
    f"{BASE_URL}/dashboard/api/sensor-data/{equipment_id}"
)
prediction = prediction_response.json()

print(f"Prediction: {prediction['prediction']}")
print(f"Confidence: {prediction['confidence']}")
```

### Example 2: Admin Analytics Retrieval

```python
import requests

BASE_URL = "http://localhost:5000"

# Get analytics
analytics_response = requests.get(f"{BASE_URL}/admin/api/analytics")
analytics = analytics_response.json()['data']

print(f"Total Equipment: {analytics['total_equipment']}")
print(f"Healthy Equipment: {analytics['equipment_healthy']}")
print(f"System Uptime: {analytics['uptime']}")
```

---

## Best Practices

1. **Authentication**: Always include authentication headers for protected endpoints
2. **Error Handling**: Implement proper error handling for API responses
3. **Rate Limiting**: Implement exponential backoff for rate-limited requests
4. **Caching**: Cache frequently accessed data to reduce API calls
5. **Validation**: Validate input data before sending requests
6. **Security**: Never expose API keys or credentials in client-side code

---

**Last Updated:** December 2024
**API Version:** 1.0
