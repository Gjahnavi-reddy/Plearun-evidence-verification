"""End-to-end tests for the verified findings pipeline and CLI."""
import json
import subprocess
import sys
import unittest
from pathlib import Path
from plearun_pipeline.pipeline import VerificationPipeline
from plearun_pipeline.models import FindingType

ROOT = Path(__file__).parent.parent
REPORT_FILE = ROOT / "reports" / "report_fictional_02.txt"
RECORDS_DIR = ROOT / "records"


class TestPipelineE2E(unittest.TestCase):
    def test_pipeline_run_findings(self):
        pipeline = VerificationPipeline(REPORT_FILE, RECORDS_DIR)
        findings = pipeline.run()

        self.assertEqual(len(findings), 5)
        self.assertEqual(findings[0].finding, FindingType.CONFLICT)
        self.assertEqual(findings[1].finding, FindingType.MATCH)
        self.assertEqual(findings[2].finding, FindingType.CONFLICT)
        self.assertEqual(findings[3].finding, FindingType.MATCH)
        self.assertEqual(findings[4].finding, FindingType.NOT_CHECKABLE)

        # Enforce that every quote in every match/conflict is an exact substring of the cited line
        for f in findings:
            if f.finding in (FindingType.MATCH, FindingType.CONFLICT):
                self.assertIsNotNone(f.cite)
                self.assertIsNotNone(f.quote)
                target_file = RECORDS_DIR / f.cite.file
                self.assertTrue(target_file.exists())
                # Read using raw bytes and decode
                raw_lines = target_file.read_bytes().decode("utf-8", errors="replace").splitlines()
                cited_line = raw_lines[f.cite.row - 1]
                self.assertIn(f.quote, cited_line)
            else:
                self.assertIsNone(f.cite)
                self.assertIsNone(f.quote)

    def test_pipeline_run_to_json_valid_schema(self):
        pipeline = VerificationPipeline(REPORT_FILE, RECORDS_DIR)
        json_str = pipeline.run_to_json()
        data = json.loads(json_str)

        self.assertIn("findings", data)
        self.assertIsInstance(data["findings"], list)
        self.assertEqual(len(data["findings"]), 5)

        valid_finding_values = {"match", "conflict", "not_settled", "not_checkable"}
        for item in data["findings"]:
            self.assertIn("claim", item)
            self.assertIn("finding", item)
            self.assertIn(item["finding"], valid_finding_values)
            if item["finding"] in ("match", "conflict"):
                self.assertIn("cite", item)
                self.assertIn("file", item["cite"])
                self.assertIn("row", item["cite"])
                self.assertIsInstance(item["cite"]["row"], int)
                self.assertIn("quote", item)
                self.assertIsInstance(item["quote"], str)
            else:
                self.assertNotIn("cite", item)
                self.assertNotIn("quote", item)

    def test_cli_subprocess_invocation(self):
        cmd = [sys.executable, str(ROOT / "plearun_cli.py"), str(REPORT_FILE), str(RECORDS_DIR)]
        result = subprocess.run(cmd, capture_output=True, text=True)

        self.assertEqual(result.returncode, 0)
        data = json.loads(result.stdout)
        self.assertIn("findings", data)
        self.assertEqual(len(data["findings"]), 5)

    def test_cli_invalid_arguments_returns_error(self):
        cmd = [sys.executable, str(ROOT / "plearun_cli.py")]
        result = subprocess.run(cmd, capture_output=True, text=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Usage:", result.stderr)

    def test_cli_nonexistent_report_returns_error(self):
        cmd = [sys.executable, str(ROOT / "plearun_cli.py"), "nonexistent.txt", str(RECORDS_DIR)]
        result = subprocess.run(cmd, capture_output=True, text=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Error:", result.stderr)


if __name__ == "__main__":
    unittest.main()
