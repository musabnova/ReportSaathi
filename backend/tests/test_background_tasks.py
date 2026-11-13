"""
Tests for Background Task Tracking and Graceful Shutdown.

Requirements:
- Task exceptions are logged and do not become unhandled task exceptions.
- Active tasks are tracked during processing.
- Pending tasks are handled cleanly during shutdown.
- Webhook does not block while background tasks run.
"""

import asyncio
import logging
import pytest
import bot
import main


def test_track_background_task_success():
    """Tasks scheduled via track_background_task complete and are removed from ACTIVE_BACKGROUND_TASKS."""
    async def worker():
        await asyncio.sleep(0.01)
        return "completed"

    async def run_test():
        task = bot.track_background_task(worker())
        assert task in bot.ACTIVE_BACKGROUND_TASKS
        result = await task
        assert result == "completed"
        # Allow done callback to execute
        await asyncio.sleep(0.02)
        assert task not in bot.ACTIVE_BACKGROUND_TASKS

    asyncio.run(run_test())


def test_track_background_task_exception_logged_safely(caplog):
    """Unhandled exceptions in background tasks are caught by the done callback and logged without crashing."""
    async def failing_worker():
        await asyncio.sleep(0.01)
        raise RuntimeError("Simulated background task failure")

    async def run_test():
        with caplog.at_level(logging.ERROR):
            task = bot.track_background_task(failing_worker())
            await asyncio.sleep(0.05)
            assert task.done()
            assert task not in bot.ACTIVE_BACKGROUND_TASKS
            assert "Simulated background task failure" in caplog.text

    asyncio.run(run_test())


def test_shutdown_telegram_bot_cleans_up_active_tasks():
    """Application shutdown cancels and awaits pending tasks in ACTIVE_BACKGROUND_TASKS gracefully."""
    async def slow_running_worker():
        await asyncio.sleep(5.0)

    async def run_test():
        task = bot.track_background_task(slow_running_worker())
        assert task in bot.ACTIVE_BACKGROUND_TASKS
        assert not task.done()

        # Trigger graceful shutdown
        await bot.shutdown_telegram_bot()

        assert len(bot.ACTIVE_BACKGROUND_TASKS) == 0
        assert task.done()
        assert task.cancelled()

    asyncio.run(run_test())


def test_webhook_does_not_block_response(client, monkeypatch):
    """The webhook endpoint must return HTTP 200 immediately without waiting for task execution."""
    task_started = False
    task_finished = False

    async def slow_update_handler(update_data):
        nonlocal task_started, task_finished
        task_started = True
        await asyncio.sleep(1.0)
        task_finished = True

    monkeypatch.setattr(main, "handle_telegram_update", slow_update_handler)
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "valid_token")
    monkeypatch.setenv("TELEGRAM_SECRET_TOKEN", "test_secret")
    monkeypatch.setattr(main, "get_bot_token", lambda: "valid_token")
    monkeypatch.setattr(main, "get_secret_token", lambda: "test_secret")

    response = client.post(
        "/telegram/webhook",
        json={"update_id": 9999},
        headers={"X-Telegram-Bot-Api-Secret-Token": "test_secret"},
    )

    # Response is 200 OK immediately
    assert response.status_code == 200
    assert response.json() == {"ok": True}
