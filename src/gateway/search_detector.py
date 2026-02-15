"""
Search Detection Module

Determines if a user query requires web search for current information.
"""
import re
from typing import List, Tuple


class SearchDetector:
    """
    Intelligent detection of queries that need web search

    Detection criteria:
    1. Temporal keywords (today, recent, latest, current)
    2. Dynamic topics (stock market, weather, news, sports scores)
    3. Explicit search requests ("search for", "look up")
    4. Year references (2024, 2025)
    """

    # Keywords indicating current/recent information needed
    TEMPORAL_KEYWORDS = [
        'today', 'yesterday', 'this week', 'this month', 'this year',
        'recent', 'recently', 'latest', 'current', 'currently',
        'now', 'right now', 'just', 'new', 'newest',
        'upcoming', 'tomorrow', 'next week'
    ]

    # Topics that change frequently and need fresh data
    DYNAMIC_TOPICS = [
        # Finance
        'stock market', 'stock price', 'crypto', 'bitcoin', 'ethereum',
        'exchange rate', 'dow jones', 's&p 500', 'nasdaq', 'trading',
        'shares', 'market', 'cryptocurrency',

        # News & Events
        'news', 'election', 'vote', 'winner', 'score', 'game',
        'tournament', 'championship', 'won', 'lost', 'defeat',
        'super bowl', 'world cup', 'olympics',

        # Weather
        'weather', 'forecast', 'temperature', 'rain', 'snow', 'storm',

        # Technology
        'release', 'launch', 'announcement', 'update', 'version',

        # General current events
        'happening', 'occurred', 'incident', 'breaking', 'live'
    ]

    # Explicit search request phrases
    SEARCH_PHRASES = [
        'search for', 'look up', 'find information', 'google',
        'search about', 'find out', 'tell me about recent',
        'what happened', 'what\'s going on', 'what are the',
        'who won', 'what is the price', 'how much is',
        # Research and company queries
        'research', 'research on', 'do research', 'look into',
        'what does', 'what do they do', 'who are they',
        'tell me about', 'information about', 'info about',
        # Company/product queries
        '.ai', '.io', '.com', 'startup', 'company', 'these guys'
    ]

    # Year patterns (2024-2039)
    YEAR_PATTERN = re.compile(r'\b(202[4-9]|203[0-9])\b')

    # Internal/personal context keywords (exclude from web search)
    INTERNAL_KEYWORDS = [
        'acms', 'acms project', 'my project', 'our project', 'this project',
        'my system', 'our system', 'this system', 'my code', 'our code',
        'my implementation', 'our implementation', 'what we built',
        'what i built', 'my work', 'our work', 'my memories', 'my data',
        'adaptive context memory system', 'memory system',
        # Knowledge/conversation queries - prioritize internal memory
        'topics we discussed', 'topics discussed', 'we have discussed',
        'we discussed', 'our conversations', 'my conversations',
        'you know about', 'what do you know', 'summarize topics',
        'all the topics', 'from memories', 'from memory', 'knowledge base'
    ]

    @classmethod
    def needs_search(cls, query: str) -> Tuple[bool, str]:
        """
        Determine if query requires web search

        Args:
            query: User's query text

        Returns:
            (needs_search: bool, reason: str)
        """
        query_lower = query.lower()

        # 0. EXCLUDE internal/personal context queries from web search
        for keyword in cls.INTERNAL_KEYWORDS:
            if keyword in query_lower:
                return False, f"internal_context: {keyword}"

        # 1. Check for explicit search requests
        for phrase in cls.SEARCH_PHRASES:
            if phrase in query_lower:
                return True, f"explicit_search_request: {phrase}"

        # 2. Check for temporal keywords (use word boundaries to avoid "know" matching "now")
        temporal_matches = []
        for kw in cls.TEMPORAL_KEYWORDS:
            # Use regex word boundary to match whole words only
            pattern = r'\b' + re.escape(kw) + r'\b'
            if re.search(pattern, query_lower):
                temporal_matches.append(kw)
        if temporal_matches:
            return True, f"temporal_keyword: {temporal_matches[0]}"

        # 3. Check for dynamic topics
        topic_matches = [topic for topic in cls.DYNAMIC_TOPICS if topic in query_lower]
        if topic_matches:
            return True, f"dynamic_topic: {topic_matches[0]}"

        # 4. Check for year references (2024, 2025, etc.)
        if cls.YEAR_PATTERN.search(query):
            return True, "year_reference"

        return False, "no_search_needed"

    @classmethod
    def extract_search_query(cls, query: str) -> str:
        """
        Extract optimized search query from user's question

        Removes question words and focuses on key terms.

        Example:
            "What is the stock market doing today?" → "stock market today"
        """
        # Remove common question prefixes
        query_cleaned = re.sub(
            r'^(what|who|when|where|why|how|is|are|was|were|can|could|tell me|show me|please)\s+',
            '',
            query.lower(),
            flags=re.IGNORECASE
        )

        # Remove trailing question marks
        query_cleaned = query_cleaned.rstrip('?')

        return query_cleaned.strip()


# Quick test function
if __name__ == "__main__":
    test_queries = [
        "What is the stock market doing today?",
        "Tell me about Python programming",
        "Who won the Super Bowl in 2024?",
        "Explain quantum physics",
        "What's the weather forecast for tomorrow?",
        "Latest news about AI",
        "What is the price of Bitcoin?",
        "How do I learn machine learning?"
    ]

    for query in test_queries:
        needs_search, reason = SearchDetector.needs_search(query)
        print(f"Query: {query}")
        print(f"Needs search: {needs_search} ({reason})")
        if needs_search:
            print(f"Optimized: {SearchDetector.extract_search_query(query)}")
        print()
