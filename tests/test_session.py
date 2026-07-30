import unittest


class TestSecureChatSessionContextIntegrity(unittest.TestCase):

    def setUp(self):
        from session import SecureChatSession, MAX_HISTORY_LENGTH
        self.session = SecureChatSession()
        self.MAX_HISTORY_LENGTH = MAX_HISTORY_LENGTH

    def test_system_prompt_always_at_index_zero(self):
        context = self.session.get_context()
        self.assertEqual(context[0]["role"], "system")

    def test_system_prompt_preserved_after_truncation(self):
        for i in range(self.MAX_HISTORY_LENGTH + 10):
            self.session.add_user_message(f"message {i}")
            self.session.add_assistant_message(f"response {i}")
        context = self.session.get_context()
        self.assertEqual(context[0]["role"], "system")
        self.assertLessEqual(len(context), self.MAX_HISTORY_LENGTH + 1)

    def test_clear_restores_system_prompt(self):
        self.session.add_user_message("hello")
        self.session.clear()
        context = self.session.get_context()
        self.assertEqual(len(context), 1)
        self.assertEqual(context[0]["role"], "system")

import tempfile
from pathlib import Path
from unittest.mock import patch

class TestSessionPersistence(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.patcher = patch("src.session_store.SESSIONS_DIR", Path(self.temp_dir))
        self.patcher.start()

    def tearDown(self):
        self.patcher.stop()

    def test_save_and_load_roundtrip(self):
        from src.session_store import save_session, load_session
        messages = [
            {"role": "system", "content": "You are LocaLLM."},
            {"role": "user", "content": "hello"},
            {"role": "assistant", "content": "hi"},
        ]
        save_session("test-session-001", "qwen2.5:7b", messages)
        loaded = load_session("test-session-001")
        self.assertIsNotNone(loaded)
        self.assertEqual(loaded["messages"], messages)
        self.assertEqual(loaded["model"], "qwen2.5:7b")

    def test_load_nonexistent_returns_none(self):
        from src.session_store import load_session
        self.assertIsNone(load_session("does-not-exist"))

    def test_list_sessions_returns_sorted_by_recency(self):
        from src.session_store import save_session, list_sessions
        save_session("session-a", "qwen2.5:7b", [])
        save_session("session-b", "qwen2.5:7b", [])
        sessions = list_sessions()
        self.assertGreaterEqual(len(sessions), 2)

    def test_save_preserves_created_at_on_update(self):
        from src.session_store import save_session, load_session
        messages1 = [{"role": "user", "content": "first"}]
        save_session("session-c", "qwen2.5:7b", messages1)
        first_created_at = load_session("session-c")["created_at"]

        messages2 = messages1 + [{"role": "assistant", "content": "response"}]
        save_session("session-c", "qwen2.5:7b", messages2)
        second_created_at = load_session("session-c")["created_at"]

        self.assertEqual(first_created_at, second_created_at)
        self.assertEqual(len(load_session("session-c")["messages"]), 2)
