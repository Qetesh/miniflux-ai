import os
import sys
import types
from unittest import mock

import pytest

# Stub litellm before importing
_fake_litellm = types.ModuleType("litellm")

_fake_message = mock.MagicMock()
_fake_message.content = "Test summary"

_fake_choice = mock.MagicMock()
_fake_choice.message = _fake_message

_fake_response = mock.MagicMock()
_fake_response.choices = [_fake_choice]

_fake_litellm.completion = mock.MagicMock(return_value=_fake_response)
sys.modules["litellm"] = _fake_litellm


@pytest.fixture(autouse=True)
def reset_mocks():
    _fake_litellm.completion.reset_mock()
    _fake_litellm.completion.return_value = _fake_response
    _fake_message.content = "Test summary"
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
    # Clear cached modules so Config re-reads config.yml from new cwd
    for mod_name in list(sys.modules):
        if mod_name.startswith("core.") or mod_name.startswith("common."):
            del sys.modules[mod_name]
    yield


def test_litellm_basic_call():
    from core.get_ai_result import get_ai_result

    result = get_ai_result("Summarize this", "<p>Hello world</p>")
    assert result == "Test summary"
    _fake_litellm.completion.assert_called_once()


def test_litellm_drop_params():
    from core.get_ai_result import get_ai_result

    get_ai_result("Summarize", "<p>Test</p>")
    call_kwargs = _fake_litellm.completion.call_args[1]
    assert call_kwargs["drop_params"] is True


def test_litellm_model_forwarded():
    from core.get_ai_result import get_ai_result

    get_ai_result("Summarize", "<p>Test</p>")
    call_kwargs = _fake_litellm.completion.call_args[1]
    assert call_kwargs["model"] == "anthropic/claude-sonnet-4-6"


def test_litellm_api_key_forwarded():
    from core.get_ai_result import get_ai_result

    get_ai_result("Summarize", "<p>Test</p>")
    call_kwargs = _fake_litellm.completion.call_args[1]
    assert call_kwargs["api_key"] == "sk-test-123"


def test_litellm_content_placeholder():
    from core.get_ai_result import get_ai_result

    get_ai_result("Process ${content} now", "<p>Hello</p>")
    call_kwargs = _fake_litellm.completion.call_args[1]
    messages = call_kwargs["messages"]
    assert messages[0]["role"] == "system"
    assert messages[0]["content"] == "You are a helpful assistant."
    assert "Hello" in messages[1]["content"]


def test_litellm_system_prompt():
    from core.get_ai_result import get_ai_result

    get_ai_result("Custom system prompt", "<p>Content</p>")
    call_kwargs = _fake_litellm.completion.call_args[1]
    messages = call_kwargs["messages"]
    assert messages[0]["role"] == "system"
    assert messages[0]["content"] == "Custom system prompt"


def test_litellm_timeout_forwarded():
    from core.get_ai_result import get_ai_result

    get_ai_result("Summarize", "<p>Test</p>")
    call_kwargs = _fake_litellm.completion.call_args[1]
    assert call_kwargs["timeout"] == 30
