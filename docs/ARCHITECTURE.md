# SEPEHR | سپهر — Architecture Documentation

## Overview

SEPEHR is a secure, offline-capable emergency communication and information platform designed for operation on domestic infrastructure during internet disruptions, natural disasters, and crisis situations.

**Design Principles:**
- Reliability over features
- Simplicity over cleverness  
- Offline-first, sync when possible
- Mobile-first, works on low-end Android
- Zero external dependencies at runtime
- Secure by default

---

## System Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    CLIENTS                               │
│  Android PWA  │  Desktop Browser  │  Admin Panel         │
└───────────────────────┬─────────────────────────────────┘
                        │ HTTPS / WSS
┌───────────────────────▼─────────────────────────────────┐
│                   NGINX (TLS 1.3)                        │
│     Rate Limiting │ Security Headers │ Static Files      │
└──────┬────────────────────────────────────┬─────────────┘
       │ /api                               │ /ws
┌──────▼──────────────┐         ┌──────────▼──────────────┐
│   FastAPI Backend   │         │   WebSocket Gateway      │
│   (Uvicorn + Gunicorn)       │   (Integrated FastAPI)   │
└──────┬──────────────┘         └──────────┬──────────────┘
       │                                   │
┌──────▼───────────────────────────────────▼──────────────┐
│                    Service Layer                          │
│  Auth │ Messenger │ News │ Alerts │ Users │ Map          │
└──────┬──────────────────────────────────────────────────┘
       │
┌──────▼──────────────────────────────────────────────────┐
│                 Infrastructure Layer                      │
├─────────────┬─────────────┬──────────────┬──────────────┤
│ PostgreSQL  │    Redis    │    MinIO     │   Celery     │
│  (Primary)  │  (Cache+   │  (Object    │  (Background │
│             │  Sessions)  │   Storage)  │   Tasks)     │
└─────────────┴─────────────┴──────────────┴──────────────┘
```

---

## Module Architecture

### 1. HOME (Crisis Dashboard)
- Real-time emergency alert stream via WebSocket
- Aggregated feed: alerts → news → messages → system status
- Offline cache via Service Worker + IndexedDB
- Connectivity status indicator

### 2. MESSENGER (Secure Communication)
- WebSocket-based real-time messaging
- E2E encryption at application layer (X25519 + AES-256-GCM)
- Message types: text, voice, image, file, location
- Group conversations (max 500 members)
- Delivery receipts: sent → delivered → read

### 3. NEWS (Information Network)
- Hierarchical: Server → Category → Post
- Role-based publishing (Publisher role required)
- Offline-cached articles via Service Worker
- No engagement mechanics — pure information delivery

### 4. MAP (Crisis Awareness)
- Leaflet + OpenStreetMap (fully self-hostable tiles)
- Offline tile caching via Service Worker
- Emergency POI types: hospital, shelter, aid, safe_route, danger_zone
- Location sharing via Messenger (coordinate message type)

---

## Database Schema Design

### Users & Auth
```sql
users(id, username, password_hash, role, display_name, avatar_key, 
      is_active, last_seen, created_at, updated_at, deleted_at)

refresh_tokens(id, user_id, token_hash, expires_at, created_at, revoked_at)

audit_logs(id, user_id, action, resource_type, resource_id, 
           ip_address, user_agent, metadata, created_at)
```

### Messenger
```sql
conversations(id, type[direct|group], name, avatar_key, 
              created_by, created_at, updated_at, deleted_at)

conversation_members(id, conversation_id, user_id, role[member|admin], 
                     joined_at, left_at, is_muted)

messages(id, conversation_id, sender_id, type[text|voice|image|file|location|system],
         content_encrypted, iv, content_preview, file_key, file_size, file_mime,
         reply_to_id, is_deleted, created_at, updated_at)

message_receipts(id, message_id, user_id, status[sent|delivered|read], updated_at)
```

### News
```sql
news_servers(id, name, slug, description, icon_key, is_active, 
             created_by, created_at, updated_at)

news_categories(id, server_id, name, slug, description, color, 
                sort_order, is_active, created_at)

news_posts(id, server_id, category_id, publisher_id, title, slug, 
           summary, content, cover_image_key, video_url, 
           status[draft|published|archived], published_at, 
           created_at, updated_at, deleted_at)
```

### Alerts & Map
```sql
emergency_alerts(id, title, content, severity[info|warning|danger|critical],
                 area_geojson, issued_by, expires_at, is_active, 
                 created_at, updated_at)

map_points(id, name, type[hospital|shelter|aid|danger|safe_route],
           latitude, longitude, description, contact, is_active,
           created_by, created_at, updated_at)
```

---

## Security Architecture

### Authentication Flow
```
1. POST /auth/login → username + password
2. Argon2id password verification
3. Issue: access_token (15min JWT) + refresh_token (30d, stored as hash)
4. Client stores tokens in memory (access) + secure httpOnly cookie (refresh)
5. Auto-refresh via interceptor before expiry
6. Logout: revoke refresh token server-side
```

### Message Encryption
```
1. On registration: generate X25519 keypair
2. Public key stored server-side
3. Private key stored encrypted in client (derived from password via PBKDF2)
4. Per-message: ephemeral key + AES-256-GCM
5. Content encrypted before transmission
6. Server stores only ciphertext + IV
```

### Network Security
- TLS 1.3 only (Nginx)
- HSTS with 1-year max-age
- CSP: strict nonce-based
- Rate limiting: per-IP and per-user
- Request size limits enforced at Nginx + FastAPI

---

## Performance Strategy

### Backend
- Async SQLAlchemy (asyncpg driver)
- Redis for: sessions, rate limiting, WebSocket pub/sub, hot cache
- Connection pooling: PostgreSQL (20 connections), Redis (50 connections)
- Pagination: cursor-based for all list endpoints

### Frontend
- Next.js App Router with React Server Components where applicable
- TanStack Query for server state (stale-while-revalidate)
- Zustand for client state (minimal, no persistence of sensitive data)
- Service Worker: cache-first for static, network-first for API
- Critical CSS inlined, non-critical deferred

### Offline Strategy
- Service Worker (Workbox) handles all caching
- IndexedDB (via Dexie.js) for offline message queue
- Background sync for queued messages when online
- Map tiles cached on first view (LRU, max 500MB)

---

## Deployment Architecture

```
Server Requirements (Minimum):
- CPU: 2 cores
- RAM: 4GB
- Storage: 100GB SSD
- OS: Ubuntu 22.04 LTS

Services:
- Nginx (reverse proxy, SSL termination)
- FastAPI (4 Uvicorn workers via Gunicorn)
- PostgreSQL 16
- Redis 7
- MinIO (object storage)
- Celery (background tasks)
- Flower (Celery monitoring, internal only)

All services run as Docker containers via Docker Compose
Orchestrated by systemd service for auto-restart
```

---

## Folder Structure

```
sepehr/
├── backend/
│   ├── app/
│   │   ├── api/v1/
│   │   │   ├── endpoints/        # Route handlers
│   │   │   └── dependencies/     # FastAPI dependencies
│   │   ├── core/                 # Config, security, exceptions
│   │   ├── domain/
│   │   │   ├── models/           # SQLAlchemy models
│   │   │   ├── schemas/          # Pydantic schemas
│   │   │   └── enums/            # Python enums
│   │   ├── services/             # Business logic
│   │   ├── repositories/         # Data access layer
│   │   ├── infrastructure/       # DB, cache, storage, WS
│   │   ├── middleware/           # Custom middleware
│   │   └── utils/                # Helpers, crypto
│   ├── migrations/               # Alembic migrations
│   ├── tests/
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── app/                  # Next.js App Router pages
│   │   ├── components/           # Reusable components
│   │   ├── hooks/                # Custom React hooks
│   │   ├── stores/               # Zustand stores
│   │   ├── lib/                  # API client, utils
│   │   └── types/                # TypeScript types
│   ├── public/
│   └── package.json
├── infrastructure/
│   ├── nginx/                    # Nginx config
│   └── monitoring/               # Prometheus + Grafana
├── .github/workflows/            # CI/CD
├── scripts/                      # setup.sh, backup.sh
├── docker-compose.yml
├── docker-compose.prod.yml
└── .env.example
```
