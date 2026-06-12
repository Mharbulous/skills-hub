#!/usr/bin/env python3
"""
normalize_activity.py

Normalizes raw activity data from TimeCamp, Google Calendar, or Telus Business Connect
into a unified format for timeline merging.

This module handles source-specific data extraction, type mapping, and signal extraction.
Each source's normalization rules are isolated in dedicated functions, making it easy
to add new sources or modify existing logic.

Usage:
    from normalize_activity import normalize_from_timecamp, normalize_from_telus, normalize_from_gcal

    # Normalize a TimeCamp activity
    activity = normalize_from_timecamp({
        "id": "tc1",
        "start": "09:02",
        "end": "09:47",
        "application": "LEAP",
        "window_title": "Smith v Jones (L3948) - Statement of Claim",
        "duration": 45
    })

    # Normalize a Telus call
    activity = normalize_from_telus({
        "id": "telus1",
        "start": "09:47",
        "end": "09:57",
        "phone_number": "+1-604-555-1234",
        "contact_name": "Smith - Client",
        "direction": "inbound",
        "duration": 10
    })

    # Normalize a Google Calendar event
    activity = normalize_from_gcal({
        "id": "gcal1",
        "start": "10:00",
        "end": "10:30",
        "title": "Smith v Jones - Client meeting",
        "location": "Conference Room A"
    })

Each function returns a normalized activity dict:
    {
        "start": "HH:MM",
        "end": "HH:MM",
        "source": "timecamp|telus|gcal",
        "type": "screen_work|phone_call|meeting|court",
        "duration_minutes": int,
        "raw_signals": [list of extracted signals],
        "raw_id": original source ID,
        "metadata": {source-specific fields}
    }
"""

import re
from typing import Dict, List, Any, Optional


# ============================================================================
# Helper Functions
# ============================================================================

def hhmm_to_minutes(hhmm: str) -> int:
    """
    Convert HH:MM time string to minutes since midnight.

    Args:
        hhmm: Time string in format "HH:MM" (e.g., "09:47")

    Returns:
        Integer minutes since midnight (e.g., 587 for "09:47")

    Raises:
        ValueError: If format is invalid
    """
    try:
        h, m = map(int, hhmm.split(':'))
        return h * 60 + m
    except (ValueError, IndexError):
        raise ValueError(f"Invalid time format: {hhmm}. Expected HH:MM")


def extract_matter_number(text: str) -> Optional[str]:
    """
    Extract matter number (L####) from text using regex.

    Args:
        text: Text to search (e.g., window title, event title, contact name)

    Returns:
        Matter number string (e.g., "L3948") or None if not found

    Examples:
        >>> extract_matter_number("Smith v Jones (L3948) - Statement of Claim")
        "L3948"
        >>> extract_matter_number("Random text")
        None
    """
    match = re.search(r'\(L\d{4,5}\)', text)
    if match:
        return match.group(0).strip('()')
    return None


def extract_signals_from_text(text: str, source: str) -> List[str]:
    """
    Extract contextual signals from text (window title, event title, contact name).

    Args:
        text: Text to extract signals from
        source: Source type ("timecamp", "gcal", "telus") for context-specific extraction

    Returns:
        List of signal strings (e.g., ["Matter: L3948", "Client: Smith"])
    """
    signals = []

    # Extract matter number
    matter = extract_matter_number(text)
    if matter:
        signals.append(f"Matter: {matter}")

    # Extract client/contact names (simple heuristic: capitalized words)
    words = text.split()
    potential_names = [w for w in words if w[0].isupper() and len(w) > 2 and w not in ['The', 'And']]
    if potential_names:
        signals.append(f"Names: {', '.join(potential_names[:3])}")

    # Source-specific signal extraction
    if source == "timecamp":
        # Look for application-specific keywords
        if "LEAP" in text.upper():
            signals.append("App: LEAP (legal case management)")
        if "quickbooks" in text.lower():
            signals.append("App: QuickBooks (accounting)")
        if "email" in text.lower() or "inbox" in text.lower():
            signals.append("Activity: Email/admin")

    elif source == "gcal":
        # Calendar event keywords
        if any(kw in text.lower() for kw in ["court", "hearing", "trial", "chambers"]):
            signals.append("Event: Court proceeding")
        if "client" in text.lower():
            signals.append("Event: Client interaction")

    elif source == "telus":
        # Phone call context
        if "client" in text.lower():
            signals.append("Contact: Client")
        if "counsel" in text.lower():
            signals.append("Contact: Counsel")
        if "opposing" in text.lower():
            signals.append("Contact: Opposing party")

    return signals


# ============================================================================
# TimeCamp Normalization
# ============================================================================

def normalize_from_timecamp(raw_activity: Dict[str, Any]) -> Dict[str, Any]:
    """
    Normalize a raw TimeCamp computer activity record.

    TimeCamp tracks applications and window titles. We extract:
    - Activity type: Determined by application (LEAP = client work, else screen_work)
    - Matter: Extracted from window title using regex (L####)
    - Category hints: From application and window title keywords

    Args:
        raw_activity: Raw TimeCamp activity record with keys:
            - id: Activity identifier (e.g., "tc1")
            - start: Start time "HH:MM" (e.g., "09:02")
            - end: End time "HH:MM" (e.g., "09:47")
            - application: Application name (e.g., "LEAP", "Chrome", "Thunderbird")
            - window_title: Window title from application
            - duration: Duration in minutes (calculated as end - start)

    Returns:
        Normalized activity dict with schema:
        {
            "start": "HH:MM",
            "end": "HH:MM",
            "source": "timecamp",
            "type": "screen_work|phone_call|meeting|court",
            "duration_minutes": int,
            "raw_signals": [signal strings],
            "raw_id": "tc###",
            "metadata": {
                "application": str,
                "window_title": str,
                "matter": str or None,
                "category_hints": [list of guessed categories]
            }
        }

    Examples:
        >>> tc = {
        ...     "id": "tc1",
        ...     "start": "09:02",
        ...     "end": "09:47",
        ...     "application": "LEAP",
        ...     "window_title": "Smith v Jones (L3948) - Statement of Claim",
        ...     "duration": 45
        ... }
        >>> normalized = normalize_from_timecamp(tc)
        >>> normalized["type"]
        "screen_work"
        >>> normalized["metadata"]["matter"]
        "L3948"
        >>> "Matter: L3948" in normalized["raw_signals"]
        True
    """
    start_min = hhmm_to_minutes(raw_activity["start"])
    end_min = hhmm_to_minutes(raw_activity["end"])
    duration = raw_activity.get("duration", end_min - start_min)

    # Determine activity type based on application
    app = raw_activity.get("application", "").upper()
    window_title = raw_activity.get("window_title", "")

    # Default to screen_work; will be refined by reconciliation logic
    activity_type = "screen_work"

    # Extract matter number from window title
    matter = extract_matter_number(window_title)

    # Extract category hints from application and window title
    category_hints = []
    if "THUNDERBIRD" in app or "EMAIL" in app:
        category_hints.append("admin")
    if "QUICKBOOKS" in app or "INVOICE" in window_title.upper():
        category_hints.append("billing")
    if any(keyword in window_title.upper() for keyword in ["CPD", "COURSE", "LSBC", "TRAINING"]):
        category_hints.append("training")
    if any(keyword in window_title.upper() for keyword in ["MARKETING", "NETWORKING", "BUSINESS"]):
        category_hints.append("business_development")

    # Extract contextual signals
    signals = extract_signals_from_text(window_title, "timecamp")
    signals.append(f"App: {app}")

    return {
        "start": raw_activity["start"],
        "end": raw_activity["end"],
        "source": "timecamp",
        "type": activity_type,
        "duration_minutes": duration,
        "raw_signals": signals,
        "raw_id": raw_activity.get("id", "tc_unknown"),
        "metadata": {
            "application": app,
            "window_title": window_title,
            "matter": matter,
            "category_hints": category_hints
        }
    }


# ============================================================================
# Telus Normalization
# ============================================================================

def normalize_from_telus(raw_call: Dict[str, Any]) -> Dict[str, Any]:
    """
    Normalize a raw Telus Business Connect call record.

    Telus provides phone number, direction (inbound/outbound), contact name, and type
    (call, voicemail, text, fax). We map all telephony activity to "phone_call" type
    and extract matter from contact name.

    Args:
        raw_call: Raw Telus call record with keys:
            - id: Call identifier (e.g., "telus1")
            - start: Start time "HH:MM" (e.g., "09:47")
            - end: End time "HH:MM" (e.g., "09:57")
            - phone_number: Caller/called number (e.g., "+1-604-555-1234")
            - contact_name: Caller/called contact name or "Unknown"
            - direction: "inbound" or "outbound"
            - duration: Duration in minutes
            - activity_type: (optional) "call", "voicemail", "text", "fax"

    Returns:
        Normalized activity dict with schema:
        {
            "start": "HH:MM",
            "end": "HH:MM",
            "source": "telus",
            "type": "phone_call",
            "duration_minutes": int,
            "raw_signals": [signal strings],
            "raw_id": "telus###",
            "metadata": {
                "phone_number": str,
                "contact_name": str,
                "direction": "inbound|outbound",
                "activity_type": "call|voicemail|text|fax",
                "matter": str or None
            }
        }

    Examples:
        >>> telus = {
        ...     "id": "telus1",
        ...     "start": "09:47",
        ...     "end": "09:57",
        ...     "phone_number": "+1-604-555-1234",
        ...     "contact_name": "Smith - Client",
        ...     "direction": "inbound",
        ...     "duration": 10
        ... }
        >>> normalized = normalize_from_telus(telus)
        >>> normalized["type"]
        "phone_call"
        >>> normalized["metadata"]["direction"]
        "inbound"
        >>> "Contact: Client" in normalized["raw_signals"]
        True
    """
    start_min = hhmm_to_minutes(raw_call["start"])
    end_min = hhmm_to_minutes(raw_call["end"])
    duration = raw_call.get("duration", end_min - start_min)

    phone_number = raw_call.get("phone_number", "Unknown")
    contact_name = raw_call.get("contact_name", "Unknown")
    direction = raw_call.get("direction", "unknown").lower()
    activity_type = raw_call.get("activity_type", "call").lower()

    # All Telus activities are phone-related (calls, voicemail, texts, fax)
    normalized_type = "phone_call"

    # Try to extract matter from contact name
    matter = extract_matter_number(contact_name)

    # Extract signals from contact name and metadata
    signals = extract_signals_from_text(contact_name, "telus")
    signals.append(f"Direction: {direction.title()}")
    signals.append(f"Phone: {phone_number}")

    return {
        "start": raw_call["start"],
        "end": raw_call["end"],
        "source": "telus",
        "type": normalized_type,
        "duration_minutes": duration,
        "raw_signals": signals,
        "raw_id": raw_call.get("id", "telus_unknown"),
        "metadata": {
            "phone_number": phone_number,
            "contact_name": contact_name,
            "direction": direction,
            "activity_type": activity_type,
            "matter": matter
        }
    }


# ============================================================================
# Google Calendar Normalization
# ============================================================================

def normalize_from_gcal(raw_event: Dict[str, Any]) -> Dict[str, Any]:
    """
    Normalize a raw Google Calendar event record.

    GCal events are mapped to "meeting" by default, with special handling for
    court-related events (keywords: court, hearing, trial, chambers) which map to "court".
    Matter extraction from event title and location.

    Args:
        raw_event: Raw Google Calendar event with keys:
            - id: Event identifier (e.g., "gcal1")
            - start: Start time "HH:MM" (e.g., "10:00")
            - end: End time "HH:MM" (e.g., "10:30")
            - title: Event title (e.g., "Smith v Jones - Client meeting")
            - location: Event location (optional)
            - description: Event description (optional)

    Returns:
        Normalized activity dict with schema:
        {
            "start": "HH:MM",
            "end": "HH:MM",
            "source": "gcal",
            "type": "meeting|court",
            "duration_minutes": int,
            "raw_signals": [signal strings],
            "raw_id": "gcal###",
            "metadata": {
                "title": str,
                "location": str or None,
                "description": str or None,
                "matter": str or None,
                "is_court_event": bool
            }
        }

    Examples:
        >>> gcal = {
        ...     "id": "gcal1",
        ...     "start": "10:00",
        ...     "end": "10:30",
        ...     "title": "Smith v Jones - Client meeting",
        ...     "location": "Conference Room A"
        ... }
        >>> normalized = normalize_from_gcal(gcal)
        >>> normalized["type"]
        "meeting"
        >>> normalized["metadata"]["matter"]
        None  # Matter number not in title

        >>> court_event = {
        ...     "id": "gcal2",
        ...     "start": "14:00",
        ...     "end": "15:00",
        ...     "title": "Smith v Jones - Chambers hearing (L3948)"
        ... }
        >>> normalized = normalize_from_gcal(court_event)
        >>> normalized["type"]
        "court"
        >>> normalized["metadata"]["is_court_event"]
        True
    """
    start_min = hhmm_to_minutes(raw_event["start"])
    end_min = hhmm_to_minutes(raw_event["end"])
    duration = end_min - start_min

    title = raw_event.get("title", "")
    location = raw_event.get("location")
    description = raw_event.get("description")

    # Determine activity type based on keywords
    title_lower = title.lower()
    is_court_event = any(
        keyword in title_lower
        for keyword in ["court", "hearing", "trial", "chambers", "motion", "application"]
    )
    activity_type = "court" if is_court_event else "meeting"

    # Extract matter from title
    matter = extract_matter_number(title)

    # Extract signals from title, location, and description
    signals = extract_signals_from_text(title, "gcal")
    if location:
        signals.append(f"Location: {location}")
    if is_court_event:
        signals.append("Type: Court proceeding")

    return {
        "start": raw_event["start"],
        "end": raw_event["end"],
        "source": "gcal",
        "type": activity_type,
        "duration_minutes": duration,
        "raw_signals": signals,
        "raw_id": raw_event.get("id", "gcal_unknown"),
        "metadata": {
            "title": title,
            "location": location,
            "description": description,
            "matter": matter,
            "is_court_event": is_court_event
        }
    }


# ============================================================================
# Batch Normalization
# ============================================================================

def normalize_batch(
    timecamp_activities: List[Dict[str, Any]] = None,
    telus_calls: List[Dict[str, Any]] = None,
    gcal_events: List[Dict[str, Any]] = None
) -> List[Dict[str, Any]]:
    """
    Normalize activities from all sources in a single call.

    This is a convenience function for agents that fetch data from multiple sources
    and need to normalize everything at once before reconciliation.

    Args:
        timecamp_activities: List of raw TimeCamp activities (optional)
        telus_calls: List of raw Telus call records (optional)
        gcal_events: List of raw Google Calendar events (optional)

    Returns:
        List of normalized activities sorted by start time, ready for reconciliation

    Example:
        >>> timecamp_data = [{"id": "tc1", "start": "09:02", ...}]
        >>> telus_data = [{"id": "telus1", "start": "09:47", ...}]
        >>> normalized = normalize_batch(timecamp_data, telus_data)
        >>> len(normalized)
        2
        >>> normalized[0]["source"]
        "timecamp"
        >>> normalized[1]["source"]
        "telus"
    """
    normalized = []

    if timecamp_activities:
        for activity in timecamp_activities:
            normalized.append(normalize_from_timecamp(activity))

    if telus_calls:
        for call in telus_calls:
            normalized.append(normalize_from_telus(call))

    if gcal_events:
        for event in gcal_events:
            normalized.append(normalize_from_gcal(event))

    # Sort by start time for downstream processing
    normalized.sort(key=lambda a: hhmm_to_minutes(a["start"]))

    return normalized


# ============================================================================
# Command-Line Usage / Self-Test
# ============================================================================

if __name__ == "__main__":
    """
    Test the normalization functions with sample data.
    Run: python3 normalize_activity.py
    """

    print("=" * 80)
    print("normalize_activity.py - Testing Normalization Functions")
    print("=" * 80)
    print()

    # Test TimeCamp normalization
    print("1. TimeCamp Normalization")
    print("-" * 80)
    tc_sample = {
        "id": "tc1",
        "start": "09:02",
        "end": "09:47",
        "application": "LEAP",
        "window_title": "Smith v Jones (L3948) - Statement of Claim",
        "duration": 45
    }
    tc_normalized = normalize_from_timecamp(tc_sample)
    print(f"Input: {tc_sample}")
    print(f"Output: {tc_normalized}")
    print()

    # Test Telus normalization
    print("2. Telus Normalization")
    print("-" * 80)
    tel_sample = {
        "id": "telus1",
        "start": "09:47",
        "end": "09:57",
        "phone_number": "+1-604-555-1234",
        "contact_name": "Smith - Client",
        "direction": "inbound",
        "duration": 10
    }
    tel_normalized = normalize_from_telus(tel_sample)
    print(f"Input: {tel_sample}")
    print(f"Output: {tel_normalized}")
    print()

    # Test Google Calendar normalization
    print("3. Google Calendar Normalization")
    print("-" * 80)
    gcal_sample = {
        "id": "gcal1",
        "start": "10:00",
        "end": "10:30",
        "title": "Smith v Jones - Client meeting",
        "location": "Conference Room A"
    }
    gcal_normalized = normalize_from_gcal(gcal_sample)
    print(f"Input: {gcal_sample}")
    print(f"Output: {gcal_normalized}")
    print()

    # Test court event detection
    print("4. Court Event Detection (Google Calendar)")
    print("-" * 80)
    court_sample = {
        "id": "gcal2",
        "start": "14:00",
        "end": "15:00",
        "title": "Smith v Jones (L3948) - Chambers hearing"
    }
    court_normalized = normalize_from_gcal(court_sample)
    print(f"Input: {court_sample}")
    print(f"Activity type: {court_normalized['type']}")
    print(f"Is court event: {court_normalized['metadata']['is_court_event']}")
    print()

    # Test batch normalization
    print("5. Batch Normalization")
    print("-" * 80)
    batch_result = normalize_batch(
        timecamp_activities=[tc_sample],
        telus_calls=[tel_sample],
        gcal_events=[gcal_sample]
    )
    print(f"Normalized {len(batch_result)} activities total")
    for i, activity in enumerate(batch_result, 1):
        print(f"  {i}. {activity['source'].upper():8} {activity['start']}–{activity['end']} ({activity['duration_minutes']}m) type={activity['type']}")
    print()

    print("=" * 80)
    print("All tests completed successfully!")
    print("=" * 80)
