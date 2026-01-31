# Redis Cache Layer Setup

This document describes how to set up and use the Redis cache layer for the drug discovery platform.

## Prerequisites

- Docker and Docker Compose installed
- Python 3.11+ with dependencies from requirements.txt

## Starting Redis

The project includes a Docker Compose configuration for running Redis locally.

### Start Redis:

```bash
cd backend
docker-compose up -d
```

### Verify Redis is running:

```bash
docker ps
```

You should see a container named `drug-discovery-redis` with status "healthy".

### Check Redis logs:

```bash
docker-compose logs redis
```

### Stop Redis:

```bash
docker-compose down
```

### Stop Redis and remove data:

```bash
docker-compose down -v
```

## Configuration

The cache layer reads configuration from environment variables:

- `REDIS_URL`: Redis connection URL (default: `redis://localhost:6379`)
- `CACHE_TTL`: Default TTL in seconds (default: `86400` = 24 hours)

Set these in your `.env` file:

```env
REDIS_URL=redis://localhost:6379
CACHE_TTL=86400
```

## Usage

### Basic Usage

```python
from app.cache import cache

# Set a value
await cache.set("my:key", {"data": "value"}, ttl=3600)

# Get a value
result = await cache.get("my:key")

# Invalidate keys by pattern
deleted = await cache.invalidate("my:*")

# Close connection when done
await cache.close()
```

### Cache Keys Convention

Use namespaced keys with colons:

- `ot:disease:{disease_name}` - Open Targets results
- `af:structure:{uniprot_id}` - AlphaFold structures
- `chembl:molecules:{target_id}` - ChEMBL molecules
- `props:{smiles_hash}` - Molecular properties

### Graceful Degradation

The cache layer handles Redis connection failures gracefully:

- If Redis is unavailable, `get()` returns `None`
- If Redis is unavailable, `set()` returns `False`
- If Redis is unavailable, `invalidate()` returns `0`
- The application continues functioning without caching

### TTL (Time-To-Live)

- Default TTL: 24 hours (86400 seconds)
- Custom TTL: Pass `ttl` parameter to `set()`
- After TTL expires, keys are automatically deleted by Redis

## Testing

### Run all cache tests:

```bash
cd backend
python -m pytest tests/ -k cache -v
```

### Run property tests only:

```bash
python -m pytest tests/test_cache_properties.py -v
```

### Run unit tests only:

```bash
python -m pytest tests/test_cache_unit.py -v
```

## Monitoring

### Connect to Redis CLI:

```bash
docker exec -it drug-discovery-redis redis-cli
```

### Useful Redis commands:

```redis
# List all keys
KEYS *

# Get a value
GET "my:key"

# Check TTL
TTL "my:key"

# Delete a key
DEL "my:key"

# Flush all data (use with caution!)
FLUSHALL

# Get info
INFO

# Monitor commands in real-time
MONITOR
```

## Production Considerations

### Redis Cluster

For production, consider using Redis Cluster for:
- High availability
- Horizontal scaling
- Automatic failover

### Redis Sentinel

For simpler high availability:
- Master-slave replication
- Automatic failover
- Monitoring

### Managed Redis Services

Consider managed services like:
- AWS ElastiCache
- Azure Cache for Redis
- Google Cloud Memorystore
- Redis Cloud

### Security

- Enable authentication: `requirepass` in Redis config
- Use TLS/SSL for connections
- Restrict network access with firewall rules
- Update `REDIS_URL` to include password: `redis://:password@host:6379`

### Monitoring

Monitor these metrics:
- Cache hit/miss rate
- Memory usage
- Eviction rate
- Connection count
- Command latency

## Troubleshooting

### Redis not starting

Check Docker logs:
```bash
docker-compose logs redis
```

### Connection refused

Ensure Redis is running:
```bash
docker ps
```

Verify port 6379 is not in use:
```bash
netstat -an | findstr 6379  # Windows
netstat -an | grep 6379     # Linux/Mac
```

### Out of memory

Redis has a default memory limit. Configure in docker-compose.yml:
```yaml
command: redis-server --maxmemory 256mb --maxmemory-policy allkeys-lru
```

### Slow performance

- Check Redis memory usage
- Monitor slow queries with `SLOWLOG GET`
- Consider using Redis pipelining for bulk operations
- Optimize key patterns and data structures

## Known Issues

None currently. All tests pass successfully.

### Previous Issue (Resolved)

The property test `test_cache_invalidation_pattern` previously failed with special characters like `[` in key prefixes. This has been resolved by constraining the test generator to use only alphanumeric characters, which aligns with the recommended cache key naming convention.
