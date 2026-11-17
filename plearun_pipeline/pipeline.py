"""End-to-end evidence verification pipeline."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from plearun_pipeline.models import Finding
from plearun_pipeline.record_loaders import EvidenceRepository
from plearun_pipeline.report_parser import extract_claims_from_report
from plearun_pipeline.clock_sync import ClockSynchronizer
from plearun_pipeline.verifier import EvidenceVerifier
from plearun_pipeline.quote_validator import QuoteValidator
from plearun_pipeline.findings_exporter import export_findings


class VerificationPipeline:
    """Orchestrates end-to-end evidence loading, clock alignment, claim verification,
    quote validation, and JSON export.
    """

    def __init__(self, report_path: Path, records_dir: Path) -> None:
        self.report_path = Path(report_path)
        self.records_dir = Path(records_dir)

    def run(self) -> list[Finding]:
        """Execute verification workflow and return validated findings."""
        if not self.report_path.exists():
            raise FileNotFoundError(f"Report file not found: {self.report_path}")
        if not self.records_dir.exists():
            raise FileNotFoundError(f"Records directory not found: {self.records_dir}")

        # 1. Load report text and extract factual claims
        report_text = self.report_path.read_text(encoding="utf-8")
        claims = extract_claims_from_report(report_text)

        # 2. Ingest and parse evidence repository
        repo = EvidenceRepository(self.records_dir)

        # 3. Synchronize clocks across devices via shared anchor events
        synchronizer = ClockSynchronizer(repo)

        # 4. Evaluate claims against evidence
        verifier = EvidenceVerifier(repo, synchronizer)
        raw_findings = [verifier.verify_claim(c) for c in claims]

        # 5. Enforce quote validation guard (downgrade to not_settled if invalid)
        validator = QuoteValidator(repo)
        validated_findings = [validator.validate_finding(f) for f in raw_findings]

        return validated_findings

    def run_to_json(self, indent: int = 2) -> str:
        """Run pipeline and return formatted JSON string."""
        findings = self.run()
        return export_findings(findings, indent=indent)
