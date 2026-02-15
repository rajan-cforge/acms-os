"""
Privacy Enforcement

Ensures confidential data never leaves the local system.
"""

import logging
from typing import Optional, Set

from .models import DataClassification

logger = logging.getLogger(__name__)


class PrivacyViolationError(Exception):
    """Raised when attempting to send confidential data externally"""

    def __init__(
        self,
        data_classification: DataClassification,
        destination: str,
        message: Optional[str] = None
    ):
        self.data_classification = data_classification
        self.destination = destination
        self.message = message or (
            f"Cannot send {data_classification.value} data to {destination}. "
            "Confidential and local-only data must remain on local system."
        )
        super().__init__(self.message)


class PrivacyEnforcer:
    """
    Enforces privacy policies on data egress.

    Ensures that confidential and local-only data never leaves
    the local system to external APIs.
    """

    # Destinations that are considered "local" and safe for all data
    LOCAL_DESTINATIONS: Set[str] = {
        "local",
        "postgres",
        "postgresql",
        "weaviate",
        "redis",
        "file",
        "filesystem",
        "memory",
        "sqlite",
    }

    # Destinations that are considered "external" and restricted
    EXTERNAL_DESTINATIONS: Set[str] = {
        "claude_api",
        "anthropic_api",
        "openai_api",
        "gemini_api",
        "google_api",
        "plaid_api",
        "gmail_api",
        "calendar_api",
        "browser_chatgpt",
        "browser_claude",
        "browser_gemini",
        "webhook",
        "email",
        "sms",
        "notification",
    }

    # Data classifications that CANNOT go to external destinations
    RESTRICTED_CLASSIFICATIONS: Set[DataClassification] = {
        DataClassification.CONFIDENTIAL,
        DataClassification.LOCAL_ONLY,
    }

    def __init__(self):
        logger.info("[PrivacyEnforcer] Initialized")

    def is_local_destination(self, destination: str) -> bool:
        """Check if destination is considered local/safe"""
        destination_lower = destination.lower()
        return (
            destination_lower in self.LOCAL_DESTINATIONS or
            destination_lower.startswith("local") or
            destination_lower.startswith("file://")
        )

    def is_external_destination(self, destination: str) -> bool:
        """Check if destination is external"""
        destination_lower = destination.lower()
        return (
            destination_lower in self.EXTERNAL_DESTINATIONS or
            destination_lower.endswith("_api") or
            destination_lower.startswith("http") or
            destination_lower.startswith("browser_")
        )

    def validate_egress(
        self,
        data_classification: Optional[DataClassification],
        destination: str,
        raise_on_violation: bool = True
    ) -> bool:
        """
        Validate that data egress is allowed.

        Args:
            data_classification: Sensitivity level of data
            destination: Where data is going
            raise_on_violation: If True, raises PrivacyViolationError

        Returns:
            True if allowed, False if blocked

        Raises:
            PrivacyViolationError: If restricted data is going to external destination
        """
        # No classification = assume public, allow
        if data_classification is None:
            return True

        # Local destinations are always OK
        if self.is_local_destination(destination):
            return True

        # Check if classification is restricted
        if data_classification in self.RESTRICTED_CLASSIFICATIONS:
            if self.is_external_destination(destination):
                logger.warning(
                    f"[PrivacyEnforcer] BLOCKED: {data_classification.value} -> {destination}"
                )
                if raise_on_violation:
                    raise PrivacyViolationError(data_classification, destination)
                return False

        # Public and internal data can go to external destinations
        return True

    def classify_destination(self, destination: str) -> str:
        """Classify a destination as local, external, or unknown"""
        if self.is_local_destination(destination):
            return "local"
        if self.is_external_destination(destination):
            return "external"
        return "unknown"

    def get_allowed_destinations(
        self,
        data_classification: DataClassification
    ) -> Set[str]:
        """Get set of allowed destinations for a classification"""
        if data_classification in self.RESTRICTED_CLASSIFICATIONS:
            return self.LOCAL_DESTINATIONS.copy()
        else:
            return self.LOCAL_DESTINATIONS | self.EXTERNAL_DESTINATIONS

    def sanitize_for_external(
        self,
        data: dict,
        fields_to_redact: Set[str] = None
    ) -> dict:
        """
        Sanitize data before sending to external destination.

        Redacts specified fields and any fields containing 'password',
        'secret', 'token', 'key', 'credential'.
        """
        if fields_to_redact is None:
            fields_to_redact = set()

        sensitive_patterns = {
            'password', 'secret', 'token', 'key', 'credential',
            'api_key', 'apikey', 'auth', 'ssn', 'social_security',
            'credit_card', 'card_number', 'cvv', 'bank_account'
        }

        sanitized = {}
        for key, value in data.items():
            key_lower = key.lower()

            # Check if field should be redacted
            should_redact = (
                key in fields_to_redact or
                any(pattern in key_lower for pattern in sensitive_patterns)
            )

            if should_redact:
                sanitized[key] = "[REDACTED]"
            elif isinstance(value, dict):
                sanitized[key] = self.sanitize_for_external(value, fields_to_redact)
            else:
                sanitized[key] = value

        return sanitized
