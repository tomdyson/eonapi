# EON API - Docker Deployment Guide

This guide covers deploying the EON API web UI using Docker.

## What Gets Deployed

- **Web UI**: FastAPI/Uvicorn server running on port 8000
- **No credentials required**: Users enter their E.ON Next credentials in the browser (stored in localStorage)

## Prerequisites

- Docker (and optionally Docker Compose)
- (For Fly.io) Fly CLI installed: `curl -L https://fly.io/install.sh | sh`

## Local Development with Docker Compose

### 1. Build and Run

```bash
# Start the service
docker-compose up -d

# View logs
docker-compose logs -f
```

### 2. Access the UI

Open your browser to: http://localhost:8000

Enter your E.ON Next credentials in the web interface.

### 3. Stop the Service

```bash
docker-compose down
```

## Deployment to Fly.io

### 1. Install Fly CLI

```bash
curl -L https://fly.io/install.sh | sh
```

### 2. Login and Deploy

```bash
# Login to Fly
fly auth login

# Launch the app (follow the prompts)
fly launch

# Deploy
fly deploy
```

### 3. Access Your App

```bash
# Open in browser
fly open

# View logs
fly logs

# Check status
fly status
```

The app will auto-scale: it spins down when not in use and automatically starts when accessed, making it very cost-effective.

## Deployment to Coolify

### 1. Add New Application

1. Go to your Coolify dashboard
2. Click "New Resource" → "Dockerfile"
3. Connect your Git repository or upload the project

### 2. Configure

- Set internal port: `8000`
- Enable HTTPS (Coolify handles this automatically)

### 3. Deploy

Click "Deploy" and Coolify will:
- Build the Docker image
- Start the container
- Set up SSL/TLS
- Provide you with a URL

## Alternative: Generic Docker Deployment

For any Docker-compatible hosting (DigitalOcean, AWS ECS, Railway, Render, etc.):

### Build and Run

```bash
# Build the image
docker build -t eonapi:latest .

# Run the container
docker run -d \
  --name eonapi \
  -p 8000:8000 \
  --restart unless-stopped \
  eonapi:latest
```

### View Logs

```bash
docker logs -f eonapi
```

## Updating the Application

```bash
# Docker Compose
git pull
docker-compose up -d --build

# Fly.io
git pull
fly deploy

# Standalone Docker
git pull
docker build -t eonapi:latest .
docker stop eonapi && docker rm eonapi
docker run -d --name eonapi -p 8000:8000 --restart unless-stopped eonapi:latest
```

## Troubleshooting

### Container exits immediately

Check the logs:
```bash
docker logs eonapi
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

3. Check logs:
   ```bash
   docker logs eonapi
   ```

### Can't log in with E.ON credentials

The web UI stores credentials in your browser's localStorage. Try:
1. Clear your browser cache/localStorage
2. Verify your credentials work on the E.ON Next website
3. Check browser console for errors (F12 → Console tab)

## Cost Considerations

### Fly.io
- Free tier includes 3 shared-cpu VMs with 256MB RAM
- With auto-stop enabled (default), this app runs comfortably on the free tier
- Only runs when accessed, then auto-stops after inactivity

### Coolify
- Self-hosted, so only costs are for your server
- Lightweight app - 512MB RAM is sufficient

### Other Providers
- Railway: Free tier available with 500 hours/month
- Render: Free tier available (spins down after 15 min inactivity)
- DigitalOcean: $4-6/month droplet

## Optional: Scheduled Stats Command

If you want to run the `eonapi stats` command on a schedule (e.g., to monitor consumption automatically), you have a few options:

### Option 1: Host Machine Cron (Recommended)

If you're running Docker on a server you control, set up a cron job on the host:

```bash
# Edit crontab
crontab -e

# Add a job to run stats every 6 hours
0 */6 * * * docker exec eonapi eonapi stats --username "your@email.com" --password "yourpassword" --days 30 >> /var/log/eonapi-stats.log 2>&1
```

### Option 2: GitHub Actions

Create a scheduled workflow that runs the stats command:

```yaml
# .github/workflows/stats.yml
name: Daily Stats
on:
  schedule:
    - cron: '0 */6 * * *'  # Every 6 hours
  workflow_dispatch:  # Manual trigger

jobs:
  stats:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.12'
      - run: pip install eonapi
      - run: eonapi stats --username "${{ secrets.EON_USERNAME }}" --password "${{ secrets.EON_PASSWORD }}" --days 30
```

Set `EON_USERNAME` and `EON_PASSWORD` as repository secrets.

### Option 3: Cloud Scheduler

Use a cloud-based scheduler service:

- **AWS EventBridge + Lambda**: Trigger a Lambda function to run stats
- **Google Cloud Scheduler**: Schedule a Cloud Run job
- **Render Cron Jobs**: If hosting on Render, use their built-in cron feature

### Option 4: Separate Container with Cron

Build a separate lightweight container that runs cron:

```dockerfile
FROM python:3.12-slim

RUN apt-get update && apt-get install -y cron && rm -rf /var/lib/apt/lists/*
RUN pip install eonapi

# Create cron job
RUN echo "0 */6 * * * eonapi stats --username \$EON_USERNAME --password \$EON_PASSWORD --days 30 >> /var/log/cron.log 2>&1" > /etc/cron.d/eonapi-stats
RUN chmod 0644 /etc/cron.d/eonapi-stats
RUN crontab /etc/cron.d/eonapi-stats

CMD ["cron", "-f"]
```

Run it alongside your web UI with Docker Compose:

```yaml
services:
  web:
    build: .
    ports:
      - "8000:8000"

  stats:
    build:
      context: .
      dockerfile: Dockerfile.cron
    environment:
      - EON_USERNAME=${EON_USERNAME}
      - EON_PASSWORD=${EON_PASSWORD}
```

## Security Considerations

1. **Credentials**: The web UI stores credentials in browser localStorage only - they never touch the server
2. **HTTPS**: Always use HTTPS in production (Fly.io and Coolify provide this automatically)
3. **Public access**: Consider adding authentication if deploying publicly, or use Fly.io's built-in IP restrictions
4. **Updates**: Regularly update the Docker base image for security patches

## Support

For deployment platform issues:
- Fly.io docs: https://fly.io/docs/
- Coolify docs: https://coolify.io/docs/
- Docker docs: https://docs.docker.com/

For EON API application issues, open an issue on the GitHub repository.
