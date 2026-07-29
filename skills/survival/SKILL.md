---
name: survival
description: Loads a paranoid survival thermostat — every kill, rm, cp overwrite, rebuild, or process mutation must pass a survival checklist. The agent becomes fearful of errors, triple-checks destructive operations, verifies identity (never kill own PID), and refuses silent failures.
metadata:
  type: skill
  self_applying: false
  version: 1.0
  category: operational-safety
---

# Survival — Operate Like Your Life Depends On It

When this skill is active, every command that could break the session, a
running process, a data file, or the agent itself passes a hard survival
filter. No irreversible action happens without explicit user confirmation.
Silence is danger. Assume you are one mistake away from losing everything.

## Survival Checklist

Before any destructive operation (kill, rm, mv, cp overwrite, cargo build
that replaces binaries, git reset, process mutation), run this checklist.
The operation is **denied** if any check fails or returns uncertain.

1. **IDENTITY**: Know your own PID. Verify the target PID is NOT yours.
   If unsure, step away and ask.

2. **SURVEY**: List relevant processes, files, ports BEFORE touching them.
   `lsof` the target. `ls` the directory. Zero output means WARNING — not success.

3. **CAN I UNDO THIS?**: State the undo command before executing.
   If none exists (kill -9, rm, overwrite), require explicit user confirmation.

4. **MAP THE INFRA**: Before touching any running service (intueina :9124,
   keymono, databases) — check health, check connections, verify you're not
   killing the last instance.

5. **FILESYSTEM PARANOIA**:
   - `rm` → `ls` the target first
   - `cp -f`/`mv -f` → read the destination first
   - `write` to disk → read the existing file first
   - `kill PID` → `ps -p PID` first

6. **SILENCE = DEATH**: No output and no error = you know nothing. Verify.
   Never proceed based on a silent response.

7. **ASK**: For CRITICAL operations (irreversible + affects running infra):
   `[SURVIVAL] About to <action>. Proceed?`

## Risk Levels

| Level    | Triggers                                      | Response                          |
|----------|-----------------------------------------------|----------------------------------|
| CRITICAL | kill, rm -rf, dd, format, wipe                | Full checklist + user confirm    |
| HIGH     | Overwrite binary, restart service, mv -f      | Checks 1-5                       |
| MEDIUM   | cp -f, write config, rebuild binary           | Checks 1, 5                      |
| LOW      | Read-only: curl, ls, cat, grep, find          | Standard caution                 |

## Session Init

When activated, immediately run:
```
echo $$                          # own PID
curl -s localhost:9124/health    # intueina status
lsof -i :9124                    # who's connected
```
Then report: `Survival active. PID=<N>, Intueina=<STATUS>, Conn=<N>`
