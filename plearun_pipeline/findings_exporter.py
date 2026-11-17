"""Exporter for schema-compliant verified findings JSON."""
from __future__ import annotations

import json
from typing import Any

from plearun_pipeline.models import Finding, FindingType


def export_findings(findings: list[Finding], indent: int = 2) -> str:
    """Format findings list into assignment-compliant JSON string.
    
    Format:
    {
      "findings": [
        {
          "claim": "<the claim as written in the report>",
          "finding": "match" | "conflict" | "not_settled" | "not_checkable",
          "cite": {"file": "<record file name>", "row": <row number or cue number>},
          "quote": "<text copied exactly from that row>"
        }
      ]
    }
    """
    serialized_findings = [f.to_dict() for f in findings]
    result: dict[str, Any] = {"findings": serialized_findings}
    return json.dumps(result, indent=indent, ensure_ascii=False)
