---
name: draft-small-claims-form
description: Draft a defendant's Reply to a Notice of Claim in BC Small Claims Court and fill the official court forms. Use whenever the user asks to respond to a small claims notice of claim, draft a reply form, prepare a small claims defence, fill out Form 2 (Reply) or Form 38 (Address for Service), or respond to a small claims action. Also trigger when the user references a Notice of Claim and asks to prepare the defendant's response or file a reply.
---




### Additional forms (`assets/`)
A library of BC Small Claims and Provincial Small Claims forms is bundled in `assets/small-claims/`. **Do not load these into context proactively.** Read a form from this folder only when the user specifically asks to fill it.

### Complete Forms Index

See [`assets/small-claims/AGENTS.md`](assets/small-claims/AGENTS.md) for the full index of bundled BC Small Claims forms.

## Solicitor Details (Hardcoded)

Always use these details for solicitor/lawyer fields on all forms:

| Field | Value |
|-------|-------|
| Name | Brahm Dorst |
| Firm | Logica Law |
| Street | 179 Davie Street |
| Suite | Suite 215 |
| City / Province / Postal | Vancouver, BC  V6Z 2Y1 |
| Email | brahm@logicalaw.ca |

---

## Workflow

### Step 1 — Read the Notice of Claim

The PDF is often a scanned image. Extract text with OCR:

```bash
# Convert to images
pdftoppm -r 200 "<input.pdf>" /tmp/noc_page

# OCR each page
for f in /tmp/noc_page*.ppm; do
  echo "=== $f ===" && tesseract "$f" stdout 2>/dev/null
done
```

Extract from the OCR output:
- Court file number and registry location
- Claimant name(s) and address
- Defendant name(s)
- Each factual allegation under "What Happened"
- Relief sought

### Step 2 — Clarify the Defendant's Position

Use `AskUserQuestion` to confirm the defendant's position on each material allegation. Base questions on what was actually alleged — not generic prompts.

Structure: one question per major disputed fact, with options such as "Deny entirely," "Admit in part," or a specific factual alternative. Always include a question on whether the defendant wants to include a counterclaim.

If there are more than 4 material disputes, use two rounds of AskUserQuestion.

### Step 3 — Draft the Word Reply

Read the `docx` skill's SKILL.md, then produce a Word document with:

**Header block:**
- Court: "PROVINCIAL COURT OF BRITISH COLUMBIA — SMALL CLAIMS DIVISION"
- Registry location and court file number
- Parties
- Title: "REPLY OF THE DEFENDANT"

**Body:**
- **Part 1 — Disagreement:** Defendant disagrees with the claim in its entirety (or in par