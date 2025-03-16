import re


class PIIHandler:
    def __init__(self, patterns: list[str]) -> None:
        self.patterns = [re.compile(p) for p in patterns]

    def detect_and_redact(self, text: str) -> tuple[str, bool]:
        """Detect and redact PII from text."""
        has_pii = False
        for pattern in self.patterns:
            if pattern.search(text):
                has_pii = True
                text = pattern.sub("[REDACTED]", text)
        return text, has_pii
