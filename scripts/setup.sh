#!/usr/bin/env bash
# =============================================================================
# SEPEHR | سپهر — Production Setup Script
# =============================================================================
# Usage:
#   chmod +x setup.sh
#   sudo ./setup.sh
#
# This script will:
#   1. Check system requirements
#   2. Install Docker & Docker Compose
#   3. Configure the environment
#   4. Obtain SSL certificates (Let's Encrypt)
#   5. Build and start all services
#   6. Run database migrations
#   7. Create the initial admin user
#   8. Configure systemd for auto-restart
#   9. Set up log rotation
#  10. Configure automatic backups
# =============================================================================

set -euo pipefail

# ── Colors ────────────────────────────────────────────────────────────────────
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
BOLD='\033[1m'
NC='\033[0m'

# ── Logging ───────────────────────────────────────────────────────────────────
log()     { echo -e "${GREEN}[✓]${NC} $1"; }
warn()    { echo -e "${YELLOW}[⚠]${NC} $1"; }
error()   { echo -e "${RED}[✗]${NC} $1"; exit 1; }
info()    { echo -e "${BLUE}[→]${NC} $1"; }
section() { echo -e "\n${BOLD}${BLUE}══ $1 ══${NC}\n"; }

# ── Banner ────────────────────────────────────────────────────────────────────
print_banner() {
    echo -e "${BLUE}"
    cat << 'BANNER'
  ╔═══════════════════════════════════════╗
  ║        سپهر  |  SEPEHR               ║
  ║   Emergency Communication Platform   ║
  ║        Production Setup v1.0         ║
  ╚═══════════════════════════════════════╝
BANNER
    echo -e "${NC}"
}

# ── Variables ─────────────────────────────────────────────────────────────────
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
COMPOSE_FILE="$SCRIPT_DIR/docker-compose.yml"
ENV_FILE="$SCRIPT_DIR/.env"
LOG_FILE="/var/log/sepehr-setup.log"
MIN_DOCKER_VERSION="24.0"
MIN_RAM_GB=2

# ── Checks ────────────────────────────────────────────────────────────────────
check_root() {
    if [[ $EUID -ne 0 ]]; then
        error "This script must be run as root. Use: sudo ./setup.sh"
    fi
}

check_os() {
    if [[ ! -f /etc/os-release ]]; then
        error "Cannot detect OS. Supported: Ubuntu 20.04+, Debian 11+"
    fi
    source /etc/os-release
    case "$ID" in
        ubuntu|debian) log "OS: $PRETTY_NAME" ;;
        *) warn "Untested OS: $PRETTY_NAME — proceeding anyway" ;;
    esac
}

check_ram() {
    local ram_gb
    ram_gb=$(awk '/MemTotal/ {printf "%d", $2/1024/1024}' /proc/meminfo)
    if [[ $ram_gb -lt $MIN_RAM_GB ]]; then
        warn "Only ${ram_gb}GB RAM detected. Minimum recommended: ${MIN_RAM_GB}GB"
    else
        log "RAM: ${ram_gb}GB"
    fi
}

check_disk() {
    local free_gb
    free_gb=$(df -BG "$SCRIPT_DIR" | awk 'NR==2{print $4}' | tr -d 'G')
    if [[ $free_gb -lt 20 ]]; then
        warn "Only ${free_gb}GB free disk. Minimum recommended: 20GB"
    else
        log "Disk: ${free_gb}GB free"
    fi
}

# ── Install Docker ─────────────────────────────────────────────────────────────
install_docker() {
    section "Installing Docker"
    if command -v docker &>/dev/null; then
        local ver
        ver=$(docker version --format '{{.Server.Version}}' 2>/dev/null || echo "0")
        log "Docker already installed: v$ver"
        return
    fi

    info "Installing Docker CE..."
    apt-get update -qq
    apt-get install -y -qq ca-certificates curl gnupg lsb-release

    install -m 0755 -d /etc/apt/keyrings
    curl -fsSL https://download.docker.com/linux/ubuntu/gpg \
        | gpg --dearmor -o /etc/apt/keyrings/docker.gpg
    chmod a+r /etc/apt/keyrings/docker.gpg

    echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] \
https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo "$VERSION_CODENAME") stable" \
        | tee /etc/apt/sources.list.d/docker.list > /dev/null

    apt-get update -qq
    apt-get install -y -qq docker-ce docker-ce-cli containerd.io docker-compose-plugin

    systemctl enable docker --now
    log "Docker installed successfully"
}

# ── Configure Environment ──────────────────────────────────────────────────────
configure_env() {
    section "Configuring Environment"

    if [[ -f "$ENV_FILE" ]]; then
        warn ".env file already exists. Skipping interactive setup."
        warn "Edit $ENV_FILE manually if needed."
        return
    fi

    cp "$SCRIPT_DIR/.env.example" "$ENV_FILE"

    # Prompt for domain
    read -rp "Enter your domain name (e.g. sepehr.example.ir): " DOMAIN
    sed -i "s/sepehr\.example\.ir/$DOMAIN/g" "$ENV_FILE"

    # Generate SECRET_KEY
    local secret_key
    secret_key=$(python3 -c "import secrets; print(secrets.token_hex(64))")
    sed -i "s/CHANGE_ME_GENERATE_WITH_SECRETS_TOKEN_HEX_64/$secret_key/" "$ENV_FILE"

    # Generate DB password
    local db_pass
    db_pass=$(python3 -c "import secrets, string; print(''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(40)))")
    sed -i "s/CHANGE_ME_STRONG_DB_PASSWORD/$db_pass/g" "$ENV_FILE"

    # Generate Redis password
    local redis_pass
    redis_pass=$(python3 -c "import secrets, string; print(''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(40)))")
    sed -i "s/CHANGE_ME_STRONG_REDIS_PASSWORD/$redis_pass/g" "$ENV_FILE"

    # Generate MinIO credentials
    local minio_access
    minio_access=$(python3 -c "import secrets, string; print(''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(20)))")
    local minio_secret
    minio_secret=$(python3 -c "import secrets, string; print(''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(40)))")
    sed -i "s/CHANGE_ME_MINIO_ACCESS_KEY/$minio_access/" "$ENV_FILE"
    sed -i "s/CHANGE_ME_MINIO_SECRET_KEY_MIN_20_CHARS/$minio_secret/" "$ENV_FILE"

    # Admin password
    read -rsp "Enter admin password (min 16 chars): " ADMIN_PASS
    echo
    if [[ ${#ADMIN_PASS} -lt 16 ]]; then
        error "Admin password too short (min 16 chars)"
    fi
    sed -i "s/CHANGE_ME_ADMIN_PASSWORD_MIN_16_CHARS/$ADMIN_PASS/" "$ENV_FILE"

    # Grafana password
    local grafana_pass
    grafana_pass=$(python3 -c "import secrets, string; print(''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(24)))")
    sed -i "s/CHANGE_ME_GRAFANA_PASSWORD/$grafana_pass/" "$ENV_FILE"

    chmod 600 "$ENV_FILE"
    log "Environment configured: $ENV_FILE"
}

# ── SSL Certificate ────────────────────────────────────────────────────────────
setup_ssl() {
    section "Setting Up SSL Certificate"

    source "$ENV_FILE"

    if [[ -d "/etc/letsencrypt/live/$DOMAIN" ]]; then
        log "SSL certificate already exists for $DOMAIN"
        return
    fi

    info "Installing Certbot..."
    apt-get install -y -qq certbot

    read -rp "Enter your email for Let's Encrypt notifications: " LE_EMAIL

    info "Obtaining certificate for $DOMAIN..."
    certbot certonly \
        --standalone \
        --non-interactive \
        --agree-tos \
        --email "$LE_EMAIL" \
        --domains "$DOMAIN" \
        --pre-hook "docker stop sepehr_nginx 2>/dev/null || true" \
        --post-hook "docker start sepehr_nginx 2>/dev/null || true"

    log "SSL certificate obtained for $DOMAIN"

    # Auto-renewal cron
    if ! crontab -l 2>/dev/null | grep -q "certbot renew"; then
        (crontab -l 2>/dev/null; echo "0 3 * * * certbot renew --quiet --deploy-hook 'docker exec sepehr_nginx nginx -s reload'") | crontab -
        log "SSL auto-renewal cron configured"
    fi
}

# ── Build and Start ────────────────────────────────────────────────────────────
build_and_start() {
    section "Building and Starting Services"

    cd "$SCRIPT_DIR"

    info "Pulling base images..."
    docker compose pull --quiet postgres redis minio nginx 2>/dev/null || true

    info "Building application images..."
    docker compose build --no-cache

    info "Starting infrastructure services..."
    docker compose up -d postgres redis minio
    
    info "Waiting for databases to be ready (30s)..."
    sleep 30

    info "Running database migrations..."
    docker compose run --rm backend alembic upgrade head

    info "Creating initial admin user..."
    source "$ENV_FILE"
    docker compose run --rm backend python -c "
import asyncio
from app.infrastructure.database.session import AsyncSessionFactory
from app.services.auth_service import AuthService
from app.domain.schemas.auth import RegisterRequest
from app.domain.enums.all import UserRole
from app.domain.models.all import User
from sqlalchemy import select

async def create_admin():
    async with AsyncSessionFactory() as db:
        existing = await db.scalar(
            select(User).where(User.username == '${ADMIN_USERNAME:-admin}')
        )
        if existing:
            print('Admin user already exists — skipping')
            return
        service = AuthService(db)
        user, _ = await service.register(
            RegisterRequest(
                username='${ADMIN_USERNAME:-admin}',
                password='${ADMIN_PASSWORD}',
                display_name='Administrator'
            )
        )
        user.role = UserRole.ADMINISTRATOR
        await db.commit()
        print(f'Admin user created: {user.username}')

asyncio.run(create_admin())
"

    info "Starting all services..."
    docker compose up -d

    info "Waiting for services to be healthy (20s)..."
    sleep 20

    # Health check
    local retries=0
    while [[ $retries -lt 10 ]]; do
        if curl -sf "http://localhost/api/health" &>/dev/null; then
            log "Backend is healthy"
            break
        fi
        retries=$((retries + 1))
        sleep 5
    done

    if [[ $retries -eq 10 ]]; then
        warn "Backend health check timed out. Check logs: docker compose logs backend"
    fi
}

# ── Systemd Service ────────────────────────────────────────────────────────────
configure_systemd() {
    section "Configuring Systemd Auto-restart"

    cat > /etc/systemd/system/sepehr.service << EOF
[Unit]
Description=SEPEHR Emergency Communication Platform
Requires=docker.service
After=docker.service network-online.target
Wants=network-online.target

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=$SCRIPT_DIR
EnvironmentFile=$ENV_FILE
ExecStart=/usr/bin/docker compose up -d
ExecStop=/usr/bin/docker compose down
ExecReload=/usr/bin/docker compose up -d
TimeoutStartSec=300
TimeoutStopSec=60
Restart=on-failure
RestartSec=30

[Install]
WantedBy=multi-user.target
EOF

    systemctl daemon-reload
    systemctl enable sepehr.service
    log "Systemd service configured: sepehr.service"
}

# ── Log Rotation ───────────────────────────────────────────────────────────────
configure_logrotate() {
    section "Configuring Log Rotation"

    cat > /etc/logrotate.d/sepehr << 'EOF'
/var/lib/docker/containers/*/*.log {
    daily
    rotate 7
    compress
    delaycompress
    missingok
    notifempty
    copytruncate
}

/var/log/sepehr*.log {
    daily
    rotate 14
    compress
    delaycompress
    missingok
    notifempty
    create 640 root adm
}
EOF

    log "Log rotation configured"
}

# ── Backup Configuration ───────────────────────────────────────────────────────
configure_backups() {
    section "Configuring Automated Backups"

    mkdir -p /opt/sepehr/backups

    cat > /usr/local/bin/sepehr-backup.sh << BACKUP_EOF
#!/usr/bin/env bash
# SEPEHR — Automated Backup Script
set -euo pipefail

BACKUP_DIR="/opt/sepehr/backups"
DATE=\$(date +%Y%m%d_%H%M%S)
RETENTION_DAYS=7

mkdir -p "\$BACKUP_DIR"

# PostgreSQL backup
echo "Backing up PostgreSQL..."
docker exec sepehr_postgres pg_dump -U sepehr sepehr | gzip > "\$BACKUP_DIR/postgres_\$DATE.sql.gz"

# Redis backup
echo "Backing up Redis..."
docker exec sepehr_redis redis-cli -a "\${REDIS_PASSWORD}" BGSAVE
sleep 2
docker cp sepehr_redis:/data/dump.rdb "\$BACKUP_DIR/redis_\$DATE.rdb"

# Remove old backups
find "\$BACKUP_DIR" -name "*.gz" -mtime +\$RETENTION_DAYS -delete
find "\$BACKUP_DIR" -name "*.rdb" -mtime +\$RETENTION_DAYS -delete

echo "Backup complete: \$DATE"
echo "Location: \$BACKUP_DIR"
BACKUP_EOF

    chmod +x /usr/local/bin/sepehr-backup.sh

    # Daily backup at 02:00
    if ! crontab -l 2>/dev/null | grep -q "sepehr-backup"; then
        (crontab -l 2>/dev/null; echo "0 2 * * * /usr/local/bin/sepehr-backup.sh >> /var/log/sepehr-backup.log 2>&1") | crontab -
        log "Daily backup cron configured (02:00)"
    fi
}

# ── Summary ────────────────────────────────────────────────────────────────────
print_summary() {
    source "$ENV_FILE"
    section "Setup Complete"

    echo -e "${GREEN}${BOLD}SEPEHR is running!${NC}\n"
    echo -e "  🌐 Web:      ${BLUE}https://$DOMAIN${NC}"
    echo -e "  🔌 API:      ${BLUE}https://$DOMAIN/api/v1${NC}"
    echo -e "  🔑 Admin:    ${BLUE}Username: ${ADMIN_USERNAME:-admin}${NC}"
    echo -e "  📊 Logs:     ${BLUE}docker compose logs -f${NC}"
    echo -e "  🔄 Restart:  ${BLUE}systemctl restart sepehr${NC}"
    echo -e "  💾 Backup:   ${BLUE}/usr/local/bin/sepehr-backup.sh${NC}"
    echo ""
    echo -e "${YELLOW}⚠  Important: Change admin password immediately after first login!${NC}"
    echo -e "${YELLOW}⚠  Store your .env file securely — it contains all secrets.${NC}"
    echo ""
}

# ── Main ───────────────────────────────────────────────────────────────────────
main() {
    print_banner

    # Log all output
    exec > >(tee -a "$LOG_FILE") 2>&1

    check_root
    check_os
    check_ram
    check_disk

    install_docker
    configure_env
    setup_ssl
    build_and_start
    configure_systemd
    configure_logrotate
    configure_backups
    print_summary
}

main "$@"
