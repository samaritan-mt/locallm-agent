import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch, MagicMock

import main
from session import SecureChatSession


def _run_agent(inputs):
    main.agent_command(allow_execution=False, session_id=None, list_sessions=False, debug_timing=False)


class TestSessionProviderDefaults(unittest.TestCase):

    def test_default_provider_is_ollama(self):
        session = SecureChatSession()
        self.assertEqual(session.provider, "ollama")
        self.assertEqual(session.remote_call_count, 0)

    def test_api_key_is_never_an_attribute(self):
        session = SecureChatSession()
        self.assertFalse(hasattr(session, "openrouter_api_key"))
        self.assertFalse(hasattr(session, "api_key"))


class TestOpenRouterSwitchFlow(unittest.TestCase):

    @patch("main.os.environ.get", return_value=None)
    @patch("main.log_audit_event")
    @patch("main.OpenRouterProvider")
    @patch("main.getpass.getpass", return_value="bad-key")
    @patch("builtins.input", side_effect=["/openrouter", "/exit"])
    def test_failed_validation_leaves_session_on_ollama(
        self, mock_input, mock_getpass, mock_provider_cls, mock_log, mock_env
    ):
        mock_provider_cls.return_value.validate.return_value = (False, "OpenRouter rejected the API key.")

        real_session = SecureChatSession()
        with patch("main.SecureChatSession", return_value=real_session):
            _run_agent(None)  # must not raise

        self.assertEqual(real_session.provider, "ollama")

    @patch("main.os.environ.get", return_value=None)
    @patch("main.log_audit_event")
    @patch("main.OpenRouterProvider")
    @patch("main.typer.confirm", return_value=True)
    @patch("main.getpass.getpass", return_value="good-key")
    @patch("builtins.input", side_effect=["/openrouter", "/exit"])
    def test_successful_validation_and_confirm_switches_provider(
        self, mock_input, mock_getpass, mock_confirm, mock_provider_cls, mock_log, mock_env
    ):
        mock_provider_cls.return_value.validate.return_value = (True, "")
        mock_provider_cls.return_value.credentials = MagicMock()

        real_session = SecureChatSession()
        with patch("main.SecureChatSession", return_value=real_session):
            _run_agent(None)

        self.assertEqual(real_session.provider, "openrouter")

    @patch("main.os.environ.get", return_value=None)
    @patch("main.log_audit_event")
    @patch("main.OpenRouterProvider")
    @patch("main.typer.confirm", return_value=False)
    @patch("main.getpass.getpass", return_value="good-key")
    @patch("builtins.input", side_effect=["/openrouter", "/exit"])
    def test_declined_disclosure_stays_on_ollama_and_discards_key(
        self, mock_input, mock_getpass, mock_confirm, mock_provider_cls, mock_log, mock_env
    ):
        mock_provider_cls.return_value.validate.return_value = (True, "")
        mock_provider_cls.return_value.credentials = MagicMock()

        real_session = SecureChatSession()
        with patch("main.SecureChatSession", return_value=real_session):
            _run_agent(None)

        self.assertEqual(real_session.provider, "ollama")

    @patch("main.os.environ.get", return_value=None)
    @patch("main.log_audit_event")
    @patch("main.OpenRouterProvider")
    @patch("main.typer.confirm", return_value=True)
    @patch("main.getpass.getpass", return_value="good-key")
    @patch("builtins.input", side_effect=["/openrouter", "/ollama", "/exit"])
    def test_ollama_command_resets_provider_after_switch(
        self, mock_input, mock_getpass, mock_confirm, mock_provider_cls, mock_log, mock_env
    ):
        mock_provider_cls.return_value.validate.return_value = (True, "")
        mock_provider_cls.return_value.credentials = MagicMock()

        real_session = SecureChatSession()
        with patch("main.SecureChatSession", return_value=real_session):
            _run_agent(None)

        self.assertEqual(real_session.provider, "ollama")

    @patch("main.os.environ.get", return_value=None)
    @patch("main.log_audit_event")
    @patch("main.OpenRouterProvider")
    @patch("main.typer.confirm", return_value=True)
    @patch("main.getpass.getpass", return_value="good-key")
    @patch("builtins.input", side_effect=["/openrouter", "/exit"])
    def test_key_prompt_uses_getpass_not_input(
        self, mock_input, mock_getpass, mock_confirm, mock_provider_cls, mock_log, mock_env
    ):
        """getpass masks the key from terminal echo; input()/typer.prompt() would not."""
        mock_provider_cls.return_value.validate.return_value = (True, "")
        mock_provider_cls.return_value.credentials = MagicMock()

        _run_agent(None)

        mock_getpass.assert_called_once()
        # input() is only ever driven by the two scripted REPL lines above -
        # it is never asked to read the key itself.
        self.assertEqual(mock_input.call_count, 2)

    @patch("main.os.environ.get", return_value=None)
    @patch("main.log_audit_event")
    @patch("main.OpenRouterProvider")
    @patch("main.typer.confirm")
    @patch("main.getpass.getpass", return_value="good-key")
    @patch("builtins.input", side_effect=["/openrouter", "AKIAIOSFODNN7EXAMPLE", "/exit"])
    def test_secret_scanner_still_fires_while_on_openrouter(
        self, mock_input, mock_getpass, mock_confirm, mock_provider_cls, mock_log, mock_env
    ):
        mock_provider_cls.return_value.validate.return_value = (True, "")
        mock_provider_cls.return_value.credentials = MagicMock()
        # First confirm() is the OpenRouter disclosure, second is "Send anyway?" for the secret.
        mock_confirm.side_effect = [True, False]

        real_session = SecureChatSession()
        with patch("main.SecureChatSession", return_value=real_session):
            _run_agent(None)

        self.assertEqual(real_session.provider, "openrouter")
        self.assertEqual(mock_confirm.call_count, 2)
        self.assertIn("Send anyway", mock_confirm.call_args_list[1].args[0])


class TestOpenRouterCallCap(unittest.TestCase):

    @patch("main.os.environ.get", return_value=None)
    @patch("main.log_audit_event")
    @patch("main.OpenRouterRunTimePolicyConfig")
    @patch("main.OpenRouterProvider")
    @patch("main.typer.confirm", return_value=True)
    @patch("main.getpass.getpass", return_value="good-key")
    @patch("builtins.input", side_effect=["/openrouter", "hello", "/exit"])
    def test_max_calls_per_session_fails_closed_without_silent_fallback(
        self, mock_input, mock_getpass, mock_confirm, mock_provider_cls, mock_config_cls, mock_log, mock_env
    ):
        # A zero cap means the very first turn on openrouter must refuse to call out at all.
        mock_config_cls.return_value = SimpleNamespace(
            allowed_models=["meta-llama/llama-3.3-70b-instruct:free"],
            base_url="https://openrouter.ai/api/v1/chat/completions",
            max_output_tokens=100,
            max_calls_per_session=0,
        )
        mock_provider_cls.return_value.validate.return_value = (True, "")
        mock_provider_cls.return_value.credentials = MagicMock()

        real_session = SecureChatSession()
        with patch("main.SecureChatSession", return_value=real_session):
            _run_agent(None)

        mock_provider_cls.return_value.call.assert_not_called()
        # Fails closed on openrouter - it must NOT silently fall back to ollama.
        self.assertEqual(real_session.provider, "openrouter")
        self.assertEqual(real_session.remote_call_count, 0)


class TestPersistedSessionNeverContainsApiKey(unittest.TestCase):

    def test_save_session_only_serializes_id_model_messages(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            with patch("session_store.SESSIONS_DIR", Path(tmp_dir)):
                session = SecureChatSession()
                session.provider = "openrouter"
                # Simulate a future contributor mistakenly attaching a key to the
                # session object - save() must still never leak it (see Task 2).
                session._leaked_key_for_test_only = "sk-or-v1-should-never-persist"
                session.save()

                from session_store import load_session
                loaded = load_session(session.session_id)

        self.assertIsNotNone(loaded)
        raw = json.dumps(loaded)
        self.assertNotIn("sk-or-v1-should-never-persist", raw)
        self.assertNotIn("api_key", raw)
        self.assertNotIn("provider", loaded)


if __name__ == "__main__":
    unittest.main()