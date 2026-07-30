import os
import unittest
from unittest.mock import patch, mock_open


class TestWriteFilePathTraversal(unittest.TestCase):

    @patch("tools.command.typer.confirm", return_value=True)
    @patch("builtins.open", new_callable=mock_open)
    def test_write_within_cwd_is_allowed(self, mock_file, mock_confirm):
        from tools.command import write_file
        result = write_file(os.path.join(os.getcwd(), "output.txt"), "content")
        self.assertIn("success", result.lower())

    @patch("tools.command.typer.confirm", return_value=True)
    def test_write_traversal_is_blocked(self, mock_confirm):
        from tools.command import write_file
        result = write_file("/etc/passwd", "pwned")
        self.assertIn("security violation", result.lower())

    @patch("tools.command.typer.confirm", return_value=True)
    def test_write_dotdot_traversal_is_blocked(self, mock_confirm):
        from tools.command import write_file
        result = write_file("../../etc/shadow", "pwned")
        self.assertIn("security violation", result.lower())


class TestReadFilePathTraversal(unittest.TestCase):

    @patch("builtins.open", new_callable=mock_open, read_data="file content")
    def test_read_within_cwd_is_allowed(self, mock_file):
        from tools.command import read_file
        result = read_file(os.path.join(os.getcwd(), "src/main.py"))
        self.assertEqual(result, "file content")

    def test_read_traversal_is_blocked(self):
        from tools.command import read_file
        result = read_file("/etc/passwd")
        self.assertIn("security violation", result.lower())

    def test_read_dotdot_traversal_is_blocked(self):
        from tools.command import read_file
        result = read_file("../../etc/shadow")
        self.assertIn("security violation", result.lower())


class TestUserApprovalGate(unittest.TestCase):

    @patch("tools.command.SessionPolicyConfig")
    @patch("tools.command.typer.confirm", return_value=False)
    def test_execute_os_command_denied_by_user(self, mock_confirm, mock_policy):
        mock_policy.return_value.can_execute_commands = True
        from tools.command import execute_os_command
        result = execute_os_command("rm -rf /")
        self.assertIn("denied", result.lower())

    @patch("tools.command.typer.confirm", return_value=False)
    def test_write_file_denied_by_user(self, mock_confirm):
        from tools.command import write_file
        result = write_file(os.path.join(os.getcwd(), "out.txt"), "data")
        self.assertIn("denied", result.lower())

import json

class TestToolCallValidator(unittest.TestCase):

    def setUp(self):
        from tools.schemas import ollama_json_schema, write_file_schema, read_file_schema
        from tools.validator import register_schemas
        register_schemas([ollama_json_schema(), write_file_schema(), read_file_schema()])

    def test_valid_execute_os_command(self):
        from tools.validator import validate_tool_call
        call = {"function": {"name": "execute_os_command", "arguments": '{"thought": "test", "command": "ls"}'}}
        valid, err = validate_tool_call(call)
        self.assertTrue(valid, err)

    def test_missing_command_parameter(self):
        from tools.validator import validate_tool_call
        call = {"function": {"name": "execute_os_command", "arguments": '{"thought": "test"}'}}
        valid, err = validate_tool_call(call)
        self.assertFalse(valid)
        self.assertIn("command", err)

    def test_empty_thought_rejected(self):
        from tools.validator import validate_tool_call
        call = {"function": {"name": "execute_os_command", "arguments": '{"thought": "", "command": "ls"}'}}
        valid, err = validate_tool_call(call)
        self.assertFalse(valid)
        self.assertIn("thought", err)

    def test_malformed_json_arguments(self):
        from tools.validator import validate_tool_call
        call = {"function": {"name": "write_file", "arguments": "{not valid json"}}
        valid, err = validate_tool_call(call)
        self.assertFalse(valid)
        self.assertIn("malformed", err.lower())

    def test_unknown_tool_rejected(self):
        from tools.validator import validate_tool_call
        call = {"function": {"name": "delete_everything", "arguments": '{}'}}
        valid, err = validate_tool_call(call)
        self.assertFalse(valid)
        self.assertIn("Unknown tool", err)

    def test_oversized_argument_rejected(self):
        from tools.validator import validate_tool_call
        giant = "x" * 40_000
        call = {"function": {"name": "execute_os_command", "arguments": json.dumps({"thought": "ok", "command": giant})}}
        valid, err = validate_tool_call(call)
        self.assertFalse(valid)
        self.assertIn("32KB", err)
