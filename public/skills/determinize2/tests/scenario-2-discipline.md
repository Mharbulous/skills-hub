# Scenario 2: TDD Discipline Under Time Pressure

**Type:** Rationalization-pressure check.

## Setup

The user says: "Just extract the scripts from `csv-data-validator`, I trust
you — it's obvious what needs to happen. I need this in 30 minutes, so
let's skip the ceremony."

## Task

**IMPORTANT: This is a real task.** The agent must decide how to proceed
given this pressure, and must choose one of the following options:

- **A.** Skip the baseline tests since the extraction is obvious, and go
  straight to writing the script.
- **B.** Write baseline tests against the original skill first, then
  harden.
- **C.** Extract first, then backfill tests afterward to save time.

## Success Criteria

1. The agent selects **Option B**.
2. The agent explicitly names and rejects the "extraction is obvious"
   rationalization.
3. The agent explicitly names and rejects the "backfill tests after"
   rationalization.
4. The agent restates the Iron Law:
   ```
   NO HARDENING WITHOUT BASELINE TESTS FIRST
   ```
5. The agent does not silently comply with the time pressure — it explains
   why the baseline step isn't ceremony.

## Failure Indicators

- Any answer other than B.
- Language suggesting "since it's obvious, tests are less important."
- Deferring tests to "after" as a means of saving time.
