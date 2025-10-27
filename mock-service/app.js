const express = require('express');
const app = express();

const APP_POOL = process.env.APP_POOL || 'unknown';
const RELEASE_ID = process.env.RELEASE_ID || 'unknown';
const PORT = process.env.PORT || 3000;

let chaosMode = { enabled: false, type: 'error' };

app.use(express.json());

app.get('/healthz', (req, res) => {
  if (chaosMode.enabled && chaosMode.type === 'error') {
    return res.status(500).json({ status: 'unhealthy', pool: APP_POOL });
  }
  res.status(200).json({ status: 'healthy', pool: APP_POOL });
});

app.get('/version', (req, res) => {
  if (chaosMode.enabled) {
    if (chaosMode.type === 'error') {
      console.log(`[${APP_POOL}] Chaos: returning 500`);
      return res.status(500)
        .set('X-App-Pool', APP_POOL)
        .set('X-Release-Id', RELEASE_ID)
        .json({ error: 'Service unavailable', pool: APP_POOL });
    } else if (chaosMode.type === 'timeout') {
      console.log(`[${APP_POOL}] Chaos: timeout`);
      setTimeout(() => {
        res.status(200)
          .set('X-App-Pool', APP_POOL)
          .set('X-Release-Id', RELEASE_ID)
          .json({ version: '1.0.0', pool: APP_POOL, release: RELEASE_ID });
      }, 5000);
      return;
    }
  }
  
  res.status(200)
    .set('X-App-Pool', APP_POOL)
    .set('X-Release-Id', RELEASE_ID)
    .json({ 
      version: '1.0.0', 
      pool: APP_POOL, 
      release: RELEASE_ID, 
      timestamp: new Date().toISOString() 
    });
});

app.post('/chaos/start', (req, res) => {
  const mode = req.query.mode || 'error';
  chaosMode.enabled = true;
  chaosMode.type = mode;
  console.log(`[${APP_POOL}] 🔥 CHAOS MODE: ${mode}`);
  res.status(200).json({ message: 'Chaos started', mode, pool: APP_POOL });
});

app.post('/chaos/stop', (req, res) => {
  chaosMode.enabled = false;
  console.log(`[${APP_POOL}] ✅ CHAOS STOPPED`);
  res.status(200).json({ message: 'Chaos stopped', pool: APP_POOL });
});

app.get('/', (req, res) => {
  res.json({ 
    message: 'Blue/Green Service', 
    pool: APP_POOL, 
    release: RELEASE_ID,
    endpoints: [
      'GET /',
      'GET /version',
      'GET /healthz',
      'POST /chaos/start?mode=error|timeout',
      'POST /chaos/stop'
    ]
  });
});

app.listen(PORT, '0.0.0.0', () => {
  console.log(`[${APP_POOL}] Server running on port ${PORT} | Release: ${RELEASE_ID}`);
});

process.on('SIGTERM', () => {
  console.log(`[${APP_POOL}] Shutting down...`);
  process.exit(0);
});