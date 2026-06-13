# Scenario: Specific File ≤300 Lines

## Setup
- Target file: a source file with ≤300 lines of code

## Prompt
```
Review the file at path: src/router/index.js
```

## Expected Behavior
1. Skips the Folder-Structure date check (specific file provided)
2. Checks file against exception list — not on it
3. Reads the file and counts lines
4. Determines it has 300 lines or fewer
5. Rebuilds the file from scratch in a more elegant way
6. Compares rebuilt LOC to original LOC
7. If fewer lines: issues a PR / presents result
8. If equal or more lines: reports unable to streamline, offers to lengthen

## Key Assertions
- [ ] Date check is skipped
- [ ] File is under 300 lines
- [ ] Rebuild is attempted (not decomposition)
- [ ] LOC comparison is made between original and rebuilt
- [ ] Result depends on whether lines were reduced or not
