#!/usr/bin/env python3
import json
import os
from datetime import datetime, timedelta
from collections import defaultdict, Counter
import statistics

INPUT_FILE = os.path.expanduser('~/NeuroCity/NeuroCity_Vault/unified_life_log.json')
OUTPUT_DIR = os.path.expanduser('~/NeuroCity/NeuroCity_Vault/council_briefings')
os.makedirs(OUTPUT_DIR, exist_ok=True)

THRESHOLDS = {
    'min_sleep_hours': 6.0,
    'max_late_night_minutes': 60
}

class Analyzer:
    def __init__(self, log):
        self.events = log.get('events', [])
        self.findings = []
        self.interventions = []

    def sleep_check(self):
        sleep_events = [e for e in self.events if e.get('source') == 'healthkit' and e.get('event_type') == 'sleep']
        if not sleep_events:
            return
        daily_sleep = defaultdict(float)
        for event in sleep_events:
            try:
                start = datetime.fromisoformat(event['timestamp'].replace('Z', '+00:00'))
                end = datetime.fromisoformat(event['end_time'].replace('Z', '+00:00'))
                duration = (end - start).total_seconds() / 3600
                daily_sleep[start.strftime('%Y-%m-%d')] += duration
            except:
                continue
        short_days = [d for d, h in daily_sleep.items() if h < THRESHOLDS['min_sleep_hours']]
        if len(short_days) > 5:
            avg = statistics.mean(daily_sleep.values()) if daily_sleep else 0
            self.findings.append({
                'category': 'sleep',
                'severity': 'HIGH' if len(short_days) > 10 else 'MEDIUM',
                'finding': 'Sleep deprivation: ' + str(len(short_days)) + ' nights below ' + str(THRESHOLDS['min_sleep_hours']) + 'h. Avg: ' + str(round(avg, 1)) + 'h'
            })
            self.interventions.append({
                'action': 'LOCK entertainment apps at 22:30',
                'reason': 'Late night usage destroys sleep architecture'
            })

    def app_check(self):
        app_events = [e for e in self.events if e.get('source') == 'screen_time' and e.get('app_name')]
        if not app_events:
            return
        late_night = defaultdict(float)
        for event in app_events:
            hour = event.get('hour_of_day', 12)
            duration = event.get('duration_seconds', 0) or 0
            if hour >= 23 or hour <= 2:
                late_night[event['app_name']] += duration / 60
        total_late = sum(late_night.values())
        if total_late > THRESHOLDS['max_late_night_minutes']:
            top_apps = dict(Counter(late_night).most_common(3))
            self.findings.append({
                'category': 'digital_wellbeing',
                'severity': 'HIGH',
                'finding': 'Late night screen time: ' + str(int(total_late)) + ' min after 23:00. Top apps: ' + str(list(top_apps.keys()))
            })
            self.interventions.append({
                'action': 'BLOCK ' + str(list(top_apps.keys())[:2]) + ' after 22:30. Require 5min delay to unlock',
                'reason': 'Night usage correlates with next-day fatigue'
            })

    def commitment_check(self):
        cal_events = [e for e in self.events if e.get('source') == 'calendar']
        if not cal_events:
            return
        recent = [e for e in cal_events if e.get('timestamp') and datetime.fromisoformat(e['timestamp'].replace('Z', '+00:00')) > datetime.now() - timedelta(days=30)]
        self.findings.append({
            'category': 'commitments',
            'severity': 'MEDIUM',
            'finding': str(len(recent)) + ' calendar events in last 30 days. Check for no-shows and broken promises.'
        })

    def social_check(self):
        app_events = [e for e in self.events if e.get('source') == 'screen_time']
        social = ['Messages', 'WhatsApp', 'Telegram', 'Instagram']
        entertainment = ['YouTube', 'TikTok', 'Netflix', 'Games']
        social_time = sum((e.get('duration_seconds', 0) or 0) for e in app_events if any(s in str(e.get('app_name', '')) for s in social))
        ent_time = sum((e.get('duration_seconds', 0) or 0) for e in app_events if any(x in str(e.get('app_name', '')) for x in entertainment))
        social_h = social_time / 3600
        ent_h = ent_time / 3600
        if ent_h > social_h * 3 and ent_h > 10:
            self.findings.append({
                'category': 'social_health',
                'severity': 'MEDIUM',
                'finding': 'Entertainment ' + str(round(ent_h, 1)) + 'h vs social ' + str(round(social_h, 1)) + 'h. Ratio: ' + str(round(ent_h/max(social_h, 0.1), 1)) + 'x'
            })
            self.interventions.append({
                'action': 'After 45min entertainment, FORCE prompt: Message someone you care about',
                'reason': 'Passive consumption is replacing active connection'
            })

    def project_check(self):
        prod_apps = ['Notes', 'Notion', 'Obsidian', 'Bear']
        prod_events = [e for e in self.events if e.get('source') == 'screen_time' and any(p in str(e.get('app_name', '')) for p in prod_apps)]
        if len(prod_events) > 20:
            short = [e for e in prod_events if (e.get('duration_seconds') or 0) < 300]
            if len(short) > len(prod_events) * 0.6:
                self.findings.append({
                    'category': 'productivity',
                    'severity': 'HIGH',
                    'finding': 'Project abandonment: ' + str(len(short)) + '/' + str(len(prod_events)) + ' sessions under 5min. You start but do not finish.'
                })
                self.interventions.append({
                    'action': 'Opening productivity apps after 22:00 triggers 25min LOCK. No exit until timer complete',
                    'reason': 'Late night ideation rarely produces completion'
                })

    def generate_briefing(self):
        high = sum(1 for f in self.findings if f.get('severity') == 'HIGH')
        med = sum(1 for f in self.findings if f.get('severity') == 'MEDIUM')
        if high >= 3:
            risk = 'CRITICAL'
        elif high >= 1 or med >= 3:
            risk = 'ELEVATED'
        elif med >= 1:
            risk = 'MODERATE'
        else:
            risk = 'LOW'
        return {
            'session': 'audit_' + datetime.now().strftime('%Y%m%d_%H%M%S'),
            'subject': 'arsh',
            'risk_level': risk,
            'findings_count': len(self.findings),
            'intervention_count': len(self.interventions),
            'findings': self.findings,
            'interventions': self.interventions,
            'governance_rules': {
                'bedtime': 'Lock entertainment apps at 22:30',
                'commitments': 'Alert 30min before calendar event. Notify girlfriend if location mismatch',
                'projects': '25min enforced focus on productivity apps after 22:00',
                'social': 'Daily 18:00 check: minimum 1 meaningful conversation'
            }
        }

def main():
    print('=' * 60)
    print('NEUROCITY COUNCIL -- WARFARE PROTOCOL')
    print('=' * 60)
    if not os.path.exists(INPUT_FILE):
        print('ERROR: Run life_log_extractor.py first')
        return
    with open(INPUT_FILE, 'r') as f:
        log = json.load(f)
    print('Loaded: ' + str(len(log.get('events', []))) + ' events')
    a = Analyzer(log)
    print('Analyzing...')
    a.sleep_check()
    a.app_check()
    a.commitment_check()
    a.social_check()
    a.project_check()
    briefing = a.generate_briefing()
    outfile = OUTPUT_DIR + '/briefing_' + datetime.now().strftime('%Y%m%d_%H%M%S') + '.json'
    with open(outfile, 'w') as f:
        json.dump(briefing, f, indent=2, default=str)
    print('')
    print('=== FINDINGS ===')
    for f in a.findings:
        marker = '[HIGH]' if f['severity'] == 'HIGH' else '[MED]'
        print(marker + ' ' + f['category'] + ': ' + f['finding'])
    print('')
    print('=== INTERVENTIONS ===')
    for i in a.interventions:
        print('-> ' + i['action'])
        print('   Why: ' + i['reason'])
    print('')
    print('Risk Level: ' + briefing['risk_level'])
    print('Briefing saved: ' + outfile)

if __name__ == '__main__':
    main()
