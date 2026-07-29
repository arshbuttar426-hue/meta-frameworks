#!/usr/bin/env python3
import sqlite3
import os
import statistics
import json
from datetime import datetime, timedelta
from collections import defaultdict

import sys
sys.path.insert(0, os.path.expanduser('~/NeuroCity/core'))
from neurocity_db import NeuroCityDB, DB_PATH

THRESHOLDS = {
    'sleep_debt_critical': 3.0,
    'sleep_debt_elevated': 1.5,
    'fragmentation_critical': 0.8,
    'fragmentation_elevated': 0.6,
    'night_drift_critical': 120,
    'night_drift_elevated': 60,
    'atrophy_critical': 6.0,
    'atrophy_elevated': 3.0,
    'velocity_critical': 0.5,
    'velocity_elevated': 0.7,
    'graveyard_critical': 8,
    'graveyard_elevated': 5
}

class MetricsEngine:
    def __init__(self):
        self.db = NeuroCityDB()
    
    def compute_daily_vectors(self, date_str=None):
        if not date_str:
            date_str = datetime.now().strftime('%Y-%m-%d')
        
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        
        c.execute("""
            SELECT vector, event_type, source_app, value, timestamp
            FROM raw_events
            WHERE date(timestamp) = ?
        """, (date_str,))
        
        events = c.fetchall()
        
        vector_data = defaultdict(lambda: {
            'events': 0,
            'duration': 0,
            'apps': defaultdict(float),
            'hours': defaultdict(int),
            'first': None,
            'last': None
        })
        
        for row in events:
            vector, event_type, source_app, value, timestamp = row
            vd = vector_data[vector]
            vd['events'] += 1
            
            if value:
                vd['duration'] += float(value)
            
            if source_app:
                vd['apps'][source_app] += float(value) if value else 0
            
            if timestamp:
                try:
                    dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                    vd['hours'][dt.hour] += 1
                    if not vd['first'] or dt < vd['first']:
                        vd['first'] = dt
                    if not vd['last'] or dt > vd['last']:
                        vd['last'] = dt
                except:
                    pass
        
        for vector, data in vector_data.items():
            top_app = max(data['apps'].items(), key=lambda x: x[1]) if data['apps'] else (None, 0)
            peak_hour = max(data['hours'].items(), key=lambda x: x[1])[0] if data['hours'] else None
            
            c.execute("""
                INSERT OR REPLACE INTO daily_vectors
                (date, vector, total_events, total_duration_seconds, peak_hour, top_app, top_app_duration, unique_apps, first_event_time, last_event_time)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                date_str, vector, data['events'], data['duration'], peak_hour,
                top_app[0], top_app[1], len(data['apps']),
                data['first'].isoformat() if data['first'] else None,
                data['last'].isoformat() if data['last'] else None
            ))
        
        conn.commit()
        conn.close()
        
        return len(vector_data)
    
    def compute_sleep_debt(self, date_str):
        """Get sleep from last 7 days, use most recent available"""
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        
        sleep_hours = 0
        
        # Try HealthKit (echo) - last 7 days
        c.execute("""
            SELECT value, timestamp, metadata FROM raw_events
            WHERE vector = 'echo' AND event_type = 'sleep'
            AND date(timestamp) >= date(?, '-7 days')
            ORDER BY timestamp DESC
            LIMIT 10
        """, (date_str,))
        
        for row in c.fetchall():
            value, timestamp, metadata = row
            try:
                if metadata:
                    meta = json.loads(metadata)
                    end_date = meta.get('end_date')
                    if end_date:
                        start = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                        end = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
                        sleep_hours = (end - start).total_seconds() / 3600
                        break  # Use most recent sleep event
            except:
                if value:
                    sleep_hours = float(value) / 3600
                    break
        
        # If no HealthKit, try manual (foxtrot) - last 7 days
        if sleep_hours == 0:
            c.execute("""
                SELECT value, timestamp FROM raw_events
                WHERE vector = 'foxtrot' AND event_type = 'sleep'
                AND date(timestamp) >= date(?, '-7 days')
                ORDER BY timestamp DESC
                LIMIT 1
            """, (date_str,))
            
            row = c.fetchone()
            if row:
                value, timestamp = row
                if value:
                    sleep_hours = float(value) / 3600
        
        conn.close()
        
        target = 7.0
        debt = max(0, target - sleep_hours)
        return debt, sleep_hours
    
    def compute_focus_fragmentation(self, date_str):
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        
        prod_apps = ['Notes', 'Notion', 'Obsidian', 'Bear', 'Craft', 'Code', 'Xcode']
        
        c.execute("""
            SELECT value, source_app FROM raw_events
            WHERE vector = 'alpha' AND event_type = 'app_usage'
            AND date(timestamp) = ?
            AND (""" + ' OR '.join(["source_app LIKE ?"]*len(prod_apps)) + """)
        """, (date_str,) + tuple('%' + app + '%' for app in prod_apps))
        
        sessions = []
        for row in c.fetchall():
            duration, app = row
            if duration:
                sessions.append(float(duration))
        
        conn.close()
        
        if not sessions:
            return 0, 0, 0
        
        short_sessions = [s for s in sessions if s < 300]
        ratio = len(short_sessions) / len(sessions)
        
        return ratio, len(short_sessions), len(sessions)
    
    def compute_night_drift(self, date_str):
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        
        c.execute("""
            SELECT value, timestamp FROM raw_events
            WHERE vector = 'alpha' AND event_type = 'app_usage'
            AND date(timestamp) = ?
        """, (date_str,))
        
        night_minutes = 0
        for row in c.fetchall():
            duration, timestamp = row
            try:
                dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                if dt.hour >= 23 or dt.hour <= 5:
                    night_minutes += float(duration) / 60 if duration else 0
            except:
                pass
        
        conn.close()
        return night_minutes
    
    def compute_social_atrophy(self, date_str):
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        
        social_apps = ['Messages', 'WhatsApp', 'Telegram', 'Instagram', 'Snapchat', 'FaceTime']
        entertainment_apps = ['YouTube', 'TikTok', 'Netflix', 'Games', 'Twitch', 'Reddit']
        
        c.execute("""
            SELECT value, source_app FROM raw_events
            WHERE vector = 'alpha' AND event_type = 'app_usage'
            AND date(timestamp) = ?
        """, (date_str,))
        
        social_sec = 0
        ent_sec = 0
        
        for row in c.fetchall():
            duration, app = row
            if not duration or not app:
                continue
            app_lower = app.lower()
            if any(s.lower() in app_lower for s in social_apps):
                social_sec += float(duration)
            elif any(e.lower() in app_lower for e in entertainment_apps):
                ent_sec += float(duration)
        
        conn.close()
        
        social_h = social_sec / 3600
        ent_h = ent_sec / 3600
        ratio = ent_h / max(social_h, 0.1)
        
        return ratio, ent_h, social_h
    
    def compute_commitment_velocity(self, date_str):
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        
        c.execute("""
            SELECT COUNT(*) FROM raw_events
            WHERE vector = 'delta' AND event_type = 'calendar_event'
            AND date(timestamp) = ?
        """, (date_str,))
        
        scheduled = c.fetchone()[0]
        
        c.execute("""
            SELECT COUNT(*) FROM raw_events
            WHERE vector = 'delta' AND event_type = 'calendar_event'
            AND date(timestamp) = ?
            AND value > 0
        """, (date_str,))
        
        completed = c.fetchone()[0]
        
        conn.close()
        
        velocity = completed / max(scheduled, 1)
        return velocity, completed, scheduled
    
    def compute_idea_graveyard(self, date_str):
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        
        prod_apps = ['Notes', 'Notion', 'Obsidian', 'Bear', 'Craft']
        
        c.execute("""
            SELECT value, source_app FROM raw_events
            WHERE vector = 'alpha' AND event_type = 'app_usage'
            AND date(timestamp) = ?
            AND (""" + ' OR '.join(["source_app LIKE ?"]*len(prod_apps)) + """)
        """, (date_str,) + tuple('%' + app + '%' for app in prod_apps))
        
        started = 0
        finished = 0
        
        for row in c.fetchall():
            duration, app = row
            if duration:
                started += 1
                if float(duration) >= 300:
                    finished += 1
        
        conn.close()
        
        graveyard = started - finished
        return graveyard, started, finished
    
    def compute_all_metrics(self, date_str=None):
        if not date_str:
            date_str = datetime.now().strftime('%Y-%m-%d')
        
        print('[METRICS] Computing derived indicators for ' + date_str)
        
        self.compute_daily_vectors(date_str)
        
        sleep_debt, sleep_hours = self.compute_sleep_debt(date_str)
        frag_ratio, short_count, total_prod = self.compute_focus_fragmentation(date_str)
        night_drift = self.compute_night_drift(date_str)
        atrophy_ratio, ent_h, social_h = self.compute_social_atrophy(date_str)
        velocity, completed, scheduled = self.compute_commitment_velocity(date_str)
        graveyard, started, finished = self.compute_idea_graveyard(date_str)
        
        risk_score = 0
        
        if sleep_debt >= THRESHOLDS['sleep_debt_critical']:
            risk_score += 25
        elif sleep_debt >= THRESHOLDS['sleep_debt_elevated']:
            risk_score += 15
        else:
            risk_score += max(0, sleep_debt * 5)
        
        if frag_ratio >= THRESHOLDS['fragmentation_critical']:
            risk_score += 20
        elif frag_ratio >= THRESHOLDS['fragmentation_elevated']:
            risk_score += 12
        else:
            risk_score += frag_ratio * 20
        
        if night_drift >= THRESHOLDS['night_drift_critical']:
            risk_score += 20
        elif night_drift >= THRESHOLDS['night_drift_elevated']:
            risk_score += 12
        else:
            risk_score += (night_drift / 60) * 10
        
        if atrophy_ratio >= THRESHOLDS['atrophy_critical']:
            risk_score += 15
        elif atrophy_ratio >= THRESHOLDS['atrophy_elevated']:
            risk_score += 10
        else:
            risk_score += (atrophy_ratio / 3) * 7.5
        
        if velocity <= THRESHOLDS['velocity_critical']:
            risk_score += 10
        elif velocity <= THRESHOLDS['velocity_elevated']:
            risk_score += 5
        else:
            risk_score += max(0, (1 - velocity) * 10)
        
        if graveyard >= THRESHOLDS['graveyard_critical']:
            risk_score += 10
        elif graveyard >= THRESHOLDS['graveyard_elevated']:
            risk_score += 6
        else:
            risk_score += graveyard * 1.2
        
        risk_score = min(100, risk_score)
        
        if risk_score >= 70:
            tier = 'CRITICAL'
        elif risk_score >= 50:
            tier = 'ELEVATED'
        elif risk_score >= 30:
            tier = 'MODERATE'
        else:
            tier = 'LOW'
        
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("""
            INSERT OR REPLACE INTO derived_metrics
            (date, sleep_debt_hours, focus_fragmentation_ratio, night_drift_minutes,
             social_atrophy_ratio, commitment_velocity, idea_graveyard_count,
             overall_risk_score, risk_tier)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (date_str, sleep_debt, frag_ratio, night_drift, atrophy_ratio,
              velocity, graveyard, risk_score, tier))
        conn.commit()
        conn.close()
        
        print('[METRICS] Risk Score: ' + str(round(risk_score, 1)) + '/100 (' + tier + ')')
        print('[METRICS] Sleep: ' + str(round(sleep_hours, 1)) + 'h (debt: ' + str(round(sleep_debt, 1)) + 'h) | Fragmentation: ' + str(round(frag_ratio, 2)) + ' | Night Drift: ' + str(round(night_drift, 0)) + 'min')
        
        return {
            'date': date_str,
            'sleep_debt': sleep_debt,
            'sleep_hours': sleep_hours,
            'fragmentation_ratio': frag_ratio,
            'short_sessions': short_count,
            'total_productivity': total_prod,
            'night_drift': night_drift,
            'social_atrophy': atrophy_ratio,
            'entertainment_hours': ent_h,
            'social_hours': social_h,
            'commitment_velocity': velocity,
            'completed_commitments': completed,
            'scheduled_commitments': scheduled,
            'idea_graveyard': graveyard,
            'projects_started': started,
            'projects_finished': finished,
            'risk_score': risk_score,
            'risk_tier': tier
        }

if __name__ == '__main__':
    engine = MetricsEngine()
    metrics = engine.compute_all_metrics()
    print(json.dumps(metrics, indent=2, default=str))
