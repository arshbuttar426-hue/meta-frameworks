from __future__ import annotations
import json
import logging
from typing import Any, Optional

from research_runtime.broker import MissionBroker
from research_runtime.blackboard import Blackboard
from research_runtime.ledger import EvidenceLedger
from research_runtime.trust import TrustEngine
from research_runtime.composite import CompositeManager
from research_runtime.genome import AgentGenome, MissionGenome
from research_runtime.journal import ResearchJournal
from research_runtime.reflection import ReflectionEngine
from research_runtime.debate import InternalDebate
from research_runtime.dashboard import RuntimeDashboard
from research_runtime.knowledge import KnowledgeAutoConnector
from research_runtime.persistence import RuntimeStore

logger = logging.getLogger("runtime.cli")


class RuntimeCLI:
    def __init__(self, store: RuntimeStore):
        self.store = store
        self.trust = TrustEngine(store)
        self.broker = MissionBroker(store, self.trust)
        self.blackboard = Blackboard(store)
        self.ledger = EvidenceLedger(store)
        self.composites = CompositeManager(store)
        self.journal = ResearchJournal(store)
        self.reflection = ReflectionEngine(store)
        self.debate = InternalDebate(store)
        self.dashboard = RuntimeDashboard(store)
        self.knowledge = KnowledgeAutoConnector(store)

    def cmd_dashboard(self, _args: Any) -> None:
        print(self.dashboard.overview())

    def cmd_mission_create(self, args: Any) -> None:
        mission = self.broker.create_mission(
            objective=args.objective,
            scope=getattr(args, "scope", ""),
            priority=getattr(args, "priority", 5),
            application=getattr(args, "application", "generic"),
            tags=getattr(args, "tags", "").split(",") if getattr(args, "tags", "") else None,
        )
        print(f"Created mission: {mission.mission_id}")
        print(f"  Objective: {mission.objective}")
        print(f"  State: {mission.current_state}")
        print(f"  Application: {mission.application}")

    def cmd_mission_list(self, args: Any) -> None:
        status = getattr(args, "status", None)
        missions = self.store.list_mission_genomes(status=status)
        if not missions:
            print("No missions found.")
            return
        print(f"{'ID':<12} {'State':<16} {'Priority':<10} {'Application':<14} {'Objective'}")
        print("-" * 100)
        for m in missions:
            print(f"{m.mission_id[:8]:<12} {m.current_state:<16} {m.priority:<10} {m.application:<14} {m.objective[:50]}")

    def cmd_mission_detail(self, args: Any) -> None:
        print(self.dashboard.mission_detail(args.mission_id))

    def cmd_mission_transition(self, args: Any) -> None:
        genome = self.store.get_mission_genome(args.mission_id)
        if not genome:
            print(f"Mission {args.mission_id} not found.")
            return
        genome.transition(args.state)
        self.store.save_mission_genome(genome)
        print(f"Mission {args.mission_id[:8]} → {args.state}")

    def cmd_task_assign(self, args: Any) -> None:
        task = self.broker.assign_task(
            mission_id=args.mission_id,
            capability=args.capability,
            inputs=json.loads(getattr(args, "inputs", "{}")),
            priority=getattr(args, "priority", 5),
        )
        print(f"Created task: {task.task_id}")
        router = self.broker.route_task(task)
        if router:
            print(f"Recommended agent: {router}")
        else:
            print("No eligible agent found for routing")

    def cmd_tasks(self, args: Any) -> None:
        mission_id = getattr(args, "mission_id", None)
        tasks = self.store.list_tasks(mission_id)
        if not tasks:
            print("No tasks found.")
            return
        print(f"{'Task ID':<12} {'Capability':<30} {'Status':<12} {'Retries':<8} {'Priority'}")
        print("-" * 80)
        for t in tasks:
            print(f"{t.task_id[:8]:<12} {t.capability[:28]:<30} {t.status:<12} {t.retry_count:<8} {t.priority}")

    def cmd_blackboard_write(self, args: Any) -> None:
        result = self.blackboard.write(
            mission_id=args.mission_id,
            section=args.section,
            agent=getattr(args, "agent", "user"),
            content=args.content,
        )
        print(f"Written to blackboard: {result}")

    def cmd_blackboard_read(self, args: Any) -> None:
        section = getattr(args, "section", None)
        entries = self.blackboard.read(args.mission_id, section)
        if not entries:
            print("No blackboard entries.")
            return
        print(f"Blackboard for {args.mission_id} (section: {section or 'all'}):")
        for e in entries:
            agent = e.get("agent", "?")
            sec = e.get("section", "?")
            content = e.get("content", "")[:80]
            print(f"  [{agent}] {sec}: {content}")

    def cmd_evidence_add(self, args: Any) -> None:
        record = self.ledger.record(
            mission_id=args.mission_id,
            claim=args.claim,
            source=getattr(args, "source", "cli"),
            agent=getattr(args, "agent", "user"),
            confidence=float(getattr(args, "confidence", 0.5)),
        )
        print(f"Evidence recorded: {record['evidence_id']}")
        print(f"  Content hash: {record['content_hash'][:16]}")

    def cmd_evidence_list(self, args: Any) -> None:
        entries = self.ledger.list(args.mission_id)
        if not entries:
            print("No evidence entries.")
            return
        print(f"{'ID':<12} {'Status':<12} {'Conf':<8} {'Source':<20} {'Claim'}")
        print("-" * 90)
        for e in entries[-20:]:
            print(f"{e.get('evidence_id', '?')[:8]:<12} {e.get('verification_status', '?'):<12} {e.get('confidence', 0):<8.2f} {e.get('source', '?')[:18]:<20} {e.get('claim', '')[:50]}")

    def cmd_evidence_verify(self, args: Any) -> None:
        result = self.ledger.verify_multiple(args.evidence_ids)
        for eid, status in result.items():
            print(f"  {eid[:8]}: {status['status']}")

    def cmd_trust(self, args: Any) -> None:
        agent = getattr(args, "agent", None)
        capability = getattr(args, "capability", None)
        if agent and capability:
            score = self.trust.reliability_bayesian(agent, capability)
            trust = self.trust.get_score(agent, capability)
            ci = self.trust.confidence_interval(agent, capability)
            print(f"Trust for {agent} / {capability}")
            print(f"  Bayesian reliability: {score:.3f}")
            print(f"  Tasks: {trust.get('total_tasks', 0)}")
            print(f"  Success rate: {trust.get('success_rate', 0.5):.2%}")
            print(f"  Avg latency: {trust.get('avg_latency_ms', 0):.0f}ms")
            print(f"  Confidence interval: ({ci[0]}, {ci[1]})")
        elif capability:
            agents = self.trust.compare_agents(capability)
            if not agents:
                print(f"No trust data for {capability}")
                return
            print(f"Agent rankings for '{capability}':")
            for a in agents:
                print(f"  {a['agent']:<20} reliability={a['reliability']:.3f}  tasks={a['total_tasks']}  latency={a['avg_latency_ms']:.0f}ms")
        else:
            all_agents = self.store.list_agent_genomes()
            print("Available agents:")
            for a in all_agents:
                print(f"  {a.agent_id} ({a.role.value})")

    def cmd_composite_list(self, _args: Any) -> None:
        composites = self.composites.list()
        if not composites:
            print("No composite capabilities registered.")
            return
        print(f"{'Name':<30} {'Version':<10} {'Steps':<8} {'Description'}")
        print("-" * 80)
        for c in composites:
            pipeline = json.loads(c["pipeline_json"])
            print(f"{c['name']:<30} {c.get('version', '?'):<10} {len(pipeline):<8} {c.get('description', '')[:50]}")

    def cmd_composite_register(self, args: Any) -> None:
        pipeline = json.loads(args.pipeline)
        validation = self.composites.validate_pipeline(pipeline)
        if not validation["valid"]:
            print("Pipeline validation failed:")
            for e in validation["errors"]:
                print(f"  - {e}")
            return
        self.composites.register(
            name=args.name,
            description=getattr(args, "description", ""),
            pipeline=pipeline,
            version=getattr(args, "version", "0.1.0"),
        )
        print(f"Registered composite: {args.name} ({validation['step_count']} steps)")

    def cmd_journal(self, args: Any) -> None:
        entry_type = getattr(args, "type", None)
        entries = self.journal.read(args.mission_id, entry_type)
        if not entries:
            print("No journal entries.")
            return
        for e in entries[-20:]:
            ts = e.get("timestamp", "?")[:19]
            et = e.get("entry_type", "?")
            agent = e.get("agent", "?")
            title = e.get("title", "")
            content = e.get("content", "")[:60]
            print(f"[{ts}] {et:<10} {agent:<20} {title} | {content}")

    def cmd_reflect(self, args: Any) -> None:
        evidence = self.ledger.list(args.mission_id)
        required = int(getattr(args, "required_evidence", 3))
        findings = self.reflection.full_analysis(args.mission_id, evidence, required)
        if not findings:
            print("No reflection findings.")
            return
        for f in findings:
            print(f"  [{f['severity']}] {f['type']}: {f['finding']}")

    def cmd_debate_status(self, args: Any) -> None:
        summary = self.debate.summary(args.mission_id)
        print(json.dumps(summary, indent=2))

    def cmd_debate_record(self, args: Any) -> None:
        self.debate.record_step(
            mission_id=args.mission_id,
            round_number=int(getattr(args, "round", 0)),
            step=args.step,
            agent=getattr(args, "agent", "system"),
            content=args.content,
            confidence=float(getattr(args, "confidence", 0.0)),
        )
        print(f"Debate step recorded: round {args.round}, step {args.step}")

    def cmd_knowledge_graph(self, args: Any) -> None:
        entity_id = getattr(args, "entity_id", None)
        entity_type = getattr(args, "entity_type", None)
        if entity_id or entity_type:
            links = self.knowledge.query(entity_type, entity_id)
        else:
            summary = self.knowledge.graph_summary()
            print(json.dumps(summary, indent=2))
            return

        if not links:
            print("No knowledge links found.")
            return
        print(f"{'Source':<20} {'Relation':<16} {'Target':<20} {'Weight'}")
        print("-" * 70)
        for link in links[:30]:
            src = link.get("source_id", "")[:18]
            tgt = link.get("target_id", "")[:18]
            rel = link.get("relation", "?")
            wt = link.get("weight", 0)
            print(f"{src:<20} {rel:<16} {tgt:<20} {wt}")

    def cmd_system_status(self, _args: Any) -> None:
        print(self.dashboard.system_status())
