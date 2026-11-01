import re
from typing import Any

from .config import settings


def redact(text: str) -> str:
    for secret in (
        settings.ai_api_key,
        settings.demo_login_token,
        settings.session_secret,
        settings.mock_action_secret,
    ):
        if secret and len(secret) >= 8:
            text = text.replace(secret, "[REDACTED_SECRET]")
    text = re.sub(r"[A-Za-z0-9_.+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", "[REDACTED_EMAIL]", text)
    text = re.sub(r"(?<!\d)(?:\d[ -]?){13,19}(?!\d)", "[REDACTED_NUMBER]", text)
    text = re.sub(r"(?i)\b(cvv|otp|password|api[_ -]?key|token)\s*[:=]\s*[^\s,;]+", r"\1: [REDACTED]", text)
    return text


def sanitized(value: Any) -> Any:
    if isinstance(value, str):
        return redact(value)
    if isinstance(value, dict):
        return {
            key: sanitized(item)
            for key, item in value.items()
            if key not in ("name", "email", "tracking_number")
        }
    if isinstance(value, list):
        return [sanitized(item) for item in value]
    return value
