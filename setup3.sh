#!/bin/bash
# Quick setup script for Stage 3

set -e

echo "╔════════════════════════════════════════════════╗"
echo "║  Stage 3: Monitoring & Alerts Setup           ║"
echo "╚════════════════════════════════════════════════╝"
echo ""

# Check if we're in the right directory
if [ ! -f "docker-compose.yml" ]; then
    echo "❌ Error: docker-compose.yml not found"
    echo "Please run this script from the blue-green-deployment directory"
    exit 1
fi

echo "📁 Creating alert-watcher directory..."
mkdir -p alert-watcher

echo "✅ Directory created"
echo ""

echo "📝 Next steps:"
echo ""
echo "1. Copy the following files from the artifacts:"
echo "   - alert-watcher/watcher.py"
echo "   - alert-watcher/requirements.txt"
echo "   - alert-watcher/Dockerfile"
echo "   - nginx.conf.template (updated version)"
echo "   - docker-compose.yml (updated version)"
echo "   - runbook.md"
echo "   - STAGE3-TESTING.md"
echo ""
echo "2. Create your Slack webhook:"
echo "   https://api.slack.com/apps"
echo ""
echo "3. Update .env with your webhook URL:"
echo "   SLACK_WEBHOOK_URL=https://hooks.slack.com/services/YOUR/WEBHOOK/URL"
echo ""
echo "4. Regenerate nginx config:"
echo "   ./setup.sh"
echo ""
echo "5. Start services:"
echo "   docker-compose down"
echo "   docker-compose up -d --build"
echo ""
echo "6. Watch logs:"
echo "   docker-compose logs alert_watcher --follow"
echo ""
echo "7. Test failover:"
echo "   curl -X POST http://localhost:8081/chaos/start?mode=error"
echo "   for i in {1..20}; do curl -s http://localhost:8080/version; sleep 0.5; done"
echo ""
echo "8. Check Slack for alerts!"
echo ""