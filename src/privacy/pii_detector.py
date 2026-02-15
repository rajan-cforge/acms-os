"""
PII Detection & Masking for GDPR Compliance (Week 6 Task 2)

Detects and masks Personally Identifiable Information (PII) in text:
- SSN (Social Security Numbers)
- Credit Cards (with Luhn validation)
- Emails
- Phone Numbers
- IP Addresses

Uses regex-based detection with format-preserving masking.
"""

import re
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
from datetime import datetime


class PIIType(Enum):
    """Types of PII that can be detected"""
    SSN = "SSN"
    CREDIT_CARD = "CREDIT_CARD"
    EMAIL = "EMAIL"
    PHONE = "PHONE"
    IP_ADDRESS = "IP_ADDRESS"


@dataclass
class PIIMatch:
    """Represents a detected PII instance"""
    pii_type: PIIType
    value: str
    start: int
    end: int
    masked_value: str
    confidence: float  # 0.0-1.0


class PIIDetector:
    """
    Detect and mask PII in text

    Uses regex patterns with validation for high confidence detection.
    """

    # Regex patterns for PII detection
    SSN_PATTERN = re.compile(r'\b\d{3}-\d{2}-\d{4}\b')

    # Credit card: 13-19 digits with optional spaces/dashes
    CREDIT_CARD_PATTERN = re.compile(r'\b(?:\d{4}[\s\-]?){3}\d{4,7}\b')

    # Email: standard email format
    EMAIL_PATTERN = re.compile(
        r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
    )

    # Phone: US formats (10 digits with optional country code)
    PHONE_PATTERN = re.compile(
        r'\b(?:\+?1[\s\-]?)?\(?\d{3}\)?[\s\-]?\d{3}[\s\-]?\d{4}\b'
    )

    # IP Address: IPv4 format
    IP_PATTERN = re.compile(
        r'\b(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}'
        r'(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\b'
    )

    def __init__(self):
        """Initialize PII detector"""
        pass

    def detect(self, text: str) -> List[PIIMatch]:
        """
        Detect all PII in text

        Args:
            text: Text to scan for PII

        Returns:
            List of PIIMatch objects

        Example:
            >>> detector = PIIDetector()
            >>> text = "My SSN is 123-45-6789"
            >>> matches = detector.detect(text)
            >>> matches[0].pii_type
            <PIIType.SSN: 'SSN'>
        """
        matches = []

        # Detect SSNs
        for match in self.SSN_PATTERN.finditer(text):
            matches.append(PIIMatch(
                pii_type=PIIType.SSN,
                value=match.group(),
                start=match.start(),
                end=match.end(),
                masked_value=self._mask_ssn(match.group()),
                confidence=1.0  # SSN pattern is highly specific
            ))

        # Detect Credit Cards
        for match in self.CREDIT_CARD_PATTERN.finditer(text):
            card_number = re.sub(r'[\s\-]', '', match.group())
            if self._validate_credit_card(card_number):
                matches.append(PIIMatch(
                    pii_type=PIIType.CREDIT_CARD,
                    value=match.group(),
                    start=match.start(),
                    end=match.end(),
                    masked_value=self._mask_credit_card(match.group()),
                    confidence=0.95  # Luhn validated
                ))

        # Detect Emails
        for match in self.EMAIL_PATTERN.finditer(text):
            matches.append(PIIMatch(
                pii_type=PIIType.EMAIL,
                value=match.group(),
                start=match.start(),
                end=match.end(),
                masked_value=self._mask_email(match.group()),
                confidence=0.9  # Email pattern is fairly specific
            ))

        # Detect Phone Numbers
        for match in self.PHONE_PATTERN.finditer(text):
            matches.append(PIIMatch(
                pii_type=PIIType.PHONE,
                value=match.group(),
                start=match.start(),
                end=match.end(),
                masked_value=self._mask_phone(match.group()),
                confidence=0.85  # Phone patterns have some false positives
            ))

        # Detect IP Addresses
        for match in self.IP_PATTERN.finditer(text):
            matches.append(PIIMatch(
                pii_type=PIIType.IP_ADDRESS,
                value=match.group(),
                start=match.start(),
                end=match.end(),
                masked_value=self._mask_ip(match.group()),
                confidence=0.9
            ))

        # Sort by start position
        matches.sort(key=lambda m: m.start)

        return matches

    def mask_text(self, text: str, matches: Optional[List[PIIMatch]] = None) -> str:
        """
        Mask PII in text

        Args:
            text: Original text
            matches: Pre-detected matches (if None, will detect)

        Returns:
            Text with PII masked

        Example:
            >>> detector = PIIDetector()
            >>> text = "Email: john@example.com"
            >>> detector.mask_text(text)
            'Email: j***@example.com'
        """
        if matches is None:
            matches = self.detect(text)

        if not matches:
            return text

        # Replace from end to start to preserve offsets
        result = text
        for match in reversed(matches):
            result = (
                result[:match.start] +
                match.masked_value +
                result[match.end:]
            )

        return result

    def _mask_ssn(self, ssn: str) -> str:
        """Mask SSN: 123-45-6789 → ***-**-6789"""
        return "***-**-" + ssn[-4:]

    def _mask_credit_card(self, card: str) -> str:
        """Mask credit card: 4532-1234-5678-9010 → ****-****-****-9010"""
        # Preserve format (spaces/dashes)
        digits = re.sub(r'[\s\-]', '', card)
        masked_digits = '*' * (len(digits) - 4) + digits[-4:]

        # Reconstruct with original separators
        result = []
        digit_idx = 0
        for char in card:
            if char.isdigit():
                result.append(masked_digits[digit_idx])
                digit_idx += 1
            else:
                result.append(char)

        return ''.join(result)

    def _mask_email(self, email: str) -> str:
        """Mask email: john.doe@example.com → j***@example.com"""
        local, domain = email.split('@')
        if len(local) <= 1:
            masked_local = '*'
        else:
            masked_local = local[0] + '***'
        return f"{masked_local}@{domain}"

    def _mask_phone(self, phone: str) -> str:
        """Mask phone: (555) 123-4567 → (***) ***-4567"""
        # Keep last 4 digits, mask rest
        digits = re.sub(r'\D', '', phone)

        if len(digits) <= 4:
            return '*' * len(phone)

        # Replace all but last 4 digits with *
        result = []
        digit_idx = 0
        for char in phone:
            if char.isdigit():
                if digit_idx < len(digits) - 4:
                    result.append('*')
                else:
                    result.append(char)
                digit_idx += 1
            else:
                result.append(char)

        return ''.join(result)

    def _mask_ip(self, ip: str) -> str:
        """Mask IP: 192.168.1.1 → ***.***.***.1"""
        parts = ip.split('.')
        return '.'.join(['***'] * (len(parts) - 1) + [parts[-1]])

    def _validate_credit_card(self, card_number: str) -> bool:
        """
        Validate credit card using Luhn algorithm

        Args:
            card_number: Card number (digits only)

        Returns:
            True if valid, False otherwise
        """
        if not card_number.isdigit():
            return False

        if len(card_number) < 13 or len(card_number) > 19:
            return False

        # Luhn algorithm
        total = 0
        reverse_digits = card_number[::-1]

        for i, digit in enumerate(reverse_digits):
            n = int(digit)

            if i % 2 == 1:  # Every second digit from right
                n *= 2
                if n > 9:
                    n -= 9

            total += n

        return total % 10 == 0


class PIIScanner:
    """
    Scan and log PII across database tables

    Scans memory_items and query_logs tables for PII and logs findings.
    """

    def __init__(self, db_pool):
        """
        Initialize PII scanner

        Args:
            db_pool: AsyncPG connection pool
        """
        self.db_pool = db_pool
        self.detector = PIIDetector()

    async def scan_memory_items(
        self,
        limit: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Scan memory_items table for PII

        Args:
            limit: Max number of items to scan (None = all)

        Returns:
            Dict with scan results and statistics
        """
        async with self.db_pool.acquire() as conn:
            # Get items to scan (use actual column names: memory_id, not id)
            query = "SELECT memory_id, content, created_at FROM memory_items"
            if limit:
                query += f" ORDER BY created_at DESC LIMIT {limit}"

            items = await conn.fetch(query)

            total_scanned = 0
            items_with_pii = 0
            pii_by_type = {pii_type: 0 for pii_type in PIIType}

            for item in items:
                total_scanned += 1

                matches = self.detector.detect(item['content'])

                if matches:
                    items_with_pii += 1

                    # Log each match
                    for match in matches:
                        await self._log_pii_detection(
                            conn,
                            table_name='memory_items',
                            record_id=str(item['memory_id']),  # Use memory_id, not id
                            pii_type=match.pii_type.value,
                            field_name='content',
                            confidence=match.confidence,
                            detected_at=datetime.now()
                        )

                        pii_by_type[match.pii_type] += 1

            return {
                'table': 'memory_items',
                'total_scanned': total_scanned,
                'items_with_pii': items_with_pii,
                'pii_by_type': {k.value: v for k, v in pii_by_type.items()},
                'percentage': (items_with_pii / total_scanned * 100) if total_scanned > 0 else 0
            }

    async def scan_query_logs(
        self,
        limit: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Scan query_logs table for PII

        Args:
            limit: Max number of queries to scan (None = all)

        Returns:
            Dict with scan results and statistics
        """
        async with self.db_pool.acquire() as conn:
            # Get queries to scan (use actual column names: log_id, query, timestamp)
            query = "SELECT log_id, query, timestamp FROM query_logs"
            if limit:
                query += f" ORDER BY timestamp DESC LIMIT {limit}"

            queries = await conn.fetch(query)

            total_scanned = 0
            queries_with_pii = 0
            pii_by_type = {pii_type: 0 for pii_type in PIIType}

            for query_record in queries:
                total_scanned += 1

                matches = self.detector.detect(query_record['query'])  # Use 'query', not 'query_text'

                if matches:
                    queries_with_pii += 1

                    # Log each match
                    for match in matches:
                        await self._log_pii_detection(
                            conn,
                            table_name='query_logs',
                            record_id=str(query_record['log_id']),  # Use log_id, not id
                            pii_type=match.pii_type.value,
                            field_name='query',  # Use 'query', not 'query_text'
                            confidence=match.confidence,
                            detected_at=datetime.now()
                        )

                        pii_by_type[match.pii_type] += 1

            return {
                'table': 'query_logs',
                'total_scanned': total_scanned,
                'queries_with_pii': queries_with_pii,
                'pii_by_type': {k.value: v for k, v in pii_by_type.items()},
                'percentage': (queries_with_pii / total_scanned * 100) if total_scanned > 0 else 0
            }

    async def _log_pii_detection(
        self,
        conn,
        table_name: str,
        record_id: str,
        pii_type: str,
        field_name: str,
        confidence: float,
        detected_at: datetime
    ):
        """Log PII detection to audit table"""
        await conn.execute(
            """
            INSERT INTO pii_detection_log (
                table_name, record_id, pii_type, field_name, confidence, detected_at
            ) VALUES ($1, $2, $3, $4, $5, $6)
            """,
            table_name, record_id, pii_type, field_name, confidence, detected_at
        )


# Convenience functions

def detect_pii(text: str) -> List[PIIMatch]:
    """
    Convenience function to detect PII

    Args:
        text: Text to scan

    Returns:
        List of PIIMatch objects

    Example:
        >>> matches = detect_pii("Email me at john@example.com")
        >>> matches[0].pii_type
        <PIIType.EMAIL: 'EMAIL'>
    """
    detector = PIIDetector()
    return detector.detect(text)


def mask_pii(text: str) -> str:
    """
    Convenience function to mask PII

    Args:
        text: Text to mask

    Returns:
        Masked text

    Example:
        >>> mask_pii("SSN: 123-45-6789")
        'SSN: ***-**-6789'
    """
    detector = PIIDetector()
    return detector.mask_text(text)
