"""Intent classification using rule-based + keyword matching.

Classifies user queries into intent categories for agent routing.
Target: 80%+ accuracy on common query patterns.
"""

import re
import logging
from typing import Dict, List, Tuple
from src.gateway.models import IntentType

logger = logging.getLogger(__name__)


# Intent classification rules with keywords, patterns, and weights
INTENT_RULES = {
    IntentType.TERMINAL_COMMAND: {
        "keywords": [
            "run", "execute", "install", "docker", "pytest", "npm",
            "git", "curl", "bash", "shell", "command", "terminal",
            "start server", "kill process", "check port", "ls", "cd"
        ],
        "patterns": [
            r"^(run|execute|install|start|stop|kill)\s",
            r"\b(docker|pytest|npm|git|curl|bash)\b",
            r"how to run",
            r"execute.*command"
        ],
        "weight": 1.5  # Higher weight for exact matches
    },

    IntentType.CODE_GENERATION: {
        "keywords": [
            "write code", "generate code", "create function",
            "create class", "add method", "refactor", "code for",
            "write a function", "write a class", "build a function", "create a class"
        ],
        "patterns": [
            r"(write|generate|create)\s+(a\s+)?(function|class|method|code)",
            r"(write|give\s+me|show\s+me)\s+code",
            r"code\s+(for|to|that)",
            r"build.*function"
        ],
        "weight": 1.3
    },

    IntentType.FILE_OPERATION: {
        "keywords": [
            "read file", "write file", "edit file", "create file",
            "delete file", "move file", "copy file", "file content",
            "show file", "update file", "modify file", "open file"
        ],
        "patterns": [
            r"(read|write|edit|create|delete|move|copy|show|update|modify|open)\s+(the\s+)?(file|.*\.(py|js|json|yaml|yml|txt|md|csv))",
            r"file.*content",
            r"what's in.*file",
            r"read\s+.*\.(py|js|json|yaml|yml|txt|md|csv)"
        ],
        "weight": 1.4
    },

    IntentType.ANALYSIS: {
        "keywords": [
            "analyze", "explain", "what is", "how does", "why does",
            "compare", "evaluate", "review", "assess", "debug",
            "troubleshoot", "what's wrong", "error in", "bug in",
            # Added architectural/documentation keywords
            "architecture", "details", "overview", "system", "design",
            "structure", "documentation", "use case", "use cases",
            "end to end", "full details", "tell me about", "describe",
            "components", "workflow", "process", "implementation",
            # Added explanatory/educational keywords
            "tell me more", "tell me how", "how could i", "how can i",
            "how should i", "help me understand", "walk me through"
        ],
        "patterns": [
            r"(analyze|explain|compare|evaluate|review|assess|debug)",
            r"(what|how|why)\s+(is|does|did|can)",
            r"what's\s+(wrong|the\s+issue|happening)",
            r"error.*in",
            r"bug.*in",
            # Added patterns for architectural queries
            r"(give|tell)\s+me.*(details|overview|about)",
            r"(architecture|design|structure|system)",
            r"end\s+to\s+end",
            r"(describe|explain|show).*(architecture|system|design)",
            # Added patterns for explanatory queries
            r"tell\s+me\s+(more|how|about)",
            r"how\s+(could|can|should)\s+i\s+(implement|use|apply|integrate)",
            r"help\s+me\s+(understand|with)",
            r"walk\s+me\s+through"
        ],
        "weight": 1.4  # Increased weight to prioritize explanatory queries over code gen
    },

    IntentType.CREATIVE: {
        "keywords": [
            "write a story", "write a poem", "creative", "brainstorm",
            "generate ideas", "suggest names", "come up with",
            "write an article", "write a blog", "draft an email",
            "haiku", "sonnet", "limerick", "poetry", "write verse",
            "write a haiku", "write a sonnet", "write a limerick"
        ],
        "patterns": [
            r"write\s+(a\s+)?(story|poem|article|blog|email|haiku|sonnet|limerick|verse)",
            r"(creative|brainstorm|generate\s+ideas)",
            r"come\s+up\s+with",
            r"suggest.*names",
            r"\b(haiku|sonnet|limerick|poetry)\b"
        ],
        "weight": 1.4  # Higher than CODE_GENERATION (1.3) to prioritize creative writing
    },

    IntentType.RESEARCH: {
        "keywords": [
            "research", "find information", "search for", "lookup",
            "what's the latest", "tell me about", "learn about",
            "documentation for", "best practices", "tutorial",
            # Real-time / temporal queries (needs web search)
            "today", "right now", "currently", "current", "at the moment",
            "what time is it", "what time", "time is it", "current time",
            "markets today", "news today", "latest news", "breaking news",
            "happening now", "live", "real-time", "up to date"
        ],
        "patterns": [
            r"(research|find|search|lookup)\s+",
            r"what's\s+the\s+latest",
            r"(tell\s+me|learn)\s+about",
            r"documentation\s+for",
            r"best\s+practices",
            r"tutorial.*for",
            # Real-time patterns
            r"(what|how).*(today|right\s+now|currently|at\s+the\s+moment)",
            r"what\s+time(\s+is\s+it)?",
            r"(current|latest|breaking)\s+(news|time|markets?|price)",
            r"(happening|going\s+on)\s+(now|today)",
            r"(live|real-time|up\s+to\s+date)"
        ],
        "weight": 1.3  # Higher weight to prioritize over ANALYSIS for real-time queries
    },

    IntentType.MEMORY_QUERY: {
        "keywords": [
            "remember", "recall", "what did I", "previous work",
            "last time", "history of", "past", "earlier",
            "show me what", "what have I", "retrieve", "yesterday",
            "last week", "before", "work on",
            # Added: Knowledge/memory/topics queries
            "memories", "memory", "topics", "knowledge", "discussed",
            "talked about", "conversations", "we discussed", "you know about"
        ],
        "patterns": [
            r"(remember|recall|retrieve)\s+",
            r"what\s+(did\s+I|have\s+I)",
            r"(previous|past|earlier)\s+work",
            r"(last\s+time|yesterday|last\s+week)",
            r"history\s+of",
            r"(what|show).*work.*on.*(yesterday|last\s+week|before)",
            # Added: Patterns for knowledge/topic queries
            r"(from|in)\s+(my\s+)?(memories|memory|knowledge)",  # "from my memories"
            r"(summarize|summary|list).*(topics|knowledge|memories)",  # "summarize topics"
            r"(topics|things).*(discussed|talked|know)",  # "topics we discussed"
            r"what\s+(do\s+)?you\s+know\s+about",  # "what do you know about"
            r"(all|the)\s+topics"  # "all topics", "the topics"
        ],
        "weight": 1.5
    },

    IntentType.EMAIL: {
        "keywords": [
            # NOTE: Removed "from" - too generic, causes false positives
            # "from my emails" was being parsed as "emails from sender=my"
            "email", "emails", "inbox", "unread", "mail", "gmail",
            "sender", "senders", "received",
            "action items", "deadlines", "email insights",
            "priority emails", "important emails", "newsletters",
            "mailing list", "email summary"
        ],
        "patterns": [
            r"\b(email|emails|inbox|gmail|mail)\b",
            r"(unread|priority|important)\s+(email|mail|message)",
            # Specific patterns for email content queries
            r"(from|in)\s+(my\s+)?(email|emails|inbox|mail)",  # "from my emails" → email intent
            r"email\s+(from|to|about|insight|summary)",
            r"(show|list|get)\s+(my\s+)?(email|inbox|mail)",
            r"who\s+(sent|emailed)",
            r"(action\s+item|deadline).*email",
            r"email.*(insight|summary|digest)",
            r"(summarize|summary\s+of).*email",
            r"(subscription|recurring).*email",  # subscription queries
            r"email.*(subscription|recurring)"
        ],
        "weight": 1.6  # High weight to prioritize email queries
    },

    IntentType.FINANCE: {
        "keywords": [
            "portfolio", "holdings", "stocks", "investments",
            "financial", "finance", "money", "account balance",
            "transactions", "trades", "positions", "securities",
            "constitution", "rules", "allocation", "plaid",
            "brokerage", "etrade", "fidelity", "wells fargo"
        ],
        "patterns": [
            r"\b(portfolio|holdings|investments|stocks)\b",
            r"(my\s+)?(financial|finance)\s+(data|info|summary)",
            r"(show|get|what).*(portfolio|holdings|positions)",
            r"(constitution|rules|allocation)",
            r"(transaction|trade|buy|sell)\s+history",
            r"(account|investment)\s+(balance|value)",
            r"how\s+(is|are)\s+my\s+(portfolio|investments)"
        ],
        "weight": 1.6  # High weight to prioritize finance queries
    }
}


class IntentClassifier:
    """Rule-based intent classifier using keywords and regex patterns."""

    def __init__(self):
        """Initialize the intent classifier."""
        self.rules = INTENT_RULES
        logger.info("IntentClassifier initialized with %d intent types", len(self.rules))

    def classify(self, query: str) -> Tuple[IntentType, float]:
        """Classify a query into an intent type.

        Args:
            query: User query string

        Returns:
            Tuple of (IntentType, confidence_score)

        Algorithm:
            1. Score each intent based on keyword/pattern matches
            2. Apply weight multipliers
            3. Return highest scoring intent
            4. Default to ANALYSIS if no strong matches
        """
        query_lower = query.lower().strip()

        # Score each intent
        scores: Dict[IntentType, float] = {}

        for intent_type, rules in self.rules.items():
            score = 0.0

            # Keyword matching
            for keyword in rules["keywords"]:
                if keyword.lower() in query_lower:
                    score += 1.0

            # Pattern matching
            for pattern in rules["patterns"]:
                if re.search(pattern, query_lower):
                    score += 2.0  # Patterns are stronger signals

            # Apply weight multiplier
            score *= rules["weight"]

            scores[intent_type] = score

        # Find highest scoring intent
        if not scores or max(scores.values()) == 0:
            # Default to ANALYSIS for ambiguous queries
            logger.info("No strong intent match, defaulting to ANALYSIS")
            return IntentType.ANALYSIS, 0.5

        best_intent = max(scores, key=scores.get)
        best_score = scores[best_intent]

        # Normalize confidence (rough heuristic)
        total_score = sum(scores.values())
        confidence = min(best_score / (total_score + 1e-6), 1.0)

        logger.info(
            "Intent classified: %s (confidence: %.2f, score: %.2f)",
            best_intent.value, confidence, best_score
        )

        return best_intent, round(confidence, 3)

    def get_top_intents(self, query: str, top_k: int = 3) -> List[Tuple[IntentType, float]]:
        """Get top K most likely intents for a query.

        Args:
            query: User query string
            top_k: Number of top intents to return

        Returns:
            List of (IntentType, confidence) tuples, sorted by confidence
        """
        query_lower = query.lower().strip()

        # Score each intent (same as classify())
        scores: Dict[IntentType, float] = {}

        for intent_type, rules in self.rules.items():
            score = 0.0

            for keyword in rules["keywords"]:
                if keyword.lower() in query_lower:
                    score += 1.0

            for pattern in rules["patterns"]:
                if re.search(pattern, query_lower):
                    score += 2.0

            score *= rules["weight"]
            scores[intent_type] = score

        # Sort by score and return top K
        sorted_intents = sorted(scores.items(), key=lambda x: x[1], reverse=True)

        # Normalize scores to confidences
        total_score = sum(s for _, s in sorted_intents) + 1e-6
        top_intents = [
            (intent, round(score / total_score, 3))
            for intent, score in sorted_intents[:top_k]
            if score > 0
        ]

        return top_intents if top_intents else [(IntentType.ANALYSIS, 0.5)]


# Global classifier instance
_classifier_instance = None


def get_intent_classifier() -> IntentClassifier:
    """Get global intent classifier instance.

    Returns:
        IntentClassifier: Global classifier instance
    """
    global _classifier_instance
    if _classifier_instance is None:
        _classifier_instance = IntentClassifier()
    return _classifier_instance
