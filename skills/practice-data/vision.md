# Practice-Database — Vision & Design Philosophy

**Date:** 2026-04-23

## 1. Platform & Scope

practice-data is a helper skill within Co-Clerk, a Claude Cowork plugin for BC litigation practice management. It is not user-invocable — the practitioner never calls it directly. Every other skill that touches the shared SQLite database delegates to this skill for path resolution, schema initialization, and CRUD operations.

This skill owns four interlocked concerns:

- **Schema** — all `CREATE TABLE` definitions for practice.db live here and nowhere else
- **Path resolution** — the database location is read from `AppData\Roaming\Coclerk\coclerk.json`, which is also the sole record of the accounting system configuration
- **Initialization** — first-run setup, auto-move enforcement (relocating a misplaced DB to the configured path), and idempotent schema creation on every session
- **Consumer contract** — field-level guarantees (sign convention, date format, absence semantics) that downstream skills can rely on without inspecting source data

## 2. Purpose

### Audience

The direct audience is every other Co-Clerk skill that reads from or writes to the practice database. The practitioner is the indirect beneficiary: because one skill owns the schema, every skill's output draws from the same, consistently structured data.

### Pain Points

**Schema fragmentation.** Without a designated authority, each skill that needed persistent state would define its own tables. Over time, schemas would diverge — duplicate columns, inconsistent naming, conflicting types — with no clear owner to resolve conflicts.

**Silent schema drift.** When one skill's `CREATE TABLE` is modified, other skills that depended on the old column names break at runtime with opaque errors. Centralizing definitions makes breaking changes explicit and reviewable.

**Multiple uncoordinated sqlite3 connections.** Each skill opening its own connection to practice.db, constructing its own path, and making its own schema assumptions produces a system where a single file move, rename, or OneDrive sync event breaks different skills in different ways with no common recovery path.

**Data sovereignty fragility.** Client data must remain on the practitioner's local machine — BC Law Society requirements are not negotiable. If the database path were hardcoded or scattered across skills, there would be no single place to enforce or audit where the data lives.

### Value Proposition

A single, stable data layer that every skill trusts. Skills that need retainer balances, time entries, task state, or matter status get them from one place, with known column semantics and ISO 8601 dates — without knowing where the database lives or how it was initialized. When the database needs to move, one config value changes and every skill adapts.

### Killer Use Case

A new Co-Clerk installation. The practitioner runs any skill for the first time. practice-data reads `coclerk.json`, finds the database file, runs the idempotent `CREATE TABLE IF NOT EXISTS` block, and returns a ready connection — the skill that invoked it gets back a path to a valid, fully-structured database without any setup ceremony. On first use when `coclerk.json` does not exist, the initialization protocol runs, creates the config and database, and reports "Created a new practice database." No skill needs to handle first-run logic independently.

## 3. Theme & Design Philosophy

### Design Principles

**1. One skill owns the schema — no exceptions.**
No other skill may define a table, run `CREATE TABLE`, or open its own `sqlite3.connect()` to practice.db. Schema is a contract. Contracts need a single author.
**Why:** A schema definition in a downstream skill is invisible to every other skill. The first time two skills define conflicting schemas for what is nominally the same table, data integrity breaks silently — rows written by one skill are misread by another. By the time the discrepancy surfaces, the source is opaque.
**Violation example:** The billing-summary skill adds a `billed_at` column to `time_entries` in its own `CREATE TABLE` block. The practice-data skill's canonical schema doesn't include that column. On the next initialization, the column is absent on fresh installs. billing-summary fails with `no such column: billed_at` on new machines only, and no one can tell which skill is authoritative.

**2. Surface path resolution failures — never hardcode or guess.**
Always read the database location from `coclerk.json`. If the file is missing or the path is wrong, surface the problem explicitly. Never fall back to a hardcoded path, a default filename, or a guessed location.
**Why:** A hardcoded fallback creates a second, shadow database that silently receives writes while the real database goes empty. The practitioner has no indication anything is wrong until data is irrecoverably split.
**Violation example:** A skill cannot find `coclerk.json` and falls back to `./practice.db` in the current working directory. Writes succeed. The practitioner's configured database receives nothing. When they next open Co-Clerk from a different directory, that "data" is gone.

**3. Absence is not zero — distinguish unknown from confirmed empty.**
A missing row in `matters` means retainer status is unknown, not depleted. A `regular_trust = 0` entry means the retainer is confirmed depleted. These are different states and must not be conflated.
**Why:** Treating absence as zero causes a funded-retainer file to appear depleted. The practitioner deprioritizes it, work falls behind, and the client relationship suffers — all because a missing row was silently upgraded to a confirmed zero balance.
**Violation example:** The file prioritizer queries `regular_trust` for all active matters. Any matter with no row in `matters` is assigned a balance of 0 and deprioritized. A newly opened file with a $10,000 retainer is invisible to the prioritizer until the next CSV import.

**4. Data sovereignty is a hard architectural constraint, not a preference.**
The database must always reside on the practitioner's local machine at the path specified in `coclerk.json`. No client data is uploaded, embedded in plugin files, or written to cloud storage. The config file that locates the database contains only a file path and accounting system name — no client data.
**Why:** BC Law Society requirements mandate that lawyers maintain control over client information. A design that allows client data to leave the machine — even temporarily, even as a cache — is a compliance violation regardless of the reason.
**Violation example:** A skill caches a recent query result in a temporary file in the system temp directory. The temp directory is synced by OneDrive. Client matter data is now in Microsoft's cloud infrastructure without the practitioner's knowledge.

**5. Handle transient storage errors without treating them as corruption.**
The database may live in a OneDrive-synced folder. Sync activity, antivirus, or other open handles can produce transient `disk I/O error` messages. Retry once with a brief delay; if the error persists, open read-only via URI (`sqlite3.connect(f'file:{db_path}?mode=ro', uri=True)`) before concluding the database is damaged.
**Why:** Declaring a database corrupt when it is merely locked by a sync agent causes the practitioner to believe they have lost data. The appropriate response to a transient I/O error is a retry, not a data-loss warning.
**Violation example:** OneDrive is mid-sync. A time entry query returns `disk I/O error`. The skill reports "your database may be corrupt — please restore from backup." The database is fine; the sync completed in two seconds.

**6. Never bypass this skill by reading source data directly.**
If a database read fails, surface the error. Do not fall back to parsing a UNITY CSV, a LEAP export, or any other source file to answer a query.
**Why:** Source files enter Co-Clerk only through the import workflow. Reading them directly bypasses normalization, sign convention correction, and date standardization — and produces answers that contradict what the database would say once the import runs. The practitioner cannot tell which answer is correct.
**Violation example:** The retainer tracker cannot reach the database and silently falls back to parsing the most recently uploaded UNITY CSV. The CSV balance for one matter is negative (UNITY's convention). The tracker reports a negative retainer balance. The practitioner assumes the retainer is overdrawn; the actual normalized balance is $3,200 positive.

### Litmus Test

> "Does this involve defining tables, initializing the database, resolving the database path, or enforcing the consumer contract for practice.db?"

- **Yes → here:** Adding a column to an existing table, handling first-run initialization, resolving `coclerk.json` on a new machine, enforcing that `regular_trust` is never positive
- **No → downstream skill:** Calculating WIP from time entries, importing a UNITY CSV, querying the most active matters, generating an invoice

## 4. Non-Goals

- **Business logic or decision-making** — practice-data stores and retrieves data; it does not calculate WIP, rank files by priority, or decide when to send a retainer notice
- **Reporting or summarization** — producing human-readable output from stored data belongs to downstream skills
- **Accounting system integration** — data enters through the import workflow of dedicated skills (retainer-tracking, invoice-tracking); practice-data does not read UNITY CSV files or call LEAP's API
- **Trust accounting compliance** — the schema tracks retainer balances and time entries for practice management purposes; LSBC trust accounting reconciliation and compliance reporting are out of scope
- **Multi-database support** — the architecture is exactly one practice database per practitioner. No other databases may be created outside the two-tier structure (practice.db + per-matter evidence databases)

## 5. North Star

**Zero schema drift**: no other skill in Co-Clerk ever runs a `CREATE TABLE` or opens its own `sqlite3.connect()` to practice.db.

A secondary signal: every field-level guarantee in the consumer contract is honoured — no downstream skill has ever needed to inspect a raw UNITY value, apply a sign correction, or reparse a date because practice-data returned it inconsistently.

Success is measured by the absence of failures. When a new skill can be built that reads from the database without consulting source CSV formats, without applying its own normalization, and without hedging against schema surprises — that is the north star realized.

## 6. Anti-Patterns

**Pattern:** Defining `CREATE TABLE` in a downstream skill.
**Why it's wrong:** Creates a second, uncoordinated schema definition. On first install or after a schema migration, one definition wins and the other is either ignored or produces an error. The skill that lost becomes unpredictably broken.
**What to do instead:** Add the column to the canonical schema in practice-data's SKILL.md. Run the idempotent `CREATE TABLE IF NOT EXISTS` block as part of the standard initialization flow.

---

**Pattern:** Hardcoding a database path or username.
**Why it's wrong:** Breaks on any machine other than the one where the path was hardcoded. When the practitioner moves their database folder (to a new machine, a different OneDrive location, or an external drive), the hardcoded path silently fails or creates a shadow database.
**What to do instead:** Always read `database.folder` and `database.filename` from `coclerk.json`. Never reference a specific username, drive letter, or folder name in code.

---

**Pattern:** Treating a missing `matters` row as a zero retainer balance.
**Why it's wrong:** No row means the file has not been imported — retainer status is unknown. Treating it as zero causes funded-retainer files to be invisible to the prioritizer and other downstream skills that use balance to gate decisions.
**What to do instead:** Distinguish three states explicitly: `regular_trust = NULL or row absent` = unknown; `regular_trust = 0` = confirmed depleted; `regular_trust > 0` should never appear (UNITY reports trust credits as negative; normalized value is `abs(balance)`).

---

**Pattern:** Copying the live `.db` file with `cp` or file tools to read it.
**Why it's wrong:** A raw copy of an open SQLite database can capture pages mid-flush, producing an empty or structurally inconsistent copy. The copy appears valid but returns wrong results.
**What to do instead:** Open the configured path directly with `sqlite3.connect()`. For read-only access where lock contention is a concern, use `sqlite3.connect(f'file:{db_path}?mode=ro', uri=True)`.

---

**Pattern:** Falling back to source CSV parsing when a database read fails.
**Why it's wrong:** The CSV enters Co-Clerk only through the import workflow, which applies normalization (sign convention, date format, column mapping). Reading it directly bypasses that normalization and produces answers inconsistent with what the database would return.
**What to do instead:** Surface the database error to the user. Do not substitute CSV data for database data.

---

**Pattern:** Declaring `disk I/O error` as database corruption.
**Why it's wrong:** OneDrive sync, antivirus scanning, or another open handle routinely produces transient I/O errors on databases in synced folders. Treating these as corruption causes unnecessary alarm and can prompt the practitioner to restore from backup when no backup is needed.
**What to do instead:** Retry once. If the error persists, open read-only via URI. Only report possible corruption if the file is structurally unreadable after both attempts.
