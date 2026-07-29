#!/usr/bin/env python3
import json
import os
import sqlite3
from datetime import datetime, timedelta

VAULT = os.path.expanduser('~/NeuroCity/NeuroCity_Vault')
DB_PATH = os.path.join(VAULT, 'council_history.db')
BRIEFING_DIR = os.path.join(VAULT, 'council_briefings')

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS daily_metrics (
        date TEXT PRIMARY KEY,
        total_events INTEGER,
        sleep_avg REAL,
        late_night_minutes REAL,
        productivity_sessions INTEGER,
        abandoned_sessions INTEGER,
        entertainment_hours REAL,
        social_hours REAL,
        risk_level TEXT,
        findings_count INTEGER,
        timestamp TEXT
    )''')
    conn.commit()
    conn.close()

def load_latest_briefing():
    if not os.path.exists(BRIEFING_DIR):
        return None
    files = sorted([f for f in os.listdir(BRIEFING_DIR) if f.endswith('.json')])
    if not files:
        return None
    with open(os.path.join(BRIEFING_DIR, files[-1])) as f:
        return json.load(f)

def load_yesterday():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
    c.execute('SELECT * FROM daily_metrics WHERE date = ?', (yesterday,))
    row = c.fetchone()
    conn.close()
    return row

def extract_metrics(briefing):
    findings = briefing.get('findings', [])
    sleep_avg = None
    late_night = 0
    prod_sessions = 0
    abandoned = 0
    ent_hours = 0
    social_hours = 0
    
    for f in findings:
        cat = f.get('category', '')
        finding = f.get('finding', '')
        if cat == 'sleep' and 'Avg:' in finding:
            try:
                sleep_avg = float(finding.split('Avg: ')[1].split('h')[0])
            except:
                pass
        if cat == 'digital_wellbeing' and 'min' in finding:
            try:
                late_night = float(finding.split(': ')[1].split(' min')[0])
            except:
                pass
        if cat == 'productivity' and '/' in finding:
            try:
                parts = finding.split('/')
                abandoned = int(parts[0].split(': ')[1])
                prod_sessions = int(parts[1].split(' ')[0])
            except:
                pass
        if cat == 'social_health' and 'h vs' in finding:
            try:
                ent_hours = float(finding.split('Entertainment ')[1].split('h')[0])
                social_hours = float(finding.split('social ')[1].split('h')[0])
            except:
                pass
    
    return {
        'total_events': briefing.get('findings_count', 0),
        'sleep_avg': sleep_avg,
        'late_night_minutes': late_night,
        'productivity_sessions': prod_sessions,
        'abandoned_sessions': abandoned,
        'entertainment_hours': ent_hours,
        'social_hours': social_hours,
        'risk_level': briefing.get('risk_level', 'UNKNOWN'),
        'findings_count': len(findings)
    }

def store_metrics(date_str, metrics):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''INSERT OR REPLACE INTO daily_metrics 
        (date, total_events, sleep_avg, late_night_minutes, productivity_sessions,
         abandoned_sessions, entertainment_hours, social_hours, risk_level, findings_count, timestamp)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
        (date_str, metrics['total_events'], metrics['sleep_avg'], metrics['late_night_minutes'],
         metrics['productivity_sessions'], metrics['abandoned_sessions'], metrics['entertainment_hours'],
         metrics['social_hours'], metrics['risk_level'], metrics['findings_count'], datetime.now().isoformat()))
    conn.commit()
    conn.close()

def generate_alert(metrics, yesterday_row):
    alerts = []
    if yesterday_row:
        y_sleep = yesterday_row[2]
        y_late = yesterday_row[3]
        y_risk = yesterday_row[8]
        
        if metrics['sleep_avg'] and y_sleep and metrics['sleep_avg'] < y_sleep - 0.5:
            alerts.append('SLEEP DECLINING: ' + str(round(metrics['sleep_avg'], 1)) + 'h vs yesterday ' + str(round(y_sleep, 1)) + 'h')
        
        if metrics['late_night_minutes'] > y_late * 1.5 and metrics['late_night_minutes'] > 30:
            alerts.append('LATE NIGHT SPIKE: ' + str(int(metrics['late_night_minutes'])) + ' min vs yesterday ' + str(int(y_late)) + ' min')
        
        if metrics['risk_level'] != y_risk and metrics['risk_level'] in ['CRITICAL', 'ELEVATED']:
            alerts.append('RISK ESCALATED: ' + y_risk + ' -> ' + metrics['risk_level'])
    
    if metrics['sleep_avg'] and metrics['sleep_avg'] < 5.0:
        alerts.append('CRITICAL SLEEP: ' + str(round(metrics['sleep_avg'], 1)) + 'h. Intervention required tonight.')
    
    if metrics['abandoned_sessions'] and metrics['productivity_sessions'] and metrics['abandoned_sessions'] / max(metrics['productivity_sessions'], 1) > 0.8:
        alerts.append('PROJECT DEATH SPIRAL: ' + str(metrics['abandoned_sessions']) + '/' + str(metrics['productivity_sessions']) + ' abandoned')
    
    return alerts

def main():
    init_db()
    
    briefing = load_latest_briefing()
    if not briefing:
        print('[DELTA] No briefing found. Run council_life_analyzer.py first.')
        return
    
    metrics = extract_metrics(briefing)
    today = datetime.now().strftime('%Y-%m-%d')
    
    yesterday = load_yesterday()
    alerts = generate_alert(metrics, yesterday)
    
    store_metrics(today, metrics)
    
    if alerts:
        print('')
        print('=== COUNCIL ALERTS ===')
        for alert in alerts:
            print('!! ' + alert)
        print('')
        
        msg = ' | '.join(alerts[:2])
        os.system("""osascript -e 'display notification "%s" with title "NeuroCity Council"'""" % msg)
    else:
        print('[DELTA] No significant changes. Standing watch.')

if __name__ == '__main__':
    main()
