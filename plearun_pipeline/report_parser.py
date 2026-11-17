"""Parser for extracting verifiable factual claims from incident reports."""
from __future__ import annotations

import re
from datetime import datetime, timezone, timedelta
from typing import Optional

from plearun_pipeline.models import Claim

DEFAULT_TIMEZONE = timezone(timedelta(hours=-5))


def extract_incident_date(text: str) -> str:
    """Extract incident date in YYYY-MM-DD format if present in text, else fallback to 2026-03-02."""
    m = re.search(r"\b(\d{4}-\d{2}-\d{2})\b", text)
    if m:
        return m.group(1)
    return "2026-03-02"


def is_header_or_metadata(sentence: str) -> bool:
    """Detect non-factual header or metadata banner lines."""
    s = sentence.strip()
    if re.search(r"SYNTHETIC\s*-\s*FICTIONAL\s*CASE", s, re.IGNORECASE):
        return True
    if re.search(r"^incident\s+\d{4}-\d{2}-\d{2}", s, re.IGNORECASE):
        return True
    if re.search(r"^INCIDENT\s*REPORT", s, re.IGNORECASE) and len(s.split()) <= 4:
        return True
    return False


def split_report_into_claims(report_text: str) -> list[str]:
    """Split report text into individual claim sentences, excluding header banners."""
    lines = [l.strip() for l in report_text.splitlines() if l.strip()]
    raw_sentences: list[str] = []

    for line in lines:
        # If the entire line is a synthetic header banner, skip the line
        if re.search(r"SYNTHETIC\s*-\s*FICTIONAL\s*CASE", line, re.IGNORECASE):
            continue

        # Split line by sentence boundaries (. ! ?) followed by whitespace and uppercase
        # Avoid splitting on abbreviations like e.g., i.e., or numbers
        parts = re.split(r"(?<=[.!?])\s+(?=[A-Z])", line)
        for part in parts:
            p = part.strip()
            if p and not is_header_or_metadata(p):
                raw_sentences.append(p)

    return raw_sentences


def parse_claim(claim_text: str, incident_date: str = "2026-03-02") -> Claim:
    """Extract structured parameters (time, speed, zone, event type) from a claim sentence."""
    text_lower = claim_text.lower()
    claim_type = "general"
    target_time: Optional[datetime] = None
    target_speed: Optional[int] = None
    target_zone: Optional[int] = None
    metadata: dict[str, Any] = {}

    # Extract wall-clock time if mentioned (e.g., at 21:14, around 21:16, at 21:11)
    m_time = re.search(r"\b(?:at|around|about)?\s*(\d{1,2}:\d{2})\b", claim_text)
    if m_time:
        t_str = m_time.group(1)
        h, m = (int(x) for x in t_str.split(":"))
        y, mon, d = (int(x) for x in incident_date.split("-"))
        target_time = datetime(y, mon, d, h, m, 0, tzinfo=DEFAULT_TIMEZONE)
        metadata["time_str"] = t_str

    # Extract speed (e.g., 58 mph)
    m_speed = re.search(r"(\d+)\s*mph", text_lower)
    if m_speed:
        target_speed = int(m_speed.group(1))

    # Extract posted zone (e.g., posted 45 zone, 45 zone)
    m_zone = re.search(r"(?:posted\s*)?(\d+)\s*zone", text_lower)
    if m_zone:
        target_zone = int(m_zone.group(1))

    # Extract relative timing (e.g., roughly 2 minutes after the stop)
    m_rel = re.search(r"(\d+)\s*minutes?\s*after", text_lower)
    if m_rel:
        metadata["relative_minutes"] = int(m_rel.group(1))

    # Determine claim category
    if "on scene" in text_lower or "arrived" in text_lower or "unit on scene" in text_lower:
        claim_type = "unit_arrival"
    elif "mph" in text_lower or "speed" in text_lower:
        claim_type = "speed_observation"
    elif "stop" in text_lower or "lot" in text_lower or "pulled into" in text_lower:
        claim_type = "vehicle_stop"
    elif "911" in text_lower:
        claim_type = "call_911"
    elif "only car" in text_lower or "lane" in text_lower or "traffic" in text_lower:
        claim_type = "traffic_count"

    # Unique ID based on hash or index
    claim_id = f"claim_{abs(hash(claim_text)) % 100000}"

    return Claim(
        claim_id=claim_id,
        claim_text=claim_text,
        claim_type=claim_type,
        target_time=target_time,
        target_speed=target_speed,
        target_zone=target_zone,
        metadata=metadata,
    )


def extract_claims_from_report(report_text: str) -> list[Claim]:
    """Parse all verifiable claims from full report text."""
    date_str = extract_incident_date(report_text)
    claim_strings = split_report_into_claims(report_text)
    return [parse_claim(s, incident_date=date_str) for s in claim_strings]
