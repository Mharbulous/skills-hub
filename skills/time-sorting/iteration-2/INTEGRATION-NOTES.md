# Integration Notes: Adding Validation Guidance to SKILL.md

## Summary

This document describes where and how to update the main `SKILL.md` file to reference the new Telus CSV validation guidance.

---

## File to Update

**Location:** `/sessions/cool-lucid-pascal/mnt/Coclerk/plugin/skills/time-sorting/SKILL.md`

---

## Change 1: Update Step 1c (Fetch Telus Connect Data)

### Current Text (Lines 168–172)

```markdown
#### 1c: Fetch Telus Connect Data

See `reference/TelusConnect.md` § CSV Format for expected columns and handling.

Store raw data as `raw:telus:{YYYY-MM-DD}`. Record `"telus"` in `sources_fetched` or `sources_failed`.
```

### Proposed Update

```markdown
#### 1c: Fetch Telus Connect Data

See `reference/TelusConnect.md` § CSV Format for expected columns and handling.
For validation rules, error scenarios, and graceful handling of malformed input, see `reference/TelusConnect.md` § CSV Validation & Error Handling.

Store raw data as `raw:telus:{YYYY-MM-DD}`. Record `"telus"` in `sources_fetched` or `sources_failed`.
```

### Change Details

- **Line number:** 170 (after "See `reference/TelusConnect.md`...")
- **Action:** Add one sentence pointing to the new validation section
- **Rationale:** Ensures practitioners and implementers know that validation guidance exists and where to find it

---

## Change 2: Add Validation Section to reference/TelusConnect.md

### File to Update

**Location:** `/sessions/cool-lucid-pascal/mnt/Coclerk/plugin/skills/time-sorting/reference/TelusConnect.md`

### Where to Add

At the end of the file, after the existing "Raw Data Storage" section (after line 54).

### Content to Add

Copy the entire contents of `TELUSCONNECT-VALIDATION-SECTION.md` (from iteration-2 folder) and insert it into `reference/TelusConnect.md`.

This includes:
- § CSV Validation & Error Handling (main section header)
- Subsections on expected format, validation rules, field parsing, examples, error handling, and graceful degradation

### Result

The updated `reference/TelusConnect.md` file will have:

1. Configuration (existing)
2. CSV Format (existing)
3. Activity Types (existing)
4. Normalizing for Merge (existing)
5. Source Hierarchy (existing)
6. Task Assignment Context (existing)
7. Raw Data Storage (existing)
8. **CSV Validation & Error Handling** ← NEW
   - Expected CSV Format
   - Validation Rules
   - Field Validation & Parsing
   - Example Valid CSV
   - Example Invalid CSV — Error Scenarios
   - Error Handling Strategy
   - Graceful Degradation
   - Logging

---

## Implementation Checklist

- [ ] Read current `reference/TelusConnect.md` to confirm structure
- [ ] Copy content from `TELUSCONNECT-VALIDATION-SECTION.md` (skip the "Integration Notes" subsection at the end)
- [ ] Paste into `reference/TelusConnect.md` after the "Raw Data Storage" section
- [ ] Update SKILL.md line 170 to add the reference sentence
- [ ] Test: Verify that a broken Telus CSV triggers an error message per the validation rules
- [ ] Test: Verify that Telus-less sorts continue gracefully (record "telus" in `sources_failed`)
- [ ] Document the new section in the skill's changelog/version notes if applicable

---

## Testing Guidance

Once integrated, the skill should exhibit these behaviors:

### Test 1: Valid Telus CSV
- File: Valid UTF-8, all required columns, well-formed data
- Expected: "Parsed Telus CSV: {N} entries. {M} entries with valid assignment context."
- Result: Activities assigned correctly, confidence levels reflect Telus signals

### Test 2: Missing Required Column
- File: UTF-8, missing "Direction" column
- Expected: Error message — "Telus CSV is missing required column(s): Direction. Found columns: Date, Time, Duration, Phone Number, Contact Name"
- Result: "telus" recorded in `sources_failed`, sort proceeds with other sources

### Test 3: Malformed Date
- File: UTF-8, all columns present, one row has date "2026-13-45"
- Expected: Error message — "Invalid date '2026-13-45' at row 3. Expected YYYY-MM-DD or MM/DD/YYYY"
- Result: "telus" recorded in `sources_failed`, sort proceeds

### Test 4: Non-UTF-8 Encoding
- File: Windows-1252 encoded, otherwise valid
- Expected: Error message — "Telus CSV file is not UTF-8 encoded. Please save the file as UTF-8 and try again."
- Result: "telus" recorded in `sources_failed`

### Test 5: Overlapping Calls
- File: Two calls with overlapping time windows on the same day
- Expected: No error; merge phase reconciles per source hierarchy
- Result: Both calls in merged timeline, or one replaces portion of the other per hierarchy

### Test 6: Duplicate Call
- File: Same call entry appears twice
- Expected: Silent skip; log message (if verbose mode enabled)
- Result: Deduplicated in merge; practitioner sees only one instance

### Test 7: No Telus CSV Provided
- Command: "sort time" (no `--telus` flag or CSV path)
- Expected: No error; "telus" recorded in `sources_fetched` as skipped or not attempted
- Result: Sort proceeds with TimeCamp + Google Calendar; note in output "Note: Telus data not available — phone calls are not included in this sort."

---

## Documentation & Handoff

### Deliverables

1. **TELUSCONNECT-VALIDATION-SECTION.md** — Ready to add to `reference/TelusConnect.md`
2. **ERROR-SCENARIOS.md** — Comprehensive catalog of errors, causes, and recovery paths
3. **INTEGRATION-NOTES.md** — This file; describes integration steps

### Files to Deliver to Practitioner/Developer

All three files in `/sessions/cool-lucid-pascal/mnt/Coclerk/plugin/skills/time-sorting/iteration-2/`:

- `TELUSCONNECT-VALIDATION-SECTION.md` — Copy to `reference/TelusConnect.md`
- `ERROR-SCENARIOS.md` — Reference for debugging and feature development
- `INTEGRATION-NOTES.md` — Integration checklist and testing guide

### Next Steps for Implementer

1. **Merge validation section into reference file:**
   - Open `reference/TelusConnect.md`
   - Append the content from `TELUSCONNECT-VALIDATION-SECTION.md`
   - Save and commit

2. **Update SKILL.md to reference validation:**
   - Edit line 170
   - Add sentence: "For validation rules, error scenarios, and graceful handling of malformed input, see `reference/TelusConnect.md` § CSV Validation & Error Handling."
   - Save and commit

3. **Implement validation logic in the skill (if not yet done):**
   - Follow the error detection and handling rules in `TELUSCONNECT-VALIDATION-SECTION.md`
   - Consult `ERROR-SCENARIOS.md` for comprehensive error catalog
   - Implement with early stopping (don't silently skip bad rows)
   - Report errors with line number, field, expected format, and recovery hint

4. **Test per the checklist in "Testing Guidance" section**

5. **Consider adding a "Telus CSV Troubleshooting" quick-reference guide to the practitioner handbook** (optional, lower priority)

---

## Backward Compatibility

These changes are **additive only** — they do not break existing functionality:

- Existing valid Telus CSVs continue to work
- New validation rules only reject malformed data (which was being silently ignored or causing crashes before)
- Graceful degradation is unchanged (missing Telus data is acceptable)
- No API or data model changes required

---

## Known Limitations & Future Enhancements

### Current Scope (Covered in This Iteration)

- UTF-8 encoding validation ✓
- Required column validation ✓
- Date, time, duration, phone number, direction field validation ✓
- Graceful error messages with line numbers and recovery hints ✓
- Duplicate and overlap detection (logging only) ✓

### Out of Scope (Future Iterations)

- Automatic charset detection and conversion (e.g., detect Windows-1252 and offer to convert)
- Telus portal API integration (instead of CSV upload)
- Batching and re-sort resumption (if a large file has 1 error at row 1000, allow skipping that row and continuing)
- Phone number international format support (currently North American only)
- Contact name fuzzy matching (to auto-assign calls to known clients)

---

## Questions & Support

For questions about:
- **Validation rules:** See `TELUSCONNECT-VALIDATION-SECTION.md`
- **Error scenarios & recovery:** See `ERROR-SCENARIOS.md`
- **Integration steps:** See this file (INTEGRATION-NOTES.md)
- **Testing:** See "Testing Guidance" section above

For implementation questions, refer to the skill's main documentation (`SKILL.md` and vision documents).
