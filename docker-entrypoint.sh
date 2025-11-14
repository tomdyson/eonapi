#!/bin/bash
set -e

# Environment variables for E.ON credentials
# These should be set via environment variables or secrets
: ${EON_USERNAME:?"EON_USERNAME environment variable is required"}
: ${EON_PASSWORD:?"EON_PASSWORD environment variable is required"}

# Optional configuration
: ${STATS_SCHEDULE:="0 */6 * * *"}  # Default: every 6 hours
: ${STATS_DAYS:="30"}                # Default: 30 days of data
: ${WEB_HOST:="0.0.0.0"}
: ${WEB_PORT:="8000"}

echo "================================================"
echo "EON API - Docker Deployment"
echo "================================================"
echo "Web UI will be available on port ${WEB_PORT}"
echo "Stats command scheduled: ${STATS_SCHEDULE}"
echo "Stats will analyze last ${STATS_DAYS} days"
echo "================================================"

# Create a script for the stats command
cat > /app/run-stats.sh << 'EOF'
#!/bin/bash
cd /app
source /app/.venv/bin/activate
echo "[$(date)] Running stats command..."
eonapi stats --username "$EON_USERNAME" --password "$EON_PASSWORD" --days "$STATS_DAYS" >> /var/log/eonapi-stats.log 2>&1
echo "[$(date)] Stats command completed"
EOF

chmod +x /app/run-stats.sh

# Create log directory
mkdir -p /var/log
touch /var/log/eonapi-stats.log

# Set up cron job
echo "Setting up cron job: ${STATS_SCHEDULE}"
echo "${STATS_SCHEDULE} /app/run-stats.sh" | crontab -

# Start cron in the background
echo "Starting cron daemon..."
cron

# Display initial log message
echo "Cron job installed successfully"
echo "To view stats logs: docker exec <container> tail -f /var/log/eonapi-stats.log"
echo ""

# Run an initial stats command in the background
echo "Running initial stats command in background..."
/app/run-stats.sh &

# Start the web UI in the foreground
echo "Starting web UI on ${WEB_HOST}:${WEB_PORT}..."
exec uvicorn eonapi.server:app --host "${WEB_HOST}" --port "${WEB_PORT}"
