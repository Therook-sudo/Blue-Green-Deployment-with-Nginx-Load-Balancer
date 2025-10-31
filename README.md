# Blue/Green Deployment with Monitoring & Alerts

A production-ready Blue/Green deployment system with Nginx load balancing, automatic failover, real-time monitoring, and Slack alerting.

## 🎯 Overview

This project implements:
- **Blue/Green Deployment**: Two identical services with automatic failover
- **Nginx Load Balancer**: Reverse proxy with health-based routing  
- **Real-time Monitoring**: Python log watcher tracking deployment health
- **Slack Alerts**: Instant notifications on failovers and error spikes
- **Operational Runbook**: Clear guidance for on-call engineers

## 🏗️ Architecture

```
                    ┌─────────────┐
                    │   Client    │
                    └──────┬──────┘
                           │
                           │ http://localhost:8080
                           ▼
                    ┌─────────────┐
                    │    Nginx    │────┐
                    │  (Port 80)  │    │ Structured
                    └──────┬──────┘    │ JSON Logs
                           │           ▼
            ┌──────────────┴───────┬──────────────┐
            │                      │ Alert Watcher│
            ▼                      │  (Python)    │
     ┌─────────────┐              └──────┬───────┘
     │  Blue Pool  │                     │
     │  Port 8081  │                     ▼
     └─────────────┘              ┌──────────────┐
            ▼                     │    Slack     │
     ┌─────────────┐              │   Channel    │
     │ Green Pool  │              └──────────────┘
     │  Port 8082  │
     └─────────────┘
```

## ✨ Features

### Stage 2 (Baseline)
- ✅ Automatic failover (Blue ↔ Green)
- ✅ Zero downtime during failures
- ✅ Chaos engineering support
- ✅ Header-based pool identification

### Stage 3 (Monitoring & Alerts)
- ✅ **Structured JSON logging** - All request details captured
- ✅ **Real-time log analysis** - Python watcher processes logs continuously
- ✅ **Failover detection** - Alerts when traffic switches pools
- ✅ **Error rate monitoring** - Tracks 5xx errors over sliding window
- ✅ **Slack integration** - Instant alerts to your team channel
- ✅ **Alert deduplication** - Cooldown periods prevent spam
- ✅ **Maintenance mode** - Suppress alerts during planned changes
- ✅ **Operational runbook** - Clear response procedures

## 🚀 Quick Start

### Prerequisites

- Docker & Docker Compose
- Slack workspace with webhook access
- `envsubst` (part of `gettext-base`)
- Linux/macOS (or WSL2 on Windows)

### Installation

**1. Clone repository**
```bash
git clone https://github.com/yourusername/blue-green-deployment.git
cd blue-green-deployment
```

**2. Create Slack webhook**
- Go to https://api.slack.com/apps
- Create new app → Incoming Webhooks
- Copy webhook URL

**3. Configure environment**
```bash
cp .env.example .env
nano .env  # Add your SLACK_WEBHOOK_URL
```

**4. Generate Nginx config**
```bash
chmod +x setup.sh
./setup.sh
```

**5. Start all services**
```bash
docker-compose up -d --build
```

**6. Verify deployment**
```bash
# Check all containers running
docker-compose ps

# Test endpoint
curl http://localhost:8080/version

# Watch alert watcher
docker-compose logs alert_watcher --follow
```

## 🧪 Testing

### Test 1: Basic Failover

```bash
# Verify Blue is active
for i in {1..5}; do
  curl -s http://localhost:8080/version | grep -o '"pool":"[^"]*"'
done

# Trigger chaos on Blue
curl -X POST "http://localhost:8081/chaos/start?mode=error"

# Watch automatic failover to Green
for i in {1..20}; do
  curl -s http://localhost:8080/version | grep -o '"pool":"[^"]*"'
  sleep 0.5
done

# Stop chaos
curl -X POST "http://localhost:8081/chaos/stop"
```

**Expected:**
- ✅ All requests return HTTP 200
- ✅ Pool switches from `blue` to `green`
- ✅ Slack alert: "Failover Detected!"

### Test 2: Error Rate Alert

```bash
# Trigger chaos
curl -X POST "http://localhost:8081/chaos/start?mode=error"

# Generate high error traffic
for i in {1..250}; do
  curl -s http://localhost:8080/version > /dev/null 2>&1
done

# Stop chaos
curl -X POST "http://localhost:8081/chaos/stop"
```

**Expected:**
- ✅ Error rate exceeds threshold (2%)
- ✅ Slack alert: "High Error Rate Detected!"

### Test 3: Structured Logging

```bash
# View structured logs
docker-compose exec nginx tail -f /var/log/nginx/access.log

# Pretty-print JSON
docker-compose exec nginx tail -5 /var/log/nginx/access.log | jq .
```

**Expected log format:**
```json
{
  "time": "2025-10-27T14:32:15+00:00",
  "pool": "blue",
  "release": "blue-v1.0.0",
  "status": 200,
  "upstream_status": "200",
  "upstream_addr": "172.18.0.2:3000",
  "request_time": 0.003
}
```

## 📊 Monitoring

### View Real-Time Metrics

```bash
# Alert watcher output
docker-compose logs alert_watcher --follow

# Nginx access logs
docker-compose exec nginx tail -f /var/log/nginx/access.log

# Specific pool logs
docker-compose logs app_blue --follow
docker-compose logs app_green --follow
```

### Check Current State

```bash
# Active pool
curl -s http://localhost:8080/version | jq -r '.pool'

# Error rate
docker-compose logs alert_watcher --tail=5

# Container status
docker-compose ps
```

## 🔔 Slack Alerts

### Alert Types

#### 🔄 Failover Detected
```
Failover Detected!
• From: blue
• To: green
• Release: green-v1.0.0
• Upstream: app_green:3000
• Time: 2025-10-27 14:32:15
```

**Triggers when:**
- Traffic switches from one pool to another
- Nginx detects primary pool failure

#### 🚨 High Error Rate
```
High Error Rate Detected!
• Error Rate: 15.50% (threshold: 2.0%)
• Window Size: 200 requests
• Current Pool: blue
• Action Required: Check upstream health
```

**Triggers when:**
- 5xx error rate exceeds threshold
- Calculated over sliding window

### Alert Configuration

Adjust in `.env`:

```bash
ERROR_RATE_THRESHOLD=2.0    # Percentage (2.0 = 2%)
WINDOW_SIZE=200             # Requests to track
ALERT_COOLDOWN_SEC=300      # Seconds between alerts
MAINTENANCE_MODE=false      # Suppress failover alerts
```

## 📋 Endpoints

### Via Nginx (Port 8080)
- `GET /` - Service information
- `GET /version` - Version with pool headers
- `GET /healthz` - Health check
- `POST /chaos/start?mode=error|timeout` - Simulate failure
- `POST /chaos/stop` - Stop simulation

### Direct Access
- **Blue**: `http://localhost:8081/*`
- **Green**: `http://localhost:8082/*`

## ⚙️ Configuration

### Environment Variables (.env)

```bash
# Deployment
ACTIVE_POOL=blue
RELEASE_ID_BLUE=blue-v1.0.0
RELEASE_ID_GREEN=green-v1.0.0

# Slack
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/YOUR/WEBHOOK/URL

# Monitoring
ERROR_RATE_THRESHOLD=2.0
WINDOW_SIZE=200
ALERT_COOLDOWN_SEC=300
MAINTENANCE_MODE=false
```

### Nginx Failover Settings

```nginx
upstream backend {
    server app_blue:3000 max_fails=1 fail_timeout=5s;
    server app_green:3000 backup;
}

proxy_connect_timeout 2s;
proxy_send_timeout 2s;
proxy_read_timeout 2s;
```

## 📖 Operational Runbook

See [runbook.md](./runbook.md) for detailed response procedures:

- 🔄 **Failover Alert** → Check primary pool health
- 🚨 **Error Rate Alert** → Investigate upstream logs
- 🔧 **Maintenance Mode** → Suppress alerts during changes
- ⚡ **Manual Failover** → Force pool switch

## 🏗️ Project Structure

```
blue-green-deployment/
├── README.md                    # This file
├── runbook.md                   # Operations guide
├── DECISION.md                  # Architecture decisions
├── STAGE3-TESTING.md           # Testing guide
├── .env.example                 # Environment template
├── .gitignore
├── docker-compose.yml           # Container orchestration
├── nginx.conf.template          # Nginx config template
├── setup.sh                     # Config generator
├── test-failover.sh             # Basic failover test
├── mock-service/                # Node.js application
│   ├── Dockerfile
│   ├── package.json
│   └── app.js
└── alert-watcher/               # Monitoring service
    ├── Dockerfile
    ├── requirements.txt
    └── watcher.py
```

## 🔍 Troubleshooting

### No Slack Alerts Received

```bash
# Check webhook URL
echo $SLACK_WEBHOOK_URL

# Test webhook manually
curl -X POST $SLACK_WEBHOOK_URL \
  -H 'Content-Type: application/json' \
  -d '{"text":"Test alert"}'

# Check watcher logs
docker-compose logs alert_watcher | grep -i slack
```

### Watcher Not Starting

```bash
# Check container status
docker-compose ps alert_watcher

# View logs
docker-compose logs alert_watcher

# Rebuild
docker-compose up -d --build alert_watcher
```

### Logs Not JSON Formatted

```bash
# Verify nginx.conf has log_format
cat nginx.conf | grep -A 10 "log_format"

# Regenerate if needed
./setup.sh
docker-compose restart nginx
```

## 📸 Screenshots (For Submission)

Required screenshots:
1. **Failover Alert** - Slack message showing Blue→Green failover
2. **Error Rate Alert** - Slack message showing high error rate
3. **Container Logs** - Terminal showing structured JSON logs

See [STAGE3-TESTING.md](./STAGE3-TESTING.md) for screenshot guidelines.

## 🤝 Contributing

Contributions welcome! Please:
1. Fork the repository
2. Create feature branch
3. Test thoroughly
4. Submit pull request

## 📝 License

MIT License - see LICENSE file for details

## 🔗 Related Documentation

- [runbook.md](./runbook.md) - Operational procedures
- [DECISION.md](./DECISION.md) - Architecture decisions
- [STAGE3-TESTING.md](./STAGE3-TESTING.md) - Complete testing guide
- [Docker Compose Docs](https://docs.docker.com/compose/)
- [Nginx Upstream Module](http://nginx.org/en/docs/http/ngx_http_upstream_module.html)

## 📞 Support

- Check [runbook.md](./runbook.md) for common issues
- Review logs: `docker-compose logs`
- Open GitHub issue for bugs

---

**Built with ❤️ for reliable, observable deployments**

**Stage 2 Complete** ✅ Zero-downtime failover  
**Stage 3 Complete** ✅ Real-time monitoring & alerts