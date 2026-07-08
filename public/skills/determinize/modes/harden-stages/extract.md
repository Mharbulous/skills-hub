# Stage 4: Extract

## Goal

Turn the selected candidate section into a verified, runnable helper
script, and produce a hardened SKILL.md that calls it.

## Prerequisites

- `baseline-results.md` and the scenario files from Stage 3, saved to disk.
- A language selected (per `modes/harden.md`'s language-selection
  procedure) and its reference file (`references/python.md` or
  `references/javascript.md`) loaded — this must have happened by now at
  the latest.

## Steps

### Step 1: Write and run the helper script

Write the helper script in `<skill-name>-hardened/scripts/`, following the
template and conventions in the loaded language reference. The script
must:

- Accept the candidate section's inputs.
- Produce the candidate section's outputs.
- Handle every edge case documented in the Stage 3 scenario files.

Then **actually run it** against sample input and verify the output — do
not assume correctness from reading the script.

### Step 2: Build the hardened SKILL.md

Copy the original SKILL.md into `<skill-name>-hardened/SKILL.md`. Replace
only the extracted section with:

```
Run: <runtime> scripts/<name>.<ext> <args>
```

plus a 1–2 line note describing input, output, and purpose. Keep every
non-deterministic section and every reference/declarative section inline,
unchanged. The result should read as an orchestrator that delegates the
one deterministic piece to a script and keeps everything else as
LLM-driven prose.

### Step 3: Copy supporting files

Copy `references/` and any other supporting files from the original skill
directory into the hardened directory, unchanged.

## Output artifacts

```
<skill-name>-hardened/
  SKILL.md              # procedural section replaced with a script call
  scripts/<name>.<ext>  # extracted helper script (verified runnable)
  references/           # inherited from original (if any)
  tests/                # already present from Stage 3
    baseline-results.md
    scenario-*.md
```

## Gate

Before proceeding: confirm the script runs successfully against sample
input, the hardened SKILL.md is complete and reads as an orchestrator, and
all supporting files are copied over.

**Read `verify.md` next.**
