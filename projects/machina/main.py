#!/usr/bin/env python3
"""
Forensic Instrument — Entry Point
==================================
Run this file to start the engine.
"""

import os, sys

# Ensure env vars are set
if not os.environ.get("FORENSIC_CONFIG_KEY"):
    os.environ["FORENSIC_CONFIG_KEY"] = "dev"
    print("[WARN] FORENSIC_CONFIG_KEY not set, using default 'dev'")

if not os.environ.get("FORENSIC_OPERATOR_KEY"):
    os.environ["FORENSIC_OPERATOR_KEY"] = "dev"
    print("[WARN] FORENSIC_OPERATOR_KEY not set, using default 'dev'")

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from engine import ForensicEngine

def main():
    print("=" * 60)
    print("FORENSIC INSTRUMENT v1.0.0-constitution")
    print("=" * 60)

    try:
        engine = ForensicEngine("config.json")
        print("
" + engine.get_status())
        print("
Engine ready.")
        print("
Example usage:")
        print('  result = engine.ingest_symbol("B", (1,0,2,1), known_value=0.85)')
        print('  pred = engine.predict("B", (1,0,2,1), current_price=0.85)')

        # Demo run
        print("
--- DEMO RUN ---")
        for sym, corners, val in [("B", (1,0,2,1), 0.85), ("C", (2,0,0,1), 1.45)]:
            r = engine.ingest_symbol(sym, corners, known_value=val)
            print(f"  {sym}: {r['record'].quality}")

        health = engine.health_check()
        print(f"
System health: {health['codec']['frozen']}")
        print(f"Registry groups: {health['registry']['total_groups']}")
        print(f"Status: {engine.get_status()}")

        return engine

    except Exception as e:
        print(f"
[ERROR] {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    engine = main()
