# Production Deployment

Bitwise deploys to a Linux box via Cloudflare Tunnel. GitHub Actions builds images on push to `main`, Watchtower auto-pulls them on the server.

## Architecture

```
Internet → Cloudflare CDN (bitwise.mikeayles.com) → cloudflared → caddy:80 → backend/frontend
```

No open ports on the server. Cloudflare handles HTTPS and DDoS protection.

## One-Time Setup

### 1. Install Docker

```bash
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER
# Log out and back in
```

### 2. Create Cloudflare Tunnel

1. Go to Cloudflare Zero Trust dashboard → Networks → Tunnels
2. Create a tunnel, copy the token
3. Add a public hostname: `bitwise.mikeayles.com` → `http://caddy:80`

### 3. Authenticate to GHCR

Create a GitHub PAT with `read:packages` scope, then:

```bash
echo "YOUR_PAT" | docker login ghcr.io -u YOUR_GITHUB_USERNAME --password-stdin
```

### 4. Deploy

```bash
sudo mkdir -p /opt/bitwise-cloud/backups
cd /opt/bitwise-cloud

# Copy compose files, .env, and scripts/
# Generate secrets and edit .env:
#   openssl rand -base64 32   (for POSTGRES_PASSWORD, REDIS_PASSWORD)
#   openssl rand -base64 64   (for JWT_SECRET)

# Lock down the secrets file
chmod 600 .env

docker compose -f docker-compose.yml -f docker-compose.prod.yml pull
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d
```

### 5. Verify

```bash
docker compose ps                          # All containers healthy
docker compose logs cloudflared            # Tunnel connected
docker compose exec backend curl -s http://localhost:8000/api/health
```

Then visit `https://bitwise.mikeayles.com` — should load the app. The `/api/health` endpoint checks Postgres and Redis connectivity and returns `"healthy"` or `"degraded"`.

### 6. Monitoring

Set up UptimeRobot (or similar) to monitor `https://bitwise.mikeayles.com/api/health`.

### 7. Backups

```bash
chmod +x scripts/backup-postgres.sh
# Add to crontab:
echo "0 3 * * * /opt/bitwise-cloud/scripts/backup-postgres.sh" | crontab -
```

Test a restore periodically — an untested backup is not a backup:

```bash
# Restore to a throwaway database to verify:
docker compose exec postgres createdb -U bitwise bitwise_test
gunzip -c backups/bitwise-YYYYMMDD-HHMMSS.sql.gz | \
  docker compose exec -T postgres psql -U bitwise bitwise_test
docker compose exec postgres dropdb -U bitwise bitwise_test
```

## Updating

Push to `main` → GitHub Actions builds + smoke tests → pushes `:latest` → Watchtower pulls within 60s.

Note: Watchtower polls on a 60s interval, so deploys are not instant. CI only tags `:latest` after the backend passes a health check smoke test, so broken builds won't reach production.

To manually update:

```bash
cd /opt/bitwise-cloud
docker compose -f docker-compose.yml -f docker-compose.prod.yml pull
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d
```

## Rollback

Every build pushes an immutable `:sha-<commit>` tag alongside `:latest`. To roll back to a known-good version:

```bash
cd /opt/bitwise-cloud

# 1. Stop watchtower so it doesn't pull :latest again
docker compose -f docker-compose.yml -f docker-compose.prod.yml stop watchtower

# 2. Pin to a known-good SHA (find from GitHub Actions or `docker image ls`)
export GOOD_SHA=abc123def456

# 3. Pull and run the pinned images
docker compose -f docker-compose.yml -f docker-compose.prod.yml pull \
  --ignore-buildable
# Or manually:
docker pull ghcr.io/michaelayles/bitwise-cloud-backend:$GOOD_SHA
docker pull ghcr.io/michaelayles/bitwise-cloud-caddy:$GOOD_SHA

# 4. Override images temporarily (edit docker-compose.prod.yml or use env vars)
BACKEND_TAG=$GOOD_SHA CADDY_TAG=$GOOD_SHA \
  docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d

# 5. Fix the issue on main, push, then restart watchtower
docker compose -f docker-compose.yml -f docker-compose.prod.yml start watchtower
```

## Scaling Notes

**Alembic migrations** run on backend startup (`alembic upgrade head`). This is safe for a single backend instance. If you ever scale to multiple backend replicas, you'll need to move migrations to a separate init container or one-shot job to avoid race conditions.

**Secrets**: The `.env` file contains production credentials. Keep it `chmod 600` and owned by the deploy user. Do not commit it to git.

## Troubleshooting

```bash
docker compose logs -f backend             # Backend logs
docker compose logs -f worker              # Celery worker logs
docker compose logs -f cloudflared         # Tunnel logs
docker compose logs -f watchtower          # Auto-update logs
docker compose exec postgres psql -U bitwise bitwise   # DB shell
```

## Restore from Backup

```bash
gunzip -c backups/bitwise-YYYYMMDD-HHMMSS.sql.gz | \
  docker compose exec -T postgres psql -U bitwise bitwise
```
