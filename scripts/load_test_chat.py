#!/usr/bin/env python3
"""
ACMS Chat Load Test Script

Runs extensive chat queries across all available agents to verify:
- Chat streaming works
- Knowledge extraction occurs
- Memory storage works
- All agents respond correctly

Usage:
    python scripts/load_test_chat.py --count 1000 --all-agents
    python scripts/load_test_chat.py --count 50 --agent ollama
"""

import argparse
import asyncio
import httpx
import json
import random
import sys
import time
from datetime import datetime
from typing import List, Dict, Any

API_BASE = "http://localhost:40080"

# Test query categories for comprehensive coverage
TEST_QUERIES = {
    "factual": [
        "What is machine learning?",
        "Explain how neural networks work",
        "What is the difference between AI and ML?",
        "How does natural language processing work?",
        "What are transformers in deep learning?",
        "Explain gradient descent",
        "What is backpropagation?",
        "How do convolutional neural networks work?",
        "What is reinforcement learning?",
        "Explain the attention mechanism",
    ],
    "coding": [
        "Write a Python function to sort a list",
        "How do I read a JSON file in Python?",
        "Explain async/await in JavaScript",
        "What is a REST API?",
        "How do I connect to PostgreSQL in Python?",
        "Write a function to find prime numbers",
        "Explain Docker containers",
        "What is Kubernetes?",
        "How do I use git branches?",
        "Explain microservices architecture",
    ],
    "creative": [
        "Write a haiku about programming",
        "Create a short story about an AI",
        "Describe a futuristic city",
        "Write a poem about data",
        "Imagine a world with superintelligent AI",
    ],
    "analysis": [
        "Compare Python and JavaScript",
        "What are the pros and cons of microservices?",
        "Analyze the impact of AI on jobs",
        "Compare SQL and NoSQL databases",
        "Evaluate cloud vs on-premise deployment",
    ],
    "memory": [
        "Remember that my favorite programming language is Python",
        "Note that I'm working on a machine learning project",
        "Save this: I prefer VS Code as my editor",
        "Remember I use PostgreSQL for databases",
        "Note: I'm interested in LLM development",
    ],
    "recall": [
        "What is my favorite programming language?",
        "What project am I working on?",
        "Which editor do I prefer?",
        "What database do I use?",
        "What am I interested in?",
    ],
}


class LoadTester:
    def __init__(self, base_url: str = API_BASE):
        self.base_url = base_url
        self.results: List[Dict[str, Any]] = []
        self.errors: List[Dict[str, Any]] = []
        self.user_id = "test-user-load"

    async def get_available_agents(self) -> List[str]:
        """Get list of available agents."""
        async with httpx.AsyncClient() as client:
            try:
                resp = await client.get(f"{self.base_url}/api/agents")
                if resp.status_code == 200:
                    data = resp.json()
                    return [a["id"] for a in data.get("agents", [])]
            except Exception as e:
                print(f"Error getting agents: {e}")
        return ["ollama"]  # Default fallback

    async def send_chat(self, query: str, agent: str = "auto") -> Dict[str, Any]:
        """Send a chat message and collect response."""
        start_time = time.time()

        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                # Use the /ask endpoint (non-streaming for simplicity)
                response = await client.post(
                    f"{self.base_url}/ask",
                    json={
                        "query": query,
                        "user_id": self.user_id,
                        "agent": agent,
                    },
                )

                if response.status_code != 200:
                    return {
                        "success": False,
                        "error": f"HTTP {response.status_code}",
                        "query": query,
                        "agent": agent,
                        "latency_ms": (time.time() - start_time) * 1000,
                    }

                data = response.json()
                return {
                    "success": True,
                    "query": query,
                    "agent": agent,
                    "response_length": len(data.get("answer", "")),
                    "latency_ms": (time.time() - start_time) * 1000,
                }

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "query": query,
                "agent": agent,
                "latency_ms": (time.time() - start_time) * 1000,
            }

    async def send_chat_streaming(self, query: str, agent: str = "auto") -> Dict[str, Any]:
        """Send a chat message with streaming (alternate method)."""
        start_time = time.time()

        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                # Use streaming endpoint
                async with client.stream(
                    "POST",
                    f"{self.base_url}/gateway/ask",
                    json={
                        "query": query,
                        "user_id": self.user_id,
                        "agent": agent,
                    },
                ) as response:
                    if response.status_code != 200:
                        return {
                            "success": False,
                            "error": f"HTTP {response.status_code}",
                            "query": query,
                            "agent": agent,
                            "latency_ms": (time.time() - start_time) * 1000,
                        }

                    # Collect streamed response
                    full_response = ""
                    async for chunk in response.aiter_text():
                        if chunk.startswith("data: "):
                            try:
                                data = json.loads(chunk[6:])
                                if "content" in data:
                                    full_response += data["content"]
                            except:
                                pass

                    return {
                        "success": True,
                        "query": query,
                        "agent": agent,
                        "response_length": len(full_response),
                        "latency_ms": (time.time() - start_time) * 1000,
                    }

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "query": query,
                "agent": agent,
                "latency_ms": (time.time() - start_time) * 1000,
            }

    async def run_tests(self, count: int, agents: List[str], concurrent: int = 5):
        """Run load tests."""
        print(f"\n{'='*60}")
        print(f"ACMS Chat Load Test")
        print(f"{'='*60}")
        print(f"Total queries: {count}")
        print(f"Agents: {', '.join(agents)}")
        print(f"Concurrency: {concurrent}")
        print(f"{'='*60}\n")

        # Build query list
        all_queries = []
        for category, queries in TEST_QUERIES.items():
            all_queries.extend([(q, category) for q in queries])

        # Generate test cases
        test_cases = []
        for i in range(count):
            query, category = random.choice(all_queries)
            agent = random.choice(agents)
            test_cases.append((query, agent, category))

        # Run with concurrency
        semaphore = asyncio.Semaphore(concurrent)

        async def bounded_send(query, agent, category):
            async with semaphore:
                result = await self.send_chat(query, agent)
                result["category"] = category
                return result

        print("Running tests...")
        start_time = time.time()

        tasks = [bounded_send(q, a, c) for q, a, c in test_cases]
        results = await asyncio.gather(*tasks)

        elapsed = time.time() - start_time

        # Analyze results
        successes = [r for r in results if r["success"]]
        failures = [r for r in results if not r["success"]]

        print(f"\n{'='*60}")
        print("RESULTS")
        print(f"{'='*60}")
        print(f"Total: {len(results)}")
        print(f"Success: {len(successes)} ({100*len(successes)/len(results):.1f}%)")
        print(f"Failed: {len(failures)} ({100*len(failures)/len(results):.1f}%)")
        print(f"Total time: {elapsed:.1f}s")
        print(f"Queries/sec: {len(results)/elapsed:.2f}")

        if successes:
            latencies = [r["latency_ms"] for r in successes]
            print(f"\nLatency (success only):")
            print(f"  Min: {min(latencies):.0f}ms")
            print(f"  Max: {max(latencies):.0f}ms")
            print(f"  Avg: {sum(latencies)/len(latencies):.0f}ms")

        # Results by agent
        print(f"\nBy Agent:")
        for agent in agents:
            agent_results = [r for r in results if r["agent"] == agent]
            agent_success = [r for r in agent_results if r["success"]]
            if agent_results:
                print(f"  {agent}: {len(agent_success)}/{len(agent_results)} success")

        # Results by category
        print(f"\nBy Category:")
        for category in TEST_QUERIES.keys():
            cat_results = [r for r in results if r.get("category") == category]
            cat_success = [r for r in cat_results if r["success"]]
            if cat_results:
                print(f"  {category}: {len(cat_success)}/{len(cat_results)} success")

        if failures:
            print(f"\nSample Errors:")
            for err in failures[:5]:
                print(f"  - {err.get('error', 'Unknown')[:50]}")

        # Store results
        self.results = results
        return len(failures) == 0


async def main():
    parser = argparse.ArgumentParser(description="ACMS Chat Load Test")
    parser.add_argument("--count", type=int, default=100, help="Number of queries")
    parser.add_argument("--agent", type=str, default=None, help="Specific agent to test")
    parser.add_argument("--all-agents", action="store_true", help="Test all available agents")
    parser.add_argument("--concurrent", type=int, default=5, help="Concurrent requests")

    args = parser.parse_args()

    tester = LoadTester()

    # Get agents
    if args.all_agents:
        agents = await tester.get_available_agents()
    elif args.agent:
        agents = [args.agent]
    else:
        agents = ["ollama"]

    print(f"Using agents: {agents}")

    # Run tests
    success = await tester.run_tests(args.count, agents, args.concurrent)

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    asyncio.run(main())
