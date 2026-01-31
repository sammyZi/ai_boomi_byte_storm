# Deployment Guide - AI-Powered Drug Discovery Platform

This guide covers deploying the backend API to production environments.

## Table of Contents

- [Infrastructure Requirements](#infrastructure-requirements)
- [Redis Setup](#redis-setup)
- [Ollama Setup for BioMistral-7B](#ollama-setup-for-biomistral-7b)
- [Production Configuration](#production-configuration)
- [Deployment Options](#deployment-options)
- [Monitoring and Maintenance](#monitoring-and-maintenance)
- [Security Considerations](#security-considerations)
- [Troubleshooting](#troubleshooting)

## Infrastructure Requirements

### Minimum Requirements

**Backend API Server:**
- **CPU**: 4 cores
- **RAM**: 8 GB
- **Storage**: 20 GB SSD
- **OS**: Linux (Ubuntu 20.04+ recommended), Windows Server, or macOS
- **Python**: 3.11 or higher
- **Network**: Public IP with HTTPS support

**Redis Cache Server:**
- **CPU**: 2 cores
- **RAM**: 4 GB
- **Storage**: 10 GB SSD
- **Network**: Private network access to API server

**Ollama AI Server (Optional):**
- **CPU**: 4 cores
- **RAM**: 16 GB
- **GPU**: NVIDIA GPU with 8GB+ VRAM (T4, V100, A10, or better)
- **Storage**: 20 GB SSD
- **CUDA**: 11.8 or higher
- **Network**: Private network access to API server

### Recommended Production Setup

**For High Availability:**
- 2+ API server instances behind a load balancer
- Redis Cluster (3+ nodes) for distributed caching
- Dedicated Ollama GPU instance
- Separate monitoring and logging infrastructure

**Scaling Guidelines:**
- **Light Load** (<100 req/min): Single API server + Redis + Ollama
- **Medium Load** (100-500 req/min): 2-3 API servers + Redis Cluster + Ollama
- **Heavy Load** (>500 req/min): 5+ API servers + Redis Cluster + Multiple Ollama instances

## Redis Setup

### Option 1: Local Redis Installation

**Ubuntu/Debian:**
```bash
sudo apt update
sudo apt install redis-server

# Configure Redis
sudo nano /etc/redis/redis.conf

# Set the following:
# maxmemory 4gb
# maxmemory-policy allkeys-lru
# bind 0.0.0.0  # Or specific IP for security

# Start Redis
sudo systemctl start redis-server
sudo systemctl enable redis-server

# Verify
redis-cli ping
# Should return: PONG
```

**macOS:**
```bash
brew install redis

# Start Redis
brew services start redis

# Verify
redis-cli ping
```

**Windows:**
```powershell
# Download Redis from https://github.com/microsoftarchive/redis/releases
# Extract and run:
redis-server.exe

# Or install via Chocolatey:
choco install redis-64
```

### Option 2: Docker Redis

```bash
# Create docker-compose.yml
cat > docker-compose.yml << EOF
version: '3.8'

services:
  redis:
    image: redis:7-alpine
    container_name: drug-discovery-redis
    ports:
      - "6379:6379"
    volumes:
      - redis-data:/data
    command: redis-server --maxmemory 4gb --maxmemory-policy allkeys-lru
    restart: unless-stopped

volumes:
  redis-data:
EOF

# Start Redis
docker-compose up -d

# Verify
docker exec drug-discovery-redis redis-cli ping
```

### Option 3: Managed Redis Services

**AWS ElastiCache:**
```bash
# Create ElastiCache cluster via AWS Console or CLI
aws elasticache create-cache-cluster \
  --cache-cluster-id drug-discovery-cache \
  --cache-node-type cache.t3.medium \
  --engine redis \
  --num-cache-nodes 1

# Get endpoint
aws elasticache describe-cache-clusters \
  --cache-cluster-id drug-discovery-cache \
  --show-cache-node-info
```

**Azure Cache for Redis:**
```bash
# Create via Azure Portal or CLI
az redis create \
  --name drug-discovery-cache \
  --resource-group myResourceGroup \
  --location eastus \
  --sku Basic \
  --vm-size c1
```

**Google Cloud Memorystore:**
```bash
gcloud redis instances create drug-discovery-cache \
  --size=4 \
  --region=us-central1 \
  --redis-version=redis_7_0
```

### Redis Configuration for Production

Edit `/etc/redis/redis.conf`:

```conf
# Memory management
maxmemory 4gb
maxmemory-policy allkeys-lru

# Persistence (optional - we use 24h TTL)
save ""  # Disable RDB snapshots for cache-only use

# Security
requirepass your_strong_password_here
bind 127.0.0.1  # Or specific private IP

# Performance
tcp-backlog 511
timeout 0
tcp-keepalive 300
```

Update `.env` with Redis credentials:
```env
REDIS_URL=redis://:your_strong_password_here@localhost:6379
```

## Ollama Setup for BioMistral-7B

### Prerequisites

- NVIDIA GPU with 8GB+ VRAM
- CUDA 11.8 or higher
- NVIDIA drivers installed

### Installation Steps

#### 1. Install Ollama

**Linux:**
```bash
curl -fsSL https://ollama.ai/install.sh | sh
```

**macOS:**
```bash
# Download from https://ollama.ai/download
# Or use Homebrew:
brew install ollama
```

**Windows:**
```powershell
# Download installer from https://ollama.ai/download
# Run the installer
```

#### 2. Verify GPU Access

```bash
# Check NVIDIA GPU
nvidia-smi

# Should show your GPU with available memory
```

#### 3. Pull BioMistral-7B Model

```bash
# Pull the model (downloads ~4GB)
ollama pull biomistral:7b

# Verify model is available
ollama list
# Should show: biomistral:7b
```

#### 4. Start Ollama Service

**Linux (systemd):**
```bash
# Ollama installs as a systemd service automatically
sudo systemctl start ollama
sudo systemctl enable ollama

# Check status
sudo systemctl status ollama
```

**macOS:**
```bash
# Start Ollama
ollama serve

# Or run as background service
brew services start ollama
```

**Windows:**
```powershell
# Ollama runs as a Windows service after installation
# Or start manually:
ollama serve
```

#### 5. Test Ollama

```bash
# Test the API
curl http://localhost:11434/api/tags

# Test BioMistral model
curl http://localhost:11434/api/generate -d '{
  "model": "biomistral:7b",
  "prompt": "What is aspirin?",
  "stream": false
}'
```

### Ollama Configuration

Create `/etc/ollama/config.json` (Linux) or configure via environment:

```json
{
  "gpu_layers": -1,
  "num_thread": 4,
  "num_gpu": 1,
  "main_gpu": 0,
  "low_vram": false
}
```

Environment variables:
```bash
# Set GPU memory limit (optional)
export OLLAMA_GPU_MEMORY_FRACTION=0.9

# Set number of parallel requests
export OLLAMA_NUM_PARALLEL=4

# Set host and port
export OLLAMA_HOST=0.0.0.0:11434
```

### Remote Ollama Setup

If running Ollama on a separate GPU server:

**On GPU Server:**
```bash
# Start Ollama with network access
OLLAMA_HOST=0.0.0.0:11434 ollama serve
```

**On API Server (.env):**
```env
OLLAMA_BASE_URL=http://gpu-server-ip:11434
OLLAMA_MODEL=biomistral:7b
OLLAMA_TIMEOUT=5
```

### Ollama Performance Tuning

**For Better Throughput:**
```bash
# Increase parallel requests
export OLLAMA_NUM_PARALLEL=8

# Adjust context window
export OLLAMA_NUM_CTX=2048
```

**For Lower Memory Usage:**
```bash
# Enable low VRAM mode
export OLLAMA_LOW_VRAM=true

# Reduce batch size
export OLLAMA_BATCH_SIZE=128
```

## Production Configuration

### Environment Variables for Production

Create a production `.env` file:

```env
# ============================================================================
# Production Configuration
# ============================================================================

# API Configuration
API_PORT=8000
API_HOST=0.0.0.0
CORS_ORIGINS=https://yourdomain.com,https://www.yourdomain.com

# External APIs (use production endpoints)
OPEN_TARGETS_API_URL=https://api.platform.opentargets.org/api/v4
CHEMBL_API_URL=https://www.ebi.ac.uk/chembl/api/data
ALPHAFOLD_API_URL=https://alphafold.ebi.ac.uk/api

# Ollama Configuration
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=biomistral:7b
OLLAMA_TIMEOUT=5

# Redis Configuration (use production credentials)
REDIS_URL=redis://:your_production_password@redis-server:6379
CACHE_TTL=86400

# Rate Limiting
RATE_LIMIT_PER_MINUTE=100

# Logging
LOG_LEVEL=INFO

# Security Configuration (IMPORTANT!)
ENFORCE_HTTPS=true
ENVIRONMENT=production
```

### Security Hardening

**1. Enable HTTPS:**
```bash
# Install certbot for Let's Encrypt
sudo apt install certbot python3-certbot-nginx

# Get SSL certificate
sudo certbot --nginx -d api.yourdomain.com
```

**2. Configure Firewall:**
```bash
# Allow only necessary ports
sudo ufw allow 22/tcp    # SSH
sudo ufw allow 80/tcp    # HTTP (redirect to HTTPS)
sudo ufw allow 443/tcp   # HTTPS
sudo ufw enable
```

**3. Set File Permissions:**
```bash
# Protect .env file
chmod 600 .env

# Set proper ownership
chown www-data:www-data -R /path/to/backend
```

**4. Configure Nginx Reverse Proxy:**

Create `/etc/nginx/sites-available/drug-discovery`:

```nginx
upstream backend {
    server 127.0.0.1:8000;
    # Add more servers for load balancing:
    # server 127.0.0.1:8001;
    # server 127.0.0.1:8002;
}

server {
    listen 80;
    server_name api.yourdomain.com;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name api.yourdomain.com;

    ssl_certificate /etc/letsencrypt/live/api.yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/api.yourdomain.com/privkey.pem;

    # Security headers
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;

    # Rate limiting
    limit_req_zone $binary_remote_addr zone=api_limit:10m rate=100r/m;
    limit_req zone=api_limit burst=20 nodelay;

    location / {
        proxy_pass http://backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # Timeouts
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }
}
```

Enable the site:
```bash
sudo ln -s /etc/nginx/sites-available/drug-discovery /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

## Deployment Options

### Option 1: Systemd Service (Linux)

Create `/etc/systemd/system/drug-discovery.service`:

```ini
[Unit]
Description=AI-Powered Drug Discovery Platform
After=network.target redis.service

[Service]
Type=notify
User=www-data
Group=www-data
WorkingDirectory=/opt/drug-discovery/backend
Environment="PATH=/opt/drug-discovery/backend/venv/bin"
EnvironmentFile=/opt/drug-discovery/backend/.env
ExecStart=/opt/drug-discovery/backend/venv/bin/gunicorn \
    app.main:app \
    --workers 4 \
    --worker-class uvicorn.workers.UvicornWorker \
    --bind 0.0.0.0:8000 \
    --timeout 60 \
    --access-logfile /var/log/drug-discovery/access.log \
    --error-logfile /var/log/drug-discovery/error.log
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Deploy:
```bash
# Create log directory
sudo mkdir -p /var/log/drug-discovery
sudo chown www-data:www-data /var/log/drug-discovery

# Enable and start service
sudo systemctl daemon-reload
sudo systemctl enable drug-discovery
sudo systemctl start drug-discovery

# Check status
sudo systemctl status drug-discovery

# View logs
sudo journalctl -u drug-discovery -f
```

### Option 2: Docker Deployment

Create `Dockerfile`:

```dockerfile
FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    librdkit-dev \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create non-root user
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8000/health')"

# Run application
CMD ["gunicorn", "app.main:app", \
     "--workers", "4", \
     "--worker-class", "uvicorn.workers.UvicornWorker", \
     "--bind", "0.0.0.0:8000", \
     "--timeout", "60"]
```

Create `docker-compose.prod.yml`:

```yaml
version: '3.8'

services:
  api:
    build: .
    container_name: drug-discovery-api
    ports:
      - "8000:8000"
    environment:
      - REDIS_URL=redis://redis:6379
      - OLLAMA_BASE_URL=http://ollama:11434
    env_file:
      - .env
    depends_on:
      - redis
    restart: unless-stopped
    networks:
      - drug-discovery-network

  redis:
    image: redis:7-alpine
    container_name: drug-discovery-redis
    command: redis-server --maxmemory 4gb --maxmemory-policy allkeys-lru
    volumes:
      - redis-data:/data
    restart: unless-stopped
    networks:
      - drug-discovery-network

  ollama:
    image: ollama/ollama:latest
    container_name: drug-discovery-ollama
    volumes:
      - ollama-data:/root/.ollama
    ports:
      - "11434:11434"
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: 1
              capabilities: [gpu]
    restart: unless-stopped
    networks:
      - drug-discovery-network

volumes:
  redis-data:
  ollama-data:

networks:
  drug-discovery-network:
    driver: bridge
```

Deploy:
```bash
# Build and start
docker-compose -f docker-compose.prod.yml up -d

# Pull BioMistral model
docker exec drug-discovery-ollama ollama pull biomistral:7b

# View logs
docker-compose -f docker-compose.prod.yml logs -f

# Scale API servers
docker-compose -f docker-compose.prod.yml up -d --scale api=3
```

### Option 3: Kubernetes Deployment

Create `k8s/deployment.yaml`:

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: drug-discovery-api
spec:
  replicas: 3
  selector:
    matchLabels:
      app: drug-discovery-api
  template:
    metadata:
      labels:
        app: drug-discovery-api
    spec:
      containers:
      - name: api
        image: your-registry/drug-discovery-api:latest
        ports:
        - containerPort: 8000
        env:
        - name: REDIS_URL
          valueFrom:
            secretKeyRef:
              name: drug-discovery-secrets
              key: redis-url
        - name: OLLAMA_BASE_URL
          value: "http://ollama-service:11434"
        resources:
          requests:
            memory: "4Gi"
            cpu: "2"
          limits:
            memory: "8Gi"
            cpu: "4"
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 10
          periodSeconds: 5
---
apiVersion: v1
kind: Service
metadata:
  name: drug-discovery-api-service
spec:
  selector:
    app: drug-discovery-api
  ports:
  - protocol: TCP
    port: 80
    targetPort: 8000
  type: LoadBalancer
```

Deploy:
```bash
# Apply configurations
kubectl apply -f k8s/

# Check status
kubectl get pods
kubectl get services

# View logs
kubectl logs -f deployment/drug-discovery-api
```

## Monitoring and Maintenance

### Health Checks

```bash
# API health
curl https://api.yourdomain.com/health

# Redis health
redis-cli ping

# Ollama health
curl http://localhost:11434/api/tags
```

### Log Management

**Centralized Logging:**
```bash
# Install and configure log aggregation (e.g., ELK Stack, Loki)
# Forward application logs to centralized system
```

**Log Rotation:**
```bash
# Create /etc/logrotate.d/drug-discovery
/var/log/drug-discovery/*.log {
    daily
    rotate 14
    compress
    delaycompress
    notifempty
    create 0640 www-data www-data
    sharedscripts
    postrotate
        systemctl reload drug-discovery
    endscript
}
```

### Performance Monitoring

**Metrics to Track:**
- Request rate and latency (p50, p95, p99)
- Error rates by type
- Cache hit/miss rates
- External API response times
- AI model inference time
- Memory and CPU usage

**Monitoring Tools:**
- Prometheus + Grafana
- DataDog
- New Relic
- AWS CloudWatch

### Backup and Recovery

**Redis Backup:**
```bash
# Manual backup
redis-cli SAVE
cp /var/lib/redis/dump.rdb /backup/redis-$(date +%Y%m%d).rdb

# Automated backup (cron)
0 2 * * * redis-cli SAVE && cp /var/lib/redis/dump.rdb /backup/redis-$(date +\%Y\%m\%d).rdb
```

**Application Backup:**
```bash
# Backup configuration
tar -czf backup-$(date +%Y%m%d).tar.gz .env backend/
```

### Updates and Maintenance

**Update Dependencies:**
```bash
# Activate virtual environment
source venv/bin/activate

# Update packages
pip install --upgrade -r requirements.txt

# Run tests
pytest

# Restart service
sudo systemctl restart drug-discovery
```

**Update Ollama Model:**
```bash
# Pull latest model
ollama pull biomistral:7b

# Restart Ollama
sudo systemctl restart ollama
```

## Security Considerations

### 1. API Security

- ✅ HTTPS enforced in production
- ✅ CORS restricted to frontend domain
- ✅ Rate limiting (100 req/min per IP)
- ✅ Input sanitization and validation
- ✅ IP anonymization in logs

### 2. Network Security

- Use private networks for Redis and Ollama
- Implement firewall rules
- Use VPN for administrative access
- Enable DDoS protection

### 3. Data Security

- No storage of user health data
- No PII collection
- Secure environment variable storage
- Regular security audits

### 4. Compliance

- Display medical disclaimer prominently
- Log anonymization (GDPR compliance)
- Research-only usage terms
- Regular compliance reviews

## Troubleshooting

### Common Issues

**1. Redis Connection Errors**
```bash
# Check Redis is running
redis-cli ping

# Check connection
redis-cli -h <host> -p <port> -a <password> ping

# Check logs
sudo journalctl -u redis -f
```

**2. Ollama Not Responding**
```bash
# Check Ollama service
sudo systemctl status ollama

# Check GPU availability
nvidia-smi

# Restart Ollama
sudo systemctl restart ollama

# Check logs
sudo journalctl -u ollama -f
```

**3. High Memory Usage**
```bash
# Check memory
free -h

# Restart API service
sudo systemctl restart drug-discovery

# Adjust worker count in gunicorn
# Reduce --workers parameter
```

**4. Slow Response Times**
```bash
# Check cache hit rate
redis-cli INFO stats | grep keyspace_hits

# Check external API latency
curl -w "@curl-format.txt" -o /dev/null -s https://api.platform.opentargets.org/api/v4

# Check Ollama performance
time curl http://localhost:11434/api/generate -d '{"model":"biomistral:7b","prompt":"test"}'
```

**5. Rate Limit Issues**
```bash
# Check rate limiter logs
sudo journalctl -u drug-discovery | grep "rate limit"

# Adjust rate limit in .env
RATE_LIMIT_PER_MINUTE=200
```

### Getting Help

- Check logs: `sudo journalctl -u drug-discovery -f`
- Review error messages in `/var/log/drug-discovery/`
- Test individual components (Redis, Ollama, external APIs)
- Verify environment variables are set correctly
- Check network connectivity and firewall rules

## Additional Resources

- [FastAPI Deployment Guide](https://fastapi.tiangolo.com/deployment/)
- [Redis Production Checklist](https://redis.io/docs/management/optimization/)
- [Ollama Documentation](https://github.com/ollama/ollama/blob/main/docs/README.md)
- [NGINX Configuration Guide](https://nginx.org/en/docs/)
- [Let's Encrypt SSL Setup](https://letsencrypt.org/getting-started/)

---

**Requirements Validated:**
- 13.1: Configuration from environment variables
- 13.2: Ollama configuration support
- 13.3: CORS configuration
- 13.4: Port configuration
- 13.5: Log level configuration
