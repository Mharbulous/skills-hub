# Google Calendar Reference

Configuration and data details for Google Calendar integration. Load this file when fetching or interpreting calendar events.

## Configuration

Google Calendar access is via the Google Calendar MCP server. If the MCP server is not authenticated, prompt the practitioner to authenticate before proceeding.

## Fetching Events

Use the Google Calendar MCP server to list events for the target date. If the MCP server is not available or not authenticated, skip and record `"gcal"` in `sources_failed`. Tell the practitioner which source failed and why.

Retrieve events for the date range `{YYYY-MM-DD}T00:00:00` to `{YYYY-MM-DD}T23:59:59` in the practitioner's local timezone.

## Normalizing for Merge

- Default type: `activity_type: "meeting"`
- If event title contains "court", "hearing", "trial", or "chambers" → `activity_type: "court"`
- Signals = event title + description + location

## Source Hierarchy

Google Calendar is the least reliable source for determining activity type. When overlapping with TimeCamp or Telus, first try to reconcile (e.g., a GCal event titled "Smith hearing" + TimeCamp showing LEAP open to the Smith file → both agree, use both as signals). If irreconcilable, TimeCamp or Telus takes precedence. GCal fills gaps where no other source has data. Calendar event context is always preserved as an attribution signal even when another source takes precedence for activity type.

## Raw Data Storage

```bash
cowork-db set timesort "raw:gcal:{YYYY-MM-DD}" '{json_array}'
```

Record `"gcal"` in `sources_fetched`.
