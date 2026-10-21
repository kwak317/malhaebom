"""Regression checks for the local n8n coaching Mock workflow export."""

from __future__ import annotations

import json
from pathlib import Path
import unittest


WORKFLOW_PATH = (
    Path(__file__).resolve().parents[2]
    / "n8n"
    / "workflows"
    / "malhaebom-coaching-mock.json"
)


class N8nCoachingWorkflowExportTests(unittest.TestCase):
    def test_exported_workflow_requires_a_team_local_header_auth_credential(self) -> None:
        workflow = json.loads(WORKFLOW_PATH.read_text(encoding="utf-8"))
        nodes = {node["name"]: node for node in workflow["nodes"]}

        webhook = nodes["Receive Test Request"]
        self.assertEqual(webhook["parameters"]["authentication"], "headerAuth")
        self.assertNotIn("credentials", webhook)

    def test_exported_workflow_calls_the_compose_mock_coaching_api(self) -> None:
        workflow = json.loads(WORKFLOW_PATH.read_text(encoding="utf-8"))
        nodes = {node["name"]: node for node in workflow["nodes"]}

        request = nodes["Call Mock Coaching API"]
        parameters = request["parameters"]

        self.assertEqual(parameters["method"], "POST")
        self.assertEqual(parameters["url"], "http://api:8000/api/agent")
        self.assertTrue(parameters["sendHeaders"])
        self.assertEqual(
            {
                item["name"]: item["value"]
                for item in parameters["headerParameters"]["parameters"]
            }["Authorization"],
            "Bearer compose-e2e-token",
        )
        self.assertEqual(
            json.loads(parameters["jsonBody"]),
            {
                "action": "analyze",
                "question_id": "preset-04",
                "answer_revision_id": "00000000-0000-0000-0000-000000000101",
                "job_snapshot_id": "00000000-0000-0000-0000-000000000201",
            },
        )

    def test_exported_workflow_checks_health_and_returns_a_safe_error_summary(self) -> None:
        workflow = json.loads(WORKFLOW_PATH.read_text(encoding="utf-8"))
        nodes = {node["name"]: node for node in workflow["nodes"]}

        health_check = nodes["Health Check"]
        self.assertEqual(health_check["parameters"]["url"], "http://api:8000/health")
        self.assertEqual(health_check["onError"], "continueErrorOutput")

        error_summary = nodes["Health Error Summary"]
        assignments = error_summary["parameters"]["assignments"]["assignments"]
        self.assertEqual(
            {item["name"]: item["value"] for item in assignments},
            {
                "status": "unavailable",
                "message": "말해봄 API에 연결하지 못했습니다.",
                "technical_error": "={{$json.error.message}}",
            },
        )
        self.assertIn("If", workflow["connections"]["Health Check"]["main"][0][0]["node"])
        self.assertEqual(
            workflow["connections"]["Health Check"]["main"][1][0]["node"],
            "Health Error Summary",
        )
