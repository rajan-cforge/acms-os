"""Integration tests for Quality Validation in /ask endpoint (Week 5 Task 1).

Tests the full quality validation flow:
1. Quality scores are calculated for all Claude responses
2. quality_validation metadata is present in API responses
3. High-quality responses (>= 0.8) are cached
4. Low-quality responses (< 0.8) are NOT cached but still returned to users
5. Source type mapping (memory → document, conversation → conversation)
6. Edge cases (speculation, uncertainty, no sources)

These tests hit the actual /ask endpoint with real API calls.
"""

import pytest
import requests
import json
import time
from uuid import uuid4

# API base URL
BASE_URL = "http://localhost:40080"

# Test user
TEST_USER = str(uuid4())


class TestQualityValidationIntegration:
    """Integration tests for quality validation in /ask endpoint."""

    def setup_method(self):
        """Setup: Create test memories before each test."""
        # Store a high-quality document memory
        self.doc_memory_response = requests.post(
            f"{BASE_URL}/memories",
            json={
                "user_id": TEST_USER,
                "content": "ACMS is an Adaptive Context Memory System that uses PostgreSQL for structured data, Weaviate for vector embeddings, and Redis for caching. The Week 5 priority is memory pollution prevention with a 5-layer guardrail architecture using quality validation.",
                "tier": "LONG",
                "tags": ["acms", "architecture", "week5"],
                "metadata": {"source": "documentation"}
            }
        )
        assert self.doc_memory_response.status_code == 200, f"Failed to create test memory: {self.doc_memory_response.text}"
        self.doc_memory_id = self.doc_memory_response.json()["memory_id"]

    def teardown_method(self):
        """Cleanup: Delete test memories after each test."""
        if hasattr(self, 'doc_memory_id'):
            requests.delete(f"{BASE_URL}/memories/{self.doc_memory_id}")

    # =======================
    # Test 1: High-Quality Response with Document Sources
    # =======================

    def test_high_quality_response_with_document_sources_passes_threshold(self):
        """Test: Response with document sources should score >= 0.8 and be cached."""
        # Ask a question that will retrieve the document memory
        response = requests.post(
            f"{BASE_URL}/ask",
            json={
                "question": "What is ACMS and what databases does it use?",
                "user_id": TEST_USER,
                "context_limit": 5
            }
        )

        assert response.status_code == 200, f"Request failed: {response.text}"
        result = response.json()

        # Check quality_validation field exists
        assert "quality_validation" in result, "quality_validation field missing from response"
        qv = result["quality_validation"]

        # Check quality score >= 0.8 (high-quality with document sources)
        assert qv["confidence_score"] >= 0.8, f"Expected confidence >= 0.8, got {qv['confidence_score']}"
        assert qv["should_store"] is True, "High-quality response should have should_store=True"
        assert qv["passed_threshold"] is True, "High-quality response should pass threshold"

        # Check source trust is HIGH (1.0) for document sources
        assert qv["source_trust_score"] == 1.0, f"Expected source_trust=1.0 for documents, got {qv['source_trust_score']}"

        # Check completeness is high (Claude responses are typically > 100 chars)
        assert qv["completeness_score"] >= 0.5, f"Expected completeness >= 0.5, got {qv['completeness_score']}"

        # Check no flagged reason for high-quality
        assert qv["flagged_reason"] is None, f"High-quality response should not be flagged: {qv['flagged_reason']}"

        # Verify response was cached (from_cache might be True on second call)
        # This is just checking the first call is not from cache
        assert result["from_cache"] is False, "First query should not be from cache"

    def test_high_quality_response_is_cached_on_second_call(self):
        """Test: Second identical query should return cached result with quality validation."""
        query = "What is ACMS and what databases does it use?"

        # First call (fresh)
        response1 = requests.post(
            f"{BASE_URL}/ask",
            json={
                "question": query,
                "user_id": TEST_USER,
                "context_limit": 5
            }
        )
        assert response1.status_code == 200
        result1 = response1.json()
        assert result1["from_cache"] is False, "First query should not be from cache"
        assert result1["quality_validation"]["should_store"] is True, "First query should be high-quality"

        # Second call (should be cached)
        time.sleep(1)  # Brief pause to ensure cache is written
        response2 = requests.post(
            f"{BASE_URL}/ask",
            json={
                "question": query,
                "user_id": TEST_USER,
                "context_limit": 5
            }
        )
        assert response2.status_code == 200
        result2 = response2.json()

        # Verify second call is from cache
        assert result2["from_cache"] is True, "Second identical query should be from cache"
        # Note: Cached responses may not have quality_validation since they skip generation
        # This is expected behavior - quality validation only runs on fresh generation

    # =======================
    # Test 2: Low-Quality Response (No Sources)
    # =======================

    def test_low_quality_response_without_sources_fails_threshold(self):
        """Test: Response without sources should score < 0.8 and NOT be cached."""
        # Ask a question that has no relevant memories (empty context)
        random_query = f"What is the quantum flux capacitor theory version {uuid4()}?"

        response = requests.post(
            f"{BASE_URL}/ask",
            json={
                "question": random_query,
                "user_id": str(uuid4()),  # New user with no memories
                "context_limit": 5
            }
        )

        assert response.status_code == 200, f"Request failed: {response.text}"
        result = response.json()

        # Check quality_validation field exists
        assert "quality_validation" in result, "quality_validation field missing from response"
        qv = result["quality_validation"]

        # Low-quality responses (no sources) should have low confidence
        # With no sources: source_trust = 0.3
        # Even with perfect completeness (1.0) and no uncertainty (1.0):
        # confidence = 0.3*0.4 + 1.0*0.2 + 1.0*0.4 = 0.12 + 0.20 + 0.40 = 0.72 < 0.8
        # So it should fail threshold
        assert qv["confidence_score"] < 0.8, f"Expected confidence < 0.8 for no sources, got {qv['confidence_score']}"
        assert qv["should_store"] is False, "Low-quality response should have should_store=False"
        assert qv["passed_threshold"] is False, "Low-quality response should fail threshold"

        # Check source trust is LOW (0.3) for no sources
        assert qv["source_trust_score"] == 0.3, f"Expected source_trust=0.3 for no sources, got {qv['source_trust_score']}"

        # Check flagged reason exists
        assert qv["flagged_reason"] is not None, "Low-quality response should have flagged_reason"
        assert "no_sources" in qv["flagged_reason"].lower() or "low_trust" in qv["flagged_reason"].lower(), \
            f"Expected no_sources/low_trust in flagged_reason, got: {qv['flagged_reason']}"

        # CRITICAL: Response should still be returned to user (not rejected)
        assert "answer" in result, "Low-quality responses should still be returned to user"
        assert len(result["answer"]) > 0, "Low-quality responses should have non-empty answer"

        # Verify response was NOT cached (from_cache should be False)
        assert result["from_cache"] is False, "Low-quality responses should not be cached"

    def test_low_quality_response_is_not_cached_on_second_call(self):
        """Test: Second call for low-quality query should also be fresh (not cached)."""
        random_query = f"What is the theory of {uuid4()}?"
        user_id = str(uuid4())  # User with no memories

        # First call
        response1 = requests.post(
            f"{BASE_URL}/ask",
            json={
                "question": random_query,
                "user_id": user_id,
                "context_limit": 5
            }
        )
        assert response1.status_code == 200
        result1 = response1.json()
        assert result1["quality_validation"]["should_store"] is False, "Query should be low-quality"

        # Second call (should also be fresh, NOT cached)
        time.sleep(1)
        response2 = requests.post(
            f"{BASE_URL}/ask",
            json={
                "question": random_query,
                "user_id": user_id,
                "context_limit": 5
            }
        )
        assert response2.status_code == 200
        result2 = response2.json()

        # Verify second call is NOT from cache (low-quality responses are not cached)
        assert result2["from_cache"] is False, "Low-quality responses should not be cached"
        assert result2["quality_validation"]["should_store"] is False, "Second call should also be low-quality"

    # =======================
    # Test 3: Quality Validation Metadata Structure
    # =======================

    def test_quality_validation_metadata_structure(self):
        """Test: quality_validation field has all required components."""
        response = requests.post(
            f"{BASE_URL}/ask",
            json={
                "question": "What is ACMS?",
                "user_id": TEST_USER,
                "context_limit": 5
            }
        )

        assert response.status_code == 200
        result = response.json()
        qv = result["quality_validation"]

        # Check all required fields exist
        required_fields = [
            "confidence_score",
            "should_store",
            "source_trust_score",
            "completeness_score",
            "uncertainty_score",
            "flagged_reason",
            "passed_threshold"
        ]
        for field in required_fields:
            assert field in qv, f"Missing required field: {field}"

        # Check types
        assert isinstance(qv["confidence_score"], float), "confidence_score should be float"
        assert isinstance(qv["should_store"], bool), "should_store should be bool"
        assert isinstance(qv["source_trust_score"], float), "source_trust_score should be float"
        assert isinstance(qv["completeness_score"], float), "completeness_score should be float"
        assert isinstance(qv["uncertainty_score"], float), "uncertainty_score should be float"
        assert qv["flagged_reason"] is None or isinstance(qv["flagged_reason"], str), \
            "flagged_reason should be None or str"
        assert isinstance(qv["passed_threshold"], bool), "passed_threshold should be bool"

        # Check value ranges
        assert 0.0 <= qv["confidence_score"] <= 1.0, "confidence_score out of range [0.0, 1.0]"
        assert 0.0 <= qv["source_trust_score"] <= 1.0, "source_trust_score out of range [0.0, 1.0]"
        assert 0.0 <= qv["completeness_score"] <= 1.0, "completeness_score out of range [0.0, 1.0]"
        assert 0.0 <= qv["uncertainty_score"] <= 1.0, "uncertainty_score out of range [0.0, 1.0]"

    # =======================
    # Test 4: Source Type Mapping
    # =======================

    def test_source_type_mapping_memory_to_document(self):
        """Test: Memory sources should be mapped to 'document' type (HIGH trust 1.0)."""
        response = requests.post(
            f"{BASE_URL}/ask",
            json={
                "question": "What is the Week 5 priority for ACMS?",
                "user_id": TEST_USER,
                "context_limit": 5
            }
        )

        assert response.status_code == 200
        result = response.json()
        qv = result["quality_validation"]

        # Memory sources should be treated as documents (HIGH trust)
        assert qv["source_trust_score"] == 1.0, \
            f"Memory sources should have document trust (1.0), got {qv['source_trust_score']}"

    # =======================
    # Test 5: Threshold Enforcement
    # =======================

    def test_threshold_enforcement_at_0_8(self):
        """Test: Responses with confidence >= 0.8 pass, < 0.8 fail."""
        # Test with document sources (should pass)
        response_high = requests.post(
            f"{BASE_URL}/ask",
            json={
                "question": "What is ACMS?",
                "user_id": TEST_USER,
                "context_limit": 5
            }
        )
        assert response_high.status_code == 200
        qv_high = response_high.json()["quality_validation"]

        if qv_high["confidence_score"] >= 0.8:
            assert qv_high["should_store"] is True, "Confidence >= 0.8 should have should_store=True"
            assert qv_high["passed_threshold"] is True, "Confidence >= 0.8 should pass threshold"
            assert qv_high["flagged_reason"] is None, "Confidence >= 0.8 should not be flagged"

        # Test without sources (should fail)
        response_low = requests.post(
            f"{BASE_URL}/ask",
            json={
                "question": f"Random query {uuid4()}",
                "user_id": str(uuid4()),
                "context_limit": 5
            }
        )
        assert response_low.status_code == 200
        qv_low = response_low.json()["quality_validation"]

        if qv_low["confidence_score"] < 0.8:
            assert qv_low["should_store"] is False, "Confidence < 0.8 should have should_store=False"
            assert qv_low["passed_threshold"] is False, "Confidence < 0.8 should fail threshold"
            assert qv_low["flagged_reason"] is not None, "Confidence < 0.8 should be flagged"

    # =======================
    # Test 6: Cached Responses (No Quality Validation)
    # =======================

    def test_cached_responses_skip_quality_validation(self):
        """Test: Cached responses may not have quality_validation (optimization)."""
        query = "What is ACMS architecture?"

        # First call (fresh, will have quality validation)
        response1 = requests.post(
            f"{BASE_URL}/ask",
            json={
                "question": query,
                "user_id": TEST_USER,
                "context_limit": 5
            }
        )
        assert response1.status_code == 200
        result1 = response1.json()
        assert result1["from_cache"] is False

        # If first response is high-quality, it should be cached
        if result1.get("quality_validation", {}).get("should_store") is True:
            # Second call (should be cached)
            time.sleep(1)
            response2 = requests.post(
                f"{BASE_URL}/ask",
                json={
                    "question": query,
                    "user_id": TEST_USER,
                    "context_limit": 5
                }
            )
            assert response2.status_code == 200
            result2 = response2.json()
            assert result2["from_cache"] is True, "Second call should be from cache"

    # =======================
    # Test 7: Quality Scores Affect Confidence
    # =======================

    def test_quality_scores_used_as_confidence(self):
        """Test: Quality confidence_score should match result confidence."""
        response = requests.post(
            f"{BASE_URL}/ask",
            json={
                "question": "What is ACMS?",
                "user_id": TEST_USER,
                "context_limit": 5
            }
        )

        assert response.status_code == 200
        result = response.json()

        # The overall confidence should equal quality_validation.confidence_score
        # (Week 5 Task 1: Quality scores replace old relevance-based confidence)
        quality_confidence = result["quality_validation"]["confidence_score"]
        overall_confidence = result["confidence"]

        assert quality_confidence == overall_confidence, \
            f"Quality confidence ({quality_confidence}) should match overall confidence ({overall_confidence})"

    # =======================
    # Test 8: Real-World Scenarios
    # =======================

    def test_real_world_well_grounded_answer_passes(self):
        """Test: Well-grounded answer with document sources should pass quality check."""
        # Create a detailed memory
        memory_response = requests.post(
            f"{BASE_URL}/memories",
            json={
                "user_id": TEST_USER,
                "content": "The ACMS quality validation algorithm uses a weighted scoring system: confidence = (source_trust × 0.4) + (completeness × 0.2) + (uncertainty × 0.4). Document sources have HIGH trust (1.0), conversation sources have MEDIUM trust (0.7), and no sources have LOW trust (0.3). The threshold is 0.8.",
                "tier": "LONG",
                "tags": ["quality", "algorithm"]
            }
        )
        assert memory_response.status_code == 200
        memory_id = memory_response.json()["memory_id"]

        try:
            # Ask about quality validation algorithm
            response = requests.post(
                f"{BASE_URL}/ask",
                json={
                    "question": "How does the ACMS quality validation algorithm work?",
                    "user_id": TEST_USER,
                    "context_limit": 5
                }
            )

            assert response.status_code == 200
            result = response.json()
            qv = result["quality_validation"]

            # Well-grounded answer should pass
            assert qv["should_store"] is True, "Well-grounded answer should pass quality check"
            assert qv["confidence_score"] >= 0.8, f"Expected >= 0.8, got {qv['confidence_score']}"
            assert qv["source_trust_score"] == 1.0, "Document sources should have HIGH trust"
        finally:
            # Cleanup
            requests.delete(f"{BASE_URL}/memories/{memory_id}")

    # =======================
    # Test 9: Edge Cases
    # =======================

    def test_empty_context_still_returns_response(self):
        """Test: Even with empty context (no sources), API should return a response."""
        response = requests.post(
            f"{BASE_URL}/ask",
            json={
                "question": f"Random question {uuid4()}",
                "user_id": str(uuid4()),  # New user, no memories
                "context_limit": 5
            }
        )

        assert response.status_code == 200
        result = response.json()

        # Should have answer despite low quality
        assert "answer" in result
        assert len(result["answer"]) > 0

        # Should have quality validation
        assert "quality_validation" in result
        assert result["quality_validation"]["source_trust_score"] == 0.3  # No sources

    def test_very_short_context_limit(self):
        """Test: context_limit=1 should still work with quality validation."""
        response = requests.post(
            f"{BASE_URL}/ask",
            json={
                "question": "What is ACMS?",
                "user_id": TEST_USER,
                "context_limit": 1
            }
        )

        assert response.status_code == 200
        result = response.json()
        assert "quality_validation" in result
        assert result["quality_validation"]["confidence_score"] >= 0.0
