# Proceedings Profile -- Ensure and Retrieve Complete Proceedings Metadata

This operation owns the contract: return complete proceedings metadata for a matter. Callers do not choose a mode. The operation inspects database state and selects the correct path.

## Step 0: Resolve Matter Pointer

Use the shared pointer-resolution snippet from `SKILL.md`.

## Step 1: Query Existing Proceedings

Copy `.sqlite` files from native `case_data_dir` to a fresh temp directory, attach databases, then run:

```sql
SELECT
    p.proceeding_id,
    p.court,
    p.registry,
    p.file_number,
    p.style_of_cause,
    p.courthouse_address,
    p.trial_date,
    p.status,
    pp.role,
    pa.party_id,
    pa.name AS party_name,
    pa.party_type,
    pa.lawyer_name,
    pa.lawyer_firm
FROM main.proceedings p
LEFT JOIN main.proceeding_parties pp ON pp.proceeding_id = p.proceeding_id
LEFT JOIN main.parties pa ON pa.party_id = pp.party_id
ORDER BY p.proceeding_id, pp.role, pa.name;
```

If at least one proceeding exists and required party data is complete, skip to Step 5.

## Step 2: Select Mode

Select one of three modes from database state and matter context:

| Mode | Trigger | Source of truth |
|---|---|---|
| Commence | No proceeding exists yet because the lawyer is preparing an originating document | User interview |
| Query + fill | Proceedings exist but have gaps | Existing rows plus user-confirmed documents |
| Backfill | Documents on disk show proceedings that are missing from the database | Existing matter documents |

Form type alone does not determine mode. For example, an amended notice may be an originating-form style document, but the proceeding already exists.

## Step 3: Gather Proceedings Data

Required proceeding fields:

- `court`
- `registry`
- `file_number`
- `style_of_cause`
- `courthouse_address`
- `trial_date` if known
- `status` (`active`, `stayed`, or `concluded`)

Required party fields:

- `name`
- `party_type` (`individual`, `corporation`, `partnership`, or `other`)
- `lawyer_name` if known
- `lawyer_firm` if known

Valid proceeding-party roles:

- `plaintiff`
- `defendant`
- `third_party`
- `intervenor`
- `applicant`
- `respondent`
- `petitioner`

If counterclaims, responses to counterclaim, or third-party posture create ambiguity that cannot be expressed by these roles, read `references/deferred/counterclaim-asymmetry.md` and design against the current schema before changing the role enum.

## Step 4: Confirm and Write

Show extracted or elicited data to the user before inserting or updating. Include citations in the confirmation text, but do not try to store citations on proceedings or party rows; those tables do not have source-provenance fields.

Example confirmation:

```text
Proceeding: S-241171 (BCSC Vancouver)
  Court: Supreme Court of British Columbia
  Registry: Vancouver
  Courthouse: 800 Smithe Street, Vancouver, BC
  Trial date: not set
  Status: active
  Plaintiff: JOHN DUCKWORTH (individual) - counsel: Jane Smith, Logica Law
  Defendant: PATHFINDER CONSTRUCTION LTD. (corporation) - counsel: Bob Jones, ABC LLP

Sources reviewed:
  5. COURT FILE/NOCC.pdf#p1
```

On confirmation:

```sql
INSERT INTO main.proceedings (
    court, registry, file_number, style_of_cause,
    courthouse_address, trial_date, status
) VALUES (?, ?, ?, ?, ?, ?, ?);

INSERT INTO main.parties (
    name, party_type, lawyer_name, lawyer_firm, address, contact_info
) VALUES (?, ?, ?, ?, ?, ?);

INSERT INTO main.proceeding_parties (
    proceeding_id, party_id, role
) VALUES (?, ?, ?);
```

Check for existing party rows by normalized name before inserting a new party. Dump after mutation per `operations/maintain.md`.

## Step 5: Summary

Re-run the Step 1 query and return a grouped summary:

```text
Proceeding 1: S-241171 (BCSC Vancouver) - active
  Style of cause: Duckworth v. Pathfinder Construction Ltd.
  Courthouse: 800 Smithe Street, Vancouver, BC
  Trial date: not set
  Plaintiff:  JOHN DUCKWORTH (individual)
              Counsel: Jane Smith, Logica Law
  Defendant:  PATHFINDER CONSTRUCTION LTD. (corporation)
              Counsel: Bob Jones, ABC LLP
```

When invoked by another skill, return this summary to the caller. The caller uses the metadata; this operation does not need to know what the caller will draft.
