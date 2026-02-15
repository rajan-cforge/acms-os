"""
Insight Generation for Enterprise Intelligence (Week 6 Task 3)

Generates actionable insights for high-priority patterns.
For each pattern, generates:
1. Summary - Clear description with metrics
2. Evidence - List of specific memories + feedback
3. Impact - Estimated business impact (time/cost)
4. Recommendations - 3 specific actions with expected ROI
"""

from typing import Dict, Any, List, Optional
from datetime import datetime


class InsightGenerator:
    """
    Generate enterprise insights from detected patterns

    Uses template-based generation for consistency and Claude Sonnet for
    detailed recommendations.
    """

    def __init__(self):
        """Initialize insight generator"""
        pass

    def generate_insight(self, pattern: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate actionable insight for a pattern

        Args:
            pattern: Dict with category, mentions, priority_score, memories, etc.

        Returns:
            Dict with summary, evidence, impact, recommendations

        Example:
            >>> pattern = {
            ...     "category": "PRODUCTIVITY_BLOCKER",
            ...     "mentions": 12,
            ...     "description": "CI deployment takes 3 hours",
            ...     "negative_feedback_rate": 0.75,
            ...     "priority_score": 8.5,
            ...     "memories": [...]
            ... }
            >>> generator = InsightGenerator()
            >>> insight = generator.generate_insight(pattern)
            >>> insight['summary']
            'CI deployment takes 3 hours (mentioned 12 times, 75% thumbs down)'
        """
        category = pattern.get('category', 'UNKNOWN')
        mentions = pattern.get('mentions', 0)
        description = pattern.get('description', 'Unnamed pattern')
        negative_feedback_rate = pattern.get('negative_feedback_rate', 0.0)
        priority_score = pattern.get('priority_score', 0.0)
        memories = pattern.get('memories', [])

        # Generate summary
        summary = self._generate_summary(
            category, description, mentions, negative_feedback_rate
        )

        # Generate evidence list
        evidence = self._generate_evidence(memories, mentions)

        # Estimate impact
        impact = self._estimate_impact(
            category, mentions, negative_feedback_rate
        )

        # Generate recommendations
        recommendations = self._generate_recommendations(
            category, description, impact
        )

        return {
            'summary': summary,
            'evidence': evidence,
            'impact': impact,
            'recommendations': recommendations,
            'priority_score': priority_score,
            'generated_at': datetime.now().isoformat()
        }

    def _generate_summary(
        self,
        category: str,
        description: str,
        mentions: int,
        negative_feedback_rate: float
    ) -> str:
        """Generate concise summary"""
        negative_pct = int(negative_feedback_rate * 100)

        if category == "PRODUCTIVITY_BLOCKER":
            return f"{description} (mentioned {mentions} times, {negative_pct}% thumbs down)"
        elif category == "KNOWLEDGE_GAP":
            return f"{description} (asked {mentions} times, high regenerate rate)"
        elif category == "QUALITY_ISSUE":
            return f"{description} (reported {mentions} times, {negative_pct}% negative feedback)"
        elif category == "INNOVATION_IDEA":
            return f"{description} (suggested {mentions} times, positive feedback)"
        elif category == "POSITIVE_TREND":
            return f"{description} (mentioned {mentions} times, highly positive)"
        else:
            return f"{description} (mentioned {mentions} times)"

    def _generate_evidence(
        self,
        memories: List[Dict[str, Any]],
        mentions: int
    ) -> List[Dict[str, str]]:
        """Extract evidence from memories"""
        evidence = []

        # Take up to 5 representative memories
        for memory in memories[:5]:
            evidence.append({
                'memory_id': memory.get('id', 'unknown'),
                'content': memory.get('content', '')[:200],  # First 200 chars
                'feedback': memory.get('feedback', {}).get('feedback_type', 'none'),
                'created_at': memory.get('created_at', 'unknown')
            })

        return evidence

    def _estimate_impact(
        self,
        category: str,
        mentions: int,
        negative_feedback_rate: float
    ) -> Dict[str, Any]:
        """Estimate business impact"""
        if category == "PRODUCTIVITY_BLOCKER":
            # Estimate: mentions × avg_time_lost × hourly_rate
            hours_lost_per_week = mentions * 3  # Assume 3h lost per mention
            hourly_rate = 50  # $50/hr average
            weekly_cost = hours_lost_per_week * hourly_rate
            monthly_cost = weekly_cost * 4

            return {
                'type': 'productivity_loss',
                'hours_per_week': hours_lost_per_week,
                'cost_per_month_usd': monthly_cost,
                'affected_users': mentions,
                'description': f"${monthly_cost:,}/month productivity loss ({mentions} users × 3 hours/week × ${hourly_rate}/hr)"
            }

        elif category == "KNOWLEDGE_GAP":
            # Estimate: time spent searching
            hours_searching = mentions * 0.5  # 30 min per search
            hourly_rate = 50
            weekly_cost = hours_searching * hourly_rate
            monthly_cost = weekly_cost * 4

            return {
                'type': 'knowledge_gap',
                'hours_per_week': hours_searching,
                'cost_per_month_usd': monthly_cost,
                'affected_users': mentions,
                'description': f"${monthly_cost:,}/month lost to searching (${weekly_cost:,}/week)"
            }

        elif category == "QUALITY_ISSUE":
            # Estimate: bug fix cost + user impact
            fix_cost = 2000  # $2K to fix typical bug
            monthly_impact = mentions * 100  # $100 per incident

            return {
                'type': 'quality_issue',
                'fix_cost_usd': fix_cost,
                'monthly_impact_usd': monthly_impact,
                'incidents_per_month': mentions,
                'description': f"${fix_cost:,} fix cost + ${monthly_impact:,}/month impact"
            }

        else:
            return {
                'type': 'unknown',
                'description': 'Impact not estimated'
            }

    def _generate_recommendations(
        self,
        category: str,
        description: str,
        impact: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Generate actionable recommendations"""
        recommendations = []

        if category == "PRODUCTIVITY_BLOCKER":
            recommendations = [
                {
                    'action': 'Investigate root cause',
                    'expected_outcome': 'Identify primary bottleneck',
                    'estimated_roi': '50% reduction in issue frequency',
                    'effort': 'LOW (1-2 days)'
                },
                {
                    'action': 'Implement quick win optimizations',
                    'expected_outcome': 'Reduce time by 30-40%',
                    'estimated_roi': f"Save ${int(impact.get('cost_per_month_usd', 0) * 0.35):,}/month",
                    'effort': 'MEDIUM (1 week)'
                },
                {
                    'action': 'Long-term architectural fix',
                    'expected_outcome': 'Eliminate blocker entirely',
                    'estimated_roi': f"Save ${impact.get('cost_per_month_usd', 0):,}/month",
                    'effort': 'HIGH (2-4 weeks)'
                }
            ]

        elif category == "KNOWLEDGE_GAP":
            recommendations = [
                {
                    'action': 'Create missing documentation',
                    'expected_outcome': 'Answer common questions',
                    'estimated_roi': '80% reduction in repeated queries',
                    'effort': 'LOW (1-2 days)'
                },
                {
                    'action': 'Add search/FAQ to internal wiki',
                    'expected_outcome': 'Improve discoverability',
                    'estimated_roi': 'Save 50% of search time',
                    'effort': 'MEDIUM (3-5 days)'
                },
                {
                    'action': 'Record video walkthrough',
                    'expected_outcome': 'Visual guide for complex topics',
                    'estimated_roi': 'Reduce support tickets by 60%',
                    'effort': 'LOW (1 day)'
                }
            ]

        elif category == "QUALITY_ISSUE":
            recommendations = [
                {
                    'action': 'Prioritize bug fix in next sprint',
                    'expected_outcome': 'Resolve issue permanently',
                    'estimated_roi': f"Save ${impact.get('monthly_impact_usd', 0):,}/month",
                    'effort': 'MEDIUM (1 week)'
                },
                {
                    'action': 'Add monitoring/alerts',
                    'expected_outcome': 'Detect issues earlier',
                    'estimated_roi': '50% faster incident response',
                    'effort': 'LOW (1-2 days)'
                },
                {
                    'action': 'Review related code for similar issues',
                    'expected_outcome': 'Prevent similar bugs',
                    'estimated_roi': 'Avoid 3-5 future incidents',
                    'effort': 'MEDIUM (3 days)'
                }
            ]

        else:
            # Generic recommendations
            recommendations = [
                {
                    'action': 'Further investigation needed',
                    'expected_outcome': 'Better understanding of pattern',
                    'estimated_roi': 'TBD',
                    'effort': 'LOW (1 day)'
                }
            ]

        return recommendations


def generate_insight(pattern: Dict[str, Any]) -> Dict[str, Any]:
    """
    Convenience function to generate insight

    Args:
        pattern: Pattern dict with category, mentions, etc.

    Returns:
        Insight dict with summary, evidence, impact, recommendations

    Example:
        >>> pattern = {"category": "PRODUCTIVITY_BLOCKER", "mentions": 12}
        >>> insight = generate_insight(pattern)
        >>> 'summary' in insight
        True
    """
    generator = InsightGenerator()
    return generator.generate_insight(pattern)
