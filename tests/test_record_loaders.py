"""Unit tests for record_loaders in plearun_pipeline."""
import os
import unittest
from pathlib import Path
from plearun_pipeline.record_loaders import (
    read_file_raw,
    parse_timestamp,
    parse_vtt_timestamp,
    EvidenceRepository,
    DEFAULT_TIMEZONE,
)

ROOT = Path(__file__).parent.parent
RECORDS_DIR = ROOT / "records"


class TestRecordLoaders(unittest.TestCase):
    def test_read_camera_log_raw_and_bom(self):
        raw = read_file_raw(RECORDS_DIR / "camera_log.csv")
        self.assertEqual(raw.encoding, "utf-8-sig")
        self.assertTrue(raw.raw_lines[0].startswith("#PLEARUN"))
        self.assertEqual(raw.raw_lines[1], "timestamp,device,speed_mph,zone_mph")
        self.assertEqual(raw.raw_lines[2], "1772502579000,CAM-07,42,45")

    def test_read_notes_cp1252(self):
        raw = read_file_raw(RECORDS_DIR / "notes_cp1252.csv")
        self.assertEqual(raw.encoding, "cp1252")
        self.assertEqual(len(raw.raw_lines), 4)
        self.assertIn("Vehicle observed, plate unknown", raw.raw_lines[1])

    def test_parse_timestamp_formats(self):
        # Epoch ms
        dt_epoch = parse_timestamp(1772502579000)
        self.assertIsNotNone(dt_epoch)
        self.assertEqual(dt_epoch.hour, 20)
        self.assertEqual(dt_epoch.minute, 49)

        # ISO with offset
        dt_iso = parse_timestamp("2026-03-02T20:51:06-05:00")
        self.assertIsNotNone(dt_iso)
        self.assertEqual(dt_iso.hour, 20)
        self.assertEqual(dt_iso.minute, 51)

        # Naive datetime
        dt_naive = parse_timestamp("2026-03-02 21:10:19")
        self.assertIsNotNone(dt_naive)
        self.assertEqual(dt_naive.hour, 21)
        self.assertEqual(dt_naive.minute, 10)
        self.assertEqual(dt_naive.second, 19)

        # HH:MM
        dt_hm = parse_timestamp("21:16")
        self.assertIsNotNone(dt_hm)
        self.assertEqual(dt_hm.hour, 21)
        self.assertEqual(dt_hm.minute, 16)

    def test_parse_vtt_timestamp(self):
        self.assertAlmostEqual(parse_vtt_timestamp("00:00:03.500"), 3.5)
        self.assertAlmostEqual(parse_vtt_timestamp("00:01:10.000"), 70.0)

    def test_evidence_repository_loading(self):
        repo = EvidenceRepository(RECORDS_DIR)
        self.assertIn("camera_log.csv", repo.raw_files)
        self.assertIn("dispatch.json", repo.raw_files)
        self.assertIn("notes_cp1252.csv", repo.raw_files)
        self.assertIn("bodycam_transcript.vtt", repo.raw_files)

        # Verify camera items
        cam_items = repo.get_items_by_file("camera_log.csv")
        self.assertEqual(len(cam_items), 34)  # 36 lines minus marker line and header
        first_cam = cam_items[0]
        self.assertEqual(first_cam.row, 3)
        self.assertEqual(first_cam.device, "CAM-07")
        self.assertEqual(first_cam.payload["speed_mph"], 42)

        # Verify dispatch items
        dispatch_items = repo.get_items_by_file("dispatch.json")
        self.assertEqual(len(dispatch_items), 3)

        # Verify notes items
        notes_items = repo.get_items_by_file("notes_cp1252.csv")
        self.assertEqual(len(notes_items), 3)
        self.assertEqual(notes_items[0].row, 2)

        # Verify vtt items
        vtt_items = repo.get_items_by_file("bodycam_transcript.vtt")
        self.assertEqual(len(vtt_items), 3)
        self.assertEqual(vtt_items[0].device, "Officer Lee")
        self.assertEqual(vtt_items[0].payload["dialogue"], "58 in a 45.")


if __name__ == "__main__":
    unittest.main()
