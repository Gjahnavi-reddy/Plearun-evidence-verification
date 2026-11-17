"""Unit tests for models in plearun_pipeline."""
import unittest
from pathlib import Path
from plearun_pipeline.models import (
    Finding,
    FindingType,
    Citation,
    RawFileRecord,
    RecordItem,
    ClockOffset,
    Claim,
)


class TestModels(unittest.TestCase):
    def test_finding_match_serialization(self):
        finding = Finding(
            claim="Vehicle stopped around 21:16.",
            finding=FindingType.MATCH,
            cite=Citation(file="notes_cp1252.csv", row=4),
            quote="Stopped at lot ~21:16,21:16",
        )
        d = finding.to_dict()
        self.assertEqual(d["claim"], "Vehicle stopped around 21:16.")
        self.assertEqual(d["finding"], "match")
        self.assertEqual(d["cite"], {"file": "notes_cp1252.csv", "row": 4})
        self.assertEqual(d["quote"], "Stopped at lot ~21:16,21:16")

    def test_finding_not_settled_omits_cite_and_quote(self):
        finding = Finding(
            claim="Ambiguous claim",
            finding=FindingType.NOT_SETTLED,
            cite=Citation(file="notes.csv", row=1),
            quote="something",
        )
        d = finding.to_dict()
        self.assertEqual(d["finding"], "not_settled")
        self.assertNotIn("cite", d)
        self.assertNotIn("quote", d)

    def test_finding_not_checkable_omits_cite_and_quote(self):
        finding = Finding(
            claim="Vehicle was the only car in the lane.",
            finding=FindingType.NOT_CHECKABLE,
        )
        d = finding.to_dict()
        self.assertEqual(d["finding"], "not_checkable")
        self.assertNotIn("cite", d)
        self.assertNotIn("quote", d)

    def test_finding_match_missing_cite_raises(self):
        finding = Finding(
            claim="Speed was 58.",
            finding=FindingType.MATCH,
            cite=None,
            quote="58",
        )
        with self.assertRaises(ValueError):
            finding.to_dict()

    def test_raw_file_record_get_line(self):
        rec = RawFileRecord(
            filename="dummy.txt",
            filepath=Path("dummy.txt"),
            raw_lines=["Line 1", "Line 2", "Line 3"],
        )
        self.assertEqual(rec.get_line(1), "Line 1")
        self.assertEqual(rec.get_line(3), "Line 3")
        self.assertIsNone(rec.get_line(0))
        self.assertIsNone(rec.get_line(4))


if __name__ == "__main__":
    unittest.main()
