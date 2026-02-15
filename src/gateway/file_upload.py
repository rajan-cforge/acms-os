"""File Upload Utilities

Sprint 3 Day 13: File Upload capability

This module contains file upload validation and text extraction utilities.
Extracted from api_server.py for testability.
"""

import json
from typing import Optional


# =============================================================================
# FILE UPLOAD CONSTANTS
# =============================================================================

ALLOWED_FILE_TYPES = {
    # Text files
    "text/plain": ".txt",
    "text/markdown": ".md",
    "text/x-markdown": ".md",
    # PDF
    "application/pdf": ".pdf",
    # Images
    "image/png": ".png",
    "image/jpeg": ".jpg",
    "image/jpg": ".jpg",
    "image/gif": ".gif",
    "image/webp": ".webp",
    # JSON
    "application/json": ".json",
}

MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB


# =============================================================================
# FILE VALIDATION
# =============================================================================

def validate_file_type(content_type: str) -> bool:
    """Check if the content type is allowed.

    Args:
        content_type: MIME type of the file

    Returns:
        True if allowed, False otherwise
    """
    return content_type in ALLOWED_FILE_TYPES


def validate_file_size(size_bytes: int) -> bool:
    """Check if the file size is within limits.

    Args:
        size_bytes: Size of the file in bytes

    Returns:
        True if within limits, False otherwise
    """
    return size_bytes <= MAX_FILE_SIZE


def get_file_extension(content_type: str) -> Optional[str]:
    """Get the expected file extension for a content type.

    Args:
        content_type: MIME type of the file

    Returns:
        File extension (e.g., ".txt") or None if not allowed
    """
    return ALLOWED_FILE_TYPES.get(content_type)


# =============================================================================
# TEXT EXTRACTION
# =============================================================================

async def extract_text_from_file(
    file_content: bytes,
    content_type: str,
    filename: str
) -> Optional[str]:
    """Extract text content from uploaded file.

    Args:
        file_content: File bytes
        content_type: MIME type
        filename: Original filename

    Returns:
        Extracted text or None for images/unknown types
    """
    # Text files
    if content_type in ["text/plain", "text/markdown", "text/x-markdown"]:
        return file_content.decode('utf-8', errors='ignore')

    # JSON files
    if content_type == "application/json":
        try:
            data = json.loads(file_content.decode('utf-8'))
            return json.dumps(data, indent=2)
        except Exception:
            return file_content.decode('utf-8', errors='ignore')

    # PDF files
    if content_type == "application/pdf":
        return await _extract_pdf_text(file_content, filename)

    # Images - return description placeholder
    if content_type.startswith("image/"):
        return f"[Image file: {filename}] - Image analysis not yet implemented"

    return None


async def _extract_pdf_text(file_content: bytes, filename: str) -> str:
    """Extract text from PDF file.

    Args:
        file_content: PDF file bytes
        filename: Original filename

    Returns:
        Extracted text or placeholder message
    """
    try:
        import io
        try:
            from pypdf import PdfReader
            reader = PdfReader(io.BytesIO(file_content))
            text_parts = []
            for page in reader.pages[:10]:  # Limit to first 10 pages
                text_parts.append(page.extract_text() or "")
            return "\n\n".join(text_parts)
        except ImportError:
            try:
                import PyPDF2
                reader = PyPDF2.PdfReader(io.BytesIO(file_content))
                text_parts = []
                for page in reader.pages[:10]:
                    text_parts.append(page.extract_text() or "")
                return "\n\n".join(text_parts)
            except ImportError:
                return f"[PDF file: {filename}] - PDF text extraction not available"
    except Exception as e:
        return f"[PDF file: {filename}] - Text extraction failed: {str(e)}"


# =============================================================================
# ERROR MESSAGES
# =============================================================================

def get_invalid_type_error() -> str:
    """Get error message for invalid file type."""
    return f"File type not supported. Allowed types: {list(ALLOWED_FILE_TYPES.keys())}"


def get_file_too_large_error() -> str:
    """Get error message for file too large."""
    return f"File too large. Maximum size: {MAX_FILE_SIZE / 1024 / 1024}MB"
