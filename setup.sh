#!/bin/bash
set -e

echo "🔧 Blue/Green Deployment Setup"
echo "================================"

if [ ! -f .env ]; then
    echo "❌ Error: .env file not found"
    echo "Run: cp .env.example .env"
    exit 1
fi

source .env

# Validate ACTIVE_POOL
if [ "$ACTIVE_POOL" != "blue" ] && [ "$ACTIVE_POOL" != "green" ]; then
    echo "❌ Error: ACTIVE_POOL must be 'blue' or 'green'"
    exit 1
fi

# Determine backup pool
if [ "$ACTIVE_POOL" = "blue" ]; then
    export BACKUP_POOL="green"
else
    export BACKUP_POOL="blue"
fi

echo "✅ Configuration:"
echo "   Active Pool: $ACTIVE_POOL"
echo "   Backup Pool: $BACKUP_POOL"
echo ""

# IMPORTANT: The template uses ${ACTIVE_POOL} and ${BACKUP_POOL}
# which will be replaced with "blue" or "green"
# The resulting nginx.conf will have: server app_blue:3000
# because the template has: server app_${ACTIVE_POOL}:3000

echo "📝 Generating nginx.conf from template..."
envsubst '${ACTIVE_POOL} ${BACKUP_POOL}' < nginx.conf.template > nginx.conf

echo "✅ nginx.conf generated successfully!"
echo ""

# Verify the generated config
echo "📋 Verifying generated configuration..."
if grep -q "server app_${ACTIVE_POOL}:3000" nginx.conf; then
    echo "✅ Active pool: app_${ACTIVE_POOL}"
fi

if grep -q "server app_${BACKUP_POOL}:3000" nginx.conf; then
    echo "✅ Backup pool: app_${BACKUP_POOL}"
fi

echo ""
echo "Next step: docker-compose up -d --build"