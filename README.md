# Blue/Green Deployment with Nginx Load Balancer

A production-ready Blue/Green deployment system using Docker Compose and Nginx with automatic failover capabilities and zero-downtime deployment.

## 🎯 Overview

This project demonstrates a Blue/Green deployment pattern where:
- **Blue** and **Green** are identical Node.js services running as separate containers
- **Nginx** acts as a reverse proxy and load balancer
- Traffic automatically fails over from Blue to Green when Blue becomes unhealthy
- **Zero failed requests** during failover transitions

## 🏗️ Architecture

```
                    ┌─────────────┐
                    │   Client    │
                    └──────┬──────┘
                           │
                           │ http://localhost:8080
                           ▼
                    ┌─────────────┐
                    │    Nginx    │
                    │  (Port 80)  │
                    └──────┬──────┘
                           │
            ┌──────────────┴──────────────┐
            │                             │
            ▼                             ▼
     ┌─────────────┐             ┌─────────────┐
     │  Blue Pool  │             │ Green Pool  │
     │  (Primary)  │             │  (Backup)   │
     │  Port 8081  │             │  Port 8082  │
     └─────────────┘             └─────────────┘
```

### Key Components

1. **Nginx (Port 8080)** - Public-facing reverse proxy
   - Routes all traffic to active pool (Blue by default)
   - Automatically fails over to backup pool on errors
   - Configured with tight timeouts (2s) for fast failure detection

2. **Blue Service (Port 8081)** - Primary application instance
   - Marked as active pool in Nginx upstream configuration
   - Can be directly accessed for chaos testing

3. **Green Service (Port 8082)** - Backup application instance
   - Marked as backup in Nginx upstream configuration
   - Only receives traffic when Blue fails

## ✨ Features

- ✅ **Automatic Failover**: Switches from Blue to Green within 2 seconds of detecting failure
- ✅ **Zero Downtime**: No failed requests during failover (tested with 20+ consecutive requests)
- ✅ **Chaos Engineering**: Built-in endpoints to simulate failures and timeouts
- ✅ **Header Forwarding**: Preserves `X-App-Pool` and `X-Release-Id` headers
- ✅ **Health Checks**: Continuous monitoring of service health
- ✅ **Easy Configuration**: Environment-based configuration via `.env` file
- ✅ **Parameterized Nginx**: Template-based Nginx config using `envsubst`

## 🚀 Quick Start

### Prerequisites

- Docker & Docker Compose installed
- `envsubst` (part of `gettext-base` package on Ubuntu)
- Linux/macOS environment (Windows users: use WSL2 or Ubuntu VM)

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/yourusername/blue-green-deployment.git
   cd blue-green-deployment
   ```

2. **Create environment file**
   ```bash
   cp .env.example .env
   ```

3. **Generate Nginx configuration**
   ```bash
   chmod +x setup.sh
   ./setup.sh
   ```

4. **Build and start services**
   ```bash
   docker-compose up -d --build
   ```

5. **Verify deployment**
   ```bash
   curl http://localhost:8080/version
   ```

   Expected response:
   ```json
   {
     "version": "1.0.0",
     "pool": "blue",
     "release": "blue-v1.0.0",
     "timestamp": "2025-10-27T..."
   }
   ```

## 🧪 Testing Failover

### Automated Test

Run the comprehensive test script:

```bash
chmod +x test-failover.sh
./test-failover.sh
```

This will:
1. ✅ Verify Blue is active
2. 🔥 Trigger chaos mode on Blue
3. 📊 Make 20 requests and verify zero failures
4. ✅ Confirm traffic switched to Green
5. 🛑 Stop chaos mode

### Manual Testing

#### Step 1: Verify Blue is active
```bash
for i in {1..5}; do 
  curl -s http://localhost:8080/version | grep -o '"pool":"[^"]*"'
done
```
All requests should return `"pool":"blue"`

#### Step 2: Trigger chaos on Blue
```bash
curl -X POST "http://localhost:8081/chaos/start?mode=error"
```

#### Step 3: Observe automatic failover
```bash
for i in {1..20}; do 
  echo "Request $i:"
  curl -s -w "HTTP: %{http_code}\n" http://localhost:8080/version | grep -E "pool|HTTP"
  sleep 0.5
done
```

**Expected Results:**
- ✅ All requests return HTTP 200
- ✅ Pool changes from "blue" to "green"
- ✅ Zero failed requests

#### Step 4: Stop chaos
```bash
curl -X POST "http://localhost:8081/chaos/stop"
```

## 📋 Available Endpoints

### Via Nginx (Port 8080)
- `GET /` - Service information
- `GET /version` - Version and pool info with headers
- `GET /healthz` - Health check
- `POST /chaos/start?mode=error|timeout` - Start chaos simulation
- `POST /chaos/stop` - Stop chaos simulation

### Direct Access
- **Blue**: `http://localhost:8081/*`
- **Green**: `http://localhost:8082/*`

## ⚙️ Configuration

### Environment Variables (.env)

```bash
# Active pool (blue or green)
ACTIVE_POOL=blue

# Release identifiers
RELEASE_ID_BLUE=blue-v1.0.0
RELEASE_ID_GREEN=green-v1.0.0
```

### Nginx Failover Settings

Key configurations in `nginx.conf.template`:

```nginx
upstream backend {
    # Primary server with aggressive failure detection
    server app_${ACTIVE_POOL}:3000 max_fails=1 fail_timeout=5s;
    
    # Backup server (only used when primary fails)
    server app_${BACKUP_POOL}:3000 backup;
}

# Tight timeouts for fast failure detection
proxy_connect_timeout 2s;
proxy_send_timeout 2s;
proxy_read_timeout 2s;

# Retry policy
proxy_next_upstream error timeout http_500 http_502 http_503 http_504;
proxy_next_upstream_tries 2;
proxy_next_upstream_timeout 10s;
```

### Switching Active Pool

To switch from Blue to Green:

1. Update `.env`:
   ```bash
   ACTIVE_POOL=green
   ```

2. Regenerate Nginx config and reload:
   ```bash
   ./setup.sh
   docker-compose restart nginx
   ```

## 🔍 Monitoring & Debugging

### View Logs

```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f nginx
docker-compose logs -f app_blue
docker-compose logs -f app_green
```

### Check Service Status

```bash
docker-compose ps
```

### Test Direct Endpoints

```bash
# Test Blue directly
curl http://localhost:8081/version

# Test Green directly
curl http://localhost:8082/version

# Check headers
curl -i http://localhost:8080/version | grep -E "X-App-Pool|X-Release-Id"
```

## 🛠️ Troubleshooting

### Issue: Containers not starting
```bash
docker-compose down
docker-compose up -d --build
docker-compose logs
```

### Issue: Port conflicts
```bash
# Check what's using the ports
sudo lsof -i :8080
sudo lsof -i :8081
sudo lsof -i :8082
```

### Issue: Nginx configuration errors
```bash
# Verify nginx.conf was generated
cat nginx.conf

# Regenerate if needed
./setup.sh

# Test Nginx config
docker-compose exec nginx nginx -t
```

### Issue: Failover not working
1. Check Nginx logs: `docker-compose logs nginx`
2. Verify chaos is active: `curl http://localhost:8081/version` should return 500
3. Check timeout settings in nginx.conf
4. Ensure both Blue and Green containers are running

## 📊 Performance Characteristics

- **Failover Detection Time**: ~2 seconds (configurable via timeouts)
- **Total Request Time During Failover**: <4 seconds (1 failed attempt + 1 successful retry)
- **Success Rate During Failover**: 100% (zero failed requests to clients)
- **Recovery Time**: ~5 seconds (via `fail_timeout` setting)

## 🏗️ Project Structure

```
blue-green-deployment/
├── README.md                 # This file
├── DECISION.md              # Architecture decisions and rationale
├── .env.example             # Environment template
├── .gitignore               # Git ignore rules
├── docker-compose.yml       # Container orchestration
├── nginx.conf.template      # Nginx configuration template
├── setup.sh                 # Configuration generator script
├── test-failover.sh         # Automated testing script
└── mock-service/            # Node.js application
    ├── Dockerfile           # Container image definition
    ├── package.json         # Node.js dependencies
    └── app.js               # Application code
```

## 📚 Technical Details

### Nginx Upstream Strategy

The deployment uses Nginx's `backup` directive to implement true Blue/Green behavior:
- Primary server receives 100% of traffic under normal conditions
- Backup server only receives traffic when primary is marked as down
- Fast failure detection via `max_fails=1` and `fail_timeout=5s`

### Retry Mechanism

Nginx retries failed requests automatically:
- Retries on: connection errors, timeouts, 5xx responses
- Maximum 2 attempts (1 to primary, 1 to backup)
- 10-second total timeout to meet <10s requirement

### Header Preservation

Application-set headers are forwarded to clients:
- `X-App-Pool`: Identifies which pool served the request (blue/green)
- `X-Release-Id`: Identifies the release version
- No header stripping ensures transparency

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## 📝 License

This project is open source and available under the MIT License.

## 🔗 Related Documentation

- [DECISION.md](./DECISION.md) - Detailed architecture decisions
- [Docker Compose Documentation](https://docs.docker.com/compose/)
- [Nginx Upstream Module](http://nginx.org/en/docs/http/ngx_http_upstream_module.html)

## 📞 Support

If you encounter any issues:
1. Check the [Troubleshooting](#-troubleshooting) section
2. Review logs: `docker-compose logs`
3. Open an issue on GitHub

---

**Built with ❤️ for zero-downtime deployments**