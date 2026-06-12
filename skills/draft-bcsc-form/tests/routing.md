# Routing Validation -- Expected Outcomes (v2)

Run these checks before merging any registry or harness change. For each prompt, verify the classification pipeline selects the correct sequence and step IDs.

## Registry <-> File System Integrity

For each REGISTRY entry with a `workflow` field, the file **must** exist:

| Form | Workflow path | File exists? |
|------|--------------|-------------|
| Bill of Costs (form-62) | `forms/boc/workflow.md` | YES |

For each `forms/<name>/workflow.md` on disk, a REGISTRY entry **must** exist:

| Workflow file | REGISTRY entry? |
|--------------|---------------|
| `forms/boc/workflow.md` | YES -- `form-62` |

## Representative Prompt -> Expected Route (v2)

| Prompt | Expected sequence | Classification path |
|--------|------------------|---------------------|
| "Draft a notice of application for [matter]" | `full` (gen -> draft -> asm) | Tier 1: regular -> Tier 2: form-32 -> Tier 3: none -> full |
| "Draft an NOA -- use the case data for facts" | `full` | Tier 1: regular -> Tier 2: form-32 -> Tier 3: none -> full |
| "Just give me a blank NOA form for [matter]" | `generate` | Tier 1: regular -> Tier 2: form-32 -> Tier 3: generate |
| "Fill out the NOA header for [matter]" | `generate` | Tier 1: regular -> Tier 2: form-32 -> Tier 3: generate |
| "Draft the substance for the [matter] NOA" | `draft` | Tier 1: regular -> Tier 2: form-32 -> Tier 3: draft |
| "Draft Parts 2 and 3 for my NOA" | `draft` | Tier 1: regular -> Tier 2: form-32 -> Tier 3: draft |
| "Assemble the NOA with the substance I've drafted" | `assemble` | Tier 1: regular -> Tier 2: form-32 -> Tier 3: assemble |
| "Merge my substance into the NOA form" | `assemble` | Tier 1: regular -> Tier 2: form-32 -> Tier 3: assemble |
| "Draft a bill of costs for [matter]" | `boc` | Tier 1: regular -> Tier 2: form-62 (workflow) -> boc |
| "Form 62 costs assessment" | `boc` | Tier 1: regular -> Tier 2: form-62 (workflow) -> boc |
| "Scale B tariff items for my matter" | `boc` | Tier 1: regular -> Tier 2: form-62 (workflow) -> boc |
| "Draft a petition for [matter]" | `full` | Tier 1: regular -> Tier 2: form-66 -> Tier 3: none -> full |
| "Generate a blank petition for [matter]" | `generate` | Tier 1: regular -> Tier 2: form-66 -> Tier 3: generate |
| "Draft an offer to settle costs" | `generate` | Tier 1: regular -> Tier 2: form-123 (generate_only) -> generate |
| "Draft a notice of civil claim for [matter]" | `full` | Tier 1: regular -> Tier 2: form-1 -> Tier 3: none -> full |
| "Draft an NOCC for [matter]" | `full` | Tier 1: regular -> Tier 2: form-1 -> Tier 3: none -> full |
| "Draft a response to counterclaim for [matter]" | `full` | Tier 1: regular -> Tier 2: form-4 -> Tier 3: none -> full |
| "Amend the NOCC for [matter]" | `amend` | Tier 1: amend -> amend (short-circuit) |
| "I need to amend a pleading" | `amend` | Tier 1: amend -> amend (short-circuit) |
| "Rule 6-1 amendment to the statement of defence" | `amend` | Tier 1: amend -> amend (short-circuit) |
| "Amend the response to civil claim" | `amend` | Tier 1: amend -> amend (short-circuit) |
| "Convert this LEAP template to bracket format" | `new-template` | Tier 1: new-template -> new-template (short-circuit) |
| "Draft an affidavit for [matter]" | `generate` | Tier 1: regular -> Tier 2: affidavit (generate_only) -> generate |
| "Prepare a blank affidavit for [deponent]" | `generate` | Tier 1: regular -> Tier 2: affidavit (generate_only) -> generate |
| "Fill out the affidavit header for [matter]" | `generate` | Tier 1: regular -> Tier 2: affidavit (generate_only) -> generate |
| "I have a new form export from LEAP" | `new-template` | Tier 1: new-template -> new-template (short-circuit) |

## Sequence -> Step ID Verification

Each sequence key in SEQUENCES must resolve to existing step modules:

| Sequence | Step IDs | All modules exist? |
|----------|----------|-------------------|
| `generate` | gen.matter_profile, gen.scalars, gen.fill, shared.verify | YES |
| `draft` | draft.part1, draft.part2, draft.part3, draft.part4 | YES |
| `assemble` | asm.locate_inputs, asm.assemble_body, asm.fill, shared.verify | YES |
| `full` | (generate + draft + assemble steps) | YES |
| `amend` | amend.identify, amend.propose, amend.spec, amend.run | YES |
| `new-template` | nt.inspect_tmpl, nt.configure, nt.convert, nt.validate | YES |
| `boc` | boc.setup, boc.mcq, boc.map_items, boc.units, boc.disbursements, boc.summary, boc.fill, shared.verify | YES |

## Template Asset Verification

Each REGISTRY entry's `template` field must point to an existing file:

| Template | Exists? |
|----------|---------|
| `templates/032-noa.dotx` | YES |
| `templates/062-boc.dotx` | YES |
| `templates/066-petition.dotx` | YES |
| `templates/123-otsc.dotx` | YES |
| `templates/001-nocc.dotx` | YES |
| `templates/004-rtc.dotx` | YES |
| `templates/affidavit.dotx` | YES |

## Trigger Eval Target

On description changes, run representative prompts against the skill matcher. Target: >=90% routed to `/draft-bcsc-form`. Key risk phrases that must trigger this skill:
- "bill of costs"
- "Form 62"
- "taxing of costs" / "assessment of costs"
- "tariff items"
- "scale B costs"
- "notice of application"
- "petition to the court"
- "offer to settle costs"
- "amend a pleading"
- "amend the NOCC"
- "Rule 6-1 amendment"
- "amended pleading"
- "blank form"
- "affidavit" / "draft an affidavit"
- "draft substance"
- "assemble form"
