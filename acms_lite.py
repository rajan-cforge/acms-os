#!/usr/bin/env python3
"""ACMS-Lite: Bootstrap memory for Claude Code during ACMS build."""

import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional
import hashlib
import argparse
import sys


class ACMSLite:
    """Ultra-simple memory for Claude Code - uses SQLite, no dependencies."""

    def __init__(self, db_path: str = ".acms_lite.db"):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        """Create tables if not exist."""
        conn = sqlite3.connect(self.db_path)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS memories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                content TEXT NOT NULL,
                content_hash TEXT UNIQUE NOT NULL,
                tag TEXT,
                phase TEXT,
                checkpoint INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                access_count INTEGER DEFAULT 0,
                last_accessed_at TIMESTAMP
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_tag ON memories(tag)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_phase ON memories(phase)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_checkpoint ON memories(checkpoint)")
        conn.commit()
        conn.close()

    def store(self, content: str, tag: Optional[str] = None,
              phase: Optional[str] = None, checkpoint: Optional[int] = None) -> int:
        """Store a memory. Returns memory ID."""
        content_hash = hashlib.sha256(content.encode()).hexdigest()[:16]
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            cursor.execute("""
                INSERT INTO memories (content, content_hash, tag, phase, checkpoint)
                VALUES (?, ?, ?, ?, ?)
            """, (content, content_hash, tag, phase, checkpoint))
            conn.commit()
            memory_id = cursor.lastrowid
            print(f"✅ Stored #{memory_id}: {content[:60]}...")
            return memory_id
        except sqlite3.IntegrityError:
            cursor.execute("SELECT id FROM memories WHERE content_hash = ?", (content_hash,))
            memory_id = cursor.fetchone()[0]
            print(f"ℹ️  Already exists: #{memory_id}")
            return memory_id
        finally:
            conn.close()

    def query(self, search_term: str, tag: Optional[str] = None,
              phase: Optional[str] = None, limit: int = 5) -> List[Dict]:
        """Query memories by keyword search."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        where_clauses = ["content LIKE ?"]
        params = [f"%{search_term}%"]

        if tag:
            where_clauses.append("tag = ?")
            params.append(tag)
        if phase:
            where_clauses.append("phase = ?")
            params.append(phase)

        params.append(limit)

        query = f"""
            SELECT id, content, tag, phase, checkpoint, created_at, access_count
            FROM memories WHERE {' AND '.join(where_clauses)}
            ORDER BY access_count DESC, created_at DESC LIMIT ?
        """

        cursor.execute(query, params)
        results = [dict(row) for row in cursor.fetchall()]

        if results:
            ids = [r['id'] for r in results]
            cursor.execute(f"""
                UPDATE memories SET access_count = access_count + 1,
                    last_accessed_at = CURRENT_TIMESTAMP
                WHERE id IN ({','.join('?' * len(ids))})
            """, ids)
            conn.commit()

        conn.close()
        return results

    def list_all(self, tag: Optional[str] = None, phase: Optional[str] = None,
                 checkpoint: Optional[int] = None, limit: int = 50) -> List[Dict]:
        """List all memories with optional filters."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        where_clauses = []
        params = []

        if tag:
            where_clauses.append("tag = ?")
            params.append(tag)
        if phase:
            where_clauses.append("phase = ?")
            params.append(phase)
        if checkpoint:
            where_clauses.append("checkpoint = ?")
            params.append(checkpoint)

        params.append(limit)
        where_sql = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""

        query = f"""
            SELECT id, content, tag, phase, checkpoint, created_at, access_count
            FROM memories {where_sql}
            ORDER BY created_at DESC LIMIT ?
        """

        cursor.execute(query, params)
        results = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return results

    def export(self, output_file: str = "bootstrap_memories.json"):
        """Export all memories for ingestion into full ACMS."""
        memories = self.list_all(limit=10000)
        with open(output_file, 'w') as f:
            json.dump(memories, f, indent=2, default=str)
        print(f"✅ Exported {len(memories)} memories to {output_file}")
        return output_file

    def stats(self) -> Dict:
        """Get memory statistics."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("SELECT COUNT(*) FROM memories")
        total = cursor.fetchone()[0]

        cursor.execute("SELECT tag, COUNT(*) FROM memories WHERE tag IS NOT NULL GROUP BY tag")
        by_tag = dict(cursor.fetchall())

        cursor.execute("SELECT phase, COUNT(*) FROM memories WHERE phase IS NOT NULL GROUP BY phase")
        by_phase = dict(cursor.fetchall())

        conn.close()
        return {'total': total, 'by_tag': by_tag, 'by_phase': by_phase}


def main():
    parser = argparse.ArgumentParser(description="ACMS-Lite: Memory for Claude Code")
    subparsers = parser.add_subparsers(dest='command', help='Commands')

    store_parser = subparsers.add_parser('store', help='Store a memory')
    store_parser.add_argument('content', help='Content to remember')
    store_parser.add_argument('--tag', help='Tag (decision/error/architecture/etc)')
    store_parser.add_argument('--phase', help='Build phase')
    store_parser.add_argument('--checkpoint', type=int, help='Checkpoint number')

    query_parser = subparsers.add_parser('query', help='Query memories')
    query_parser.add_argument('search', help='Search term')
    query_parser.add_argument('--tag', help='Filter by tag')
    query_parser.add_argument('--phase', help='Filter by phase')
    query_parser.add_argument('--limit', type=int, default=5, help='Max results')

    list_parser = subparsers.add_parser('list', help='List all memories')
    list_parser.add_argument('--tag', help='Filter by tag')
    list_parser.add_argument('--phase', help='Filter by phase')
    list_parser.add_argument('--checkpoint', type=int, help='Filter by checkpoint')
    list_parser.add_argument('--limit', type=int, default=50, help='Max results')

    subparsers.add_parser('export', help='Export for full ACMS')
    subparsers.add_parser('stats', help='Show statistics')

    args = parser.parse_args()
    acms = ACMSLite()

    if args.command == 'store':
        acms.store(args.content, args.tag, args.phase, args.checkpoint)
    elif args.command == 'query':
        results = acms.query(args.search, args.tag, args.phase, args.limit)
        if results:
            print(f"\n🔍 Found {len(results)} result(s):\n")
            for i, r in enumerate(results, 1):
                print(f"{i}. [{r['tag'] or 'untagged'}] {r['content']}")
                print(f"   Phase: {r['phase'] or 'N/A'} | Checkpoint: {r['checkpoint'] or 'N/A'} | Used: {r['access_count']}x\n")
        else:
            print("❌ No matching memories found")
    elif args.command == 'list':
        results = acms.list_all(args.tag, args.phase, args.checkpoint, args.limit)
        print(f"\n📋 {len(results)} memories:\n")
        for r in results:
            tag = f"[{r['tag']}]" if r['tag'] else "[untagged]"
            print(f"#{r['id']} {tag} {r['content'][:80]}")
    elif args.command == 'export':
        acms.export()
    elif args.command == 'stats':
        stats = acms.stats()
        print(f"\n📊 ACMS-Lite Statistics:")
        print(f"   Total: {stats['total']}")
        if stats['by_tag']:
            print(f"\n   By tag:")
            for tag, count in stats['by_tag'].items():
                print(f"     {tag}: {count}")
        if stats['by_phase']:
            print(f"\n   By phase:")
            for phase, count in stats['by_phase'].items():
                print(f"     {phase}: {count}")
    else:
        parser.print_help()


if __name__ == '__main__':
    main()
