#!/usr/bin/env python3
"""
Baseline Metrics Script for ACMS Phase 2
Measures current performance BEFORE query augmentation implementation.

Usage:
    python scripts/baseline_metrics.py --queries 100
    python scripts/baseline_metrics.py --queries 1000 --output baseline_2025-11-10.json
"""

import argparse
import asyncio
import json
import time
from datetime import datetime
from typing import Dict, List
import requests
import statistics

# Sample queries for testing (diverse types)
SAMPLE_QUERIES = [
    # Factual queries
    "What is ACMS?",
    "How does semantic caching work?",
    "What is the database architecture?",
    "What databases does ACMS use?",
    "What is Weaviate?",

    # Technical queries
    "How do I create a memory?",
    "How does privacy detection work?",
    "What is the 7-step gateway pipeline?",
    "How does the orchestrator work?",
    "What is the UniversalSearchEngine?",

    # Complex queries
    "How does ACMS handle privacy and security?",
    "What are the different memory tiers and when should I use them?",
    "How does ACMS integrate with Claude, ChatGPT, and Gemini?",

    # Vague queries (should improve with augmentation)
    "tell me about the database",
    "how does caching work",
    "what about security",

    # Code-related queries
    "How do I implement a new agent?",
    "What files contain the gateway logic?",
    "How do I add a new privacy level?",

    # Troubleshooting queries
    "Why is my query slow?",
    "How do I debug memory retrieval?",
    "What logs should I check?",
]


class BaselineMetrics:
    """Collect baseline performance metrics before Phase 2."""

    def __init__(self, api_url: str = "http://localhost:40080"):
        self.api_url = api_url
        self.results = []

    def search_memory(self, query: str, user_id: str = "default") -> Dict:
        """Execute a memory search and measure performance."""
        start_time = time.time()

        try:
            response = requests.post(
                f"{self.api_url}/search",
                json={
                    "query": query,
                    "user_id": user_id,
                    "limit": 10
                },
                timeout=30
            )

            elapsed_ms = (time.time() - start_time) * 1000

            if response.status_code == 200:
                data = response.json()
                return {
                    "query": query,
                    "success": True,
                    "status_code": 200,
                    "latency_ms": elapsed_ms,
                    "results_count": len(data.get("results", [])),
                    "avg_relevance": statistics.mean(
                        [r.get("crs_score", 0) for r in data.get("results", [])]
                    ) if data.get("results") else 0,
                    "cache_hit": False,  # Can't determine from /search endpoint
                }
            else:
                return {
                    "query": query,
                    "success": False,
                    "status_code": response.status_code,
                    "latency_ms": elapsed_ms,
                    "error": response.text[:200]
                }

        except Exception as e:
            elapsed_ms = (time.time() - start_time) * 1000
            return {
                "query": query,
                "success": False,
                "status_code": 0,
                "latency_ms": elapsed_ms,
                "error": str(e)
            }

    def ask_query(self, query: str, user_id: str = "default") -> Dict:
        """Execute an /ask query (uses cache and full pipeline)."""
        start_time = time.time()

        try:
            response = requests.post(
                f"{self.api_url}/ask",
                json={
                    "query": query,
                    "user_id": user_id,
                    "bypass_cache": False
                },
                timeout=60
            )

            elapsed_ms = (time.time() - start_time) * 1000

            if response.status_code == 200:
                data = response.json()
                return {
                    "query": query,
                    "success": True,
                    "status_code": 200,
                    "latency_ms": elapsed_ms,
                    "cache_hit": data.get("cache_hit", False),
                    "sources_count": len(data.get("sources", [])),
                    "answer_length": len(data.get("answer", "")),
                    "agent_used": data.get("agent_used"),
                }
            else:
                return {
                    "query": query,
                    "success": False,
                    "status_code": response.status_code,
                    "latency_ms": elapsed_ms,
                    "error": response.text[:200]
                }

        except Exception as e:
            elapsed_ms = (time.time() - start_time) * 1000
            return {
                "query": query,
                "success": False,
                "status_code": 0,
                "latency_ms": elapsed_ms,
                "error": str(e)
            }

    def run_benchmark(self, num_queries: int, endpoint: str = "search") -> Dict:
        """Run benchmark with specified number of queries."""
        print(f"Running baseline metrics: {num_queries} queries via /{endpoint}")
        print("=" * 60)

        # Generate query list (cycle through samples)
        queries = []
        for i in range(num_queries):
            queries.append(SAMPLE_QUERIES[i % len(SAMPLE_QUERIES)])

        # Execute queries
        for i, query in enumerate(queries):
            if endpoint == "search":
                result = self.search_memory(query)
            else:
                result = self.ask_query(query)

            self.results.append(result)

            # Progress indicator
            if (i + 1) % 10 == 0:
                print(f"Progress: {i + 1}/{num_queries} queries completed")

        # Calculate statistics
        return self.calculate_stats()

    def calculate_stats(self) -> Dict:
        """Calculate aggregate statistics from results."""
        successful_results = [r for r in self.results if r["success"]]

        if not successful_results:
            return {
                "error": "No successful queries",
                "total_queries": len(self.results),
                "successful_queries": 0
            }

        latencies = [r["latency_ms"] for r in successful_results]

        stats = {
            "timestamp": datetime.now().isoformat(),
            "total_queries": len(self.results),
            "successful_queries": len(successful_results),
            "failed_queries": len(self.results) - len(successful_results),
            "success_rate": len(successful_results) / len(self.results) * 100,

            "latency_stats": {
                "avg_ms": statistics.mean(latencies),
                "median_ms": statistics.median(latencies),
                "min_ms": min(latencies),
                "max_ms": max(latencies),
                "p95_ms": sorted(latencies)[int(len(latencies) * 0.95)] if len(latencies) > 20 else max(latencies),
            }
        }

        # Cache hit rate (if available from /ask endpoint)
        cache_hits = [r for r in successful_results if r.get("cache_hit", False)]
        if any("cache_hit" in r for r in successful_results):
            stats["cache_hit_rate"] = len(cache_hits) / len(successful_results) * 100

        # Results count (from /search endpoint)
        if any("results_count" in r for r in successful_results):
            results_counts = [r["results_count"] for r in successful_results if "results_count" in r]
            stats["avg_results_returned"] = statistics.mean(results_counts)

            relevance_scores = [r["avg_relevance"] for r in successful_results if "avg_relevance" in r and r["avg_relevance"] > 0]
            if relevance_scores:
                stats["avg_relevance_score"] = statistics.mean(relevance_scores)

        return stats


def main():
    parser = argparse.ArgumentParser(description="Baseline metrics for ACMS Phase 2")
    parser.add_argument("--queries", type=int, default=100, help="Number of queries to run (default: 100)")
    parser.add_argument("--endpoint", choices=["search", "ask"], default="search", help="Endpoint to test (default: search)")
    parser.add_argument("--output", type=str, help="Output file (JSON format)")
    parser.add_argument("--api-url", type=str, default="http://localhost:40080", help="API base URL")

    args = parser.parse_args()

    # Check API is reachable
    try:
        response = requests.get(f"{args.api_url}/health", timeout=5)
        if response.status_code != 200:
            print(f"ERROR: API health check failed: {response.status_code}")
            return 1
        print(f"✅ API is healthy at {args.api_url}")
    except Exception as e:
        print(f"ERROR: Cannot reach API at {args.api_url}: {e}")
        return 1

    # Run benchmark
    metrics = BaselineMetrics(api_url=args.api_url)
    stats = metrics.run_benchmark(num_queries=args.queries, endpoint=args.endpoint)

    # Print results
    print("\n" + "=" * 60)
    print("BASELINE METRICS RESULTS")
    print("=" * 60)
    print(json.dumps(stats, indent=2))

    # Save to file if specified
    if args.output:
        with open(args.output, 'w') as f:
            json.dump({
                "stats": stats,
                "all_results": metrics.results
            }, f, indent=2)
        print(f"\n✅ Results saved to {args.output}")

    # Summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"Total queries: {stats['total_queries']}")
    print(f"Success rate: {stats['success_rate']:.1f}%")
    print(f"Avg latency: {stats['latency_stats']['avg_ms']:.1f}ms")
    print(f"Median latency: {stats['latency_stats']['median_ms']:.1f}ms")
    print(f"P95 latency: {stats['latency_stats']['p95_ms']:.1f}ms")

    if "cache_hit_rate" in stats:
        print(f"Cache hit rate: {stats['cache_hit_rate']:.1f}%")

    if "avg_results_returned" in stats:
        print(f"Avg results returned: {stats['avg_results_returned']:.1f}")

    if "avg_relevance_score" in stats:
        print(f"Avg relevance score: {stats['avg_relevance_score']:.3f}")

    print("\n💡 Save these baseline metrics to compare against Phase 2 results!")
    print(f"   Expected improvements: Cache hit rate +10%, Retrieval precision +30-50%")

    return 0


if __name__ == "__main__":
    exit(main())
