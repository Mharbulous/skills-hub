# Google Calendar Reference

Configuration and data details for Google Calendar integration. Load this file when fetching calendar events for the timeline.

## Configuration

Google Calendar access is via the Google Calendar MCP server. If the MCP server is not authenticated, prompt the practitioner to authenticate before proceeding.

If the MCP server is not available or not authenticated, skip and record `"gcal"` in `sources_failed`. Tell the practitioner which source failed and why.

## Fetching Events

Use the Google Calendar MCP server to list events for the target date. Retrieve events for the date range `{YYYY-MM-DD}T00:00:00` to `{YYYY-MM-DD}T23:59:59` in the practitioner's local timezone.

Each event returned by the MCP server includes:
- `id` — the Google Calendar event ID (stable, unique per event; use as `native_id`)
- `summary` — event title
- `start` — start datetime (with timezone info)
- `end` — end datetime (with timezone info)
- `description` — optional event description
- `location` — optional location string
- `attendees` — optional list of attendees

Google Calendar events have a start and end and are stored as **activities** in the `timeline` namespace.

## Computing native_id

Use the Google Calendar event's `id` field (the iCal UID or GCal event ID) directly as `native_id`. The stable row ID is `gcal:{event_id}`.

If the event has no `id` field (unusual), compose from `start_time + "_" + calendar_id`.

Google Calendar events have a start and end and are stored as **activities** in the timeline namespace, not events.
