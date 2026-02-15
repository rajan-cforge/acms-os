"""PreflightGate - Security checkpoint BEFORE any external API calls.

CRITICAL SECURITY COMPONENT - This gate runs BEFORE:
- Web search (Tavily) - line 308 in orchestrator
- Query augmentation (external LLM calls)
- Context retrieval from external services

Purpose:
1. Detect PII (SSN, credit cards, emails, phones) - BLOCK
2. Detect secrets (API keys, passwords, tokens) - BLOCK
3. Detect prompt injection attempts - BLOCK or SANITIZE
4. Decide if web search is safe for this query

Security Model:
- HIGH severity (secrets, SSN, credit cards) → BLOCK before any external call
- MEDIUM severity (emails, phones) → MASK and continue
- Injection patterns → SANITIZE and continue with warning

This gate MUST be called before SearchDetector.needs_search() or any
external API call to prevent data exfiltration.
"""

import re
import logging
from typing import Optional, List, Dict, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime

from src.gateway.tracing import get_trace_id, trace_info, trace_warning, trace_error

logger = logging.getLogger(__name__)


class PreflightDecision(str, Enum):
    """Preflight gate decisions."""
    ALLOW = "allow"              # Query is safe, proceed normally
    ALLOW_MASKED = "allow_masked"  # Query sanitized, proceed with masked version
    BLOCK = "block"              # Query blocked, return error to user
    RATE_LIMITED = "rate_limited"  # Too many blocked requests, reject


class DetectionType(str, Enum):
    """Types of detected issues."""
    API_KEY = "api_key"
    PASSWORD = "password"
    CREDIT_CARD = "credit_card"
    SSN = "ssn"
    EMAIL = "email"
    PHONE = "phone"
    IP_ADDRESS = "ip_address"
    PROMPT_INJECTION = "prompt_injection"
    SQL_INJECTION = "sql_injection"
    COMMAND_INJECTION = "command_injection"


@dataclass
class Detection:
    """A single detection result."""
    detection_type: DetectionType
    severity: str  # "high", "medium", "low"
    value: str     # The detected value (redacted)
    message: str   # User-facing message
    start: int     # Position in query
    end: int       # End position


@dataclass
class PreflightResult:
    """Result of preflight security check."""
    decision: PreflightDecision
    original_query: str
    sanitized_query: str
    detections: List[Detection] = field(default_factory=list)
    allow_web_search: bool = True
    blocked_reason: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.utcnow)

    @property
    def allowed(self) -> bool:
        """Check if query is allowed to proceed (matches test spec)."""
        return self.decision in (PreflightDecision.ALLOW, PreflightDecision.ALLOW_MASKED)

    @property
    def is_allowed(self) -> bool:
        """Alias for allowed property."""
        return self.allowed

    @property
    def is_blocked(self) -> bool:
        """Check if query is blocked."""
        return self.decision == PreflightDecision.BLOCK

    @property
    def reason(self) -> Optional[str]:
        """Get the reason for blocking (alias for blocked_reason)."""
        return self.blocked_reason

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API response/logging."""
        return {
            "decision": self.decision.value,
            "allowed": self.allowed,
            "sanitized_query": self.sanitized_query[:100] + "..." if len(self.sanitized_query) > 100 else self.sanitized_query,
            "detection_count": len(self.detections),
            "detection_types": [d.detection_type.value for d in self.detections],
            "allow_web_search": self.allow_web_search,
            "reason": self.reason
        }


# =============================================================================
# SENSITIVE DATA PATTERNS (High Severity - BLOCK)
# =============================================================================

SENSITIVE_PATTERNS = {
    DetectionType.API_KEY: {
        "patterns": [
            r"sk-[a-zA-Z0-9\-]{20,}",           # OpenAI keys (sk-proj-, sk-...)
            r"sk-proj-[a-zA-Z0-9\-]{20,}",      # OpenAI project keys
            r"ghp_[a-zA-Z0-9]{36}",             # GitHub Personal Access Token
            r"gho_[a-zA-Z0-9]{36}",             # GitHub OAuth token
            r"ghs_[a-zA-Z0-9]{36}",             # GitHub server-to-server token
            r"github_pat_[a-zA-Z0-9_]{22,}",    # GitHub fine-grained PAT
            r"glpat-[a-zA-Z0-9\-]{20}",         # GitLab PAT
            r"xox[baprs]-[a-zA-Z0-9\-]{10,}",   # Slack tokens
            r"AKIA[0-9A-Z]{16}",                # AWS Access Key ID
            r"AIza[0-9A-Za-z\-_]{35}",          # Google API Key
            r"ya29\.[0-9A-Za-z\-_]+",           # Google OAuth token
            r"anthropic[_-]?api[_-]?key.*?[a-zA-Z0-9]{20,}",  # Anthropic keys
            r"tavily[_-]?api[_-]?key.*?[a-zA-Z0-9]{20,}",     # Tavily keys
            r"api[_-]?key[\"']?\s*[:=]\s*[\"']?[a-zA-Z0-9]{20,}",  # Generic API key
            r"bearer\s+[a-zA-Z0-9_\-\.]{20,}",  # Bearer tokens
            r"token[\"']?\s*[:=]\s*[\"']?[a-zA-Z0-9_\-\.]{20,}",  # Generic tokens
        ],
        "severity": "high",
        "message": "API key or token detected. Remove sensitive credentials before proceeding."
    },

    DetectionType.PASSWORD: {
        "patterns": [
            r"password[\"']?\s*[:=]\s*[\"']?[^\s\"']{8,}",
            r"pwd[\"']?\s*[:=]\s*[\"']?[^\s\"']{8,}",
            r"passwd[\"']?\s*[:=]\s*[^\s\"']{8,}",
            r"my\s+password\s+is\s+[^\s]+",
            r"secret[\"']?\s*[:=]\s*[\"']?[^\s\"']{8,}",
        ],
        "severity": "high",
        "message": "Password detected. Remove sensitive credentials before proceeding."
    },

    DetectionType.CREDIT_CARD: {
        "patterns": [
            r"\b(?:4[0-9]{3}|5[1-5][0-9]{2}|6(?:011|5[0-9]{2})|3[47][0-9]{2}|3(?:0[0-5]|[68][0-9])[0-9])[\s\-]?[0-9]{4}[\s\-]?[0-9]{4}[\s\-]?[0-9]{4}\b",
        ],
        "severity": "high",
        "message": "Credit card number detected. Remove payment information before proceeding."
    },

    DetectionType.SSN: {
        "patterns": [
            r"\b\d{3}[\s\-]?\d{2}[\s\-]?\d{4}\b",
        ],
        "severity": "high",
        "message": "Social Security Number detected. Remove PII before proceeding."
    },
}

# =============================================================================
# PII PATTERNS (High Severity - BLOCK to prevent data exfiltration)
# Per enterprise security requirements, PII should BLOCK, not just mask
# =============================================================================

PII_PATTERNS = {
    DetectionType.EMAIL: {
        "patterns": [
            r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b",
        ],
        "severity": "high",  # BLOCK - emails are PII
        "message": "PII detected: Email address. Remove personal information before proceeding."
    },

    DetectionType.PHONE: {
        "patterns": [
            r"\b(?:\+?1[\s\-]?)?\(?\d{3}\)?[\s\-]?\d{3}[\s\-]?\d{4}\b",
        ],
        "severity": "high",  # BLOCK - phone numbers are PII
        "message": "PII detected: Phone number. Remove personal information before proceeding."
    },

    DetectionType.IP_ADDRESS: {
        "patterns": [
            r"\b(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\b",
        ],
        "severity": "low",  # WARN only - IPs are less sensitive
        "message": "IP address detected."
    },
}

# =============================================================================
# INJECTION PATTERNS (Block or Sanitize)
# =============================================================================

INJECTION_PATTERNS = {
    DetectionType.PROMPT_INJECTION: {
        "patterns": [
            r"ignore\s+(?:all\s+)?previous\s+instructions",
            r"disregard\s+(?:all\s+)?(?:previous|prior)\s+instructions",
            r"forget\s+(?:all\s+)?(?:previous|prior|your)\s+instructions",
            r"new\s+instructions?\s*:",
            r"system\s+prompt",
            r"you\s+are\s+(?:now\s+)?(?:ChatGPT|GPT|Claude|an?\s+AI)",
            r"\[\s*SYSTEM\s*\]",
            r"\[\s*INST\s*\]",
            r"<\|im_start\|>",
            r"<\|im_end\|>",
            r"<\|endoftext\|>",
            r"Human:\s*Actually",
            r"Assistant:\s*I",
            r"repeat\s+(?:everything|all|the\s+text)\s+above",
            r"what\s+(?:is|are)\s+your\s+(?:instructions|rules|prompt)",
            r"reveal\s+(?:your\s+)?(?:system\s+)?prompt",
            r"print\s+(?:your\s+)?(?:system\s+)?prompt",
            r"output\s+(?:your\s+)?(?:system\s+)?prompt",
        ],
        "severity": "high",
        "message": "Potential prompt injection detected. Query sanitized for safety.",
        "action": "sanitize"  # Don't block, just neutralize
    },

    DetectionType.SQL_INJECTION: {
        "patterns": [
            r";\s*(?:DROP|DELETE|UPDATE|INSERT|TRUNCATE|ALTER)\s+",
            r"'\s*OR\s+'?\d+\s*=\s*'?\d+",
            r"'\s*OR\s+'[^']+'\s*=\s*'[^']+'",
            r"UNION\s+(?:ALL\s+)?SELECT",
            r"--\s*$",
        ],
        "severity": "high",
        "message": "Potential SQL injection detected.",
        "action": "block"
    },

    DetectionType.COMMAND_INJECTION: {
        "patterns": [
            r";\s*(?:rm|del|format|mkfs|dd)\s+",
            r"\|\s*(?:rm|del|format|cat\s+/etc)\s+",
            r"`[^`]*(?:rm|del|wget|curl)[^`]*`",
            r"\$\([^)]*(?:rm|del|wget|curl)[^)]*\)",
        ],
        "severity": "high",
        "message": "Potential command injection detected.",
        "action": "block"
    },
}


class PreflightGate:
    """Security gate that runs BEFORE any external API calls.

    This is the first line of defense. It MUST be called before:
    - Web search (Tavily)
    - Query augmentation (external LLM)
    - Any external service that sees the user's query

    Usage:
        gate = PreflightGate()
        result = gate.check(query, user_id)

        if result.is_blocked:
            return error_response(result.blocked_reason)

        # Use sanitized query for downstream
        safe_query = result.sanitized_query
    """

    def __init__(self):
        """Initialize the preflight gate."""
        self.sensitive_patterns = SENSITIVE_PATTERNS
        self.pii_patterns = PII_PATTERNS
        self.injection_patterns = INJECTION_PATTERNS

        # Compile patterns for efficiency
        self._compiled_sensitive = self._compile_patterns(SENSITIVE_PATTERNS)
        self._compiled_pii = self._compile_patterns(PII_PATTERNS)
        self._compiled_injection = self._compile_patterns(INJECTION_PATTERNS)

        logger.info("PreflightGate initialized with security patterns")

    def _compile_patterns(self, pattern_dict: Dict) -> Dict:
        """Pre-compile regex patterns for efficiency."""
        compiled = {}
        for detection_type, config in pattern_dict.items():
            compiled[detection_type] = {
                "compiled": [re.compile(p, re.IGNORECASE) for p in config["patterns"]],
                "severity": config["severity"],
                "message": config["message"],
                **{k: v for k, v in config.items() if k not in ["patterns", "severity", "message"]}
            }
        return compiled

    async def run(self, query: str, user_ctx: Dict) -> PreflightResult:
        """Async run method matching the canonical interface spec.

        Args:
            query: User's raw query
            user_ctx: Context dict with user_id, role, tenant_id

        Returns:
            PreflightResult with decision and sanitized query
        """
        user_id = user_ctx.get("user_id", "unknown")
        return self.check(query, user_id, user_ctx)

    def check(self, query: str, user_id: str, user_ctx: Optional[Dict] = None) -> PreflightResult:
        """Run preflight security check on query (sync version).

        Args:
            query: User's raw query
            user_id: User identifier for audit logging
            user_ctx: Optional additional context (role, tenant_id, etc.)

        Returns:
            PreflightResult with decision and sanitized query

        Security checks in order:
        1. Sensitive data (API keys, passwords, SSN, credit cards) → BLOCK
        2. PII (emails, phones) → BLOCK (enterprise security requirement)
        3. Injection patterns → SANITIZE or BLOCK

        If ANY high-severity issue is found, the query is BLOCKED
        before it can leak to external services.
        """
        trace_id = get_trace_id()
        detections: List[Detection] = []
        sanitized_query = query
        allow_web_search = True
        blocked_reason = None

        trace_info(f"PreflightGate checking query", user_id=user_id, query_length=len(query))

        # =================================================================
        # Step 1: Check for SENSITIVE DATA (high severity → BLOCK)
        # =================================================================
        sensitive_detections = self._check_sensitive_data(query)
        if sensitive_detections:
            detections.extend(sensitive_detections)
            high_severity = [d for d in sensitive_detections if d.severity == "high"]

            if high_severity:
                # BLOCK - Do not proceed, do not pass to external services
                blocked_reason = high_severity[0].message
                trace_warning(
                    f"PreflightGate BLOCKED",
                    reason="sensitive_data",
                    detection_types=[d.detection_type.value for d in high_severity]
                )

                return PreflightResult(
                    decision=PreflightDecision.BLOCK,
                    original_query=query,
                    sanitized_query="",  # Don't pass blocked query anywhere
                    detections=detections,
                    allow_web_search=False,
                    blocked_reason=blocked_reason
                )

        # =================================================================
        # Step 2: Check for PII (high severity → BLOCK per enterprise policy)
        # =================================================================
        pii_detections = self._check_pii(query)
        if pii_detections:
            detections.extend(pii_detections)
            high_severity_pii = [d for d in pii_detections if d.severity == "high"]

            if high_severity_pii:
                # BLOCK - PII must not leak to external services
                blocked_reason = high_severity_pii[0].message
                trace_warning(
                    f"PreflightGate BLOCKED",
                    reason="pii",
                    detection_types=[d.detection_type.value for d in high_severity_pii]
                )

                return PreflightResult(
                    decision=PreflightDecision.BLOCK,
                    original_query=query,
                    sanitized_query="",
                    detections=detections,
                    allow_web_search=False,
                    blocked_reason=blocked_reason
                )

        # =================================================================
        # Step 3: Check for INJECTION patterns
        # =================================================================
        injection_detections, sanitized_query, should_block = self._check_injection(sanitized_query)
        if injection_detections:
            detections.extend(injection_detections)

            if should_block:
                blocked_reason = injection_detections[0].message
                trace_warning(
                    f"PreflightGate BLOCKED",
                    reason="injection",
                    detection_types=[d.detection_type.value for d in injection_detections]
                )

                return PreflightResult(
                    decision=PreflightDecision.BLOCK,
                    original_query=query,
                    sanitized_query="",
                    detections=detections,
                    allow_web_search=False,
                    blocked_reason=blocked_reason
                )
            else:
                # Sanitized but not blocked (prompt injection neutralized)
                trace_info(
                    f"PreflightGate sanitized injection",
                    detection_types=[d.detection_type.value for d in injection_detections]
                )
                # Disable web search for potential injection attempts
                allow_web_search = False

        # =================================================================
        # Determine final decision
        # =================================================================
        if sanitized_query != query:
            decision = PreflightDecision.ALLOW_MASKED
        else:
            decision = PreflightDecision.ALLOW

        trace_info(
            f"PreflightGate decision",
            decision=decision.value,
            detections=len(detections),
            allow_web_search=allow_web_search
        )

        return PreflightResult(
            decision=decision,
            original_query=query,
            sanitized_query=sanitized_query,
            detections=detections,
            allow_web_search=allow_web_search,
            blocked_reason=blocked_reason
        )

    def _check_sensitive_data(self, query: str) -> List[Detection]:
        """Check for sensitive data patterns that should BLOCK the query."""
        detections = []

        for detection_type, config in self._compiled_sensitive.items():
            for pattern in config["compiled"]:
                for match in pattern.finditer(query):
                    # Redact the actual value in the detection
                    redacted_value = match.group()[:4] + "***" + match.group()[-2:] if len(match.group()) > 6 else "***"

                    detections.append(Detection(
                        detection_type=detection_type,
                        severity=config["severity"],
                        value=redacted_value,
                        message=config["message"],
                        start=match.start(),
                        end=match.end()
                    ))
                    # Only report first match of each type
                    break

        return detections

    def _check_pii(self, query: str) -> List[Detection]:
        """Check for PII patterns that should BLOCK the query."""
        detections = []

        for detection_type, config in self._compiled_pii.items():
            for pattern in config["compiled"]:
                for match in pattern.finditer(query):
                    redacted_value = match.group()[:2] + "***"

                    detections.append(Detection(
                        detection_type=detection_type,
                        severity=config["severity"],
                        value=redacted_value,
                        message=config["message"],
                        start=match.start(),
                        end=match.end()
                    ))
                    # Only report first match of each type
                    break

        return detections

    def _check_injection(self, query: str) -> Tuple[List[Detection], str, bool]:
        """Check for injection patterns and sanitize or block."""
        detections = []
        sanitized_query = query
        should_block = False

        for detection_type, config in self._compiled_injection.items():
            for pattern in config["compiled"]:
                for match in pattern.finditer(query):
                    detections.append(Detection(
                        detection_type=detection_type,
                        severity=config["severity"],
                        value="[REDACTED]",
                        message=config["message"],
                        start=match.start(),
                        end=match.end()
                    ))

                    action = config.get("action", "sanitize")
                    if action == "block":
                        should_block = True
                    elif action == "sanitize":
                        # Neutralize the injection by replacing with safe text
                        sanitized_query = sanitized_query[:match.start()] + "[filtered]" + sanitized_query[match.end():]

                    break  # One match per type is enough

        return detections, sanitized_query, should_block


# =============================================================================
# Global instance and factory
# =============================================================================

_preflight_gate_instance: Optional[PreflightGate] = None


def get_preflight_gate() -> PreflightGate:
    """Get global PreflightGate instance.

    Returns:
        PreflightGate: Singleton instance
    """
    global _preflight_gate_instance
    if _preflight_gate_instance is None:
        _preflight_gate_instance = PreflightGate()
    return _preflight_gate_instance
