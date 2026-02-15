"""
Tests for Structured Logging with Correlation IDs

Week 5 Day 1: Task 1 (2 hours)
Total: 10 tests

Purpose: Production-grade logging for request tracing
"""

import pytest
import logging
import json
import asyncio
from unittest.mock import Mock, patch
from io import StringIO

from src.utils.logging import (
    CorrelationIDFilter,
    JSONFormatter,
    setup_logging,
    correlation_id_ctx,
    get_correlation_id,
    set_correlation_id
)


@pytest.fixture(autouse=True)
def reset_correlation_id():
    """Reset correlation ID before each test"""
    correlation_id_ctx.set('')
    yield
    correlation_id_ctx.set('')


@pytest.fixture
def log_capture():
    """Capture log output for testing with JSON formatter"""
    stream = StringIO()
    handler = logging.StreamHandler(stream)
    handler.setLevel(logging.INFO)

    # Use JSON formatter
    formatter = JSONFormatter()
    handler.setFormatter(formatter)

    # Add correlation ID filter
    corr_filter = CorrelationIDFilter()
    handler.addFilter(corr_filter)

    logger = logging.getLogger('test_logger')
    logger.setLevel(logging.INFO)
    logger.handlers.clear()  # Clear existing handlers
    logger.addHandler(handler)

    yield logger, stream

    logger.removeHandler(handler)


def test_correlation_id_generated():
    """Test correlation ID is generated if not provided"""
    # When no correlation ID is set, one should be generated
    correlation_id = get_correlation_id()

    # Should return a valid UUID string
    assert correlation_id is not None
    assert len(correlation_id) > 0
    assert isinstance(correlation_id, str)


def test_correlation_id_from_context():
    """Test correlation ID can be set and retrieved from context"""
    # Set a specific correlation ID
    test_id = "test-correlation-123"
    set_correlation_id(test_id)

    # Should retrieve the same ID
    retrieved_id = get_correlation_id()
    assert retrieved_id == test_id


def test_correlation_id_in_logs(log_capture):
    """Test correlation ID appears in all logs"""
    logger, stream = log_capture

    # Set correlation ID
    test_id = "test-123"
    set_correlation_id(test_id)

    # Log a message
    logger.info("Test message")

    # Get log output (JSON format)
    log_output = stream.getvalue().strip()
    log_data = json.loads(log_output)

    # Correlation ID should appear in log
    assert log_data['correlation_id'] == test_id
    assert log_data['message'] == "Test message"


def test_json_log_format():
    """Test logs are in JSON format"""
    # Set up logging with JSON formatter
    stream = StringIO()
    setup_logging(stream=stream, format='json')

    logger = logging.getLogger('test_json')

    # Set correlation ID
    set_correlation_id("json-test-123")

    # Log a message
    logger.info("JSON test message")

    # Get log output
    log_output = stream.getvalue().strip()

    # Should be valid JSON
    try:
        log_data = json.loads(log_output)
        assert 'timestamp' in log_data
        assert 'level' in log_data
        assert 'correlation_id' in log_data
        assert 'message' in log_data
        assert log_data['correlation_id'] == "json-test-123"
        assert log_data['message'] == "JSON test message"
    except json.JSONDecodeError:
        pytest.fail("Log output is not valid JSON")


def test_all_log_levels_include_correlation():
    """Test INFO, WARNING, ERROR all include correlation ID"""
    stream = StringIO()
    setup_logging(stream=stream, format='json')

    logger = logging.getLogger('test_levels')

    # Set correlation ID
    test_id = "level-test-456"
    set_correlation_id(test_id)

    # Log at different levels
    logger.info("Info message")
    logger.warning("Warning message")
    logger.error("Error message")

    # Get all log lines
    log_lines = stream.getvalue().strip().split('\n')

    # All lines should have correlation ID
    for line in log_lines:
        log_data = json.loads(line)
        assert log_data['correlation_id'] == test_id


def test_nested_function_calls_preserve_correlation():
    """Test correlation ID preserved across function calls"""
    test_id = "nested-test-789"
    set_correlation_id(test_id)

    def inner_function():
        return get_correlation_id()

    def outer_function():
        return inner_function()

    # Correlation ID should be preserved
    result = outer_function()
    assert result == test_id


@pytest.mark.asyncio
async def test_concurrent_requests_different_correlations():
    """Test concurrent requests have different correlation IDs"""
    results = []

    async def request_handler(request_id):
        # Set unique correlation ID
        correlation_id = f"request-{request_id}"
        set_correlation_id(correlation_id)

        # Simulate some async work
        await asyncio.sleep(0.01)

        # Get correlation ID after async work
        retrieved_id = get_correlation_id()
        results.append((request_id, retrieved_id))

    # Run 5 concurrent requests
    await asyncio.gather(
        request_handler(1),
        request_handler(2),
        request_handler(3),
        request_handler(4),
        request_handler(5)
    )

    # Each request should maintain its own correlation ID
    assert len(results) == 5
    for request_id, correlation_id in results:
        assert correlation_id == f"request-{request_id}"


def test_exception_includes_correlation():
    """Test exceptions include correlation ID in logs"""
    stream = StringIO()
    setup_logging(stream=stream, format='json')

    logger = logging.getLogger('test_exception')

    # Set correlation ID
    test_id = "exception-test-999"
    set_correlation_id(test_id)

    # Log an exception
    try:
        raise ValueError("Test exception")
    except ValueError:
        logger.exception("Exception occurred")

    # Get log output
    log_output = stream.getvalue().strip()
    log_data = json.loads(log_output)

    # Should have correlation ID
    assert log_data['correlation_id'] == test_id
    assert 'Exception occurred' in log_data['message']
    assert log_data['level'] == 'ERROR'


def test_log_aggregation_ready():
    """Test logs can be parsed by log aggregation tools"""
    stream = StringIO()
    setup_logging(stream=stream, format='json')

    logger = logging.getLogger('test_aggregation')

    # Set correlation ID
    set_correlation_id("aggregation-test")

    # Log multiple messages
    logger.info("Message 1", extra={'user_id': 'user123', 'action': 'login'})
    logger.info("Message 2", extra={'user_id': 'user123', 'action': 'query'})
    logger.warning("Message 3", extra={'user_id': 'user123', 'action': 'error'})

    # Get all log lines
    log_lines = stream.getvalue().strip().split('\n')

    # All lines should be valid JSON
    parsed_logs = []
    for line in log_lines:
        try:
            log_data = json.loads(line)
            parsed_logs.append(log_data)
        except json.JSONDecodeError:
            pytest.fail(f"Log line is not valid JSON: {line}")

    # Should have 3 logs
    assert len(parsed_logs) == 3

    # All should have required fields
    required_fields = ['timestamp', 'level', 'correlation_id', 'message']
    for log_data in parsed_logs:
        for field in required_fields:
            assert field in log_data, f"Missing field: {field}"

    # Extra fields should be preserved
    assert parsed_logs[0]['user_id'] == 'user123'
    assert parsed_logs[0]['action'] == 'login'


# Bonus test for middleware (will implement in next step)
@pytest.mark.asyncio
async def test_middleware_adds_correlation_to_request():
    """Test FastAPI middleware adds correlation ID to requests"""
    from fastapi import FastAPI, Request
    from fastapi.testclient import TestClient
    from src.utils.logging import correlation_middleware

    app = FastAPI()
    app.middleware("http")(correlation_middleware)

    @app.get("/test")
    async def test_endpoint(request: Request):
        # Get correlation ID from context
        correlation_id = get_correlation_id()
        return {"correlation_id": correlation_id}

    client = TestClient(app)

    # Request without correlation header
    response1 = client.get("/test")
    assert response1.status_code == 200
    assert 'correlation_id' in response1.json()
    assert response1.headers.get('X-Correlation-ID') is not None

    # Request with correlation header
    response2 = client.get("/test", headers={"X-Correlation-ID": "custom-123"})
    assert response2.status_code == 200
    assert response2.json()['correlation_id'] == "custom-123"
    assert response2.headers.get('X-Correlation-ID') == "custom-123"
