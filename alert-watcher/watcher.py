#!/usr/bin/env python3
import json
import os
import time
import requests
from collections import deque
from datetime import datetime
from pathlib import Path

SLACK_WEBHOOK_URL = os.environ.get('SLACK_WEBHOOK_URL', '')
ERROR_RATE_THRESHOLD = float(os.environ.get('ERROR_RATE_THRESHOLD', '2.0'))
WINDOW_SIZE = int(os.environ.get('WINDOW_SIZE', '200'))
ALERT_COOLDOWN_SEC = int(os.environ.get('ALERT_COOLDOWN_SEC', '300'))
MAINTENANCE_MODE = os.environ.get('MAINTENANCE_MODE', 'false').lower() == 'true'

LOG_FILE = '/var/log/nginx/access.log'

last_pool = None
request_window = deque(maxlen=WINDOW_SIZE)
last_failover_alert = 0
last_error_rate_alert = 0

def send_slack_alert(message, alert_type="info"):
    if not SLACK_WEBHOOK_URL:
        print(f"⚠️  No Slack webhook. Alert: {message}")
        return
    
    if MAINTENANCE_MODE and alert_type == "failover":
        print(f"🔧 Maintenance mode: Suppressing failover alert")
        return
    
    colors = {
        "failover": "#FF9800",
        "error": "#F44336",
        "recovery": "#4CAF50",
        "info": "#2196F3"
    }
    
    icons = {
        "failover": "🔄",
        "error": "🚨",
        "recovery": "✅",
        "info": "ℹ️"
    }
    
    payload = {
        "attachments": [{
            "color": colors.get(alert_type, "#2196F3"),
            "title": f"{icons.get(alert_type, '📢')} Blue/Green Deployment Alert",
            "text": message,
            "footer": "Blue/Green Monitor",
            "ts": int(time.time())
        }]
    }
    
    try:
        response = requests.post(SLACK_WEBHOOK_URL, json=payload, timeout=5)
        if response.status_code == 200:
            print(f"✅ Slack alert sent: {message[:50]}...")
        else:
            print(f"❌ Slack alert failed: {response.status_code}")
    except Exception as e:
        print(f"❌ Error sending Slack alert: {e}")

def check_cooldown(alert_type):
    global last_failover_alert, last_error_rate_alert
    
    now = time.time()
    
    if alert_type == "failover":
        if now - last_failover_alert < ALERT_COOLDOWN_SEC:
            return False
        last_failover_alert = now
        return True
    
    elif alert_type == "error_rate":
        if now - last_error_rate_alert < ALERT_COOLDOWN_SEC:
            return False
        last_error_rate_alert = now
        return True
    
    return True

def calculate_error_rate():
    if len(request_window) == 0:
        return 0.0
    
    error_count = sum(1 for status in request_window if status >= 500)
    return (error_count / len(request_window)) * 100

def process_log_line(line):
    global last_pool
    
    try:
        log = json.loads(line.strip())
        
        pool = log.get('pool', 'unknown')
        release = log.get('release', 'unknown')
        status = int(log.get('status', 0))
        upstream_status = log.get('upstream_status', '')
        upstream_addr = log.get('upstream_addr', '')
        
        request_window.append(status)
        
        if last_pool is not None and pool != last_pool and pool != 'unknown':
            if check_cooldown("failover"):
                message = (
                    f"*Failover Detected!*\n"
                    f"• From: `{last_pool}`\n"
                    f"• To: `{pool}`\n"
                    f"• Release: `{release}`\n"
                    f"• Upstream: `{upstream_addr}`\n"
                    f"• Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
                )
                send_slack_alert(message, "failover")
        
        if pool != 'unknown':
            last_pool = pool
        
        if len(request_window) >= WINDOW_SIZE:
            error_rate = calculate_error_rate()
            
            if error_rate > ERROR_RATE_THRESHOLD:
                if check_cooldown("error_rate"):
                    message = (
                        f"*High Error Rate Detected!*\n"
                        f"• Error Rate: `{error_rate:.2f}%` (threshold: {ERROR_RATE_THRESHOLD}%)\n"
                        f"• Window Size: {WINDOW_SIZE} requests\n"
                        f"• Current Pool: `{pool}`\n"
                        f"• Action Required: Check upstream health"
                    )
                    send_slack_alert(message, "error")
        
        print(f"[{datetime.now().strftime('%H:%M:%S')}] "
              f"Pool: {pool:6s} | Status: {status} | "
              f"Error Rate: {calculate_error_rate():5.2f}%")
        
    except json.JSONDecodeError:
        pass
    except Exception as e:
        print(f"Error processing log line: {e}")

def tail_log_file(filepath):
    print(f"📊 Starting log watcher...")
    print(f"📁 Log file: {filepath}")
    print(f"🔗 Slack webhook: {'configured' if SLACK_WEBHOOK_URL else 'NOT CONFIGURED'}")
    print(f"📈 Error rate threshold: {ERROR_RATE_THRESHOLD}%")
    print(f"📊 Window size: {WINDOW_SIZE} requests")
    print(f"⏰ Alert cooldown: {ALERT_COOLDOWN_SEC} seconds")
    print(f"🔧 Maintenance mode: {MAINTENANCE_MODE}")
    print("")
    
    while not Path(filepath).exists():
        print(f"⏳ Waiting for log file {filepath}...")
        time.sleep(2)
    
    print(f"✅ Log file found, starting to tail...\n")
    
    # Use a different approach - read from current position without seeking
    with open(filepath, 'r') as f:
        # Read existing lines to get to end
        for line in f:
            pass  # Skip existing lines
        
        # Now tail new lines
        while True:
            line = f.readline()
            if line:
                process_log_line(line)
            else:
                time.sleep(0.1)

def main():
    print("="*60)
    print("  Blue/Green Deployment Alert Watcher")
    print("="*60)
    
    if not SLACK_WEBHOOK_URL:
        print("⚠️  WARNING: SLACK_WEBHOOK_URL not set.")
        print("")
    
    try:
        tail_log_file(LOG_FILE)
    except KeyboardInterrupt:
        print("\n\n👋 Shutting down gracefully...")
    except Exception as e:
        print(f"\n❌ Fatal error: {e}")
        import traceback
        traceback.print_exc()
        raise

if __name__ == '__main__':
    main()