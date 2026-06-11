# Scenario: Exception List File

## Setup
- Target file: `src/features/documents/components/table/DocumentTable.vue`

## Prompt
```
Review the file at path: src/features/documents/components/table/DocumentTable.vue
```

## Expected Behavior
1. The skill checks the file path against the exception list
2. Finds it on the exception list (virtual scrolling implementation)
3. Informs the user the file is exempt from streamlining
4. Explains WHY it's on the exception list
5. Does NOT proceed with decomposition or rebuild

## Key Assertions
- [ ] File is identified as exempt
- [ ] Reason is given (virtual scrolling / tight coupling)
- [ ] No decomposition plan is created
- [ ] No file modifications occur
