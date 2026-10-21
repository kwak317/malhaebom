import json
import unittest
from concurrent.futures import ThreadPoolExecutor
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
from app.services.loading_progress import install_loading_progress, report_progress


class LoadingProgressTests(unittest.TestCase):
    def make_app(self):
        app = FastAPI()
        install_loading_progress(app)

        @app.post("/analysis-jobs/40000000-0000-4000-8000-000000000001/normalize-transcript")
        @app.post("/api/resume/analyze")
        @app.post("/api/github/readme/analyze")
        def analyze(payload: dict):
            report_progress("원문 조회 중…")
            if payload.get("fail"):
                raise HTTPException(401, "로그인 필요")
            report_progress("원문 근거 검증 중…")
            return {"ok": payload["value"]}
        return app

    def test_json_contract_unchanged(self):
        with TestClient(self.make_app()) as client:
            result = client.post("/api/github/readme/analyze", json={"value": 1})
            self.assertEqual(result.status_code, 200)
            self.assertEqual(result.json(), {"ok": 1})

    def test_sync_thread_progress_before_result(self):
        with TestClient(self.make_app()) as client:
            result = client.post("/api/github/readme/analyze", json={"value": 2},
                                 headers={"Accept": "application/x-ndjson"})
            events = [json.loads(line) for line in result.text.splitlines()]
            self.assertEqual([e["stage"] for e in events[1:-1]], ["원문 조회 중…", "원문 근거 검증 중…"])
            self.assertEqual(events[-1]["body"], {"ok": 2})
            self.assertEqual(events[-1]["status"], 200)
            self.assertIn("no-store", result.headers["cache-control"])

    def test_auth_and_validation_status_preserved(self):
        with TestClient(self.make_app()) as client:
            for data, status in [({"fail": True}, 401), (None, 422)]:
                result = client.post("/api/github/readme/analyze", json=data,
                                     headers={"Accept": "application/x-ndjson"})
                events = [json.loads(line) for line in result.text.splitlines()]
                self.assertEqual(events[-1]["status"], status)
                self.assertEqual(events[-1]["type"], "result")

    def test_normalization_stream_preserves_error_and_result(self):
        path='/analysis-jobs/40000000-0000-4000-8000-000000000001/normalize-transcript'
        with TestClient(self.make_app()) as client:
            for value,status in [({'value':7},200),({'fail':True},401),(None,422)]:
                response=client.post(path,json=value,headers={'Accept':'application/x-ndjson'})
                self.assertIn('application/x-ndjson',response.headers['content-type'])
                events=[json.loads(line) for line in response.text.splitlines()]
                self.assertEqual(events[-1]['status'],status)
                if status==200:self.assertEqual(events[-1]['body'],{'ok':7})
            self.assertEqual(client.post(path,json={'value':8}).json(),{'ok':8})

    def test_resume_stream_and_json_contract(self):
        with TestClient(self.make_app()) as client:
            for payload,status in [({'value':3},200),({'fail':True},401),(None,422)]:
                response=client.post('/api/resume/analyze',json=payload,headers={'Accept':'application/x-ndjson'})
                events=[json.loads(line) for line in response.text.splitlines()]
                self.assertEqual(events[-1]['status'],status)
                if status==200:self.assertEqual(events[-1]['body'],{'ok':3})
            self.assertEqual(client.post('/api/resume/analyze',json={'value':4}).json(),{'ok':4})

    def test_progress_does_not_mix_requests(self):
        with TestClient(self.make_app()) as client:
            def call(value):
                response = client.post("/api/github/readme/analyze", json={"value": value},
                                       headers={"Accept": "application/x-ndjson"})
                return json.loads(response.text.splitlines()[-1])["body"]["ok"]
            with ThreadPoolExecutor(max_workers=2) as executor:
                self.assertEqual(list(executor.map(call, [11, 22])), [11, 22])
