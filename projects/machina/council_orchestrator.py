# Copyright © 2026 Arsh Buttar. All rights reserved. Confidential and proprietary.
# Unauthorized copying, distribution, or use of this work is prohibited.

#!/usr/bin/env python3
import sqlite3
import os
import json
import subprocess
from datetime import datetime, timedelta
from collections import defaultdict

import sys
sys.path.insert(0, os.path.expanduser('~/NeuroCity/core'))
from neurocity_db import NeuroCityDB, DB_PATH

class CouncilAgent:
    def __init__(self, name, db):
        self.name = name
        self.db = db
        self.findings = []
        self.recommendations = []
    
    def analyze(self, metrics, historical):
        raise NotImplementedError
    
    def report(self):
        return {
            'agent': self.name,
            'status': 'ACTIVE',
            'findings': self.findings,
            'recommendations': self.recommendations
        }

class ScoutAgent(CouncilAgent):
    def analyze(self, metrics, historical):
        self.findings = []
        self.recommendations = []
        
        if metrics.get('risk_tier') == 'CRITICAL':
            self.findings.append('CRITICAL risk score detected: ' + str(metrics.get('risk_score')))
            self.recommendations.append('IMMEDIATE: Trigger all enforcement protocols')
        
        if metrics.get('sleep_debt', 0) >= 3.0:
            self.findings.append('Sleep debt critical: ' + str(round(metrics['sleep_debt'], 1)) + 'h')
            self.recommendations.append('ENFORCE bedtime lockdown tonight')
        
        if metrics.get('night_drift', 0) >= 120:
            self.findings.append('Night drift excessive: ' + str(int(metrics['night_drift'])) + 'min past 23:00')
            self.recommendations.append('PREEMPTIVE: Lock entertainment apps at 22:30')
        
        if metrics.get('fragmentation_ratio', 0) >= 0.8:
            self.findings.append('Focus fragmentation critical: ' + str(round(metrics['fragmentation_ratio'] * 100)) + '% sessions abandoned')
            self.recommendations.append('MANDATORY: 25min focus timer on all productivity apps')
        
        if metrics.get('idea_graveyard', 0) >= 8:
            self.findings.append('Idea graveyard overflowing: ' + str(metrics['idea_graveyard']) + ' projects abandoned')
            self.recommendations.append('FREEZE: No new projects until existing ones complete')

class TheoristAgent(CouncilAgent):
    def analyze(self, metrics, historical):
        self.findings = []
        self.recommendations = []
        
        if len(historical) < 3:
            self.findings.append('Insufficient historical data for trajectory modeling')
            return
        
        sleep_trend = [h[1] for h in historical if h[1] is not None]
        risk_trend = [h[7] for h in historical if h[7] is not None]
        
        if len(sleep_trend) >= 3:
            recent_avg = sum(sleep_trend[-3:]) / 3
            older_avg = sum(sleep_trend[:3]) / 3 if len(sleep_trend) >= 6 else sleep_trend[0]
            
            if recent_avg > older_avg + 0.5:
                self.findings.append('Sleep debt TRENDING WORSE: +' + str(round(recent_avg - older_avg, 1)) + 'h over last week')
                self.recommendations.append('ESCALATE: Move bedtime enforcement to 22:00')
        
        if len(risk_trend) >= 3:
            if risk_trend[-1] > risk_trend[-3] + 10:
                self.findings.append('Risk score ACCELERATING: +' + str(round(risk_trend[-1] - risk_trend[-3], 0)) + ' points in 3 days')
                self.recommendations.append('ALERT: Subject approaching breakdown threshold. Reduce all non-essential commitments.')
        
        night_drifts = [h[3] for h in historical if h[3] is not None]
        next_day_graveyards = [h[6] for h in historical[1:] if h[6] is not None]
        
        if len(night_drifts) >= 4 and len(next_day_graveyards) >= 4:
            high_night_indices = [i for i, v in enumerate(night_drifts) if v > 60]
            corresponding_graveyards = [next_day_graveyards[i] for i in high_night_indices if i < len(next_day_graveyards)]
            
            if corresponding_graveyards and sum(corresponding_graveyards) / len(corresponding_graveyards) > 5:
                self.findings.append('CAUSAL LINK: Nights with >60min drift correlate with ' + str(round(sum(corresponding_graveyards)/len(corresponding_graveyards), 1)) + ' abandoned projects next day')
                self.recommendations.append('PRIORITIZE: Night drift reduction directly improves next-day completion rate')

class ArchitectAgent(CouncilAgent):
    def analyze(self, metrics, historical):
        self.findings = []
        self.recommendations = []
        
        tier = metrics.get('risk_tier', 'LOW')
        
        protocols = {
            'LOW': {
                'bedtime': 'Soft reminder at 22:30',
                'apps': 'No restrictions',
                'focus': 'Optional Pomodoro suggestions',
                'social': 'Weekly check-in prompt'
            },
            'MODERATE': {
                'bedtime': 'Notification + dim screen at 22:30',
                'apps': '5-minute delay to open entertainment after 23:00',
                'focus': 'Enforced 25min timer on productivity apps after 22:00',
                'social': 'Daily 18:00 connection prompt'
            },
            'ELEVATED': {
                'bedtime': 'Lock entertainment apps at 22:30, unlock requires 10-min wait',
                'apps': 'Block top 3 offending apps after 22:30',
                'focus': 'Mandatory focus mode: 45min work, 10min break, no exit',
                'social': 'Force message to priority contact if no interaction by 20:00'
            },
            'CRITICAL': {
                'bedtime': 'Full device lock at 22:00 except emergency calls',
                'apps': 'Whitelist only: calls, messages, meditation, alarm',
                'focus': 'Single-task mode: one app at a time, no switching for 60min',
                'social': 'Auto-notify emergency contact if isolation >24h'
            }
        }
        
        active_protocol = protocols.get(tier, protocols['LOW'])
        
        self.findings.append('Risk tier: ' + tier + '. Activating ' + tier + ' protocol set.')
        self.recommendations.append('PROTOCOL: ' + json.dumps(active_protocol))
        
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("INSERT OR REPLACE INTO config (key, value) VALUES (?, ?)",
                  ('active_protocol', json.dumps(active_protocol)))
        conn.commit()
        conn.close()

class LeadCoderAgent(CouncilAgent):
    def analyze(self, metrics, historical):
        self.findings = []
        self.recommendations = []
        
        tier = metrics.get('risk_tier', 'LOW')
        
        if tier in ['ELEVATED', 'CRITICAL']:
            self.findings.append('Generating enforcement scripts for tier: ' + tier)
            self.recommendations.append('DEPLOY: app_blocker.py for lockdown enforcement')
            self.recommendations.append('DEPLOY: focus_timer.py for productivity enforcement')

class CriticAgent(CouncilAgent):
    def analyze(self, metrics, historical):
        self.findings = []
        self.recommendations = []
        
        if metrics.get('night_drift', 0) > 180:
            self.findings.append('OVERRIDE RISK: Subject has history of 3+ hour night sessions. Simple app blocking may be circumvented.')
            self.recommendations.append('MITIGATION: Block at network level + notify accountability partner')
        
        if metrics.get('scheduled_commitments', 0) > 10:
            self.findings.append('FALSE POSITIVE RISK: High calendar density may trigger commitment velocity alerts even for legitimate cancellations')
            self.recommendations.append('MITIGATION: Require manual confirmation before marking commitment as "missed"')
        
        if not metrics.get('sleep_hours'):
            self.findings.append('DATA BLINDNESS: No sleep data available. Sleep debt calculation assumes 0 hours.')
            self.recommendations.append('MITIGATION: Prompt for Health export or manual sleep logging')

class ArcheologistAgent(CouncilAgent):
    def analyze(self, metrics, historical):
        self.findings = []
        self.recommendations = []
        
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("SELECT vector, COUNT(*) FROM raw_events WHERE date(timestamp) = date('now') GROUP BY vector")
        vectors_today = {row[0]: row[1] for row in c.fetchall()}
        conn.close()
        
        expected_vectors = ['alpha', 'bravo', 'delta', 'echo', 'foxtrot']
        missing = [v for v in expected_vectors if v not in vectors_today]
        
        if missing:
            self.findings.append('DATA GAPS: Missing vectors today: ' + str(missing))
            for v in missing:
                if v == 'echo':
                    self.recommendations.append('ACTION: Export Health data from iPhone')
                elif v == 'delta':
                    self.recommendations.append('ACTION: Locate Calendar database or enable calendar sync')
                elif v == 'bravo':
                    self.recommendations.append('ACTION: Grant accessibility permissions for live app monitoring')
                elif v == 'foxtrot':
                    self.recommendations.append('ACTION: Create manual_input.json for subjective logging')
        
        if 'alpha' in vectors_today and vectors_today['alpha'] < 10:
            self.findings.append('DATA STALENESS: Only ' + str(vectors_today['alpha']) + ' alpha events today.')
            self.recommendations.append('ACTION: Verify iPhone-MacBook sync, check Screen Time settings')

class WatcherAgent(CouncilAgent):
    def analyze(self, metrics, historical):
        self.findings = []
        self.recommendations = []
        
        self.findings.append('Watcher standing by. Current risk: ' + metrics.get('risk_tier', 'UNKNOWN'))
        
        tier = metrics.get('risk_tier', 'LOW')
        
        if tier == 'CRITICAL':
            msg = 'CRITICAL RISK: ' + str(round(metrics.get('risk_score', 0))) + '/100. Full lockdown engaged.'
            subprocess.run(['osascript', '-e', 'display notification "' + msg + '" with title "NeuroCity Council"'], capture_output=True)
            self.recommendations.append('EXECUTED: Critical alert notification')
            self.db.log_intervention(
                trigger_metric='overall_risk_score',
                threshold_breached=metrics.get('risk_score'),
                action_taken='critical_notification',
                enforcement_method='macOS_notification'
            )
        
        elif tier == 'ELEVATED':
            msg = 'ELEVATED RISK: ' + str(round(metrics.get('risk_score', 0))) + '/100. Night lockdown at 22:30.'
            subprocess.run(['osascript', '-e', 'display notification "' + msg + '" with title "NeuroCity Council"'], capture_output=True)
            self.recommendations.append('EXECUTED: Elevated alert notification')
            self.db.log_intervention(
                trigger_metric='overall_risk_score',
                threshold_breached=metrics.get('risk_score'),
                action_taken='elevated_notification',
                enforcement_method='macOS_notification'
            )

class CouncilOrchestrator:
    def __init__(self):
        self.db = NeuroCityDB()
        self.agents = [
            ScoutAgent('Scout', self.db),
            TheoristAgent('Theorist', self.db),
            ArchitectAgent('Architect', self.db),
            LeadCoderAgent('Lead_Coder', self.db),
            CriticAgent('Critic', self.db),
            ArcheologistAgent('Archeologist', self.db),
            WatcherAgent('Watcher', self.db)
        ]
    
    def run_session(self, metrics=None, date_str=None):
        if not date_str:
            date_str = datetime.now().strftime('%Y-%m-%d')
        
        print('=' * 70)
        print('NEUROCITY COUNCIL -- AGENTIC PLANNING SESSION')
        print('Date: ' + date_str)
        print('=' * 70)
        
        if not metrics:
            conn = sqlite3.connect(DB_PATH)
            c = conn.cursor()
            c.execute("SELECT * FROM derived_metrics WHERE date = ?", (date_str,))
            row = c.fetchone()
            conn.close()
            
            if not row:
                print('[ORCHESTRATOR] No metrics for ' + date_str + '. Run metrics_engine.py first.')
                return None
            
            metrics = {
                'date': row[0],
                'sleep_debt': row[1],
                'fragmentation_ratio': row[2],
                'night_drift': row[3],
                'social_atrophy': row[4],
                'commitment_velocity': row[5],
                'idea_graveyard': row[6],
                'risk_score': row[7],
                'risk_tier': row[8]
            }
        
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("""
            SELECT date, sleep_debt_hours, focus_fragmentation_ratio, night_drift_minutes,
                   social_atrophy_ratio, commitment_velocity, idea_graveyard_count,
                   overall_risk_score, risk_tier
            FROM derived_metrics
            WHERE date >= date('now', '-14 days')
            ORDER BY date
        """)
        historical = c.fetchall()
        conn.close()
        
        print('[ORCHESTRATOR] Loaded ' + str(len(historical)) + ' days of historical data')
        print('[ORCHESTRATOR] Current risk: ' + metrics.get('risk_tier', 'UNKNOWN') + ' (' + str(round(metrics.get('risk_score', 0))) + '/100)')
        print('')
        
        reports = []
        for agent in self.agents:
            try:
                agent.analyze(metrics, historical)
                report = agent.report()
                reports.append(report)
                
                print('--- ' + agent.name.upper() + ' ---')
                for finding in report['findings']:
                    print('FINDING: ' + finding)
                for rec in report['recommendations']:
                    print('REC: ' + rec)
                print('')
            except Exception as e:
                print('[ERROR] Agent ' + agent.name + ' failed: ' + str(e))
        
        doo = self._generate_doo(metrics, reports)
        
        doo_path = os.path.expanduser('~/NeuroCity/NeuroCity_Vault/daily_orders/')
        os.makedirs(doo_path, exist_ok=True)
        doo_file = doo_path + 'doo_' + date_str + '.json'
        with open(doo_file, 'w') as f:
            json.dump(doo, f, indent=2, default=str)
        
        print('=' * 70)
        print('DAILY OPERATIONS ORDER GENERATED')
        print('Saved: ' + doo_file)
        print('Risk Tier: ' + doo['risk_tier'])
        print('Active Interventions: ' + str(len(doo['interventions'])))
        print('=' * 70)
        
        return doo
    
    def _generate_doo(self, metrics, reports):
        all_interventions = []
        for report in reports:
            for rec in report['recommendations']:
                all_interventions.append({
                    'source_agent': report['agent'],
                    'action': rec,
                    'priority': 'CRITICAL' if 'CRITICAL' in rec or 'IMMEDIATE' in rec else 
                               'HIGH' if 'ENFORCE' in rec or 'MANDATORY' in rec else 'NORMAL'
                })
        
        priority_order = {'CRITICAL': 0, 'HIGH': 1, 'NORMAL': 2}
        all_interventions.sort(key=lambda x: priority_order.get(x['priority'], 3))
        
        schedule = {
            '18:00': [],
            '21:00': [],
            '22:00': [],
            '22:30': [],
            '23:00': []
        }
        
        for intervention in all_interventions:
            action = intervention['action']
            if 'bedtime' in action.lower() or '22:00' in action:
                schedule['22:00'].append(intervention)
            elif '22:30' in action:
                schedule['22:30'].append(intervention)
            elif '23:00' in action or 'night' in action.lower():
                schedule['23:00'].append(intervention)
            elif '18:00' in action or 'social' in action.lower():
                schedule['18:00'].append(intervention)
            elif 'focus' in action.lower() or 'productivity' in action.lower():
                schedule['21:00'].append(intervention)
            else:
                schedule['22:30'].append(intervention)
        
        return {
            'date': metrics.get('date'),
            'generated_at': datetime.now().isoformat(),
            'risk_tier': metrics.get('risk_tier'),
            'risk_score': metrics.get('risk_score'),
            'subject': 'arsh',
            'executive_summary': 'Daily assessment based on ' + str(len(reports)) + ' agent analyses',
            'interventions': all_interventions,
            'schedule': schedule,
            'agent_reports': reports
        }

if __name__ == '__main__':
    orchestrator = CouncilOrchestrator()
    doo = orchestrator.run_session()
    if doo:
        print(json.dumps(doo, indent=2, default=str))
