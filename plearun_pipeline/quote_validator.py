"""Strict quotation verification and citation validation guard."""
from __future__ import annotations

import logging
from typing import Optional

from plearun_pipeline.models import Finding, FindingType
from plearun_pipeline.record_loaders import EvidenceRepository

logger = logging.getLogger(__name__)


class QuoteValidator:
    """Enforces Rule 1 of the assignment specification:
    
    "Every match or conflict must cite a real row, and your code must verify
     the quote is an exact substring of the raw text of that row before the
     finding is written. Otherwise downgrade to not_settled."
     
    "cite and quote are required for match and conflict, and must be omitted
     for the other two."
    """

    def __init__(self, repo: EvidenceRepository) -> None:
        self.repo = repo

    def validate_finding(self, finding: Finding) -> Finding:
        """Validate citation row and exact quotation substring. Downgrades if invalid."""
        # Non-assertive findings must not include cite or quote
        if finding.finding in (FindingType.NOT_SETTLED, FindingType.NOT_CHECKABLE):
            finding.cite = None
            finding.quote = None
            return finding

        # Match and conflict require cite and quote
        if not finding.cite or not finding.quote:
            logger.warning(
                "Finding '%s' marked as %s missing cite or quote. Downgrading to not_settled.",
                finding.claim,
                finding.finding.value,
            )
            return Finding(
                claim=finding.claim,
                finding=FindingType.NOT_SETTLED,
            )

        filename = finding.cite.file
        row_num = finding.cite.row
        quote = finding.quote

        # Verify file exists in repository
        raw_record = self.repo.raw_files.get(filename)
        if not raw_record:
            logger.warning("Cited file '%s' does not exist in records. Downgrading.", filename)
            return Finding(
                claim=finding.claim,
                finding=FindingType.NOT_SETTLED,
            )

        # Verify row number is within bounds
        raw_line = raw_record.get_line(row_num)
        if raw_line is None:
            logger.warning(
                "Cited row %d in file '%s' out of bounds (total lines %d). Downgrading.",
                row_num,
                filename,
                len(raw_record.raw_lines),
            )
            return Finding(
                claim=finding.claim,
                finding=FindingType.NOT_SETTLED,
            )

        # Enforce exact substring check against raw text of that row
        if quote not in raw_line:
            logger.warning(
                "Quote '%s' is NOT an exact substring of row %d in '%s': '%s'. Downgrading to not_settled.",
                quote,
                row_num,
                filename,
                raw_line,
            )
            return Finding(
                claim=finding.claim,
                finding=FindingType.NOT_SETTLED,
            )

        # Validated successfully
        return finding
