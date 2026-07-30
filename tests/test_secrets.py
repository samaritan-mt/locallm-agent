import unittest
from src.policy.secrets import scan_for_secrets, redact_secrets, SecretMatch

class TestSecretsScanner(unittest.TestCase):

    def test_detects_aws_access_key(self):
        text = "My key is AKIAIOSFODNN7EXAMPLE and it works."
        matches = scan_for_secrets(text)
        self.assertTrue(any(m.pattern_name == "AWS Access Key" for m in matches))

    def test_detects_private_key_block(self):
        text = "-----BEGIN RSA PRIVATE KEY-----\nMIIEpAIBAAK..."
        matches = scan_for_secrets(text)
        self.assertTrue(any("Private Key" in m.pattern_name for m in matches))

    def test_detects_github_token(self):
        text = "token: ghp_ABCDEFGHIJKLMNOPQRSTUVWXYZabcd123456"
        matches = scan_for_secrets(text)
        self.assertTrue(any(m.pattern_name == "GitHub Token" for m in matches))

    def test_clean_text_returns_empty(self):
        text = "list all files in the src directory"
        matches = scan_for_secrets(text)
        self.assertEqual(matches, [])

    def test_redact_replaces_aws_key(self):
        text = "Key: AKIAIOSFODNN7EXAMPLE"
        redacted = redact_secrets(text)
        self.assertNotIn("AKIAIOSFODNN7EXAMPLE", redacted)
        self.assertIn("[REDACTED", redacted)

    def test_redact_does_not_alter_clean_text(self):
        text = "Run ls -la in the workspace directory."
        self.assertEqual(redact_secrets(text), text)

    def test_match_preview_truncates(self):
        text = "AKIAIOSFODNN7EXAMPLE"
        matches = scan_for_secrets(text)
        self.assertTrue(matches[0].match_preview.endswith("..."))
        self.assertLessEqual(len(matches[0].match_preview), 10)
