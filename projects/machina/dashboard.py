from __future__ import annotations
import json
import textwrap
from datetime import datetime, timezone
from typing import Any, Optional

from research_runtime.persistence import RuntimeStore


class RuntimeDashboard:
    def __init__(self, store: RuntimeStore):
        self.store = store

    def overview(self) -> str:
        missions = self.store.list_mission_genomes()
        tasks_list = self.store.list_tasks()
        agents = self.store.list_agent_genomes()
        evidence_count = sum(
            len(self.store.list_evidence(m.mission_id)) for m in missions
        )

        state_counts: dict[str, int] = {}
        for m in missions:
            s = m.current_state
            state_counts[s] = state_counts.get(s, 0) + 1

        task_status: dict[str, int] = {}
        for t in tasks_list:
            task_status[t.status] = task_status.get(t.status, 0) + 1

        return self._render_overview(
            total_missions=len(missions),
            mission_states=state_counts,
            total_tasks=len(tasks_list),
            task_statuses=task_status,
            total_agents=len(agents),
            total_evidence=evidence_count,
        )

    def mission_detail(self, mission_id: str) -> str:
        genome = self.store.get_mission_genome(mission_id)
        if not genome:
            return f"Mission {mission_id}: not found"

        tasks_list = self.store.list_tasks(mission_id)
        evidence = self.store.list_evidence(mission_id)
        bb_entries = self.store.read_blackboard(mission_id)
        journal = self.store.read_journal(mission_id)
        reflections = self.store.list_reflections(mission_id)

        return self._render_mission(
            genome=genome,
            tasks=tasks_list,
            evidence=evidence,
            blackboard_count=len(bb_entries),
            journal_count=len(journal),
            reflection_count=len(reflections),
        )

    def agent_report(self, agent_id: str) -> str:
        genome = self.store.get_agent_genome(agent_id)
        if not genome:
            return f"Agent {agent_id}: not found"

        capabilities = genome.available_capabilities
        trust_data = {}
        for cap in capabilities:
            trust_data[cap] = self.store.get_trust(agent_id, cap)

        return self._render_agent(
            genome=genome,
            trust_data=trust_data,
        )

    def evidence_report(self, mission_id: str) -> str:
        evidence = self.store.list_evidence(mission_id)
        if not evidence:
            return f"No evidence for mission {mission_id}"

        verified = sum(1 for e in evidence if e.get("verification_status") == "verified")
        unverified = sum(1 for e in evidence if e.get("verification_status") == "unverified")
        disputed = sum(1 for e in evidence if e.get("verification_status") == "disputed")
        avg_conf = (
            sum(e.get("confidence", 0) for e in evidence) / len(evidence)
        )

        return self._render_evidence(
            total=len(evidence),
            verified=verified,
            unverified=unverified,
            disputed=disputed,
            avg_confidence=round(avg_conf, 3),
            entries=evidence[-5:],
        )

    def active_missions_summary(self) -> str:
        missions = self.store.list_mission_genomes(status="in_progress")
        if not missions:
            return "No active missions"

        lines = [
            f"Active Missions ({len(missions)})",
            "=" * 50,
        ]
        for m in missions:
            tasks_list = self.store.list_tasks(m.mission_id)
            total = len(tasks_list)
            done = sum(1 for t in tasks_list if t.status == "completed")
            lines.append(
                f"  {m.mission_id[:8]} | {m.objective[:50]:50s} "
                f"| tasks: {done}/{total} | priority: {m.priority}"
            )
        return "\n".join(lines)

    def system_status(self) -> str:
        import sqlite3
        try:
            row = self.store.conn.execute(
                "SELECT COUNT(*) as total FROM sqlite_master WHERE type='table'"
            ).fetchone()
            table_count = row["total"] if row else 0

            counts = {}
            for table in [
                "agent_genomes", "mission_genomes", "task_assignments",
                "blackboard_entries", "evidence_ledger", "trust_records",
                "journal_entries", "reflection_entries", "debate_rounds",
                "composite_capabilities", "knowledge_links",
            ]:
                r = self.store.conn.execute(f"SELECT COUNT(*) as c FROM {table}").fetchone()
                counts[table] = r["c"] if r else 0

            total_rows = sum(counts.values())

            db_size = 0
            import os
            if os.path.exists(self.store.db_path):
                db_size = os.path.getsize(self.store.db_path)

            return self._render_system(
                table_count=table_count,
                row_counts=counts,
                total_rows=total_rows,
                db_size_kb=round(db_size / 1024, 1),
            )
        except Exception as e:
            return f"System status error: {e}"

    def _render_overview(self, **data) -> str:
        return textwrap.dedent(f"""\
            ╔══════════════════════════════════════════╗
            ║        Research Runtime Dashboard         ║
            ╚══════════════════════════════════════════╝

            Missions:      {data['total_missions']}
              States:      {json.dumps(data['mission_states'])}
            Tasks:         {data['total_tasks']}
              Statuses:    {json.dumps(data['task_statuses'])}
            Agents:        {data['total_agents']}
            Evidence:      {data['total_evidence']}
        """)

    def _render_mission(self, **data) -> str:
        g = data["genome"]
        tasks_list = data["tasks"]
        evidence = data["evidence"]
        ev_verified = sum(1 for e in evidence if e.get("verification_status") == "verified")
        task_completed = sum(1 for t in tasks_list if t.status == "completed")
        task_failed = sum(1 for t in tasks_list if t.status == "failed")

        return textwrap.dedent(f"""\
            Mission: {g.mission_id[:16]}
            ─{"─" * 60}
            Objective:   {g.objective}
            State:       {g.current_state} → {g.next_state}
            Application: {g.application}
            Priority:    {g.priority}
            Confidence:  {g.required_confidence}

            Tasks:       {len(tasks_list)} ({task_completed} done, {task_failed} failed)
            Evidence:    {len(evidence)} ({ev_verified} verified)
            Blackboard:  {data['blackboard_count']} entries
            Journal:     {data['journal_count']} entries
            Reflections: {data['reflection_count']} entries

            Created:     {g.created_at}
            Updated:     {g.updated_at}
        """)

    def _render_agent(self, **data) -> str:
        g = data["genome"]
        return textwrap.dedent(f"""\
            Agent: {g.agent_id}
            ─{"─" * 60}
            Role:        {g.role.value}
            Model:       {g.model_name} ({g.model_size_gb:.1f}GB)
            Capabilities: {len(g.available_capabilities)}
            Success Rate:{g.success_rate:.2%}
            Tasks:       {g.total_tasks} total, {g.failed_tasks} failed
            Hallucinations: {g.hallucination_count}

            Capability Trust:
            {self._render_trust(data['trust_data'])}
        """)

    def _render_trust(self, trust_data: dict) -> str:
        if not trust_data:
            return "  No trust data available"
        lines = []
        for cap, data in sorted(trust_data.items()):
            lines.append(
                f"  {cap:40s} | tasks: {data.get('total_tasks', 0):4d} "
                f"| reliability: {data.get('success_rate', 0.5):.2%}"
            )
        return "\n".join(lines)

    def _render_evidence(self, **data) -> str:
        return textwrap.dedent(f"""\
            Evidence Report
            ─{"─" * 60}
            Total:       {data['total']}
            Verified:    {data['verified']}
            Unverified:  {data['unverified']}
            Disputed:    {data['disputed']}
            Avg Confidence: {data['avg_confidence']}

            Recent Entries (last 5):
            {self._render_recent_evidence(data['entries'])}
        """)

    def _render_recent_evidence(self, entries: list[dict]) -> str:
        if not entries:
            return "  None"
        lines = []
        for e in entries:
            claim = e.get("claim", "")[:60]
            lines.append(
                f"  [{e.get('verification_status', '?')}] "
                f"{e.get('evidence_id', '?')[:8]} "
                f"conf={e.get('confidence', 0.0):.2f} | {claim}"
            )
        return "\n".join(lines)

    def _render_system(self, **data) -> str:
        return textwrap.dedent(f"""\
            System Status
            ─{"─" * 60}
            Tables:      {data['table_count']}
            Total Rows:  {data['total_rows']}
            DB Size:     {data['db_size_kb']} KB

            Row Counts:
            {json.dumps(data['row_counts'], indent=2)}
        """)
