# Required Secrets

All secrets should be stored in `~/.secrets/.env` and never committed to this repo.

| Secret | Env Variable | Purpose | Where to get it |
|--------|-------------|---------|-----------------|
| DB Admin Password | `NP_DB_ADMIN_PASSWORD` | PostgreSQL admin role (runs migrations) | Set any strong password |
| DB App Password | `NP_DB_APP_PASSWORD` | PostgreSQL app role (API runtime, RLS enforced) | Set any strong password |
| JWT Secret Key | `NP_JWT_SECRET_KEY` | Signs/verifies JWT access and refresh tokens | Generate with `openssl rand -hex 32` |
| FreeSWITCH ESL Password | `NP_FREESWITCH_ESL_PASSWORD` | Event Socket Layer authentication | Default: `ClueCon`, change in production |
| Trunk Encryption Key | `NP_TRUNK_ENCRYPTION_KEY` | Fernet key for encrypting SIP trunk passwords | Generate with `python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"` |
| MinIO Access Key | `NP_MINIO_ACCESS_KEY` | MinIO (S3-compatible) access key | Default: `minioadmin`, change in production |
| MinIO Secret Key | `NP_MINIO_SECRET_KEY` | MinIO (S3-compatible) secret key | Default: `minioadmin`, change in production |
| SMTP Host | `NP_SMTP_HOST` | SMTP server for voicemail-to-email | Default: `localhost` (MailHog in dev) |
| SMTP Port | `NP_SMTP_PORT` | SMTP port | Default: `1025` (MailHog) |
| SMTP User | `NP_SMTP_USER` | SMTP username (optional) | Empty for MailHog |
| SMTP Password | `NP_SMTP_PASSWORD` | SMTP password (optional) | Empty for MailHog |
| SMTP From Address | `NP_SMTP_FROM_ADDRESS` | From address for voicemail emails | Default: `voicemail@newphone.local` |

## Quick Setup

```bash
# Create secrets file
mkdir -p ~/.secrets
cat > ~/.secrets/.env << 'EOF'
export NP_DB_ADMIN_PASSWORD=your_admin_password_here
export NP_DB_APP_PASSWORD=your_app_password_here
export NP_JWT_SECRET_KEY=$(openssl rand -hex 32)
export NP_FREESWITCH_ESL_PASSWORD=ClueCon
export NP_MINIO_ACCESS_KEY=minioadmin
export NP_MINIO_SECRET_KEY=minioadmin
EOF

# Load before running
source ~/.secrets/.env
```

## Rotation

- **JWT Secret**: Rotating invalidates all active tokens. Coordinate with maintenance window.
- **DB Passwords**: Update in `~/.secrets/.env`, then update PostgreSQL roles, then restart services.
- **ESL Password**: Update in `~/.secrets/.env` and FreeSWITCH config, then restart both.
