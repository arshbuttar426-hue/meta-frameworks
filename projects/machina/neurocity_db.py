#!/usr/bin/env python3
import sqlite3
import os
from datetime import datetime, timedelta
from collections import defaultdict

DB_PATH = os.path.expanduser('~/NeuroCity/neurocity_intelligence.db')
os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)

SCHEMA = """
CREATE TABLE IF NOT EXISTS raw_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL,
    vector TEXT NOT NULL,
    event_type TEXT NOT NULL,
    source_app TEXT,
    value REAL,
    value_str TEXT,
    metadata TEXT,
    ingestion_time TEXT DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_raw_time ON raw_events(timestamp);
CREATE INDEX IF NOT EXISTS idx_raw_vector ON raw_events(vector);
CREATE INDEX IF NOT EXISTS idx_raw_type ON raw_events(event_type);

CREATE TABLE IF NOT EXISTS daily_vectors (
    date TEXT NOT NULL,
    vector TEXT NOT NULL,
    total_events INTEGER DEFAULT 0,
    total_duration_seconds REAL DEFAULT 0,
    peak_hour INTEGER,
    top_app TEXT,
    top_app_duration REAL DEFAULT 0,
    unique_apps INTEGER DEFAULT 0,
    first_event_time TEXT,
    last_event_time TEXT,
    PRIMARY KEY (date, vector)
);

CREATE TABLE IF NOT EXISTS derived_metrics (
    date TEXT PRIMARY KEY,
    sleep_debt_hours REAL DEFAULT 0,
    focus_fragmentation_ratio REAL DEFAULT 0,
    night_drift_minutes REAL DEFAULT 0,
    social_atrophy_ratio REAL DEFAULT 0,
    commitment_velocity REAL DEFAULT 0,
    idea_graveyard_count INTEGER DEFAULT 0,
    overall_risk_score REAL DEFAULT 0,
    risk_tier TEXT DEFAULT 'LOW',
    computed_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS intervention_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT DEFAULT CURRENT_TIMESTAMP,
    trigger_metric TEXT,
    threshold_breached REAL,
    action_taken TEXT,
    target_app TEXT,
    enforcement_method TEXT,
    user_compliance INTEGER,
    outcome_notes TEXT
);

CREATE TABLE IF NOT EXISTS agent_states (
    agent_name TEXT PRIMARY KEY,
    status TEXT DEFAULT 'IDLE',
    current_task TEXT,
    last_run TEXT,
    queue_depth INTEGER DEFAULT 0,
    priority_level TEXT DEFAULT 'NORMAL'
);

CREATE TABLE IF NOT EXISTS config (
    key TEXT PRIMARY KEY,
    value TEXT,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
);
"""

class NeuroCityDB:
    def __init__(self, db_path=None):
        self.db_path = db_path or DB_PATH
        self._init_db()
    
    def _init_db(self):
        conn = sqlite3.connect(self.db_path)
        conn.executescript(SCHEMA)
        conn.commit()
        conn.close()
    
    def insert_event(self, timestamp, vector, event_type, source_app=None, 
                     value=None, value_str=None, metadata=None):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute("""
            INSERT INTO raw_events (timestamp, vector, event_type, source_app, value, value_str, metadata)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (timestamp, vector, event_type, source_app, value, value_str, metadata))
        conn.commit()
        conn.close()
    
    def bulk_insert_events(self, events):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.executemany("""
            INSERT INTO raw_events (timestamp, vector, event_type, source_app, value, value_str, metadata)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, events)
        conn.commit()
        conn.close()
    
    def get_metric_series(self, metric_name, days=7):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute("""
            SELECT date, {} FROM derived_metrics 
            WHERE date >= date('now', '-{} days')
            ORDER BY date
        """.format(metric_name, days))
        rows = c.fetchall()
        conn.close()
        return rows
    
    def get_latest_risk(self):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute("SELECT * FROM derived_metrics ORDER BY date DESC LIMIT 1")
        row = c.fetchone()
        conn.close()
        return row
    
    def log_intervention(self, trigger_metric, threshold_breached, action_taken,
                         target_app=None, enforcement_method=None):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute("""
            INSERT INTO intervention_log (trigger_metric, threshold_breached, action_taken, target_app, enforcement_method)
            VALUES (?, ?, ?, ?, ?)
        """, (trigger_metric, threshold_breached, action_taken, target_app, enforcement_method))
        conn.commit()
        conn.close()

if __name__ == '__main__':
    db = NeuroCityDB()
    print('NeuroCity Intelligence Database initialized at: ' + DB_PATH)
