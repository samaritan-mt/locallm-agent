import unittest

class TestSystemPromptDeterminism(unittest.TestCase):

    def setUp(self):
        from src.policy.prompts import DynamicPromptManager
        self.manager = DynamicPromptManager()

    def test_system_prompt_is_deterministic(self):
        """Same inputs must always produce identical output for KV cache to work."""
        enabled_tools = ["execute_os_command", "write_file", "read_file"]
        
        first = self.manager.build_system_prompt("base_agent", enabled_tools, max_input_chars=1000000)
        second = self.manager.build_system_prompt("base_agent", enabled_tools, max_input_chars=1000000)
        self.assertEqual(first, second, "System prompt output is non-deterministic — KV cache will never hit.")

    def test_assert_deterministic_helper(self):
        # Should not raise
        self.manager.assert_deterministic("base_agent", ["execute_os_command"], max_input_chars=1000000)

    def test_system_prompt_starts_with_identity(self):
        """System prompt must begin with the core identity section."""
        prompt = self.manager.build_system_prompt("base_agent", ["execute_os_command"], max_input_chars=1000000)
        self.assertIn("LocaLLM", prompt[:1000])

    def test_disabled_tool_not_in_prompt(self):
        """Tool documentation must only appear when the tool is enabled."""
        prompt_with_write = self.manager.build_system_prompt("base_agent", ["execute_os_command", "write_file"], max_input_chars=1000000)
        prompt_without_write = self.manager.build_system_prompt("base_agent", ["execute_os_command"], max_input_chars=1000000)
        self.assertIn("write_file", prompt_with_write)
        self.assertNotIn("write_file", prompt_without_write)

    def test_no_timestamp_in_system_prompt(self):
        """Timestamps in the system prompt invalidate the KV cache."""
        import re
        prompt = self.manager.build_system_prompt("base_agent", ["execute_os_command"], max_input_chars=1000000)
        timestamp_pattern = r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}"
        match = re.search(timestamp_pattern, prompt)
        self.assertIsNone(match, f"System prompt contains a timestamp at: {match.group(0) if match else ''}")
