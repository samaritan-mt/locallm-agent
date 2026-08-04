import json
import unittest
from types import SimpleNamespace
from unittest.mock import patch, MagicMock

from openrouter.errors import UnauthorizedResponseError, TooManyRequestsResponseError

from llm_router import LLMParams
from policy.config import OpenRouterRunTimePolicyConfig
from providers.openrouter_provider import OpenRouterProvider, RemoteCredentials


def _fake_message(content=None, tool_calls=None):
    return SimpleNamespace(content=content, tool_calls=tool_calls)


def _fake_tool_call(name, arguments_json, call_id="call_1"):
    return SimpleNamespace(
        id=call_id,
        type="function",
        function=SimpleNamespace(name=name, arguments=arguments_json),
    )


class TestNormalizeMessage(unittest.TestCase):
    """The SDK returns a pydantic ChatAssistantMessage; main.py's tool-call loop
    expects the same plain-dict shape LocalOllamaProvider already returns."""

    def test_plain_text_message(self):
        message = _fake_message(content="hello there")
        normalized = OpenRouterProvider._normalize_message(message)
        self.assertEqual(normalized, {"role": "assistant", "content": "hello there", "tool_calls": None})

    def test_none_content_becomes_empty_string(self):
        message = _fake_message(content=None)
        normalized = OpenRouterProvider._normalize_message(message)
        self.assertEqual(normalized["content"], "")

    def test_tool_call_arguments_decoded_from_json_string(self):
        # The OpenAI-compatible wire format encodes `arguments` as a JSON string;
        # Ollama already hands back a parsed dict, so this must be decoded to
        # match - main.py does args.get('command') directly, not json.loads(args).
        tool_call = _fake_tool_call("execute_os_command", '{"thought": "why", "command": "ls"}')
        message = _fake_message(content=None, tool_calls=[tool_call])
        normalized = OpenRouterProvider._normalize_message(message)

        self.assertEqual(len(normalized["tool_calls"]), 1)
        args = normalized["tool_calls"][0]["function"]["arguments"]
        self.assertIsInstance(args, dict)
        self.assertEqual(args["command"], "ls")

    def test_malformed_tool_call_arguments_are_passed_through_raw(self):
        tool_call = _fake_tool_call("execute_os_command", "{not valid json")
        message = _fake_message(content=None, tool_calls=[tool_call])
        normalized = OpenRouterProvider._normalize_message(message)
        # Falls back to the raw string rather than raising - validate_tool_call
        # downstream is responsible for rejecting it cleanly.
        self.assertEqual(normalized["tool_calls"][0]["function"]["arguments"], "{not valid json")


class TestSanitizeHistory(unittest.TestCase):
    """session.messages is shared across providers; Ollama tolerates dict-shaped
    tool_call arguments and tool messages with no tool_call_id, but OpenRouter's
    strict OpenAI schema rejects both. _sanitize_history must fix this for the
    outgoing request without mutating the caller's history."""

    def test_dict_arguments_are_serialized_to_json_string(self):
        history = [
            {"role": "user", "content": "list files"},
            {
                "role": "assistant",
                "content": None,
                "tool_calls": [{
                    "id": "abc",
                    "type": "function",
                    "function": {"name": "execute_os_command", "arguments": {"command": "ls"}},
                }],
            },
        ]
        sanitized = OpenRouterProvider._sanitize_history(history)
        arguments = sanitized[1]["tool_calls"][0]["function"]["arguments"]
        self.assertIsInstance(arguments, str)
        self.assertEqual(json.loads(arguments), {"command": "ls"})

    def test_string_arguments_are_left_untouched(self):
        history = [{
            "role": "assistant",
            "content": None,
            "tool_calls": [{"id": "abc", "type": "function",
                             "function": {"name": "x", "arguments": '{"a": 1}'}}],
        }]
        sanitized = OpenRouterProvider._sanitize_history(history)
        self.assertEqual(sanitized[0]["tool_calls"][0]["function"]["arguments"], '{"a": 1}')

    def test_tool_message_gets_tool_call_id_from_preceding_assistant_call(self):
        history = [
            {"role": "user", "content": "list files"},
            {
                "role": "assistant",
                "content": None,
                "tool_calls": [{"id": "call_42", "type": "function",
                                 "function": {"name": "execute_os_command", "arguments": {"command": "ls"}}}],
            },
            {"role": "tool", "content": "file1\nfile2"},
        ]
        sanitized = OpenRouterProvider._sanitize_history(history)
        self.assertEqual(sanitized[2]["tool_call_id"], "call_42")

    def test_missing_tool_call_id_on_assistant_message_is_generated(self):
        history = [
            {
                "role": "assistant",
                "content": None,
                "tool_calls": [{"function": {"name": "execute_os_command", "arguments": {"command": "ls"}}}],
            },
            {"role": "tool", "content": "output"},
        ]
        sanitized = OpenRouterProvider._sanitize_history(history)
        generated_id = sanitized[0]["tool_calls"][0]["id"]
        self.assertTrue(generated_id)
        self.assertEqual(sanitized[1]["tool_call_id"], generated_id)

    def test_existing_tool_call_id_is_preserved(self):
        history = [
            {
                "role": "assistant",
                "content": None,
                "tool_calls": [{"id": "call_99", "type": "function",
                                 "function": {"name": "x", "arguments": {}}}],
            },
            {"role": "tool", "content": "output", "tool_call_id": "call_99"},
        ]
        sanitized = OpenRouterProvider._sanitize_history(history)
        self.assertEqual(sanitized[1]["tool_call_id"], "call_99")

    def test_does_not_mutate_original_history(self):
        original_tool_call = {"id": "abc", "type": "function",
                               "function": {"name": "x", "arguments": {"a": 1}}}
        history = [{"role": "assistant", "content": None, "tool_calls": [original_tool_call]}]
        OpenRouterProvider._sanitize_history(history)
        # The caller's dicts (e.g. session.messages, replayed to Ollama too) must be untouched.
        self.assertEqual(original_tool_call["function"]["arguments"], {"a": 1})

    def test_plain_messages_pass_through_unchanged(self):
        history = [
            {"role": "system", "content": "you are helpful"},
            {"role": "user", "content": "hi"},
            {"role": "assistant", "content": "hello"},
        ]
        self.assertEqual(OpenRouterProvider._sanitize_history(history), history)


class TestOpenRouterProviderCall(unittest.TestCase):

    def _provider(self):
        config = OpenRouterRunTimePolicyConfig()
        with patch("providers.openrouter_provider.OpenRouter"):
            return OpenRouterProvider(config, RemoteCredentials(api_key="test-key"))

    def test_call_refuses_without_allow_remote_endpoint(self):
        provider = self._provider()
        params = LLMParams(model="x", allow_remote_endpoint=False)
        result = provider.call({"model": "x", "messages": [], "temperature": 0.2}, "unused", params)
        self.assertIn("allow-remote-endpoint", result["content"])
        provider.client.chat.send.assert_not_called()

    def test_call_wraps_401_as_clean_message(self):
        provider = self._provider()
        provider.client.chat.send.side_effect = UnauthorizedResponseError.__new__(UnauthorizedResponseError)
        params = LLMParams(model="x", allow_remote_endpoint=True)
        with self.assertRaises(ValueError) as ctx:
            provider.call({"model": "x", "messages": [], "temperature": 0.2}, "unused", params)
        self.assertEqual(str(ctx.exception), "OpenRouter rejected the API key.")

    def test_call_wraps_429_as_clean_message(self):
        provider = self._provider()
        provider.client.chat.send.side_effect = TooManyRequestsResponseError.__new__(TooManyRequestsResponseError)
        params = LLMParams(model="x", allow_remote_endpoint=True)
        with self.assertRaises(ValueError) as ctx:
            provider.call({"model": "x", "messages": [], "temperature": 0.2}, "unused", params)
        self.assertIn("rate limit", str(ctx.exception))

    def test_call_returns_normalized_dict_on_success(self):
        provider = self._provider()
        choice = SimpleNamespace(message=_fake_message(content="hi"))
        provider.client.chat.send.return_value = SimpleNamespace(choices=[choice])
        params = LLMParams(model="x", allow_remote_endpoint=True)
        result = provider.call({"model": "x", "messages": [{"role": "user", "content": "hi"}], "temperature": 0.2}, "unused", params)
        self.assertEqual(result, {"role": "assistant", "content": "hi", "tool_calls": None})

    def test_validate_success(self):
        provider = self._provider()
        choice = SimpleNamespace(message=_fake_message(content="pong"))
        provider.client.chat.send.return_value = SimpleNamespace(choices=[choice])
        ok, error = provider.validate()
        self.assertTrue(ok)
        self.assertEqual(error, "")

    def test_validate_failure_does_not_raise(self):
        provider = self._provider()
        provider.client.chat.send.side_effect = UnauthorizedResponseError.__new__(UnauthorizedResponseError)
        ok, error = provider.validate()
        self.assertFalse(ok)
        self.assertEqual(error, "OpenRouter rejected the API key.")


if __name__ == "__main__":
    unittest.main()
