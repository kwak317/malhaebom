from __future__ import annotations

import json
import sys
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.check_deployment_smoke import DeploymentSmokeError, check_deployment


class _SmokeHandler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:  # noqa: N802
        if self.path == "/":
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"frontend")
            return
        if self.path in {"/health", "/bad-health/health"}:
            status = "degraded" if self.path.startswith("/bad-health") else "ok"
            body = json.dumps({"status": status}).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        self.send_response(404)
        self.end_headers()

    def do_OPTIONS(self) -> None:  # noqa: N802
        self.send_response(200)
        self.send_header("access-control-allow-origin", self.headers["Origin"])
        self.send_header("access-control-allow-methods", "GET, POST, DELETE")
        self.send_header(
            "access-control-allow-headers",
            "Accept, Authorization, Content-Type",
        )
        self.end_headers()

    def log_message(self, format: str, *args: object) -> None:
        return


class DeploymentSmokeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), _SmokeHandler)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        host, port = cls.server.server_address
        cls.base_url = f"http://{host}:{port}"

    @classmethod
    def tearDownClass(cls) -> None:
        cls.server.shutdown()
        cls.thread.join()

    def test_accepts_healthy_frontend_api_and_cors(self) -> None:
        checks = check_deployment(
            frontend_url=f"{self.base_url}/",
            api_url=self.base_url,
            origin=self.base_url,
        )

        self.assertEqual(
            checks,
            [
                "frontend: HTTP 200",
                'health: HTTP 200 {"status":"ok"}',
                "cors: HTTP 200 origin/method/header allowed",
            ],
        )

    def test_rejects_unexpected_health_payload(self) -> None:
        with self.assertRaisesRegex(DeploymentSmokeError, "health status is not ok"):
            check_deployment(
                frontend_url=f"{self.base_url}/",
                api_url=f"{self.base_url}/bad-health",
                origin=self.base_url,
            )


if __name__ == "__main__":
    unittest.main()
