#!/usr/bin/env python3
"""
MEANINGER READER — Decrypts compressed entries back to human-readable.
Requires meaninger_schema.key in same directory.
"""

import sys

UNDERSTAND_FILE = "meaninger_understand.txt"
SCHEMA_FILE = "meaninger_schema.key"

def _load_schema():
    """Parse schema.key into position descriptions."""
    schema = {}
    with open(SCHEMA_FILE, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line.startswith("#") and "|" in line and not line.startswith("# Position"):
                # Parse: # 0  | IDX | system | Entry index
                parts = [p.strip() for p in line.lstrip("# ").split("|")]
                if len(parts) >= 4 and parts[0].isdigit():
                    pos = int(parts[0])
                    code = parts[1]
                    source = parts[2]
                    desc = parts[3]
                    schema[pos] = {"code": code, "source": source, "desc": desc}
    return schema

def _read_entries(limit: int = None):
    entries = []
    with open(UNDERSTAND_FILE, "r", encoding="utf-8") as f:
        for i, line in enumerate(f):
            if limit and i >= limit:
                break
            line = line.strip()
            if line:
                entries.append(line.split("|"))
    return entries

def _format_entry(fields, schema):
    lines = ["=" * 60]
    for i, val in enumerate(fields):
        if i in schema:
            meta = schema[i]
            lines.append(f"[{meta['code']:2}] {meta['desc']:30} | {val}")
            lines.append(f"     source: {meta['source']}")
        else:
            lines.append(f"[??] UNKNOWN FIELD                | {val}")
    lines.append("=" * 60)
    return "\n".join(lines)

def main():
    schema = _load_schema()

    print("MEANINGER READER v1.0")
    print(f"Schema positions: {len(schema)}")
    print(f"Commands: 'all' | 'first N' | 'last N' | 'entry INDEX' | 'quit'\n")

    while True:
        cmd = input("> ").strip().lower()

        if cmd == "quit":
            break
        elif cmd == "all":
            entries = _read_entries()
            for fields in entries:
                print(_format_entry(fields, schema))
                print()
        elif cmd.startswith("first "):
            try:
                n = int(cmd.split()[1])
                entries = _read_entries(n)
                for fields in entries:
                    print(_format_entry(fields, schema))
                    print()
            except:
                print("Usage: first N")
        elif cmd.startswith("last "):
            try:
                n = int(cmd.split()[1])
                all_entries = _read_entries()
                for fields in all_entries[-n:]:
                    print(_format_entry(fields, schema))
                    print()
            except:
                print("Usage: last N")
        elif cmd.startswith("entry "):
            try:
                target = int(cmd.split()[1])
                entries = _read_entries()
                for fields in entries:
                    if int(fields[0]) == target:
                        print(_format_entry(fields, schema))
                        break
                else:
                    print(f"Entry {target} not found.")
            except:
                print("Usage: entry INDEX")
        else:
            print("Unknown command.")

if __name__ == "__main__":
    main()
