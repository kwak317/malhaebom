from __future__ import annotations

import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch


BACKEND_ROOT = Path(__file__).resolve().parents[1]
PROJECT_ROOT = BACKEND_ROOT.parent
for path in (PROJECT_ROOT, BACKEND_ROOT):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from evals.sync_langfuse_assets import (  # noqa: E402
    DEFAULT_DATASET_PATH,
    build_plan,
    ensure_dataset,
    sync_dataset_items,
    sync_prompt,
)


class NotFoundError(Exception):
    status_code = 404


class FakePrompt:
    def __init__(self, prompt: str, config: dict, version: int = 1):
        self.prompt = prompt
        self.config = config
        self.version = version


class FakeLangfuse:
    def __init__(self):
        self.prompt = None
        self.created_prompts = []
        self.dataset = None
        self.created_datasets = []
        self.items = []

    def get_prompt(self, *args, **kwargs):
        if self.prompt is None:
            raise NotFoundError()
        return self.prompt

    def create_prompt(self, **kwargs):
        self.created_prompts.append(kwargs)
        self.prompt = FakePrompt(kwargs["prompt"], kwargs["config"])
        return self.prompt

    def get_dataset(self, *args, **kwargs):
        if self.dataset is None:
            raise NotFoundError()
        return self.dataset

    def create_dataset(self, **kwargs):
        self.created_datasets.append(kwargs)
        self.dataset = kwargs
        return kwargs

    def create_dataset_item(self, **kwargs):
        self.items.append(kwargs)


class LangfuseAssetsTest(unittest.TestCase):
    def build_plan(self):
        with patch.dict(
            os.environ,
            {
                "COACHING_PROMPT_VERSION": "coaching-output-test",
                "COACHING_SKILL_VERSION": "interview-coach-test",
            },
            clear=True,
        ):
            return build_plan(
                prompt_name="malhaebom-coaching",
                prompt_label="candidate",
                dataset_name="malhaebom-coaching-eval-v2-test",
                dataset_path=DEFAULT_DATASET_PATH,
            )

    def test_plan_contains_exactly_30_synthetic_cases(self):
        plan = self.build_plan()

        self.assertEqual(len(plan.cases), 30)
        self.assertEqual(plan.prompt_version, "coaching-output-test")
        self.assertTrue(all(case.dataset_version == "v2" for case in plan.cases))

    def test_sync_is_idempotent_for_prompt_and_dataset_items(self):
        plan = self.build_plan()
        client = FakeLangfuse()

        prompt, prompt_status = sync_prompt(client, plan)
        dataset_status = ensure_dataset(client, plan)
        first_count = sync_dataset_items(client, plan)
        item_ids = [item["id"] for item in client.items]
        _, second_prompt_status = sync_prompt(client, plan)
        second_dataset_status = ensure_dataset(client, plan)
        second_count = sync_dataset_items(client, plan)

        self.assertEqual(prompt_status, "created")
        self.assertEqual(second_prompt_status, "unchanged")
        self.assertEqual(dataset_status, "created")
        self.assertEqual(second_dataset_status, "existing")
        self.assertEqual(first_count, 30)
        self.assertEqual(second_count, 30)
        self.assertEqual(len(set(item_ids)), 30)
        self.assertEqual(item_ids, [item["id"] for item in client.items[30:]])
        self.assertTrue(all(item["metadata"]["synthetic"] for item in client.items))
        self.assertEqual(prompt.version, 1)


if __name__ == "__main__":
    unittest.main()
