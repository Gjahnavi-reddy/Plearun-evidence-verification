"""Unit tests for report_parser in plearun_pipeline."""
import unittest
from pathlib import Path
from plearun_pipeline.report_parser import (
    extract_incident_date,
    split_report_into_claims,
    parse_claim,
    extract_claims_from_report,
)

ROOT = Path(__file__).parent.parent
SAMPLE_REPORT = ROOT / "reports" / "report_fictional_02.txt"


class TestReportParser(unittest.TestCase):
    def setUp(self):
        self.report_text = SAMPLE_REPORT.read_text(encoding="utf-8")

    def test_extract_incident_date(self):
        date_str = extract_incident_date(self.report_text)
        self.assertEqual(date_str, "2026-03-02")

    def test_split_report_into_claims(self):
        claims = split_report_into_claims(self.report_text)
        self.assertEqual(len(claims), 5)
        self.assertTrue(claims[0].startswith("Officer Lee first observed"))
        self.assertTrue(claims[1].startswith("The driver pulled into"))
        self.assertTrue(claims[2].startswith("A 911 call reporting"))
        self.assertTrue(claims[3].startswith("Dispatch records show"))
        self.assertTrue(claims[4].startswith("Officer Lee states"))

    def test_parse_claim_speed(self):
        c_text = "Officer Lee first observed the blue sedan at about 21:14 near mile marker 4, travelling 58 mph in a posted 45 zone."
        claim = parse_claim(c_text, incident_date="2026-03-02")
        self.assertEqual(claim.claim_type, "speed_observation")
        self.assertEqual(claim.target_speed, 58)
        self.assertEqual(claim.target_zone, 45)
        self.assertIsNotNone(claim.target_time)
        self.assertEqual(claim.target_time.hour, 21)
        self.assertEqual(claim.target_time.minute, 14)

    def test_parse_claim_stop(self):
        c_text = "The driver pulled into the Harbor Gas lot and stopped around 21:16."
        claim = parse_claim(c_text, incident_date="2026-03-02")
        self.assertEqual(claim.claim_type, "vehicle_stop")
        self.assertIsNotNone(claim.target_time)
        self.assertEqual(claim.target_time.minute, 16)

    def test_parse_claim_911(self):
        c_text = "A 911 call reporting the incident was logged at 21:11."
        claim = parse_claim(c_text, incident_date="2026-03-02")
        self.assertEqual(claim.claim_type, "call_911")
        self.assertIsNotNone(claim.target_time)
        self.assertEqual(claim.target_time.minute, 11)

    def test_parse_claim_unit_arrival(self):
        c_text = "Dispatch records show a unit on scene roughly 2 minutes after the stop."
        claim = parse_claim(c_text, incident_date="2026-03-02")
        self.assertEqual(claim.claim_type, "unit_arrival")
        self.assertEqual(claim.metadata.get("relative_minutes"), 2)

    def test_parse_claim_traffic_count(self):
        c_text = "Officer Lee states the vehicle was the only car in the lane."
        claim = parse_claim(c_text, incident_date="2026-03-02")
        self.assertEqual(claim.claim_type, "traffic_count")

    def test_extract_all_claims(self):
        claims = extract_claims_from_report(self.report_text)
        self.assertEqual(len(claims), 5)


if __name__ == "__main__":
    unittest.main()
