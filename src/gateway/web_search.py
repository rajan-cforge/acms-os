"""
Web Search Service

Handles web search API calls and result formatting using Tavily.
"""
import hashlib
import json
import logging
import os
from typing import List, Dict, Optional
from datetime import datetime, timedelta

from tavily import TavilyClient

logger = logging.getLogger(__name__)


class SearchResult:
    """Structured search result"""

    def __init__(self, title: str, url: str, content: str, score: float = 1.0):
        self.title = title
        self.url = url
        self.content = content
        self.score = score

    def to_dict(self) -> dict:
        return {
            "title": self.title,
            "url": self.url,
            "content": self.content,
            "score": self.score
        }


class WebSearchService:
    """
    Web search service with caching and error handling
    """

    def __init__(self):
        self.client = None
        self.cache = {}  # Simple in-memory cache
        self.enabled = os.getenv("ENABLE_WEB_SEARCH", "true").lower() == "true"
        self.max_results = int(os.getenv("SEARCH_MAX_RESULTS", "5"))
        self.cache_ttl_seconds = int(os.getenv("SEARCH_CACHE_TTL_SECONDS", "3600"))

        # Initialize Tavily client
        api_key = os.getenv("TAVILY_API_KEY", "").strip('"').strip("'")
        if api_key:
            try:
                self.client = TavilyClient(api_key=api_key)
                logger.info("✅ Tavily search client initialized")
            except Exception as e:
                logger.error(f"❌ Failed to initialize Tavily client: {e}")
        else:
            logger.warning("⚠️ TAVILY_API_KEY not set - Web search disabled")

    def _get_cache_key(self, query: str) -> str:
        """Generate cache key from query"""
        return hashlib.md5(query.lower().encode()).hexdigest()

    def _get_cached_results(self, query: str) -> Optional[List[SearchResult]]:
        """Get cached search results if still fresh"""
        cache_key = self._get_cache_key(query)

        if cache_key in self.cache:
            cached_data = self.cache[cache_key]
            cached_time = cached_data['timestamp']
            ttl = timedelta(seconds=self.cache_ttl_seconds)

            if datetime.now() - cached_time < ttl:
                logger.info(f"✅ Cache HIT for query: {query}")
                return cached_data['results']

        return None

    def _cache_results(self, query: str, results: List[SearchResult]):
        """Cache search results"""
        cache_key = self._get_cache_key(query)
        self.cache[cache_key] = {
            'timestamp': datetime.now(),
            'results': results
        }

    async def search(self, query: str, max_results: Optional[int] = None) -> List[SearchResult]:
        """
        Perform web search

        Args:
            query: Search query
            max_results: Maximum number of results (default from settings)

        Returns:
            List of SearchResult objects
        """
        if not self.enabled:
            logger.warning("⚠️ Web search is disabled")
            return []

        if not self.client:
            logger.error("❌ Tavily client not initialized")
            return []

        # Check cache first
        cached = self._get_cached_results(query)
        if cached:
            return cached

        max_results = max_results or self.max_results

        try:
            logger.info(f"🔍 Searching: {query}")

            # Call Tavily API (synchronous)
            response = self.client.search(
                query=query,
                search_depth="advanced",
                max_results=max_results,
                include_answer=False,  # We'll synthesize our own
                include_raw_content=False  # Don't need full HTML
            )

            # Parse results
            results = []
            for item in response.get('results', []):
                result = SearchResult(
                    title=item.get('title', ''),
                    url=item.get('url', ''),
                    content=item.get('content', ''),
                    score=item.get('score', 1.0)
                )
                results.append(result)

            logger.info(f"✅ Found {len(results)} results for: {query}")

            # Cache results
            self._cache_results(query, results)

            return results

        except Exception as e:
            logger.error(f"❌ Search failed: {e}")
            return []

    def format_results_for_llm(self, results: List[SearchResult]) -> str:
        """
        Format search results as context for LLM

        Returns formatted string with numbered sources
        """
        if not results:
            return "No search results found."

        formatted = "# Web Search Results\n\n"

        for i, result in enumerate(results, 1):
            formatted += f"## Source {i}: {result.title}\n"
            formatted += f"URL: {result.url}\n"
            formatted += f"{result.content}\n\n"

        return formatted


# Global instance
web_search_service = WebSearchService()
