---
name: prompt-restructurer
description: >
  Restructure Firestore prompt data so each component maps to Gemini's native API parameters.
  Moves schema definitions from systemInstruction/contents into fieldPrompts.responseSchema,
  cleans system instructions to contain only stable behavioral guidance, and ensures contents
  holds only per-request variable data. Use when (1) restructuring a specific stage/session prompt,
  (2) auditing all prompts for Gemini best-practice compliance, (3) user says "restructure prompts",
  "fix prompt structure", or "optimize for Gemini native schema".
disable-model-invocation: true
---

# Prompt Restructurer

Restructure Firestore prompt variant documents so each field maps cleanly to Gemini's native API parameters.

## Target Mapping

| Firestore Field | Gemini API Parameter | Content |
|---|---|---|
| `turns[system].content` | `systemInstruction` | Stable behavioral guidance only: role, domain knowledge, field instructions, guardrails. NO schemas, NO "return JSON" directives. |
| `turns[user].content` | `contents` | Per-request task directive + template variables. NO schema info. Negative constraints LAST. |
| `fieldPrompts.responseSchema` | `responseSchema` | Proper Gemini JSON Schema: `type: "OBJECT"/"STRING"/"ARRAY"/"BOOLEAN"/"INTEGER"`, `nullable: true`, `required: [...]`, `items: {...}` |

## Firestore Location

Database: `db-global`, collection: `prompts/{stageId}/sessions/{sessionId}/variants/{variantId}`

Variant document structure:
```json
{
  "name": "Original",
  "turns": [
    { "role": "system", "content": "..." },
    { "role": "user", "content": "..." }
  ],
  "fieldPrompts": {
    "dataBindings": [],
    "responseSchema": {}
  }
}
```

## Variant Metadata

Variant documents may contain additional fields beyond the core structure above:

| Field | Purpose |
|---|---|
| `jurisdiction` | Regional variant selector (e.g., `"BC"`) |
| `variant` | Variant label used for A/B testing or overrides |
| `sessionInstruction` | **Legacy** -- `loadPrompt.js` extracts from the first turn with `role: "system"`, not this field. Harmless; leave in place. |
| `createdAt` / `updatedAt` | Timestamps managed by write operations |

The write script uses Firestore `update()`, so unlisted fields are preserved automatically. Do not strip or recreate the full document -- only update `turns` and `fieldPrompts`.

## Procedure

### Step 1 -- Pre-check (triage)

Before reading or classifying, determine if the variant needs restructuring at all.

**Skip entirely if any of these apply:**

1. **Field-assembly session** -- `turns: null`. Nothing to restructure. Log as "skipped: field-assembly (turns is null)."

2. **Continuation session** -- Only 1 turn with `role: "user"` and no system turn. These are follow-up user turns in a multi-turn API call; the parent session provides the system instruction. Skip unless the user turn embeds schema definitions. Log as "skipped: continuation session."

   Known continuation sessions and their parents:
   - `categorizeCourt/court-record` -- parent: `categorizeCourt/law`
   - `categorizeParty/correspondence` -- parent: `categorizeParty/solicitor-client`
   - `categorizeParty/work-product` -- parent: `categorizeParty/solicitor-client`

3. **Already compliant** -- `fieldPrompts.responseSchema` is already populated AND the system instruction contains no embedded schema examples or redundant JSON-enforcement directives. Log as "skipped: already compliant."

If none of the above apply, proceed to Step 2.

### Step 2 -- Read current data

Run from the `functions/` directory:
```bash
node ~/.claude/skills/prompt-restructurer/scripts/firestore-prompt-ops.js read <stageId> <sessionId>
```

Record the `variantId` from the output -- you will need it for writing in Step 6.

Also read the seed data in `functions/scripts/promptStagesV2.js` to understand the original intent. Use seed data to confirm the Firestore variant is complete (nothing dropped in migration). Seed is reference-only -- Firestore is the source of truth.

### Step 3 -- Classify each section

**Opening checkpoint:** If `fieldPrompts.responseSchema` is already populated, skip "Schema definition" classification -- focus on Behavioral, Redundant, and Per-request only.

For every paragraph/block in the system instruction, classify:

| Classification | Action |
|---|---|
| **Schema definition** -- JSON examples, "Return this exact structure: {...}", field type specs | Extract to `fieldPrompts.responseSchema` as Gemini JSON Schema |
| **Behavioral guidance** -- role definition, domain knowledge, field-specific instructions, guardrails | Keep in system instruction |
| **Redundant with native responseSchema** -- "Return ONLY valid JSON", "no markdown", "no code fences" | Remove -- but ONLY if responseSchema will be populated after restructuring. If no schema applies, array/type directives are Behavioral (Keep). |
| **Per-request variable data** -- template vars like `{userName}`, matter context | Must be in contents (user turn), not system instruction |

**User turn guidance:** Inspect the user turn separately. A static task directive with no schema and no template variables is already correct -- do not reclassify it.

**No system instruction:** If the variant has no system turn (e.g., continuation sessions), classification applies only to the user turn content. If the user turn is a clean task directive, there is nothing to classify.

### Step 4 -- Restructure

Apply the best practices from `references/gemini-best-practices.md`:

**System instruction** (stable, cacheable):
- Role definition
- Domain knowledge and conventions
- Behavioral constraints and guardrails
- Field-specific extraction rules (what each field means, how to populate it)

**Contents / user turn** (variable per-call):
1. Context data (matterContext, firmSection) -- via dataBindings
2. Task directive ("Analyze the attached document...")
3. Source material references
4. Negative constraints LAST ("Do NOT...", "NEVER...")

**responseSchema** (Gemini JSON Schema):
- Convert JSON examples to proper schema with `type`, `nullable`, `required`, `items`
- Use UPPERCASE type names: `OBJECT`, `STRING`, `ARRAY`, `BOOLEAN`, `INTEGER`
- Every nullable field: `{ type: "STRING", nullable: true }`
- Arrays: `{ type: "ARRAY", items: { type: "STRING" } }`

**fieldPrompts handling:**
- If `fieldPrompts` is `null` and no schema to extract: leave as `null`. Do NOT create `{ responseSchema: null }`.
- If `fieldPrompts` has `dataBindings`: preserve the entire array unchanged (same length, order, values).
- If `fieldPrompts` has `responseSchema` already populated: verify format (UPPERCASE types, nullable, required) but do not recreate from scratch.

**Preserve unchanged:**
- `fieldPrompts.dataBindings`
- `name` field
- Sessions with `turns: null` (field-assembly type -- skip, nothing to restructure)

**No changes needed:** If classification reveals no changes are required, the variant is already compliant. Proceed to Step 5 (Present) with a "no changes" finding. Do NOT proceed to Step 6 (Write).

### Step 5 -- Present for review

Show a classification table:

```
| Section | Classification | Action |
|---|---|---|
| "You are a legal..." | Behavioral | Keep in systemInstruction |
| "Return this exact JSON..." | Schema definition | Extract to responseSchema |
| "Return ONLY valid JSON" | Redundant | Remove |
```

Then show the proposed new values for `turns` and `fieldPrompts`.

**If no restructuring needed:** Present the following instead:

> Variant `<stageId>/<sessionId>/<variantId>` is already compliant with Gemini best practices. No changes required.

Show the classification table for audit trail. Do NOT proceed to Step 6.

### Step 6 -- Write to Firestore

Save the restructured data to a temp JSON file and write:
```bash
node ~/.claude/skills/prompt-restructurer/scripts/firestore-prompt-ops.js write <stageId> <sessionId> <variantId> /tmp/restructured.json
```

Use the `variantId` from Step 2. This may be `r1`, `r6`, or any revision -- not necessarily `v1`.

### Step 7 -- Verify

**Short-circuit:** If the session was skipped in Step 1 (continuation, field-assembly, or already compliant), mark as complete without **running** the checklist below.

Read back and confirm:
- System instruction contains NO JSON schema examples
- User turn contains NO schema information
- `fieldPrompts.responseSchema` is a valid Gemini JSON Schema (or null if no schema applies)
- `fieldPrompts.dataBindings` identical to original (same length, order, values)
- Field count matches original intent

## Special Cases

- **No schema to extract** (fingerprint, llm-judging, etc.): Clean system/contents split only. Leave `fieldPrompts` as-is (null stays null).
- **Continuation sessions**: Skip entirely (covered in Step 1 pre-check).
- **Dynamic schemas** (`matter-extract/extract-fields`): `responseSchema: null` because schema is built at runtime by `buildExtractionSchema()`. Clean system/contents split only.
- **Google Search grounding** (`buildFirmProfile` sessions): `systemInstruction` IS compatible with `googleSearch`; `responseMimeType: 'application/json'` is NOT. Structure correctly regardless.

## Inventory

Run `node ~/.claude/skills/prompt-restructurer/scripts/firestore-prompt-ops.js list` for current inventory.

## Reference

For detailed rationale on systemInstruction vs contents placement, caching economics, and attention weight research, read `references/gemini-best-practices.md`.
