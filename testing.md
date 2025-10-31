# Stage 3 Testing Guide

## Complete Step-by-Step Testing for Local Development

---

## Prerequisites

Before starting, ensure you have:
- ✅ Stage 2 working (Blue/Green deployment with failover)
- ✅ Slack workspace access
- ✅ Slack webhook URL created
- ✅ Docker and Docker Compose installed

---

## Part 1: Setup (30 minutes)

### Step 1: Create Slack Webhook

1. Go to https://api.slack.com/apps
2. Click "Create New App" → "From scratch"
3. App Name: `Blue-Green Alerts`
4. Workspace: Select your workspace
5. Click "Incoming Webhooks" → Toggle ON
6. Click "Add New Webhook to Workspace"
7. Select channel: `#blue-green-alerts` (create if needed)
8. Copy the webhook URL (starts with `https://hooks.slack.com/services/`)

### Step 2: Update Project Structure

```bash
cd ~/blue-green-deployment

# Create alert-watcher directory
mkdir -p alert-watcher

# Your structure should now look like:
# blue-green-deployment/
# ├── alert-watcher/
# ├── mock-service/
# ├── docker-compose.yml
# ├── nginx.conf.template
# ├── setup.sh
# └── .env
```

### Step 3: Create Alert Watcher Files

Create `alert-watcher/watcher.py` (copy from artifact above)

Create `alert-watcher/requirements.txt`:
```
requests==2.31.0
```

Create `alert-watcher/Dockerfile` (copy from artifact above)

### Step 4: Update Docker Compose

Replace your `docker-compose.yml` with the Stage 3 version (from artifact above)

### Step 5: Update Nginx Configuration

Replace your `nginx.conf.template` with the Stage 3 version (from artifact above)

### Step 6: Update Environment File

```bash
# Update .env
cat > .env << 'EOF'
# Blue/Green Configuration
ACTIVE_POOL=blue
RELEASE_ID_BLUE=blue-v1.0.0
RELEASE_ID_GREEN=green-v1.0.0

# Slack Integration (REPLACE WITH YOUR WEBHOOK!)
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/YOUR/WEBHOOK/URL

# Alert Configuration
ERROR_RATE_THRESHOLD=2.0
WINDOW_SIZE=200
ALERT_COOLDOWN_SEC=300
MAINTENANCE_MODE=false
EOF

# Edit and add your actual webhook URL
nano .env
```

### Step 7: Create Runbook

Create `runbook.md` (copy from artifact above)

---

## Part 2: Build and Start (10 minutes)

### Step 1: Regenerate Nginx Config

```bash
./setup.sh
```

**Expected output:**
```
🔧 Blue/Green Deployment Setup
================================
✅ Configuration:
   Active Pool: blue
   Backup Pool: green

✅ nginx.conf generated successfully!
```

### Step 2: Stop Old Containers

```bash
docker-compose down
```

### Step 3: Build New Setup

```bash
docker-compose up -d --build
```

**Expected output:**
```
Building alert_watcher
...
Creating blue-green-deployment_nginx_1
Creating blue-green-deployment_app_blue_1
Creating blue-green-deployment_app_green_1
Creating blue-green-deployment_alert_watcher_1
```

### Step 4: Verify All Services Running

```bash
docker-compose ps
```

**Expected: All services should be "Up"**
```
NAME                                    STATUS
blue-green-deployment-nginx-1           Up
blue-green-deployment-app_blue-1        Up
blue-green-deployment-app_green-1       Up
blue-green-deployment-alert_watcher-1   Up
```

### Step 5: Check Watcher Logs

```bash
docker-compose logs alert_watcher
```

**Expected output:**
```
============================================================
  Blue/Green Deployment Alert Watcher
============================================================
📊 Starting log watcher...
📁 Log file: /var/log/nginx/access.log
🔗 Slack webhook: configured
📈 Error rate threshold: 2.0%
📊 Window size: 200 requests
⏰ Alert cooldown: 300 seconds
🔧 Maintenance mode: False

✅ Log file found, starting to tail...
```

---

## Part 3: Test Structured Logging (5 minutes)

### Test 1: Generate Some Traffic

```bash
# Make 10 requests
for i in {1..10}; do
  curl -s http://localhost:8080/version > /dev/null
  sleep 0.2
done
```

### Test 2: Check Nginx Logs

```bash
docker-compose exec nginx tail -n 5 /var/log/nginx/access.log
```

**Expected: JSON-formatted logs with pool info**
```json
{"time":"2025-10-27T14:32:15+00:00","remote_addr":"172.18.0.1","request_method":"GET","request_uri":"/version","status":200,"body_bytes_sent":123,"request_time":0.002,"upstream_addr":"172.18.0.2:3000","upstream_status":"200","upstream_response_time":"0.001","pool":"blue","release":"blue-v1.0.0"}
```

**✅ Checkpoint: You should see:**
- ✅ JSON format
- ✅ `"pool":"blue"`
- ✅ `"release":"blue-v1.0.0"`
- ✅ `"upstream_status":"200"`

### Test 3: Check Watcher Processing

```bash
docker-compose logs alert_watcher --tail=10
```

**Expected: Watcher processing logs**
```
[14:32:15] Pool: blue   | Status: 200 | Error Rate:  0.00%
[14:32:16] Pool: blue   | Status: 200 | Error Rate:  0.00%
[14:32:17] Pool: blue   | Status: 200 | Error Rate:  0.00%
```

---

## Part 4: Test Failover Alert (15 minutes)

This will generate a **Failover Detected** alert in Slack.

### Step 1: Verify Blue is Active

```bash
for i in {1..5}; do
  curl -s http://localhost:8080/version | grep -o '"pool":"[^"]*"'
done
```

**Expected:** All show `"pool":"blue"`

### Step 2: Trigger Chaos on Blue

```bash
curl -X POST "http://localhost:8081/chaos/start?mode=error"
```

**Expected response:**
```json
{"message":"Chaos started","mode":"error","pool":"blue"}
```

### Step 3: Generate Traffic to Trigger Failover

```bash
# Make 20 requests - this will trigger failover
for i in {1..20}; do
  echo "Request $i:"
  curl -s http://localhost:8080/version | grep -o '"pool":"[^"]*"'
  sleep 0.5
done
```

**Expected behavior:**
- First 1-2 requests: `"pool":"blue"` (or errors)
- Remaining requests: `"pool":"green"` (failover happened!)

### Step 4: Check Slack Channel

Go to your Slack channel (`#blue-green-alerts`)

**Expected: Slack alert received!**
```
🔄 Blue/Green Deployment Alert

Failover Detected!
• From: blue
• To: green
• Release: green-v1.0.0
• Upstream: app_green:3000
• Time: 2025-10-27 14:35:22
```

**📸 TAKE SCREENSHOT #1: Failover Alert in Slack**

### Step 5: Verify in Watcher Logs

```bash
docker-compose logs alert_watcher | grep -A 5 "Failover"
```

**Expected:**
```
✅ Slack alert sent: *Failover Detected!*...
```

### Step 6: Stop Chaos

```bash
curl -X POST "http://localhost:8081/chaos/stop"
```

---

## Part 5: Test Error Rate Alert (15 minutes)

This will generate a **High Error Rate** alert in Slack.

### Step 1: Verify Current State

```bash
# Blue should be recovered by now, but traffic still on Green
curl -s http://localhost:8080/version | grep -o '"pool":"[^"]*"'
```

### Step 2: Force Traffic Back to Blue

```bash
# Restart nginx to retry Blue
docker-compose restart nginx
sleep 5
```

### Step 3: Trigger Chaos Again

```bash
curl -X POST "http://localhost:8081/chaos/start?mode=error"
```

### Step 4: Generate High Error Rate

We need to generate enough errors to exceed 2% threshold.
With WINDOW_SIZE=200, we need >4 errors in 200 requests.

```bash
# Generate 250 requests (some will be errors)
echo "Generating traffic to trigger error-rate alert..."
for i in {1..250}; do
  curl -s http://localhost:8080/version > /dev/null 2>&1
  if [ $((i % 50)) -eq 0 ]; then
    echo "Progress: $i/250"
  fi
done
```

### Step 5: Check Watcher Logs for Error Rate

```bash
docker-compose logs alert_watcher --tail=20
```

**Expected: High error rate detected**
```
[14:40:15] Pool: green  | Status: 200 | Error Rate: 15.50%
✅ Slack alert sent: *High Error Rate Detected!*...
```

### Step 6: Check Slack Channel

Go to your Slack channel.

**Expected: Error rate alert received!**
```
🚨 Blue/Green Deployment Alert

High Error Rate Detected!
• Error Rate: 15.50% (threshold: 2.0%)
• Window Size: 200 requests
• Current Pool: green
• Action Required: Check upstream health
```

**📸 TAKE SCREENSHOT #2: High Error Rate Alert in Slack**

### Step 7: Stop Chaos

```bash
curl -X POST "http://localhost:8081/chaos/stop"
curl -X POST "http://localhost:8082/chaos/stop"
```

---

## Part 6: Verify Container Logs (5 minutes)

### Check Nginx Structured Logs

```bash
docker-compose exec nginx tail -n 10 /var/log/nginx/access.log | jq .
```

**Expected: Pretty-printed JSON**
```json
{
  "time": "2025-10-27T14:45:12+00:00",
  "remote_addr": "172.18.0.1",
  "request_method": "GET",
  "request_uri": "/version",
  "status": 200,
  "body_bytes_sent": 156,
  "request_time": 0.003,
  "upstream_addr": "172.18.0.3:3000",
  "upstream_status": "200",
  "upstream_response_time": "0.002",
  "pool": "green",
  "release": "green-v1.0.0"
}
```

**📸 TAKE SCREENSHOT #3: Container Logs showing structured logging**

---

## Part 7: Test Maintenance Mode (Optional - 5 minutes)

### Enable Maintenance Mode

```bash
# Update .env
sed -i 's/MAINTENANCE_MODE=false/MAINTENANCE_MODE=true/' .env

# Restart watcher to pick up change
docker-compose restart alert_watcher

# Check logs
docker-compose logs alert_watcher | tail -5
```

**Expected:**
```
🔧 Maintenance mode: True
```

### Trigger Failover (Should NOT Alert)

```bash
# Trigger chaos
curl -X POST "http://localhost:8081/chaos/start?mode=error"

# Generate traffic
for i in {1..10}; do
  curl -s http://localhost:8080/version > /dev/null
done

# Check watcher logs
docker-compose logs alert_watcher --tail=10
```

**Expected:**
```
🔧 Maintenance mode: Suppressing failover alert
```

**No Slack alert should be sent!**

### Disable Maintenance Mode

```bash
sed -i 's/MAINTENANCE_MODE=true/MAINTENANCE_MODE=false/' .env
docker-compose restart alert_watcher
curl -X POST "http://localhost:8081/chaos/stop"
```

---

## Part 8: Verify All Requirements

### ✅ Checklist

- [ ] Nginx logs show structured JSON format
- [ ] Nginx logs include: pool, release, upstream_status, upstream_addr
- [ ] Alert watcher container running and processing logs
- [ ] Failover alert received in Slack (Screenshot #1)
- [ ] Error-rate alert received in Slack (Screenshot #2)
- [ ] Container logs screenshot (Screenshot #3)
- [ ] Runbook.md exists and is complete
- [ ] README.md updated with Stage 3 instructions
- [ ] .env.example includes all new variables
- [ ] Stage 2 tests still pass (basic failover works)

---

## Part 9: Create Screenshots for Submission

### Screenshot 1: Failover Alert
- **What:** Slack message showing failover detection
- **Must show:**
  - "Failover Detected!" heading
  - From/To pools
  - Release ID
  - Timestamp
  - Full message visible

### Screenshot 2: High Error Rate Alert
- **What:** Slack message showing error rate threshold breach
- **Must show:**
  - "High Error Rate Detected!" heading
  - Error rate percentage
  - Threshold
  - Window size
  - Full message visible

### Screenshot 3: Container Logs
- **What:** Terminal showing structured Nginx logs
- **Must show:**
  - JSON-formatted log entries
  - Fields: pool, release, upstream_status
  - Multiple log lines
  - Readable text

---

## Troubleshooting Common Issues

### Issue: No Slack Alerts Received

**Check 1: Webhook URL**
```bash
echo $SLACK_WEBHOOK_URL
# Should start with https://hooks.slack.com/services/
```

**Check 2: Test webhook manually**
```bash
curl -X POST $SLACK_WEBHOOK_URL \
  -H 'Content-Type: application/json' \
  -d '{"text":"Test from command line"}'
```

**Check 3: Watcher logs**
```bash
docker-compose logs alert_watcher | grep -i slack
```

### Issue: Watcher Shows "Slack webhook: NOT CONFIGURED"

```bash
# Check if .env is loaded
docker-compose config | grep SLACK_WEBHOOK

# If empty, rebuild:
docker-compose down
docker-compose up -d --build
```

### Issue: Logs Don't Show JSON Format

```bash
# Check nginx.conf was generated with log format
cat nginx.conf | grep -A 10 "log_format"

# Should show the detailed_upstream format

# If not, regenerate:
./setup.sh
docker-compose restart nginx
```

### Issue: Failover Not Triggering Alert

```bash
# Verify watcher sees the pool change
docker-compose logs alert_watcher --tail=50 | grep Pool

# Should show pool changing from blue to green
```

---

## Clean Up After Testing

```bash
# Stop all services
docker-compose down

# Remove volumes (if you want fresh start)
docker-compose down -v

# Keep screenshots and logs for submission!
```

---

## Final Verification Before Submission

Run this complete test one more time:

```bash
# 1. Clean start
docker-compose down -v
./setup.sh
docker-compose up -d --build
sleep 15

# 2. Test failover
curl -X POST "http://localhost:8081/chaos/start?mode=error"
for i in {1..20}; do curl -s http://localhost:8080/version > /dev/null; sleep 0.3; done

# 3. Wait for Slack alert (check #blue-green-alerts channel)

# 4. Test error rate
for i in {1..250}; do curl -s http://localhost:8080/version > /dev/null 2>&1; done

# 5. Wait for Slack alert

# 6. Take screenshots

# 7. Stop chaos
curl -X POST "http://localhost:8081/chaos/stop"
curl -X POST "http://localhost:8082/chaos/stop"
```

**✅ You're ready to submit when:**
1. All 3 screenshots captured
2. Both alert types received in Slack
3. Stage 2 tests still pass
4. Runbook complete
5. README updated

---

Good luck! 🚀