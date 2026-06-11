# Predict Mode — Predictive Pre-Loading

**Invoked via:** `/agents-md-curator predict "description"`

Pre-loads `<CURATED>` content for upcoming work before commits exist.

## Steps

1. **Parse feature description** [Haiku] — Spawn a **Haiku** agent to extract likely file paths, folder patterns, and keywords from the description. Returns a JSON list of path patterns.
   - **Why Haiku:** Keyword extraction and path pattern matching — mechanical, not semantic.
2. **Query cold storage** [Python] — Run SQL query to find lines with historical `relevant_paths` matching the extracted patterns. No LLM needed.
3. **Rank matches** [Python] — Sort by relevance event frequency.
4. **Record predicted events** [Python] — For each candidate line, insert a `predicted` `relevance_event` whose `relevant_paths` is the path patterns Haiku extracted. This is critical: the depth-placement pass uses `relevant_paths` to route the line to the right managed file. Without realistic paths on the predicted event, the prediction would land at the wrong depth.
   ```sql
   INSERT INTO relevance_events (line_id, repo, relevant_paths, event_type, notes)
   VALUES (?, '<repo>', '<comma-separated extracted paths>', 'predicted', ?);
   ```
5. **Run depth placement** [Python] — `python scripts/depth_placement.py <db_path>` — recomputes which managed file each line belongs in, now considering the freshly inserted predicted events.
6. **Run competitive placement per file** [Python] — `python scripts/competitive_placement.py <db_path> --managed-files <json>` using Phase 5's `by_file` map. Predicted events count at 0.25x, so they only displace placed lines if they have meaningful repeated history.

## Predicted Event Weighting

Predicted events count at ~0.25x observed in the composite score. Speculative until confirmed.

## Confirmation Behavior

If actual commits later confirm the prediction, an `observed` event supplements the `predicted` one. The predicted event remains in the record but the observed event carries full weight, and the line's depth assignment may shift if the observed paths differ from what Haiku predicted.
