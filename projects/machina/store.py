# Copyright © 2026 Arsh Buttar. All rights reserved. Confidential and proprietary.
# Unauthorized copying, distribution, or use of this work is prohibited.

from __future__ import annotations
import json
import sqlite3
import threading
from pathlib import Path
from typing import Any, Optional

from core.types import (
    Claim, Evidence, Hypothesis, KnowledgeNode, KnowledgeEdge,
    Mission, JournalEntry, ResearchNote, PaperDraft, DebateRound,
    AgentRole, MissionStatus, ResearchGrade,
)


class Store:
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
        return self._local.conn

    def _init_db(self) -> None:
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        conn = self.conn
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS missions (
                mission_id TEXT PRIMARY KEY,
                objective TEXT NOT NULL,
                scope TEXT DEFAULT '',
                deadline TEXT,
                confidence_target REAL DEFAULT 0.8,
                allowed_sources TEXT DEFAULT '[]',
                deliverables TEXT DEFAULT '[]',
                status TEXT DEFAULT 'draft',
                assigned_agents TEXT DEFAULT '[]',
                dependencies TEXT DEFAULT '[]',
                parent_question TEXT DEFAULT '',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                completed_at TEXT
            );
            CREATE TABLE IF NOT EXISTS claims (
                claim_id TEXT PRIMARY KEY,
                statement TEXT NOT NULL,
                claim_type TEXT DEFAULT 'fact',
                confidence REAL DEFAULT 0.0,
                grade TEXT DEFAULT 'unknown',
                evidence_ids TEXT DEFAULT '[]',
                contradictions TEXT DEFAULT '[]',
                source_agent TEXT,
                timestamp TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS evidence (
                claim_id TEXT NOT NULL,
                source_id TEXT NOT NULL,
                source_url TEXT,
                source_title TEXT,
                retrieved_at TEXT,
                content_hash TEXT,
                confidence REAL DEFAULT 0.0,
                evidence_level TEXT DEFAULT 'single_source',
                reasoning_chain TEXT DEFAULT '[]',
                unknowns TEXT DEFAULT '[]',
                assumptions TEXT DEFAULT '[]',
                supporting INTEGER DEFAULT 1,
                agent_id TEXT DEFAULT 'smolm3_research_associate',
                timestamp TEXT NOT NULL,
                PRIMARY KEY (claim_id, source_id)
            );
            CREATE TABLE IF NOT EXISTS hypotheses (
                hypothesis_id TEXT PRIMARY KEY,
                statement TEXT NOT NULL,
                grade TEXT DEFAULT 'hypothesis',
                supporting_claims TEXT DEFAULT '[]',
                contradicting_claims TEXT DEFAULT '[]',
                confidence REAL DEFAULT 0.0,
                proposed_by TEXT DEFAULT 'gemma_composer',
                timestamp TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS knowledge_nodes (
                node_id TEXT PRIMARY KEY,
                label TEXT NOT NULL,
                node_type TEXT DEFAULT 'concept',
                attributes TEXT DEFAULT '{}',
                confidence REAL DEFAULT 0.0,
                grade TEXT DEFAULT 'unknown',
                timestamp TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS knowledge_edges (
                edge_id TEXT PRIMARY KEY,
                source_id TEXT NOT NULL,
                target_id TEXT NOT NULL,
                relation TEXT NOT NULL,
                weight REAL DEFAULT 1.0,
                evidence_ids TEXT DEFAULT '[]',
                timestamp TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS journal (
                entry_id TEXT PRIMARY KEY,
                timestamp TEXT NOT NULL,
                agent TEXT NOT NULL,
                action TEXT DEFAULT '',
                reason TEXT DEFAULT '',
                input_summary TEXT DEFAULT '',
                output_summary TEXT DEFAULT '',
                confidence REAL DEFAULT 0.0,
                sources TEXT DEFAULT '[]',
                next_action TEXT DEFAULT '',
                mission_id TEXT,
                metadata TEXT DEFAULT '{}'
            );
            CREATE TABLE IF NOT EXISTS research_notes (
                note_id TEXT PRIMARY KEY,
                mission_id TEXT,
                title TEXT DEFAULT '',
                content TEXT DEFAULT '',
                agent TEXT DEFAULT 'gemma_composer',
                tags TEXT DEFAULT '[]',
                timestamp TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS papers (
                paper_id TEXT PRIMARY KEY,
                mission_id TEXT,
                title TEXT DEFAULT '',
                abstract TEXT DEFAULT '',
                sections TEXT DEFAULT '{}',
                citations TEXT DEFAULT '[]',
                authors TEXT DEFAULT '[]',
                status TEXT DEFAULT 'draft',
                confidence REAL DEFAULT 0.0,
                grade TEXT DEFAULT 'unknown',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                reviewer_approved INTEGER DEFAULT 0
            );
            CREATE TABLE IF NOT EXISTS debate_rounds (
                mission_id TEXT NOT NULL,
                round_number INTEGER NOT NULL,
                proposal TEXT DEFAULT '',
                evidence_summary TEXT DEFAULT '',
                critique TEXT DEFAULT '',
                alternative TEXT DEFAULT '',
                revision TEXT DEFAULT '',
                confidence REAL DEFAULT 0.0,
                agreement INTEGER DEFAULT 0,
                timestamp TEXT NOT NULL,
                PRIMARY KEY (mission_id, round_number)
            );
            CREATE TABLE IF NOT EXISTS meta (
                key TEXT PRIMARY KEY,
                value TEXT
            );
        """)
        conn.commit()

    def save_mission(self, mission: Mission) -> None:
        self.conn.execute(
            """INSERT OR REPLACE INTO missions
               (mission_id, objective, scope, deadline, confidence_target,
                allowed_sources, deliverables, status, assigned_agents,
                dependencies, parent_question, created_at, updated_at, completed_at)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                mission.mission_id, mission.objective, mission.scope,
                mission.deadline, mission.confidence_target,
                json.dumps(mission.allowed_sources),
                json.dumps(mission.deliverables),
                mission.status.value,
                json.dumps([a.value for a in mission.assigned_agents]),
                json.dumps(mission.dependencies),
                mission.parent_question,
                mission.created_at, mission.updated_at, mission.completed_at,
            ),
        )
        self.conn.commit()

    def get_mission(self, mission_id: str) -> Optional[Mission]:
        row = self.conn.execute(
            "SELECT * FROM missions WHERE mission_id = ?", (mission_id,)
        ).fetchone()
        if not row:
            return None
        return self._row_to_mission(row)

    def list_missions(self, status: Optional[str] = None) -> list[Mission]:
        if status:
            rows = self.conn.execute(
                "SELECT * FROM missions WHERE status = ? ORDER BY created_at DESC",
                (status,),
            ).fetchall()
        else:
            rows = self.conn.execute(
                "SELECT * FROM missions ORDER BY created_at DESC"
            ).fetchall()
        return [self._row_to_mission(r) for r in rows]

    def save_claim(self, claim: Claim) -> None:
        self.conn.execute(
            """INSERT OR REPLACE INTO claims
               (claim_id, statement, claim_type, confidence, grade,
                evidence_ids, contradictions, source_agent, timestamp, updated_at)
               VALUES (?,?,?,?,?,?,?,?,?,?)""",
            (
                claim.claim_id, claim.statement, claim.claim_type.value,
                claim.confidence, claim.grade.value,
                json.dumps(claim.evidence_ids),
                json.dumps(claim.contradictions),
                claim.source_agent.value if claim.source_agent else None,
                claim.timestamp, claim.updated_at,
            ),
        )
        self.conn.commit()

    def get_claim(self, claim_id: str) -> Optional[Claim]:
        row = self.conn.execute(
            "SELECT * FROM claims WHERE claim_id = ?", (claim_id,)
        ).fetchone()
        if not row:
            return None
        return self._row_to_claim(row)

    def search_claims(self, query: str) -> list[Claim]:
        rows = self.conn.execute(
            "SELECT * FROM claims WHERE statement LIKE ? ORDER BY confidence DESC",
            (f"%{query}%",),
        ).fetchall()
        return [self._row_to_claim(r) for r in rows]

    def save_evidence(self, evidence: Evidence) -> None:
        self.conn.execute(
            """INSERT OR REPLACE INTO evidence
               (claim_id, source_id, source_url, source_title, retrieved_at,
                content_hash, confidence, evidence_level, reasoning_chain,
                unknowns, assumptions, supporting, agent_id, timestamp)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                evidence.claim_id, evidence.source.source_id,
                evidence.source.source_url, evidence.source.source_title,
                evidence.source.retrieved_at, evidence.source.content_hash,
                evidence.confidence, evidence.evidence_level.value,
                json.dumps(evidence.reasoning_chain),
                json.dumps(evidence.unknowns),
                json.dumps(evidence.assumptions),
                1 if evidence.supporting else 0,
                evidence.agent_id.value,
                evidence.timestamp,
            ),
        )
        self.conn.commit()

    def get_evidence_for_claim(self, claim_id: str) -> list[Evidence]:
        rows = self.conn.execute(
            "SELECT * FROM evidence WHERE claim_id = ?", (claim_id,)
        ).fetchall()
        return [self._row_to_evidence(r) for r in rows]

    def save_hypothesis(self, hypothesis: Hypothesis) -> None:
        self.conn.execute(
            """INSERT OR REPLACE INTO hypotheses
               (hypothesis_id, statement, grade, supporting_claims,
                contradicting_claims, confidence, proposed_by, timestamp)
               VALUES (?,?,?,?,?,?,?,?)""",
            (
                hypothesis.hypothesis_id, hypothesis.statement,
                hypothesis.grade.value,
                json.dumps(hypothesis.supporting_claims),
                json.dumps(hypothesis.contradicting_claims),
                hypothesis.confidence,
                hypothesis.proposed_by.value,
                hypothesis.timestamp,
            ),
        )
        self.conn.commit()

    def list_hypotheses(self) -> list[Hypothesis]:
        rows = self.conn.execute(
            "SELECT * FROM hypotheses ORDER BY confidence DESC"
        ).fetchall()
        return [self._row_to_hypothesis(r) for r in rows]

    def save_node(self, node: KnowledgeNode) -> None:
        self.conn.execute(
            """INSERT OR REPLACE INTO knowledge_nodes
               (node_id, label, node_type, attributes, confidence, grade, timestamp)
               VALUES (?,?,?,?,?,?,?)""",
            (
                node.node_id, node.label, node.node_type,
                json.dumps(node.attributes), node.confidence,
                node.grade.value, node.timestamp,
            ),
        )
        self.conn.commit()

    def save_edge(self, edge: KnowledgeEdge) -> None:
        self.conn.execute(
            """INSERT OR REPLACE INTO knowledge_edges
               (edge_id, source_id, target_id, relation, weight, evidence_ids, timestamp)
               VALUES (?,?,?,?,?,?,?)""",
            (
                edge.edge_id, edge.source_id, edge.target_id,
                edge.relation, edge.weight,
                json.dumps(edge.evidence_ids), edge.timestamp,
            ),
        )
        self.conn.commit()

    def get_graph(self) -> tuple[list[KnowledgeNode], list[KnowledgeEdge]]:
        nodes = [
            self._row_to_node(r)
            for r in self.conn.execute("SELECT * FROM knowledge_nodes").fetchall()
        ]
        edges = [
            self._row_to_edge(r)
            for r in self.conn.execute("SELECT * FROM knowledge_edges").fetchall()
        ]
        return nodes, edges

    def save_journal(self, entry: JournalEntry) -> None:
        self.conn.execute(
            """INSERT INTO journal
               (entry_id, timestamp, agent, action, reason, input_summary,
                output_summary, confidence, sources, next_action, mission_id, metadata)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                entry.entry_id, entry.timestamp, entry.agent.value,
                entry.action, entry.reason, entry.input_summary,
                entry.output_summary, entry.confidence,
                json.dumps(entry.sources), entry.next_action,
                entry.mission_id, json.dumps(entry.metadata),
            ),
        )
        self.conn.commit()

    def get_journal(self, limit: int = 100, agent: Optional[str] = None) -> list[JournalEntry]:
        if agent:
            rows = self.conn.execute(
                "SELECT * FROM journal WHERE agent = ? ORDER BY timestamp DESC LIMIT ?",
                (agent, limit),
            ).fetchall()
        else:
            rows = self.conn.execute(
                "SELECT * FROM journal ORDER BY timestamp DESC LIMIT ?", (limit,)
            ).fetchall()
        return [self._row_to_journal(r) for r in reversed(rows)]

    def save_note(self, note: ResearchNote) -> None:
        self.conn.execute(
            """INSERT OR REPLACE INTO research_notes
               (note_id, mission_id, title, content, agent, tags, timestamp)
               VALUES (?,?,?,?,?,?,?)""",
            (
                note.note_id, note.mission_id, note.title, note.content,
                note.agent.value, json.dumps(note.tags), note.timestamp,
            ),
        )
        self.conn.commit()

    def get_notes(self, mission_id: str) -> list[ResearchNote]:
        rows = self.conn.execute(
            "SELECT * FROM research_notes WHERE mission_id = ? ORDER BY timestamp",
            (mission_id,),
        ).fetchall()
        return [self._row_to_note(r) for r in rows]

    def save_paper(self, paper: PaperDraft) -> None:
        self.conn.execute(
            """INSERT OR REPLACE INTO papers
               (paper_id, mission_id, title, abstract, sections, citations,
                authors, status, confidence, grade, created_at, updated_at,
                reviewer_approved)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                paper.paper_id, paper.mission_id, paper.title,
                paper.abstract, json.dumps(paper.sections),
                json.dumps(paper.citations),
                json.dumps([a.value for a in paper.authors]),
                paper.status, paper.confidence, paper.grade.value,
                paper.created_at, paper.updated_at,
                1 if paper.reviewer_approved else 0,
            ),
        )
        self.conn.commit()

    def get_paper(self, paper_id: str) -> Optional[PaperDraft]:
        row = self.conn.execute(
            "SELECT * FROM papers WHERE paper_id = ?", (paper_id,)
        ).fetchone()
        return self._row_to_paper(row) if row else None

    def save_debate_round(self, mission_id: str, round_data: DebateRound) -> None:
        self.conn.execute(
            """INSERT OR REPLACE INTO debate_rounds
               (mission_id, round_number, proposal, evidence_summary,
                critique, alternative, revision, confidence, agreement, timestamp)
               VALUES (?,?,?,?,?,?,?,?,?,?)""",
            (
                mission_id, round_data.round_number, round_data.proposal,
                round_data.evidence_summary, round_data.critique,
                round_data.alternative, round_data.revision,
                round_data.confidence, 1 if round_data.agreement else 0,
                round_data.timestamp,
            ),
        )
        self.conn.commit()

    def get_debate_rounds(self, mission_id: str) -> list[DebateRound]:
        rows = self.conn.execute(
            "SELECT * FROM debate_rounds WHERE mission_id = ? ORDER BY round_number",
            (mission_id,),
        ).fetchall()
        return [self._row_to_debate(r) for r in rows]

    def set_meta(self, key: str, value: str) -> None:
        self.conn.execute(
            "INSERT OR REPLACE INTO meta (key, value) VALUES (?, ?)",
            (key, value),
        )
        self.conn.commit()

    def get_meta(self, key: str) -> Optional[str]:
        row = self.conn.execute(
            "SELECT value FROM meta WHERE key = ?", (key,)
        ).fetchone()
        return row["value"] if row else None

    @staticmethod
    def _row_to_mission(row: sqlite3.Row) -> Mission:
        return Mission(
            mission_id=row["mission_id"],
            objective=row["objective"],
            scope=row["scope"],
            deadline=row["deadline"],
            confidence_target=row["confidence_target"],
            allowed_sources=json.loads(row["allowed_sources"]),
            deliverables=json.loads(row["deliverables"]),
            status=MissionStatus(row["status"]),
            assigned_agents=[AgentRole(a) for a in json.loads(row["assigned_agents"])],
            dependencies=json.loads(row["dependencies"]),
            parent_question=row["parent_question"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
            completed_at=row["completed_at"],
        )

    @staticmethod
    def _row_to_claim(row: sqlite3.Row) -> Claim:
        return Claim(
            claim_id=row["claim_id"],
            statement=row["statement"],
            claim_type=ClaimType(row["claim_type"]),
            confidence=row["confidence"],
            grade=ResearchGrade(row["grade"]),
            evidence_ids=json.loads(row["evidence_ids"]),
            contradictions=json.loads(row["contradictions"]),
            source_agent=AgentRole(row["source_agent"]) if row["source_agent"] else None,
            timestamp=row["timestamp"],
            updated_at=row["updated_at"],
        )

    @staticmethod
    def _row_to_evidence(row: sqlite3.Row) -> Evidence:
        from core.types import Citation
        return Evidence(
            claim_id=row["claim_id"],
            source=Citation(
                source_id=row["source_id"],
                source_url=row["source_url"],
                source_title=row["source_title"],
                retrieved_at=row["retrieved_at"],
                content_hash=row["content_hash"],
            ),
            confidence=row["confidence"],
            evidence_level=EvidenceLevel(row["evidence_level"]),
            reasoning_chain=json.loads(row["reasoning_chain"]),
            unknowns=json.loads(row["unknowns"]),
            assumptions=json.loads(row["assumptions"]),
            supporting=bool(row["supporting"]),
            agent_id=AgentRole(row["agent_id"]),
            timestamp=row["timestamp"],
        )

    @staticmethod
    def _row_to_hypothesis(row: sqlite3.Row) -> Hypothesis:
        return Hypothesis(
            hypothesis_id=row["hypothesis_id"],
            statement=row["statement"],
            grade=ResearchGrade(row["grade"]),
            supporting_claims=json.loads(row["supporting_claims"]),
            contradicting_claims=json.loads(row["contradicting_claims"]),
            confidence=row["confidence"],
            proposed_by=AgentRole(row["proposed_by"]),
            timestamp=row["timestamp"],
        )

    @staticmethod
    def _row_to_node(row: sqlite3.Row) -> KnowledgeNode:
        return KnowledgeNode(
            node_id=row["node_id"],
            label=row["label"],
            node_type=row["node_type"],
            attributes=json.loads(row["attributes"]),
            confidence=row["confidence"],
            grade=ResearchGrade(row["grade"]),
            timestamp=row["timestamp"],
        )

    @staticmethod
    def _row_to_edge(row: sqlite3.Row) -> KnowledgeEdge:
        return KnowledgeEdge(
            edge_id=row["edge_id"],
            source_id=row["source_id"],
            target_id=row["target_id"],
            relation=row["relation"],
            weight=row["weight"],
            evidence_ids=json.loads(row["evidence_ids"]),
            timestamp=row["timestamp"],
        )

    @staticmethod
    def _row_to_journal(row: sqlite3.Row) -> JournalEntry:
        return JournalEntry(
            entry_id=row["entry_id"],
            timestamp=row["timestamp"],
            agent=AgentRole(row["agent"]),
            action=row["action"],
            reason=row["reason"],
            input_summary=row["input_summary"],
            output_summary=row["output_summary"],
            confidence=row["confidence"],
            sources=json.loads(row["sources"]),
            next_action=row["next_action"],
            mission_id=row["mission_id"],
            metadata=json.loads(row["metadata"]) if row["metadata"] else {},
        )

    @staticmethod
    def _row_to_note(row: sqlite3.Row) -> ResearchNote:
        return ResearchNote(
            note_id=row["note_id"],
            mission_id=row["mission_id"],
            title=row["title"],
            content=row["content"],
            agent=AgentRole(row["agent"]),
            tags=json.loads(row["tags"]),
            timestamp=row["timestamp"],
        )

    @staticmethod
    def _row_to_paper(row: sqlite3.Row) -> PaperDraft:
        return PaperDraft(
            paper_id=row["paper_id"],
            mission_id=row["mission_id"],
            title=row["title"],
            abstract=row["abstract"],
            sections=json.loads(row["sections"]),
            citations=json.loads(row["citations"]),
            authors=[AgentRole(a) for a in json.loads(row["authors"])],
            status=row["status"],
            confidence=row["confidence"],
            grade=ResearchGrade(row["grade"]),
            created_at=row["created_at"],
            updated_at=row["updated_at"],
            reviewer_approved=bool(row["reviewer_approved"]),
        )

    @staticmethod
    def _row_to_debate(row: sqlite3.Row) -> DebateRound:
        return DebateRound(
            round_number=row["round_number"],
            proposal=row["proposal"],
            evidence_summary=row["evidence_summary"],
            critique=row["critique"],
            alternative=row["alternative"],
            revision=row["revision"],
            confidence=row["confidence"],
            agreement=bool(row["agreement"]),
            timestamp=row["timestamp"],
        )
