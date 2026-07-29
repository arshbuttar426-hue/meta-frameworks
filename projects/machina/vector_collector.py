#!/usr/bin/env python3
import sqlite3
import os
import glob
import subprocess
import json
from datetime import datetime, timedelta
from collections import defaultdict
import xml.etree.ElementTree as ET

import sys
sys.path.insert(0, os.path.expanduser('~/NeuroCity/core'))
from neurocity_db import NeuroCityDB

DB = NeuroCityDB()

def collect_alpha():
    events = []
    kdb = os.path.expanduser('~/Library/Application Support/Knowledge/knowledgeC.db')
    if not os.path.exists(kdb):
        return events
    
    try:
        conn = sqlite3.connect(kdb)
        c = conn.cursor()
        
        c.execute("""
            SELECT ZCREATIONDATE, ZSTREAMNAME, ZVALUESTRING, ZSTARTDATE, ZENDDATE
            FROM ZOBJECT
            WHERE ZSTREAMNAME IN ('/app/usage', '/app/webUsage', '/app/mediaUsage')
            AND ZCREATIONDATE > (SELECT MAX(ZCREATIONDATE) - 86400 FROM ZOBJECT)
            ORDER BY ZCREATIONDATE DESC
            LIMIT 10000
        """)
        
        epoch = datetime(2001, 1, 1)
        for row in c.fetchall():
            creation, stream, value, start, end = row
            ts = epoch + timedelta(seconds=float(creation)) if creation else None
            start_ts = epoch + timedelta(seconds=float(start)) if start else None
            end_ts = epoch + timedelta(seconds=float(end)) if end else None
            duration = (end_ts - start_ts).total_seconds() if (end_ts and start_ts) else 0
            
            events.append((
                ts.isoformat() if ts else None,
                'alpha',
                'app_usage',
                value,
                duration,
                None,
                json.dumps({'stream': stream})
            ))
        
        c.execute("""
            SELECT ZCREATIONDATE, ZVALUESTRING
            FROM ZOBJECT
            WHERE ZSTREAMNAME = '/display/isBacklit'
            AND ZCREATIONDATE > (SELECT MAX(ZCREATIONDATE) - 86400 FROM ZOBJECT)
            ORDER BY ZCREATIONDATE DESC
            LIMIT 1000
        """)
        for row in c.fetchall():
            creation, value = row
            ts = epoch + timedelta(seconds=float(creation)) if creation else None
            events.append((
                ts.isoformat() if ts else None,
                'alpha',
                'screen_state',
                'system_display',
                0,
                value,
                None
            ))
        
        conn.close()
    except Exception as e:
        print('[ALPHA] Error: ' + str(e))
    
    return events

def collect_bravo():
    events = []
    now = datetime.now().isoformat()
    
    try:
        result = subprocess.run(
            ['osascript', '-e', 'tell application "System Events" to get name of first application process whose frontmost is true'],
            capture_output=True, text=True, timeout=5
        )
        front_app = result.stdout.strip()
        if front_app:
            events.append((now, 'bravo', 'frontmost_app', front_app, 0, None, None))
    except:
        pass
    
    try:
        result = subprocess.run(
            ['ioreg', '-c', 'IOHIDSystem'],
            capture_output=True, text=True, timeout=5
        )
        for line in result.stdout.split('\n'):
            if 'HIDIdleTime' in line:
                parts = line.split('=')
                if len(parts) > 1:
                    idle_ns = int(parts[1].strip().rstrip('L'))
                    idle_sec = idle_ns / 1000000000
                    events.append((now, 'bravo', 'idle_time', 'system', idle_sec, None, None))
                break
    except:
        pass
    
    try:
        result = subprocess.run(
            ['python3', '-c', 'import Quartz; print(Quartz.CGSessionCopyCurrentDictionary())'],
            capture_output=True, text=True, timeout=5
        )
        if 'OnConsoleKey' in result.stdout:
            locked = '0' if 'OnConsoleKey = 1' in result.stdout else '1'
            events.append((now, 'bravo', 'screen_lock', 'system', 0, locked, None))
    except:
        pass
    
    return events

def collect_delta():
    events = []
    candidates = glob.glob(os.path.expanduser('~/Library/Calendars/**/*.sqlitedb'), recursive=True)
    
    for cal_db in candidates:
        try:
            conn = sqlite3.connect(cal_db)
            c = conn.cursor()
            c.execute("""
                SELECT summary, start_date, end_date, location, all_day
                FROM CalendarItem
                WHERE start_date IS NOT NULL
                AND datetime(start_date + 978307200, 'unixepoch') >= datetime('now', '-7 days')
                ORDER BY start_date DESC
                LIMIT 500
            """)
            
            epoch = datetime(2001, 1, 1)
            for row in c.fetchall():
                summary, start, end, loc, all_day = row
                start_ts = epoch + timedelta(seconds=float(start)) if start else None
                end_ts = epoch + timedelta(seconds=float(end)) if end else None
                duration = (end_ts - start_ts).total_seconds() if (end_ts and start_ts) else 0
                
                events.append((
                    start_ts.isoformat() if start_ts else None,
                    'delta',
                    'calendar_event',
                    summary,
                    duration,
                    loc,
                    json.dumps({'all_day': bool(all_day)})
                ))
            conn.close()
            break
        except:
            continue
    
    return events

def collect_echo():
    events = []
    files = glob.glob(os.path.expanduser('~/Downloads/apple_health_export*/export.xml'))
    if not files:
        return events
    
    try:
        tree = ET.parse(files[0])
        root = tree.getroot()
        
        type_map = {
            'HKQuantityTypeIdentifierHeartRate': 'heart_rate',
            'HKCategoryTypeIdentifierSleepAnalysis': 'sleep',
            'HKQuantityTypeIdentifierStepCount': 'steps',
            'HKQuantityTypeIdentifierActiveEnergyBurned': 'active_energy'
        }
        
        for rec in root.findall('.//Record'):
            rt = rec.get('type', '')
            if rt in type_map:
                events.append((
                    rec.get('startDate'),
                    'echo',
                    type_map[rt],
                    rec.get('sourceName'),
                    float(rec.get('value', 0)) if rec.get('value') else None,
                    rec.get('unit'),
                    json.dumps({'end_date': rec.get('endDate')})
                ))
    except Exception as e:
        print('[ECHO] Error: ' + str(e))
    
    return events

def collect_foxtrot():
    events = []
    manual_file = os.path.expanduser('~/NeuroCity/manual_input.json')
    if not os.path.exists(manual_file):
        return events
    
    try:
        with open(manual_file) as f:
            entries = json.load(f)
        for entry in entries:
            events.append((
                entry.get('timestamp', datetime.now().isoformat()),
                'foxtrot',
                entry.get('event_type', 'manual'),
                entry.get('app', 'user'),
                entry.get('value'),
                entry.get('note'),
                None
            ))
    except:
        pass
    
    return events

def collect_all():
    print('=' * 70)
    print('NEUROCITY MULTI-VECTOR COLLECTOR')
    print('Harvesting all telemetry vectors...')
    print('=' * 70)
    
    all_events = []
    
    vectors = [
        ('Alpha (knowledgeC)', collect_alpha),
        ('Bravo (live macOS)', collect_bravo),
        ('Delta (Calendar)', collect_delta),
        ('Echo (HealthKit)', collect_echo),
        ('Foxtrot (Manual)', collect_foxtrot)
    ]
    
    for name, collector in vectors:
        try:
            events = collector()
            all_events.extend(events)
            print('[' + name + '] Collected ' + str(len(events)) + ' events')
        except Exception as e:
            print('[' + name + '] FAILED: ' + str(e))
    
    if all_events:
        DB.bulk_insert_events(all_events)
        print('[DATABASE] Inserted ' + str(len(all_events)) + ' total events')
    else:
        print('[DATABASE] No events to insert')
    
    return len(all_events)

if __name__ == '__main__':
    collect_all()
