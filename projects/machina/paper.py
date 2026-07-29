from __future__ import annotations
import json
import logging
from datetime import datetime, timezone
from typing import Optional

from core.types import (
    AgentRole, PaperDraft, ResearchGrade, Mission, ResearchNote,
)
from memory.store import Store
from memory.journal import Journal
from agents.gemma import GemmaComposer
from agents.smolm import SmolLM3
from agents.phi import Phi4Mini
from agents.vibe import VibeThinker

logger = logging.getLogger(__name__)


class PaperWorkflow:
    def __init__(self, store: Store, journal: Journal,
                 gemma: GemmaComposer, smolm: SmolLM3,
                 phi: Phi4Mini, vibe: VibeThinker):
        self.store = store
        self.journal = journal
        self.gemma = gemma
        self.smolm = smolm
        self.phi = phi
        self.vibe = vibe

    def draft(self, mission: Mission, notes: list[ResearchNote],
              claims_summary: dict | None = None) -> PaperDraft:
        self.journal.write(
            agent=AgentRole.GEMMA,
            action="paper_draft_start",
            reason=f"Starting draft for mission {mission.mission_id}",
            input_summary=mission.objective,
            mission_id=mission.mission_id,
        )

        notes_text = "\n\n".join(
            f"[{n.agent.value}] {n.title}: {n.content[:500]}"
            for n in notes
        )

        draft_prompt = (
            f"Mission objective: {mission.objective}\n"
            f"Scope: {mission.scope}\n\n"
            f"Research Notes:\n{notes_text}\n\n"
            f"Claims summary: {claims_summary or 'N/A'}\n\n"
            "Write a paper draft as structured JSON with these sections:\n"
            "1. abstract (brief summary)\n"
            "2. introduction (motivation and question)\n"
            "3. methodology (approach taken)\n"
            "4. findings (results with confidence levels)\n"
            "5. discussion (interpretation and limitations)\n"
            "6. open_questions\n"
            "7. conclusion\n\n"
            "Each section should expose confidence levels and uncertainty. "
            "Never overclaim."
        )

        draft_result = self.gemma.think(draft_prompt, temperature=0.4, structured=True)

        if isinstance(draft_result, dict) and "error" not in draft_result:
            sections = draft_result
        else:
            sections = {"abstract": "Draft pending...", "body": str(draft_result)[:2000]}

        paper = PaperDraft(
            mission_id=mission.mission_id,
            title=f"Research Report: {mission.objective[:80]}",
            abstract=str(sections.get("abstract", "")),
            sections=sections,
            authors=[
                AgentRole.GEMMA,
                AgentRole.SMOLM3,
                AgentRole.PHI4,
                AgentRole.VIBE,
            ],
        )
        self.store.save_paper(paper)

        self.journal.write(
            agent=AgentRole.GEMMA,
            action="paper_draft_complete",
            reason="Initial paper draft written",
            input_summary=mission.objective,
            output_summary=json.dumps({"paper_id": paper.paper_id, "sections": list(sections.keys())}),
            confidence=0.5,
            mission_id=mission.mission_id,
            next_action="peer_review",
        )
        return paper

    def review(self, paper: PaperDraft) -> PaperDraft:
        self.journal.write(
            agent=AgentRole.PHI4,
            action="paper_review_start",
            reason=f"Reviewing paper {paper.paper_id}",
            mission_id=paper.mission_id,
        )

        full_text = "\n\n".join(
            f"## {k}\n{v}" for k, v in paper.sections.items()
        )
        evidence_summary = {"citations": paper.citations}

        review = self.phi.review_conclusion(full_text, evidence_summary)
        if isinstance(review, dict) and "error" not in review:
            verdict = review.get("verdict", "revision")
            concerns = review.get("concerns", [])
            reviewer_confidence = review.get("confidence", 0.5)

            paper.reviewer_approved = verdict == "pass"
            paper.confidence = reviewer_confidence
            paper.status = verdict
            paper.updated_at = datetime.now(timezone.utc).isoformat()

            self.journal.write(
                agent=AgentRole.PHI4,
                action="paper_review_complete",
                reason=f"Review verdict: {verdict}",
                input_summary=paper.title,
                output_summary=json.dumps({"verdict": verdict, "concerns": concerns}),
                confidence=reviewer_confidence,
                mission_id=paper.mission_id,
                next_action="revision" if verdict != "pass" else "publication_candidate",
            )

        self.store.save_paper(paper)
        return paper

    def revise(self, paper: PaperDraft, review_result: dict | None = None) -> PaperDraft:
        self.journal.write(
            agent=AgentRole.GEMMA,
            action="paper_revision_start",
            reason=f"Revising paper {paper.paper_id} based on review",
            mission_id=paper.mission_id,
        )

        if not review_result:
            review_result = {"verdict": "revision", "concerns": ["Review data unavailable"]}

        full_text = "\n\n".join(
            f"## {k}\n{v}" for k, v in paper.sections.items()
        )
        revision_prompt = (
            f"Original draft:\n{full_text}\n\n"
            f"Reviewer feedback:\n{json.dumps(review_result, indent=2)}\n\n"
            "Revise the paper addressing ALL reviewer concerns. "
            "Maintain scientific rigor. Expose remaining uncertainties."
        )
        revision = self.gemma.think(revision_prompt, temperature=0.4)

        paper.sections["revision_notes"] = str(revision)[:2000]
        paper.status = "revised"
        paper.updated_at = datetime.now(timezone.utc).isoformat()
        self.store.save_paper(paper)

        self.journal.write(
            agent=AgentRole.GEMMA,
            action="paper_revision_complete",
            reason=f"Paper {paper.paper_id} revised",
            input_summary=paper.title,
            mission_id=paper.mission_id,
            next_action="human_review",
        )
        return paper

    def finalize(self, paper: PaperDraft) -> PaperDraft:
        paper.status = "publication_candidate"
        paper.updated_at = datetime.now(timezone.utc).isoformat()
        self.store.save_paper(paper)

        self.journal.write(
            agent=AgentRole.GEMMA,
            action="paper_finalized",
            reason=f"Paper {paper.paper_id} ready for human review",
            input_summary=paper.title,
            output_summary=json.dumps({
                "paper_id": paper.paper_id,
                "confidence": paper.confidence,
                "status": paper.status,
            }),
            confidence=paper.confidence,
            mission_id=paper.mission_id,
        )
        return paper
