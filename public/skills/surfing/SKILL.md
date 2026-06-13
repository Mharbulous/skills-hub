---
name: surfing
description: >
  Site-specific browser automation knowledge base — remembers quirks, workarounds,
  automation scripts, and interaction patterns for specific websites learned from
  previous sessions. Use this skill whenever Claude is about to interact with a website
  using browser tools — especially sites that have been visited before. For Playwright
  infrastructure (MCP config, Edge/CDP, tool reference), use /playwright instead.
  Also triggers on: browser verification, visual mockup, "show me", UI inspection.
---

# Surfing — Browser Automation Knowledge Base

## What this skill does

When you're about to interact with a website using browser tools, this skill tells you
what you've already learned about that site — shadow DOM quirks, navigation paths that
work (and ones that don't), form interaction patterns, timing issues, and workarounds
discovered through trial and error.

The knowledge lives in site-specific reference files. You only load the one you need.

## Playwright MCP

**For Playwright infrastructure** (MCP configuration, Edge/CDP setup, tool reference,
React SPA workarounds, parallel sessions, and troubleshooting), see the `/playwright`
skill. Invoke `/playwright` before any browser automation session.

This skill covers only **site-specific interaction knowledge** — quirks, workarounds,
and automation scripts for specific websites.

### Brainstorming Visual Companion Override

**This skill replaces the design-software visual companion.** When the marketplace
design-software checklist says "Offer visual companion (if topic will involve visual
questions)":

1. Do NOT offer the HTML companion server
2. Do NOT start `scripts/start-server.sh`
3. Instead, use Playwright MCP tools to show visuals
4. The user typically already has the dev server running — navigate to the relevant route

Skip the companion consent message entirely. The user has pre-authorized Playwright
for visual work.

### Critical Gotchas

**Verify against production routes, not just mockups.** When verifying handover claims
or inspecting current UI state, check the production route — not just dev mockup routes.
Dev mockups may be stale or simplified.

### Common Mistakes

| Mistake | Fix |
|---|---|
| Offering HTML companion during design-software | Use Playwright MCP instead — this skill overrides that step |
| Only checking dev mockup route | Verify production route too — mockups can be stale |
| Asking user to manually verify UI | Use Playwright to verify yourself |

## Playwright MCP tab concurrency {#tab-concurrency}

### Shared MCP server architecture

All Claude Code sessions on this machine connect to **the same Playwright MCP
server instance** — an SSE endpoint at `http://[::1]:8931/sse` (see `.mcp.json`).
There is no per-session isolation at the server level.

### Tab isolation within a single session

Creating a new tab via `browser_tabs(action="new")` gives you a logically separate
browsing context within the same browser window. This is useful for:

- **SSO/navigation hijacking** — keeping two Intuit domains in separate tabs so
  SSO redirects don't clobber your active session (see `references/qbo.md` for the
  Intuit-specific pattern)
- **Side-by-side contexts** — loading a reference page in one tab while working in
  another

Tab isolation works reliably within a single Claude Code session.

### Multi-session concurrency is NOT safe

If two Claude Code sessions both connect to the same Playwright MCP server and
issue commands concurrently, the following problems arise:

1. **`browser_snapshot` returns only the ACTIVE tab's accessibility tree.** If
   session A switches tabs or navigates, session B's next snapshot will return
   the wrong page — silently, with no error. Each session believes it is reading
   its own page, but both are reading whichever tab was last made active.

2. **The MCP SSE connection is serial.** Playwright MCP likely processes tool
   calls sequentially over the single SSE connection. Interleaved commands from
   two sessions will produce unpredictable results: session A's `browser_click`
   may fire on the page session B has open, and vice versa.

3. **No locking or session isolation.** The Playwright server has no concept of
   per-client sessions. Every connected client shares the same browser state.

### Recommendation

- **Tab isolation** is the right tool for SSO separation and context switching
  **within a single session**.
- **Multi-session concurrency** on the same MCP server is not safe. Tasks
  requiring browser automation must be dispatched **serially**, not in parallel.
  (See also: `feedback_qbo_serial_tasks.md` in Memory.)
- If true parallelism is needed in the future, it would require running separate
  Playwright MCP server instances on different ports, one per concurrent session.

---

## How to use this skill

### Step 1: Identify the site

Look at the current context to determine which site you're about to interact with:
- Check the active tab URL (from recent `navigate` calls)
- Check what the user is asking you to do
- Check the domain in any URLs mentioned

### Step 2: Check for a matching reference file

Consult the site index below. If there's a match, read that reference file before
you start clicking around. The knowledge in these files was earned the hard way —
don't skip it.

If there's no match, proceed normally. But pay attention to what you learn, because
you (or the user) may want to add a new reference file afterward.

### Step 3: Closing ceremony — self-improvement check

This skill contributes a step to the session's closing ceremony. At the end of
every session where browser tools were used, before the session ends, do the
following:

**Reflect on dead ends.** Review the session's browser interactions and ask:
did we hit at least 3 dead-end steps or red herrings while navigating a website
that could have been avoided if we'd known better going in? Examples of dead ends:
- Clicking elements that turned out to be in shadow DOM / iframe
- Trying a navigation path that failed before finding one that worked
- Experimenting with multiple interaction methods before finding the right one
- Waiting on pages that timeout and need a different approach
- Using the wrong URL, form, or portal when an alternate path exists

**If yes (3+ dead ends on a site):** You **must** use `/skill-creator` to update
the `/surfing` skill — add the lessons learned to the appropriate reference file
(or create a new one). Skill files are **read-only** at their installed location;
direct edits via `Edit` or `Write` will fail with `EROFS: read-only file system`.
The `/skill-creator` skill knows how to copy the skill to a writable location,
apply edits, and repackage it. This is the only way to persist updates to
reference files.

This is not optional. The whole point of this skill is to accumulate knowledge so
future sessions don't repeat the same experiments. The threshold of 3 dead ends
exists to filter out minor hiccups that aren't worth documenting, but anything
above that threshold represents real time savings for the future.

**If no:** Move on. Not every session produces new surfing knowledge, and that's
fine — it may mean the existing reference files are doing their job.

**Things worth capturing in reference files:**
- **Shadow DOM / iframe patterns** — elements that aren't in the main DOM
- **Navigation paths** — when the obvious route fails but an alternate works
- **Timing issues** — pages that need waits, or actions that need delays
- **Authentication boundaries** — what Claude can do vs. what the user must do
- **Form interaction quirks** — fields that need JavaScript vs. direct input
- **Cookie/consent walls** — sites that timeout or block on first load
- **Element targeting** — when `find` doesn't work but `javascript_tool` does
- **Workarounds** — alternate paths that bypass broken features

**Important:** This closing ceremony step combines with other skills' closing
ceremonies. For example, if `/tax-org-session` is also active, its stopping
ceremony (check checkbox, update session log, refresh dashboard) runs too. The
surfing self-improvement check is additive — it doesn't replace other ceremonies.

## Site Index

| Domain pattern | Reference file | Description |
|---|---|---|
| `cra-arc.gc.ca`, `canada.ca/revenue-agency` | `references/cra.md` | CRA My Account, My Business Account, GST/HST |
| `qbo.intuit.com`, `quickbooks.intuit.com` | `references/qbo.md` + `scripts/qbo-*.js` | QuickBooks Online (includes automation scripts) |
| `mbna.ca` | `references/mbna.md` | MBNA Mastercard portal |
| `royalbank.com`, `rbcroyalbank.com` | `references/rbc.md` | RBC Online Banking |
| `lsbc.org`, `lawsociety.bc.ca` | `references/lsbc.md` | Law Society of BC Member Portal |

> **No match?** Proceed without a reference file. If you learn something useful,
> suggest creating a new one at the end of the session.
