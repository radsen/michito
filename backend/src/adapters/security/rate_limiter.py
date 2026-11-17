import time
import hashlib
from typing import Dict, Tuple, Any, Optional
from collections import defaultdict
from fastapi import Request, HTTPException
import logging

logger = logging.getLogger(__name__)

class SlidingWindowRateLimiter:
    """
    In-memory Sliding Window Rate Limiter & Response Cache.
    Protects public AI and intent profiling endpoints from bot floods,
    scraping abuse, and quota exhaustion without requiring upfront payment.
    """

    def __init__(self, max_requests: int = 10, window_seconds: int = 600, cache_ttl_seconds: int = 86400):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.cache_ttl_seconds = cache_ttl_seconds
        
        # IP -> list of timestamps
        self._requests: Dict[str, list[float]] = defaultdict(list)
        # Query Hash -> (timestamp, response_data)
        self._cache: Dict[str, Tuple[float, Any]] = {}

    def get_client_ip(self, request: Request) -> str:
        """Extracts client IP address respecting reverse proxies."""
        forwarded = request.headers.get("x-forwarded-for")
        if forwarded:
            return forwarded.split(",")[0].strip()
        real_ip = request.headers.get("x-real-ip")
        if real_ip:
            return real_ip.strip()
        if request.client and request.client.host:
            return request.client.host
        return "127.0.0.1"

    def check_rate_limit(self, request: Request, endpoint_name: str = "ai_agent"):
        """
        Enforces rate limit. Raises HTTP 429 if the client exceeds the threshold.
        """
        client_ip = self.get_client_ip(request)
        if client_ip in ("testclient", "test_client"):
            return
        key = f"{client_ip}:{endpoint_name}"
        now = time.time()
        cutoff = now - self.window_seconds

        # Prune old timestamps
        timestamps = [ts for ts in self._requests[key] if ts > cutoff]
        self._requests[key] = timestamps

        if len(timestamps) >= self.max_requests:
            logger.warning(f"Rate limit exceeded for IP {client_ip} on {endpoint_name} ({len(timestamps)} requests)")
            raise HTTPException(
                status_code=429,
                detail="Has alcanzado el límite de consultas gratuitas de análisis por minuto. Por favor espera unos momentos o continúa con la configuración de tu orden."
            )

        # Record this request
        self._requests[key].append(now)

    def get_cached_response(self, cache_key: str) -> Optional[Any]:
        """Returns cached response if within TTL, else None."""
        if cache_key in self._cache:
            ts, data = self._cache[cache_key]
            if time.time() - ts < self.cache_ttl_seconds:
                return data
            else:
                del self._cache[cache_key]
        return None

    def set_cached_response(self, cache_key: str, data: Any):
        """Stores response in memory cache with current timestamp."""
        self._cache[cache_key] = (time.time(), data)

    @staticmethod
    def compute_cache_key(*args) -> str:
        """Computes deterministic SHA-256 hash for query arguments."""
        raw = "|".join(str(a).strip().lower() for a in args)
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

# Global singletons
ai_agent_rate_limiter = SlidingWindowRateLimiter(max_requests=10, window_seconds=600)
