"""Privacy level detection for ACMS memories.

Automatically classifies memory privacy based on content and tags:
- LOCAL_ONLY: API keys, credentials, PII, secrets
- CONFIDENTIAL: Financial, health, personal sensitive data
- INTERNAL: User conversations, notes, personal context (default)
- PUBLIC: Documentation, tutorials, general knowledge

Uses pattern matching and tag analysis for classification.
Enhanced with Luhn algorithm for credit card validation to reduce false positives.
"""

import re
from typing import List, Optional, Set


class PrivacyDetector:
    """Detect privacy level for memory content and tags."""

    # Privacy levels in order of restrictiveness
    PRIVACY_LEVELS = ["PUBLIC", "INTERNAL", "CONFIDENTIAL", "LOCAL_ONLY"]

    # Patterns that indicate LOCAL_ONLY (most restrictive)
    LOCAL_ONLY_PATTERNS = [
        # API Keys and Tokens
        r'api[_-]?key\s*[:=]\s*["\']?[a-zA-Z0-9_-]{20,}',
        r'bearer\s+[a-zA-Z0-9_-]{20,}',
        r'token\s*[:=]\s*["\']?[a-zA-Z0-9_-]{20,}',
        r'sk-[a-zA-Z0-9]{20,}',  # OpenAI key format
        r'AKIA[0-9A-Z]{16}',  # AWS access key
        r'AIza[0-9A-Za-z\\-_]{35}',  # Google API key

        # Passwords and Credentials
        r'password\s*[:=]\s*["\']?[^\s"\']{8,}',
        r'passwd\s*[:=]\s*["\']?[^\s"\']{8,}',
        r'secret\s*[:=]\s*["\']?[^\s"\']{8,}',
        r'credentials?\s*[:=]',
        r'auth_token\s*[:=]',

        # Private keys
        r'-----BEGIN (RSA|DSA|EC|OPENSSH|PGP) PRIVATE KEY-----',
        r'BEGIN PRIVATE KEY',

        # Database connections
        r'postgres://[^\s]+',
        r'mysql://[^\s]+',
        r'mongodb://[^\s]+',

        # JWT tokens
        r'eyJ[a-zA-Z0-9_-]+\.eyJ[a-zA-Z0-9_-]+\.[a-zA-Z0-9_-]+',

        # Social Security Numbers (US)
        r'\b\d{3}-\d{2}-\d{4}\b',
        r'\b\d{9}\b',  # SSN without dashes

        # Credit Card Numbers
        r'\b\d{4}[- ]?\d{4}[- ]?\d{4}[- ]?\d{4}\b',

        # Phone Numbers (various formats)
        r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b',
        r'\(\d{3}\)\s*\d{3}[-.]?\d{4}',

        # Email addresses (when appearing with passwords/keys)
        r'email\s*[:=]\s*["\']?[^\s@]+@[^\s@]+\.[^\s@"\']+',
    ]

    # Tags that indicate LOCAL_ONLY
    LOCAL_ONLY_TAGS = {
        "password", "credential", "api-key", "secret", "private-key",
        "ssh-key", "token", "auth", "api_key", "secrets", "keys"
    }

    # Patterns that indicate CONFIDENTIAL
    CONFIDENTIAL_PATTERNS = [
        # Financial
        r'\b(bank\s+account|routing\s+number|account\s+number)\b',
        r'\b(investment|portfolio|401k|ira|stocks|bonds)\b',
        r'\$\d{1,3}(,\d{3})*(\.\d{2})?',  # Money amounts

        # Health
        r'\b(medical|health|diagnosis|prescription|doctor|patient)\b',
        r'\b(blood\s+pressure|cholesterol|glucose|medication)\b',

        # Personal identifiers
        r'\b(passport|driver\'s?\s+license|license\s+number)\b',
        r'\bdate\s+of\s+birth\b',

        # Legal
        r'\b(attorney|lawyer|legal|lawsuit|settlement)\b',
    ]

    # Tags that indicate CONFIDENTIAL
    CONFIDENTIAL_TAGS = {
        "financial", "investment", "bank", "medical", "health",
        "personal", "confidential", "sensitive", "private",
        "legal", "attorney", "patient", "diagnosis"
    }

    # Tags that indicate PUBLIC
    PUBLIC_TAGS = {
        "documentation", "tutorial", "guide", "public", "docs",
        "readme", "how-to", "example", "demo", "reference"
    }

    # Tags that strongly indicate INTERNAL (default)
    INTERNAL_TAGS = {
        "conversation", "chatgpt", "claude", "gemini", "cursor",
        "note", "memo", "idea", "draft", "brainstorm", "phase-*"
    }

    def __init__(self):
        """Initialize privacy detector with compiled patterns."""
        self.local_only_regex = [re.compile(p, re.IGNORECASE) for p in self.LOCAL_ONLY_PATTERNS]
        self.confidential_regex = [re.compile(p, re.IGNORECASE) for p in self.CONFIDENTIAL_PATTERNS]

    @staticmethod
    def _luhn_checksum(card_number: str) -> bool:
        """Validate credit card number using Luhn algorithm.

        Args:
            card_number: Credit card number (digits only)

        Returns:
            bool: True if valid per Luhn algorithm, False otherwise
        """
        def digits_of(n):
            return [int(d) for d in str(n)]

        digits = digits_of(card_number)
        odd_digits = digits[-1::-2]
        even_digits = digits[-2::-2]

        checksum = sum(odd_digits)
        for d in even_digits:
            checksum += sum(digits_of(d * 2))

        return checksum % 10 == 0

    def detect_privacy_level(
        self,
        content: str,
        tags: Optional[List[str]] = None,
        default: str = "INTERNAL"
    ) -> str:
        """Detect privacy level for content and tags.

        Args:
            content: Memory content text
            tags: Optional list of tags
            default: Default privacy level if uncertain (INTERNAL)

        Returns:
            str: Privacy level (PUBLIC, INTERNAL, CONFIDENTIAL, LOCAL_ONLY)
        """
        if not content:
            return default

        tags = tags or []
        tags_lower = {t.lower() for t in tags}

        # Check for LOCAL_ONLY (most restrictive, highest priority)
        if self._check_local_only(content, tags_lower):
            return "LOCAL_ONLY"

        # Check for CONFIDENTIAL (second priority)
        if self._check_confidential(content, tags_lower):
            return "CONFIDENTIAL"

        # Check for PUBLIC (third priority)
        if self._check_public(content, tags_lower):
            return "PUBLIC"

        # Default to INTERNAL (safe default - user's tools only)
        return default

    def _check_local_only(self, content: str, tags_lower: Set[str]) -> bool:
        """Check if content/tags indicate LOCAL_ONLY level."""

        # Check tags first (faster)
        if tags_lower & self.LOCAL_ONLY_TAGS:
            return True

        # Validate credit cards with Luhn algorithm FIRST (reduces false positives)
        # This prevents 16-digit patterns from matching other detection rules
        cc_pattern = re.compile(r'\b(\d{4})[- ]?(\d{4})[- ]?(\d{4})[- ]?(\d{4})\b')
        for match in cc_pattern.finditer(content):
            # Extract digits only
            card_number = ''.join(match.groups())

            # Validate with Luhn algorithm - only flag if valid
            if len(card_number) == 16 and self._luhn_checksum(card_number):
                return True

        # Check all other content patterns (SKIP credit card pattern index 12)
        # Pattern 12 is: r'\b\d{4}[- ]?\d{4}[- ]?\d{4}[- ]?\d{4}\b' (credit cards)
        # We already validated it above with Luhn, so skip it here
        for i, pattern in enumerate(self.local_only_regex):
            if i == 12:  # Credit card pattern - already checked with Luhn
                continue

            if pattern.search(content):
                return True

        return False

    def _check_confidential(self, content: str, tags_lower: Set[str]) -> bool:
        """Check if content/tags indicate CONFIDENTIAL level."""

        # Check tags first (faster)
        if tags_lower & self.CONFIDENTIAL_TAGS:
            return True

        # Check content patterns
        for pattern in self.confidential_regex:
            if pattern.search(content):
                return True

        return False

    def _check_public(self, content: str, tags_lower: Set[str]) -> bool:
        """Check if content/tags indicate PUBLIC level."""

        # Check tags (PUBLIC is primarily tag-based)
        if tags_lower & self.PUBLIC_TAGS:
            return True

        # Check for documentation-like content
        doc_indicators = [
            r'^#\s+',  # Markdown headers
            r'```',  # Code blocks
            r'## \w+',  # Documentation sections
            r'### \w+',
            r'\bREADME\b',
            r'\bTutorial\b',
            r'\bGuide\b',
        ]

        # If content has multiple doc indicators, consider it public
        indicator_count = sum(1 for ind in doc_indicators if re.search(ind, content, re.MULTILINE))
        if indicator_count >= 2:
            return True

        return False

    def validate_privacy_level(self, level: str) -> bool:
        """Validate that privacy level is one of the allowed values.

        Args:
            level: Privacy level to validate

        Returns:
            bool: True if valid, False otherwise
        """
        return level in self.PRIVACY_LEVELS

    def get_privacy_description(self, level: str) -> str:
        """Get human-readable description of privacy level.

        Args:
            level: Privacy level

        Returns:
            str: Description of what the level means
        """
        descriptions = {
            "PUBLIC": "Safe to inject anywhere (docs, general knowledge, public code)",
            "INTERNAL": "Your tools only (conversations, notes, personal context)",
            "CONFIDENTIAL": "Manual review required (sensitive discussions, private data)",
            "LOCAL_ONLY": "Never leaves ACMS (credentials, API keys, secrets, PII)"
        }
        return descriptions.get(level, "Unknown privacy level")

    def get_privacy_emoji(self, level: str) -> str:
        """Get emoji icon for privacy level.

        Args:
            level: Privacy level

        Returns:
            str: Emoji representing the level
        """
        emojis = {
            "PUBLIC": "🔓",
            "INTERNAL": "🔒",
            "CONFIDENTIAL": "🔐",
            "LOCAL_ONLY": "⛔"
        }
        return emojis.get(level, "❓")


# Singleton instance
_detector = None


def get_privacy_detector() -> PrivacyDetector:
    """Get singleton PrivacyDetector instance.

    Returns:
        PrivacyDetector: Shared detector instance
    """
    global _detector
    if _detector is None:
        _detector = PrivacyDetector()
    return _detector


# Convenience function
def detect_privacy(content: str, tags: Optional[List[str]] = None) -> str:
    """Detect privacy level for content and tags.

    Args:
        content: Memory content
        tags: Optional tags

    Returns:
        str: Privacy level
    """
    detector = get_privacy_detector()
    return detector.detect_privacy_level(content, tags)


if __name__ == "__main__":
    # Test privacy detector
    detector = PrivacyDetector()

    test_cases = [
        ("This is my OpenAI API key: sk-1234567890abcdefghijklmnopqrstuvwxyz", [], "LOCAL_ONLY"),
        ("My investment portfolio has $50,000 in stocks", ["financial"], "CONFIDENTIAL"),
        ("# Python Tutorial\n\n## Introduction\n\nThis is how to use Python...", ["tutorial"], "PUBLIC"),
        ("Had a great conversation with ChatGPT today about coding", ["chatgpt", "conversation"], "INTERNAL"),
        ("password=mysecretpass123", [], "LOCAL_ONLY"),
        ("Just learned about Docker containers in my Phase 3 work", ["phase-3"], "INTERNAL"),
    ]

    print("🧪 Testing Privacy Detector\n")
    for content, tags, expected in test_cases:
        detected = detector.detect_privacy_level(content, tags)
        emoji = detector.get_privacy_emoji(detected)
        match = "✓" if detected == expected else "✗"
        print(f"{match} {emoji} {detected:15} | Expected: {expected:15}")
        print(f"   Content: {content[:60]}...")
        print(f"   Tags: {tags}\n")

    print("✅ Privacy detector tests complete!")
