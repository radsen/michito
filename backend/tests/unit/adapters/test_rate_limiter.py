import pytest
from unittest.mock import MagicMock
from fastapi import HTTPException
from src.adapters.security.rate_limiter import SlidingWindowRateLimiter

def test_sliding_window_rate_limiter_allows_under_threshold():
    limiter = SlidingWindowRateLimiter(max_requests=3, window_seconds=10)
    mock_req = MagicMock()
    mock_req.headers.get.return_value = None
    mock_req.client.host = "192.168.1.50"

    # 3 calls should pass
    limiter.check_rate_limit(mock_req, "test_action")
    limiter.check_rate_limit(mock_req, "test_action")
    limiter.check_rate_limit(mock_req, "test_action")

    # 4th call should raise HTTPException 429
    with pytest.raises(HTTPException) as exc_info:
        limiter.check_rate_limit(mock_req, "test_action")
    assert exc_info.value.status_code == 429
    assert "límite" in exc_info.value.detail.lower()

def test_rate_limiter_caching():
    limiter = SlidingWindowRateLimiter()
    key = limiter.compute_cache_key("test_prompt", "CO")
    
    assert limiter.get_cached_response(key) is None
    limiter.set_cached_response(key, {"sample": 123})
    assert limiter.get_cached_response(key) == {"sample": 123}
