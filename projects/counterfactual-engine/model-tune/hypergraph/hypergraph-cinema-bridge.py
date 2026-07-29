#!/usr/bin/env python3
"""
hypergraph-cinema-bridge.py

Reads cinema knowledge base (YAMLs) and feeds structured context
to the hypergraph engine for cinematic reasoning.

Usage:
    python3 hypergraph-cinema-bridge.py "a glass shattering in reverse, chaos frozen mid-air"
"""
import sys
import yaml
from pathlib import Path

CINEMA_DATA = Path("/Users/arshbuttar/cinema/data")
KNOWLEDGE_BANK = CINEMA_DATA / "knowledge-bank"

def load_knowledge(category: str, file: str) -> dict:
    path = KNOWLEDGE_BANK / category / file
    if path.exists():
        with open(path) as f:
            return yaml.safe_load(f)
    return {}

def build_context(topic: str) -> str:
    chaos = load_knowledge("aesthetics", "cinematic-chaos.yaml")
    mood = load_knowledge("aesthetics", "mood.yaml")
    
    context = f"""TOPIC: {topic}

CINEMATIC CHAOS RULES:
{chr(10).join("- " + r for r in chaos.get("rules", []))}

COHERENCE ANCHORS:
{chr(10).join("- " + a for a in chaos.get("coherence_anchors", []))}

8-SECOND STRUCTURE:
{chr(10).join("- " + p["phase"] + " (" + p["duration"] + "): " + p["description"] for p in chaos.get("chaos_escalation", []))}

MOOD PALETTE:
{chr(10).join("- " + m for m in mood.get("rules", [])[:4])}

INSTRUCTION:
Create an 8-second Google Veo 3.1 prompt. The sequence must be chaotic yet coherent.
Follow the 8-second structure exactly. Use ONE coherence anchor. Return ONLY the prompt.
"""
    return context

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 hypergraph-cinema-bridge.py <topic>")
        sys.exit(1)
    topic = " ".join(sys.argv[1:])
    print(build_context(topic))
