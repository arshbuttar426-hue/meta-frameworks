from __future__ import annotations
import json
import logging
from typing import Optional

from core.types import (
    AgentRole, Mission, MissionStatus, ResearchGrade,
    Hypothesis, Claim, PaperDraft, ResearchNote,
    KnowledgeNode, KnowledgeEdge, extract_string,
)
from memory.store import Store
from memory.journal import Journal
from memory.mission_store import MissionStore
from memory.evidence_db import EvidenceDB
from memory.knowledge_graph import KnowledgeGraph
from llm.client import LLMClient
from agents.gemma import GemmaComposer
from agents.smolm import SmolLM3
from agents.phi import Phi4Mini
from agents.vibe import VibeThinker
from lifecycle.mission import MissionSystem
from lifecycle.debate import DebateProtocol
from lifecycle.paper import PaperWorkflow

logger = logging.getLogger(__name__)


class ResearchLifecycle:
    def __init__(self, store: Store, llm: LLMClient, journal: Journal):
        self.store = store
        self.llm = llm
        self.journal = journal

        self.gemma = GemmaComposer(llm, journal)
        self.smolm = SmolLM3(llm, journal)
        self.phi = Phi4Mini(llm, journal)
        self.vibe = VibeThinker(llm, journal)

        self.mission_sys = MissionSystem(store, llm, journal)
        self.evidence = EvidenceDB(store)
        self.graph = KnowledgeGraph(store)

        self.debate = DebateProtocol(
            store, journal, self.gemma, self.smolm, self.phi, self.vibe,
        )
        self.paper_workflow = PaperWorkflow(
            store, journal, self.gemma, self.smolm, self.phi, self.vibe,
        )

    def run(self, question: str) -> dict:
        logger.info(f"=== Research Lifecycle Start: {question[:80]} ===")
        self.journal.write(
            agent=AgentRole.GEMMA,
            action="lifecycle_start",
            reason=f"New research initiated",
            input_summary=question,
            next_action="mission_planning",
        )

        mission = self._phase_mission_planning(question)
        extracted_claims, claims_for_review, contradictions = self._phase_evidence_collection(mission)
        debate_rounds = self._phase_debate(mission, claims_for_review, contradictions)
        hypothesis = self._phase_analysis(mission, debate_rounds, extracted_claims, contradictions)
        paper = self._phase_paper(mission)
        self._phase_knowledge_update(mission, hypothesis)

        self.mission_sys.update_status(mission.mission_id, MissionStatus.COMPLETED)
        self.journal.write(
            agent=AgentRole.GEMMA,
            action="lifecycle_complete",
            reason=f"Research lifecycle completed for {mission.mission_id}",
            input_summary=question,
            output_summary=json.dumps({
                "mission_id": mission.mission_id,
                "paper_id": paper.paper_id if paper else None,
                "notes_count": len(self.mission_sys.get_notes(mission.mission_id)),
            }),
            mission_id=mission.mission_id,
        )
        return {
            "mission": mission,
            "debate_rounds": len(debate_rounds),
            "paper": paper,
        }

    def _phase_mission_planning(self, question: str) -> Mission:
        logger.info("Phase 1: Mission Planning")
        mission = self.mission_sys.formulate(question)
        self.mission_sys.update_status(mission.mission_id, MissionStatus.ASSIGNED)
        return mission

    def _phase_evidence_collection(self, mission: Mission) -> tuple[list, list, dict]:
        logger.info("Phase 2: Evidence Collection (Chain: SmolLM3 -> VibeThinker -> Phi-4)")
        self.mission_sys.update_status(mission.mission_id, MissionStatus.IN_PROGRESS)

        context = f"Research objective: {mission.objective}\nScope: {mission.scope}"

        extraction = self.smolm.extract_evidence(
            source_text=context,
            source_id=f"mission_{mission.mission_id[:8]}",
        )
        self.journal.write(
            agent=AgentRole.SMOLM3,
            action="chain_link_1_extraction",
            reason="First link: extracted evidence from source",
            input_summary=context[:200],
            output_summary=str(extraction)[:300],
            mission_id=mission.mission_id,
            next_action="chain_vibe_thinker",
            metadata={"chain_position": 1, "chain_total": 4},
        )

        extracted_claims = []
        if isinstance(extraction, list):
            for item in extraction:
                stmt = (extract_string(item, "statement", "Statement", "claim", "Claim")
                        or str(item))
                claim = self.evidence.record_claim(
                    statement=stmt,
                    source_agent=AgentRole.SMOLM3,
                )
                extracted_claims.append(claim)
        elif isinstance(extraction, dict) and "error" not in extraction:
            stmt = (extract_string(extraction, "statement", "Statement", "claim", "Claim")
                    or str(extraction))
            claim = self.evidence.record_claim(
                statement=stmt,
                source_agent=AgentRole.SMOLM3,
            )
            extracted_claims.append(claim)

        alternatives = self.vibe.generate_hypotheses(
            context,
            [c.statement for c in extracted_claims[:5]] or [mission.objective],
        )
        self.journal.write(
            agent=AgentRole.VIBE,
            action="chain_link_2_hypotheses",
            reason="Second link: generated alternative hypotheses from extracted evidence",
            input_summary=str(extraction)[:200],
            output_summary=str(alternatives)[:300],
            mission_id=mission.mission_id,
            next_action="chain_phi_review",
            metadata={"chain_position": 2, "chain_total": 4},
        )
        self.mission_sys.add_note(
            mission.mission_id,
            "Alternative Hypotheses (from SmolLM3 extraction)",
            json.dumps(alternatives, indent=2),
            AgentRole.VIBE,
        )

        claims_for_review = [
            {"statement": c.statement, "confidence": c.confidence}
            for c in extracted_claims
        ]
        contradictions = self.phi.detect_contradictions(claims_for_review)
        self.journal.write(
            agent=AgentRole.PHI4,
            action="chain_link_3_contradiction_check",
            reason="Third link: checked extracted claims for contradictions",
            input_summary=str(claims_for_review)[:200],
            output_summary=str(contradictions)[:300],
            mission_id=mission.mission_id,
            next_action="chain_gemma_synthesis",
            metadata={"chain_position": 3, "chain_total": 4},
        )

        return extracted_claims, claims_for_review, contradictions

    def _phase_debate(self, mission: Mission, claims_for_review: list,
                      contradictions: dict) -> list:
        logger.info("Phase 3: Internal Debate")
        evidence_dicts = claims_for_review
        if isinstance(contradictions, dict) and "contradictions" in contradictions:
            for c in contradictions["contradictions"]:
                evidence_dicts.append({"statement": str(c), "confidence": 0.0})

        debate_rounds = self.debate.conduct(
            mission, mission.objective, evidence_dicts,
        )
        return debate_rounds

    def _phase_analysis(self, mission: Mission, debate_rounds: list,
                        extracted_claims: list, contradictions: dict) -> Hypothesis:
        logger.info("Phase 4: Analysis (Gemma synthesizes chain output)")
        debate_summary = "\n".join(
            f"Round {r.round_number}: conf={r.confidence:.2f} agreed={r.agreement}"
            for r in debate_rounds
        )
        chain_context = {
            "evidence_from_smolm": [c.statement for c in extracted_claims],
            "contradictions_from_phi": contradictions,
            "debate_summary": debate_summary,
        }

        synthesis = self.gemma.synthesize(
            [{"chain_context": chain_context, "debate": debate_summary}],
            mission.objective,
        )
        self.journal.write(
            agent=AgentRole.GEMMA,
            action="chain_link_4_synthesis",
            reason="Fourth link: synthesized all chain outputs into conclusion",
            input_summary=str(chain_context)[:200],
            output_summary=str(synthesis)[:300],
            mission_id=mission.mission_id,
            next_action="paper_draft",
            metadata={"chain_position": 4, "chain_total": 4},
        )

        synthesis_text = json.dumps(synthesis, indent=2) if isinstance(synthesis, dict) else synthesis
        self.mission_sys.add_note(
            mission.mission_id,
            "Synthesis (from chain: Smol->Vibe->Phi->Gemma)",
            str(synthesis_text)[:2000],
            AgentRole.GEMMA,
        )

        hypothesis = Hypothesis(
            statement=str(synthesis.get("conclusion", synthesis)) if isinstance(synthesis, dict) else synthesis,
            proposed_by=AgentRole.GEMMA,
        )
        self.store.save_hypothesis(hypothesis)
        return hypothesis

    def _phase_paper(self, mission: Mission) -> Optional[PaperDraft]:
        logger.info("Phase 5: Paper Draft")
        notes = self.mission_sys.get_notes(mission.mission_id)
        claims = self.store.search_claims(mission.objective)
        claims_summary = {
            "total_claims": len(claims),
            "claims": [
                {"statement": c.statement, "confidence": c.confidence}
                for c in claims[:10]
            ],
        } if claims else None

        paper = self.paper_workflow.draft(mission, notes, claims_summary)
        paper = self.paper_workflow.review(paper)

        if not paper.reviewer_approved:
            paper = self.paper_workflow.revise(paper)
            paper = self.paper_workflow.review(paper)

        paper = self.paper_workflow.finalize(paper)
        return paper

    def _phase_knowledge_update(self, mission: Mission, hypothesis: Hypothesis) -> None:
        logger.info("Phase 6: Knowledge Graph Update")
        concept_nodes = self.graph.find_nodes(mission.objective[:50])
        if not concept_nodes:
            node = self.graph.add_node(
                label=mission.objective[:100],
                node_type="research_question",
                confidence=hypothesis.confidence,
                grade=hypothesis.grade,
            )
            finding_node = self.graph.add_node(
                label=str(hypothesis.statement)[:100],
                node_type="finding",
                confidence=hypothesis.confidence,
            )
            self.graph.add_edge(node.node_id, finding_node.node_id, "resulted_in")

    def status_report(self) -> dict:
        active_missions = self.mission_sys.missions.list_active()
        completed = self.mission_sys.missions.list_by_status(MissionStatus.COMPLETED)
        hypotheses = self.store.list_hypotheses()
        nodes, edges = self.store.get_graph()

        return {
            "active_missions": len(active_missions),
            "completed_missions": len(completed),
            "hypotheses": len(hypotheses),
            "knowledge_graph": {"nodes": len(nodes), "edges": len(edges)},
            "journal_entries": len(self.store.get_journal(limit=10000)),
            "recent_missions": [
                {"id": m.mission_id[:8], "objective": m.objective[:60], "status": m.status.value}
                for m in active_missions[:5]
            ],
        }
