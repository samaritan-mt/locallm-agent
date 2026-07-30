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

    @patch("tools.command.typer.confirm", return_value=False)
    def test_execute_os_command_denied_by_user(self, mock_confirm):
        from tools.command import execute_os_command
        result = execute_os_command("rm -rf /")
        self.assertIn("denied", result.lower())

    @patch("tools.command.typer.confirm", return_value=False)
    def test_write_file_denied_by_user(self, mock_confirm):
        from tools.command import write_file
        result = write_file(os.path.join(os.getcwd(), "out.txt"), "data")
        self.assertIn("denied", result.lower())
