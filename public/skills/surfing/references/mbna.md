# MBNA Mastercard Portal

Site-specific knowledge for interacting with MBNA's online portal via browser automation.

## Table of Contents

1. [Authentication](#authentication)
2. [Portal structure](#portal-structure)
3. [Downloading statements](#downloading-statements)

---

## Authentication {#authentication}

**URL:** `mbna.ca` — NOT TD Online Banking (TD owns MBNA but accounts are separate)

Login is under Laura Dorst's name but shows both cards. Brahm handles authentication.

---

## Portal structure {#portal-structure}

**Two cards visible on the portal:**
- **Card ending 4762** = Brahm's card (MBNA Platinum Plus® Mastercard®)
  - Two underlying account numbers: old card 549198XXXXXX3983 (Jan 2019–Jul 2021)
    replaced by 523465XXXXXX2413 (Aug 2021–present)
- **Card ending 4769** = Laura's card (MBNA True Line® Mastercard®)
  - Account 523441XXXXXX4769, cardholder LAURA M DORST
  - Opened early 2023 (first statement Feb 2023)

**Statement history:** Portal has ~7 years of history back to Jan 2019.

---

## Downloading statements {#downloading-statements}

**Statement download method:** Navigate to statement history, select the statement
period, and download as PDF. Statements download with generic filenames like
`statementHistoryOpenSave.PDF` or `statementHistoryOpenSave (1).PDF` — they need
to be renamed after download.

**Distinguishing cards in downloaded PDFs:** Use PDF text extraction to check the
account number and cardholder name in the statement. Brahm's card shows
"549198XXXXXX3983" or "523465XXXXXX2413"; Laura's shows "523441XXXXXX4769" and
"LAURA M DORST".

**Naming convention for filing:**
- Brahm's: `YYYY-MM-01 | STMT | MBNA Mastercard XXXX | Month Year.pdf`
- Laura's: `YYYY-MM-01 | STMT | MBNA Mastercard DorstL 4769 | Month Year.pdf`
