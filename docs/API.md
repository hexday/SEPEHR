# SEPEHR | سپهر — API Documentation

**Base URL:** `https://your-domain.ir/api/v1`
**WebSocket:** `wss://your-domain.ir/ws`

All responses use JSON. All authenticated endpoints require:
```
Authorization: Bearer <access_token>
```

---

## Authentication

### POST /auth/register
Register a new user.

**Request:**
```json
{
  "username": "john_doe",
  "password": "securepassword123",
  "display_name": "John Doe",
  "public_key": "base64_encoded_x25519_public_key"  // optional, for E2E encryption
}
```

**Response 201:**
```json
{
  "access_token": "eyJ...",
  "refresh_token": "base64url...",
  "token_type": "bearer",
  "expires_in": 900
}
```

**Errors:** `422` (validation), `409` (USERNAME_EXISTS)

---

### POST /auth/login
Authenticate with username and password.

**Request:**
```json
{
  "username": "john_doe",
  "password": "securepassword123"
}
```

**Response 200:** Same as register.

**Errors:** `401` (INVALID_CREDENTIALS)

---

### POST /auth/refresh
Issue new access token using refresh token.

**Request:**
```json
{
  "refresh_token": "base64url..."
}
```

**Response 200:** Same as login.

---

### POST /auth/logout
Revoke refresh token. *(Authenticated)*

**Request:**
```json
{
  "refresh_token": "base64url..."
}
```

**Response:** `204 No Content`

---

### GET /auth/me
Get current user profile. *(Authenticated)*

**Response 200:**
```json
{
  "id": "uuid",
  "username": "john_doe",
  "display_name": "John Doe",
  "avatar_url": null,
  "role": "user",
  "is_active": true,
  "last_seen": "2024-01-15T10:30:00Z",
  "public_key": "base64...",
  "created_at": "2024-01-01T00:00:00Z"
}
```

---

### PATCH /auth/me
Update profile. *(Authenticated)*

**Request:**
```json
{
  "display_name": "John Updated",
  "public_key": "new_base64_key"
}
```

---

## Messenger

### GET /messenger/conversations
List conversations ordered by last activity. *(Authenticated)*

**Query params:** `limit` (default 30), `offset` (default 0)

**Response 200:**
```json
[
  {
    "id": "uuid",
    "type": "direct",
    "name": null,
    "avatar_url": null,
    "last_message_at": "2024-01-15T10:30:00Z",
    "created_at": "2024-01-01T00:00:00Z",
    "member_count": 2,
    "last_message": { "..." },
    "unread_count": 3
  }
]
```

---

### POST /messenger/conversations/direct
Get or create a direct conversation. *(Authenticated)*

**Request:**
```json
{
  "recipient_username": "jane_doe"
}
```

**Response 201:** Conversation object.

---

### POST /messenger/conversations/group
Create a group conversation. *(Authenticated)*

**Request:**
```json
{
  "name": "Emergency Team Alpha",
  "member_usernames": ["user1", "user2", "user3"]
}
```

**Response 201:** Conversation object.

---

### GET /messenger/conversations/{id}/messages
Get messages with cursor-based pagination. *(Authenticated, member only)*

**Query params:** `limit` (default 30), `before_id` (cursor)

**Response 200:**
```json
{
  "messages": [...],
  "has_more": true,
  "cursor": "message_id_of_oldest"
}
```

---

### POST /messenger/conversations/{id}/messages/text
Send an encrypted text message. *(Authenticated, member only)*

**Request:**
```json
{
  "content_encrypted": "base64_aes_gcm_ciphertext",
  "iv": "hex_initialization_vector",
  "content_preview": "First 256 chars for notifications",
  "reply_to_id": "uuid_or_null"
}
```

**Response 201:** Message object.

---

### POST /messenger/conversations/{id}/messages/location
Send a location pin. *(Authenticated, member only)*

**Request:**
```json
{
  "latitude": 35.6892,
  "longitude": 51.3890,
  "reply_to_id": null
}
```

---

### POST /messenger/conversations/{id}/messages/media
Upload and send a media file. *(Authenticated, member only)*

**Form data:** `file` (binary), `message_type` (image|voice|file)

**Response 201:** Message object with `file_url`.

---

### DELETE /messenger/messages/{id}
Delete a message (soft delete). *(Authenticated, sender or admin)*

**Response:** `204 No Content`

---

## News

### GET /news/servers
List all active news servers. *(Authenticated)*

**Response 200:**
```json
[
  {
    "id": "uuid",
    "name": "اخبار ملی",
    "slug": "national-news",
    "description": "...",
    "icon_url": null,
    "is_active": true,
    "sort_order": 0,
    "category_count": 5
  }
]
```

---

### GET /news/servers/{id}/categories
List categories in a news server. *(Authenticated)*

---

### GET /news/posts
List published news posts. *(Authenticated)*

**Query params:** `server_id`, `category_id`, `limit`, `offset`

---

### GET /news/posts/{id}
Get a single news post with full content. *(Authenticated)*

---

### POST /news/posts
Create a news post. *(Publisher or Administrator)*

**Request:**
```json
{
  "server_id": "uuid",
  "category_id": "uuid_or_null",
  "title": "Breaking: Major earthquake",
  "summary": "A 6.2 magnitude earthquake...",
  "content": "Full article content in markdown...",
  "video_url": null,
  "publish": true
}
```

---

## Emergency Alerts

### GET /alerts
List emergency alerts. *(Authenticated)*

**Query params:** `active_only` (default true), `limit` (default 20)

---

### POST /alerts
Create emergency alert. *(Administrator only)*

**Request:**
```json
{
  "title": "Gas leak in District 5",
  "content": "Evacuate immediately. Move to designated shelters.",
  "severity": "critical",
  "area_geojson": { "type": "Polygon", "coordinates": [...] },
  "expires_at": "2024-01-15T18:00:00Z"
}
```

*Note: Also broadcasts via WebSocket to all connected clients.*

---

### PATCH /alerts/{id}/deactivate
Deactivate an alert. *(Administrator only)*

---

## Crisis Map

### GET /map/points
List crisis map points. *(Authenticated)*

**Query params:** `point_type` (hospital|shelter|aid_center|safe_route|danger_zone|checkpoint|water|food)

---

### POST /map/points
Add a crisis map point. *(Moderator or Administrator)*

**Request:**
```json
{
  "name": "Tehran Red Crescent Center",
  "type": "aid_center",
  "latitude": 35.6892,
  "longitude": 51.3890,
  "description": "24/7 emergency aid and medical supplies",
  "contact": "+98-21-1234567",
  "address": "Tehran, District 6, Vali Asr Ave"
}
```

---

## WebSocket Protocol

**Connect:** `wss://your-domain.ir/ws?token=<access_token>`

### Server → Client Events

| Type | Payload | Description |
|------|---------|-------------|
| `connected` | `{user_id, timestamp}` | Connection confirmed |
| `ping` | — | Heartbeat (respond with pong) |
| `new_message` | `{conversation_id, message}` | New message received |
| `typing` | `{user_id, conversation_id}` | User is typing |
| `read_receipt` | `{reader_id, message_id, conversation_id}` | Message read |
| `emergency_alert` | Alert object | System-wide alert broadcast |
| `error` | `{message}` | Error notification |

### Client → Server Events

| Type | Payload | Description |
|------|---------|-------------|
| `pong` | — | Heartbeat response |
| `typing` | `{conversation_id}` | Signal typing activity |
| `read_receipt` | `{message_id, conversation_id}` | Mark message as read |

### Error Codes (WebSocket close)
| Code | Meaning |
|------|---------|
| `4001` | Invalid/expired authentication token |
| `4003` | User not found or deactivated |
| `1000` | Normal closure (logout) |

---

## Error Response Format

All errors follow this format:
```json
{
  "error": "ERROR_CODE",
  "message": "Human-readable description",
  "detail": null
}
```

### Common Error Codes
| Code | HTTP | Meaning |
|------|------|---------|
| `VALIDATION_ERROR` | 422 | Input validation failed |
| `UNAUTHORIZED` | 401 | Authentication required |
| `INVALID_CREDENTIALS` | 401 | Wrong username/password |
| `TOKEN_EXPIRED` | 401 | JWT token expired |
| `INVALID_TOKEN` | 401 | Malformed/revoked token |
| `FORBIDDEN` | 403 | Insufficient permissions |
| `NOT_FOUND` | 404 | Resource not found |
| `USERNAME_EXISTS` | 409 | Username already taken |
| `FILE_TOO_LARGE` | 413 | Upload exceeds size limit |
| `UNSUPPORTED_FILE_TYPE` | 415 | File type not allowed |
| `RATE_LIMITED` | 429 | Too many requests |

---

## Rate Limits

| Endpoint Group | Limit | Window |
|----------------|-------|--------|
| Auth endpoints | 10 requests | 1 minute |
| API endpoints | 100 requests | 1 minute |
| Upload endpoints | 30 requests | 1 minute |
| WebSocket messages | 200 messages | 1 minute |

Rate limit headers are returned on every response:
- `X-RateLimit-Remaining: 45`

When exceeded, HTTP `429` is returned with:
```json
{
  "error": "RATE_LIMITED",
  "message": "Too many requests. Please slow down."
}
```
