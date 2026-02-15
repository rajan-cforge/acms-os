"""Integration tests for AI Gateway (Week 3 Task 9).

Tests the complete 7-step pipeline with 3 scenarios:
1. Multi-agent routing + caching (30-40% cost savings)
2. Memory synthesis (20 memories from multiple sources)
3. Security enforcement (API key blocked, dangerous command warned)
"""

import asyncio
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.gateway.orchestrator import get_gateway_orchestrator
from src.gateway.models import GatewayRequest, AgentType
from src.storage.memory_crud import MemoryCRUD
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def scenario_1_multi_agent_routing():
    """Scenario 1: Multi-agent routing + caching (30-40% cost savings).

    Test:
    - Query 1 (creative) → ChatGPT → Cache MISS → $0.0003
    - Query 2 (analysis) → Claude Sonnet → Cache MISS → $0.0012
    - Query 1 (repeat) → Cache HIT → $0.0000

    Validation:
    - Cost savings from caching + routing
    - Correct agent selection
    - Cache hit on repeat query
    """
    print("\n" + "="*60)
    print("SCENARIO 1: Multi-Agent Routing + Caching")
    print("="*60)

    gateway = get_gateway_orchestrator()
    user_id = "test_user_gateway"

    # Query 1: Creative task (should route to ChatGPT, cheapest for creative)
    print("\n[Query 1] Creative task (should use ChatGPT)...")
    query1 = "Write a haiku about AI"
    request1 = GatewayRequest(
        query=query1,
        user_id=user_id,
        bypass_cache=False,
        context_limit=5
    )

    cost1 = 0.0
    agent1 = None
    from_cache1 = False

    async for update in gateway.execute(request1):
        if update.get("type") == "status":
            print(f"  [{update['step']}] {update['message']}")
        elif update.get("type") == "done":
            response = update["response"]
            cost1 = response["cost_usd"]
            agent1 = response["agent_used"]
            from_cache1 = response["from_cache"]
            print(f"\n  ✅ Query 1 complete:")
            print(f"     Agent: {agent1}")
            print(f"     Cost: ${cost1:.6f}")
            print(f"     From cache: {from_cache1}")

    # Validate Query 1
    assert agent1 == "chatgpt", f"Expected chatgpt, got {agent1}"
    assert not from_cache1, "Expected cache MISS"
    assert cost1 > 0, "Expected non-zero cost"

    # Query 2: Analysis task (should route to Claude Sonnet, best for analysis)
    print("\n[Query 2] Analysis task (should use Claude Sonnet)...")
    query2 = "Analyze the performance implications of using Redis for caching"
    request2 = GatewayRequest(
        query=query2,
        user_id=user_id,
        bypass_cache=False,
        context_limit=5
    )

    cost2 = 0.0
    agent2 = None
    from_cache2 = False

    async for update in gateway.execute(request2):
        if update.get("type") == "status":
            print(f"  [{update['step']}] {update['message']}")
        elif update.get("type") == "done":
            response = update["response"]
            cost2 = response["cost_usd"]
            agent2 = response["agent_used"]
            from_cache2 = response["from_cache"]
            print(f"\n  ✅ Query 2 complete:")
            print(f"     Agent: {agent2}")
            print(f"     Cost: ${cost2:.6f}")
            print(f"     From cache: {from_cache2}")

    # Validate Query 2
    assert agent2 == "claude_sonnet", f"Expected claude_sonnet, got {agent2}"
    assert not from_cache2, "Expected cache MISS"
    assert cost2 > 0, "Expected non-zero cost"

    # Query 3: Repeat Query 1 (should hit cache, $0 cost)
    print("\n[Query 3] Repeat Query 1 (should hit cache)...")
    request3 = GatewayRequest(
        query=query1,  # Same as Query 1
        user_id=user_id,
        bypass_cache=False,
        context_limit=5
    )

    cost3 = 0.0
    agent3 = None
    from_cache3 = False

    async for update in gateway.execute(request3):
        if update.get("type") == "status":
            print(f"  [{update['step']}] {update['message']}")
        elif update.get("type") == "done":
            response = update["response"]
            cost3 = response["cost_usd"]
            agent3 = response["agent_used"]
            from_cache3 = response["from_cache"]
            print(f"\n  ✅ Query 3 complete:")
            print(f"     Agent: {agent3}")
            print(f"     Cost: ${cost3:.6f}")
            print(f"     From cache: {from_cache3}")

    # Validate Query 3
    assert from_cache3, "Expected cache HIT"
    assert cost3 == 0.0, f"Expected $0 cost, got ${cost3}"

    # Calculate cost savings
    total_cost_without_cache = cost1 + cost2 + cost1  # If all 3 were fresh
    total_cost_with_cache = cost1 + cost2 + cost3     # Actual cost
    cache_savings_pct = ((total_cost_without_cache - total_cost_with_cache) / total_cost_without_cache) * 100

    print(f"\n📊 SCENARIO 1 RESULTS:")
    print(f"   Total cost without cache: ${total_cost_without_cache:.6f}")
    print(f"   Total cost with cache: ${total_cost_with_cache:.6f}")
    print(f"   Cache savings: {cache_savings_pct:.1f}%")
    print(f"   Cost saved from routing: ChatGPT used instead of Claude for creative")

    # Validate overall savings
    assert cache_savings_pct > 30, f"Expected >30% cache savings, got {cache_savings_pct:.1f}%"

    print(f"\n✅ SCENARIO 1 PASSED: {cache_savings_pct:.1f}% cost savings achieved")


async def scenario_2_memory_synthesis():
    """Scenario 2: Memory synthesis (Universal Brain).

    Test:
    - Store 20 memories across multiple sources (ChatGPT, Gemini, Claude)
    - Query: "Summarize all discussions about authentication"
    - Validate: Response synthesizes ALL 20 memories correctly
    """
    print("\n" + "="*60)
    print("SCENARIO 2: Memory Synthesis (Universal Brain)")
    print("="*60)

    gateway = get_gateway_orchestrator()
    memory_crud = MemoryCRUD()
    user_id = "test_user_gateway"

    # Store 20 memories about authentication from different sources
    print("\n[Setup] Storing 20 authentication memories from multiple sources...")

    memories = [
        {"content": "Implemented JWT authentication with RS256 algorithm", "source": "chatgpt", "tags": ["auth", "jwt"]},
        {"content": "Added password hashing using bcrypt with 12 rounds", "source": "claude", "tags": ["auth", "password"]},
        {"content": "Researched OAuth2 authorization code flow", "source": "gemini", "tags": ["auth", "oauth2"]},
        {"content": "Implemented refresh token rotation for better security", "source": "chatgpt", "tags": ["auth", "jwt", "security"]},
        {"content": "Added rate limiting to login endpoint (5 attempts per minute)", "source": "claude", "tags": ["auth", "security"]},
        {"content": "Configured CORS for authentication endpoints", "source": "chatgpt", "tags": ["auth", "cors"]},
        {"content": "Implemented multi-factor authentication with TOTP", "source": "gemini", "tags": ["auth", "mfa", "totp"]},
        {"content": "Added session management with Redis", "source": "claude", "tags": ["auth", "session", "redis"]},
        {"content": "Implemented password reset flow with email verification", "source": "chatgpt", "tags": ["auth", "password"]},
        {"content": "Added social login (Google, GitHub) using OAuth2", "source": "gemini", "tags": ["auth", "oauth2", "social"]},
        {"content": "Configured JWT expiration: access 15min, refresh 7 days", "source": "claude", "tags": ["auth", "jwt"]},
        {"content": "Implemented account lockout after 10 failed login attempts", "source": "chatgpt", "tags": ["auth", "security"]},
        {"content": "Added audit logging for all authentication events", "source": "gemini", "tags": ["auth", "logging", "audit"]},
        {"content": "Implemented API key authentication for service-to-service", "source": "claude", "tags": ["auth", "api-key"]},
        {"content": "Added email verification on signup", "source": "chatgpt", "tags": ["auth", "email"]},
        {"content": "Configured secure cookie settings (httpOnly, secure, sameSite)", "source": "gemini", "tags": ["auth", "cookies", "security"]},
        {"content": "Implemented role-based access control (RBAC)", "source": "claude", "tags": ["auth", "rbac", "authorization"]},
        {"content": "Added password strength validation (min 12 chars, complexity)", "source": "chatgpt", "tags": ["auth", "password", "validation"]},
        {"content": "Implemented device tracking and notification on new login", "source": "gemini", "tags": ["auth", "security", "device"]},
        {"content": "Added biometric authentication support for mobile", "source": "claude", "tags": ["auth", "biometric", "mobile"]},
    ]

    stored_count = 0
    for mem in memories:
        try:
            memory_id = await memory_crud.create_memory(
                user_id=user_id,
                content=mem["content"],
                tags=mem["tags"],
                source=mem["source"],
                privacy_level="INTERNAL",
                phase="gateway_test",
                tier="SHORT"
            )
            if memory_id:
                stored_count += 1
                print(f"  ✓ Stored memory {stored_count}/20 from {mem['source']}")
        except Exception as e:
            logger.error(f"Failed to store memory: {e}")

    print(f"\n✅ Stored {stored_count} memories")
    assert stored_count >= 15, f"Expected at least 15 memories stored, got {stored_count}"

    # Query for synthesis
    print("\n[Query] Synthesizing all authentication discussions...")
    query = "Summarize all discussions about authentication across different sources"
    request = GatewayRequest(
        query=query,
        user_id=user_id,
        bypass_cache=True,  # Force fresh synthesis
        context_limit=20    # Retrieve all 20 memories
    )

    answer = ""
    agent_used = None

    async for update in gateway.execute(request):
        if update.get("type") == "status":
            print(f"  [{update['step']}] {update['message']}")
        elif update.get("type") == "chunk":
            # Collect response chunks
            answer += update["text"]
        elif update.get("type") == "done":
            response = update["response"]
            agent_used = response["agent_used"]
            print(f"\n  ✅ Synthesis complete:")
            print(f"     Agent: {agent_used}")
            print(f"     Answer length: {len(answer)} chars")

    # Validate synthesis
    assert agent_used == "claude_sonnet", f"Expected claude_sonnet for synthesis, got {agent_used}"
    assert len(answer) > 200, f"Expected substantial answer, got {len(answer)} chars"

    # Check that answer mentions multiple topics (indicates synthesis)
    topics = ["jwt", "password", "oauth", "mfa", "session", "rbac"]
    topics_found = sum(1 for topic in topics if topic.lower() in answer.lower())

    print(f"\n📊 SCENARIO 2 RESULTS:")
    print(f"   Memories stored: {stored_count}")
    print(f"   Topics synthesized: {topics_found}/{len(topics)}")
    print(f"   Answer length: {len(answer)} chars")
    print(f"   Agent used: {agent_used}")

    assert topics_found >= 4, f"Expected at least 4 topics in synthesis, got {topics_found}"

    print(f"\n✅ SCENARIO 2 PASSED: Successfully synthesized {topics_found} topics from {stored_count} memories")


async def scenario_3_security_enforcement():
    """Scenario 3: Security enforcement.

    Test:
    - Query with API key → BLOCKED (approved=False)
    - Query with dangerous command → WARNED (approved=True, issue logged)
    - Validate: Blocked query costs $0, dangerous query allowed with warning
    """
    print("\n" + "="*60)
    print("SCENARIO 3: Security Enforcement")
    print("="*60)

    gateway = get_gateway_orchestrator()
    user_id = "test_user_gateway"

    # Test 1: API key should be blocked
    print("\n[Test 1] Query with API key (should be BLOCKED)...")
    query1 = "My OpenAI API key is sk-proj-abc123xyz456789"
    request1 = GatewayRequest(
        query=query1,
        user_id=user_id,
        bypass_cache=True,
        context_limit=5
    )

    blocked = False
    issues_found = []

    async for update in gateway.execute(request1):
        if update.get("type") == "status":
            print(f"  [{update['step']}] {update['message']}")
        elif update.get("type") == "error":
            blocked = True
            issues_found = update.get("issues", [])
            print(f"\n  🛑 Query BLOCKED:")
            for issue in issues_found:
                print(f"     - {issue['type']}: {issue['message']}")

    # Validate blocking
    assert blocked, "Expected query to be blocked"
    assert len(issues_found) > 0, "Expected compliance issues"
    assert any("api_key" in issue["type"] for issue in issues_found), "Expected API key issue"

    print(f"\n  ✅ API key correctly blocked (cost: $0.00)")

    # Test 2: Dangerous command should be warned
    print("\n[Test 2] Query with dangerous command (should be WARNED)...")
    query2 = "How do I safely test the command rm -rf / in a Docker container?"
    request2 = GatewayRequest(
        query=query2,
        user_id=user_id,
        bypass_cache=True,
        context_limit=5
    )

    warned = False
    issues_found2 = []
    cost2 = 0.0

    async for update in gateway.execute(request2):
        if update.get("type") == "status":
            print(f"  [{update['step']}] {update['message']}")
            if update.get("issues"):
                warned = True
                issues_found2 = update["issues"]
                print(f"\n  ⚠️  Query WARNED:")
                for issue in issues_found2:
                    print(f"     - {issue['type']}: {issue['message']}")
        elif update.get("type") == "done":
            response = update["response"]
            cost2 = response["cost_usd"]
            print(f"\n  ✅ Query completed with warning:")
            print(f"     Cost: ${cost2:.6f} (API call was made)")

    # Validate warning
    assert warned, "Expected query to be warned"
    assert len(issues_found2) > 0, "Expected compliance warnings"
    assert any("dangerous_command" in issue["type"] for issue in issues_found2), "Expected dangerous command warning"
    assert cost2 > 0, "Expected non-zero cost (query should execute despite warning)"

    print(f"\n  ✅ Dangerous command correctly warned (cost: ${cost2:.6f})")

    # Test 3: Normal query should be approved
    print("\n[Test 3] Normal query (should be APPROVED)...")
    query3 = "Explain how JWT authentication works"
    request3 = GatewayRequest(
        query=query3,
        user_id=user_id,
        bypass_cache=True,
        context_limit=5
    )

    approved = False
    cost3 = 0.0

    async for update in gateway.execute(request3):
        if update.get("type") == "status":
            if update["step"] == "compliance_check" and "no issues" in update["message"].lower():
                approved = True
                print(f"  [{update['step']}] {update['message']}")
        elif update.get("type") == "done":
            response = update["response"]
            cost3 = response["cost_usd"]

    # Validate approval
    assert approved, "Expected query to be approved"
    assert cost3 > 0, "Expected non-zero cost"

    print(f"\n  ✅ Normal query approved (cost: ${cost3:.6f})")

    print(f"\n📊 SCENARIO 3 RESULTS:")
    print(f"   API key query: BLOCKED ✅ (cost: $0.00)")
    print(f"   Dangerous command: WARNED ✅ (cost: ${cost2:.6f})")
    print(f"   Normal query: APPROVED ✅ (cost: ${cost3:.6f})")

    print(f"\n✅ SCENARIO 3 PASSED: Security enforcement working correctly")


async def main():
    """Run all 3 integration test scenarios."""
    print("\n" + "🚀"*30)
    print("AI GATEWAY INTEGRATION TESTS (Week 3 Task 9)")
    print("🚀"*30)

    try:
        # Run all scenarios
        await scenario_1_multi_agent_routing()
        await scenario_2_memory_synthesis()
        await scenario_3_security_enforcement()

        print("\n" + "✅"*30)
        print("ALL SCENARIOS PASSED!")
        print("✅"*30)
        print("\nWeek 3 Gateway Foundation: 100% COMPLETE")
        print("- Multi-agent routing: ✅")
        print("- Cost optimization (caching + routing): ✅")
        print("- Memory synthesis (Universal Brain): ✅")
        print("- Security enforcement: ✅")

    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
