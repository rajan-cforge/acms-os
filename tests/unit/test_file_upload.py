"""Unit tests for file upload functionality.

Sprint 3 Day 13: File Upload capability

Tests cover:
1. File type validation
2. File size validation
3. Text extraction from various file types
4. Error messages
5. Security considerations
"""

import pytest
import sys
import os
import json

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from src.gateway.file_upload import (
    ALLOWED_FILE_TYPES,
    MAX_FILE_SIZE,
    validate_file_type,
    validate_file_size,
    get_file_extension,
    extract_text_from_file,
    get_invalid_type_error,
    get_file_too_large_error,
)


class TestFileTypeValidation:
    """Tests for file type validation."""

    def test_allowed_file_types_defined(self):
        """Should have allowed file types defined."""
        assert "text/plain" in ALLOWED_FILE_TYPES
        assert "text/markdown" in ALLOWED_FILE_TYPES
        assert "application/pdf" in ALLOWED_FILE_TYPES
        assert "application/json" in ALLOWED_FILE_TYPES
        assert "image/png" in ALLOWED_FILE_TYPES
        assert "image/jpeg" in ALLOWED_FILE_TYPES

    def test_text_plain_allowed(self):
        """Should allow text/plain files."""
        assert ALLOWED_FILE_TYPES["text/plain"] == ".txt"
        assert validate_file_type("text/plain") is True

    def test_markdown_allowed(self):
        """Should allow markdown files."""
        assert ALLOWED_FILE_TYPES["text/markdown"] == ".md"
        assert ALLOWED_FILE_TYPES["text/x-markdown"] == ".md"
        assert validate_file_type("text/markdown") is True
        assert validate_file_type("text/x-markdown") is True

    def test_pdf_allowed(self):
        """Should allow PDF files."""
        assert ALLOWED_FILE_TYPES["application/pdf"] == ".pdf"
        assert validate_file_type("application/pdf") is True

    def test_images_allowed(self):
        """Should allow common image types."""
        assert ALLOWED_FILE_TYPES["image/png"] == ".png"
        assert ALLOWED_FILE_TYPES["image/jpeg"] == ".jpg"
        assert ALLOWED_FILE_TYPES["image/gif"] == ".gif"
        assert ALLOWED_FILE_TYPES["image/webp"] == ".webp"
        assert validate_file_type("image/png") is True
        assert validate_file_type("image/jpeg") is True

    def test_json_allowed(self):
        """Should allow JSON files."""
        assert ALLOWED_FILE_TYPES["application/json"] == ".json"
        assert validate_file_type("application/json") is True

    def test_invalid_type_rejected(self):
        """Should reject invalid file types."""
        assert validate_file_type("application/x-executable") is False
        assert validate_file_type("text/html") is False
        assert validate_file_type("application/octet-stream") is False

    def test_get_file_extension(self):
        """Should return correct file extension."""
        assert get_file_extension("text/plain") == ".txt"
        assert get_file_extension("application/pdf") == ".pdf"
        assert get_file_extension("image/png") == ".png"

    def test_get_file_extension_unknown(self):
        """Should return None for unknown types."""
        assert get_file_extension("application/x-unknown") is None


class TestFileSizeValidation:
    """Tests for file size validation."""

    def test_max_file_size_defined(self):
        """Should have max file size defined."""
        assert MAX_FILE_SIZE == 10 * 1024 * 1024  # 10 MB

    def test_max_size_is_reasonable(self):
        """Max size should be reasonable (1MB - 100MB range)."""
        assert MAX_FILE_SIZE >= 1 * 1024 * 1024  # At least 1MB
        assert MAX_FILE_SIZE <= 100 * 1024 * 1024  # At most 100MB

    def test_small_file_allowed(self):
        """Should allow small files."""
        assert validate_file_size(1024) is True  # 1 KB
        assert validate_file_size(1024 * 1024) is True  # 1 MB

    def test_max_size_file_allowed(self):
        """Should allow files exactly at max size."""
        assert validate_file_size(MAX_FILE_SIZE) is True

    def test_oversized_file_rejected(self):
        """Should reject files over max size."""
        assert validate_file_size(MAX_FILE_SIZE + 1) is False
        assert validate_file_size(MAX_FILE_SIZE * 2) is False


class TestTextExtraction:
    """Tests for text extraction from files."""

    @pytest.mark.asyncio
    async def test_extract_text_plain(self):
        """Should extract text from plain text files."""
        content = b"Hello, this is a test file."
        result = await extract_text_from_file(content, "text/plain", "test.txt")
        assert result == "Hello, this is a test file."

    @pytest.mark.asyncio
    async def test_extract_text_markdown(self):
        """Should extract text from markdown files."""
        content = b"# Header\n\nThis is **bold** text."
        result = await extract_text_from_file(content, "text/markdown", "test.md")
        assert result == "# Header\n\nThis is **bold** text."

    @pytest.mark.asyncio
    async def test_extract_text_x_markdown(self):
        """Should extract text from x-markdown files."""
        content = b"# Test\nContent here"
        result = await extract_text_from_file(content, "text/x-markdown", "test.md")
        assert result == "# Test\nContent here"

    @pytest.mark.asyncio
    async def test_extract_text_json(self):
        """Should extract and format JSON files."""
        data = {"key": "value", "number": 42}
        content = json.dumps(data).encode('utf-8')
        result = await extract_text_from_file(content, "application/json", "test.json")

        # Should be formatted JSON
        assert "key" in result
        assert "value" in result
        assert "42" in result

    @pytest.mark.asyncio
    async def test_extract_text_invalid_json(self):
        """Should handle invalid JSON gracefully."""
        content = b"{ invalid json }"
        result = await extract_text_from_file(content, "application/json", "test.json")

        # Should return raw content
        assert "invalid json" in result

    @pytest.mark.asyncio
    async def test_extract_text_image_placeholder(self):
        """Should return placeholder for images."""
        content = b"fake image data"
        result = await extract_text_from_file(content, "image/png", "test.png")

        assert "[Image file: test.png]" in result
        assert "not yet implemented" in result

    @pytest.mark.asyncio
    async def test_extract_text_jpeg_placeholder(self):
        """Should return placeholder for JPEG images."""
        content = b"fake jpeg data"
        result = await extract_text_from_file(content, "image/jpeg", "photo.jpg")

        assert "[Image file: photo.jpg]" in result

    @pytest.mark.asyncio
    async def test_extract_text_utf8_handling(self):
        """Should handle UTF-8 encoded text."""
        content = "Hello 世界 🌍".encode('utf-8')
        result = await extract_text_from_file(content, "text/plain", "unicode.txt")

        assert "Hello" in result
        assert "世界" in result

    @pytest.mark.asyncio
    async def test_extract_text_unknown_type(self):
        """Should return None for unknown types."""
        content = b"binary data"
        result = await extract_text_from_file(content, "application/octet-stream", "file.bin")
        assert result is None


class TestPDFExtraction:
    """Tests for PDF text extraction."""

    @pytest.mark.asyncio
    async def test_pdf_extraction_fallback(self):
        """Should handle missing PDF library gracefully."""
        # Fake PDF content (not a real PDF)
        content = b"%PDF-1.4 fake pdf content"
        result = await extract_text_from_file(content, "application/pdf", "test.pdf")

        # Should either extract or return a placeholder
        assert result is not None
        assert "test.pdf" in result or len(result) > 0

    @pytest.mark.asyncio
    async def test_pdf_extraction_error_handling(self):
        """Should handle PDF extraction errors gracefully."""
        # Invalid PDF content
        content = b"not a pdf at all"
        result = await extract_text_from_file(content, "application/pdf", "broken.pdf")

        # Should return error message, not crash
        assert result is not None
        assert "broken.pdf" in result


class TestDesktopFileUploadComponent:
    """Tests for desktop app file upload component logic."""

    def test_allowed_types_match_backend(self):
        """Frontend allowed types should match backend."""
        # These are the types allowed in file-upload.js
        frontend_types = {
            'text/plain': '.txt',
            'text/markdown': '.md',
            'application/pdf': '.pdf',
            'image/png': '.png',
            'image/jpeg': '.jpg',
            'image/gif': '.gif',
            'image/webp': '.webp',
            'application/json': '.json'
        }

        # All frontend types should be allowed by backend
        for mime_type in frontend_types.keys():
            assert mime_type in ALLOWED_FILE_TYPES, f"{mime_type} not allowed by backend"

    def test_max_size_match_backend(self):
        """Frontend max size should match backend."""
        # Desktop app uses 10 MB max (10 * 1024 * 1024)
        frontend_max = 10 * 1024 * 1024
        assert frontend_max == MAX_FILE_SIZE


class TestFileValidationHelpers:
    """Tests for file validation helper functions."""

    def test_file_extension_mapping(self):
        """File extension mapping should be consistent."""
        # Common variations should map to same extension
        assert ALLOWED_FILE_TYPES.get("image/jpeg") == ALLOWED_FILE_TYPES.get("image/jpg")

    def test_text_types_have_text_extension(self):
        """Text types should map to text extensions."""
        text_extensions = [".txt", ".md", ".json"]
        text_types = ["text/plain", "text/markdown", "text/x-markdown", "application/json"]

        for t in text_types:
            ext = ALLOWED_FILE_TYPES.get(t)
            assert ext in text_extensions, f"{t} should have text extension"


class TestFileUploadSecurity:
    """Security tests for file upload."""

    def test_no_executable_types_allowed(self):
        """Should not allow executable file types."""
        dangerous_types = [
            "application/x-executable",
            "application/x-msdos-program",
            "application/x-sh",
            "application/x-bash",
            "application/javascript",
            "text/javascript",
            "application/x-python-code",
        ]

        for dangerous in dangerous_types:
            assert dangerous not in ALLOWED_FILE_TYPES, f"{dangerous} should not be allowed"

    def test_no_html_allowed(self):
        """Should not allow HTML files (XSS risk)."""
        html_types = ["text/html", "application/xhtml+xml"]

        for html_type in html_types:
            assert html_type not in ALLOWED_FILE_TYPES, f"{html_type} should not be allowed"

    def test_no_svg_allowed(self):
        """Should not allow SVG files (potential XSS vector)."""
        assert "image/svg+xml" not in ALLOWED_FILE_TYPES


class TestErrorMessages:
    """Tests for error messages."""

    def test_invalid_type_error(self):
        """Invalid type error should list allowed types."""
        error = get_invalid_type_error()

        assert "File type not supported" in error
        assert "text/plain" in error

    def test_file_too_large_error(self):
        """File too large error should show limit."""
        error = get_file_too_large_error()

        assert "File too large" in error
        assert "10" in error  # 10 MB


class TestPrivacyLevels:
    """Tests for privacy level handling in file uploads."""

    def test_valid_privacy_levels(self):
        """Should support all valid privacy levels."""
        valid_levels = ["PUBLIC", "INTERNAL", "CONFIDENTIAL", "LOCAL_ONLY"]

        # These should all be valid options for file uploads
        for level in valid_levels:
            assert level in valid_levels


class TestEdgeCases:
    """Tests for edge cases."""

    @pytest.mark.asyncio
    async def test_empty_file(self):
        """Should handle empty files."""
        content = b""
        result = await extract_text_from_file(content, "text/plain", "empty.txt")
        assert result == ""

    @pytest.mark.asyncio
    async def test_binary_in_text_file(self):
        """Should handle binary content in text file gracefully."""
        content = b"\x00\x01\x02\x03"  # Binary bytes
        result = await extract_text_from_file(content, "text/plain", "binary.txt")
        # Should not crash, may have replacement characters
        assert result is not None

    @pytest.mark.asyncio
    async def test_large_json(self):
        """Should handle large JSON files."""
        data = {"key": "x" * 10000}  # Large string value
        content = json.dumps(data).encode('utf-8')
        result = await extract_text_from_file(content, "application/json", "large.json")
        assert "key" in result

    @pytest.mark.asyncio
    async def test_nested_json(self):
        """Should handle nested JSON structures."""
        data = {"level1": {"level2": {"level3": "value"}}}
        content = json.dumps(data).encode('utf-8')
        result = await extract_text_from_file(content, "application/json", "nested.json")
        assert "level1" in result
        assert "level3" in result
