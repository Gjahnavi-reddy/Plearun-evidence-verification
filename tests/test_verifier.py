"""Unit tests for verifier in plearun_pipeline."""
import unittest
from pathlib import Path
from plearun_pipeline.record_loaders import EvidenceRepository
from plearun_pipeline.clock_sync import ClockSynchronizer
from plearun_pipeline.report_parser import extract_claims_from_report
from plearun_pipeline.verifier import EvidenceVerifier
from plearun_pipeline.models import FindingType

ROOT = Path(__file__).parent.parent
RECORDS_DIR = ROOT / "records"
SAMPLE_REPORT = ROOT / "reports" / "report_fictional_02.txt"


class TestVerifier(unittest.TestCase):
    def setUp(self):
        self.repo = EvidenceRepository(RECORDS_DIR)
        self.sync = ClockSynchronizer(self.repo)
        self.verifier = EvidenceVerifier(self.repo, self.sync)
        report_text = SAMPLE_REPORT.read_text(encoding="utf-8")
        self.claims = extract_claims_from_report(report_text)

    def test_verify_all_fictional_02_claims(self):
        # 5 claims
        findings = [self.verifier.verify_claim(c) for c in self.claims]
        self.assertEqual(len(findings), 5)

        # Claim 1: Speed observation -> conflict with camera row 18 (CAM-07 clocked 62 mph)
        self.assertEqual(findings[0].finding, FindingType.CONFLICT)
        self.assertEqual(findings[0].cite.file, "camera_log.csv")
        self.assertEqual(findings[0].cite.row, 18)

        # Claim 2: Vehicle stop -> match with notes row 4 (Stopped at lot ~21:16,21:16)
        self.assertEqual(findings[1].finding, FindingType.MATCH)
        self.assertEqual(findings[1].cite.file, "notes_cp1252.csv")
        self.assertEqual(findings[1].cite.row, 4)

        # Claim 3: 911 call -> conflict with dispatch row 9 (logged at 21:10:19 vs 21:11)
        self.assertEqual(findings[2].finding, FindingType.CONFLICT)
        self.assertEqual(findings[2].cite.file, "dispatch.json")

        # Claim 4: Unit on scene roughly 2 min after stop -> match with dispatch row 14
        self.assertEqual(findings[3].finding, FindingType.MATCH)
        self.assertEqual(findings[3].cite.file, "dispatch.json")

        # Claim 5: Only car in the lane -> not_checkable
        self.assertEqual(findings[4].finding, FindingType.NOT_CHECKABLE)


if __name__ == "__main__":
    unittest.main()
