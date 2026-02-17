# Production Deployment

BitWise Cloud deploys to a Linux box via Cloudflare Tunnel. GitHub Actions builds images on push to `main`, Watchtower auto-pulls them on the server.

## Architecture

```
Internet → Cloudflare CDN (app.bitwise.cloud) → cloudflared → caddy:80 → backend/frontend
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
3. Add a public hostname: `app.bitwise.cloud` → `http://caddy:80`

### 3. Authenticate to GHCR

Create a GitHub PAT with `read:packages` scope, then:

```bash
echo "YOUR_PAT" | docker login ghcr.io -u YOUR_GITHUB_USERNAME --password-stdin
```

### 4. Deploy

```bash
sudo mkdir -p /opt/bitwise-cloud/backups
cd /opt/bitwise-cloud

# Copy compose files and .env
# Edit .env with production values (use `openssl rand -base64 32` for secrets)

docker compose -f docker-compose.yml -f docker-compose.prod.yml pull
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d
```

### 5. Verify

```bash
docker compose ps                          # All containers healthy
docker compose logs cloudflared            # Tunnel connected
curl -s http://localhost:80/api/health     # Won't work (no host ports) — check via:
docker compose exec backend curl -s http://localhost:8000/api/health
```

Then visit `https://app.bitwise.cloud` — should load the app.

### 6. Monitoring

Set up UptimeRobot (or similar) to monitor `https://app.bitwise.cloud/api/health`.

### 7. Backups

```bash
chmod +x scripts/backup-postgres.sh
# Add to crontab:
echo "0 3 * * * /opt/bitwise-cloud/scripts/backup-postgres.sh" | crontab -
```

## Updating

Push to `main` → GitHub Actions builds images → Watchtower pulls within 60s.

To manually update:

```bash
cd /opt/bitwise-cloud
docker compose -f docker-compose.yml -f docker-compose.prod.yml pull
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d
```

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
