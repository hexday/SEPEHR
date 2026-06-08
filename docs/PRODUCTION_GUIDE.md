# SEPEHR | سپهر — Production & Maintenance Guide

## Quick Start

### Prerequisites
- Ubuntu 22.04 LTS (minimum)
- 4GB RAM (2GB minimum)
- 50GB SSD
- Domain name with DNS pointing to your server
- Root or sudo access

### One-Command Deployment

```bash
git clone https://github.com/your-org/sepehr.git
cd sepehr
sudo chmod +x scripts/setup.sh
sudo ./scripts/setup.sh
```

The setup script handles everything: Docker, SSL, databases, migrations, admin user, and systemd.

---

## Manual Deployment

### 1. Configure Environment

```bash
cp .env.example .env
# Edit .env — fill ALL values marked CHANGE_ME
nano .env
```

**Critical values to set:**
- `SECRET_KEY` — generate with: `python3 -c "import secrets; print(secrets.token_hex(64))"`
- `POSTGRES_PASSWORD` — strong random password
- `REDIS_PASSWORD` — strong random password
- `MINIO_ACCESS_KEY` and `MINIO_SECRET_KEY`
- `ADMIN_PASSWORD` — min 16 chars
- `DOMAIN` — your domain name

### 2. Obtain SSL Certificate

```bash
apt-get install certbot
certbot certonly --standalone -d your-domain.ir --email your@email.ir --agree-tos
```

### 3. Build and Start

```bash
# Start infrastructure first
docker compose up -d postgres redis minio

# Wait 20 seconds for databases to initialize
sleep 20

# Run migrations
docker compose run --rm backend alembic upgrade head

# Start all services
docker compose up -d

# Verify
docker compose ps
curl https://your-domain.ir/api/health
```

---

## Daily Operations

### Service Management

```bash
# View all service status
docker compose ps

# View logs (all services)
docker compose logs -f

# View logs (specific service)
docker compose logs -f backend
docker compose logs -f frontend
docker compose logs -f nginx

# Restart a service
docker compose restart backend

# Restart all services
systemctl restart sepehr
```

### Database Operations

```bash
# Connect to PostgreSQL
docker exec -it sepehr_postgres psql -U sepehr -d sepehr

# Backup database manually
docker exec sepehr_postgres pg_dump -U sepehr sepehr | gzip > backup_$(date +%Y%m%d).sql.gz

# Restore from backup
gunzip -c backup_20240101.sql.gz | docker exec -i sepehr_postgres psql -U sepehr -d sepehr

# Run a migration
docker compose run --rm backend alembic upgrade head

# Roll back last migration
docker compose run --rm backend alembic downgrade -1

# View migration history
docker compose run --rm backend alembic history
```

### Cache Operations

```bash
# Connect to Redis CLI
docker exec -it sepehr_redis redis-cli -a $REDIS_PASSWORD

# Clear all cache (careful!)
docker exec sepehr_redis redis-cli -a $REDIS_PASSWORD FLUSHDB

# View cache stats
docker exec sepehr_redis redis-cli -a $REDIS_PASSWORD INFO stats
```

---

## Updates

### Rolling Update (Zero Downtime)

```bash
cd /opt/sepehr

# Pull latest code
git pull origin main

# Build new images
docker compose build --no-cache

# Run migrations (backward-compatible migrations only)
docker compose run --rm backend alembic upgrade head

# Rolling restart
docker compose up -d --no-deps backend
sleep 10
docker compose up -d --no-deps frontend

# Reload Nginx (if config changed)
docker exec sepehr_nginx nginx -s reload

# Verify
curl https://your-domain.ir/api/health
```

---

## Backup & Restore

### Manual Backup

```bash
/usr/local/bin/sepehr-backup.sh
```

Backups are stored in `/opt/sepehr/backups/` and retained for 7 days.

### Restore PostgreSQL

```bash
# Stop backend to prevent writes
docker compose stop backend celery_worker

# Restore
gunzip -c /opt/sepehr/backups/postgres_20240101_020000.sql.gz \
  | docker exec -i sepehr_postgres psql -U sepehr -d sepehr

# Restart
docker compose start backend celery_worker
```

### Restore Redis

```bash
docker compose stop redis

# Copy RDB file into container
docker cp /opt/sepehr/backups/redis_20240101_020000.rdb sepehr_redis:/data/dump.rdb

docker compose start redis
```

---

## Security

### Change Admin Password

```bash
docker compose run --rm backend python -c "
import asyncio
from app.infrastructure.database.session import AsyncSessionFactory
from app.core.security import hash_password
from app.domain.models.all import User
from sqlalchemy import select, update

async def change_admin_password(new_pass: str):
    async with AsyncSessionFactory() as db:
        await db.execute(
            update(User)
            .where(User.username == 'admin')
            .values(password_hash=hash_password(new_pass))
        )
        await db.commit()
        print('Admin password changed')

asyncio.run(change_admin_password('your-new-secure-password'))
"
```

### Rotate Secret Key

Rotating `SECRET_KEY` invalidates all existing JWT tokens (all users logged out):

```bash
# Generate new key
NEW_KEY=$(python3 -c "import secrets; print(secrets.token_hex(64))")

# Update .env
sed -i "s/^SECRET_KEY=.*/SECRET_KEY=$NEW_KEY/" .env

# Restart backend
docker compose restart backend
```

### View Audit Logs

```bash
docker exec sepehr_postgres psql -U sepehr -d sepehr \
  -c "SELECT created_at, action, ip_address, u.username
      FROM audit_logs al
      LEFT JOIN users u ON al.user_id = u.id
      ORDER BY created_at DESC
      LIMIT 50;"
```

---

## Monitoring

### Check System Health

```bash
# Full health status
curl https://your-domain.ir/api/health

# Docker container health
docker compose ps

# Resource usage
docker stats --no-stream

# Disk usage
df -h
du -sh /var/lib/docker/volumes/sepehr_*
```

### View Prometheus Metrics

Prometheus runs on port `9090` (internal only).

To access from your local machine:
```bash
ssh -L 9090:localhost:9090 user@your-server
# Then open: http://localhost:9090
```

### Grafana Dashboard

Grafana runs on port `3001` (internal only).

```bash
ssh -L 3001:localhost:3001 user@your-server
# Then open: http://localhost:3001
# Login: admin / (GRAFANA_PASSWORD from .env)
```

---

## Troubleshooting

### Backend Won't Start

```bash
# Check logs
docker compose logs backend

# Common causes:
# 1. Database not ready — wait and retry
# 2. Migration not run — docker compose run --rm backend alembic upgrade head
# 3. .env values missing — check all CHANGE_ME values are set
```

### WebSocket Connections Failing

```bash
# Check Nginx WebSocket config
docker exec sepehr_nginx nginx -t

# Verify backend is accepting WS
curl -i -N -H "Connection: Upgrade" \
     -H "Upgrade: websocket" \
     -H "Host: your-domain.ir" \
     https://your-domain.ir/ws?token=test
# Should return 400 or 401, not 502
```

### SSL Certificate Renewal Issues

```bash
# Manual renewal
certbot renew --dry-run

# Force renewal
certbot renew --force-renewal

# Reload Nginx after renewal
docker exec sepehr_nginx nginx -s reload
```

### Database Connection Pool Exhausted

```bash
# View active connections
docker exec sepehr_postgres psql -U sepehr -d sepehr \
  -c "SELECT count(*), state FROM pg_stat_activity GROUP BY state;"

# Terminate idle connections
docker exec sepehr_postgres psql -U sepehr -d sepehr \
  -c "SELECT pg_terminate_backend(pid) FROM pg_stat_activity
      WHERE state = 'idle' AND query_start < NOW() - INTERVAL '10 minutes';"
```

---

## Scaling

### Scale Backend Workers

```bash
# Edit docker-compose.yml CMD line:
# Change --workers 4 to --workers 8

# Or override at runtime:
docker compose up -d --scale backend=2
```

### MinIO Storage Growth

```bash
# Check MinIO disk usage
docker exec sepehr_minio du -sh /data/

# Cleanup orphaned files (run maintenance task)
docker compose run --rm celery_worker python -c "
from app.tasks.maintenance import cleanup_orphaned_files
cleanup_orphaned_files()
"
```

---

## Uninstall

```bash
# Stop and remove all containers
docker compose down

# Remove volumes (DESTROYS ALL DATA)
docker compose down -v

# Remove images
docker compose down --rmi all

# Disable systemd service
systemctl disable sepehr.service
rm /etc/systemd/system/sepehr.service
systemctl daemon-reload
```
