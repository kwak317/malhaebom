from __future__ import annotations

import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
POLICY_WORKFLOW = PROJECT_ROOT / ".github" / "workflows" / "pr-policy-check.yml"
RERUN_WORKFLOW = PROJECT_ROOT / ".github" / "workflows" / "pr-policy-rerun-on-edit.yml"
PRODUCT_CI_WORKFLOW = PROJECT_ROOT / ".github" / "workflows" / "product-ci.yml"
PRODUCT_CI_REQUIREMENTS = PROJECT_ROOT / "backend" / "requirements-ci.txt"


class PrPolicyWorkflowTests(unittest.TestCase):
    def test_product_ci_runs_backend_frontend_and_build_on_pull_requests(self) -> None:
        workflow = PRODUCT_CI_WORKFLOW.read_text(encoding="utf-8")

        self.assertIn("types: [opened, synchronize, reopened]", workflow)
        self.assertIn('python-version: "3.12"', workflow)
        self.assertIn("python -m pip install -r backend/requirements-ci.txt", workflow)
        # All current backend test modules use unittest.TestCase; pytest
        # collects them too, so running both suites duplicates the same tests.
        self.assertNotIn("python -m unittest discover", workflow)
        self.assertIn("python -m pytest backend/tests -q", workflow)
        self.assertIn('node-version: "22.14.0"', workflow)
        self.assertIn("npm ci --prefix frontend", workflow)
        self.assertIn("npm --prefix frontend test", workflow)
        self.assertIn("npm --prefix frontend run build", workflow)
        self.assertIn("cancel-in-progress: true", workflow)

    def test_product_ci_requirements_exclude_model_runtime_dependencies(self) -> None:
        requirements = PRODUCT_CI_REQUIREMENTS.read_text(encoding="utf-8")
        active_requirements = "\n".join(
            line for line in requirements.splitlines() if line and not line.startswith("#")
        )

        self.assertIn("-r requirements-eval.txt", active_requirements)
        self.assertIn("fastapi==0.115.12", active_requirements)
        self.assertIn("numpy>=1.26,<3", active_requirements)
        self.assertIn("pytest>=8,<9", active_requirements)
        self.assertNotIn("faster-whisper", active_requirements)
        self.assertNotIn("silero-vad", active_requirements)
        self.assertNotIn("torch==", active_requirements)
        self.assertNotIn("torchaudio", active_requirements)

    def test_policy_workflow_uses_commit_events_and_current_pr_body(self) -> None:
        workflow = POLICY_WORKFLOW.read_text(encoding="utf-8")

        self.assertIn("types: [opened, synchronize, reopened]", workflow)
        self.assertNotIn("types: [opened, synchronize, reopened, edited]", workflow)
        self.assertNotIn("github.event.pull_request.body", workflow)
        self.assertIn(
            'gh api "repos/${{ github.repository }}/pulls/${{ github.event.pull_request.number }}"',
            workflow,
        )
        self.assertIn("--jq '.body // \"\"' > /tmp/pr_body.txt", workflow)
        self.assertIn(
            "group: pr-policy-${{ github.event.pull_request.number }}-${{ github.event.pull_request.head.sha }}",
            workflow,
        )
        self.assertIn("cancel-in-progress: true", workflow)

    def test_edit_helper_reruns_existing_policy_run_for_current_head(self) -> None:
        workflow = RERUN_WORKFLOW.read_text(encoding="utf-8")

        self.assertIn("types: [edited]", workflow)
        self.assertIn("actions: write", workflow)
        self.assertIn("pull-requests: read", workflow)
        self.assertIn(
            "github.event.pull_request.head.repo.full_name == github.repository",
            workflow,
        )
        self.assertIn("--workflow pr-policy-check.yml", workflow)
        self.assertIn('--commit "${HEAD_SHA}"', workflow)
        self.assertIn(
            'gh api --method POST "repos/${GITHUB_REPOSITORY}/actions/runs/${run_id}/rerun"',
            workflow,
        )
        self.assertIn(
            "group: pr-policy-edit-rerun-${{ github.event.pull_request.number }}",
            workflow,
        )
        self.assertIn("cancel-in-progress: true", workflow)

    def test_edit_helper_rechecks_current_head_before_rerun(self) -> None:
        workflow = RERUN_WORKFLOW.read_text(encoding="utf-8")

        read_current_head = workflow.index(
            '"repos/${GITHUB_REPOSITORY}/pulls/${PR_NUMBER}"'
        )
        compare_current_head = workflow.index(
            'if [[ "${current_head_sha}" != "${HEAD_SHA}" ]]'
        )
        skip_obsolete_rerun = workflow.index(
            "skipping obsolete policy rerun"
        )
        rerun_call = workflow.index(
            'gh api --method POST "repos/${GITHUB_REPOSITORY}/actions/runs/${run_id}/rerun"'
        )

        self.assertLess(read_current_head, compare_current_head)
        self.assertLess(compare_current_head, skip_obsolete_rerun)
        self.assertLess(skip_obsolete_rerun, rerun_call)
        self.assertIn("exit 0", workflow[skip_obsolete_rerun:rerun_call])


if __name__ == "__main__":
    unittest.main()
