"""
Tests for Telegram Webhook Security Endpoint (/telegram/webhook).

Requirements:
- Missing configured secret -> 403
- Missing request header -> 403
- Incorrect secret -> 403
- Correct secret -> 200
"""

import os
import pytest
from fastapi.testclient import TestClient
import bot
import main


def test_webhook_missing_configured_secret(client, monkeypatch):
    """If TELEGRAM_SECRET_TOKEN is not configured or empty, webhook requests must be rejected with HTTP 403."""
    monkeypatch.delenv("TELEGRAM_SECRET_TOKEN", raising=False)
    monkeypatch.setattr(bot, "get_secret_token", lambda: None)

    response = client.post(
        "/telegram/webhook",
        json={"update_id": 1001, "message": {"text": "/start"}},
        headers={"X-Telegram-Bot-Api-Secret-Token": "some_token"},
    )
    assert response.status_code == 403
    assert "Webhook secret not configured" in response.json()["detail"]


def test_webhook_empty_configured_secret(client, monkeypatch):
    """If TELEGRAM_SECRET_TOKEN is an empty whitespace string, reject with HTTP 403."""
    monkeypatch.setenv("TELEGRAM_SECRET_TOKEN", "   ")
    monkeypatch.setattr(bot, "get_secret_token", lambda: None)

    response = client.post(
        "/telegram/webhook",
        json={"update_id": 1002},
        headers={"X-Telegram-Bot-Api-Secret-Token": "some_token"},
    )
    assert response.status_code == 403
    assert "Webhook secret not configured" in response.json()["detail"]


def test_webhook_missing_request_header(client, monkeypatch):
    """If the incoming X-Telegram-Bot-Api-Secret-Token header is missing, return HTTP 403."""
    test_secret = "configured_secret_token_12345"
    monkeypatch.setenv("TELEGRAM_SECRET_TOKEN", test_secret)
    monkeypatch.setattr(bot, "get_secret_token", lambda: test_secret)

    response = client.post(
        "/telegram/webhook",
        json={"update_id": 1003},
    )
    assert response.status_code == 403
    assert "Invalid Telegram secret token header" in response.json()["detail"]


def test_webhook_incorrect_secret_header(client, monkeypatch):
    """If the incoming X-Telegram-Bot-Api-Secret-Token does not match, return HTTP 403."""
    test_secret = "configured_secret_token_12345"
    monkeypatch.setenv("TELEGRAM_SECRET_TOKEN", test_secret)
    monkeypatch.setattr(bot, "get_secret_token", lambda: test_secret)

    response = client.post(
        "/telegram/webhook",
        json={"update_id": 1004},
        headers={"X-Telegram-Bot-Api-Secret-Token": "attacker_invalid_secret_token"},
    )
    assert response.status_code == 403
    assert "Invalid Telegram secret token header" in response.json()["detail"]


def test_webhook_correct_secret_header(client, monkeypatch):
    """If the secret token matches via constant-time comparison, return HTTP 200 OK immediately."""
    test_secret = "configured_secret_token_12345"
    monkeypatch.setenv("TELEGRAM_SECRET_TOKEN", test_secret)
    monkeypatch.setattr(bot, "get_secret_token", lambda: test_secret)
    monkeypatch.setattr(bot, "get_bot_token", lambda: "mock_token")

    response = client.post(
        "/telegram/webhook",
        json={"update_id": 1005, "message": {"chat": {"id": 12345}, "text": "/help"}},
        headers={"X-Telegram-Bot-Api-Secret-Token": test_secret},
    )
    assert response.status_code == 200
    assert response.json() == {"ok": True}


def test_webhook_invalid_json_body(client, monkeypatch):
    """If the payload is invalid JSON, return HTTP 400 Bad Request."""
    test_secret = "configured_secret_token_12345"
    monkeypatch.setenv("TELEGRAM_SECRET_TOKEN", test_secret)
    monkeypatch.setattr(bot, "get_secret_token", lambda: test_secret)
    monkeypatch.setattr(bot, "get_bot_token", lambda: "mock_token")

    response = client.post(
        "/telegram/webhook",
        content="this is not valid json",
        headers={
            "Content-Type": "application/json",
            "X-Telegram-Bot-Api-Secret-Token": test_secret,
        },
    )
    assert response.status_code == 400
    assert "Invalid JSON payload" in response.json()["detail"]
