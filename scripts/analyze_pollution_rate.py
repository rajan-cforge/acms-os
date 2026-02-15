"""
ACMS Quality-Based Memory Pollution Analysis Script

Analyzes pollution rate using the quality validation system's confidence scores.
Works with memory_items table and confidence_score/flagged columns.

Usage:
    python scripts/analyze_pollution_rate.py --dry-run
    python scripts/analyze_pollution_rate.py --threshold 0.8
    python scripts/analyze_pollution_rate.py --cleanup
"""

import asyncio
import sys
import os
import argparse
from datetime import datetime
from typing import List, Dict
import logging

# Add project root to path
sys.path.append('/path/to/acms')

from sqlalchemy import create_engine, text

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class PollutionAnalyzer:
    """Analyze memory pollution using quality scores"""

    def __init__(self, threshold=0.8, dry_run=True):
        self.threshold = threshold
        self.dry_run = dry_run

        # Get database config from environment (same as src/storage/database.py)
        db_host = os.getenv("ACMS_DB_HOST", "localhost")
        db_port = os.getenv("ACMS_DB_PORT", "40432")
        db_name = os.getenv("ACMS_DB_NAME", "acms")
        db_user = os.getenv("ACMS_DB_USER", "acms")
        db_password = os.getenv("ACMS_DB_PASSWORD", "acms_password")

        self.engine = create_engine(
            f'postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}'
        )

    def get_pollution_statistics(self) -> Dict:
        """Get comprehensive pollution statistics"""
        with self.engine.connect() as conn:
            # Total memories
            total_result = conn.execute(text("SELECT COUNT(*) as count FROM memory_items"))
            total_count = total_result.fetchone()._mapping['count']

            # Memories with confidence scores
            scored_result = conn.execute(
                text("SELECT COUNT(*) as count FROM memory_items WHERE confidence_score IS NOT NULL")
            )
            scored_count = scored_result.fetchone()._mapping['count']

            # Low confidence memories (below threshold)
            low_conf_result = conn.execute(
                text("""
                    SELECT COUNT(*) as count
                    FROM memory_items
                    WHERE confidence_score IS NOT NULL
                    AND confidence_score < :threshold
                """),
                {"threshold": self.threshold}
            )
            low_conf_count = low_conf_result.fetchone()._mapping['count']

            # Flagged memories
            flagged_result = conn.execute(
                text("SELECT COUNT(*) as count FROM memory_items WHERE flagged = true")
            )
            flagged_count = flagged_result.fetchone()._mapping['count']

            # Memories by tier
            tier_result = conn.execute(
                text("""
                    SELECT tier, COUNT(*) as count,
                           AVG(confidence_score) as avg_confidence
                    FROM memory_items
                    WHERE confidence_score IS NOT NULL
                    GROUP BY tier
                    ORDER BY tier
                """)
            )
            tier_stats = [dict(row._mapping) for row in tier_result]

            # Calculate pollution rate
            if scored_count > 0:
                pollution_rate = (low_conf_count / scored_count) * 100
            else:
                pollution_rate = 0.0

            return {
                'total_memories': total_count,
                'scored_memories': scored_count,
                'low_confidence_count': low_conf_count,
                'flagged_count': flagged_count,
                'pollution_rate': pollution_rate,
                'tier_stats': tier_stats,
                'threshold': self.threshold
            }

    def get_polluted_memories(self) -> List[Dict]:
        """Get list of memories below quality threshold"""
        with self.engine.connect() as conn:
            result = conn.execute(
                text("""
                    SELECT id, user_id, content, confidence_score, flagged,
                           flagged_reason, created_at, tier, source
                    FROM memory_items
                    WHERE confidence_score IS NOT NULL
                    AND confidence_score < :threshold
                    ORDER BY confidence_score ASC
                    LIMIT 50
                """),
                {"threshold": self.threshold}
            )
            return [dict(row._mapping) for row in result]

    def print_statistics_report(self, stats: Dict):
        """Print detailed statistics report"""
        print("\n" + "=" * 80)
        print("ACMS MEMORY POLLUTION ANALYSIS REPORT")
        print("=" * 80)
        print(f"\nTimestamp: {datetime.now().isoformat()}")
        print(f"Quality Threshold: {stats['threshold']}")
        print("\n--- OVERALL STATISTICS ---")
        print(f"Total Memories: {stats['total_memories']}")
        print(f"Memories with Quality Scores: {stats['scored_memories']}")
        print(f"Low Confidence Memories (< {stats['threshold']}): {stats['low_confidence_count']}")
        print(f"Flagged Memories: {stats['flagged_count']}")
        print(f"\n🎯 POLLUTION RATE: {stats['pollution_rate']:.2f}%")

        if stats['pollution_rate'] < 5.0:
            print("✅ PASS - Pollution rate is below 5% target!")
        else:
            print("❌ FAIL - Pollution rate exceeds 5% target")

        print("\n--- BREAKDOWN BY TIER ---")
        for tier_stat in stats['tier_stats']:
            avg_conf = tier_stat['avg_confidence']
            print(f"{tier_stat['tier']:8} : {tier_stat['count']:6} memories "
                  f"(avg confidence: {avg_conf:.3f})")

    def print_polluted_memories_report(self, memories: List[Dict]):
        """Print report of polluted memories"""
        if not memories:
            print("\n✅ No polluted memories found!")
            return

        print("\n" + "=" * 80)
        print(f"LOW QUALITY MEMORIES (showing up to 50)")
        print("=" * 80)

        for i, mem in enumerate(memories):
            print(f"\n[{i+1}] ID: {mem['id']}")
            print(f"User: {mem['user_id']}")
            print(f"Confidence Score: {mem['confidence_score']:.3f}")
            print(f"Flagged: {mem['flagged']}")
            if mem['flagged_reason']:
                print(f"Reason: {mem['flagged_reason']}")
            print(f"Tier: {mem['tier']} | Source: {mem.get('source', 'N/A')}")
            print(f"Created: {mem['created_at']}")

            # Show first 150 chars of content
            content = mem['content']
            preview = content[:150] + "..." if len(content) > 150 else content
            print(f"Content: {preview}")
            print("-" * 80)

    def delete_polluted_memories(self, threshold: float):
        """Delete memories below quality threshold"""
        if self.dry_run:
            logger.info("[DRY RUN] Would delete memories below threshold")
            return

        with self.engine.connect() as conn:
            result = conn.execute(
                text("""
                    DELETE FROM memory_items
                    WHERE confidence_score IS NOT NULL
                    AND confidence_score < :threshold
                    RETURNING id
                """),
                {"threshold": threshold}
            )
            deleted_ids = [row._mapping['id'] for row in result]
            conn.commit()

        logger.info(f"✅ Deleted {len(deleted_ids)} polluted memories")
        return deleted_ids

    def run_analysis(self):
        """Run complete pollution analysis"""
        logger.info("🔍 Analyzing memory pollution using quality scores...")

        # Get statistics
        stats = self.get_pollution_statistics()
        self.print_statistics_report(stats)

        # Get polluted memories
        polluted = self.get_polluted_memories()
        self.print_polluted_memories_report(polluted)

        # Summary
        print("\n" + "=" * 80)
        print("SUMMARY")
        print("=" * 80)
        print(f"✅ Analysis complete")
        print(f"📊 Pollution Rate: {stats['pollution_rate']:.2f}%")
        print(f"🎯 Target: < 5.0%")
        print(f"📝 Memories to review/cleanup: {stats['low_confidence_count']}")

        if not self.dry_run:
            print(f"\n⚠️  Cleanup mode is OFF (dry-run)")
            print(f"   To delete polluted memories, run with --cleanup flag")

        return stats


def main():
    parser = argparse.ArgumentParser(
        description="ACMS Memory Pollution Analysis using Quality Scores"
    )
    parser.add_argument(
        '--threshold',
        type=float,
        default=0.8,
        help="Quality threshold (default: 0.8)"
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        default=True,
        help="Run analysis without making changes (default)"
    )
    parser.add_argument(
        '--cleanup',
        action='store_true',
        help="Delete memories below threshold (use with caution)"
    )

    args = parser.parse_args()

    # If cleanup is specified, disable dry-run
    dry_run = not args.cleanup

    analyzer = PollutionAnalyzer(threshold=args.threshold, dry_run=dry_run)
    stats = analyzer.run_analysis()

    # If cleanup requested, execute deletion
    if args.cleanup:
        print("\n" + "=" * 80)
        print("⚠️  CLEANUP MODE ACTIVATED")
        print("=" * 80)
        confirm = input(f"\nType 'DELETE' to confirm deletion of {stats['low_confidence_count']} memories: ")

        if confirm == "DELETE":
            deleted_ids = analyzer.delete_polluted_memories(args.threshold)
            logger.info(f"✅ Cleanup complete - {len(deleted_ids)} memories deleted")
        else:
            logger.info("Cleanup cancelled")


if __name__ == "__main__":
    main()
