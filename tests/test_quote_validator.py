"""Unit tests for quote_validator in plearun_pipeline."""
import unittest
from pathlib import Path
from plearun_pipeline.record_loaders import EvidenceRepository
from plearun_pipeline.quote_validator import QuoteValidator
from plearun_pipeline.models import Finding, FindingType, Citation

ROOT = Path(__file__).parent.parent
RECORDS_DIR = ROOT / "records"


class TestQuoteValidator(unittest.TestCase):
    def setUp(self):
        self.repo = EvidenceRepository(RECORDS_DIR)
        self.validator = QuoteValidator(self.repo)

    def test_valid_quote_preserved(self):
        finding = Finding(
            claim="The vehicle was observed.",
            finding=FindingType.MATCH,
            cite=Citation(file="notes_cp1252.csv", row=2),
            quote="Vehicle observed, plate unknown",
        )
        validated = self.validator.validate_finding(finding)
        self.assertEqual(validated.finding, FindingType.MATCH)
        self.assertIsNotNone(validated.cite)
        self.assertEqual(validated.quote, "Vehicle observed, plate unknown")

    def test_invalid_substring_downgraded_to_not_settled(self):
        finding = Finding(
            claim="The vehicle was observed.",
            finding=FindingType.MATCH,
            cite=Citation(file="notes_cp1252.csv", row=2),
            quote="Fabricated text not in line",
        )
        validated = self.validator.validate_finding(finding)
        self.assertEqual(validated.finding, FindingType.NOT_SETTLED)
        self.assertIsNone(validated.cite)
        self.assertIsNone(validated.quote)

    def test_invalid_row_number_downgraded(self):
        finding = Finding(
            claim="Something",
            finding=FindingType.CONFLICT,
            cite=Citation(file="notes_cp1252.csv", row=999),
            quote="Vehicle",
        )
        validated = self.validator.validate_finding(finding)
        self.assertEqual(validated.finding, FindingType.NOT_SETTLED)
        self.assertIsNone(validated.cite)

    def test_nonexistent_file_downgraded(self):
        finding = Finding(
            claim="Something",
            finding=FindingType.CONFLICT,
            cite=Citation(file="ghost_file.csv", row=1),
            quote="Something",
        )
        validated = self.validator.validate_finding(finding)
        self.assertEqual(validated.finding, FindingType.NOT_SETTLED)

    def test_not_settled_and_not_checkable_strip_cite_and_quote(self):
        finding = Finding(
            claim="Claim without proof",
            finding=FindingType.NOT_SETTLED,
            cite=Citation(file="notes_cp1252.csv", row=2),
            quote="Vehicle",
        )
        validated = self.validator.validate_finding(finding)
        self.assertEqual(validated.finding, FindingType.NOT_SETTLED)
        self.assertIsNone(validated.cite)
        self.assertIsNone(validated.quote)


if __name__ == "__main__":
    unittest.main()
