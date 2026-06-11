# RBC Online Banking

Site-specific knowledge for interacting with RBC Online Banking via browser automation.

## Table of Contents

1. [Authentication](#authentication)
2. [Account Documents](#account-documents)
3. [Known quirks](#known-quirks)

---

## Authentication {#authentication}

**URL:** `royalbank.com` or `rbcroyalbank.com`

Brahm handles login (credentials + possible verification questions). Wait for
confirmation before navigating.

---

## Account Documents {#account-documents}

**Accessing statements:** Navigate to Account Documents (not Account Activity).
The portal says "Up to 7 years of documents are available."

**Business Chequing account:** 06160-1003003, opened ~April 2023. No statements
exist before this date.

**Visa cards:**
- Avion Visa ending 4872 — billing cycle ~27th of month. This is the primary
  business Visa.
- Visa ending 2495 — discovered Sep 2025, status unclear (personal or second
  business card). Only one statement on file.

**Statement format:** RBC statements download as PDFs with reasonably descriptive
filenames.

---

## Known quirks {#known-quirks}

**"eStatements only go back ~2 years" was wrong.** As of 2026-03-23, the portal
confirmed 7 years of history are available. A previous session observed a ~2 year
limit, but this appears to have been a temporary issue or misunderstanding.

**One Visa card, not two.** Prior gap analyses assumed two separate RBC Visa cards
(one billing ~4th, one ~27th). In fact there is only ONE card (Avion 4872) — the
different dates were different statement cycle dates for the same card.
