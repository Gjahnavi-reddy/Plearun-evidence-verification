"""Unit tests for clock_sync in plearun_pipeline."""
import unittest
from pathlib import Path
from plearun_pipeline.record_loaders import EvidenceRepository
from plearun_pipeline.clock_sync import ClockSynchronizer

ROOT = Path(__file__).parent.parent
RECORDS_DIR = ROOT / "records"


class TestClockSync(unittest.TestCase):
    def setUp(self):
        self.repo = EvidenceRepository(RECORDS_DIR)
        self.sync = ClockSynchronizer(self.repo)

    def test_dispatch_clock_reference(self):
        self.assertTrue(self.sync.is_aligned("dispatch"))
        offset = self.sync.get_offset("dispatch")
        self.assertEqual(offset.offset_seconds, 0.0)

    def test_notes_clock_alignment(self):
        self.assertTrue(self.sync.is_aligned("notes"))
        offset = self.sync.get_offset("notes")
        self.assertGreaterEqual(offset.confidence, 0.8)

    def test_cam07_alignment_and_cam03_unaligned(self):
        # CAM-07 is aligned via stop event at 21:16:48
        self.assertTrue(self.sync.is_aligned("CAM-07"))
        # CAM-03 lacks anchor, must NOT be aligned
        self.assertFalse(self.sync.is_aligned("CAM-03"))

    def test_bodycam_wall_time(self):
        self.assertTrue(self.sync.is_aligned("bodycam"))
        # Cue 3 at 6 seconds should correspond to ~21:16
        t_cue3 = self.sync.get_bodycam_wall_time(6.0)
        self.assertIsNotNone(t_cue3)
        self.assertEqual(t_cue3.hour, 21)
        self.assertEqual(t_cue3.minute, 16)


if __name__ == "__main__":
    unittest.main()
