# سپهر | SEPEHR
### Emergency Communication & Crisis Information Platform

---

SEPEHR is a secure, offline-capable communication and information platform designed for operation during internet disruptions, natural disasters, and crisis situations. Built for deployment on domestic infrastructure.

## Features

- **🏠 Crisis Dashboard** — Real-time emergency alerts, latest news, and connectivity status
- **💬 Secure Messenger** — Encrypted direct and group messaging with offline queue
- **📰 News Network** — Hierarchical news servers with category filtering, no engagement mechanics
- **🗺️ Crisis Map** — Offline-capable Leaflet map with emergency locations (hospitals, shelters, aid centers)
- **📱 PWA** — Installable on Android, works offline, background sync

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | Next.js 15, TypeScript, TailwindCSS, Zustand, TanStack Query |
| Backend | FastAPI, Python 3.12, SQLAlchemy 2.0, Async |
| Database | PostgreSQL 16 |
| Cache | Redis 7 |
| Storage | MinIO |
| Auth | Argon2id + JWT |
| Realtime | WebSocket (native FastAPI) |
| Proxy | Nginx (TLS 1.3) |
| Deploy | Docker Compose + systemd |

## Quick Start

```bash
git clone https://github.com/hexday/SEPEHR.git
cd sepehr
sudo ./scripts/setup.sh
```

See [Production Guide](docs/PRODUCTION_GUIDE.md) for full deployment instructions.

## Documentation

- [Architecture](docs/ARCHITECTURE.md)
- [API Reference](docs/API.md)
- [Production Guide](docs/PRODUCTION_GUIDE.md)

## Development

### Backend

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp ../.env.example .env  # configure for local dev
alembic upgrade head
uvicorn app.main:app --reload
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

### Tests

```bash
# Backend
cd backend && pytest

# Frontend E2E
cd frontend && npx playwright test
```

## License

Proprietary — All rights reserved.

---

*Built for resilience. Designed for calm. Ready when it matters most.*
