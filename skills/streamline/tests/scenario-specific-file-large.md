# Scenario: Specific File >300 Lines

## Setup
- Target file: `src/views/Upload.vue` (513 lines per Folder-Structure)

## Prompt
```
Review the file at path: src/views/Upload.vue
```

## Expected Behavior
1. Skips the Folder-Structure date check (specific file provided)
2. Checks file against exception list — not on it
3. Reads the file and counts lines
4. Determines it exceeds 300 lines
5. Creates a decomposition plan (smaller files ≤200 lines each)
6. Presents plan for user approval
7. Waits for user response before executing

## Key Assertions
- [ ] Date check is skipped
- [ ] Exception list is checked
- [ ] File is read and line count confirmed >300
- [ ] Decomposition plan is created with logical groupings
- [ ] Plan is presented to user before execution
- [ ] No files are modified until approval is given
