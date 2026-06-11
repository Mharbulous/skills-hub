---
name: one-click-testing
description: Use when testing or improving the one-click firm setup system - pops next lawyer from the sample list, runs buildFirmProfile, evaluates against success criteria, iterates on the prompt, and commits improvements. Triggers on "test one-click", "improve firm extraction", "calibrate firm profile"
disable-model-invocation: true
---

# One-Click Testing

Single-lawyer-per-run testing workflow for the one-click firm setup system (`functions/firm-profile/buildFirmProfile.js`). Each invocation consumes one lawyer pair from the sample list, giving 20 unique test runs.

## Success Criteria

Every extracted firm profile MUST satisfy ALL of these:

1. **Third-Person Description** — `firmDescription` uses third-person narrator voice ("X Law is a firm that..."), never first-person ("We believe..."). No verbatim copy from website.
2. **Firm Practice Areas** — `firmPracticeAreas` array present in output, positioned after `firmDescription`. Derived primarily from aggregated lawyer bios, NOT firm marketing pages.
3. **Per-Lawyer Practice Areas** — Each lawyer in `personnel` has a `practiceAreas` string array. Bar Number and Jurisdiction fields are REMOVED from the schema.
4. **Lawyer Bios > Firm Claims** — When firm-level practice area claims conflict with aggregated lawyer bio specialties, lawyer data takes precedence.
5. **Full Address** — `firmStreetAddress`, `firmCity`, `firmState`, `firmZip` all populated (when address exists on firm website).

## Workflow

### Phase 1: Pop Next Lawyer from Sample List

1. Read `tests/samples/lawyerlist.md`
2. Parse the markdown tables to find the **first data row** (the first `| # | Name | Email | Notes |` entry that hasn't been consumed yet)
3. If no entries remain, STOP and report: "Lawyer list exhausted — all 20 test pairs have been used."
4. **Display the chosen pair to the user** — output the name, email, and notes so the user can verify which lawyer was selected
5. Extract `name` and `email` from that row
6. Write to `functions/test-lawyers.json` as: `[{ "name": "...", "email": "..." }]` (single-entry array)
7. **Remove that row from `tests/samples/lawyerlist.md`** — delete the entire table row. Also decrement the count in the section header comment (e.g., "Solo Practitioners (4)" becomes "Solo Practitioners (3)"). If a section becomes empty (0 entries), remove the section header and empty table header too.
8. Update the `# | Name | Email | Notes` numbering in remaining rows (re-number sequentially starting from 1 across all sections)

**IMPORTANT:** Display the chosen lawyer pair BEFORE running the test, so the user sees it immediately.

### Phase 2: Run Test

```bash
cd functions && node test-firm-profile.js --batch test-lawyers.json
```

The harness evaluates the result against all success criteria and prints:
- Per-result scores with specific failure reasons
- Summary with per-check pass rates

### Phase 3: Evaluate & Iterate

Read test results. For each failing criterion:

| Failure | Fix Location |
|---------|-------------|
| First-person description | Strengthen prompt instruction in `PROMPT` constant |
| Missing firmPracticeAreas | Add field to prompt JSON schema + extraction instruction |
| Missing per-lawyer practiceAreas | Add to personnel schema in prompt + instruct to extract from bios |
| Bar # still present | Remove from prompt schema entirely |
| Missing address components | Strengthen address extraction instructions |

**Edit ONLY** the `PROMPT` constant and return schema in `functions/firm-profile/buildFirmProfile.js`. Do NOT change the function signature, the `createAI()` logic, or the JSON parsing.

After each edit, re-run the test. Target: **all checks passing**.

### Phase 4: Update Dependent Code

After the prompt and schema are finalized, update these files to match the new schema:

- `functions/firm-profile/buildFirmProfile.js` — return object: add `firmPracticeAreas`, defensively map personnel to strip `barNumber`/`licensingJurisdiction` and normalize `practiceAreas` to array
- `src/core/firm/composables/useFirmMembersManager.js` — `applyProfile()`: pass `firmPracticeAreas` in firm update, pass `practiceAreas` per member, remove bar fields
- `src/core/firm/components/FirmProfilePreviewDialog.vue` — replace Bar #/Jurisdiction columns with Practice Areas column, add firm-level practice areas display
- `src/dev-demos/views/OneClickSetupTester.vue` — update `firmFields` array and personnel table columns
- `src/services/firmService.js` — `addUnlicensedMember()`: replace `barNumber`/`licensingJurisdiction` with `practiceAreas`
- `functions/test-firm-profile.js` — evaluation checks for all success criteria

### Phase 5: Commit

Commit all changes with a descriptive message referencing the test result.

## Key Files

| File | Role |
|------|------|
| `tests/samples/lawyerlist.md` | Sample lawyer pairs (consumed one per run, 20 total) |
| `functions/firm-profile/buildFirmProfile.js` | Extraction prompt + Gemini call (edit the PROMPT constant) |
| `functions/test-firm-profile.js` | CLI test harness with automated evaluation |
| `functions/test-lawyers.json` | Test data (overwritten each run with single lawyer pair) |
| `src/core/firm/composables/useFirmMembersManager.js` | Frontend consumer of profile data |
| `src/core/firm/components/FirmProfilePreviewDialog.vue` | Preview UI for extracted profile |
| `src/services/firmService.js` | Firestore writes for firm members |

## Red Flags — STOP and Reassess

- Changing `createAI()`, JSON parsing, or function signature — only the `PROMPT` constant and return schema should change
- Batch pass rate below 50% after 3 iterations — the prompt approach may need structural rethinking (e.g., two-pass extraction)
- Skipping the batch re-run after a prompt edit — EVERY change must be validated
- Adding bar # or jurisdiction back "for completeness" — these are explicitly removed from the schema

## Common Mistakes

- **Editing function logic instead of the prompt** — Only the `PROMPT` constant and return schema need changing. The AI call, JSON parsing, and `createAI()` are correct as-is.
- **Forgetting to update the return object** — When adding `firmPracticeAreas` to the prompt schema, also add it to the return object (line ~114-126). Defensively map personnel to strip any hallucinated bar fields.
- **Not re-running the batch after changes** — Every prompt edit must be validated with a full batch run.
- **Using GEMINI_API_KEY for grounded search** — Google Search grounding requires Vertex AI (`GOOGLE_CLOUD_PROJECT`), not the Developer API key. Use ADC.
- **Relying on firm marketing pages for practice areas** — The prompt must instruct Gemini to derive practice areas primarily from lawyer bios, not the firm's "Areas of Practice" nav menu.
