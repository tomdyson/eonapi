# EON API - Docker Deployment Guide

This guide covers deploying the EON API application with both the web UI and scheduled stats command using Docker.

## Architecture

The deployment includes:
- **Web UI**: FastAPI/Uvicorn server running on port 8000
- **Scheduled Stats**: Cron job that runs the `eonapi stats` command periodically (default: every 6 hours)
- **Single Container**: Both services run in the same container for simplicity

## Prerequisites

- Docker and Docker Compose installed
- E.ON Next account credentials
- (For Fly.io) Fly CLI installed: `curl -L https://fly.io/install.sh | sh`

## Local Development with Docker Compose

### 1. Create Environment File

Create a `.env` file in the project root (never commit this file):

```bash
EON_USERNAME=your@email.com
EON_PASSWORD=your_password
STATS_SCHEDULE=0 */6 * * *  # Every 6 hours (optional)
STATS_DAYS=30               # Last 30 days (optional)
```

### 2. Build and Run

```bash
# Build the image
docker-compose build

# Start the service
docker-compose up -d

# View logs
docker-compose logs -f

# View stats logs specifically
docker-compose exec eonapi tail -f /var/log/eonapi-stats.log
```

### 3. Access the UI

Open your browser to: http://localhost:8000

### 4. Stop the Service

```bash
docker-compose down
```

## Deployment to Fly.io

### 1. Install Fly CLI

```bash
curl -L https://fly.io/install.sh | sh
```

### 2. Login to Fly

```bash
fly auth login
```

### 3. Create and Configure App

```bash
# Initialize the app (if not already done)
fly launch --no-deploy

# Set your E.ON credentials as secrets
fly secrets set EON_USERNAME=your@email.com
fly secrets set EON_PASSWORD=your_password

# Optional: customize the schedule
fly secrets set STATS_SCHEDULE="0 */6 * * *"
fly secrets set STATS_DAYS=30
```

### 4. Deploy

```bash
fly deploy
```

### 5. Monitor

```bash
# View logs
fly logs

# View specific stats logs
fly ssh console -C "tail -f /var/log/eonapi-stats.log"

# Check app status
fly status

# Open the app in browser
fly open
```

### 6. Scale (if needed)

```bash
# Scale to more memory if needed
fly scale memory 512

# Keep at least 1 machine running
fly scale count 1
```

## Deployment to Coolify

### 1. Add New Application

1. Go to your Coolify dashboard
2. Click "New Resource" → "Docker Compose"
3. Paste the contents of `docker-compose.yml`

### 2. Set Environment Variables

In Coolify's environment variable section, add:

```
EON_USERNAME=your@email.com
EON_PASSWORD=your_password
STATS_SCHEDULE=0 */6 * * *
STATS_DAYS=30
```

### 3. Configure Port

- Set internal port: `8000`
- Enable HTTPS (Coolify handles this automatically)

### 4. Deploy

Click "Deploy" and Coolify will:
- Build the Docker image
- Start the container
- Set up SSL/TLS
- Provide you with a URL

### 5. View Logs

Use Coolify's built-in log viewer or SSH into the container:

```bash
docker exec -it <container_id> tail -f /var/log/eonapi-stats.log
```

## Alternative: Generic Docker Deployment

For any Docker-compatible hosting (DigitalOcean, AWS ECS, etc.):

### 1. Build the Image

```bash
docker build -t eonapi:latest .
```

### 2. Run the Container

```bash
docker run -d \
  --name eonapi \
  -p 8000:8000 \
  -e EON_USERNAME=your@email.com \
  -e EON_PASSWORD=your_password \
  -e STATS_SCHEDULE="0 */6 * * *" \
  -e STATS_DAYS=30 \
  --restart unless-stopped \
  eonapi:latest
```

### 3. View Logs

```bash
# Web UI logs
docker logs -f eonapi

# Stats logs
docker exec eonapi tail -f /var/log/eonapi-stats.log
```

## Configuration Options

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `EON_USERNAME` | *required* | Your E.ON Next account email |
| `EON_PASSWORD` | *required* | Your E.ON Next account password |
| `STATS_SCHEDULE` | `0 */6 * * *` | Cron schedule for stats command |
| `STATS_DAYS` | `30` | Number of days of data to analyze |
| `WEB_HOST` | `0.0.0.0` | Web UI host address |
| `WEB_PORT` | `8000` | Web UI port |

### Cron Schedule Examples

The `STATS_SCHEDULE` uses standard cron syntax:

```
# Every hour
0 * * * *

# Every 6 hours (default)
0 */6 * * *

# Every day at midnight
0 0 * * *

# Every day at 6 AM
0 6 * * *

# Every Monday at 9 AM
0 9 * * 1
```

## Monitoring and Maintenance

### Check Stats Execution

```bash
# For Docker Compose
docker-compose exec eonapi cat /var/log/eonapi-stats.log

# For Fly.io
fly ssh console -C "cat /var/log/eonapi-stats.log"

# For standalone Docker
docker exec eonapi cat /var/log/eonapi-stats.log
```

### Restart the Service

```bash
# Docker Compose
docker-compose restart

# Fly.io
fly apps restart

# Standalone Docker
docker restart eonapi
```

### Update the Application

```bash
# Docker Compose
git pull
docker-compose build
docker-compose up -d

# Fly.io
git pull
fly deploy

# Standalone Docker
git pull
docker build -t eonapi:latest .
docker stop eonapi
docker rm eonapi
# Then run the docker run command again
```

## Security Considerations

1. **Never commit credentials**: Always use environment variables or secrets management
2. **Use HTTPS**: Fly.io and Coolify provide this automatically; for other deployments, use a reverse proxy with SSL
3. **Restrict access**: Consider adding authentication or IP whitelisting for the web UI
4. **Keep updated**: Regularly update the base image and dependencies

## Troubleshooting

### Container exits immediately

Check the logs for missing environment variables:
```bash
docker logs eonapi
```

Make sure `EON_USERNAME` and `EON_PASSWORD` are set.

### Stats not running

1. Check cron is running:
   ```bash
   docker exec eonapi ps aux | grep cron
   ```

2. Check the cron schedule:
   ```bash
   docker exec eonapi crontab -l
   ```

3. View stats logs:
   ```bash
   docker exec eonapi cat /var/log/eonapi-stats.log
   ```

### Web UI not accessible

1. Check the container is running:
   ```bash
   docker ps | grep eonapi
   ```

2. Check port mapping:
   ```bash
   docker port eonapi
   ```

3. Check web server logs:
   ```bash
   docker logs eonapi
   ```

### Authentication failures

Verify your E.ON credentials:
```bash
docker exec eonapi env | grep EON_
```

If credentials look correct, try logging into the E.ON Next website to ensure your account is active.

## Cost Considerations

### Fly.io
- Free tier: 3 shared-cpu-1x VMs with 256MB RAM (sufficient for this app)
- This app should run comfortably on the free tier

### Coolify
- Self-hosted, so only costs are for your server
- Minimum 1GB RAM server recommended

### DigitalOcean
- $4/month droplet (512MB RAM) should be sufficient
- $6/month for 1GB RAM recommended for smoother operation

## Support

For issues specific to deployment, check:
- Fly.io docs: https://fly.io/docs/
- Coolify docs: https://coolify.io/docs/
- Docker docs: https://docs.docker.com/

For issues with the EON API application itself, open an issue on the GitHub repository.
