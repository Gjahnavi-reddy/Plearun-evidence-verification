"""Core data models for Plearun Evidence Verification Pipeline."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Optional


class FindingType(str, Enum):
    """Permitted finding categories as defined in assignment specification."""
    MATCH = "match"
    CONFLICT = "conflict"
    NOT_SETTLED = "not_settled"
    NOT_CHECKABLE = "not_checkable"


@dataclass(frozen=True)
class Citation:
    """Represents a citation to an exact row or cue in an evidence file."""
    file: str
    row: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "file": self.file,
            "row": self.row,
        }


@dataclass
class Finding:
    """A verified finding for a single claim.
    
    In accordance with the specification:
    - cite and quote are REQUIRED for 'match' and 'conflict'
    - cite and quote MUST BE OMITTED for 'not_settled' and 'not_checkable'
    """
    claim: str
    finding: FindingType
    cite: Optional[Citation] = None
    quote: Optional[str] = None

    def __post_init__(self) -> None:
        if isinstance(self.finding, str) and not isinstance(self.finding, FindingType):
            self.finding = FindingType(self.finding)

    def to_dict(self) -> dict[str, Any]:
        """Convert finding to standard JSON serializable dict."""
        data: dict[str, Any] = {
            "claim": self.claim,
            "finding": self.finding.value,
        }
        if self.finding in (FindingType.MATCH, FindingType.CONFLICT):
            if self.cite is None or self.quote is None:
                raise ValueError(
                    f"Findings of type '{self.finding.value}' must provide both 'cite' and 'quote'."
                )
            data["cite"] = self.cite.to_dict()
            data["quote"] = self.quote
        return data


@dataclass
class RawFileRecord:
    """Preserves raw line-by-line file content for verbatim substring validation."""
    filename: str
    filepath: Path
    raw_lines: list[str] = field(default_factory=list)
    encoding: str = "utf-8"

    def get_line(self, row_1_based: int) -> Optional[str]:
        """Fetch 1-based row text."""
        if 1 <= row_1_based <= len(self.raw_lines):
            return self.raw_lines[row_1_based - 1]
        return None


@dataclass
class RecordItem:
    """A parsed unit of machine or officer evidence."""
    file: str
    row: int
    raw_text: str
    timestamp: Optional[datetime] = None
    device: Optional[str] = None
    payload: dict[str, Any] = field(default_factory=dict)


@dataclass
class ClockOffset:
    """Estimated clock offset for an unsynchronized device relative to CAD reference time.
    
    adjusted_time = device_time + offset_seconds
    """
    device: str
    offset_seconds: float = 0.0
    confidence: float = 0.0
    is_aligned: bool = False
    reason: str = ""


@dataclass
class Claim:
    """A factual claim extracted from an incident report."""
    claim_id: str
    claim_text: str
    claim_type: str = "general"
    target_time: Optional[datetime] = None
    target_speed: Optional[int] = None
    target_zone: Optional[int] = None
    target_unit: Optional[str] = None
    metadata: dict[str, Any] = field(default_factory=dict)
