from __future__ import annotations
import json
import logging
from typing import Optional

from core.types import (
    AgentRole, DebateRound, Mission, JournalEntry,
)
from memory.store import Store
from memory.journal import Journal
from agents.gemma import GemmaComposer
from agents.smolm import SmolLM3
from agents.phi import Phi4Mini
from agents.vibe import VibeThinker

logger = logging.getLogger(__name__)


class DebateProtocol:
    def __init__(self, store: Store, journal: Journal,
                 gemma: GemmaComposer, smolm: SmolLM3,
                 phi: Phi4Mini, vibe: VibeThinker,
                 max_rounds: int = 5):
        self.store = store
        self.journal = journal
        self.gemma = gemma
        self.smolm = smolm
        self.phi = phi
        self.vibe = vibe
        self.max_rounds = max_rounds

    def conduct(self, mission: Mission, initial_proposal: str,
                evidence: list[dict]) -> list[DebateRound]:
        logger.info(f"Starting debate for mission {mission.mission_id}")
        rounds: list[DebateRound] = []
        current_proposal = initial_proposal
        target = mission.confidence_target

        for r in range(1, self.max_rounds + 1):
            debate_round = self._run_round(r, current_proposal, evidence)
            rounds.append(debate_round)
            self.store.save_debate_round(mission.mission_id, debate_round)

            self.journal.write(
                agent=AgentRole.GEMMA,
                action="debate_round",
                reason=f"Debate round {r}/{self.max_rounds} completed",
                input_summary=f"Proposal: {current_proposal[:200]}",
                output_summary=json.dumps({
                    "round": r,
                    "confidence": debate_round.confidence,
                    "agreement": debate_round.agreement,
                }),
                confidence=debate_round.confidence,
                mission_id=mission.mission_id,
            )

            if debate_round.agreement:
                logger.info(f"Consensus reached at round {r}")
                break

            current_proposal = debate_round.revision or debate_round.proposal

        return rounds

    def _run_round(self, round_num: int, proposal: str,
                   evidence: list[dict]) -> DebateRound:
        evidence_summary = evidence if isinstance(evidence, str) else json.dumps(evidence, indent=2)

        critique = self.phi.critique_hypothesis(proposal, evidence)
        alternative = self.vibe.generate_hypotheses(
            proposal, [e.get("claim", "") for e in (evidence if isinstance(evidence, list) else [])]
        )
        revision_prompt = (
            f"Original proposal: {proposal}\n\n"
            f"Reviewer critique: {critique}\n\n"
            f"Alternative ideas: {alternative}\n\n"
            f"Revise the proposal to address the critique while incorporating "
            f"stronger evidence. Maintain scientific rigor."
        )
        revision = self.gemma.think(revision_prompt, temperature=0.5)

        confidence = self._estimate_confidence(critique, proposal)

        agreement = confidence >= 0.7

        return DebateRound(
            round_number=round_num,
            proposal=proposal,
            evidence_summary=str(evidence_summary)[:500],
            critique=str(critique)[:500],
            alternative=str(alternative)[:500],
            revision=str(revision)[:500],
            confidence=confidence,
            agreement=agreement,
        )

    def _estimate_confidence(self, critique: dict | str, proposal: str) -> float:
        if isinstance(critique, dict):
            return critique.get("confidence", 0.5)
        critic = self.phi.critique_hypothesis(proposal, [])
        if isinstance(critic, dict):
            return critic.get("confidence", 0.5)
        return 0.5

    def get_debate_history(self, mission_id: str) -> list[DebateRound]:
        return self.store.get_debate_rounds(mission_id)

    def summarize_debate(self, mission_id: str) -> str:
        rounds = self.get_debate_history(mission_id)
        if not rounds:
            return "No debate records found."
        lines = [f"Debate for mission {mission_id}: {len(rounds)} rounds"]
        for r in rounds:
            status = "AGREED" if r.agreement else "DISPUTED"
            lines.append(
                f"  Round {r.round_number}: conf={r.confidence:.2f} [{status}]"
            )
        final = rounds[-1]
        lines.append(f"Final confidence: {final.confidence:.2f}")
        lines.append("Consensus reached" if final.agreement else "Disagreement persists")
        return "\n".join(lines)
