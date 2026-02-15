"""Intelligence Hub module for ACMS.

Contains components for:
- Knowledge extraction with intent/entity/topic analysis
- Topic extraction from Q&A pairs and memories
- Insights generation and pattern detection
- Executive report generation
"""

from src.intelligence.knowledge_extractor import (
    KnowledgeExtractor,
    KnowledgeEntry,
    IntentAnalysis,
    Entity,
    Relation,
    get_knowledge_extractor,
)

from src.intelligence.topic_extractor import (
    TopicExtractor,
    ExtractionMethod,
    TopicExtractionResult,
    BatchExtractionResult,
    ExtractableItem,
    EXTRACTOR_VERSION,
    BATCH_CONFIG,
    get_extractable_text,
)

from src.intelligence.insights_engine import (
    InsightsEngine,
    InsightsSummary,
    TopicStat,
    TopicAnalysis,
    TrendsResponse,
    TrendPoint,
    TrendDirection,
    GeneratedInsight,
    InsightEvidence,
    InsightType,
    TrustLevel,
    Recommendation,
    INSIGHTS_CONFIG,
)

from src.intelligence.report_generator import (
    ReportGenerator,
    IntelligenceReport,
    ReportType,
    ReportStatus,
    ReportSummary,
    TopicEntry,
    ReportInsight,
    ReportRecommendation,
    KnowledgeGrowth,
    AgentStats,
    REPORT_CONFIG,
)

from src.intelligence.knowledge_insights import (
    KnowledgeInsightsService,
    calculate_depth_level,
    ExpertiseCenter,
    LearningPattern,
    AttentionSignal,
    Recommendation as KnowledgeRecommendation,
)

__all__ = [
    # Knowledge Extractor (Dec 2025)
    "KnowledgeExtractor",
    "KnowledgeEntry",
    "IntentAnalysis",
    "Entity",
    "Relation",
    "get_knowledge_extractor",
    # Topic Extractor
    "TopicExtractor",
    "ExtractionMethod",
    "TopicExtractionResult",
    "BatchExtractionResult",
    "ExtractableItem",
    "EXTRACTOR_VERSION",
    "BATCH_CONFIG",
    "get_extractable_text",
    # Insights Engine
    "InsightsEngine",
    "InsightsSummary",
    "TopicStat",
    "TopicAnalysis",
    "TrendsResponse",
    "TrendPoint",
    "TrendDirection",
    "GeneratedInsight",
    "InsightEvidence",
    "InsightType",
    "TrustLevel",
    "Recommendation",
    "INSIGHTS_CONFIG",
    # Report Generator
    "ReportGenerator",
    "IntelligenceReport",
    "ReportType",
    "ReportStatus",
    "ReportSummary",
    "TopicEntry",
    "ReportInsight",
    "ReportRecommendation",
    "KnowledgeGrowth",
    "AgentStats",
    "REPORT_CONFIG",
    # Knowledge Insights (Dec 2025)
    "KnowledgeInsightsService",
    "calculate_depth_level",
    "ExpertiseCenter",
    "LearningPattern",
    "AttentionSignal",
    "KnowledgeRecommendation",
]
