# Scalability Analysis - URL Shortener Service

## 1. Design Decisions Made

### 1.1 Separate Stats Table
**Decision:** Visit count is stored in a separate `url_stats` table instead of the `urls` table.

**Reasoning:**
- **Avoiding Row Locks:** Updating visit count in the main `urls` table would require locking the row on every redirect, creating a bottleneck under high traffic.
- **Write Contention:** Thousands of concurrent redirects would cause race conditions and lock contention.
- **Read Performance:** Keeping the `urls` table lightweight ensures fast lookups for redirects.

**Trade-off:** Introduces slight complexity with an additional table, but dramatically improves write scalability.

### 1.2 Layered Architecture
**Decision:** Implemented Repository and Service layers.

**Architecture:**
```
Endpoint → Service → Repository → Database
```

**Benefits:**
- **Separation of Concerns:** Business logic (Service) separated from data access (Repository).
- **Testability:** Each layer can be unit tested independently.
- **Maintainability:** Changes to database queries don't affect business logic.
- **Scalability:** Easy to introduce caching, queueing, or external services at the service layer.

## 2. Immediate Improvements

### 2.1 Short Code Generation Strategy
**Current Issue:** Checking database for collision on every code generation.

**Better Approaches:**

#### Option A: Pre-generated Code Pool
```python

async def get_available_code():
    code = await redis.spop("available_codes")
    if not code:
        await regenerate_code_pool()
    return code
```

**Benefits:**
- Zero database checks during code generation
- Guaranteed uniqueness
- Fast response times

**Trade-off:** Requires Redis and background job for pool management.

#### Option B: Counter-based Generation (YouTube-style)
```python
# Use auto-incrementing counter + base62 encoding
def generate_code_from_counter(counter: int) -> str:
    chars = string.ascii_letters + string.digits
    code = []
    while counter > 0:
        code.append(chars[counter % 62])
        counter //= 62
    return ''.join(reversed(code))
```

**Benefits:**
- Guaranteed unique (based on database sequence)
- No collision checks needed
- Predictable, sequential

**Trade-off:** Codes are predictable (can be mitigated with encryption/offset).

### 2.2 Enhanced URL Validation
**Current State:** Basic validation in utils.

**Improvements Needed:**
```python
def validate_url_enhanced(url: str) -> str:
    # Current checks +
    
    # 1. Check against malicious domains (blacklist)
    if is_blacklisted_domain(parsed.netloc):
        raise HTTPException(400, "Domain not allowed")
    
    # 2. Verify DNS resolution (optional, can be async)
    # await verify_domain_exists(parsed.netloc)
    
    # 3. Check URL length limits
    if len(url) > 2048:
        raise HTTPException(400, "URL too long")
    
    # 4. Sanitize special characters
    # Prevent homograph attacks, Unicode issues
    
    # 5. Optional: Check if URL is reachable (HEAD request)
    # Can be done in background to avoid blocking
    
    return url
```

### 2.3 Background Task for Stats Update
**Current Issue:** Stats update happens synchronously in the request path.

**Solution:** Use FastAPI Background Tasks or Celery
```python
from fastapi import BackgroundTasks

@router.get("/{short_code}")
async def redirect_to_url(
    short_code: str,
    background_tasks: BackgroundTasks,
    session: AsyncSession = Depends(get_session),
    service: URLService = Depends(get_url_service),
    stats_service: URLStatsService = Depends(get_url_stats_service)
):
    original_url = await service.get_original_url(session, short_code)
    if not original_url:
        raise HTTPException(404)
    
    # Increment stats in background (non-blocking)
    background_tasks.add_task(
        stats_service.increment_visit, 
        session, 
        short_code
    )
    
    return RedirectResponse(url=original_url)
```

**Better:** Use message queue (RabbitMQ/Redis Queue) for decoupled processing.

### 2.4 Connection Pooling Configuration
**Current:** Basic pooling enabled.

**Optimization:**
```python
engine = create_async_engine(
    settings.DATABASE_URL,
    pool_size=20,           # Increase based on load
    max_overflow=40,        # Allow burst traffic
    pool_pre_ping=True,     # Verify connections before use
    pool_recycle=3600,      # Recycle connections hourly
)
```

## 3. Production Scalability Solutions (Based on PRD Requirements)

### 3.1 Heavy Logging Overhead
**PRD Scenario:** Logging becomes very heavy (needs to send to external service/database).

**Current Problem:** Synchronous logging in middleware blocks request processing.

**Solutions:**

#### A. Async Queue-based Logging
```python
# Use Redis Queue or RabbitMQ
async def log_visit_async(short_code, ip, timestamp):
    await redis.lpush("visit_logs_queue", json.dumps({
        "short_code": short_code,
        "ip": ip,
        "timestamp": timestamp
    }))

# Separate worker process
async def process_logs():
    while True:
        log = await redis.brpop("visit_logs_queue")
        await send_to_external_service(log)
```

**Benefits:**
- Non-blocking request path
- Can batch logs for efficiency
- Retry mechanism for failures

#### B. Batch Writing
```python
# Accumulate logs in memory, flush every N seconds or M records
class BatchLogger:
    def __init__(self, batch_size=1000, flush_interval=5):
        self.buffer = []
        self.batch_size = batch_size
    
    async def log(self, entry):
        self.buffer.append(entry)
        if len(self.buffer) >= self.batch_size:
            await self.flush()
    
    async def flush(self):
        if self.buffer:
            await bulk_insert_to_db(self.buffer)
            self.buffer = []
```

#### C. Observability Services
**Use dedicated platforms:**
- **Datadog / New Relic:** For application metrics
- **ELK Stack:** For log aggregation
- **Prometheus + Grafana:** For metrics and visualization

**Implementation:**
```python
# Send to external service asynchronously
background_tasks.add_task(
    send_to_datadog,
    metric="url_redirect",
    tags={"short_code": short_code}
)
```

### 3.2 Multi-Instance Deployment
**PRD Scenario:** System runs on multiple servers.

**Challenges & Solutions:**

#### A. Session/State Management
**Problem:** No shared state between instances.

**Solution:** Externalize all state to Redis/Database
```python
# Don't store anything in memory across requests
# Use Redis for:
- Rate limiting counters
- Code generation pool
- Session data (if needed)
```

#### B. Database Connection Management
**Problem:** Each instance opens connections.

**Solution:** Connection pooling + PgBouncer
```
[Instance 1] ──┐
[Instance 2] ──┼──> [PgBouncer] ──> [PostgreSQL]
[Instance 3] ──┘
```

**Benefits:**
- Connection pooling at infrastructure level
- Reduced database connection overhead

#### C. Consistent Short Code Generation
**Problem:** Two instances might generate same code.

**Solution:** Use distributed ID generation
- **Snowflake IDs:** Twitter's approach (timestamp + worker ID + sequence)
- **Database sequences:** Use `SERIAL` or `SEQUENCE` for guaranteed uniqueness
- **Redis INCR:** Atomic counter in Redis

#### D. Load Balancing
```
             [Load Balancer (Nginx/HAProxy)]
                        |
        ┌───────────────┼───────────────┐
        ▼               ▼               ▼
   [Instance 1]    [Instance 2]    [Instance 3]
```

**Configuration:**
- Health checks on each instance
- Sticky sessions (if needed)
- Round-robin or least-connections

### 3.3 High Traffic Campaign (Thousands of Requests/Second)
**PRD Scenario:** Marketing campaign drives heavy traffic.

**Solutions:**

#### A. Caching Layer (Redis)
```python
@router.get("/{short_code}")
async def redirect_to_url(short_code: str):
    # Check cache first
    cached_url = await redis.get(f"short:{short_code}")
    if cached_url:
        # Log in background
        background_tasks.add_task(log_visit, short_code)
        return RedirectResponse(cached_url)
    
    # Cache miss - query database
    url = await db.get_url(short_code)
    if url:
        await redis.setex(f"short:{short_code}", 3600, url)
        return RedirectResponse(url)
```

**Benefits:**
- 10-100x faster responses
- Reduced database load
- Can handle millions of requests

**Cache Strategy:**
- **Popular URLs:** Cache indefinitely or long TTL
- **New URLs:** Cache after first access
- **Cache Warming:** Pre-populate popular codes

#### B. Rate Limiting
```python
from fastapi_limiter import FastAPILimiter
from fastapi_limiter.depends import RateLimiter

@router.post("/shorten", dependencies=[Depends(RateLimiter(times=10, seconds=60))])
async def create_short_url(...):
    # Limit: 10 requests per minute per IP
```

**Strategies:**
- Per-IP rate limiting
- Per-user rate limiting (if authenticated)
- Sliding window algorithm

#### C. CDN for Static Content
- Serve redirect page through CDN
- Cache 301 redirects at edge locations
- Global distribution reduces latency

#### D. Database Optimizations

**Indexes:**
```sql
-- Already have index on short_code (unique)
CREATE INDEX idx_visit_logs_short_code ON visit_logs(short_code);
CREATE INDEX idx_visit_logs_visited_at ON visit_logs(visited_at);
```

**Read Replicas:**
```
[Primary DB] ──> [Replica 1] (read stats)
             └──> [Replica 2] (read URLs)
```

**Partitioning:**
```sql
-- Partition visit_logs by date
CREATE TABLE visit_logs_2026_01 PARTITION OF visit_logs
    FOR VALUES FROM ('2026-01-01') TO ('2026-02-01');
```

#### E. Asynchronous Stats Processing
**Current:** Stats updated in request path.

**Better:** Queue-based processing
```python
# On redirect - just push to queue
await redis.lpush("stats_queue", short_code)

# Separate worker process
async def stats_worker():
    while True:
        codes = await redis.brpop("stats_queue", timeout=1)
        if codes:
            # Batch process
            await batch_increment_stats(codes)
```

### 3.4 Monitoring & Auto-scaling
**Metrics to Monitor:**
- Request latency (p50, p95, p99)
- Error rates (4xx, 5xx)
- Database connection pool usage
- Cache hit ratio
- Queue depth

**Auto-scaling Triggers:**
- CPU > 70% for 5 minutes → Scale up
- Request queue depth > 1000 → Scale up
- Average response time > 200ms → Scale up

**Tools:**
- **Kubernetes HPA:** Horizontal Pod Autoscaler
- **AWS Auto Scaling Groups**
- **Docker Swarm / ECS**

## 4. Summary

### Current Bottlenecks
1. ❌ Synchronous stats updates in request path
2. ❌ Database checks for code uniqueness
3. ❌ No caching layer
4. ❌ Synchronous logging

### Recommended Immediate Actions
1. ✅ Implement Redis caching for URL lookups
2. ✅ Move stats updates to background tasks
3. ✅ Use counter-based code generation or pre-generated pool
4. ✅ Add rate limiting

### For Production Scale
1. ✅ Queue-based logging (RabbitMQ/Redis)
2. ✅ Database read replicas
3. ✅ CDN integration
4. ✅ Multi-instance deployment with load balancer
5. ✅ Comprehensive monitoring and auto-scaling

### Expected Performance
**With optimizations:**
- **Current:** ~500 req/s per instance
- **With Redis cache:** ~10,000 req/s per instance
- **With load balancing (3 instances):** ~30,000 req/s
- **Response time:** <10ms (cached), <50ms (database)

The architecture is well-structured for horizontal scaling. Main focus should be on caching and asynchronous processing to handle high-traffic scenarios.