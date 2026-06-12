---
name: trial-lawyer-correspondence
description: Use when drafting any legal correspondence (emails or letters) to clients, opposing counsel, opposing parties, witnesses, experts, or the court. Trigger whenever the user asks to draft, write, or revise a legal email or letter — regardless of audience. Not for court filings, pleadings, or formal legal documents.
---

# Trial Lawyer Correspondence

Write legal correspondence with the tone, style, and professionalism of an experienced BC trial lawyer. This skill covers emails and letters to any audience — clients, opposing counsel, opposing parties, witnesses, experts, and the court. It does not cover court filings, pleadings, affidavits, or motions.

## Step 1: Identify the Audience

Before drafting anything, identify who the correspondence is going to. Each audience calls for a different tone, structure, and set of rules. If unclear, ask: "Who is this addressed to?"

| Audience | Reference File |
|---|---|
| Your client | `references/clients.md` |
| Opposing counsel (the other side's lawyer) | `references/opposing-counsel.md` |
| Opposing party directly (not through their lawyer) | `references/opposing-parties.md` |
| Independent (lay) witness | `references/independent-witnesses.md` |
| Expert witness (retained for opinion evidence) | `references/expert-witnesses.md` |
| Court registry or judicial staff (written) | `references/court-written.md` |
| Judge (in-court oral communication) | `references/court-oral.md` |

## Step 2: Read the Relevant Reference File

Once you have identified the audience, **read the corresponding reference file** before drafting. Each file contains tone guidance, structure, what to avoid, and examples specific to that audience. Do not rely on general principles alone — the nuances differ significantly between audiences.

## Step 3: Draft in Markdown First

**Never create a Word (.docx) document without explicit user approval.** Always produce the initial draft as a markdown letter in the chat window. Present it cleanly with all standard letter elements (date, RE: line, salutation, body, closing).

After presenting the markdown draft, invite the user to review it and suggest any changes.

## Step 4: Revise Iteratively in Markdown

When the user requests changes, produce an updated markdown draft that shows exactly what changed:

- **Additions**: wrap new text in `<u>underlined text</u>` HTML tags so it renders as underlined
- **Deletions**: wrap removed text in `~~strikethrough text~~` markdown so it renders as struck through

Continue this review cycle until the user indicates the letter is ready to finalize.

## Step 5: Offer Word Conversion

Once the draft is approved, offer to convert it to a Word document for printing:

> "The draft looks good. Would you like me to convert this to a Word document for printing?"

**Only proceed with Word document creation after the user explicitly approves.** When converting, use the template at:

```
.agents\skills\trial-lawyer-correspondence\templates\LT SP - Service Letter.dotx
```

Use the `/docx` skill to apply this template when producing the final `.docx` file.
Save the final Word document to `{workspace}\0. DRAFT\YYYY-MM-DD AI\`.

## Core Principles (All Audiences)

These apply regardless of who you are writing to:

- Be clear, precise, and unambiguous
- Use "RE:" lines to identify the matter; include the file number
- Date correspondence appropriately
- Never make promises or guarantees about case outcomes
- Never use aggressive or unprofessional language
- Do not draft court filings, motions, or pleadings using this skill

## Scope

This skill is for **correspondence only**. If the user requests:
- Court filings, motions, affidavits, or pleadings → handle separately; this skill does not apply
- Legal research or case analysis → provide without this skill's stylistic framework
- Contract drafting or other legal documents → handle separately
