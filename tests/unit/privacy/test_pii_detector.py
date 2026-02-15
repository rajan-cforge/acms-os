"""
Unit tests for PII Detection & Masking (Week 6 Task 2)

Tests regex-based PII detection and format-preserving masking.
"""

import pytest
from src.privacy.pii_detector import (
    PIIDetector,
    PIIType,
    PIIMatch,
    detect_pii,
    mask_pii
)


class TestSSNDetection:
    """Test SSN detection and masking"""

    def test_detect_ssn(self):
        """Should detect SSN in standard format"""
        detector = PIIDetector()
        text = "My SSN is 123-45-6789"

        matches = detector.detect(text)

        assert len(matches) == 1
        assert matches[0].pii_type == PIIType.SSN
        assert matches[0].value == "123-45-6789"
        assert matches[0].confidence == 1.0

    def test_mask_ssn(self):
        """Should mask SSN keeping last 4 digits"""
        detector = PIIDetector()
        text = "SSN: 123-45-6789"

        masked = detector.mask_text(text)

        assert masked == "SSN: ***-**-6789"
        assert "123" not in masked
        assert "6789" in masked

    def test_multiple_ssns(self):
        """Should detect multiple SSNs"""
        detector = PIIDetector()
        text = "SSN1: 123-45-6789, SSN2: 987-65-4321"

        matches = detector.detect(text)

        assert len(matches) == 2
        assert all(m.pii_type == PIIType.SSN for m in matches)


class TestCreditCardDetection:
    """Test credit card detection with Luhn validation"""

    def test_detect_valid_credit_card(self):
        """Should detect valid credit card (Luhn validated)"""
        detector = PIIDetector()
        # Valid test card number: Visa test card 4111111111111111
        text = "Card: 4111-1111-1111-1111"

        matches = detector.detect(text)

        assert len(matches) == 1
        assert matches[0].pii_type == PIIType.CREDIT_CARD
        assert matches[0].confidence == 0.95

    def test_mask_credit_card(self):
        """Should mask credit card keeping last 4 digits"""
        detector = PIIDetector()
        text = "Card: 4111-1111-1111-1111"

        masked = detector.mask_text(text)

        assert masked == "Card: ****-****-****-1111"
        assert "4111-1111-1111-1111" not in masked
        assert "1111" in masked

    def test_reject_invalid_luhn(self):
        """Should reject numbers that fail Luhn validation"""
        detector = PIIDetector()
        # Invalid card (fails Luhn check)
        text = "Card: 1234-5678-9012-3456"

        matches = detector.detect(text)

        # Should not detect as credit card
        credit_cards = [m for m in matches if m.pii_type == PIIType.CREDIT_CARD]
        assert len(credit_cards) == 0

    def test_credit_card_without_dashes(self):
        """Should detect credit cards without dashes"""
        detector = PIIDetector()
        # Visa test card without dashes
        text = "Card: 4111111111111111"

        matches = detector.detect(text)

        assert len(matches) == 1
        assert matches[0].pii_type == PIIType.CREDIT_CARD


class TestEmailDetection:
    """Test email detection and masking"""

    def test_detect_email(self):
        """Should detect email addresses"""
        detector = PIIDetector()
        text = "Contact me at john.doe@example.com"

        matches = detector.detect(text)

        assert len(matches) == 1
        assert matches[0].pii_type == PIIType.EMAIL
        assert matches[0].value == "john.doe@example.com"

    def test_mask_email(self):
        """Should mask email keeping first char and domain"""
        detector = PIIDetector()
        text = "Email: john.doe@example.com"

        masked = detector.mask_text(text)

        assert masked == "Email: j***@example.com"
        assert "john" not in masked
        assert "example.com" in masked

    def test_mask_short_email(self):
        """Should handle single-char local part"""
        detector = PIIDetector()
        text = "Email: a@example.com"

        masked = detector.mask_text(text)

        assert masked == "Email: *@example.com"

    def test_multiple_emails(self):
        """Should detect multiple emails"""
        detector = PIIDetector()
        text = "Emails: alice@foo.com, bob@bar.com"

        matches = detector.detect(text)

        assert len(matches) == 2
        assert all(m.pii_type == PIIType.EMAIL for m in matches)


class TestPhoneDetection:
    """Test phone number detection and masking"""

    def test_detect_phone_with_dashes(self):
        """Should detect phone with dashes"""
        detector = PIIDetector()
        text = "Call me at 555-123-4567"

        matches = detector.detect(text)

        assert len(matches) == 1
        assert matches[0].pii_type == PIIType.PHONE

    def test_detect_phone_with_parens(self):
        """Should detect phone with parentheses"""
        detector = PIIDetector()
        text = "Phone: (555) 123-4567"

        matches = detector.detect(text)

        assert len(matches) == 1
        assert matches[0].pii_type == PIIType.PHONE

    def test_mask_phone(self):
        """Should mask phone keeping last 4 digits"""
        detector = PIIDetector()
        text = "Phone: (555) 123-4567"

        masked = detector.mask_text(text)

        assert masked == "Phone: (***) ***-4567"
        assert "555" not in masked
        assert "4567" in masked

    def test_detect_phone_with_country_code(self):
        """Should detect phone with +1 country code"""
        detector = PIIDetector()
        text = "Phone: +1 555-123-4567"

        matches = detector.detect(text)

        assert len(matches) == 1
        assert matches[0].pii_type == PIIType.PHONE


class TestIPAddressDetection:
    """Test IP address detection and masking"""

    def test_detect_ip_address(self):
        """Should detect IPv4 addresses"""
        detector = PIIDetector()
        text = "Server IP: 192.168.1.1"

        matches = detector.detect(text)

        assert len(matches) == 1
        assert matches[0].pii_type == PIIType.IP_ADDRESS
        assert matches[0].value == "192.168.1.1"

    def test_mask_ip_address(self):
        """Should mask IP keeping last octet"""
        detector = PIIDetector()
        text = "IP: 192.168.1.100"

        masked = detector.mask_text(text)

        assert masked == "IP: ***.***.***.100"
        assert "192" not in masked
        assert "100" in masked


class TestMultiplePIITypes:
    """Test detection of multiple PII types in same text"""

    def test_detect_mixed_pii(self):
        """Should detect multiple PII types"""
        detector = PIIDetector()
        text = "Contact John at john@example.com or (555) 123-4567. SSN: 123-45-6789"

        matches = detector.detect(text)

        # Should detect email, phone, SSN
        assert len(matches) == 3

        types_found = {m.pii_type for m in matches}
        assert PIIType.EMAIL in types_found
        assert PIIType.PHONE in types_found
        assert PIIType.SSN in types_found

    def test_mask_mixed_pii(self):
        """Should mask all PII types"""
        detector = PIIDetector()
        text = "Email: john@example.com, SSN: 123-45-6789"

        masked = detector.mask_text(text)

        # Both should be masked
        assert "john@example.com" not in masked
        assert "123-45-6789" not in masked
        assert "j***@example.com" in masked
        assert "***-**-6789" in masked


class TestConvenienceFunctions:
    """Test convenience functions"""

    def test_detect_pii_function(self):
        """Should work via convenience function"""
        matches = detect_pii("SSN: 123-45-6789")

        assert len(matches) == 1
        assert matches[0].pii_type == PIIType.SSN

    def test_mask_pii_function(self):
        """Should work via convenience function"""
        masked = mask_pii("SSN: 123-45-6789")

        assert masked == "SSN: ***-**-6789"


class TestEdgeCases:
    """Test edge cases and error handling"""

    def test_empty_text(self):
        """Should handle empty text"""
        detector = PIIDetector()

        matches = detector.detect("")
        assert len(matches) == 0

        masked = detector.mask_text("")
        assert masked == ""

    def test_no_pii(self):
        """Should return original text if no PII"""
        detector = PIIDetector()
        text = "This is a normal sentence with no PII"

        matches = detector.detect(text)
        assert len(matches) == 0

        masked = detector.mask_text(text)
        assert masked == text

    def test_pii_at_boundaries(self):
        """Should detect PII at start/end of text"""
        detector = PIIDetector()

        # At start
        text1 = "123-45-6789 is my SSN"
        matches1 = detector.detect(text1)
        assert len(matches1) == 1

        # At end
        text2 = "My SSN is 123-45-6789"
        matches2 = detector.detect(text2)
        assert len(matches2) == 1
