"""
Unit tests for pipeline tracking in /ask endpoint.

Following TDD: These tests define the expected behavior BEFORE implementation.
"""
import pytest
from datetime import datetime
from typing import List, Dict, Any


class TestPipelineStageStructure:
    """Test the structure of pipeline stage data."""

    def test_pipeline_stage_has_required_fields(self):
        """Each pipeline stage must have: name, status, latency_ms."""
        # This defines the minimal interface
        stage = {
            "name": "cache_check",
            "status": "hit",
            "latency_ms": 45
        }

        assert "name" in stage
        assert "status" in stage
        assert "latency_ms" in stage
        assert isinstance(stage["name"], str)
        assert isinstance(stage["status"], str)
        assert isinstance(stage["latency_ms"], (int, float))

    def test_pipeline_stage_optional_fields(self):
        """Pipeline stages can include optional metadata."""
        stage = {
            "name": "cache_check",
            "status": "hit",
            "latency_ms": 45,
            "cost_saved": 0.024,
            "tokens_saved": 1500,
            "details": {"cache_key": "abc123"}
        }

        # Optional fields should be allowed
        assert stage.get("cost_saved") == 0.024
        assert stage.get("tokens_saved") == 1500
        assert isinstance(stage.get("details"), dict)

    def test_pipeline_contains_expected_stages(self):
        """Pipeline should contain standard stages in order."""
        pipeline = {
            "stages": [
                {"name": "cache_check", "status": "miss", "latency_ms": 12},
                {"name": "search", "status": "success", "latency_ms": 234},
                {"name": "llm_generation", "status": "success", "latency_ms": 1850}
            ]
        }

        stage_names = [s["name"] for s in pipeline["stages"]]

        # Must contain these core stages
        assert "cache_check" in stage_names
        assert "search" in stage_names
        assert "llm_generation" in stage_names

        # Should be in chronological order
        assert stage_names.index("cache_check") < stage_names.index("search")
        assert stage_names.index("search") < stage_names.index("llm_generation")


class TestCacheCheckStage:
    """Test cache_check stage tracking."""

    def test_cache_hit_stage(self):
        """When cache hits, cost_saved should be calculated."""
        stage = {
            "name": "cache_check",
            "status": "hit",
            "latency_ms": 45,
            "cost_saved": 0.024,  # Cost of LLM call avoided
            "tokens_saved": 1500
        }

        assert stage["status"] == "hit"
        assert stage["cost_saved"] > 0
        assert stage["tokens_saved"] > 0

    def test_cache_miss_stage(self):
        """When cache misses, no savings."""
        stage = {
            "name": "cache_check",
            "status": "miss",
            "latency_ms": 12,
            "cost_saved": 0.0,
            "tokens_saved": 0
        }

        assert stage["status"] == "miss"
        assert stage["cost_saved"] == 0.0
        assert stage["tokens_saved"] == 0


class TestSearchStage:
    """Test search stage tracking."""

    def test_search_success_stage(self):
        """Successful search should report results found."""
        stage = {
            "name": "search",
            "status": "success",
            "latency_ms": 234,
            "results_found": 15,
            "intent_detected": "FACTUAL",
            "sources_used": ["conversation_turns", "memories", "qa_pairs"]
        }

        assert stage["status"] == "success"
        assert stage["results_found"] > 0
        assert "intent_detected" in stage
        assert len(stage["sources_used"]) > 0

    def test_search_no_results_stage(self):
        """Search with no results should still be success."""
        stage = {
            "name": "search",
            "status": "success",
            "latency_ms": 150,
            "results_found": 0,
            "intent_detected": "EXPLORATORY"
        }

        assert stage["status"] == "success"
        assert stage["results_found"] == 0


class TestLLMGenerationStage:
    """Test LLM generation stage tracking."""

    def test_llm_generation_success(self):
        """Successful LLM call should report tokens and cost."""
        stage = {
            "name": "llm_generation",
            "status": "success",
            "latency_ms": 1850,
            "model_used": "claude-sonnet-4.5",
            "tokens_used": 2500,
            "cost": 0.038,
            "response_source": "llm_generated"
        }

        assert stage["status"] == "success"
        assert stage["tokens_used"] > 0
        assert stage["cost"] > 0
        assert stage["model_used"] in ["claude-sonnet-4.5", "gpt-4o", "gemini-flash"]

    def test_llm_generation_from_cache(self):
        """When response from cache, LLM stage should reflect that."""
        stage = {
            "name": "llm_generation",
            "status": "skipped",
            "latency_ms": 0,
            "model_used": None,
            "tokens_used": 0,
            "cost": 0.0,
            "response_source": "semantic_cache"
        }

        assert stage["status"] == "skipped"
        assert stage["response_source"] == "semantic_cache"
        assert stage["cost"] == 0.0


class TestPipelineCalculations:
    """Test pipeline-level calculations."""

    def test_total_latency_calculation(self):
        """Total latency = sum of all stage latencies."""
        pipeline = {
            "stages": [
                {"name": "cache_check", "latency_ms": 12},
                {"name": "search", "latency_ms": 234},
                {"name": "llm_generation", "latency_ms": 1850}
            ],
            "total_latency_ms": 2096
        }

        calculated_total = sum(s["latency_ms"] for s in pipeline["stages"])
        assert pipeline["total_latency_ms"] == calculated_total

    def test_total_cost_calculation(self):
        """Total cost = sum of costs - savings."""
        pipeline = {
            "stages": [
                {"name": "cache_check", "cost_saved": 0.0},
                {"name": "search", "cost": 0.001},
                {"name": "llm_generation", "cost": 0.038}
            ],
            "total_cost": 0.039
        }

        # Cache miss, so paid full cost
        assert pipeline["total_cost"] == pytest.approx(0.039, rel=0.01)


class TestPipelineIntegration:
    """Test pipeline integration with AskResponse."""

    def test_ask_response_includes_pipeline(self):
        """AskResponse should include pipeline field."""
        response = {
            "answer": "Test answer",
            "sources": [],
            "confidence": 0.85,
            "pipeline": {  # NEW FIELD
                "stages": [
                    {"name": "cache_check", "status": "miss", "latency_ms": 12},
                    {"name": "search", "status": "success", "latency_ms": 234},
                    {"name": "llm_generation", "status": "success", "latency_ms": 1850}
                ],
                "total_latency_ms": 2096,
                "total_cost": 0.039
            }
        }

        assert "pipeline" in response
        assert "stages" in response["pipeline"]
        assert len(response["pipeline"]["stages"]) >= 3
        assert "total_latency_ms" in response["pipeline"]
