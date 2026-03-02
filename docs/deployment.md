# Production Deployment Guide

This document covers deploying the Aspendora Connect PBX platform to a production server. It assumes a single-server deployment with Docker Compose. For multi-server or Kubernetes deployments, adapt accordingly.

---

## 1. Prerequisites

### Hardware Requirements

| Component | Minimum | Recommended (50 tenants) |
|-----------|---------|--------------------------|
| CPU | 4 cores | 8 cores |
| RAM | 8 GB | 16 GB |
| Storage | 100 GB SSD | 250 GB NVMe SSD |
| Network | 100 Mbps | 1 Gbps |

### Software Requirements

- Ubuntu 22.04 LTS or Debian 12 (other Linux distros work but are not tested)
- Docker Engine 24.0+ with Compose v2
- A registered domain name (e.g., `pbx.example.com`)
- A valid TLS certificate (Let's Encrypt or commercial)
- `git` for cloning the repository

### Network Requirements

- Static public IP address
- Ports 443, 5061, 7443 (TCP) and 10000-20000 (UDP) open to the internet
- Outbound internet access for Docker image pulls, Let's Encrypt, and SIP trunking

---

## 2. Server Preparation

### 2.1 System Updates

```bash
sudo apt update && sudo apt upgrade -y
sudo apt install -y curl wget git ufw fail2ban unattended-upgrades
```

### 2.2 Firewall Configuration

```bash
# Reset and set defaults
sudo ufw default deny incoming
sudo ufw default allow outgoing

# SSH (restrict to your IP if possible)
sudo ufw allow 22/tcp

# HTTPS (web UI + API via reverse proxy)
sudo ufw allow 443/tcp

# SIP TLS
sudo ufw allow 5061/tcp

# WebRTC WSS
sudo ufw allow 7443/tcp

# RTP media (UDP range)
sudo ufw allow 10000:20000/udp

# Enable firewall
sudo ufw enable
sudo ufw status verbose
```

**Do NOT expose** these ports to the public internet:
- 5432 (PostgreSQL)
- 6379 (Redis)
- 8000 (API direct -- use reverse proxy)
- 3000/3001 (Web UI / Grafana -- use reverse proxy)
- 8021 (FreeSWITCH ESL)
- 9000/9001 (MinIO)
- 9090 (Prometheus)
- 9093 (Alertmanager)

### 2.3 Install Docker Engine

```bash
# Remove old versions
sudo apt remove -y docker docker-engine docker.io containerd runc 2>/dev/null

# Add Docker GPG key and repository
sudo install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
sudo chmod a+r /etc/apt/keyrings/docker.gpg

echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] \
  https://download.docker.com/linux/ubuntu \
  $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | \
  sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

sudo apt update
sudo apt install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

# Add your user to the docker group (log out and back in after)
sudo usermod -aG docker $USER

# Verify
docker --version
docker compose version
```

### 2.4 Kernel Tuning

Create `/etc/sysctl.d/99-newphone.conf`:

```bash
cat <<'EOF' | sudo tee /etc/sysctl.d/99-newphone.conf
# File descriptor limits for many concurrent calls
fs.file-max = 1048576

# Network buffer tuning for RTP
net.core.rmem_max = 16777216
net.core.wmem_max = 16777216
net.core.rmem_default = 262144
net.core.wmem_default = 262144
net.core.netdev_max_backlog = 65536

# TCP tuning
net.ipv4.tcp_max_syn_backlog = 65536
net.ipv4.tcp_tw_reuse = 1
net.ipv4.tcp_fin_timeout = 15
net.ipv4.ip_local_port_range = 1024 65535

# Connection tracking for SIP/RTP
net.netfilter.nf_conntrack_max = 262144
net.netfilter.nf_conntrack_udp_timeout = 60
net.netfilter.nf_conntrack_udp_timeout_stream = 180

# Disable IPv6 if not needed
net.ipv6.conf.all.disable_ipv6 = 1
net.ipv6.conf.default.disable_ipv6 = 1
EOF

sudo sysctl --system
```

Set file descriptor limits in `/etc/security/limits.d/99-newphone.conf`:

```bash
cat <<'EOF' | sudo tee /etc/security/limits.d/99-newphone.conf
*    soft    nofile    1048576
*    hard    nofile    1048576
root soft    nofile    1048576
root hard    nofile    1048576
EOF
```

### 2.5 NTP Synchronization

Accurate time is critical for TLS, CDR timestamps, and call recording metadata.

```bash
sudo apt install -y chrony
sudo systemctl enable chrony
sudo systemctl start chrony

# Verify sync
chronyc tracking
```

---

## 3. DNS Configuration

### Required DNS Records

| Type | Name | Value | TTL |
|------|------|-------|-----|
| A | `pbx.example.com` | `<server-public-ip>` | 300 |
| A | `sip.example.com` | `<server-public-ip>` | 300 |
| SRV | `_sips._tcp.example.com` | `0 5 5061 sip.example.com` | 3600 |

### Optional Records

| Type | Name | Value | TTL |
|------|------|-------|-----|
| A | `grafana.example.com` | `<server-public-ip>` | 300 |
| NAPTR | `example.com` | `10 100 "S" "SIPS+D2T" "" _sips._tcp.example.com` | 3600 |
| CAA | `example.com` | `0 issue "letsencrypt.org"` | 3600 |

The SRV record tells SIP clients where to find your server and on which port. NAPTR records are optional but help with SIP routing standards compliance.

---

## 4. TLS Certificates

### 4.1 Install Certbot

```bash
sudo apt install -y certbot
```

### 4.2 Obtain Certificates

Stop any service on port 80 temporarily, then:

```bash
sudo certbot certonly --standalone \
  -d pbx.example.com \
  -d sip.example.com \
  --agree-tos \
  --email admin@example.com \
  --non-interactive
```

Certificates are stored at:
- `/etc/letsencrypt/live/pbx.example.com/fullchain.pem`
- `/etc/letsencrypt/live/pbx.example.com/privkey.pem`

### 4.3 FreeSWITCH TLS Setup

FreeSWITCH requires certificates in a specific location. Create a deploy hook:

```bash
cat <<'HOOK' | sudo tee /etc/letsencrypt/renewal-hooks/deploy/newphone-freeswitch.sh
#!/bin/bash
CERT_SRC="/etc/letsencrypt/live/pbx.example.com"
CERT_DST="/opt/new-phone/freeswitch/tls"

mkdir -p "$CERT_DST"
cp "$CERT_SRC/fullchain.pem" "$CERT_DST/wss.pem"
cp "$CERT_SRC/privkey.pem" "$CERT_DST/wss.key"
cat "$CERT_SRC/fullchain.pem" "$CERT_SRC/privkey.pem" > "$CERT_DST/agent.pem"
cp "$CERT_SRC/chain.pem" "$CERT_DST/cafile.pem"
chmod 644 "$CERT_DST"/*.pem "$CERT_DST"/*.key

# Reload FreeSWITCH TLS profiles
cd /opt/new-phone && docker compose exec -T freeswitch fs_cli -x "sofia profile tls restart" 2>/dev/null || true
HOOK

sudo chmod +x /etc/letsencrypt/renewal-hooks/deploy/newphone-freeswitch.sh
```

Run the hook once to copy the initial certificates:

```bash
sudo /etc/letsencrypt/renewal-hooks/deploy/newphone-freeswitch.sh
```

### 4.4 Automatic Renewal

Certbot sets up a systemd timer automatically. Verify:

```bash
sudo systemctl list-timers | grep certbot
```

Test renewal:

```bash
sudo certbot renew --dry-run
```

---

## 5. Environment Configuration

### 5.1 Clone the Repository

```bash
sudo mkdir -p /opt/new-phone
sudo chown $USER:$USER /opt/new-phone
git clone <repository-url> /opt/new-phone
cd /opt/new-phone
```

### 5.2 Create the Environment File

```bash
cp .env.example .env
```

### 5.3 Generate Secrets

Generate each secret and replace the placeholder values in `.env`:

```bash
# JWT secret (64 characters)
openssl rand -base64 48

# Trunk encryption key (Fernet key)
python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"

# Database passwords (one per user)
openssl rand -base64 32  # for NP_DB_ADMIN_PASSWORD
openssl rand -base64 32  # for NP_DB_APP_PASSWORD

# MinIO credentials
openssl rand -base64 24  # for NP_MINIO_ACCESS_KEY
openssl rand -base64 32  # for NP_MINIO_SECRET_KEY

# Grafana admin password
openssl rand -base64 24  # for NP_GRAFANA_ADMIN_PASSWORD
```

### 5.4 Production .env Values

Edit `.env` with the generated values. Key settings to change from defaults:

```env
# === Database ===
NP_DB_ADMIN_PASSWORD=<generated-strong-password>
NP_DB_APP_PASSWORD=<generated-strong-password>

# === JWT ===
NP_JWT_SECRET_KEY=<generated-64-char-secret>

# === Encryption ===
NP_TRUNK_ENCRYPTION_KEY=<generated-fernet-key>

# === MinIO ===
NP_MINIO_ACCESS_KEY=<generated-access-key>
NP_MINIO_SECRET_KEY=<generated-secret-key>

# === FreeSWITCH ===
NP_FREESWITCH_ESL_PASSWORD=<change-from-default-ClueCon>

# === SMTP (use real mail server) ===
NP_SMTP_HOST=smtp.example.com
NP_SMTP_PORT=587
NP_SMTP_USER=notifications@example.com
NP_SMTP_PASSWORD=<smtp-password>
NP_SMTP_FROM_ADDRESS=pbx@example.com

# === Monitoring ===
NP_GRAFANA_ADMIN_PASSWORD=<generated-password>

# === Disable debug mode ===
NP_DEBUG=false
NP_LOG_LEVEL=WARNING

# === Do not expose internal ports on host ===
NP_DB_HOST_PORT=127.0.0.1:5434
NP_FS_ESL_HOST_PORT=127.0.0.1:8022
NP_AI_WS_HOST_PORT=127.0.0.1:8090
NP_AI_API_HOST_PORT=127.0.0.1:8091
```

### 5.5 Secure the .env File

```bash
chmod 600 .env
```

---

## 6. Production Docker Compose Override

Create `docker-compose.prod.yml` alongside the main compose file. This overrides development defaults with production settings.

```yaml
# docker-compose.prod.yml
# Usage: docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d

services:
  postgres:
    restart: unless-stopped
    ports:
      - "127.0.0.1:5434:5432"
    deploy:
      resources:
        limits:
          cpus: "2.0"
          memory: 2G
        reservations:
          memory: 512M
    logging:
      driver: json-file
      options:
        max-size: "10m"
        max-file: "5"
    command:
      - postgres
      - -c
      - shared_buffers=512MB
      - -c
      - effective_cache_size=1536MB
      - -c
      - maintenance_work_mem=128MB
      - -c
      - checkpoint_completion_target=0.9
      - -c
      - wal_buffers=16MB
      - -c
      - random_page_cost=1.1
      - -c
      - effective_io_concurrency=200
      - -c
      - max_connections=200
      - -c
      - log_min_duration_statement=1000
      - -c
      - log_checkpoints=on
      - -c
      - log_connections=on
      - -c
      - log_disconnections=on

  redis:
    restart: unless-stopped
    ports:
      - "127.0.0.1:6379:6379"
    command: >
      redis-server
      --maxmemory 512mb
      --maxmemory-policy allkeys-lru
      --save 900 1
      --save 300 10
      --appendonly yes
      --appendfsync everysec
    deploy:
      resources:
        limits:
          cpus: "0.5"
          memory: 768M
    logging:
      driver: json-file
      options:
        max-size: "10m"
        max-file: "5"

  minio:
    restart: unless-stopped
    ports:
      - "127.0.0.1:9000:9000"
      # Remove console port in production (access via reverse proxy if needed)
    deploy:
      resources:
        limits:
          cpus: "1.0"
          memory: 1G
    logging:
      driver: json-file
      options:
        max-size: "10m"
        max-file: "5"

  freeswitch:
    restart: unless-stopped
    ports:
      - "5061:5061/tcp"
      - "7443:7443/tcp"
      # Remove ESL host port exposure
      # Remove WS dev port (5066)
    deploy:
      resources:
        limits:
          cpus: "2.0"
          memory: 2G
        reservations:
          memory: 512M
    logging:
      driver: json-file
      options:
        max-size: "10m"
        max-file: "5"

  api:
    restart: unless-stopped
    ports:
      - "127.0.0.1:8000:8000"
    deploy:
      resources:
        limits:
          cpus: "2.0"
          memory: 1G
        reservations:
          memory: 256M
    logging:
      driver: json-file
      options:
        max-size: "10m"
        max-file: "5"

  web:
    restart: unless-stopped
    ports:
      - "127.0.0.1:3000:80"
    deploy:
      resources:
        limits:
          cpus: "0.5"
          memory: 256M
    logging:
      driver: json-file
      options:
        max-size: "10m"
        max-file: "5"

  ai-engine:
    restart: unless-stopped
    ports:
      - "127.0.0.1:8090:8090"
      - "127.0.0.1:8091:8091"
    deploy:
      resources:
        limits:
          cpus: "1.0"
          memory: 1G
    logging:
      driver: json-file
      options:
        max-size: "10m"
        max-file: "5"

  prometheus:
    restart: unless-stopped
    ports:
      - "127.0.0.1:9090:9090"
    deploy:
      resources:
        limits:
          cpus: "0.5"
          memory: 512M
    logging:
      driver: json-file
      options:
        max-size: "10m"
        max-file: "5"

  grafana:
    restart: unless-stopped
    ports:
      - "127.0.0.1:3001:3000"
    deploy:
      resources:
        limits:
          cpus: "0.5"
          memory: 512M
    logging:
      driver: json-file
      options:
        max-size: "10m"
        max-file: "5"

  alertmanager:
    restart: unless-stopped
    ports:
      - "127.0.0.1:9093:9093"
    deploy:
      resources:
        limits:
          cpus: "0.25"
          memory: 128M
    logging:
      driver: json-file
      options:
        max-size: "10m"
        max-file: "5"

  node-exporter:
    restart: unless-stopped
    deploy:
      resources:
        limits:
          cpus: "0.25"
          memory: 128M
    logging:
      driver: json-file
      options:
        max-size: "5m"
        max-file: "3"

  redis-exporter:
    restart: unless-stopped
    ports:
      - "127.0.0.1:9121:9121"
    deploy:
      resources:
        limits:
          cpus: "0.25"
          memory: 128M
    logging:
      driver: json-file
      options:
        max-size: "5m"
        max-file: "3"

  postgres-exporter:
    restart: unless-stopped
    ports:
      - "127.0.0.1:9187:9187"
    deploy:
      resources:
        limits:
          cpus: "0.25"
          memory: 128M
    logging:
      driver: json-file
      options:
        max-size: "5m"
        max-file: "3"

  # Remove mailhog in production
  mailhog:
    profiles:
      - dev-only
```

### Using the Production Override

```bash
# Start in production mode
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d

# Create an alias for convenience
alias dc-prod='docker compose -f docker-compose.yml -f docker-compose.prod.yml'
```

---

## 7. Reverse Proxy (Nginx)

### 7.1 Install Nginx

```bash
sudo apt install -y nginx
sudo systemctl enable nginx
```

### 7.2 Nginx Configuration

Create `/etc/nginx/sites-available/newphone`:

```nginx
# Rate limiting zones
limit_req_zone $binary_remote_addr zone=api_limit:10m rate=30r/s;
limit_req_zone $binary_remote_addr zone=login_limit:10m rate=5r/m;
limit_conn_zone $binary_remote_addr zone=ws_limit:10m;

# Upstream definitions
upstream api_backend {
    server 127.0.0.1:8000;
    keepalive 32;
}

upstream web_backend {
    server 127.0.0.1:3000;
}

upstream grafana_backend {
    server 127.0.0.1:3001;
}

upstream ai_ws_backend {
    server 127.0.0.1:8090;
}

# Redirect HTTP to HTTPS
server {
    listen 80;
    listen [::]:80;
    server_name pbx.example.com;

    # Let's Encrypt challenge
    location /.well-known/acme-challenge/ {
        root /var/www/certbot;
    }

    location / {
        return 301 https://$host$request_uri;
    }
}

# Main HTTPS server
server {
    listen 443 ssl http2;
    listen [::]:443 ssl http2;
    server_name pbx.example.com;

    # TLS configuration
    ssl_certificate /etc/letsencrypt/live/pbx.example.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/pbx.example.com/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256:ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384:ECDHE-ECDSA-CHACHA20-POLY1305:ECDHE-RSA-CHACHA20-POLY1305:DHE-RSA-AES128-GCM-SHA256:DHE-RSA-AES256-GCM-SHA384;
    ssl_prefer_server_ciphers off;
    ssl_session_cache shared:SSL:10m;
    ssl_session_timeout 1d;
    ssl_session_tickets off;

    # OCSP stapling
    ssl_stapling on;
    ssl_stapling_verify on;
    ssl_trusted_certificate /etc/letsencrypt/live/pbx.example.com/chain.pem;
    resolver 8.8.8.8 8.8.4.4 valid=300s;

    # Security headers
    add_header Strict-Transport-Security "max-age=63072000; includeSubDomains; preload" always;
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;
    add_header Content-Security-Policy "default-src 'self'; script-src 'self' 'unsafe-inline' 'unsafe-eval'; style-src 'self' 'unsafe-inline'; img-src 'self' data: blob:; connect-src 'self' wss://$host; media-src 'self' blob:; font-src 'self' data:; frame-ancestors 'self';" always;
    add_header Permissions-Policy "camera=(), microphone=(self), geolocation=()" always;

    # General proxy settings
    proxy_http_version 1.1;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;

    # Client body size (for file uploads -- recordings, voicemail, etc.)
    client_max_body_size 50m;

    # API routes
    location /api/ {
        limit_req zone=api_limit burst=60 nodelay;
        proxy_pass http://api_backend;
        proxy_read_timeout 30s;
        proxy_send_timeout 30s;
    }

    # Auth endpoints (stricter rate limit)
    location /api/v1/auth/login {
        limit_req zone=login_limit burst=3 nodelay;
        proxy_pass http://api_backend;
    }

    location /api/v1/auth/token {
        limit_req zone=login_limit burst=3 nodelay;
        proxy_pass http://api_backend;
    }

    # WebSocket connections (SIP.js, real-time events)
    location /ws {
        limit_conn ws_limit 100;
        proxy_pass http://api_backend;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_read_timeout 86400s;
        proxy_send_timeout 86400s;
    }

    # AI engine WebSocket
    location /ai/ws {
        limit_conn ws_limit 50;
        proxy_pass http://ai_ws_backend;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_read_timeout 86400s;
        proxy_send_timeout 86400s;
    }

    # Health check endpoint (no rate limit, for monitoring)
    location /api/v1/health {
        proxy_pass http://api_backend;
        access_log off;
    }

    # Web UI (React SPA)
    location / {
        proxy_pass http://web_backend;
        proxy_intercept_errors on;

        # SPA fallback: serve index.html for client-side routes
        error_page 404 = /index.html;
    }

    # Static assets caching
    location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg|woff|woff2|ttf|eot)$ {
        proxy_pass http://web_backend;
        expires 30d;
        add_header Cache-Control "public, immutable";
        access_log off;
    }

    # Block access to hidden files
    location ~ /\. {
        deny all;
        access_log off;
        log_not_found off;
    }
}

# Grafana (optional separate vhost, or use /grafana/ path)
server {
    listen 443 ssl http2;
    listen [::]:443 ssl http2;
    server_name grafana.example.com;

    ssl_certificate /etc/letsencrypt/live/pbx.example.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/pbx.example.com/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;

    add_header Strict-Transport-Security "max-age=63072000" always;
    add_header X-Frame-Options "DENY" always;

    location / {
        proxy_pass http://grafana_backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # Grafana WebSocket (live dashboards)
    location /api/live/ {
        proxy_pass http://grafana_backend;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_http_version 1.1;
    }
}
```

### 7.3 Enable the Site

```bash
sudo ln -sf /etc/nginx/sites-available/newphone /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t
sudo systemctl reload nginx
```

---

## 8. Deployment

### 8.1 Build and Start Services

```bash
cd /opt/new-phone

# Build all images
docker compose -f docker-compose.yml -f docker-compose.prod.yml build

# Start services
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d

# Watch logs during initial startup
docker compose -f docker-compose.yml -f docker-compose.prod.yml logs -f --tail=50
```

### 8.2 Database Setup

Wait for the `postgres` and `api` containers to be healthy, then run migrations:

```bash
# Check health
docker compose ps

# Run database migrations
docker compose exec api alembic upgrade head

# (Optional) Load seed data for initial tenant/admin
docker compose exec -T postgres psql -U new_phone_admin -d new_phone < db/seed/dev-seed.sql
```

### 8.3 Create MinIO Buckets

The API creates required buckets on startup, but you can verify:

```bash
docker compose exec minio mc alias set local http://localhost:9000 "$NP_MINIO_ACCESS_KEY" "$NP_MINIO_SECRET_KEY"
docker compose exec minio mc ls local/
```

### 8.4 Verify Services

```bash
# All containers should be "Up" and "healthy"
docker compose ps

# API health check
curl -s https://pbx.example.com/api/v1/health | jq .

# Web UI should load
curl -s -o /dev/null -w "%{http_code}" https://pbx.example.com/

# FreeSWITCH status
docker compose exec freeswitch fs_cli -x "sofia status"

# Check TLS is working
openssl s_client -connect pbx.example.com:5061 -brief </dev/null
openssl s_client -connect pbx.example.com:443 -brief </dev/null
```

---

## 9. Monitoring Setup

### 9.1 Grafana

Grafana is available at `https://grafana.example.com` (or via reverse proxy).

**First login:**
1. Username: `admin`
2. Password: the value of `NP_GRAFANA_ADMIN_PASSWORD` from `.env`
3. Change the admin password immediately after first login

Pre-provisioned dashboards are loaded automatically from `monitoring/grafana/dashboards/`.

### 9.2 Alertmanager

Configure alert destinations in `monitoring/alertmanager/alertmanager.yml`:

```yaml
global:
  smtp_smarthost: 'smtp.example.com:587'
  smtp_from: 'alerts@example.com'
  smtp_auth_username: 'alerts@example.com'
  smtp_auth_password: '<smtp-password>'

route:
  receiver: 'ops-team'
  group_wait: 30s
  group_interval: 5m
  repeat_interval: 4h

receivers:
  - name: 'ops-team'
    email_configs:
      - to: 'ops@example.com'
    # Optional: Slack webhook
    # slack_configs:
    #   - api_url: 'https://hooks.slack.com/services/xxx/yyy/zzz'
    #     channel: '#alerts'
```

Restart alertmanager after changes:

```bash
docker compose restart alertmanager
```

### 9.3 Prometheus

Prometheus is available at `http://127.0.0.1:9090` (localhost only). Data is retained for 30 days by default (configured in docker-compose).

---

## 10. Maintenance and Updates

### 10.1 Update Procedure

```bash
cd /opt/new-phone

# Pull latest code
git pull origin main

# Pull latest base images
docker compose pull

# Rebuild application images
docker compose -f docker-compose.yml -f docker-compose.prod.yml build

# Run database migrations BEFORE restarting
docker compose exec api alembic upgrade head

# Rolling restart (services with dependencies restart in order)
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d

# Verify health
docker compose ps
curl -s https://pbx.example.com/api/v1/health | jq .
```

### 10.2 Zero-Downtime API Updates

For API-only updates that do not require migration:

```bash
# Build the new image
docker compose -f docker-compose.yml -f docker-compose.prod.yml build api

# Restart only the API (other services stay up)
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --no-deps api
```

### 10.3 Log Management

Container logs are capped by the json-file driver settings in the production override (10 MB x 5 files per container). You can also view logs with:

```bash
# Tail logs for a specific service
docker compose logs -f --tail=100 api

# Export logs for analysis
docker compose logs --since="2h" api > /tmp/api-logs.txt
```

### 10.4 Certificate Renewal

Let's Encrypt certificates auto-renew via the certbot systemd timer. The deploy hook (section 4.3) automatically copies renewed certs to FreeSWITCH and reloads the TLS profile.

To manually trigger renewal:

```bash
sudo certbot renew
sudo systemctl reload nginx
```

### 10.5 Docker Cleanup

Periodically reclaim disk space (does NOT affect running containers or named volumes):

```bash
# Remove unused images and build cache
docker image prune -f
docker builder prune -f
```

**Never run `docker system prune` or `docker volume prune` on a production server** without explicitly verifying what will be removed.

---

## 11. Scaling

### 11.1 Multiple API Workers

Scale the API service horizontally behind the Nginx reverse proxy:

```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --scale api=3
```

Update the Nginx upstream to load balance:

```nginx
upstream api_backend {
    server 127.0.0.1:8000;
    server 127.0.0.1:8001;
    server 127.0.0.1:8002;
    keepalive 32;
}
```

Note: When scaling the API, you must assign different host ports to each instance, or use Docker's internal networking and point Nginx at container IPs.

### 11.2 PostgreSQL Read Replicas

For read-heavy workloads (CDR queries, reporting), add a streaming replica:

1. Configure the primary in `postgresql.conf`:
   ```
   wal_level = replica
   max_wal_senders = 3
   ```
2. Set up a replica server with `pg_basebackup`
3. Point read-only API queries to the replica connection string

### 11.3 Redis Sentinel

For Redis high availability:

1. Deploy 3 Redis Sentinel instances
2. Update `NP_REDIS_URL` to use the Sentinel connection format
3. Redis Sentinel handles automatic failover

### 11.4 Capacity Planning

| Metric | Single Server Estimate |
|--------|----------------------|
| Concurrent calls | 100-200 |
| Registered endpoints | 1,000-2,000 |
| API requests/sec | 500+ |
| Tenants | 50-100 |

Bottleneck is typically FreeSWITCH RTP processing. For more than 200 concurrent calls, consider dedicated media servers.

---

## 12. Troubleshooting

### 12.1 Service Health

```bash
# Check all container states
docker compose ps

# Check a specific service's logs
docker compose logs --tail=200 api
docker compose logs --tail=200 freeswitch
docker compose logs --tail=200 postgres

# Enter a container for debugging
docker compose exec api bash
docker compose exec freeswitch fs_cli
docker compose exec postgres psql -U new_phone_admin -d new_phone
```

### 12.2 Common Issues

**API won't start / exits immediately**
- Check database connectivity: `docker compose exec api python -c "import asyncpg; print('ok')"`
- Verify `.env` values match between services
- Check migration status: `docker compose exec api alembic current`

**FreeSWITCH TLS not working**
- Verify certificates exist: `ls -la freeswitch/tls/`
- Check certificate validity: `openssl x509 -in freeswitch/tls/wss.pem -text -noout`
- Verify TLS profile is loaded: `docker compose exec freeswitch fs_cli -x "sofia status profile tls"`

**WebRTC not connecting**
- Verify WSS port 7443 is reachable: `openssl s_client -connect pbx.example.com:7443 -brief </dev/null`
- Check browser console for WebSocket errors
- Verify CORS and CSP headers allow WebSocket connections

**Database connection refused**
- Check PostgreSQL is healthy: `docker compose ps postgres`
- Verify pg_hba.conf allows connections from Docker network
- Check connection count: `docker compose exec postgres psql -U new_phone_admin -c "SELECT count(*) FROM pg_stat_activity;"`

**High memory usage**
- Check container resource usage: `docker stats --no-stream`
- FreeSWITCH memory often grows with concurrent calls -- check `fs_cli -x "show channels"`
- PostgreSQL shared_buffers may need tuning

**Recordings not saving**
- Check MinIO is healthy: `docker compose ps minio`
- Verify bucket exists: `docker compose exec minio mc ls local/recordings/`
- Check the recordings volume mount: `docker compose exec api ls -la /recordings/`

### 12.3 Enable Debug Mode (Temporarily)

```bash
# Edit .env
NP_DEBUG=true
NP_LOG_LEVEL=DEBUG

# Restart API with debug logging
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --no-deps api

# Watch detailed logs
docker compose logs -f api

# IMPORTANT: Disable debug mode after troubleshooting
NP_DEBUG=false
NP_LOG_LEVEL=WARNING
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --no-deps api
```

### 12.4 Network Diagnostics

```bash
# Check Docker network
docker network inspect new_phone_net

# Test inter-container connectivity
docker compose exec api python -c "import httpx; print(httpx.get('http://freeswitch:8021').status_code)" 2>&1 || echo "Expected -- ESL is not HTTP"

# Check port bindings
docker compose port api 8000
ss -tlnp | grep -E '(8000|5061|7443|443)'
```

### 12.5 Rollback

If an update causes issues, roll back to the previous version:

```bash
cd /opt/new-phone

# Check out the previous version
git log --oneline -5   # find the previous good commit
git checkout <previous-commit-hash>

# Rebuild and restart
docker compose -f docker-compose.yml -f docker-compose.prod.yml build
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d

# If migrations need reverting
docker compose exec api alembic downgrade -1
```

---

## Quick Reference: Production Startup Checklist

```
[ ] Server provisioned with Ubuntu 22.04+ / 4 CPU / 8 GB RAM / 100 GB SSD
[ ] Firewall configured (443, 5061, 7443 TCP; 10000-20000 UDP)
[ ] Docker Engine 24+ installed
[ ] Kernel parameters tuned (sysctl, file descriptors)
[ ] NTP synchronized
[ ] DNS records created (A, SRV)
[ ] TLS certificates obtained and deployed
[ ] FreeSWITCH TLS certs copied and renewal hook created
[ ] Repository cloned to /opt/new-phone
[ ] .env created with strong generated secrets
[ ] .env file permissions set to 600
[ ] docker-compose.prod.yml reviewed and customized
[ ] Nginx configured with HTTPS, proxying, security headers
[ ] Services built and started
[ ] Database migrations applied
[ ] All containers healthy (docker compose ps)
[ ] API health endpoint returns 200
[ ] Web UI loads over HTTPS
[ ] SIP TLS working (openssl s_client test)
[ ] WSS working for WebRTC
[ ] Grafana accessible, admin password changed
[ ] Alertmanager configured with notification destinations
[ ] Backup cron job configured (see backup-restore.md)
[ ] Fail2ban configured
[ ] Certificate auto-renewal verified
```
