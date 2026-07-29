# Copyright © 2026 Arsh Buttar. All rights reserved. Confidential and proprietary.
# Unauthorized copying, distribution, or use of this work is prohibited.

from __future__ import annotations
import hashlib
import json
import sqlite3
import threading
from pathlib import Path
from typing import Any, Optional

from research_runtime.genome import AgentGenome, MissionGenome, TaskAssignment


class RuntimeStore:
    def __init__(self, db_path: str):
        self.db_path = db_path
        self._local = threading.local()
        self._init_db()

    @property
    def conn(self) -> sqlite3.Connection:
        if not hasattr(self._local, "conn") or self._local.conn is None:
            self._local.conn = sqlite3.connect(self.db_path)
            self._local.conn.row_factory = sqlite3.Row
            self._local.conn.execute("PRAGMA journal_mode=WAL")
            self._local.conn.execute("PRAGMA foreign_keys=ON")
        return self._local.conn

    def _init_db(self) -> None:
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        conn = self.conn
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS agent_genomes (
                agent_id TEXT PRIMARY KEY,
                role TEXT NOT NULL,
                genome_json TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS mission_genomes (
                mission_id TEXT PRIMARY KEY,
                genome_json TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS task_assignments (
                task_id TEXT PRIMARY KEY,
                mission_id TEXT NOT NULL,
                assignment_json TEXT NOT NULL,
                created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS blackboard_entries (
                entry_id TEXT PRIMARY KEY,
                mission_id TEXT NOT NULL,
                section TEXT NOT NULL,
                agent TEXT NOT NULL,
                content TEXT NOT NULL,
                content_hash TEXT NOT NULL,
                timestamp TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS evidence_ledger (
                evidence_id TEXT PRIMARY KEY,
                mission_id TEXT NOT NULL,
                claim TEXT NOT NULL,
                source TEXT NOT NULL,
                url TEXT,
                confidence REAL DEFAULT 0.0,
                extraction_method TEXT,
                verification_status TEXT DEFAULT 'unverified',
                related_evidence TEXT DEFAULT '[]',
                claim_ids TEXT DEFAULT '[]',
                content_hash TEXT NOT NULL,
                agent TEXT NOT NULL,
                timestamp TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS trust_records (
                agent TEXT NOT NULL,
                capability TEXT NOT NULL,
                total_tasks INTEGER DEFAULT 0,
                successful_tasks INTEGER DEFAULT 0,
                failed_tasks INTEGER DEFAULT 0,
                total_latency_ms REAL DEFAULT 0.0,
                hallucination_count INTEGER DEFAULT 0,
                human_overrides INTEGER DEFAULT 0,
                last_updated TEXT NOT NULL,
                PRIMARY KEY (agent, capability)
            );
            CREATE TABLE IF NOT EXISTS journal_entries (
                entry_id TEXT PRIMARY KEY,
                mission_id TEXT NOT NULL,
                entry_type TEXT NOT NULL,
                agent TEXT,
                title TEXT,
                content TEXT,
                timestamp TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS reflection_entries (
                reflection_id TEXT PRIMARY KEY,
                mission_id TEXT NOT NULL,
                analysis_type TEXT NOT NULL,
                finding TEXT NOT NULL,
                severity TEXT DEFAULT 'info',
                timestamp TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS debate_rounds (
                mission_id TEXT NOT NULL,
                round_number INTEGER NOT NULL,
                step TEXT NOT NULL,
                agent TEXT NOT NULL,
                content TEXT,
                confidence REAL DEFAULT 0.0,
                timestamp TEXT NOT NULL,
                PRIMARY KEY (mission_id, round_number, step)
            );
            CREATE TABLE IF NOT EXISTS composite_capabilities (
                name TEXT PRIMARY KEY,
                description TEXT,
                pipeline_json TEXT NOT NULL,
                version TEXT DEFAULT '0.1.0',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS master_papers (
                paper_id TEXT PRIMARY KEY,
                mission_id TEXT NOT NULL,
                paper_json TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS knowledge_links (
                link_id TEXT PRIMARY KEY,
                source_type TEXT NOT NULL,
                source_id TEXT NOT NULL,
                target_type TEXT NOT NULL,
                target_id TEXT NOT NULL,
                relation TEXT NOT NULL,
                weight REAL DEFAULT 1.0,
                auto_generated INTEGER DEFAULT 1,
                timestamp TEXT NOT NULL
            );
        """)
        conn.commit()
        self._migrate_debate_rounds(conn)
        self._migrate_master_papers(conn)

    def _migrate_debate_rounds(self, conn: sqlite3.Connection) -> None:
        try:
            cols = {
                r["name"]
                for r in conn.execute("PRAGMA table_info(debate_rounds)").fetchall()
            }
            required = {"mission_id", "round_number", "step", "agent", "content", "confidence", "timestamp"}
            if not required.issubset(cols):
                conn.executescript("""
                    DROP TABLE IF EXISTS debate_rounds_old;
                    ALTER TABLE debate_rounds RENAME TO debate_rounds_old;
                    CREATE TABLE debate_rounds (
                        mission_id TEXT NOT NULL,
                        round_number INTEGER NOT NULL,
                        step TEXT NOT NULL,
                        agent TEXT NOT NULL,
                        content TEXT,
                        confidence REAL DEFAULT 0.0,
                        timestamp TEXT NOT NULL,
                        PRIMARY KEY (mission_id, round_number, step)
                    );
                """)
                conn.commit()
        except Exception:
            pass

    def _migrate_master_papers(self, conn: sqlite3.Connection) -> None:
        try:
            cols = {
                r["name"]
                for r in conn.execute("PRAGMA table_info(master_papers)").fetchall()
            }
            for col in ("paper_json", "created_at", "updated_at"):
                if col not in cols:
                    conn.execute(
                        f"ALTER TABLE master_papers ADD COLUMN {col} TEXT NOT NULL DEFAULT ''"
                    )
            conn.commit()
        except Exception:
            pass

    def save_agent_genome(self, genome: AgentGenome) -> None:
        self.conn.execute(
            "INSERT OR REPLACE INTO agent_genomes (agent_id, role, genome_json, updated_at) VALUES (?,?,?,?)",
            (genome.agent_id, genome.role.value, json.dumps(genome.to_dict()), genome.last_active),
        )
        self.conn.commit()

    def get_agent_genome(self, agent_id: str) -> Optional[AgentGenome]:
        row = self.conn.execute(
            "SELECT genome_json FROM agent_genomes WHERE agent_id = ?", (agent_id,)
        ).fetchone()
        if not row:
            return None
        return AgentGenome.from_dict(json.loads(row["genome_json"]))

    def list_agent_genomes(self) -> list[AgentGenome]:
        rows = self.conn.execute("SELECT genome_json FROM agent_genomes").fetchall()
        return [AgentGenome.from_dict(json.loads(r["genome_json"])) for r in rows]

    def save_mission_genome(self, genome: MissionGenome) -> None:
        self.conn.execute(
            "INSERT OR REPLACE INTO mission_genomes (mission_id, genome_json, created_at, updated_at) VALUES (?,?,?,?)",
            (genome.mission_id, json.dumps(genome.to_dict()), genome.created_at, genome.updated_at),
        )
        self.conn.commit()

    def get_mission_genome(self, mission_id: str) -> Optional[MissionGenome]:
        row = self.conn.execute(
            "SELECT genome_json FROM mission_genomes WHERE mission_id = ?", (mission_id,)
        ).fetchone()
        if not row:
            return None
        return MissionGenome.from_dict(json.loads(row["genome_json"]))

    def list_mission_genomes(self, status: Optional[str] = None) -> list[MissionGenome]:
        if status:
            rows = self.conn.execute(
                "SELECT genome_json FROM mission_genomes WHERE json_extract(genome_json, '$.current_state') = ? ORDER BY created_at DESC",
                (status,),
            ).fetchall()
        else:
            rows = self.conn.execute(
                "SELECT genome_json FROM mission_genomes ORDER BY created_at DESC"
            ).fetchall()
        return [MissionGenome.from_dict(json.loads(r["genome_json"])) for r in rows]

    def save_task(self, task: TaskAssignment) -> None:
        self.conn.execute(
            "INSERT OR REPLACE INTO task_assignments (task_id, mission_id, assignment_json, created_at) VALUES (?,?,?,?)",
            (task.task_id, task.mission_id, json.dumps(task.to_dict()), task.created_at),
        )
        self.conn.commit()

    def list_tasks(self, mission_id: Optional[str] = None) -> list[TaskAssignment]:
        if mission_id:
            rows = self.conn.execute(
                "SELECT assignment_json FROM task_assignments WHERE mission_id = ? ORDER BY created_at",
                (mission_id,),
            ).fetchall()
        else:
            rows = self.conn.execute(
                "SELECT assignment_json FROM task_assignments ORDER BY created_at DESC"
            ).fetchall()
        return [TaskAssignment(**json.loads(r["assignment_json"])) for r in rows]

    def append_blackboard(self, entry_id: str, mission_id: str, section: str,
                          agent: str, content: str) -> str:
        content_hash = hashlib.sha256(content.encode()).hexdigest()[:16]
        self.conn.execute(
            "INSERT INTO blackboard_entries (entry_id, mission_id, section, agent, content, content_hash, timestamp) VALUES (?,?,?,?,?,?,?)",
            (entry_id, mission_id, section, agent, content, content_hash, _now()),
        )
        self.conn.commit()
        return content_hash

    def read_blackboard(self, mission_id: str,
                        section: Optional[str] = None) -> list[dict]:
        if section:
            rows = self.conn.execute(
                "SELECT * FROM blackboard_entries WHERE mission_id = ? AND section = ? ORDER BY timestamp",
                (mission_id, section),
            ).fetchall()
        else:
            rows = self.conn.execute(
                "SELECT * FROM blackboard_entries WHERE mission_id = ? ORDER BY section, timestamp",
                (mission_id,),
            ).fetchall()
        return [dict(r) for r in rows]

    def save_evidence(self, evidence: dict) -> None:
        evidence_id = evidence.get("evidence_id", _uuid())
        content = evidence.get("claim", "")
        content_hash = hashlib.sha256(content.encode()).hexdigest()
        self.conn.execute(
            """INSERT OR REPLACE INTO evidence_ledger
               (evidence_id, mission_id, claim, source, url, confidence,
                extraction_method, verification_status, related_evidence,
                claim_ids, content_hash, agent, timestamp)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                evidence_id,
                evidence.get("mission_id", ""),
                content,
                evidence.get("source", ""),
                evidence.get("url"),
                evidence.get("confidence", 0.0),
                evidence.get("extraction_method", "unknown"),
                evidence.get("verification_status", "unverified"),
                json.dumps(evidence.get("related_evidence", [])),
                json.dumps(evidence.get("claim_ids", [])),
                content_hash,
                evidence.get("agent", "system"),
                _now(),
            ),
        )
        self.conn.commit()

    def get_evidence(self, evidence_id: str) -> Optional[dict]:
        row = self.conn.execute(
            "SELECT * FROM evidence_ledger WHERE evidence_id = ?", (evidence_id,)
        ).fetchone()
        return dict(row) if row else None

    def list_evidence(self, mission_id: str) -> list[dict]:
        rows = self.conn.execute(
            "SELECT * FROM evidence_ledger WHERE mission_id = ? ORDER BY timestamp",
            (mission_id,),
        ).fetchall()
        return [dict(r) for r in rows]

    def update_trust(self, agent: str, capability: str, success: bool,
                     latency_ms: float = 0.0, hallucinated: bool = False,
                     overridden: bool = False) -> None:
        existing = self.conn.execute(
            "SELECT * FROM trust_records WHERE agent = ? AND capability = ?",
            (agent, capability),
        ).fetchone()
        if existing:
            self.conn.execute(
                """UPDATE trust_records SET
                   total_tasks = total_tasks + 1,
                   successful_tasks = successful_tasks + ?,
                   failed_tasks = failed_tasks + ?,
                   total_latency_ms = total_latency_ms + ?,
                   hallucination_count = hallucination_count + ?,
                   human_overrides = human_overrides + ?,
                   last_updated = ?
                   WHERE agent = ? AND capability = ?""",
                (
                    1 if success else 0,
                    0 if success else 1,
                    latency_ms,
                    1 if hallucinated else 0,
                    1 if overridden else 0,
                    _now(),
                    agent, capability,
                ),
            )
        else:
            self.conn.execute(
                """INSERT INTO trust_records
                   (agent, capability, total_tasks, successful_tasks, failed_tasks,
                    total_latency_ms, hallucination_count, human_overrides, last_updated)
                   VALUES (?,?,1,?,?,?,?,?,?)""",
                (
                    agent, capability,
                    1 if success else 0,
                    0 if success else 1,
                    latency_ms,
                    1 if hallucinated else 0,
                    1 if overridden else 0,
                    _now(),
                ),
            )
        self.conn.commit()

    def get_trust(self, agent: str, capability: str) -> dict:
        row = self.conn.execute(
            "SELECT * FROM trust_records WHERE agent = ? AND capability = ?",
            (agent, capability),
        ).fetchone()
        if not row:
            return {"total_tasks": 0, "success_rate": 0.5, "avg_latency_ms": 0.0}
        d = dict(row)
        d["success_rate"] = (
            d["successful_tasks"] / d["total_tasks"] if d["total_tasks"] > 0 else 0.5
        )
        d["avg_latency_ms"] = (
            d["total_latency_ms"] / d["total_tasks"] if d["total_tasks"] > 0 else 0.0
        )
        return d

    def save_journal_entry(self, entry_id: str, mission_id: str,
                           entry_type: str, title: str, content: str,
                           agent: Optional[str] = None) -> None:
        self.conn.execute(
            "INSERT INTO journal_entries (entry_id, mission_id, entry_type, agent, title, content, timestamp) VALUES (?,?,?,?,?,?,?)",
            (entry_id, mission_id, entry_type, agent, title, content, _now()),
        )
        self.conn.commit()

    def read_journal(self, mission_id: str,
                     entry_type: Optional[str] = None) -> list[dict]:
        if entry_type:
            rows = self.conn.execute(
                "SELECT * FROM journal_entries WHERE mission_id = ? AND entry_type = ? ORDER BY timestamp",
                (mission_id, entry_type),
            ).fetchall()
        else:
            rows = self.conn.execute(
                "SELECT * FROM journal_entries WHERE mission_id = ? ORDER BY timestamp",
                (mission_id,),
            ).fetchall()
        return [dict(r) for r in rows]

    def save_reflection(self, reflection_id: str, mission_id: str,
                        analysis_type: str, finding: str,
                        severity: str = "info") -> None:
        self.conn.execute(
            "INSERT INTO reflection_entries (reflection_id, mission_id, analysis_type, finding, severity, timestamp) VALUES (?,?,?,?,?,?)",
            (reflection_id, mission_id, analysis_type, finding, severity, _now()),
        )
        self.conn.commit()

    def list_reflections(self, mission_id: str) -> list[dict]:
        rows = self.conn.execute(
            "SELECT * FROM reflection_entries WHERE mission_id = ? ORDER BY timestamp",
            (mission_id,),
        ).fetchall()
        return [dict(r) for r in rows]

    def save_debate_step(self, mission_id: str, round_number: int,
                         step: str, agent: str, content: str,
                         confidence: float = 0.0) -> None:
        self.conn.execute(
            "INSERT OR REPLACE INTO debate_rounds (mission_id, round_number, step, agent, content, confidence, timestamp) VALUES (?,?,?,?,?,?,?)",
            (mission_id, round_number, step, agent, content, confidence, _now()),
        )
        self.conn.commit()

    def read_debate(self, mission_id: str) -> list[dict]:
        rows = self.conn.execute(
            "SELECT * FROM debate_rounds WHERE mission_id = ? ORDER BY round_number, step",
            (mission_id,),
        ).fetchall()
        return [dict(r) for r in rows]

    def save_composite(self, name: str, description: str,
                       pipeline_json: str, version: str = "0.1.0") -> None:
        self.conn.execute(
            "INSERT OR REPLACE INTO composite_capabilities (name, description, pipeline_json, version, created_at, updated_at) VALUES (?,?,?,?,?,?)",
            (name, description, pipeline_json, version, _now(), _now()),
        )
        self.conn.commit()

    def list_composites(self) -> list[dict]:
        rows = self.conn.execute(
            "SELECT * FROM composite_capabilities ORDER BY name"
        ).fetchall()
        return [dict(r) for r in rows]

    def save_master_paper(self, paper: Any) -> None:
        import json
        paper_dict = paper.to_dict() if hasattr(paper, "to_dict") else paper
        paper_json = json.dumps(paper_dict)
        self.conn.execute(
            "INSERT OR REPLACE INTO master_papers (paper_id, mission_id, paper_json, created_at, updated_at) VALUES (?,?,?,?,?)",
            (paper.paper_id, paper.mission_id, paper_json, paper.created_at, paper.updated_at),
        )
        self.conn.commit()

    def get_master_paper(self, paper_id: str) -> Optional[dict]:
        row = self.conn.execute(
            "SELECT paper_json FROM master_papers WHERE paper_id = ?", (paper_id,)
        ).fetchone()
        if not row:
            return None
        return json.loads(row["paper_json"])

    def list_master_papers(self, mission_id: Optional[str] = None) -> list[dict]:
        if mission_id:
            rows = self.conn.execute(
                "SELECT paper_json FROM master_papers WHERE mission_id = ? ORDER BY created_at DESC",
                (mission_id,),
            ).fetchall()
        else:
            rows = self.conn.execute(
                "SELECT paper_json FROM master_papers ORDER BY created_at DESC"
            ).fetchall()
        import json
        return [json.loads(r["paper_json"]) for r in rows]

    def save_knowledge_link(self, link_id: str, source_type: str, source_id: str,
                            target_type: str, target_id: str, relation: str,
                            weight: float = 1.0, auto_generated: bool = True) -> None:
        self.conn.execute(
            "INSERT OR REPLACE INTO knowledge_links (link_id, source_type, source_id, target_type, target_id, relation, weight, auto_generated, timestamp) VALUES (?,?,?,?,?,?,?,?,?)",
            (link_id, source_type, source_id, target_type, target_id, relation, weight, 1 if auto_generated else 0, _now()),
        )
        self.conn.commit()

    def query_knowledge_links(self, entity_type: Optional[str] = None,
                               entity_id: Optional[str] = None) -> list[dict]:
        if entity_id:
            rows = self.conn.execute(
                "SELECT * FROM knowledge_links WHERE source_id = ? OR target_id = ? ORDER BY weight DESC",
                (entity_id, entity_id),
            ).fetchall()
        elif entity_type:
            rows = self.conn.execute(
                "SELECT * FROM knowledge_links WHERE source_type = ? OR target_type = ? ORDER BY weight DESC",
                (entity_type, entity_type),
            ).fetchall()
        else:
            rows = self.conn.execute(
                "SELECT * FROM knowledge_links ORDER BY timestamp DESC LIMIT 100"
            ).fetchall()
        return [dict(r) for r in rows]


def _now() -> str:
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).isoformat()


def _uuid() -> str:
    import uuid
    return str(uuid.uuid4())
