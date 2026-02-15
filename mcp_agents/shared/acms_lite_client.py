"""
ACMS-Lite Client for MCP Agents
Provides interface for agents to query/store in ACMS-Lite shared memory
"""
import sqlite3
import json
from datetime import datetime
from typing import List, Dict, Optional
from pathlib import Path


class ACMSLiteClient:
    """Client for interacting with ACMS-Lite database"""

    def __init__(self, db_path: str = None):
        if db_path is None:
            # Default to project root
            project_root = Path(__file__).parent.parent.parent
            db_path = project_root / ".acms_lite.db"
        self.db_path = str(db_path)

    def store(self, content: str, tag: str = "", phase: str = "",
              checkpoint: Optional[int] = None, metadata: Optional[Dict] = None) -> int:
        """Store memory in ACMS-Lite"""
        import hashlib

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Generate content hash
        content_hash = hashlib.sha256(content.encode()).hexdigest()

        # If metadata provided, append as JSON to content
        if metadata:
            content_with_metadata = f"{content}\n[METADATA: {json.dumps(metadata)}]"
        else:
            content_with_metadata = content

        try:
            cursor.execute("""
                INSERT INTO memories (content, content_hash, tag, phase, checkpoint, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (content_with_metadata, content_hash, tag, phase, checkpoint, datetime.now().isoformat()))

            memory_id = cursor.lastrowid
            conn.commit()
        except sqlite3.IntegrityError:
            # Duplicate content_hash - return existing ID
            cursor.execute("SELECT id FROM memories WHERE content_hash = ?", (content_hash,))
            memory_id = cursor.fetchone()[0]
        finally:
            conn.close()

        return memory_id

    def query(self, search_term: str = "", tag: Optional[str] = None,
              phase: Optional[str] = None, limit: int = 10) -> List[Dict]:
        """Query memories from ACMS-Lite"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        query = "SELECT * FROM memories WHERE 1=1"
        params = []

        if search_term:
            query += " AND content LIKE ?"
            params.append(f"%{search_term}%")
        if tag:
            query += " AND tag = ?"
            params.append(tag)
        if phase:
            query += " AND phase = ?"
            params.append(phase)

        query += " ORDER BY created_at DESC LIMIT ?"
        params.append(limit)

        cursor.execute(query, params)
        results = [dict(row) for row in cursor.fetchall()]
        conn.close()

        return results

    def list_recent(self, limit: int = 10, tag: Optional[str] = None,
                    phase: Optional[str] = None) -> List[Dict]:
        """List recent memories"""
        return self.query(search_term="", tag=tag, phase=phase, limit=limit)

    def get_interface_contract(self, component_a: str, component_b: str) -> Optional[Dict]:
        """Get interface contract between two components"""
        memories = self.query(search_term=f"{component_a} {component_b}", tag="contract", limit=50)

        for memory in memories:
            content = memory['content']
            # Check if this is the right contract
            if component_a in content and component_b in content:
                try:
                    # Extract JSON from content (before metadata)
                    if '[METADATA:' in content:
                        json_content = content.split('[METADATA:')[0].strip()
                    else:
                        json_content = content
                    return json.loads(json_content)
                except (json.JSONDecodeError, KeyError):
                    continue

        return None

    def store_interface_contract(self, component_a: str, component_b: str,
                                 contract: Dict) -> int:
        """Store interface contract between components"""
        return self.store(
            content=json.dumps(contract, indent=2),
            tag="contract",
            phase="interface",
            metadata={
                "component_a": component_a,
                "component_b": component_b,
                "type": "interface_contract",
                "created_at": datetime.now().isoformat()
            }
        )

    def get_stats(self) -> Dict:
        """Get database statistics"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("SELECT COUNT(*) FROM memories")
        total = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(DISTINCT tag) FROM memories WHERE tag != ''")
        unique_tags = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(DISTINCT phase) FROM memories WHERE phase != ''")
        unique_phases = cursor.fetchone()[0]

        conn.close()

        return {
            "total_memories": total,
            "unique_tags": unique_tags,
            "unique_phases": unique_phases
        }
