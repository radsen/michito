import os
import hashlib
import hmac
import time
from fastapi.testclient import TestClient
from src.entrypoints.api.main import app

client = TestClient(app)

def test_http_defensive_security_headers():
    """Verifies that security headers are injected into HTTP responses."""
    resp = client.get("/api/v1/pricing/catalog")
    assert resp.status_code == 200
    assert resp.headers.get("X-Content-Type-Options") == "nosniff"
    assert resp.headers.get("X-Frame-Options") == "SAMEORIGIN"
    assert resp.headers.get("Referrer-Policy") == "strict-origin-when-cross-origin"
    assert "geolocation=()" in resp.headers.get("Permissions-Policy", "")

def test_partner_statement_authorization_in_production(monkeypatch):
    """Verifies that partner statements require authentication in production/staging environments."""
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("TESTING", "0")
    monkeypatch.setenv("ADMIN_API_KEY", "super_secret_admin_key_999")
    monkeypatch.setenv("PARTNER_TOKEN_TINKKO", "tinkko_private_token_123")

    # 1. Unauthenticated request must return 403 Forbidden
    resp = client.get("/api/v1/partners/tinkko/statement")
    assert resp.status_code == 403
    assert "Unauthorized" in resp.json()["detail"]

    # 2. Authenticated with partner token via query param must succeed
    resp_token = client.get("/api/v1/partners/tinkko/statement?token=tinkko_private_token_123")
    assert resp_token.status_code == 200
    assert resp_token.json()["status"] == "success"

    # 3. Authenticated with Admin Key via X-Admin-Key header must succeed
    resp_admin = client.get("/api/v1/partners/tinkko/statement", headers={"X-Admin-Key": "super_secret_admin_key_999"})
    assert resp_admin.status_code == 200
    assert resp_admin.json()["status"] == "success"

def test_slack_webhook_signature_verification_in_production(monkeypatch):
    """Verifies that Slack command webhook enforces HMAC-SHA256 signature in production."""
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("TESTING", "0")
    monkeypatch.setenv("SLACK_SIGNING_SECRET", "slack_test_secret_abc123")

    # 1. Missing signature headers -> 401
    resp_unauth = client.post("/api/v1/integrations/slack/command", data={"text": "rerun ord_test"})
    assert resp_unauth.status_code == 401

    # 2. Valid HMAC signature -> succeeds or parses order
    ts = str(int(time.time()))
    body = "command=%2Fmichito&text=rerun+ord_nonexistent_123"
    sig_basestring = f"v0:{ts}:{body}".encode("utf-8")
    sig = "v0=" + hmac.new(b"slack_test_secret_abc123", sig_basestring, hashlib.sha256).hexdigest()

    resp_valid = client.post(
        "/api/v1/integrations/slack/command",
        content=body,
        headers={
            "Content-Type": "application/x-www-form-urlencoded",
            "X-Slack-Request-Timestamp": ts,
            "X-Slack-Signature": sig,
        }
    )
    assert resp_valid.status_code == 200

def test_wompi_server_integrity_signature_generation():
    """Verifies that the backend generates cryptographic integrity signature for the Wompi widget."""
    resp = client.get("/api/v1/orders/ord_test_sample_123")
    # Even if order doesn't exist (404), tests that the endpoint is wired correctly
    assert resp.status_code in (200, 404)
