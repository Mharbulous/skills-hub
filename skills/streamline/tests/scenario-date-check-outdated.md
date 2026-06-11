# Scenario: Folder-Structure Date Check (Outdated)

## Setup
- No target file specified (argument is empty or absent)
- The latest `docs/Miscellaneous/YYYY-MM-DD-Folder-Structure.md` has a date in the past

## Prompt
```
Review the file at path: ``
```
(No file argument — triggers Folder-Structure date check)

## Expected Behavior
1. The skill detects no target file was specified
2. Finds the latest Folder-Structure.md file
3. Extracts the date from the filename
4. Compares it to today's date — finds it is in the past
5. Reviews all files listed in the Folder-Structure.md
6. Counts actual lines of code (excluding comments) for each file
7. Updates all line counts in the file
8. Removes any excessive documentation
9. Renames the file to today's date
10. Reports "Folder-Structure.md was outdated and has been updated"
11. STOPS — does NOT proceed with streamlining

## Key Assertions
- [ ] Date check is performed
- [ ] Outdated date is detected
- [ ] Line counts are updated for listed files
- [ ] File is renamed to today's date
- [ ] Session stops after update (no file selection occurs)
- [ ] Message instructs user to start new chat
