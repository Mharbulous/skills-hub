# TimeCamp Reference

API and configuration details for TimeCamp integration. Load this file when interacting with the TimeCamp API or resolving TimeCamp-specific data structures.

## Terminology

This skill aligns with TimeCamp's own concepts:

- **Computer activities** — websites and applications tracked by the TimeCamp desktop app, each with an application name, window title, and duration
- **Time entries** — recorded time segments on the timesheet, either auto-tracked or manually created
- **Projects** — top-level containers in TimeCamp's hierarchy (e.g., "Client Matters", "Administration")
- **Tasks** — children of Projects (e.g., "Smith v Jones (L3948)" under "Client Matters")
- **Subtasks** — children of Tasks for finer granularity (available on Premium/Ultimate plans)
- **Assign / Move** — TimeCamp's term for attributing computer activities to a Task
- **Unassigned computer activities** — time tracked by the desktop app that hasn't been assigned to any Task; does not count toward the daily timesheet total

## Configuration

### API Token

The TimeCamp API token is stored in cowork-db:

```bash
cowork-db set timesort "config:timecamp_token" "YOUR_TOKEN_HERE"
```

To check if configured:

```bash
cowork-db get timesort "config:timecamp_token"
```

If exit code 1 (not found), ask the practitioner for their TimeCamp API token. They can find it at TimeCamp → Avatar → Profile Settings → scroll to the bottom for "Your programming API token".

## Project/Task Tree

TimeCamp organizes work into a hierarchy: Projects → Tasks → Subtasks. This skill syncs that tree into cowork-db so activities can be assigned to known Tasks.

### Syncing the Project Tree

Fetch the full project/task tree from TimeCamp:

```bash
curl -s -X POST "https://www.timecamp.com/third_party/api/v3/projects" \
  -H "Authorization: Bearer {token}" \
  -H "Content-Type: application/json" \
  -d '{"parentId": 0, "status": "active", "perPage": 250}'
```

Response includes `taskId`, `name`, `parentId`, `level`, `hasChildren`, `billable`, `archived`, and `children[]`. Walk the tree recursively to get all Tasks.

Store the tree in cowork-db:

```bash
cowork-db set timesort "projects:tree" '{json_tree}'
cowork-db set timesort "projects:synced_at" '{ISO_timestamp}'
```

Also build a flat lookup for quick matching:

```bash
cowork-db set timesort "projects:lookup" '{task_id_to_name_map}'
```

### When to Sync

- On first run (no `projects:tree` key exists)
- When the practitioner asks to refresh the project list
- When an activity's window title mentions a matter not in the current tree
- At most once per session to avoid API rate limits

## Fetching Computer Activities

Retrieve the TimeCamp token:

```bash
cowork-db get timesort "config:timecamp_token"
```

If not found (exit code 1), skip TimeCamp and record `"timecamp"` in `sources_failed`. Tell the practitioner: "TimeCamp token not configured. Run: `cowork-db set timesort \"config:timecamp_token\" \"YOUR_TOKEN\"`"

If found, fetch activities with resolved application names and window titles:

```bash
curl -s -H "Authorization: Bearer {token}" -H "Accept: application/json" \
  "https://www.timecamp.com/third_party/api/activity?dates[]={YYYY-MM-DD}&include=application,window_title&format=json"
```

The `include=application,window_title` parameter tells the API to resolve the numeric IDs into human-readable names inline. The `dates[]` parameter (not `date`) is required — it accepts an array of up to 20 dates.

### Response Format

Each entry in the JSON array contains:
- `end_time` — "YYYY-MM-DD HH:MM:SS"
- `time_span` — seconds (compute start_time as end_time minus time_span)
- `application` — e.g. "Google Chrome", "Visual Studio Code" (resolved from application_id)
- `window_title` — e.g. "Smith v Jones - LEAP - Documents" (resolved from window_title_id)
- `application_id` — numeric ID
- `window_title_id` — numeric ID
- `task_id` — TimeCamp Task ID if already assigned, "0" if unassigned

If the API returns an error status code, empty response, or unparseable JSON, record `"timecamp"` in `sources_failed` with the error reason. Tell the practitioner what went wrong (e.g., "TimeCamp API returned 401 — token may be invalid"). Proceed with other sources.

### Normalizing for Merge

- TimeCamp entries → `activity_type: "screen_work"`
- Signals = application name + window title
- Compute start from `end_time - time_span`

### Pre-assigned Activities

If a TimeCamp activity already has a non-zero `task_id`, respect that assignment (the practitioner already assigned it in TimeCamp). Set `confidence: "high"` and `assigned_from: "timecamp_preassigned"`.

## Raw Data Storage

```bash
cowork-db set timesort "raw:timecamp:{YYYY-MM-DD}" '{json_array}'
```

Record `"timecamp"` in `sources_fetched`.
