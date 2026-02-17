# Mike TODO

Manual/infrastructure tasks that require human action.

## Production Setup (One-Time)

- [ ] Create Cloudflare Tunnel in Zero Trust dashboard, copy token
- [ ] Configure tunnel public hostname: `app.bitwise.cloud` → `http://caddy:80`
- [ ] Set up `/opt/bitwise-cloud/` on the Linux box with `.env` (generate secrets with `openssl rand -base64 32`)
- [ ] `chmod 600 .env` on production server
- [ ] `docker login ghcr.io` on the Linux box (GitHub PAT with `read:packages`)
- [ ] First deploy: `docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d`
- [ ] Verify GitHub Actions ran successfully on first push (check GHCR packages are created)
- [ ] Make GHCR packages public (or keep private + ensure watchtower can auth)

## Monitoring & Backups

- [ ] Set up UptimeRobot to monitor `https://app.bitwise.cloud/api/health`
- [ ] Add backup cron: `0 3 * * * /opt/bitwise-cloud/scripts/backup-postgres.sh`
- [ ] Test a backup restore at least once to verify it works
- [ ] Optional: configure rclone for R2 offsite backups

## DNS & Domain

- [ ] Point `app.bitwise.cloud` (or `app.bitwisemcp.com`) to the Cloudflare Tunnel
- [ ] Decide on landing page domain setup (Cloudflare Pages, out of scope for now)

## Ongoing

- [ ] Periodically test backup restores (monthly)
- [ ] Review Watchtower logs after deploys to confirm auto-updates are working
- [ ] Keep Docker and Docker Compose updated on the Linux box
