---
name: draft-small-claims-form
description: Draft a defendant's Reply to a Notice of Claim in BC Small Claims Court and fill the official court forms. Use whenever the user asks to respond to a small claims notice of claim, draft a reply form, prepare a small claims defence, fill out Form 2 (Reply) or Form 38 (Address for Service), or respond to a small claims action. Also trigger when the user references a Notice of Claim and asks to prepare the defendant's response or file a reply.
---

# BC Small Claims Reply

Produces three deliverables for a defendant responding to a BC Small Claims Notice of Claim:
1. A Word document draft of the Reply (for review and signature)
2. Form 2 (Reply) — filled official PDF, ready to file
3. Form 38 (Address for Service) — filled official PDF, ready to file

All lawyer-facing outputs save to `{workspace}\0. DRAFT\YYYY-MM-DD AI\`.

## Bundled Forms

### Active assets (`assets/`)
Forms used directly in the standard Reply workflow — always available:
- `assets/scl002.pdf` — Form 2: Reply
- `assets/scl057.pdf` — Form 38: Address for Service

### Additional forms (`assets/`)
A library of BC Small Claims and Provincial Small Claims forms is bundled in `assets/`. **Do not load these into context proactively.** Read a form from this folder only when the user specifically asks to fill it.

### Complete Forms Index

Use this index to find the correct file. `assets/` = always bundled; `assets/` = load on demand; `—` = not bundled (send user to download link).

| Form name | Form # | File |
|-----------|--------|------|
| Acceptance of offer | SCR Form 19, SCL805 | `assets/scl805.pdf` |
| Acknowledgment of payment | SCL800 | `assets/scl800.pdf` |
| Additional page | SCL029 | — |
| Address for service | SCR Form 38, SCL057 | `assets/scl057.pdf` |
| Affidavit | SCL848 | `assets/scl848.pdf` |
| Affidavit in support of garnishing order after judgment | COEA Form B, PSC014 | `assets/psc014.pdf` |
| Affidavit in support of garnishing order before action | COEA Form A, SCL806 | `assets/scl806.pdf` |
| Affidavit in support of garnishing order/judgment | COEA Form C, PSC003 | `assets/psc003.pdf` |
| Affidavit of non-compliance | SCL808 | `assets/scl808.pdf` |
| Affidavit of service | SCL004c | `assets/scl004c.pdf` |
| Affidavit to cancel a dismissal or default order | SCL020 | `assets/scl020.pdf` |
| Agreement | SCL028 | `assets/scl028.pdf` |
| Application (Local Government Act) | ADM865 | `assets/adm865.pdf` |
| Application for default order | SCR Form 5, SCL005 | `assets/scl005.pdf` |
| Application for exemption | SCR Form 36, SCL055 | `assets/scl055.pdf` |
| Application record/order | SCL026 | `assets/scl026.pdf` |
| Application registration/renewal of a judgment | SCL815 | `assets/scl815.pdf` |
| Application to a judge — Filing Assistant | SCR Form 17, SCL017 | `assets/scl017.pdf` |
| Application to the registrar — Filing Assistant | SCR Form 16, SCL016 | `assets/scl016.pdf` |
| Certificate | SCL804 | `assets/scl804.pdf` |
| Certificate of amounts owing | SCL840 | `assets/scl840.pdf` |
| Certificate of compliance | SCR Form 37, SCL056 | `assets/scl056.pdf` |
| Certificate of readiness | SCR Form 7, SCL007 | `assets/scl007.pdf` |
| Certificate of service | SCR Form 4, SCL004f | `assets/scl004f.pdf` |
| Consent order | SCL021 | `assets/scl021.pdf` |
| Consent to act as guardian ad litem | SCL807 | `assets/scl807.pdf` |
| Consent to adjourn settlement conference | SCL829 | `assets/scl829.pdf` |
| Consent to adjourn trial conference | SCL828 | — |
| Electronic filing statement | SCR Form 28, SCL830 | `assets/scl830.pdf` |
| Fax cover sheet | SCR Form 20, ADM833smcl | — |
| Fee declaration | SCR Form 30, SCL833 | `assets/scl833.pdf` |
| Garnishing order (absolute) | COEA Form E, SCL839 | `assets/scl839.pdf` |
| Garnishing order (after judgment) | COEA Form D, PSC013 | `assets/psc013.pdf` |
| Garnishing order (before judgment) | COEA Form F, PSC002 | `assets/psc002.pdf` |
| Garnishment application (Federal) | GAR form | — |
| Mediation agreement | SCR Form 25, SCL044 | `assets/scl044.pdf` |
| Mediation compensation order | SCR Form 26, SCL827 | `assets/scl827.pdf` |
| Notice of claim — Filing Assistant | SCR Form 1, SCL001 | `assets/scl001.pdf` |
| Notice of civil resolution tribunal claim | SCR Form 34, SCL053 | `assets/scl053.pdf` |
| Notice of payment hearing | SCR Form 13, SCL013 | `assets/scl013.pdf` |
| Notice of payment out | PSC024 | `assets/psc024.pdf` |
| Notice of withdrawal | SCL019 | `assets/scl019.pdf` |
| Notice to mediate ($10,000–$35,000) | SCR Form 29, SCL832 | `assets/scl832.pdf` |
| Notice to the claimant | SCL025 | `assets/scl025.pdf` |
| Offer to settle | SCR Form 18, SCL803 | `assets/scl803.pdf` |
| Order | SCL809 | `assets/scl809.pdf` |
| Order for seizure and sale | SCR Form 11, SCL011 | `assets/scl011.pdf` |
| Payment order | SCR Form 10, SCL010 | `assets/scl010.pdf` |
| Personal information for document service by sheriff | SHS852 | `assets/shs852.pdf` |
| Reply — Filing Assistant | SCR Form 2, SCL002 | `assets/scl002.pdf` |
| Reply to third party notice | Form 3.1, SCL801 | `assets/scl801.pdf` |
| Request for judgment or for dismissal | SCR Form 23, SCL042 | `assets/scl042.pdf` |
| Request for payment out | SCL841 | `assets/scl841.pdf` |
| Result of mediation | SCR Form 24, SCL043 | `assets/scl043.pdf` |
| Statement of finances | Form 40, SCL024 | `assets/scl024.pdf` |
| Summary trial for financial debt cover sheet | SCL838 | `assets/scl838.pdf` |
| Summons to a default hearing | SCR Form 14, SCL014 | `assets/scl014.pdf` |
| Summons to a payment hearing | SCR Form 12, SCL012 | `assets/scl012.pdf` |
| Summons to witness | SCR Form 8, SCL008 | `assets/scl008.pdf` |
| Supporting materials cover sheet | Form 39, SCL849 | `assets/scl849.pdf` |
| Third party notice — Filing Assistant | SCR Form 3, SCL003 | — |
| Trial statement | SCR Form 33, SCL045 | `assets/scl045.pdf` |
| Verification of default | SCR Form 31, SCL834 | `assets/scl834.pdf` |

If the user asks to fill a form marked `—`, respond:
> "That form isn't bundled with this skill. You can download it here: https://www2.gov.bc.ca/gov/content/justice/courthouse-services/documents-forms-records/court-forms/small-claims-forms — please upload it and I'll fill it in."

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
