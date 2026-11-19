"""
Tests for API Rate Limiting on /explain-text and /explain-file.

Requirements:
- Allowed requests within limits succeed (HTTP 200).
- Exceeded requests return HTTP 429 with safe, clear detail message.
- Independent client IPs: exhaustion for one IP does not affect other client IPs.
- Normal Telegram webhook processing is never blocked by user rate limits.
"""

import pytest
from fastapi.testclient import TestClient
import main


def test_rate_limit_allowed_requests(client, mock_services):
    """Requests under the rate limit succeed normally."""
    headers = {"X-Forwarded-For": "203.0.113.1"}
    payload = {"text": "Hemoglobin 14.0 g/dL", "language": "English"}

    for _ in range(3):
        response = client.post("/explain-text", json=payload, headers=headers)
        assert response.status_code == 200


def test_rate_limit_exceeded_returns_429(client, mock_services, monkeypatch):
    """When requests exceed the configured rate limit, return HTTP 429."""
    # Configure a small limit for rapid deterministic testing
    monkeypatch.setattr(main, "RATE_LIMIT_TEXT", "3/minute")
    # Re-apply the limit to the endpoint
    main.limiter.reset()

    headers = {"X-Forwarded-For": "203.0.113.50"}
    payload = {"text": "WBC count 7000 /mcL", "language": "English"}

    # Exceed the limit
    responses = []
    for _ in range(25):
        resp = client.post("/explain-text", json=payload, headers=headers)
        responses.append(resp)

    # At least one request must be throttled with HTTP 429
    throttled = [r for r in responses if r.status_code == 429]
    assert len(throttled) > 0, "Expected at least one request to be rate-limited with HTTP 429"
    assert "Rate limit exceeded" in throttled[0].json()["detail"]


def test_independent_client_ips(client, mock_services):
    """Exhausting limits for Client A does not block requests from Client B."""
    ip_a_headers = {"X-Forwarded-For": "203.0.113.100"}
    ip_b_headers = {"X-Forwarded-For": "203.0.113.200"}
    payload = {"text": "Platelets 250,000 /mcL", "language": "English"}

    # Exhaust Client A
    for _ in range(25):
        client.post("/explain-text", json=payload, headers=ip_a_headers)

    # Client B should still be allowed
    resp_b = client.post("/explain-text", json=payload, headers=ip_b_headers)
    assert resp_b.status_code == 200, f"Client B must not be throttled by Client A, got {resp_b.status_code}"


def test_telegram_webhook_not_rate_limited(client, monkeypatch):
    """Telegram webhook endpoint is not subject to user explanation rate limiting."""
    monkeypatch.setattr(main, "get_secret_token", lambda: "mock_secret")
    monkeypatch.setattr(main, "get_bot_token", lambda: "mock_token")

    headers = {
        "X-Forwarded-For": "149.154.167.220",  # Telegram server IP range
        "X-Telegram-Bot-Api-Secret-Token": "mock_secret",
    }

    # Send rapid webhook requests
    for i in range(20):
        resp = client.post(
            "/telegram/webhook",
            json={"update_id": 5000 + i, "message": {"text": "/help"}},
            headers=headers,
        )
        assert resp.status_code == 200, f"Webhook should never be throttled, failed on call {i}"


def test_explain_file_rate_limited(client, mock_services):
    """The /explain-file endpoint is protected by rate limiting."""
    headers = {"X-Forwarded-For": "203.0.113.77"}
    pdf_bytes = b"%PDF-1.4 dummy report"
    files = {"file": ("report.pdf", pdf_bytes, "application/pdf")}
    data = {"language": "English"}

    responses = []
    for _ in range(20):
        resp = client.post("/explain-file", files=files, data=data, headers=headers)
        responses.append(resp)

    # Verify at least one request gets 429
    throttled = [r for r in responses if r.status_code == 429]
    assert len(throttled) > 0
    assert "Rate limit exceeded" in throttled[0].json()["detail"]


def test_spoofed_x_forwarded_for_cannot_bypass_rate_limit(client, mock_services):
    """
    An attacker cannot bypass rate limits by rotating spoofed IPs at the start of
    the X-Forwarded-For header when behind a trusted proxy.
    The real client IP appended by the proxy (203.0.113.88) must be tracked.
    """
    real_ip = "203.0.113.88"
    payload = {"text": "Hemoglobin 13.5 g/dL", "language": "English"}

    responses = []
    # Attacker rotates spoofed IP prefixes on every request
    for i in range(25):
        spoofed_prefix = f"192.0.2.{i % 250}"
        headers = {"X-Forwarded-For": f"{spoofed_prefix}, {real_ip}"}
        resp = client.post("/explain-text", json=payload, headers=headers)
        responses.append(resp)

    # Must be throttled based on real_ip despite rotated spoofed prefix
    throttled = [r for r in responses if r.status_code == 429]
    assert len(throttled) > 0, "Spoofed X-Forwarded-For prefixes must not bypass rate limiting!"


def test_malformed_x_forwarded_for_handled_safely(client, mock_services):
    """Malformed or injected values in X-Forwarded-For do not crash the application."""
    headers = {"X-Forwarded-For": "not-a-valid-ip; <script>alert(1)</script>"}
    payload = {"text": "Platelets 200,000 /mcL", "language": "English"}

    response = client.post("/explain-text", json=payload, headers=headers)
    assert response.status_code in (200, 429)


def test_get_client_ip_unit():
    """Unit tests for get_client_ip verifying secure proxy extraction and validation."""
    class DummyClient:
        def __init__(self, host):
            self.host = host

    class DummyRequest:
        def __init__(self, headers, client_host=None):
            self.headers = headers
            self.client = DummyClient(client_host) if client_host else None

    # Single IP from proxy
    req1 = DummyRequest({"X-Forwarded-For": "198.51.100.5"})
    assert main.get_client_ip(req1) == "198.51.100.5"

    # Multi-hop: client spoofed 1.1.1.1, proxy appended 198.51.100.5
    req2 = DummyRequest({"X-Forwarded-For": "1.1.1.1, 198.51.100.5"})
    assert main.get_client_ip(req2) == "198.51.100.5"

    # Multi-hop with multiple spoofed hops: 1.1.1.1, 2.2.2.2, proxy appended 198.51.100.5
    req3 = DummyRequest({"X-Forwarded-For": "1.1.1.1, 2.2.2.2, 198.51.100.5"})
    assert main.get_client_ip(req3) == "198.51.100.5"

    # Direct client connection without proxy header
    req4 = DummyRequest({}, client_host="192.168.1.50")
    assert main.get_client_ip(req4) == "192.168.1.50"

    # Malformed IP falls back safely
    req5 = DummyRequest({"X-Forwarded-For": "invalid-ip-string"}, client_host="10.0.0.1")
    assert main.get_client_ip(req5) == "10.0.0.1"