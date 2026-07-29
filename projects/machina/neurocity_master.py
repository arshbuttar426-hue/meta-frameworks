#!/usr/bin/env python3
import argparse
import os
import sys
import time
import json

sys.path.insert(0, os.path.expanduser('~/NeuroCity/core'))
sys.path.insert(0, os.path.expanduser('~/NeuroCity/collectors'))
sys.path.insert(0, os.path.expanduser('~/NeuroCity/agents'))

from neurocity_db import NeuroCityDB
from metrics_engine import MetricsEngine
from council_orchestrator import CouncilOrchestrator

def run_full_pipeline():
    print('=' * 70)
    print('NEUROCITY INTELLIGENCE FRAMEWORK')
    print('Initializing full pipeline...')
    print('=' * 70)
    
    db = NeuroCityDB()
    print('[MASTER] Database ready')
    
    try:
        from vector_collector import collect_all
        print('[MASTER] Starting data collection...')
        count = collect_all()
        print('[MASTER] Collected ' + str(count) + ' events')
    except Exception as e:
        print('[MASTER] Collector not available or failed: ' + str(e))
        print('[MASTER] Continuing with existing data...')
    
    print('[MASTER] Computing derived metrics...')
    engine = MetricsEngine()
    metrics = engine.compute_all_metrics()
    print('[MASTER] Metrics computed')
    
    print('[MASTER] Convening Council...')
    council = CouncilOrchestrator()
    doo = council.run_session(metrics=metrics)
    
    if doo:
        print('[MASTER] Pipeline complete. Risk: ' + doo['risk_tier'])
    else:
        print('[MASTER] Council session failed')
    
    return doo

def print_report():
    doo_dir = os.path.expanduser('~/NeuroCity/NeuroCity_Vault/daily_orders/')
    if not os.path.exists(doo_dir):
        print('No daily orders found. Run pipeline first.')
        return
    
    files = sorted([f for f in os.listdir(doo_dir) if f.endswith('.json')])
    if not files:
        print('No daily orders found. Run pipeline first.')
        return
    
    with open(os.path.join(doo_dir, files[-1])) as f:
        doo = json.load(f)
    
    print('=' * 60)
    print('DAILY OPERATIONS ORDER')
    print('Date: ' + doo.get('date', 'UNKNOWN'))
    print('Generated: ' + doo.get('generated_at', 'UNKNOWN'))
    print('Risk: ' + doo.get('risk_tier', 'UNKNOWN') + ' (' + str(round(doo.get('risk_score', 0))) + '/100)')
    print('=' * 60)
    print()
    print('INTERVENTIONS:')
    for i in doo.get('interventions', []):
        print('[' + i.get('priority', 'NORMAL') + '] ' + i.get('source_agent', 'UNKNOWN') + ': ' + i.get('action', ''))
    print()
    print('SCHEDULE:')
    for time_slot, actions in doo.get('schedule', {}).items():
        if actions:
            print(time_slot + ':')
            for a in actions:
                print('  - ' + a.get('action', ''))

def run_dashboard():
    import sqlite3
    from neurocity_db import DB_PATH
    
    while True:
        os.system('clear')
        print('=' * 60)
        print('NEUROCITY LIVE DASHBOARD')
        print('Last update: ' + time.strftime('%H:%M:%S'))
        print('=' * 60)
        
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        
        c.execute("SELECT * FROM derived_metrics ORDER BY date DESC LIMIT 1")
        row = c.fetchone()
        if row:
            print('Date: ' + row[0])
            print('Risk: ' + row[8] + ' (' + str(round(row[7])) + '/100)')
            print('Sleep Debt: ' + str(round(row[1], 1)) + 'h')
            print('Night Drift: ' + str(round(row[3], 0)) + 'min')
            print('Idea Graveyard: ' + str(row[6]))
        else:
            print('No metrics available. Run pipeline first.')
        
        c.execute("SELECT vector, COUNT(*) FROM raw_events WHERE date(timestamp) = date('now') GROUP BY vector")
        vectors = c.fetchall()
        print()
        print('Today\'s Events:')
        for v, count in vectors:
            print('  ' + v + ': ' + str(count))
        
        conn.close()
        
        print()
        print('Press Ctrl+C to exit')
        time.sleep(30)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='NeuroCity Intelligence Framework')
    parser.add_argument('--report', action='store_true', help='Print latest DOO')
    parser.add_argument('--dashboard', action='store_true', help='Live dashboard')
    args = parser.parse_args()
    
    if args.report:
        print_report()
    elif args.dashboard:
        try:
            run_dashboard()
        except KeyboardInterrupt:
            print('\nDashboard stopped.')
    else:
        run_full_pipeline()
