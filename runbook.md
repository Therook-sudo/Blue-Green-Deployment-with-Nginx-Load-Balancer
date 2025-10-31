# Blue/Green Deployment Operations Runbook

## Overview

This runbook provides operational guidance for responding to alerts from the Blue/Green deployment monitoring system.

---

## Alert Types

### 🔄 Failover Detected

**Alert Message:**
```
Failover Detected!
• From: blue
• To: green
• Release: green-v1.0.0
• Upstream: app_green:3000
• Time: 2025-10-27 14:32:15
```

**What it means:**
- Traffic has automatically switched from one pool to another
- This typically indicates the primary pool (Blue) has become unhealthy
- Nginx detected failures and is now routing to the backup pool (Green)

**Operator Actions:**

1. **Investigate Primary Pool Health**
   ```bash
   # Check container status
   docker-compose ps
   
   # Check primary pool logs
   docker-compose logs app_blue --tail=100
   
   # Test primary pool directly
   curl http://localhost:8081/healthz
   curl http://localhost:8081/version
   ```

2. **Verify Failover Success**
   ```bash
   # Confirm traffic is going to Green
   curl -i http://localhost:8080/version | grep X-App-Pool
   # Should show: X-App-Pool: green
   
   # Make several requests to ensure stability
   for i in {1..10}; do
     curl -s http://localhost:8080/version | grep -o '"pool":"[^"]*"'
   done
   ```

3. **Check for Chaos Mode**
   ```bash
   # If chaos was triggered intentionally, stop it
   curl -X POST http://localhost:8081/chaos/stop
   
   # Wait 5-10 seconds for recovery
   sleep 10
   
   # Verify Blue is healthy again
   curl http://localhost:8081/version
   ```

4. **Determine If Action Is Needed**
   - **If chaos mode**: No action needed, this was expected
   - **If unplanned**: Investigate Blue container logs for errors
   - **If Blue is crashed**: Restart the container
     ```bash
     docker-compose restart app_blue
     ```

5. **Monitor Recovery**
   - After Blue recovers, traffic will automatically return to Blue (after fail_timeout)
   - Watch for a "recovery" failover alert (Green → Blue)

**Expected Recovery Time:**
- Failover detection: ~2 seconds
- Recovery attempt: 5 seconds (configurable via fail_timeout)
- Total: ~7 seconds from failure to recovery attempt

---

### 🚨 High Error Rate Detected

**Alert Message:**
```
High Error Rate Detected!
• Error Rate: 15.50% (threshold: 2.0%)
• Window Size: 200 requests
• Current Pool: blue
• Action Required: Check upstream health
```

**What it means:**
- The current active pool is returning excessive 5xx errors
- Error rate exceeded the configured threshold (default: 2%)
- Calculated over a sliding window (default: last 200 requests)

**Operator Actions:**

1. **Identify Current Active Pool**
   ```bash
   # Check which pool is serving
   curl -s http://localhost:8080/version | grep -o '"pool":"[^"]*"'
   ```

2. **Check Upstream Logs**
   ```bash
   # If Blue is active
   docker-compose logs app_blue --tail=50 --follow
   
   # If Green is active
   docker-compose logs app_green --tail=50 --follow
   ```

3. **Check Nginx Error Logs**
   ```bash
   docker-compose exec nginx cat /var/log/nginx/error.log
   ```

4. **Test Upstream Health**
   ```bash
   # Test Blue
   curl http://localhost:8081/healthz
   curl http://localhost:8081/version
   
   # Test Green
   curl http://localhost:8082/healthz
   curl http://localhost:8082/version
   ```

5. **Determine Root Cause**
   Common causes:
   - Application bug or crash
   - Resource exhaustion (CPU/memory)
   - Database connection issues
   - Dependency service failure
   - Configuration error

6. **Mitigation Options**

   **Option A: Force Failover (if other pool is healthy)**
   ```bash
   # If Blue is failing and Green is healthy
   # Update .env
   ACTIVE_POOL=green
   
   # Regenerate nginx config
   ./setup.sh
   
   # Reload Nginx
   docker-compose restart nginx
   ```

   **Option B: Restart Failing Container**
   ```bash
   docker-compose restart app_blue
   # or
   docker-compose restart app_green
   ```

   **Option C: Roll Back Release**
   ```bash
   # If a recent deployment caused the issue
   # Update image tags in docker-compose.yml
   # Or update RELEASE_ID in .env
   
   docker-compose up -d --force-recreate app_blue
   ```

7. **Verify Error Rate Drops**
   ```bash
   # Monitor the alert_watcher logs
   docker-compose logs alert_watcher --tail=20 --follow
   
   # Watch for error rate to drop below threshold
   ```

**When to Escalate:**
- Error rate remains above threshold for >5 minutes
- Both pools are returning errors
- Underlying infrastructure issues (database down, etc.)

---

### ✅ Recovery (Implicit)

**What it means:**
- The system has automatically recovered
- Primary pool is healthy again
- Traffic may have returned to primary

**Operator Actions:**
1. **Verify Stability**
   ```bash
   # Make continuous requests to ensure no errors
   for i in {1..50}; do
     curl -s http://localhost:8080/version
     sleep 0.5
   done
   ```

2. **Review Incident Timeline**
   - Check alert timestamps
   - Review logs for root cause
   - Document in incident log

3. **No Further Action Required**
   - System is self-healing
   - Continue normal monitoring

---

## Planned Maintenance

### Suppressing Alerts During Maintenance

When performing planned pool switches or deployments:

```bash
# Set maintenance mode in .env
MAINTENANCE_MODE=true

# Reload configuration
docker-compose up -d alert_watcher

# Perform maintenance...
# (failover alerts will be suppressed)

# After maintenance, disable maintenance mode
MAINTENANCE_MODE=false
docker-compose up -d alert_watcher
```

**Note:** Error-rate alerts are NOT suppressed during maintenance mode.

---

## Manual Pool Switch

To manually switch active pools:

```bash
# 1. Update .env
#    Change: ACTIVE_POOL=blue
#    To:     ACTIVE_POOL=green

# 2. Regenerate nginx config
./setup.sh

# 3. Reload Nginx (no downtime)
docker-compose restart nginx

# 4. Verify switch
curl -i http://localhost:8080/version | grep X-App-Pool
# Should show: X-App-Pool: green
```

---

## Testing Alerts

### Test Failover Alert

```bash
# Trigger chaos on Blue
curl -X POST http://localhost:8081/chaos/start?mode=error

# Make requests to trigger failover
for i in {1..10}; do
  curl -s http://localhost:8080/version
  sleep 0.5
done

# Check Slack for failover alert
# Check watcher logs
docker-compose logs alert_watcher --tail=20

# Stop chaos
curl -X POST http://localhost:8081/chaos/stop
```

### Test Error Rate Alert

```bash
# Trigger chaos on active pool
curl -X POST http://localhost:8081/chaos/start?mode=error

# Generate enough traffic to exceed threshold
# (need ~5+ errors in 200 requests = 2.5% error rate)
for i in {1..250}; do
  curl -s http://localhost:8080/version > /dev/null
done

# Check Slack for error-rate alert
# Stop chaos
curl -X POST http://localhost:8081/chaos/stop
```

---

## Monitoring Commands

### Check Current State

```bash
# Which pool is active?
curl -s http://localhost:8080/version | jq -r '.pool'

# Current error rate
docker-compose logs alert_watcher --tail=5

# Recent failovers
docker-compose logs alert_watcher | grep "Failover"

# Container status
docker-compose ps
```

### View Logs

```bash
# All services
docker-compose logs --tail=50 --follow

# Nginx access logs (structured JSON)
docker-compose exec nginx tail -f /var/log/nginx/access.log

# Alert watcher
docker-compose logs alert_watcher --follow

# Specific pool
docker-compose logs app_blue --follow
```

### Health Checks

```bash
# Public endpoint (via Nginx)
curl http://localhost:8080/healthz

# Blue direct
curl http://localhost:8081/healthz

# Green direct
curl http://localhost:8082/healthz
```

---

## Configuration Reference

### Alert Thresholds

Adjust in `.env`:

```bash
# Error rate threshold (percentage)
ERROR_RATE_THRESHOLD=2.0

# Number of requests to track
WINDOW_SIZE=200

# Cooldown between duplicate alerts (seconds)
ALERT_COOLDOWN_SEC=300
```

### Nginx Failover Settings

In `nginx.conf.template`:

```nginx
# Mark server as failed after 1 error
max_fails=1

# Try again after 5 seconds
fail_timeout=5s

# Timeout before retrying backup
proxy_connect_timeout 2s
proxy_send_timeout 2s
proxy_read_timeout 2s
```

---

## Troubleshooting

### Alert Not Received in Slack

1. **Check webhook URL**
   ```bash
   echo $SLACK_WEBHOOK_URL
   # Should be: https://hooks.slack.com/services/...
   ```

2. **Test webhook manually**
   ```bash
   curl -X POST $SLACK_WEBHOOK_URL \
     -H 'Content-Type: application/json' \
     -d '{"text":"Test alert"}'
   ```

3. **Check watcher logs**
   ```bash
   docker-compose logs alert_watcher
   # Look for "Slack alert sent" or error messages
   ```

### False Positive Alerts

**If failover alerts trigger too frequently:**
- Increase `fail_timeout` in nginx.conf
- Check for network instability
- Review application performance

**If error-rate alerts trigger too frequently:**
- Increase `ERROR_RATE_THRESHOLD`
- Increase `WINDOW_SIZE`
- Investigate root cause of errors

### Watcher Not Starting

```bash
# Check watcher container status
docker-compose ps alert_watcher

# View watcher logs
docker-compose logs alert_watcher

# Common issues:
# - Missing nginx logs volume
# - Invalid Python syntax
# - Missing requirements

# Rebuild if needed
docker-compose up -d --build alert_watcher
```

---

## Escalation

Contact the on-call engineer if:
- Both pools are failing (no healthy upstream)
- Error rate persists above threshold for >10 minutes
- Failover loop detected (Blue→Green→Blue repeatedly)
- Infrastructure-level issues (database, network, etc.)
- Alert system itself is down

**Escalation Contact:** [Your team's escalation process]

---

## Appendix: Alert Examples

### Successful Failover Example
```
🔄 Blue/Green Deployment Alert
Failover Detected!
• From: blue
• To: green
• Release: green-v1.0.0
• Upstream: app_green:3000
• Time: 2025-10-27 14:32:15

✅ Action taken: Verified Green is healthy, investigated Blue logs
✅ Outcome: Chaos mode was active, stopped and Blue recovered
```

### High Error Rate Example
```
🚨 Blue/Green Deployment Alert
High Error Rate Detected!
• Error Rate: 15.50% (threshold: 2.0%)
• Window Size: 200 requests
• Current Pool: blue
• Action Required: Check upstream health

✅ Action taken: Restarted app_blue container
✅ Outcome: Error rate dropped to 0.5%, system stable
```

---

**Last Updated:** October 27, 2025  
**Version:** 3.0  
**Maintained By:** DevOps Team