from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.services.tts_asset_selector import TtsAssetSelector


class TtsAssetSelectorTest(unittest.TestCase):
    def test_catalog_has_nine_current_question_assets_and_one_stale_core_asset(self):
        path = BACKEND_ROOT.parent / "configs" / "tts" / "tts_template_catalog.json"
        templates = json.loads(path.read_text(encoding="utf-8"))["templates"]
        questioners = [item for item in templates if item["speakerRole"] == "questioner"]
        coaches = [item for item in templates if item["speakerRole"] == "coach"]

        self.assertEqual(len(templates), 100)
        self.assertEqual(len(questioners), 10)
        self.assertEqual(len(coaches), 90)
        self.assertEqual({item["issueCode"] for item in coaches}, {"SPEED_FAST", "LONG_SILENCE", "FILLER_REPEAT", "LOW_VOLUME", "TERMINAL_INTONATION"})
        current_questioners = [item for item in questioners if item["questionId"] != "preset-04"]
        stale_core = next(item for item in questioners if item["questionId"] == "preset-04")
        self.assertEqual(len(current_questioners), 9)
        self.assertTrue(all(
            item["qcStatus"] == "accepted"
            and item["isPrimary"] is True
            and item["audioAssetId"] is not None
            for item in current_questioners
        ))
        self.assertEqual(stale_core["displayText"], "프로젝트 개발 중 발생한 문제를 어떻게 해결했나요?")
        self.assertEqual(stale_core["qcStatus"], "draft")
        self.assertFalse(stale_core["isPrimary"])
        self.assertIsNone(stale_core["audioAssetId"])
        self.assertTrue(all(item["qcStatus"] == "draft" and item["audioAssetId"] is None for item in coaches))

    def test_draft_template_returns_text_fallback(self):
        selector = TtsAssetSelector(BACKEND_ROOT.parent / "configs" / "tts" / "tts_template_catalog.json")
        item = selector.select_coach(["SPEED_FAST"])[0]
        self.assertEqual(item["mode"], "text")
        self.assertIsNone(item["audioAssetId"])

    def test_local_reviewed_low_volume_template_keeps_text_fallback_with_spoken_text(self):
        selector = TtsAssetSelector(BACKEND_ROOT.parent / "configs" / "tts" / "tts_template_catalog.json")

        item = selector.select_coach(["LOW_VOLUME"])[0]

        self.assertEqual(item["mode"], "text")
        self.assertIsNone(item["audioAssetId"])
        self.assertEqual(
            item["displayText"],
            "문장 끝까지 일정한 목소리로 전달해 보세요. 다음 답변에서도 이 리듬을 이어 가 보세요.",
        )

    def test_manifest_records_two_local_reviewed_coach_assets_pending_private_upload(self):
        path = BACKEND_ROOT.parent / "configs" / "tts" / "tts_asset_manifest.json"
        manifest = json.loads(path.read_text(encoding="utf-8"))

        coach = manifest["coach"]
        self.assertEqual(coach["speaker"], "candidate_03_coach")
        self.assertEqual(coach["templateStatus"], "local_reviewed_pending_private_upload")
        self.assertEqual([item["templateId"] for item in coach["templates"]], ["coach-low-volume-01", "coach-low-volume-02"])
        self.assertTrue(all(item["audioAssetId"] is None for item in coach["templates"]))

    def test_questioner_catalog_matches_the_ten_visible_preset_questions_after_private_upload(self):
        catalog_path = BACKEND_ROOT.parent / "configs" / "tts" / "tts_template_catalog.json"
        manifest_path = BACKEND_ROOT.parent / "configs" / "tts" / "tts_asset_manifest.json"
        templates = json.loads(catalog_path.read_text(encoding="utf-8"))["templates"]
        questioners = [item for item in templates if item["speakerRole"] == "questioner"]
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

        self.assertEqual(
            [item["questionId"] for item in questioners],
            [f"preset-{number:02d}" for number in range(1, 11)],
        )
        self.assertEqual(
            [item["displayText"] for item in questioners],
            [
                "자기소개를 해주세요.",
                "지원한 이유를 말씀해주세요.",
                "본인의 장점을 말씀해주세요.",
                "프로젝트 개발 중 발생한 문제를 어떻게 해결했나요?",
                "협업 중 갈등을 해결했던 경험을 말씀해주세요.",
                "실패 경험과 배운 점을 말씀해주세요.",
                "가장 기억에 남는 프로젝트를 소개해주세요.",
                "본인이 맡았던 역할을 설명해주세요.",
                "입사 후 어떤 개발자가 되고 싶은가요?",
                "마지막으로 하고 싶은 말을 말씀해주세요.",
            ],
        )
        self.assertEqual(sum(item["qcStatus"] == "accepted" for item in questioners), 9)
        self.assertEqual(sum(item["isPrimary"] is True for item in questioners), 9)
        self.assertEqual(
            [item["audioAssetId"] for item in questioners],
            [
                f"questioner-preset-{number:02d}-v1" if number != 4 else None
                for number in range(1, 11)
            ],
        )
        self.assertEqual(manifest["questioner"]["templateStatus"], "accepted_private_uploaded_with_stale_preset_04")
        stale_manifest = next(item for item in manifest["questioner"]["templates"] if item["questionId"] == "preset-04")
        self.assertEqual(stale_manifest["deploymentStatus"], "stale_text_do_not_use")
        selector = TtsAssetSelector(catalog_path)
        selected_assets = [
            selector.select_preset_question(f"preset-{number:02d}")
            for number in range(1, 11)
        ]
        self.assertEqual(
            [item["audioAssetId"] if item else None for item in selected_assets],
            [
                f"questioner-preset-{number:02d}-v1" if number != 4 else None
                for number in range(1, 11)
            ],
        )

    def test_accepted_primary_template_returns_audio_asset(self):
        catalog = {"templates": [{"templateId": "coach-1", "speakerRole": "coach", "issueCode": "SPEED_FAST", "displayText": "천천히 말해 보세요.", "qcStatus": "accepted", "isPrimary": True, "audioAssetId": "coach-speed-fast-01"}]}
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "catalog.json"
            path.write_text(json.dumps(catalog), encoding="utf-8")
            item = TtsAssetSelector(path).select_coach(["SPEED_FAST"])[0]
        self.assertEqual(item["mode"], "audio")
        self.assertEqual(item["audioAssetId"], "coach-speed-fast-01")

    def test_accepted_primary_preset_question_returns_audio_asset(self):
        catalog = {"templates": [{
            "templateId": "question-01",
            "questionId": "preset-01",
            "speakerRole": "questioner",
            "displayText": "자기소개를 해주세요.",
            "qcStatus": "accepted",
            "isPrimary": True,
            "audioAssetId": "questioner-preset-01-v1",
        }]}
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "catalog.json"
            path.write_text(json.dumps(catalog), encoding="utf-8")
            result = TtsAssetSelector(path).select_preset_question("preset-01")

        self.assertIsNotNone(result)
        self.assertEqual(result["mode"], "audio")
        self.assertEqual(result["audioAssetId"], "questioner-preset-01-v1")

    def test_draft_or_unknown_preset_question_is_not_an_audio_asset(self):
        catalog = {"templates": [{
            "templateId": "question-01",
            "questionId": "preset-01",
            "speakerRole": "questioner",
            "displayText": "자기소개를 해주세요.",
            "qcStatus": "draft",
            "isPrimary": False,
            "audioAssetId": None,
        }]}
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "catalog.json"
            path.write_text(json.dumps(catalog), encoding="utf-8")
            selector = TtsAssetSelector(path)

            self.assertIsNone(selector.select_preset_question("preset-01"))
            self.assertIsNone(selector.select_preset_question("preset-11"))
