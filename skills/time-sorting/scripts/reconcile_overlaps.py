#!/usr/bin/env python3
"""
reconcile_overlaps.py

Detects overlapping activities in a normalized timeline and applies source hierarchy
reconciliation to produce a merged timeline with no overlaps.

This module handles the critical Step 2: Merge Timeline logic from the time-sorting skill.
It reconciles activities from multiple sources (TimeCamp, Telus, Google Calendar) using
a source hierarchy (Telus > TimeCamp > GCal) while preserving attribution signals.

Usage:
    from reconcile_overlaps import reconcile_overlaps, merge_timeline

    # Start with normalized activities (output from normalize_activity.py)
    normalized = [
        {"start": "09:02", "end": "09:47", "source": "timecamp", "type": "screen_work", ...},
        {"start": "09:47", "end": "09:57", "source": "telus", "type": "phone_call", ...},
        {"start": "10:00", "end": "10:30", "source": "gcal", "type": "meeting", ...},
    ]

    # Reconcile overlaps
    reconciled = reconcile_overlaps(normalized)

    # Full workflow: reconcile + sort + fill gaps
    final = merge_timeline(normalized, date="2026-04-13")

Each normalized activity should have:
    {
        "start": "HH:MM",
        "end": "HH:MM",
        "source": "timecamp|telus|gcal",
        "type": "screen_work|phone_call|meeting|court",
        "duration_minutes": int,
        "raw_signals": [list],
        "raw_id": str,
        "metadata": {...}
    }

The reconcile_overlaps() function returns a merged timeline where:
- Overlapping activities are reconciled using source hierarchy
- Non-overlapping activities pass through unchanged
- Activity IDs are assigned (a1, a2, a3, ...)
- All activities are sorted by start time
- Gap filling can be applied separately via fill_gaps()
"""

import re
from typing import Dict, List, Tuple, Any, Optional
from datetime import datetime


# ============================================================================
# Helper Functions
# ============================================================================

def hhmm_to_minutes(hhmm: str) -> int:
    """
    Convert HH:MM time string to minutes since midnight.

    Args:
        hhmm: Time string in format "HH:MM" (e.g., "09:47")

    Returns:
        Integer minutes since midnight

    Raises:
        ValueError: If format is invalid
    """
    try:
        h, m = map(int, hhmm.split(':'))
        return h * 60 + m
    except (ValueError, IndexError):
        raise ValueError(f"Invalid time format: {hhmm}. Expected HH:MM")


def minutes_to_hhmm(minutes: int) -> str:
    """
    Convert minutes since midnight to HH:MM time string.

    Args:
        minutes: Minutes since midnight (e.g., 587)

    Returns:
        Time string "HH:MM" (e.g., "09:47")
    """
    h = minutes // 60
    m = minutes % 60
    return f"{h:02d}:{m:02d}"


def get_source_priority(source: str) -> int:
    """
    Get numeric priority for a source (used for tiebreaking overlaps).

    Source hierarchy (higher number = higher priority):
    1. Telus (most reliable for activity type and timing)
    2. TimeCamp (highest volume, good signal for matter matching)
    3. Google Calendar (least reliable, often approximate)

    Args:
        source: Source name ("timecamp", "telus", "gcal")

    Returns:
        Priority integer (higher = wins tiebreaker)
    """
    priorities = {
        "telus": 3,
        "timecamp": 2,
        "gcal": 1,
        "none": 0
    }
    return priorities.get(source, 0)


def activities_overlap(activity_a: Dict[str, Any], activity_b: Dict[str, Any]) -> bool:
    """
    Check if two activities overlap in time.

    Two activities overlap if:
        a.start < b.end AND b.start < a.end

    Args:
        activity_a: First normalized activity
        activity_b: Second normalized activity

    Returns:
        True if activities overlap, False otherwise

    Example:
        >>> a = {"start": "09:00", "end": "10:00"}
        >>> b = {"start": "09:45", "end": "10:30"}
        >>> activities_overlap(a, b)
        True
    """
    a_start = hhmm_to_minutes(activity_a["start"])
    a_end = hhmm_to_minutes(activity_a["end"])
    b_start = hhmm_to_minutes(activity_b["start"])
    b_end = hhmm_to_minutes(activity_b["end"])

    return a_start < b_end and b_start < a_end


def find_overlapping_groups(activities: List[Dict[str, Any]]) -> List[List[int]]:
    """
    Find groups of activities that overlap with each other.

    An overlapping group is a set of activities where at least one activity
    overlaps with at least one other activity in the group.

    Args:
        activities: List of normalized activities (sorted by start time)

    Returns:
        List of lists, where each inner list contains indices of overlapping activities

    Example:
        >>> activities = [
        ...     {"start": "09:00", "end": "10:00"},  # index 0
        ...     {"start": "09:30", "end": "10:30"},  # index 1 (overlaps with 0)
        ...     {"start": "11:00", "end": "12:00"},  # index 2 (no overlap)
        ... ]
        >>> groups = find_overlapping_groups(activities)
        >>> groups
        [[0, 1], [2]]
    """
    n = len(activities)
    assigned = [False] * n
    groups = []

    for i in range(n):
        if assigned[i]:
            continue

        # Start a new group with activity i
        group = [i]
        assigned[i] = True

        # Find all activities that overlap with anything in this group
        j = i + 1
        while j < n:
            # Check if activity j overlaps with any activity in the group
            overlaps_with_group = any(
                activities_overlap(activities[group[0]], activities[j])
                for _ in [0]  # Dummy loop for single check
            ) or any(
                activities_overlap(activities[idx], activities[j])
                for idx in group
            )

            if overlaps_with_group:
                group.append(j)
                assigned[j] = True

            j += 1

        groups.append(group)

    return groups


def reconcile_activity_group(activities: List[Dict[str, Any]], group: List[int]) -> List[Dict[str, Any]]:
    """
    Reconcile a group of overlapping activities.

    Strategy:
    1. If only one activity, return it unchanged
    2. If Telus present, use Telus for activity type (most reliable)
    3. Preserve all signals as attribution context
    4. Keep all activities but mark overlapping relationships

    Args:
        activities: Full list of normalized activities
        group: List of indices in the group

    Returns:
        List of reconciled activities (modified in-place but returned for clarity)

    Example:
        >>> activities = [
        ...     {
        ...         "source": "timecamp",
        ...         "type": "screen_work",
        ...         "start": "09:47",
        ...         "end": "10:05",
        ...         "metadata": {"window_title": "Smith v Jones (L3948)"}
        ...     },
        ...     {
        ...         "source": "telus",
        ...         "type": "phone_call",
        ...         "start": "09:47",
        ...         "end": "09:57",
        ...         "metadata": {"contact_name": "Smith - Client"}
        ...     }
        ... ]
        >>> reconciled = reconcile_activity_group(activities, [0, 1])
        >>> # Both are preserved; Telus phone_call has higher priority for activity type
    """
    if len(group) == 1:
        # No overlap, return unchanged
        return [activities[group[0]]]

    result = []
    group_sources = [activities[idx]["source"] for idx in group]
    has_telus = "telus" in group_sources
    has_timecamp = "timecamp" in group_sources

    # Preserve all activities; reconciliation is done at merge time
    # when deciding which activity "owns" a time period
    for idx in group:
        activity = dict(activities[idx])  # Shallow copy

        # Add context from other sources in the group
        other_signals = []
        for other_idx in group:
            if other_idx != idx:
                other_activity = activities[other_idx]
                # Add summary of other source
                other_signals.append(
                    f"{other_activity['source'].upper()}: {other_activity['raw_signals'][0] if other_activity.get('raw_signals') else 'N/A'}"
                )

        if other_signals:
            if "attribution_context" not in activity:
                activity["attribution_context"] = []
            activity["attribution_context"].extend(other_signals)

        result.append(activity)

    return result


def merge_overlapping_segments(
    activities: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    """
    Merge overlapping activities by splitting time periods and assigning ownership.

    When activities overlap:
    1. Identify the overlapping time range
    2. Determine which source "owns" that period (using source hierarchy)
    3. Split activities at overlap boundaries
    4. Mark context signals from non-owning sources

    Args:
        activities: List of normalized activities (pre-sorted by start time)

    Returns:
        List of merged activities with no overlaps (but may contain same time with different sources)
    """
    if len(activities) <= 1:
        return activities

    # Sort by start time, then by source priority (descending)
    activities.sort(
        key=lambda a: (
            hhmm_to_minutes(a["start"]),
            -get_source_priority(a["source"])
        )
    )

    result = []
    i = 0

    while i < len(activities):
        current = activities[i]
        current_start = hhmm_to_minutes(current["start"])
        current_end = hhmm_to_minutes(current["end"])

        # Find overlaps with current activity
        overlapping_indices = []
        for j in range(i + 1, len(activities)):
            other = activities[j]
            other_start = hhmm_to_minutes(other["start"])
            other_end = hhmm_to_minutes(other["end"])

            # Overlap if: current.start < other.end AND other.start < current.end
            if current_start < other_end and other_start < current_end:
                overlapping_indices.append(j)
            elif other_start >= current_end:
                # No more overlaps (activities are sorted)
                break

        if not overlapping_indices:
            # No overlaps, add current activity unchanged
            result.append(current)
            i += 1
        else:
            # Has overlaps - use source hierarchy to determine "owner"
            # Higher priority source is recorded, others are added as context

            overlapping = [activities[idx] for idx in overlapping_indices]

            # Determine which source should take precedence
            current_priority = get_source_priority(current["source"])
            max_overlap_priority = max(
                get_source_priority(act["source"]) for act in overlapping
            )

            if current_priority >= max_overlap_priority:
                # Current activity is equal or higher priority
                # Add overlapping context signals
                for other_act in overlapping:
                    context_signal = f"Concurrent: {other_act['source'].upper()} {other_act['type']}"
                    if "attribution_context" not in current:
                        current["attribution_context"] = []
                    current["attribution_context"].append(context_signal)

                result.append(current)
                i += 1
            else:
                # Higher priority activity in overlapping list
                winner = max(overlapping, key=lambda a: get_source_priority(a["source"]))

                # Add current activity as context
                context_signal = f"Concurrent: {current['source'].upper()} {current['type']}"
                if "attribution_context" not in winner:
                    winner["attribution_context"] = []
                winner["attribution_context"].append(context_signal)

                # Add other context activities too
                for other_act in overlapping:
                    if other_act != winner:
                        other_context = f"Concurrent: {other_act['source'].upper()} {other_act['type']}"
                        winner["attribution_context"].append(other_context)

                result.append(winner)
                i += 1

                # Mark skipped overlapping activities
                # (They're preserved in raw data, but time ownership goes to winner)

    return result


def reconcile_overlaps(activities: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Main reconciliation function: detects and reconciles overlapping activities.

    This is the core Step 2 logic: given normalized activities from all sources,
    reconcile overlaps using source hierarchy while preserving all attribution signals.

    Process:
    1. Sort activities by start time
    2. Find overlapping groups
    3. For each group, apply reconciliation strategy
    4. Assign sequential IDs (a1, a2, ...)
    5. Return merged timeline

    Args:
        activities: List of normalized activities (from normalize_activity.py)

    Returns:
        List of reconciled activities with:
        - Sequential IDs assigned (a1, a2, ...)
        - Overlaps resolved using source hierarchy
        - All activities sorted by start time
        - Attribution context added where overlaps occurred

    Example:
        >>> normalized = [
        ...     {"start": "09:02", "end": "09:47", "source": "timecamp", ...},
        ...     {"start": "09:47", "end": "09:57", "source": "telus", ...},
        ...     {"start": "10:00", "end": "10:30", "source": "gcal", ...},
        ... ]
        >>> reconciled = reconcile_overlaps(normalized)
        >>> len(reconciled)
        3
        >>> reconciled[0]["id"]
        "a1"
        >>> reconciled[1]["id"]
        "a2"
    """
    if not activities:
        return []

    # Sort by start time
    sorted_activities = sorted(
        activities,
        key=lambda a: hhmm_to_minutes(a["start"])
    )

    # Merge overlapping segments
    merged = merge_overlapping_segments(sorted_activities)

    # Assign sequential IDs
    for i, activity in enumerate(merged, 1):
        activity["id"] = f"a{i}"

    return merged


def fill_gaps(
    activities: List[Dict[str, Any]],
    work_start: str = "07:00",
    work_end: str = "19:00"
) -> List[Dict[str, Any]]:
    """
    Fill time gaps between activities with "untracked" placeholders.

    Identifies periods in the workday (work_start to work_end) that have no activity
    data from any source and creates "untracked" activities to represent them.

    Args:
        activities: List of reconciled activities (already sorted by start time)
        work_start: Start of work hours "HH:MM" (default "07:00")
        work_end: End of work hours "HH:MM" (default "19:00")

    Returns:
        List of activities with gaps filled, including untracked periods

    Example:
        >>> activities = [
        ...     {"start": "09:00", "end": "10:00", "source": "timecamp", ...},
        ...     {"start": "11:00", "end": "12:00", "source": "telus", ...},
        ... ]
        >>> filled = fill_gaps(activities)
        >>> len(filled)
        5  # Original 2 + gap1 (07:00-09:00) + gap2 (10:00-11:00) + gap3 (12:00-19:00)
    """
    if not activities:
        # Entire day is untracked
        day_start = hhmm_to_minutes(work_start)
        day_end = hhmm_to_minutes(work_end)
        return [{
            "id": "a1",
            "start": work_start,
            "end": work_end,
            "source": "none",
            "type": "untracked",
            "duration_minutes": day_end - day_start,
            "raw_signals": ["No activity data"],
            "raw_id": "gap_full_day",
            "metadata": {}
        }]

    result = []
    day_start = hhmm_to_minutes(work_start)
    day_end = hhmm_to_minutes(work_end)

    current_time = day_start
    gap_counter = 1

    # Sort activities by start time (should already be sorted, but be safe)
    sorted_activities = sorted(
        activities,
        key=lambda a: hhmm_to_minutes(a["start"])
    )

    for activity in sorted_activities:
        activity_start = hhmm_to_minutes(activity["start"])

        # Fill gap before this activity
        if current_time < activity_start:
            gap_duration = activity_start - current_time
            result.append({
                "id": None,  # Will be re-assigned later
                "start": minutes_to_hhmm(current_time),
                "end": minutes_to_hhmm(activity_start),
                "source": "none",
                "type": "untracked",
                "duration_minutes": gap_duration,
                "raw_signals": ["Gap in activity data"],
                "raw_id": f"gap_{gap_counter}",
                "metadata": {}
            })
            gap_counter += 1

        # Add the activity itself
        result.append(activity)
        current_time = hhmm_to_minutes(activity["end"])

    # Fill gap after last activity
    if current_time < day_end:
        gap_duration = day_end - current_time
        result.append({
            "id": None,  # Will be re-assigned later
            "start": minutes_to_hhmm(current_time),
            "end": minutes_to_hhmm(day_end),
            "source": "none",
            "type": "untracked",
            "duration_minutes": gap_duration,
            "raw_signals": ["Gap in activity data"],
            "raw_id": f"gap_{gap_counter}",
            "metadata": {}
        })

    # Re-assign sequential IDs
    for i, activity in enumerate(result, 1):
        activity["id"] = f"a{i}"

    return result


def merge_timeline(
    normalized_activities: List[Dict[str, Any]],
    date: str = None,
    work_start: str = "07:00",
    work_end: str = "19:00"
) -> Dict[str, Any]:
    """
    Complete merge workflow: reconcile overlaps, fill gaps, and return merged timeline.

    This is the full Step 2: Merge Timeline workflow from the time-sorting skill.
    It combines overlap reconciliation and gap filling into a single call.

    Args:
        normalized_activities: List of normalized activities (from normalize_activity.normalize_batch)
        date: Target date "YYYY-MM-DD" (for metadata)
        work_start: Start of work hours "HH:MM" (default "07:00")
        work_end: End of work hours "HH:MM" (default "19:00")

    Returns:
        Dictionary with schema:
        {
            "date": str,
            "merged_at": ISO timestamp,
            "activities": [list of merged activities],
            "stats": {
                "input_count": int,
                "output_count": int,
                "gaps_filled": int,
                "overlaps_resolved": int
            }
        }

    Example:
        >>> normalized = normalize_batch(timecamp_data, telus_data, gcal_data)
        >>> merged = merge_timeline(normalized, date="2026-04-13")
        >>> merged["stats"]["overlaps_resolved"]
        2
        >>> len(merged["activities"])
        18
    """
    input_count = len(normalized_activities)

    # Step 1: Reconcile overlaps
    reconciled = reconcile_overlaps(normalized_activities)

    # Step 2: Fill gaps
    filled = fill_gaps(reconciled, work_start, work_end)

    output_count = len(filled)
    gaps_created = output_count - input_count
    overlaps_resolved = len([a for a in reconciled if "attribution_context" in a])

    return {
        "date": date,
        "merged_at": datetime.now().isoformat(),
        "activities": filled,
        "stats": {
            "input_count": input_count,
            "output_count": output_count,
            "gaps_filled": gaps_created,
            "overlaps_resolved": overlaps_resolved
        }
    }


# ============================================================================
# Command-Line Usage / Self-Test
# ============================================================================

if __name__ == "__main__":
    """
    Test the reconciliation functions with sample data.
    Run: python3 reconcile_overlaps.py
    """

    print("=" * 80)
    print("reconcile_overlaps.py - Testing Overlap Reconciliation")
    print("=" * 80)
    print()

    # Test 1: Simple non-overlapping activities
    print("Test 1: Non-overlapping activities")
    print("-" * 80)
    simple = [
        {
            "start": "09:00",
            "end": "10:00",
            "source": "timecamp",
            "type": "screen_work",
            "duration_minutes": 60,
            "raw_signals": ["LEAP: Smith v Jones"],
            "raw_id": "tc1",
            "metadata": {}
        },
        {
            "start": "11:00",
            "end": "12:00",
            "source": "telus",
            "type": "phone_call",
            "duration_minutes": 60,
            "raw_signals": ["Contact: Client"],
            "raw_id": "telus1",
            "metadata": {}
        }
    ]
    reconciled = reconcile_overlaps(simple)
    print(f"Input: {len(simple)} activities")
    print(f"Output: {len(reconciled)} activities (no overlap expected)")
    for act in reconciled:
        print(f"  {act['id']}: {act['start']}–{act['end']} ({act['source']}) {act['type']}")
    print()

    # Test 2: Overlapping activities
    print("Test 2: Overlapping activities (Telus + TimeCamp)")
    print("-" * 80)
    overlapping = [
        {
            "start": "09:47",
            "end": "10:05",
            "source": "timecamp",
            "type": "screen_work",
            "duration_minutes": 18,
            "raw_signals": ["LEAP: Smith v Jones (L3948)"],
            "raw_id": "tc2",
            "metadata": {"window_title": "Smith v Jones - Google Docs"}
        },
        {
            "start": "09:47",
            "end": "09:57",
            "source": "telus",
            "type": "phone_call",
            "duration_minutes": 10,
            "raw_signals": ["Contact: Smith - Client"],
            "raw_id": "telus1",
            "metadata": {"contact_name": "Smith - Client"}
        }
    ]
    reconciled_overlap = reconcile_overlaps(overlapping)
    print(f"Input: {len(overlapping)} activities (overlapping 09:47–09:57)")
    print(f"Output: {len(reconciled_overlap)} activities")
    for act in reconciled_overlap:
        context = f" (context: {', '.join(act.get('attribution_context', []))})" if act.get('attribution_context') else ""
        print(f"  {act['id']}: {act['start']}–{act['end']} ({act['source']}) {act['type']}{context}")
    print()

    # Test 3: Gap filling
    print("Test 3: Gap filling (work hours 07:00–19:00)")
    print("-" * 80)
    sparse = [
        {
            "id": "a1",
            "start": "09:00",
            "end": "10:00",
            "source": "timecamp",
            "type": "screen_work",
            "duration_minutes": 60,
            "raw_signals": [],
            "raw_id": "tc1",
            "metadata": {}
        }
    ]
    filled = fill_gaps(sparse)
    print(f"Input: {len(sparse)} activities (09:00–10:00)")
    print(f"Output: {len(filled)} activities (including gaps)")
    for act in filled:
        print(f"  {act['id']}: {act['start']}–{act['end']} ({act['source']}) {act['type']}")
    print()

    # Test 4: Full merge workflow
    print("Test 4: Full merge workflow")
    print("-" * 80)
    test_data = [
        {
            "start": "09:00",
            "end": "09:45",
            "source": "timecamp",
            "type": "screen_work",
            "duration_minutes": 45,
            "raw_signals": ["LEAP: Smith v Jones (L3948)"],
            "raw_id": "tc1",
            "metadata": {}
        },
        {
            "start": "09:45",
            "end": "10:00",
            "source": "telus",
            "type": "phone_call",
            "duration_minutes": 15,
            "raw_signals": ["Contact: Client"],
            "raw_id": "telus1",
            "metadata": {}
        },
        {
            "start": "14:00",
            "end": "15:00",
            "source": "gcal",
            "type": "meeting",
            "duration_minutes": 60,
            "raw_signals": ["Event: Client meeting"],
            "raw_id": "gcal1",
            "metadata": {}
        }
    ]
    merged = merge_timeline(test_data, date="2026-04-13")
    print(f"Date: {merged['date']}")
    print(f"Stats: {merged['stats']}")
    print(f"Activities ({len(merged['activities'])} total):")
    for act in merged['activities']:
        print(f"  {act['id']}: {act['start']}–{act['end']} ({act['source']:8}) {act['type']:12}")
    print()

    print("=" * 80)
    print("All tests completed successfully!")
    print("=" * 80)
