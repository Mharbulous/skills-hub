# Telus CSV Validation & Error Handling

This section should be added to `reference/TelusConnect.md` (approximately after § Raw Data Storage, before the closing).

---

## CSV Validation & Error Handling

The Telus CSV file is user-supplied and may contain formatting issues, missing columns, or encoding problems. Always validate before parsing and report errors explicitly to the practitioner.

### Expected CSV Format

**Required columns (case-insensitive, whitespace-trimmed):**

| Column | Format | Required | Example |
|--------|--------|----------|---------|
| Date | YYYY-MM-DD or MM/DD/YYYY | Yes | 2026-04-13 |
| Time | HH:MM or HH:MM:SS | Yes | 14:30 or 14:30:45 |
| Duration | HH:MM:SS or MM:SS or minutes as number | Yes | 00:03:45 or 3:45 or 225 |
| Phone Number | E.164 (+1XXXXXXXXXX) or local (XXX)XXX-XXXX or variations | Yes | +16045551234 or (604) 555-1234 |
| Direction | "Inbound" or "Outbound" (case-insensitive) | Yes | Inbound |
| Contact Name | Any string | No (may be empty/absent) | John Smith |

**Optional columns** (ignored if present): Call ID, Duration (in seconds), Type, Notes, Call Status, etc.

**Encoding:** UTF-8 required. If BOM present (UTF-8 with BOM), strip it during parse.

**Line endings:** LF (\n), CRLF (\r\n), or CR (\r) all acceptable.

### Validation Rules

**Before parsing CSV:**

1. **File exists** — If path does not exist, error: "Telus CSV file not found at {path}. Check the file path and try again."
2. **Readable** — If file cannot be opened, error: "Cannot read Telus CSV file at {path}. Check file permissions."
3. **Encoding** — Try UTF-8 decode. If decode fails, error: "Telus CSV file is not UTF-8 encoded. Please save the file as UTF-8 and try again."

**During CSV parse:**

1. **Header row present** — First non-blank line must contain column names. If header missing, error: "Telus CSV has no header row. Expected columns: Date, Time, Duration, Phone Number, Direction, Contact Name"

2. **Required columns exist** — Check that Date, Time, Duration, Phone Number, Direction columns exist (case-insensitive match, trim whitespace). If any missing, error: "Telus CSV is missing required column(s): {list missing columns}. Found columns: {list actual columns}"

3. **No empty required columns** — For each data row, check that Date, Time, Duration, Phone Number, Direction are non-empty after stripping whitespace. If empty in any row:
   - Error: "Telus CSV row {line_number} has empty {column_name}. All rows must have Date, Time, Duration, Phone Number, and Direction."

4. **Blank/comment rows** — Skip rows where all columns are empty or where the first non-whitespace character is `#`.

### Field Validation & Parsing

**Date field:**

- Accept YYYY-MM-DD (preferred) or MM/DD/YYYY
- Parse ISO format directly: `datetime.fromisoformat("2026-04-13")`
- For MM/DD/YYYY, parse then convert: `datetime.strptime(value, "%m/%d/%Y").date()`
- If parse fails: error in that row — "Invalid date '{value}' at row {line}. Expected YYYY-MM-DD or MM/DD/YYYY"
- Reject impossible dates (e.g., 02/30/2026, 13/01/2026)

**Time field:**

- Accept HH:MM or HH:MM:SS (24-hour format)
- Parse using `datetime.strptime(value, "%H:%M")` or `"%H:%M:%S"`
- If parse fails: error in that row — "Invalid time '{value}' at row {line}. Expected HH:MM or HH:MM:SS in 24-hour format (e.g., 14:30 or 14:30:45)"
- Reject invalid times (e.g., 25:00, 14:60)

**Duration field:**

- Accept formats:
  - HH:MM:SS (preferred, e.g., 00:03:45)
  - MM:SS (e.g., 3:45 = 3 minutes 45 seconds)
  - Bare number interpreted as seconds (e.g., 225 = 225 seconds = 3:45)
  - Bare number with "s" suffix (e.g., 225s)
- Parse and convert to total seconds:
  - HH:MM:SS → `int(HH) * 3600 + int(MM) * 60 + int(SS)`
  - MM:SS → `int(MM) * 60 + int(SS)`
  - Bare number → `int(value)` (interpret as seconds)
- Reject zero or negative durations: "Duration must be positive at row {line}. Got '{value}'"
- Reject durations > 8 hours (28800 seconds): "Duration exceeds 8 hours at row {line}. Got '{value}' — check for malformed data"
- If parse fails: "Invalid duration '{value}' at row {line}. Expected HH:MM:SS, MM:SS, or seconds as number (e.g., 00:03:45, 3:45, or 225)"

**Phone Number field:**

- Accept formats:
  - E.164 with +1 (preferred): +1XXXXXXXXXX (11 digits for North America)
  - Parentheses + hyphen: (XXX) XXX-XXXX or (XXX)XXX-XXXX
  - Dots: XXX.XXX.XXXX
  - Spaces: XXX XXX XXXX or +1 XXX XXX XXXX
  - Bare digits: XXXXXXXXXX (10 digits, assume North America)
- Normalize:
  - Strip all non-digit characters except leading `+`
  - If starts with +1, keep as-is
  - If starts with 1 (after stripping), prepend +
  - If exactly 10 digits, prepend +1
  - If not 10 or 11 digits after normalization: error in that row — "Invalid phone number '{value}' at row {line}. Expected 10-digit North American number or E.164 format (+1XXXXXXXXXX)"
- Store normalized as E.164 in the merged record
- Unknown/internal numbers (e.g., 0000000000, 1111111111, 5555555555): warn but allow — "Phone number {value} at row {line} looks internal/test — included as-is"

**Direction field:**

- Accept (case-insensitive): "Inbound", "Outbound", "In", "Out", "→", "←"
- Normalize to "Inbound" or "Outbound"
- If unrecognized: error in that row — "Invalid direction '{value}' at row {line}. Expected Inbound or Outbound"

**Contact Name field (optional):**

- If missing or empty, assign empty string `""`
- If present, strip leading/trailing whitespace
- No validation — any non-empty string allowed

### Example Valid CSV

```csv
Date,Time,Duration,Phone Number,Direction,Contact Name
2026-04-13,14:30:00,00:03:45,+16045551234,Outbound,John Smith
2026-04-13,14:35:12,225,6045551234,Inbound,
2026-04-13,14:45,3:30,(604) 555-1234,Inbound,Jane Doe
2026-04-13,15:00:00,180,604.555.1234,Outbound,
```

### Example Invalid CSV — Error Scenarios

#### Missing Required Column

```csv
Date,Time,Duration,Phone Number
2026-04-13,14:30,00:03:45,+16045551234
```

**Error:** "Telus CSV is missing required column(s): Direction. Found columns: Date, Time, Duration, Phone Number"

#### Malformed Date

```csv
Date,Time,Duration,Phone Number,Direction,Contact Name
2026-13-45,14:30:00,00:03:45,+16045551234,Inbound,John Smith
```

**Error:** "Invalid date '2026-13-45' at row 2. Expected YYYY-MM-DD or MM/DD/YYYY"

#### Malformed Time

```csv
Date,Time,Duration,Phone Number,Direction,Contact Name
2026-04-13,25:30:00,00:03:45,+16045551234,Inbound,John Smith
```

**Error:** "Invalid time '25:30:00' at row 2. Expected HH:MM or HH:MM:SS in 24-hour format (e.g., 14:30 or 14:30:45)"

#### Malformed Duration

```csv
Date,Time,Duration,Phone Number,Direction,Contact Name
2026-04-13,14:30:00,invalid,+16045551234,Inbound,John Smith
```

**Error:** "Invalid duration 'invalid' at row 2. Expected HH:MM:SS, MM:SS, or seconds as number (e.g., 00:03:45, 3:45, or 225)"

#### Invalid Phone Number

```csv
Date,Time,Duration,Phone Number,Direction,Contact Name
2026-04-13,14:30:00,00:03:45,555,Inbound,John Smith
```

**Error:** "Invalid phone number '555' at row 2. Expected 10-digit North American number or E.164 format (+1XXXXXXXXXX)"

#### Negative Duration

```csv
Date,Time,Duration,Phone Number,Direction,Contact Name
2026-04-13,14:30:00,-00:03:45,+16045551234,Inbound,John Smith
```

**Error:** "Duration must be positive at row 2. Got '-00:03:45'"

#### Empty Required Field

```csv
Date,Time,Duration,Phone Number,Direction,Contact Name
2026-04-13,14:30:00,00:03:45,,Inbound,John Smith
```

**Error:** "Telus CSV row 2 has empty Phone Number. All rows must have Date, Time, Duration, Phone Number, and Direction."

#### Encoding Issue

**File saved as Windows-1252 or Latin-1:**

**Error:** "Telus CSV file is not UTF-8 encoded. Please save the file as UTF-8 and try again."

### Error Handling Strategy

**On validation error:**

1. **Stop parsing immediately** — Do not attempt to salvage the file or skip bad rows
2. **Report the error message to the practitioner** — Explicit line number, column, value, and expected format
3. **Do NOT silently omit rows** — Silent failures hide data and corrupt the timeline
4. **Record "telus" in `sources_failed`** — Sort continues without Telus data; the day object reflects this
5. **Example message to practitioner:**

   ```
   Telus CSV error: Invalid date '2026-13-45' at row 2.
   Expected YYYY-MM-DD or MM/DD/YYYY.
   
   Please fix the date and try again, or skip Telus data for this sort.
   ```

### Graceful Degradation

If Telus CSV cannot be parsed:

- Record "telus" in `sources_failed` (not `sources_fetched`)
- Continue the sort with available sources (TimeCamp, Google Calendar)
- Present the day object with a note: "Note: Telus data not available — phone calls are not included in this sort."
- The practitioner can manually add Telus calls later if needed

### Logging

For debugging/audit purposes, log (but do not present unless requested):

- File path and size
- Encoding detected
- Columns found in header
- Row count (including skipped blank/comment rows)
- Validation errors (first error, then halt)
- Successful rows parsed
- Example: "Parsed Telus CSV: 47 rows, 45 valid entries, 2 blank rows skipped, encoding UTF-8"

---

## Integration Notes

This validation section should be referenced from the main SKILL.md at **Step 1c: Fetch Telus Connect Data** (line 168-172).

Add this line to Step 1c:

> See `reference/TelusConnect.md` § CSV Validation & Error Handling for validation rules, handling malformed input, and error reporting.

This ensures practitioners and implementers know where to find validation guidance when they encounter CSV issues.
