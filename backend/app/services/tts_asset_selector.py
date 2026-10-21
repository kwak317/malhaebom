from __future__ import annotations

import json
from pathlib import Path


class TtsAssetSelector:
    def __init__(self, catalog_path: Path | str) -> None:
        self.catalog_path = Path(catalog_path)

    def select_coach(self, issue_codes: list[str]) -> list[dict[str, object]]:
        catalog = json.loads(self.catalog_path.read_text(encoding="utf-8"))
        templates = catalog["templates"]
        selections: list[dict[str, object]] = []
        for code in issue_codes[:2]:
            candidates = [item for item in templates if item.get("issueCode") == code and item.get("speakerRole") == "coach"]
            primary = next((item for item in candidates if item.get("qcStatus") == "accepted" and item.get("isPrimary") and item.get("audioAssetId")), None)
            fallback = candidates[0] if candidates else None
            if primary:
                selections.append({"issueCode": code, "mode": "audio", "templateId": primary["templateId"], "audioAssetId": primary["audioAssetId"], "displayText": primary["displayText"]})
            elif fallback:
                selections.append({"issueCode": code, "mode": "text", "templateId": fallback["templateId"], "audioAssetId": None, "displayText": fallback["displayText"]})
        return selections

    def select_preset_question(self, question_id: str) -> dict[str, object] | None:
        catalog = json.loads(self.catalog_path.read_text(encoding="utf-8"))
        candidates = [
            item
            for item in catalog["templates"]
            if item.get("speakerRole") == "questioner" and item.get("questionId") == question_id
        ]
        primary = next(
            (
                item
                for item in candidates
                if item.get("qcStatus") == "accepted"
                and item.get("isPrimary") is True
                and isinstance(item.get("audioAssetId"), str)
                and item["audioAssetId"].strip()
            ),
            None,
        )
        if primary is None:
            return None
        return {
            "mode": "audio",
            "templateId": primary["templateId"],
            "questionId": primary["questionId"],
            "audioAssetId": primary["audioAssetId"],
            "displayText": primary["displayText"],
        }
