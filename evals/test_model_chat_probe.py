import unittest

from evals import model_chat_probe


class ModelChatProbeTest(unittest.TestCase):
    def test_formats_saved_benchmark_score_for_flash_lite(self):
        score = model_chat_probe.benchmark_summary(
            "google/gemini-3.5-flash-lite"
        )

        self.assertEqual(
            score,
            "contract 30/30 | p50 3.41s | p95 4.20s | cost $0.10707 / 30 calls",
        )


if __name__ == "__main__":
    unittest.main()
