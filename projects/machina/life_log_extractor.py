#!/usr/bin/env python3
import sqlite3
import json
import os
import glob
from datetime import datetime, timedelta
from collections import defaultdict
import xml.etree.ElementTree as ET
import subprocess

OUTPUT_FILE = os.path.expanduser('~/NeuroCity/NeuroCity_Vault/unified_life_log.json')
os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)

def apple_time_to_dt(ts):
    if not ts:
        return None
    epoch = datetime(2001, 1, 1)
    return epoch + timedelta(seconds=float(ts))

def safe_val(v):
    if v is None:
        return None
    if isinstance(v, (str, int, float, bool, list, dict)):
        return v
    return str(v)

def extract_screen_time():
    events = []
    kdb = os.path.expanduser('~/Library/Application Support/Knowledge/knowledgeC.db')
    if not os.path.exists(kdb):
        print('[EXTRACTOR] knowledgeC.db not found')
        return events
    
    try:
        conn = sqlite3.connect(kdb)
        c = conn.cursor()
        
        # Get actual columns in ZOBJECT
        c.execute("PRAGMA table_info(ZOBJECT)")
        columns = [col[1] for col in c.fetchall()]
        print('[EXTRACTOR] ZOBJECT columns: ' + str(columns))
        
        # Build query based on available columns
        has_start = 'ZSTARTDATE' in columns
        has_end = 'ZENDDATE' in columns
        has_value = 'ZVALUESTRING' in columns
        has_creation = 'ZCREATIONDATE' in columns
        
        select_cols = []
        if has_creation:
            select_cols.append('ZCREATIONDATE')
        else:
            select_cols.append('Z_PK as ZCREATIONDATE')
        select_cols.append('ZSTREAMNAME')
        if has_value:
            select_cols.append('ZVALUESTRING')
        else:
            select_cols.append('NULL as ZVALUESTRING')
        if has_start:
            select_cols.append('ZSTARTDATE')
        else:
            select_cols.append('NULL as ZSTARTDATE')
        if has_end:
            select_cols.append('ZENDDATE')
        else:
            select_cols.append('NULL as ZENDDATE')
        
        query = 'SELECT ' + ', '.join(select_cols) + ' FROM ZOBJECT WHERE ZSTREAMNAME LIKE ? OR ZSTREAMNAME LIKE ? OR ZSTREAMNAME LIKE ? OR ZSTREAMNAME LIKE ? ORDER BY ZCREATIONDATE DESC LIMIT 50000'
        
        c.execute(query, ('%usage%', '%app%', '%pickup%', '%unlock%'))
        
        for row in c.fetchall():
            creation, stream, value, start, end = row
            events.append({
                'source': 'screen_time',
                'timestamp': apple_time_to_dt(creation).isoformat() if creation else None,
                'event_type': stream,
                'app_name': value,
                'start_time': apple_time_to_dt(start).isoformat() if start else None,
                'end_time': apple_time_to_dt(end).isoformat() if end else None,
                'duration_seconds': (float(end) - float(start)) if (end and start) else None
            })
        
        # Also get display/backlit events (screen on/off)
        c.execute('SELECT ZCREATIONDATE, ZSTREAMNAME, ZVALUESTRING FROM ZOBJECT WHERE ZSTREAMNAME = ? ORDER BY ZCREATIONDATE DESC LIMIT 1000', ('/display/isBacklit',))
        for row in c.fetchall():
            creation, stream, value = row
            events.append({
                'source': 'screen_time',
                'timestamp': apple_time_to_dt(creation).isoformat() if creation else None,
                'event_type': 'screen_state',
                'app_name': 'screen_' + str(value),
                'start_time': None,
                'end_time': None,
                'duration_seconds': None
            })
        
        # Also get notification usage
        c.execute('SELECT ZCREATIONDATE, ZSTREAMNAME, ZVALUESTRING FROM ZOBJECT WHERE ZSTREAMNAME = ? ORDER BY ZCREATIONDATE DESC LIMIT 1000', ('/notification/usage',))
        for row in c.fetchall():
            creation, stream, value = row
            events.append({
                'source': 'screen_time',
                'timestamp': apple_time_to_dt(creation).isoformat() if creation else None,
                'event_type': 'notification',
                'app_name': str(value),
                'start_time': None,
                'end_time': None,
                'duration_seconds': None
            })
        
        conn.close()
        print('[EXTRACTOR] Screen Time: ' + str(len(events)) + ' events')
    except Exception as e:
        print('[EXTRACTOR] Screen Time failed: ' + str(e))
        import traceback
        traceback.print_exc()
    return events

def extract_locations():
    locs = []
    # Search multiple possible paths
    possible_paths = [
        os.path.expanduser('~/Library/Application Support/com.apple.routined/Location.sqlite'),
        os.path.expanduser('~/Library/Application Support/com.apple.routined/Local.sqlite'),
        os.path.expanduser('~/Library/Application Support/com.apple.routined/Local.sqlite-wal'),
    ]
    
    ldb = None
    for p in possible_paths:
        if os.path.exists(p):
            ldb = p
            break
    
    if not ldb:
        print('[EXTRACTOR] Locations.sqlite not found in any known path')
        return locs
    
    try:
        conn = sqlite3.connect(ldb)
        c = conn.cursor()
        
        # Check available tables
        c.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [t[0] for t in c.fetchall()]
        print('[EXTRACTOR] Location tables: ' + str(tables))
        
        # Try different table names
        if 'ZRTVISIT' in tables:
            c.execute('SELECT ZTIMESTAMP, ZLATITUDE, ZLONGITUDE, ZHORIZONTALACCURACY, ZARRIVALDATE, ZDEPARTUREDATE FROM ZRTVISIT ORDER BY ZTIMESTAMP DESC LIMIT 10000')
        elif 'ZVISIT' in tables:
            c.execute('SELECT ZTIMESTAMP, ZLATITUDE, ZLONGITUDE, ZHORIZONTALACCURACY, ZARRIVALDATE, ZDEPARTUREDATE FROM ZVISIT ORDER BY ZTIMESTAMP DESC LIMIT 10000')
        else:
            print('[EXTRACTOR] No visit table found in locations DB')
            conn.close()
            return locs
        
        for row in c.fetchall():
            ts, lat, lon, acc, arr, dep = row
            locs.append({
                'source': 'significant_locations',
                'timestamp': apple_time_to_dt(ts).isoformat() if ts else None,
                'latitude': lat,
                'longitude': lon,
                'accuracy_meters': acc,
                'arrival': apple_time_to_dt(arr).isoformat() if arr else None,
                'departure': apple_time_to_dt(dep).isoformat() if dep else None,
                'duration_minutes': ((float(dep) - float(arr)) / 60) if (dep and arr) else None,
                'place_identifier': None
            })
        conn.close()
        print('[EXTRACTOR] Locations: ' + str(len(locs)) + ' visits')
    except Exception as e:
        print('[EXTRACTOR] Locations failed: ' + str(e))
        import traceback
        traceback.print_exc()
    return locs

def extract_health():
    records = []
    files = glob.glob(os.path.expanduser('~/Downloads/apple_health_export*/export.xml'))
    if not files:
        print('[EXTRACTOR] No Health export found. Export from iPhone: Health > Profile > Export')
        return records
    try:
        tree = ET.parse(files[0])
        root = tree.getroot()
        types = {
            'HKQuantityTypeIdentifierHeartRate': 'heart_rate',
            'HKQuantityTypeIdentifierHeartRateVariabilitySDNN': 'hrv',
            'HKCategoryTypeIdentifierSleepAnalysis': 'sleep',
            'HKQuantityTypeIdentifierStepCount': 'steps',
            'HKQuantityTypeIdentifierActiveEnergyBurned': 'active_energy',
            'HKQuantityTypeIdentifierBasalEnergyBurned': 'resting_energy'
        }
        for rec in root.findall('.//Record'):
            rt = rec.get('type', '')
            if rt in types:
                records.append({
                    'source': 'healthkit',
                    'timestamp': rec.get('startDate'),
                    'event_type': types[rt],
                    'value': safe_val(rec.get('value')),
                    'unit': rec.get('unit'),
                    'device': rec.get('sourceName'),
                    'end_time': rec.get('endDate')
                })
        print('[EXTRACTOR] HealthKit: ' + str(len(records)) + ' records')
    except Exception as e:
        print('[EXTRACTOR] HealthKit failed: ' + str(e))
    return records

def extract_calendar():
    events = []
    # Search for calendar database
    candidates = [
        os.path.expanduser('~/Library/Calendars/Calendar.sqlitedb'),
    ] + glob.glob(os.path.expanduser('~/Library/Calendars/*/Calendar.sqlitedb')) + glob.glob(os.path.expanduser('~/Library/Calendars/**/*.sqlitedb'))
    
    cal_db = None
    for p in candidates:
        if os.path.exists(p):
            cal_db = p
            break
    
    if not cal_db:
        print('[EXTRACTOR] Calendar database not found')
        return events
    
    try:
        conn = sqlite3.connect(cal_db)
        c = conn.cursor()
        c.execute('SELECT summary, description, start_date, end_date, location, all_day, calendar_id FROM CalendarItem WHERE start_date IS NOT NULL ORDER BY start_date DESC LIMIT 10000')
        for row in c.fetchall():
            summary, desc, start, end, loc, all_day, cal_id = row
            events.append({
                'source': 'calendar',
                'timestamp': apple_time_to_dt(start).isoformat() if start else None,
                'event_type': 'commitment',
                'title': summary,
                'description': desc,
                'start_time': apple_time_to_dt(start).isoformat() if start else None,
                'end_time': apple_time_to_dt(end).isoformat() if end else None,
                'location': loc,
                'all_day': bool(all_day),
                'calendar_id': cal_id
            })
        conn.close()
        print('[EXTRACTOR] Calendar: ' + str(len(events)) + ' events from ' + cal_db)
    except Exception as e:
        print('[EXTRACTOR] Calendar failed: ' + str(e))
        import traceback
        traceback.print_exc()
    return events

def correlate(all_events):
    valid = [e for e in all_events if e.get('timestamp')]
    valid.sort(key=lambda x: x['timestamp'])
    for i, e in enumerate(valid):
        try:
            dt = datetime.fromisoformat(e['timestamp'].replace('Z', '+00:00'))
            e['hour_of_day'] = dt.hour
            e['day_of_week'] = dt.strftime('%A')
            e['date'] = dt.strftime('%Y-%m-%d')
        except:
            pass
        if i > 0:
            e['previous_event_type'] = valid[i-1].get('event_type')
            e['previous_source'] = valid[i-1].get('source')
        if i < len(valid) - 1:
            e['next_event_type'] = valid[i+1].get('event_type')
            e['next_source'] = valid[i+1].get('source')
    return valid

def main():
    print('=' * 70)
    print('NEUROCITY LIFE LOG EXTRACTOR v2')
    print('Extracting your digital shadow...')
    print('=' * 70)
    
    all_events = []
    all_events.extend(extract_screen_time())
    all_events.extend(extract_locations())
    all_events.extend(extract_health())
    all_events.extend(extract_calendar())
    
    print('[TOTAL] Raw events: ' + str(len(all_events)))
    
    correlated = correlate(all_events)
    
    log = {
        'extraction_timestamp': datetime.now().isoformat(),
        'total_events': len(correlated),
        'date_range': {
            'earliest': correlated[0]['timestamp'] if correlated else None,
            'latest': correlated[-1]['timestamp'] if correlated else None
        },
        'source_breakdown': {},
        'behavioral_patterns': {},
        'events': correlated
    }
    
    for e in correlated:
        src = e.get('source', 'unknown')
        log['source_breakdown'][src] = log['source_breakdown'].get(src, 0) + 1
    
    app_by_hour = defaultdict(lambda: defaultdict(int))
    loc_visits = defaultdict(int)
    sleep_hours = []
    
    for e in correlated:
        if e['source'] == 'screen_time' and e.get('app_name'):
            app_by_hour[e.get('hour_of_day', 0)][e['app_name']] += 1
        if e['source'] == 'significant_locations':
            loc = str(round(e.get('latitude', 0), 4)) + ',' + str(round(e.get('longitude', 0), 4))
            loc_visits[loc] += 1
        if e['source'] == 'healthkit' and e.get('event_type') == 'sleep':
            try:
                s = datetime.fromisoformat(e['timestamp'].replace('Z', '+00:00'))
                en = datetime.fromisoformat(e['end_time'].replace('Z', '+00:00'))
                sleep_hours.append((en - s).total_seconds() / 3600)
            except:
                pass
    
    log['behavioral_patterns'] = {
        'peak_app_hours': {str(h): dict(apps) for h, apps in sorted(app_by_hour.items())},
        'most_visited_locations': dict(sorted(loc_visits.items(), key=lambda x: -x[1])[:20]),
        'average_sleep_hours': sum(sleep_hours) / len(sleep_hours) if sleep_hours else None,
        'sleep_data_points': len(sleep_hours)
    }
    
    with open(OUTPUT_FILE, 'w') as f:
        json.dump(log, f, indent=2, default=str)
    
    print('[COMPLETE] Saved to: ' + OUTPUT_FILE)
    print('[COMPLETE] Events: ' + str(len(correlated)))
    print('[COMPLETE] Sources: ' + str(dict(log['source_breakdown'])))
    if correlated:
        print('[COMPLETE] Range: ' + str(log['date_range']['earliest']) + ' to ' + str(log['date_range']['latest']))
    
    # Trigger Council analysis
    print('[COUNCIL] Triggering analysis...')
    result = subprocess.run(
        ['/usr/bin/python3', os.path.expanduser('~/NeuroCity/council_life_analyzer.py')],
        capture_output=True,
        text=True
    )
    if result.stdout:
        print(result.stdout)
    if result.stderr:
        print('[COUNCIL ERROR] ' + result.stderr)
    
    # Trigger Delta analysis
    print('[DELTA] Triggering delta watch...')
    result2 = subprocess.run(
        ['/usr/bin/python3', os.path.expanduser('~/NeuroCity/council_delta_analyzer.py')],
        capture_output=True,
        text=True
    )
    if result2.stdout:
        print(result2.stdout)
    if result2.stderr:
        print('[DELTA ERROR] ' + result2.stderr)
    
    return log

if __name__ == '__main__':
    main()
