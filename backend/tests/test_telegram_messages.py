"""
Tests for Telegram Message Delivery & Reply Markup Serialization.

Regression tests to prevent:
'Telegram API sendMessage returned error: Bad Request: object expected as reply markup'

Requirements:
- Omit reply_markup entirely when no keyboard is needed.
- Pass valid JSON objects (dict) when inline/reply keyboards are used.
- Multi-chunk messages attach keyboard only to the final chunk.
- Check /start, /help, /language, and report analysis paths.
"""

import json
import asyncio
import pytest
import bot


@pytest.fixture
def capture_outgoing_messages(monkeypatch):
    """Intercepts _telegram_post to capture exact payloads sent to Telegram."""
    posts = []

    async def fake_telegram_post(method, payload):
        posts.append({"method": method, "payload": payload})
        if method == "sendMessage":
            return {"ok": True, "result": {"message_id": 1234}}
        if method == "answerCallbackQuery":
            return {"ok": True}
        return {"ok": True, "result": {}}

    monkeypatch.setattr(bot, "_telegram_post", fake_telegram_post)
    return posts


def test_send_message_without_keyboard_omits_reply_markup(capture_outgoing_messages):
    """Calling send_message without reply_markup must NOT include 'reply_markup' key in payload."""
    asyncio.run(bot.send_message(chat_id=111, text="Hello without keyboard"))

    assert len(capture_outgoing_messages) == 1
    call = capture_outgoing_messages[0]
    assert call["method"] == "sendMessage"
    payload = call["payload"]
    assert "reply_markup" not in payload, f"'reply_markup' must be omitted, but found: {payload.get('reply_markup')}"


def test_send_message_explicit_none_omits_reply_markup(capture_outgoing_messages):
    """Explicitly passing reply_markup=None must NOT include 'reply_markup' key in payload."""
    asyncio.run(bot.send_message(chat_id=111, text="Explicit None", reply_markup=None))

    assert len(capture_outgoing_messages) == 1
    payload = capture_outgoing_messages[0]["payload"]
    assert "reply_markup" not in payload


def test_send_message_empty_dict_omits_reply_markup(capture_outgoing_messages):
    """Passing an empty dict reply_markup={} must NOT include 'reply_markup' key in payload."""
    asyncio.run(bot.send_message(chat_id=111, text="Empty dict", reply_markup={}))

    assert len(capture_outgoing_messages) == 1
    payload = capture_outgoing_messages[0]["payload"]
    assert "reply_markup" not in payload


def test_send_message_with_valid_keyboard(capture_outgoing_messages):
    """Passing a valid keyboard dict includes reply_markup as a proper dict object."""
    keyboard = bot.get_language_inline_keyboard()
    asyncio.run(bot.send_message(chat_id=111, text="Choose language:", reply_markup=keyboard))

    assert len(capture_outgoing_messages) == 1
    payload = capture_outgoing_messages[0]["payload"]
    assert "reply_markup" in payload
    assert isinstance(payload["reply_markup"], dict)
    assert "inline_keyboard" in payload["reply_markup"]
    assert len(payload["reply_markup"]["inline_keyboard"][0]) == 3


def test_send_message_with_json_string_keyboard(capture_outgoing_messages):
    """If reply_markup is passed as a serialized JSON string, it is deserialized into an object."""
    keyboard_str = json.dumps(bot.get_language_inline_keyboard())
    asyncio.run(bot.send_message(chat_id=111, text="Choose language:", reply_markup=keyboard_str))

    assert len(capture_outgoing_messages) == 1
    payload = capture_outgoing_messages[0]["payload"]
    assert "reply_markup" in payload
    assert isinstance(payload["reply_markup"], dict)
    assert "inline_keyboard" in payload["reply_markup"]


def test_split_message_attaches_keyboard_only_to_final_chunk(capture_outgoing_messages):
    """For long split messages, earlier chunks have NO reply_markup, only final chunk has it."""
    long_text = ("Line of test report information.\n" * 200)  # Over 4000 chars
    keyboard = bot.get_language_inline_keyboard()

    asyncio.run(bot.send_message(chat_id=111, text=long_text, reply_markup=keyboard))

    assert len(capture_outgoing_messages) > 1
    # Check all chunks except the last
    for call in capture_outgoing_messages[:-1]:
        assert "reply_markup" not in call["payload"], "Earlier chunks must NOT have reply_markup"

    # Check final chunk
    final_payload = capture_outgoing_messages[-1]["payload"]
    assert "reply_markup" in final_payload
    assert isinstance(final_payload["reply_markup"], dict)


def test_start_command_has_valid_keyboard(capture_outgoing_messages):
    """The /start command response must include the language selection inline keyboard."""
    asyncio.run(bot._handle_start_command(chat_id=111))

    assert len(capture_outgoing_messages) == 1
    payload = capture_outgoing_messages[0]["payload"]
    assert "reply_markup" in payload
    assert isinstance(payload["reply_markup"], dict)
    assert "inline_keyboard" in payload["reply_markup"]


def test_help_command_omits_keyboard(capture_outgoing_messages):
    """The /help command response must NOT include reply_markup."""
    asyncio.run(bot._handle_help_command(chat_id=111))

    assert len(capture_outgoing_messages) == 1
    payload = capture_outgoing_messages[0]["payload"]
    assert "reply_markup" not in payload


def test_language_command_has_valid_keyboard(capture_outgoing_messages):
    """The /language command response must include the language selection inline keyboard."""
    asyncio.run(bot._handle_language_command(chat_id=111))

    assert len(capture_outgoing_messages) == 1
    payload = capture_outgoing_messages[0]["payload"]
    assert "reply_markup" in payload
    assert isinstance(payload["reply_markup"], dict)
    assert "inline_keyboard" in payload["reply_markup"]


def test_text_report_explanation_omits_keyboard(capture_outgoing_messages, monkeypatch):
    """Medical report explanations delivered via text must NOT include reply_markup."""
    mock_explanation = {
        "summary": "Hemoglobin normal.",
        "tests": [
            {
                "name": "Hemoglobin",
                "value": "14.2 g/dL",
                "normal_range": "13.0 - 17.0 g/dL",
                "status": "normal",
                "meaning": "Healthy.",
            }
        ],
        "questions_for_doctor": [],
        "disclaimer": "Educational information only.",
    }
    monkeypatch.setattr(bot, "explain_report", lambda text, language="English": mock_explanation)
    monkeypatch.setattr(bot, "log_usage", lambda **kwargs: True)

    asyncio.run(bot._process_text_report(chat_id=111, raw_text="Hemoglobin 14.2 g/dL"))

    # Should have sent "Analyzing..." and the final explanation
    assert len(capture_outgoing_messages) >= 2
    for call in capture_outgoing_messages:
        payload = call["payload"]
        assert "reply_markup" not in payload, f"Analysis messages must not include reply_markup: {payload}"
