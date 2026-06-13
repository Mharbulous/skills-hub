# Verification Patterns

## AskUserQuestion Templates

Use `AskUserQuestion` for every interaction the user must perform. Always provide 2-4 concrete options. Describe UI elements by visual appearance and position, not code names.

### Navigation Request

```
question: "Can you switch the app to [View Name]? ([Menu] → [Item])"
options:
  - label: "Done"
    description: "I've switched to [View Name]"
  - label: "Need help"
    description: "I need guidance on how to navigate there"
```

### Hover / Tooltip Check

```
question: "Can you hover over the [element description] ([position in window]) to check if a tooltip appears?"
options:
  - label: "Tooltip visible"
    description: "I see a tooltip saying [expected text or category]"
  - label: "No tooltip"
    description: "No tooltip appeared on hover"
```

### Click Action

```
question: "Please click [button/element] and tell me what happens."
options:
  - label: "Expected result"
    description: "[specific expected outcome, e.g., 'Block disappeared from list']"
  - label: "Nothing happened"
    description: "Clicked but no visible change"
  - label: "Error occurred"
    description: "Something went wrong"
```

### State Transition Verification

```
question: "After [action], switch to [View] and check: does [element] appear with [expected state]?"
options:
  - label: "Yes, correct state"
    description: "[specific expected appearance]"
  - label: "Not visible"
    description: "I don't see the expected element"
  - label: "Visible but wrong state"
    description: "It's there but [missing expected attribute]"
```

### Process Confirmation

```
question: "I need to [destructive/notable action]. OK to proceed?"
options:
  - label: "Yes, go ahead"
    description: "[what will happen]"
  - label: "No, I'll handle it"
    description: "I'll do this myself"
```

## Negative Response Protocol

When the user reports something missing, wrong, or not working — **capture a screenshot before treating it as a failure.** Users can give false negatives: they may look in the wrong spot, misidentify an element, or miss something small.

1. Capture the current window with /glimpse
2. Examine the screenshot yourself against the spec
3. If the element IS present and correct: tell the user exactly what you see and where, then re-ask
4. If the element is genuinely missing/wrong: proceed to issue handling

This applies to every negative AskUserQuestion response — hover tests ("No tooltip"), click tests ("Nothing happened"), navigation checks ("Not visible"). Trust your eyes over verbal reports when they conflict.

## Screenshot Interpretation

When reading a /glimpse screenshot, check for:

1. **Layout** — Are panels, rows, and columns in the right positions?
2. **Content** — Do labels, values, and text match the spec?
3. **State indicators** — Checkmarks, badges, pills, disabled states
4. **Buttons/controls** — Present, enabled/disabled, correct labels
5. **Empty states** — Does the empty state message appear when there's no data?
6. **Banners/alerts** — Status bars, error banners, provenance lines

Report observations in a structured format:

```
**[View Name] panel verification:**
- Element A: [observed state] ✅ or ❌
- Element B: [observed state] ✅ or ❌
- Element C: needs user interaction (hover/click) to verify
```

## Round-Trip Testing Pattern

A round-trip test exercises: Action → Verify arrival → Reverse → Verify return.

**Example: Approve/Unapprove**

| Step | Who | Action | Verify |
|------|-----|--------|--------|
| 1 | User | Click "Approve" on block in Pending Review | Block disappears from list |
| 2 | User | Switch to Approved view | — |
| 3 | Claude | Capture screenshot | Block appears with ✓✓ and Unapprove button |
| 4 | User | Click "Unapprove" on that block | Block disappears from Approved |
| 5 | User | Switch back to Pending Review | — |
| 6 | Claude | Capture screenshot | Block reappears in Pending Review |

Each step captures evidence (screenshot or user confirmation). If any step fails, stop the round-trip and investigate.

## Data Seeding Decision Tree

```
App shows empty view where spec expects data?
├── Spec mentions seeding → Seed data
├── Navigate to a date/context with existing data → Try that first
└── No existing data anywhere → Seed data

Seeding approach:
├── Database accessible from CLI? → Direct SQL
├── Database encrypted? → Use app's own infrastructure (connection factory)
├── Web app with API? → Direct API calls
└── No easy path? → Ask user to create data manually
```

After seeding, always restart the app and verify data appears before proceeding.
