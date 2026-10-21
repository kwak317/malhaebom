from __future__ import annotations

import argparse
import json
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


class DeploymentSmokeError(RuntimeError):
    pass


def _request(request: Request, timeout: float) -> tuple[int, dict[str, str], bytes]:
    try:
        with urlopen(request, timeout=timeout) as response:
            headers = {name.lower(): value for name, value in response.headers.items()}
            return response.status, headers, response.read()
    except (HTTPError, URLError, TimeoutError) as exc:
        raise DeploymentSmokeError(f"request failed: {request.full_url}: {exc}") from exc


def check_deployment(
    *,
    frontend_url: str,
    api_url: str,
    origin: str,
    timeout: float = 10.0,
) -> list[str]:
    frontend_status, _, _ = _request(Request(frontend_url), timeout)
    if frontend_status != 200:
        raise DeploymentSmokeError(f"frontend returned HTTP {frontend_status}")

    health_url = f"{api_url.rstrip('/')}/health"
    health_status, _, health_body = _request(Request(health_url), timeout)
    try:
        health_payload = json.loads(health_body)
    except json.JSONDecodeError as exc:
        raise DeploymentSmokeError("health response is not JSON") from exc
    if health_status != 200 or health_payload.get("status") != "ok":
        raise DeploymentSmokeError("health status is not ok")

    cors_url = f"{api_url.rstrip('/')}/api/job-recommendations"
    cors_request = Request(cors_url, method="OPTIONS")
    cors_request.add_header("Origin", origin)
    cors_request.add_header("Access-Control-Request-Method", "GET")
    cors_request.add_header("Access-Control-Request-Headers", "authorization")
    cors_status, cors_headers, _ = _request(cors_request, timeout)
    allowed_origin = cors_headers.get("access-control-allow-origin", "")
    allowed_methods = {
        value.strip().upper()
        for value in cors_headers.get("access-control-allow-methods", "").split(",")
    }
    allowed_headers = {
        value.strip().lower()
        for value in cors_headers.get("access-control-allow-headers", "").split(",")
    }
    if (
        cors_status != 200
        or allowed_origin != origin
        or "GET" not in allowed_methods
        or "authorization" not in allowed_headers
    ):
        raise DeploymentSmokeError("CORS policy does not allow the frontend request")

    return [
        "frontend: HTTP 200",
        'health: HTTP 200 {"status":"ok"}',
        "cors: HTTP 200 origin/method/header allowed",
    ]


def main() -> int:
    parser = argparse.ArgumentParser(description="Check public deployment reachability and CORS.")
    parser.add_argument("--frontend-url", default="https://malhaebom.xyz/")
    parser.add_argument(
        "--api-url",
        default="https://malhaebom-mk2-fmf5h3xp4q-du.a.run.app",
    )
    parser.add_argument("--origin", default="https://malhaebom.xyz")
    parser.add_argument("--timeout", type=float, default=10.0)
    args = parser.parse_args()

    try:
        checks = check_deployment(
            frontend_url=args.frontend_url,
            api_url=args.api_url,
            origin=args.origin,
            timeout=args.timeout,
        )
    except DeploymentSmokeError as exc:
        print(f"FAIL: {exc}")
        return 1

    for check in checks:
        print(f"PASS: {check}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
