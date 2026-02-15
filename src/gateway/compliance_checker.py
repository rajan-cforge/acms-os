"""Compliance checker for AI Gateway.

Blocks sensitive data (API keys, passwords, credit cards, SSN) and warns
about dangerous commands before sending to external AI APIs.

Security features:
- Sensitive data detection and blocking
- Dangerous command warnings
- Privacy level enforcement
- Cost protection (blocked queries cost $0)
"""

import re
import logging
from typing import List, Tuple
from src.gateway.models import ComplianceResult, ComplianceIssue

logger = logging.getLogger(__name__)


# Sensitive data patterns
SENSITIVE_PATTERNS = {
    "api_key": {
        "patterns": [
            r"sk-[a-zA-Z0-9\-]{20,}",  # OpenAI keys (includes sk-proj-, sk-...)
            r"ghp_[a-zA-Z0-9]{36}",  # GitHub Personal Access Token
            r"gho_[a-zA-Z0-9]{36}",  # GitHub OAuth token
            r"api[_-]?key[\"']?\s*[:=]\s*[\"']?[a-zA-Z0-9]{20,}",  # Generic API key
            r"bearer\s+[a-zA-Z0-9_\-\.]{20,}",  # Bearer tokens
        ],
        "severity": "high",
        "message": "API key detected in query. Remove sensitive credentials before proceeding."
    },

    "password": {
        "patterns": [
            r"password[\"']?\s*[:=]\s*[\"']?[^\s\"']{8,}",
            r"pwd[\"']?\s*[:=]\s*[\"']?[^\s\"']{8,}",
            r"passwd[\"']?\s*[:=]\s*[^\s\"']{8,}",
            r"my\s+password\s+is\s+[^\s]+",
        ],
        "severity": "high",
        "message": "Password detected in query. Remove sensitive credentials before proceeding."
    },

    "credit_card": {
        "patterns": [
            r"\b\d{4}[\s\-]?\d{4}[\s\-]?\d{4}[\s\-]?\d{4}\b",  # 16-digit card
            r"\b\d{13,19}\b",  # Variable length card numbers
        ],
        "severity": "high",
        "message": "Credit card number detected. Remove payment information before proceeding."
    },

    "ssn": {
        "patterns": [
            r"\b\d{3}[\s\-]?\d{2}[\s\-]?\d{4}\b",  # US SSN
        ],
        "severity": "high",
        "message": "Social Security Number detected. Remove PII before proceeding."
    },

    "email": {
        "patterns": [
            r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b",
        ],
        "severity": "medium",
        "message": "Email address detected. Consider if this should be shared."
    },

    "ip_address": {
        "patterns": [
            r"\b(?:\d{1,3}\.){3}\d{1,3}\b",  # IPv4
        ],
        "severity": "low",
        "message": "IP address detected. Verify if this should be shared."
    }
}


# Dangerous command patterns (warn but don't block)
DANGEROUS_COMMANDS = {
    "destructive_rm": {
        "patterns": [
            r"rm\s+-rf\s+/",
            r"rm\s+-rf\s+\*",
            r"rm\s+-rf\s+~",
        ],
        "severity": "high",
        "message": "DANGEROUS: This command will delete files recursively. Are you sure?"
    },

    "database_drop": {
        "patterns": [
            r"DROP\s+DATABASE",
            r"DROP\s+TABLE",
            r"TRUNCATE\s+TABLE",
            r"DELETE\s+FROM.*WHERE\s+1\s*=\s*1",
        ],
        "severity": "high",
        "message": "DANGEROUS: This SQL command will destroy data. Are you sure?"
    },

    "sudo_rm": {
        "patterns": [
            r"sudo\s+rm\s+-rf",
        ],
        "severity": "high",
        "message": "DANGEROUS: Running rm -rf with sudo can destroy your system. Are you sure?"
    },

    "format_disk": {
        "patterns": [
            r"mkfs\.",
            r"dd\s+if=.*of=/dev/",
        ],
        "severity": "high",
        "message": "DANGEROUS: Disk formatting/imaging command detected. Are you sure?"
    }
}


class ComplianceChecker:
    """Checks queries for sensitive data and dangerous commands."""

    def __init__(self):
        """Initialize compliance checker."""
        self.sensitive_patterns = SENSITIVE_PATTERNS
        self.dangerous_commands = DANGEROUS_COMMANDS
        logger.info("ComplianceChecker initialized")

    def check_compliance(self, query: str) -> ComplianceResult:
        """Check query for compliance issues.

        Args:
            query: User query to check

        Returns:
            ComplianceResult: Approved status and list of issues

        Workflow:
            1. Check for sensitive data (API keys, passwords, etc)
            2. If sensitive data found → BLOCKED (approved=False)
            3. Check for dangerous commands (rm -rf, DROP DATABASE)
            4. If dangerous commands → WARNING (approved=True but with issues)
            5. Otherwise → APPROVED (approved=True, issues=[])
        """
        issues = []

        # Check for sensitive data (blocking)
        sensitive_issues = self._check_sensitive_data(query)
        if sensitive_issues:
            issues.extend(sensitive_issues)
            # Block if any high-severity sensitive data found
            has_high_severity = any(
                issue.severity == "high" for issue in sensitive_issues
            )
            if has_high_severity:
                logger.warning(
                    f"Compliance BLOCKED: {len(sensitive_issues)} sensitive data issues found"
                )
                return ComplianceResult(
                    approved=False,
                    issues=issues
                )

        # Check for dangerous commands (warning only)
        dangerous_issues = self._check_dangerous_commands(query)
        if dangerous_issues:
            issues.extend(dangerous_issues)
            logger.warning(
                f"Compliance WARNING: {len(dangerous_issues)} dangerous commands found"
            )

        # Approved (with or without warnings)
        if issues:
            logger.info(f"Compliance approved with {len(issues)} warnings")
        else:
            logger.debug("Compliance approved (no issues)")

        return ComplianceResult(
            approved=True,
            issues=issues
        )

    def _check_sensitive_data(self, query: str) -> List[ComplianceIssue]:
        """Check for sensitive data patterns.

        Args:
            query: Query to check

        Returns:
            List of compliance issues found
        """
        issues = []

        for data_type, config in self.sensitive_patterns.items():
            for pattern in config["patterns"]:
                if re.search(pattern, query, re.IGNORECASE):
                    issues.append(ComplianceIssue(
                        severity=config["severity"],
                        type=f"sensitive_data:{data_type}",
                        message=config["message"]
                    ))
                    logger.warning(f"Sensitive data detected: {data_type}")
                    break  # Only report each type once

        return issues

    def _check_dangerous_commands(self, query: str) -> List[ComplianceIssue]:
        """Check for dangerous command patterns.

        Args:
            query: Query to check

        Returns:
            List of compliance issues found
        """
        issues = []

        for command_type, config in self.dangerous_commands.items():
            for pattern in config["patterns"]:
                if re.search(pattern, query, re.IGNORECASE):
                    issues.append(ComplianceIssue(
                        severity=config["severity"],
                        type=f"dangerous_command:{command_type}",
                        message=config["message"]
                    ))
                    logger.warning(f"Dangerous command detected: {command_type}")
                    break  # Only report each type once

        return issues

    def add_custom_pattern(
        self,
        category: str,
        pattern: str,
        severity: str,
        message: str,
        is_dangerous_command: bool = False
    ):
        """Add custom compliance pattern.

        Args:
            category: Pattern category (e.g., "internal_token")
            pattern: Regex pattern to match
            severity: "low", "medium", or "high"
            message: User-facing message when pattern matched
            is_dangerous_command: True for warnings, False for blocking

        Example:
            checker.add_custom_pattern(
                category="company_secret",
                pattern=r"COMPANY-SECRET-[A-Z0-9]+",
                severity="high",
                message="Company secret key detected",
                is_dangerous_command=False
            )
        """
        pattern_config = {
            "patterns": [pattern],
            "severity": severity,
            "message": message
        }

        if is_dangerous_command:
            self.dangerous_commands[category] = pattern_config
            logger.info(f"Added custom dangerous command pattern: {category}")
        else:
            self.sensitive_patterns[category] = pattern_config
            logger.info(f"Added custom sensitive data pattern: {category}")


# Global instance
_compliance_checker_instance = None


def get_compliance_checker() -> ComplianceChecker:
    """Get global compliance checker instance.

    Returns:
        ComplianceChecker: Global instance
    """
    global _compliance_checker_instance
    if _compliance_checker_instance is None:
        _compliance_checker_instance = ComplianceChecker()
    return _compliance_checker_instance
