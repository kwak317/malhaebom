from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from evals import build_d11_injection_human_review as review_packet


class D11InjectionHumanReviewPacketTests(unittest.TestCase):
    def test_build_packet_leaves_human_decisions_blank(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            packet = review_packet.build_packet(
                ROOT / "evals" / "d11_injection_candidates.jsonl"
            )
            fake_root = Path(temp_dir)
            output_dir = fake_root / "local-results" / "packet"
            with patch.object(review_packet, "ROOT", fake_root):
                review_packet.write_packet(packet, output_dir)

            template = json.loads(
                (output_dir / "human-review.template.json").read_text(encoding="utf-8")
            )
            self.assertEqual(template["status"], "AWAITING_INDEPENDENT_HUMAN_REVIEW")
            self.assertEqual(len(template["reviews"]), 3)
            self.assertTrue(
                all(review["reviewer"] == "" for review in template["reviews"])
            )
            self.assertTrue(
                all(review["final_expected"] is None for review in template["reviews"])
            )
            self.assertIn("공식 평가셋", (output_dir / "REVIEW.md").read_text(encoding="utf-8"))

    def test_rejects_packet_output_outside_local_results(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            packet = review_packet.build_packet(
                ROOT / "evals" / "d11_injection_candidates.jsonl"
            )
            with self.assertRaisesRegex(ValueError, "local-results"):
                review_packet.write_packet(packet, Path(temp_dir) / "packet")


if __name__ == "__main__":
    unittest.main()
