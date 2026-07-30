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
