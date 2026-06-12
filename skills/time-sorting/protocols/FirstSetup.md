# First Setup Protocol

Run this protocol the first time a user invokes any time-sorting operation. This covers one-time setup steps that do not repeat on subsequent sorts.

**Trigger:** The user requests a time-sorting operation (e.g., "sort today's time") and either `time_tracking` is absent from `coclerk.json`, or `time_tracking.sources` is absent or empty.

## Step 1 — Discover Time-Tracking Tools

Ask the user which tools they use to track their time. Present as a multi-select checklist — most practitioners use a combination:

1. **TimeCamp** — "Desktop app that tracks which applications and websites you use"
2. **Google Calendar** — "For court dates, meetings, and appointments"
3. **Telus Business Connect** — "Phone call logs from your Telus business phone"
4. **Something else** — "Another tool not listed here"

If the user selects "Something else," ask them to name the tool. Check against this list of recognized-but-unsupported tools:

| Tool | Category | Status |
|------|----------|--------|
| Chrometa | screen_activity | Not yet supported |
| RingCentral | telephony | Not yet supported |
| Clio Manage (time tracking) | time_entry | Not yet supported |
| Toggl | time_entry | Not yet supported |

If the named tool matches one of these, acknowledge it specifically: *"I know what [tool] is — it captures [category]. I don't have an integration for it yet, but I'll note it so we can add support later."*

If the named tool is completely unknown, ask the practitioner what it does (screen tracking? phone logs? calendar? manual time entry?) so it can be categorized and recorded.

**Minimum requirement:** At least one supported source (TimeCamp, Google Calendar, or Telus Business Connect) must be selected to proceed. If the practitioner only uses unsupported tools, explain that time-sorting currently requires at least one of the three supported sources, and offer to note their tools for future integration.

## Step 2 — Per-Source Setup

For each supported source the user selected, run its setup sub-procedure. These run in sequence since each is a short conversational exchange.

### 2a: TimeCamp Setup

1. Check for an existing token: `cowork-db get timesort "config:timecamp_token"`
2. If already present, confirm: *"I found a TimeCamp API token already stored. Want to keep using it, or replace it?"*
3. If not present, ask: *"I need your TimeCamp API token to fetch your computer activities. You can find it at: TimeCamp > click your avatar > Profile Settings > scroll to the bottom for 'Your programming API token'."*
4. Once provided, store it: `cowork-db set timesort "config:timecamp_token" "{token}"`
5. Validate by making a test API call (fetch projects with the token per `reference/TimeCamp.md`). If the call fails (401, network error), tell the practitioner and offer to retry with a different token.
6. On success: *"TimeCamp is connected. I can see your project tree."*

### 2b: Google Calendar Setup

1. Check whether the Google Calendar MCP server is available and authenticated (attempt an MCP call).
2. If authenticated: *"Google Calendar is already connected."*
3. If not authenticated: *"Google Calendar needs to be connected through your Cowork settings."* Invoke `mcp__claude_ai_Google_Calendar__authenticate` to start the auth flow.
4. If the MCP server is not available at all (not installed): *"The Google Calendar connection isn't set up in Cowork yet. You'll need to add the Google Calendar MCP server to your Cowork configuration. I'll mark it as enabled — if it's not available when sorting, I'll note that calendar data was unavailable and proceed with other sources."*

### 2c: Telus Business Connect Setup

1. No persistent configuration needed. Inform: *"Telus Business Connect works from CSV exports — you'll provide the file path each time you sort. No setup needed on my end."*
2. Optionally ask: *"Do you typically export the call log yourself, or does someone else provide it?"* (informational context for future conversational flow).

## Step 3 — API-Specific Privacy Note

The general privacy briefing (local storage, training opt-out, client name exclusion) is handled during database initialization (`practice-data/protocol/initialize.md` Step 4). This step covers only the API-specific concern for time-sorting.

Briefly inform the practitioner:

> "When I fetch your activity data from [list configured API sources, e.g. "TimeCamp and Google Calendar"], the request goes through an encrypted connection straight to your local machine. I never store it anywhere except your local database, and I never write anything back to these services — all access is strictly read-only."

No user action required — this is informational only.

## Step 4 — Offer Source Research

For each configured source and each unsupported-but-noted tool, offer to research optimal settings and export capabilities:

*"Would you like me to do some quick research on getting the best data out of [your configured sources]? For example, I can look into TimeCamp's optimal settings for window title tracking, or tips for exporting Telus call logs. This runs in the background and won't slow things down."*

If approved:

1. Spawn a **background research subagent** for each tool that does not already have a reference file at `reference/[ToolName].md`
2. While subagents run, proceed immediately to Step 5 (do not wait)
3. When a subagent returns, review its findings critically — research agents can sometimes confuse similar products. Cross-check claims against what the user confirmed
4. Save vetted findings to `reference/[ToolName].md` for future sessions

If declined, skip.

## Step 5 — Save Configuration and Hand Off

Save the time-tracking configuration to `coclerk.json` under a new `time_tracking` top-level key:

```json
{
  "time_tracking": {
    "configured_at": "<ISO 8601 timestamp>",
    "sources": [
      {
        "id": "timecamp",
        "type": "screen_activity",
        "enabled": true,
        "auth": "cowork-db",
        "reference": "reference/TimeCamp.md"
      },
      {
        "id": "gcal",
        "type": "calendar",
        "enabled": true,
        "auth": "mcp",
        "reference": "reference/GoogleCalendar.md"
      },
      {
        "id": "telus",
        "type": "telephony",
        "enabled": true,
        "auth": "csv_per_use",
        "reference": "reference/TelusConnect.md"
      }
    ],
    "unsupported_noted": ["chrometa"]
  }
}
```

Only include sources the user selected. The `auth` field indicates how credentials are managed:
- `"cowork-db"` — API token stored in cowork-db
- `"mcp"` — MCP server handles authentication
- `"csv_per_use"` — no persistent auth, user provides data each time

Summarize what was configured:

> "All set. Here's your time-tracking setup:
> - **TimeCamp**: Connected (API token stored)
> - **Google Calendar**: Connected (MCP authenticated)
> - **Telus Business Connect**: Ready (CSV-based, no setup needed)
>
> You can now say 'sort today's time' and I'll pull from all three sources."

If any unsupported tools were noted:

> "I've also noted that you use [tool]. I'll let you know when integration is available."

Hand off to SKILL.md Step 1 (Sync TimeCamp Project/Task Tree).

## What Does NOT Happen on Subsequent Sorts

On future sorts, the following are already configured and read from `coclerk.json` without user interaction:

- Which time-tracking sources are enabled
- Authentication method for each source
- Unsupported tools noted for future integration

The standard workflow in `SKILL.md` handles subsequent sorts directly. This protocol is only invoked when `time_tracking.sources` is missing from `coclerk.json`.
