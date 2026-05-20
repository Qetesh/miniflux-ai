import os
import sys
import types
from unittest import mock

import pytest

# ---------------------------------------------------------------------------
# Stub litellm + its exceptions before any project imports
# ---------------------------------------------------------------------------
_fake_litellm = types.ModuleType("litellm")
_fake_exceptions = types.ModuleType("litellm.exceptions")


class _FakeAuthenticationError(Exception):
    pass


class _FakeBadRequestError(Exception):
    pass


class _FakeNotFoundError(Exception):
    pass


class _FakeRateLimitError(Exception):
    pass


class _FakeTimeout(Exception):
    pass


_fake_exceptions.AuthenticationError = _FakeAuthenticationError
_fake_exceptions.BadRequestError = _FakeBadRequestError
_fake_exceptions.NotFoundError = _FakeNotFoundError
_fake_exceptions.RateLimitError = _FakeRateLimitError
_fake_exceptions.Timeout = _FakeTimeout

_fake_litellm.exceptions = _fake_exceptions

_fake_message = mock.MagicMock()
_fake_message.content = "Test summary"

_fake_choice = mock.MagicMock()
_fake_choice.message = _fake_message

_fake_response = mock.MagicMock()
_fake_response.choices = [_fake_choice]

_fake_litellm.completion = mock.MagicMock(return_value=_fake_response)

sys.modules["litellm"] = _fake_litellm
sys.modules["litellm.exceptions"] = _fake_exceptions


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------
@pytest.fixture(autouse=True)
def reset_mocks():
    _fake_litellm.completion.reset_mock()
    _fake_litellm.completion.side_effect = None
    _fake_litellm.completion.return_value = _fake_response
    _fake_message.content = "Test summary"
    _fake_choice.message = _fake_message
    _fake_response.choices = [_fake_choice]
    yield


@pytest.fixture(autouse=True)
def setup_config(tmp_path, monkeypatch):
    config_file = tmp_path / "config.yml"
    config_file.write_text(
        """
llm:
  provider: litellm
  model: anthropic/claude-sonnet-4-6
  api_key: sk-test-123
  timeout: 30
miniflux:
  base_url: http://localhost
  api_key: test
"""
    )
    monkeypatch.chdir(tmp_path)
    for mod_name in list(sys.modules):
        if mod_name.startswith("core.") or mod_name.startswith("common."):
            del sys.modules[mod_name]
    yield


def _get_ai_result():
    from core.get_ai_result import get_ai_result
    return get_ai_result


# ---------------------------------------------------------------------------
# Unit tests: basic functionality
# ---------------------------------------------------------------------------
def test_basic_call():
    result = _get_ai_result()("Summarize this", "<p>Hello world</p>")
    assert result == "Test summary"
    _fake_litellm.completion.assert_called_once()


def test_drop_params_always_true():
    _get_ai_result()("Summarize", "<p>Test</p>")
    call_kwargs = _fake_litellm.completion.call_args[1]
    assert call_kwargs["drop_params"] is True


def test_model_forwarded():
    _get_ai_result()("Summarize", "<p>Test</p>")
    call_kwargs = _fake_litellm.completion.call_args[1]
    assert call_kwargs["model"] == "anthropic/claude-sonnet-4-6"


def test_api_key_forwarded():
    _get_ai_result()("Summarize", "<p>Test</p>")
    call_kwargs = _fake_litellm.completion.call_args[1]
    assert call_kwargs["api_key"] == "sk-test-123"


def test_timeout_forwarded():
    _get_ai_result()("Summarize", "<p>Test</p>")
    call_kwargs = _fake_litellm.completion.call_args[1]
    assert call_kwargs["timeout"] == 30


def test_content_placeholder_uses_system_assistant():
    _get_ai_result()("Process ${content} now", "<p>Hello</p>")
    call_kwargs = _fake_litellm.completion.call_args[1]
    messages = call_kwargs["messages"]
    assert messages[0]["role"] == "system"
    assert messages[0]["content"] == "You are a helpful assistant."
    assert "Hello" in messages[1]["content"]


def test_no_placeholder_uses_prompt_as_system():
    _get_ai_result()("Custom system prompt", "<p>Content</p>")
    call_kwargs = _fake_litellm.completion.call_args[1]
    messages = call_kwargs["messages"]
    assert messages[0]["role"] == "system"
    assert messages[0]["content"] == "Custom system prompt"


def test_provider_prefixed_model_string():
    _get_ai_result()("Hi", "<p>Test</p>")
    call_kwargs = _fake_litellm.completion.call_args[1]
    assert "/" in call_kwargs["model"]


# ---------------------------------------------------------------------------
# Unit tests: API key omitted when not set
# ---------------------------------------------------------------------------
def test_api_key_omitted_when_none(tmp_path, monkeypatch):
    config_file = tmp_path / "config.yml"
    config_file.write_text(
        """
llm:
  provider: litellm
  model: openai/gpt-4o-mini
  timeout: 30
miniflux:
  base_url: http://localhost
  api_key: test
"""
    )
    monkeypatch.chdir(tmp_path)
    for mod_name in list(sys.modules):
        if mod_name.startswith("core.") or mod_name.startswith("common."):
            del sys.modules[mod_name]

    from core.get_ai_result import get_ai_result
    get_ai_result("Summarize", "<p>Test</p>")
    call_kwargs = _fake_litellm.completion.call_args[1]
    assert "api_key" not in call_kwargs


# ---------------------------------------------------------------------------
# Unit tests: exception handling (litellm-specific exceptions)
# ---------------------------------------------------------------------------
def test_auth_error_raises():
    _fake_litellm.completion.side_effect = _FakeAuthenticationError("Invalid API key")
    with pytest.raises(_FakeAuthenticationError, match="Invalid API key"):
        _get_ai_result()("Summarize", "<p>Test</p>")


def test_not_found_error_raises():
    _fake_litellm.completion.side_effect = _FakeNotFoundError("Model not found")
    with pytest.raises(_FakeNotFoundError, match="Model not found"):
        _get_ai_result()("Summarize", "<p>Test</p>")


def test_rate_limit_error_raises():
    _fake_litellm.completion.side_effect = _FakeRateLimitError("429 Too Many Requests")
    with pytest.raises(_FakeRateLimitError, match="429"):
        _get_ai_result()("Summarize", "<p>Test</p>")


def test_timeout_error_raises():
    _fake_litellm.completion.side_effect = _FakeTimeout("Request timed out")
    with pytest.raises(_FakeTimeout, match="timed out"):
        _get_ai_result()("Summarize", "<p>Test</p>")


def test_bad_request_error_raises():
    _fake_litellm.completion.side_effect = _FakeBadRequestError("context_length_exceeded")
    with pytest.raises(_FakeBadRequestError, match="context_length_exceeded"):
        _get_ai_result()("Summarize", "<p>Test</p>")


def test_generic_exception_still_raises():
    _fake_litellm.completion.side_effect = RuntimeError("unexpected")
    with pytest.raises(RuntimeError, match="unexpected"):
        _get_ai_result()("Summarize", "<p>Test</p>")


# ---------------------------------------------------------------------------
# Unit tests: empty/null/malformed response
# ---------------------------------------------------------------------------
def test_empty_response_content_returns_empty_string():
    _fake_message.content = None
    result = _get_ai_result()("Summarize", "<p>Test</p>")
    assert result == ""


def test_empty_string_response():
    _fake_message.content = ""
    result = _get_ai_result()("Summarize", "<p>Test</p>")
    assert result == ""


def test_no_choices_raises():
    _fake_response.choices = []
    with pytest.raises((IndexError, AttributeError)):
        _get_ai_result()("Summarize", "<p>Test</p>")


# ---------------------------------------------------------------------------
# Unit tests: max_length truncation
# ---------------------------------------------------------------------------
def test_max_length_truncation(tmp_path, monkeypatch):
    config_file = tmp_path / "config.yml"
    config_file.write_text(
        """
llm:
  provider: litellm
  model: openai/gpt-4o-mini
  api_key: sk-test
  timeout: 30
  max_length: 10
miniflux:
  base_url: http://localhost
  api_key: test
"""
    )
    monkeypatch.chdir(tmp_path)
    for mod_name in list(sys.modules):
        if mod_name.startswith("core.") or mod_name.startswith("common."):
            del sys.modules[mod_name]

    from core.get_ai_result import get_ai_result
    get_ai_result("Summarize ${content}", "<p>" + "A" * 100 + "</p>")
    call_kwargs = _fake_litellm.completion.call_args[1]
    user_content = call_kwargs["messages"][1]["content"]
    assert len(user_content) < 100


# ---------------------------------------------------------------------------
# Integration test: full mocked request-response cycle
# ---------------------------------------------------------------------------
def test_full_request_response_cycle():
    get_ai_result = _get_ai_result()
    result = get_ai_result(
        "You are a news summarizer. Summarize: ${content}",
        "<html><body><h1>Breaking News</h1><p>AI advances continue.</p></body></html>",
    )
    assert result == "Test summary"
    call_kwargs = _fake_litellm.completion.call_args[1]
    assert call_kwargs["model"] == "anthropic/claude-sonnet-4-6"
    assert call_kwargs["drop_params"] is True
    assert call_kwargs["api_key"] == "sk-test-123"
    assert call_kwargs["timeout"] == 30
    assert len(call_kwargs["messages"]) == 2
    assert call_kwargs["messages"][0]["role"] == "system"
    assert call_kwargs["messages"][1]["role"] == "user"
    assert "AI advances" in call_kwargs["messages"][1]["content"]
