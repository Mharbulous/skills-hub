# Common Telus CSV Error Scenarios & Recovery Paths

This document catalogs typical errors practitioners encounter when supplying Telus CSV files, their root causes, detection methods, error messages, and recovery steps.

## Error Categories

### 1. File System Errors

These occur before CSV parsing begins.

#### 1.1 File Not Found

**Scenario:** Practitioner specifies a path that doesn't exist.

```
Command: sort time 2026-04-13 with Telus CSV at ~/Downloads/telus-2026-04-13.csv
Error: Telus CSV file not found at ~/Downloads/telus-2026-04-13.csv. Check the file path and try again.
```

**Root causes:**
- Wrong path (e.g., `/home` instead of `~/`)
- File not downloaded yet
- File moved or deleted after download
- Typo in filename

**Detection:** `os.path.exists(path)` returns False

**Recovery:**
1. Ask practitioner to confirm file path
2. Check ~/Downloads (common location)
3. Check Desktop
4. Check Documents
5. Provide: "Run `ls -la {guessed_paths}` to verify the file exists"

---

#### 1.2 Permission Denied

**Scenario:** File exists but is not readable.

```
Error: Cannot read Telus CSV file at ~/Downloads/telus.csv. Check file permissions.
```

**Root causes:**
- File owned by another user
- File read permission not set (e.g., `chmod 000` accidentally)
- File on a network drive that requires authentication
- Antivirus software locking the file

**Detection:** `open(path, 'r')` raises `PermissionError`

**Recovery:**
1. On macOS/Linux: "Run `chmod 644 {path}` to make the file readable"
2. On Windows: "Right-click the file → Properties → Security tab → check you have Read permission"
3. If network drive: "Verify you're logged in to the network and the drive is mounted"
4. If antivirus: "Whitelist the file or temporarily disable antivirus scan"

---

### 2. Encoding Errors

These occur during file read (before CSV parse).

#### 2.1 Non-UTF-8 Encoding

**Scenario:** File saved in Windows-1252, Latin-1, or another encoding.

```
Error: Telus CSV file is not UTF-8 encoded. Please save the file as UTF-8 and try again.
```

**Root causes:**
- Exported from Microsoft Excel on Windows (defaults to system encoding, often Windows-1252)
- Exported from older versions of Telus portal
- User manually edited the file in a non-UTF-8 editor
- Special characters in Contact Names (e.g., accented letters) caused encoding conversion

**Detection:** Try `open(path, 'r', encoding='utf-8').read()` — if it raises `UnicodeDecodeError`, file is not UTF-8

**Alternative detection:** Look for null bytes (`\x00`) or invalid sequences in file head. Files with Windows-1252 characters like `\x92` (smart quote) will fail UTF-8 decode.

**Recovery:**
1. **On macOS/Linux (using `iconv`):**
   ```bash
   iconv -f WINDOWS-1252 -t UTF-8 ~/Downloads/telus.csv > ~/Downloads/telus-utf8.csv
   ```
2. **On Windows (using PowerShell):**
   ```powershell
   Get-Content ~/Downloads/telus.csv | Out-File -Encoding UTF8 ~/Downloads/telus-utf8.csv
   ```
3. **In Excel (all platforms):**
   - Open the file
   - File → Save As → Format: CSV UTF-8 (.csv)
4. **In Google Sheets:**
   - File → Download as CSV (UTF-8 is default)

**Additional context:** UTF-8 BOM (Byte Order Mark: `\xEF\xBB\xBF`) is acceptable — strip it during parse.

---

### 3. CSV Structure Errors

These occur during header/column validation.

#### 3.1 No Header Row

**Scenario:** File contains only data rows, no column names.

```
CSV content:
2026-04-13,14:30:00,00:03:45,+16045551234,Inbound,John Smith
2026-04-13,14:35:12,00:05:00,+16045551235,Outbound,

Error: Telus CSV has no header row. Expected columns: Date, Time, Duration, Phone Number, Direction, Contact Name
```

**Root causes:**
- User copied data rows without the header
- CSV was auto-generated without headers (e.g., via API dump)
- User accidentally deleted the header row when editing

**Detection:** Parse first row as header; if none of the expected columns (case-insensitive) match, assume no header and error

**Recovery:**
1. Provide template: "Add this header row as the first line: `Date,Time,Duration,Phone Number,Direction,Contact Name`"
2. Or: "Download the full CSV from Telus portal, which includes headers"

---

#### 3.2 Missing Required Column

**Scenario:** One or more required columns are absent.

```
CSV header:
Date,Time,Duration,Phone Number

Error: Telus CSV is missing required column(s): Direction, Contact Name. Found columns: Date, Time, Duration, Phone Number
```

**Root causes:**
- User copied only a subset of columns (e.g., from a filtered view in Telus portal)
- CSV was manually edited and a column was deleted
- Telus export options were misconfigured

**Detection:** Check for presence of Date, Time, Duration, Phone Number, Direction (case-insensitive, trim whitespace)

**Required columns:** Date, Time, Duration, Phone Number, Direction
**Optional columns:** Contact Name

**Recovery:**
1. If exporting from Telus portal: "Ensure you select all columns in the export dialog"
2. If manually edited: "Re-download the full CSV from Telus"
3. If Contact Name is missing: "This is optional — the sort will proceed; caller context will be less rich"
4. If Direction is missing: "Download the full export — Direction is required to classify calls as inbound or outbound"

---

#### 3.3 Unexpected Column Order

**Scenario:** Columns are present but in a different order than expected.

```
CSV header:
Phone Number,Date,Time,Duration,Direction,Contact Name

Status: No error — CSV parser should be order-agnostic
```

**Root causes:**
- Telus export changed column order
- User manually reordered columns
- CSV was processed by another tool that reordered headers

**Detection:** Parse header as dictionary/map (name → column index), not positional

**Recovery:** None needed — parser is order-agnostic

---

### 4. Field Validation Errors

These occur during row parsing.

#### 4.1 Malformed Date

**Scenario:** Date field does not match expected format.

```
Row 2: 2026-13-45,14:30:00,00:03:45,+16045551234,Inbound,John Smith
Error: Invalid date '2026-13-45' at row 2. Expected YYYY-MM-DD or MM/DD/YYYY
```

**Root causes:**
- Typo (e.g., month = 13)
- Impossible date (e.g., 02/30/2026)
- Date in an unexpected format (e.g., DD/MM/YYYY from a non-US region)
- Telus portal used non-standard date format
- Spreadsheet software auto-converted date to a different locale

**Detection:** Try parsing with expected formats; if all fail, catch exception and report

**Recovery:**
1. Check the actual date in the Telus portal and correct the typo
2. Verify your system locale is correct (especially if Telus portal is in a different region)
3. Re-export the CSV — ensure date format matches YYYY-MM-DD

---

#### 4.2 Malformed Time

**Scenario:** Time field does not match expected format.

```
Row 3: 2026-04-13,25:30:00,00:03:45,+16045551234,Inbound,John Smith
Error: Invalid time '25:30:00' at row 3. Expected HH:MM or HH:MM:SS in 24-hour format (e.g., 14:30 or 14:30:45)
```

**Root causes:**
- Hour out of range (e.g., 25, 99)
- Minute/second out of range (e.g., 14:75)
- 12-hour format with AM/PM suffix not recognized (e.g., "2:30 PM")
- Time in HH.MM.SS format (dots instead of colons)
- Spreadsheet software formatted time as "14:30:00.123" (with milliseconds)

**Detection:** Try parsing with `%H:%M` and `%H:%M:%S`; if both fail, report error

**Recovery:**
1. Correct the time in the CSV
2. Ensure 24-hour format (e.g., 14:30, not 2:30 PM)
3. If exporting from Telus: check export settings for time format
4. If spreadsheet: format the Time column as `[HH]:MM:SS` before exporting to CSV

---

#### 4.3 Malformed Duration

**Scenario:** Duration field cannot be parsed.

```
Row 4: 2026-04-13,14:30:00,malformed,+16045551234,Inbound,John Smith
Error: Invalid duration 'malformed' at row 4. Expected HH:MM:SS, MM:SS, or seconds as number (e.g., 00:03:45, 3:45, or 225)
```

**Root causes:**
- Non-numeric value
- Wrong format (e.g., "3h 45m" instead of "03:45")
- Spreadsheet formula that didn't evaluate
- Time format instead of duration (e.g., "14:30" instead of "00:03:45")

**Detection:** Try parsing as HH:MM:SS, MM:SS, or integer seconds; if all fail, report error

**Recovery:**
1. Correct the duration
2. If Telus shows duration in minutes (e.g., "3.75"), multiply by 60 to get seconds (225) or convert to MM:SS (03:45)
3. If exporting from Telus: some versions show duration in minutes; convert to seconds or HH:MM:SS format

---

#### 4.4 Negative or Zero Duration

**Scenario:** Duration parses but is invalid (≤ 0).

```
Row 5: 2026-04-13,14:30:00,-00:03:45,+16045551234,Inbound,John Smith
Error: Duration must be positive at row 5. Got '-00:03:45'
```

**Root causes:**
- Typo (negative sign instead of positive)
- Data corruption
- Telus exported a cancellation or error record

**Detection:** After parsing duration to seconds, check `seconds > 0`

**Recovery:**
1. Check the Telus portal for the actual call duration
2. Correct the sign (remove `-`)
3. If the call was cancelled or didn't complete, consider omitting this row entirely

---

#### 4.5 Duration Exceeds 8 Hours

**Scenario:** Duration parses but is unreasonably long.

```
Row 6: 2026-04-13,14:30:00,28800,+16045551234,Inbound,John Smith
Error: Duration exceeds 8 hours at row 6. Got '28800' — check for malformed data
```

**Root causes:**
- Time format error (e.g., duration in minutes but parsed as seconds)
- Spreadsheet formula returned a large number (e.g., seconds since epoch)
- Telus data corruption

**Detection:** After parsing to seconds, check `seconds ≤ 28800` (8 hours)

**Recovery:**
1. Check the Telus portal — did the call actually last 8+ hours? (Very unlikely for a call)
2. Verify the duration value — is it in the right unit? (minutes vs. seconds)
3. If clearly wrong, correct it or omit the row
4. If legitimate (e.g., very long conference call), you can override the validation by manually editing the CSV before re-sorting

---

#### 4.6 Invalid Phone Number

**Scenario:** Phone number cannot be normalized.

```
Row 7: 2026-04-13,14:30:00,00:03:45,555,Inbound,John Smith
Error: Invalid phone number '555' at row 7. Expected 10-digit North American number or E.164 format (+1XXXXXXXXXX)
```

**Root causes:**
- Number too short (e.g., extension instead of full number)
- Number too long (e.g., country code + number, non-North American)
- Non-numeric characters (e.g., "Call blocked")
- Placeholder/test number (e.g., 0000000000)

**Detection:** Normalize and check length; after stripping non-digits and leading `+`, expect exactly 10 digits (or 11 starting with 1)

**Recovery:**
1. Check the Telus portal — what is the full phone number?
2. Correct the number in the CSV
3. If it's an internal extension, provide the full business line number instead
4. If it's a non-North American number, prepend the country code (e.g., +447911... for UK)

**Special case — test/placeholder numbers:**
If the number is `0000000000`, `1111111111`, `5555555555`, etc., the parser will warn but accept it:
```
Warning: Phone number 5555555555 at row 7 looks internal/test — included as-is
```
The sort will proceed, but the call context may not be useful.

---

#### 4.7 Invalid Direction

**Scenario:** Direction field is not "Inbound" or "Outbound".

```
Row 8: 2026-04-13,14:30:00,00:03:45,+16045551234,Unknown,John Smith
Error: Invalid direction 'Unknown' at row 8. Expected Inbound or Outbound
```

**Root causes:**
- Typo or misspelling (e.g., "In" instead of "Inbound")
- Non-English value (e.g., "Entrante" or "Sortante")
- Data corruption

**Accepted formats (case-insensitive):**
- Inbound, In, ← (left arrow)
- Outbound, Out, → (right arrow)

**Detection:** Normalize to lowercase, compare against accepted values

**Recovery:**
1. Correct the direction in the CSV
2. If in a non-English language, translate to Inbound/Outbound or use a symbol
3. Re-export from Telus if the original data was corrupted

---

### 5. Logical Errors

These are valid CSV data but with logical inconsistencies.

#### 5.1 Duplicate Entries

**Scenario:** Same call appears twice in the CSV.

```
Row 5: 2026-04-13,14:30:00,00:03:45,+16045551234,Inbound,John Smith
Row 6: 2026-04-13,14:30:00,00:03:45,+16045551234,Inbound,John Smith
```

**Root causes:**
- Telus export included duplicates
- User manually copied a row
- CSV was merged from two sources without deduplication

**Detection:** After parsing, check for duplicate {date, time, duration, phone_number} tuples; flag and skip the duplicate

**Recovery:**
1. Check the Telus portal — is the call listed once or twice?
2. Remove the duplicate row from the CSV
3. If both rows are needed (different contexts), add a Contact Name or note to differentiate them
4. Re-sort with the cleaned CSV

**Current implementation:** Silently skip duplicates and log the count. No error raised, but practitioner is notified: "Parsed 47 rows; 2 duplicates skipped; 45 unique entries."

---

#### 5.2 Overlapping Calls

**Scenario:** Two calls with overlapping time windows (not duplicates).

```
Row 5: 2026-04-13,14:30:00,00:05:00,+16045551234,Inbound,John Smith
Row 6: 2026-04-13,14:32:00,00:03:00,+16045551235,Outbound,Jane Doe
```

**Interpretation:** Calls overlap from 14:32:00 to 14:35:00 (3 minutes). This is logically possible (e.g., call transfer, conference, parallel lines).

**Root causes:**
- Telus systems recorded overlapping activities on different lines
- User has multiple phone lines or extensions
- Data is legitimate (conference call, transfer)

**Detection:** After parsing, check for overlapping {date, time window} pairs; log but allow

**Recovery:**
1. This is usually okay — overlapping calls are legitimate
2. During merge, the time-sorting skill will reconcile overlapping activities from different sources (Telus, TimeCamp, GCal) using source hierarchy and context
3. Practitioner reviews the sorted day and can manually correct if needed

**Current implementation:** No error — overlapping entries are allowed and passed through as-is. The merge phase handles reconciliation.

---

### 6. Practical Recovery Workflows

#### Workflow A: Export Fresh from Telus Portal

1. Log in to Telus Business Connect
2. Navigate to Call History / Activity Log
3. Select date range (e.g., last 7 days, or a single day)
4. Click "Export" or "Download"
5. Choose format: CSV
6. Ensure encoding is UTF-8 (some Telus versions default to system encoding)
7. Save to ~/Downloads
8. Use the file path in the sort command: `sort time with Telus CSV at ~/Downloads/telus_calls.csv`

#### Workflow B: Fix Common Issues in Excel/Sheets

1. Open the CSV in Excel or Google Sheets
2. **Encoding issue?**
   - Excel: File → Save As → Format: "CSV UTF-8 (.csv)"
   - Sheets: File → Download → CSV
3. **Missing columns?**
   - Check Telus portal export options — ensure all columns are selected
4. **Malformed dates/times?**
   - Select the column → Format as Date (YYYY-MM-DD) or Time (HH:MM:SS)
   - Excel may auto-correct; re-verify the values
5. **Malformed durations?**
   - Check if duration is in minutes (Telus setting) — multiply by 60 if needed
   - Or convert to HH:MM:SS format
6. **Invalid phone numbers?**
   - Ensure full 10-digit number with area code
   - Excel may auto-format phone numbers — set column to Text to preserve leading zeros
7. Save as CSV
8. Re-sort with the corrected file

#### Workflow C: Skip Telus Data for This Sort

If the Telus CSV is corrupted or not worth fixing:

1. Don't provide a Telus path — omit `--telus` or `with Telus CSV at {path}`
2. The sort proceeds with TimeCamp + Google Calendar data only
3. Present the day with a note: "Note: Telus data not available — phone calls are not included in this sort."
4. Practitioner can manually note phone calls, or fix Telus data and re-sort later

---

### 7. Telemetry & Debugging

To help diagnose issues, capture this info before throwing an error:

```
Telus CSV parse attempt:
  Path: {path}
  File size: {bytes}
  Encoding detected: UTF-8 (or error)
  Header: {list columns}
  Row count: {total rows}
  Valid rows: {parsed count}
  Errors: {list}
  First error at row {N}: {message}
```

Log this (not shown to practitioner unless requested), so you can debug patterns in Telus exports across many sorts.

---

### 8. Summary Table

| Error | Detection | User Message | Recovery |
|-------|-----------|--------------|----------|
| File not found | `os.path.exists()` | "Telus CSV file not found at {path}. Check the file path and try again." | Verify path, check ~/Downloads |
| Permission denied | `open()` raises `PermissionError` | "Cannot read Telus CSV file at {path}. Check file permissions." | `chmod 644` or Windows Properties |
| Not UTF-8 | `open(utf-8)` raises `UnicodeDecodeError` | "Telus CSV file is not UTF-8 encoded. Please save the file as UTF-8 and try again." | Iconv, Excel Save As, or Google Sheets |
| No header | Header columns don't match | "Telus CSV has no header row. Expected columns: ..." | Add header row or re-export |
| Missing column | Column name not in header | "Telus CSV is missing required column(s): {list}. Found columns: {list}" | Re-export with all columns |
| Malformed date | `datetime.strptime()` fails | "Invalid date '{value}' at row {N}. Expected YYYY-MM-DD or MM/DD/YYYY" | Correct the date |
| Malformed time | `strptime()` fails | "Invalid time '{value}' at row {N}. Expected HH:MM or HH:MM:SS..." | Correct the time, use 24-hour |
| Malformed duration | Parse fails, or ≤ 0 | "Invalid duration '{value}' at row {N}. Expected HH:MM:SS, MM:SS, or seconds..." | Correct the duration |
| Duration > 8h | `seconds > 28800` | "Duration exceeds 8 hours at row {N}. Got '{value}' — check for malformed data" | Verify in Telus, correct or omit |
| Invalid phone | Normalization fails | "Invalid phone number '{value}' at row {N}. Expected 10-digit North American number or E.164..." | Correct to full 10-digit + area code |
| Invalid direction | Not in ["inbound", "outbound", ...] | "Invalid direction '{value}' at row {N}. Expected Inbound or Outbound" | Correct to Inbound or Outbound |
| Duplicate entry | Exact match on {date, time, duration, phone} | Silently skip; log count. No error. | Optional: remove from CSV |
| Overlapping calls | Overlapping time windows | No error; log as allowed. Merge phase reconciles. | Review in sorted day; correct if needed |

