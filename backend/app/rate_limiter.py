"""Rate limiting middleware for API endpoints.

This module implements rate limiting to prevent abuse and ensure
fair resource allocation across users.
"""

import time
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Dict, Tuple
from fastapi import Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware


class RateLimiter:
    """In-memory rate limiter using sliding window algorithm.
    
    Tracks requests per IP address and enforces rate limits.
    In production, consider using Redis for distributed rate limiting.
    """
    
    def __init__(self, requests_per_minute: int = 100):
        """Initialize rate limiter.
        
        Args:
            requests_per_minute: Maximum requests allowed per minute per IP
        """
        self.requests_per_minute = requests_per_minute
        self.window_seconds = 60
        # Store: IP -> list of (timestamp, count) tuples
        self.request_log: Dict[str, list] = defaultdict(list)
    
    def is_allowed(self, client_ip: str) -> Tuple[bool, int]:
        """Check if request from IP is allowed.
        
        Args:
            client_ip: Client IP address
        
        Returns:
            Tuple of (is_allowed, remaining_requests)
        
        Validates: Requirements 12.3, 12.4
        """
        current_time = time.time()
        window_start = current_time - self.window_seconds
        
        # Clean up old entries
        self.request_log[client_ip] = [
            timestamp for timestamp in self.request_log[client_ip]
            if timestamp > window_start
        ]
        
        # Count requests in current window
        request_count = len(self.request_log[client_ip])
        
        # Check if limit exceeded
        if request_count >= self.requests_per_minute:
            return False, 0
        
        # Add current request
        self.request_log[client_ip].append(current_time)
        
        remaining = self.requests_per_minute - request_count - 1
        return True, remaining
    
    def cleanup_old_entries(self):
        """Periodically clean up old entries to prevent memory growth."""
        current_time = time.time()
        window_start = current_time - self.window_seconds
        
        # Remove IPs with no recent requests
        ips_to_remove = []
        for ip, timestamps in self.request_log.items():
            # Filter out old timestamps
            recent = [t for t in timestamps if t > window_start]
            if not recent:
                ips_to_remove.append(ip)
            else:
                self.request_log[ip] = recent
        
        for ip in ips_to_remove:
            del self.request_log[ip]


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Middleware to enforce rate limiting on API requests."""
    
    def __init__(self, app, rate_limiter: RateLimiter):
        """Initialize middleware.
        
        Args:
            app: FastAPI application
            rate_limiter: RateLimiter instance
        """
        super().__init__(app)
        self.rate_limiter = rate_limiter
    
    async def dispatch(self, request: Request, call_next):
        """Process request with rate limiting.
        
        Args:
            request: Incoming request
            call_next: Next middleware/handler
        
        Returns:
            Response or 429 error if rate limit exceeded
        """
        # Skip rate limiting for health check and docs
        if request.url.path in ["/health", "/", "/docs", "/redoc", "/openapi.json"]:
            return await call_next(request)
        
        # Get client IP (handle proxies)
        client_ip = request.client.host
        if "x-forwarded-for" in request.headers:
            client_ip = request.headers["x-forwarded-for"].split(",")[0].strip()
        
        # Check rate limit
        is_allowed, remaining = self.rate_limiter.is_allowed(client_ip)
        
        if not is_allowed:
            # Return 429 Too Many Requests
            raise HTTPException(
                status_code=429,
                detail={
                    "error_code": "RATE_LIMIT_EXCEEDED",
                    "message": f"Rate limit exceeded. Maximum {self.rate_limiter.requests_per_minute} requests per minute allowed.",
                    "timestamp": datetime.utcnow().isoformat()
                }
            )
        
        # Add rate limit headers to response
        response = await call_next(request)
        response.headers["X-RateLimit-Limit"] = str(self.rate_limiter.requests_per_minute)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        
        return response
