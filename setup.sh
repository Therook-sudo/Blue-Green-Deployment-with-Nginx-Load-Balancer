#!/bin/bash
set -e

if [ ! -f .env ]; then
    echo "❌ Error: .env file not found"
    exit 1
fi

source .env

if [ "$ACTIVE_POOL" = "blue" ]; then
    export BACKUP_POOL="green"
elif [ "$ACTIVE_POOL" = "green" ]; then
    export BACKUP_POOL="blue"
else
    echo "❌ Error: ACTIVE_POOL must be 'blue' or 'green'"
    exit 1
fi

echo "✅ Configuration:"
echo "   Active Pool: $ACTIVE_POOL"
echo "   Backup Pool: $BACKUP_POOL"

envsubst '${ACTIVE_POOL} ${BACKUP_POOL}' < nginx.conf.template > nginx.conf

echo "✅ nginx.conf generated!"
echo ""
echo "Generated upstream configuration:"
cat nginx.conf | grep -A 2 "upstream backend"

chmod +x setup.sh