import re
from dataclasses import dataclass

@dataclass
class SecretMatch:
    pattern_name: str
    match_preview: str  # First 6 chars of matched value + "..."

SECRET_PATTERNS = {
    "AWS Access Key":        r"AKIA[0-9A-Z]{16}",
    "AWS Secret Key":        r"(?i)aws.{0,20}secret.{0,20}['\"][0-9a-zA-Z/+]{40}['\"]",
    "Private Key Block":     r"-----BEGIN (RSA |EC |OPENSSH )?PRIVATE KEY-----",
    "Generic API Key":       r"(?i)(api[_\-]?key|apikey)\s*[:=]\s*['\"]?[A-Za-z0-9\-_]{20,}",
    "Generic Token":         r"(?i)(token|secret|password)\s*[:=]\s*['\"]?[A-Za-z0-9\-_!@#$%^&*]{16,}",
    "GitHub Token":          r"gh[pousr]_[A-Za-z0-9]{36}",
    "Slack Token":           r"xox[baprs]-[A-Za-z0-9\-]{10,}",
    "Anthropic API Key":     r"sk-ant-[A-Za-z0-9\-_]{32,}",
    "OpenAI API Key":        r"sk-[A-Za-z0-9]{48}",
    "Database URL":          r"(?i)(postgres|mysql|mongodb)://[^:]+:[^@]+@",
}

def scan_for_secrets(text: str) -> list[SecretMatch]:
    """Returns a list of detected secret patterns. Empty list means clean."""
    matches = []
    for name, pattern in SECRET_PATTERNS.items():
        for m in re.finditer(pattern, text):
            preview = m.group(0)[:6] + "..."
            matches.append(SecretMatch(pattern_name=name, match_preview=preview))
    return matches

def redact_secrets(text: str) -> str:
    """Replace matched secret values with [REDACTED]. Use for audit logs."""
    for name, pattern in SECRET_PATTERNS.items():
        text = re.sub(pattern, f"[REDACTED:{name}]", text, flags=re.IGNORECASE)
    return text
