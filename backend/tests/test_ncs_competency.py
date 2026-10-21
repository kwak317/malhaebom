from __future__ import annotations

import os
import sys
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

import httpx

from fastapi.testclient import TestClient

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.core.auth import InvalidAccessToken
from app.main import create_app
from app.schemas.ncs_competency import NcsBackendCompetenciesResponse
from app.services.ncs_competency import (
    NCS_API_URL,
    NcsCompetencyService,
    NcsCompetencySettings,
    NcsCompetencyUnavailable,
)


UNIT_NAMES = {
    "2001020232": "응용SW 기초 기술 활용",
    "2001020205": "데이터 입출력 구현",
    "2001020218": "인터페이스 설계",
    "2001020211": "서버프로그램 구현",
    "2001020227": "애플리케이션 테스트 수행",
    "2001020219": "애플리케이션 요구사항 분석",
    "2001020217": "애플리케이션 리팩토링",
    "2001020214": "애플리케이션 배포",
}


def official_rows():
    return [
        {
            "NCS_LCLAS_CD": "20",
            "NCS_MCLAS_CD": "01",
            "NCS_SCLAS_CD": "02",
            "NCS_SUBD_CD": "02",
            "USG_YN": "Y",
            "NCS_CL_CD": f"{code}_23v6",
            "COMPE_UNIT_NAME": name,
            "COMPE_UNIT_DEF": f"{name}에 필요한 업무 능력이다.",
        }
        for code, name in UNIT_NAMES.items()
    ]


class FakeResponse:
    def __init__(self, payload: object, status_code: int = 200) -> None:
        self.payload = payload
        self.status_code = status_code

    def json(self):
        return self.payload


class FakeHttpClient:
    def __init__(self, response: FakeResponse) -> None:
        self.response = response
        self.requests: list[tuple[str, dict[str, object]]] = []

    def get(self, url: str, **kwargs):
        self.requests.append((url, kwargs))
        return self.response


def provider_response(rows):
    return {"response": {
        "header": {"resultCode": "00", "resultMsg": "NORMAL_SERVICE"},
        "body": {"items": {"item": rows}},
    }}


class FakeVerifier:
    def verify_access_token(self, token: str) -> str:
        if token != "owner-token":
            raise InvalidAccessToken()
        return "owner"


class FakeStore:
    def __init__(self):
        self.value = None
        self.loads = 0
        self.saves = 0
    def save(self, value):
        self.saves += 1
        self.value = value.model_copy(deep=True)
    def load(self):
        self.loads += 1
        if self.value is None:
            raise NcsCompetencyUnavailable("missing")
        return self.value.model_copy(deep=True)


class NcsCompetencyServiceTest(unittest.TestCase):
    def test_loads_reviewed_backend_options_from_official_units(self):
        http = FakeHttpClient(FakeResponse(provider_response(official_rows())))
        service = NcsCompetencyService(NcsCompetencySettings("issued%2Bkey"), http)

        result = service.backend_competencies()

        self.assertEqual(http.requests[0][0], NCS_API_URL)
        params = http.requests[0][1]["params"]
        self.assertEqual(params["serviceKey"], "issued+key")
        self.assertEqual(params["NCS_SUBD_CD"], "02")
        self.assertEqual(params["USG_YN"], "Y")
        self.assertEqual(len(result.options), 9)
        self.assertEqual([option.category for option in result.options].count("knowledge"), 3)
        self.assertEqual([option.category for option in result.options].count("skill"), 3)
        self.assertEqual([option.category for option in result.options].count("attitude"), 3)
        self.assertIn("서버프로그램 구현", [option.ncs_unit_name for option in result.options])
        self.assertNotIn("issued", result.model_dump_json())

    def test_rejects_wrong_job_and_old_units(self):
        rows = official_rows()
        rows[0]["NCS_SUBD_CD"] = "03"
        rows[1]["USG_YN"] = "N"
        service = NcsCompetencyService(
            NcsCompetencySettings("test-key"),
            FakeHttpClient(FakeResponse(provider_response(rows))),
        )

        with self.assertRaises(NcsCompetencyUnavailable):
            service.backend_competencies()

    def test_rejects_provider_error_without_leaking_key(self):
        service = NcsCompetencyService(
            NcsCompetencySettings("secret-key"),
            FakeHttpClient(FakeResponse({"response": {"header": {"resultCode": "30"}}})),
        )

        with self.assertRaises(NcsCompetencyUnavailable) as caught:
            service.backend_competencies()
        self.assertNotIn("secret-key", str(caught.exception))

    def test_initial_timeout_does_not_automatically_read_db_and_retry_skips_api(self):
        http = Mock()
        http.get.side_effect = [FakeResponse(provider_response(official_rows())), httpx.ConnectTimeout("private-key-url")]
        store = FakeStore()
        service = NcsCompetencyService(NcsCompetencySettings("secret-key"), http, store)
        live = service.backend_competencies()
        with self.assertRaises(NcsCompetencyUnavailable):
            service.backend_competencies()
        self.assertEqual(store.loads, 0)
        # A fresh service instance can use the shared store with no successful API call.
        restarted = NcsCompetencyService(NcsCompetencySettings("secret-key"), http, store)
        cached = restarted.stored_backend_competencies()
        self.assertEqual(http.get.call_count, 2)
        self.assertEqual(cached.data_source, "cached")
        self.assertEqual(cached.fetched_at, live.fetched_at)
        self.assertEqual(cached.options, live.options)

    def test_failed_api_response_never_overwrites_saved_snapshot(self):
        http = Mock()
        http.get.side_effect = [FakeResponse(provider_response(official_rows())), FakeResponse(provider_response([]))]
        store = FakeStore()
        service = NcsCompetencyService(NcsCompetencySettings("secret-key"), http, store)
        live = service.backend_competencies()
        with self.assertRaises(NcsCompetencyUnavailable):
            service.backend_competencies()
        self.assertEqual(store.saves, 1)
        self.assertEqual(service.stored_backend_competencies().options, live.options)

    def test_database_failure_does_not_hide_successful_api_response(self):
        store = Mock()
        store.save.side_effect = NcsCompetencyUnavailable("db unavailable")
        service = NcsCompetencyService(NcsCompetencySettings("key"), FakeHttpClient(FakeResponse(provider_response(official_rows()))), store)
        self.assertEqual(service.backend_competencies().data_source, "live")

    def test_missing_snapshot_is_an_error(self):
        service = NcsCompetencyService(NcsCompetencySettings("key"), Mock(), FakeStore())
        with self.assertRaises(NcsCompetencyUnavailable):
            service.stored_backend_competencies()

    def test_timeout_without_previous_success_still_fails(self):
        http = Mock()
        http.get.side_effect = httpx.ReadTimeout("secret-key")
        service = NcsCompetencyService(NcsCompetencySettings("secret-key"), http)
        with self.assertRaises(NcsCompetencyUnavailable) as caught:
            service.backend_competencies()
        self.assertNotIn("secret-key", str(caught.exception))

    def test_missing_key_is_unavailable(self):
        with patch.dict(os.environ, {"NCS_API_KEY": ""}):
            with self.assertRaises(NcsCompetencyUnavailable):
                NcsCompetencySettings.from_env()


class NcsCompetencyApiTest(unittest.TestCase):
    def setUp(self):
        service = NcsCompetencyService(
            NcsCompetencySettings("server-only-key"),
            FakeHttpClient(FakeResponse(provider_response(official_rows()))),
            FakeStore(),
        )
        self.client = TestClient(create_app(
            token_verifier=FakeVerifier(),
            ncs_competency_service=service,
        ))

    def test_authenticated_api_returns_marked_fallback(self):
        first = self.client.get("/api/ncs/backend-competencies", headers={"Authorization": "Bearer owner-token"})
        service = self.client.app.state.ncs_competency_service
        service.http.response = FakeResponse({}, status_code=503)
        failed = self.client.get("/api/ncs/backend-competencies", headers={"Authorization": "Bearer owner-token"})
        self.assertEqual(failed.status_code, 503)
        cached = self.client.get("/api/ncs/backend-competencies?source=database", headers={"Authorization": "Bearer owner-token"})
        self.assertEqual(cached.status_code, 200)
        self.assertEqual(cached.json()["data_source"], "cached")
        self.assertEqual(cached.json()["fetched_at"], first.json()["fetched_at"])
        self.assertEqual(cached.json()["options"], first.json()["options"])
        self.assertEqual(self.client.get("/api/ncs/backend-competencies").status_code, 401)

    def test_database_retry_also_requires_login_and_rejects_unknown_source(self):
        self.assertEqual(self.client.get("/api/ncs/backend-competencies?source=database").status_code, 401)
        self.assertEqual(self.client.get("/api/ncs/backend-competencies?source=unknown", headers={"Authorization":"Bearer owner-token"}).status_code, 422)

    def test_requires_login(self):
        self.assertEqual(self.client.get("/api/ncs/backend-competencies").status_code, 401)

    def test_returns_options_without_key(self):
        response = self.client.get(
            "/api/ncs/backend-competencies",
            headers={"Authorization": "Bearer owner-token"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()["options"]), 9)
        self.assertNotIn("server-only-key", response.text)


if __name__ == "__main__":
    unittest.main()
