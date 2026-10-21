import json
import unittest
from datetime import datetime
from zoneinfo import ZoneInfo

import httpx

from app.services.public_job_catalog import search_public_catalog
from app.services.tavily_job_search import TavilyAdditionalJobSearch
from app.services.saramin_recommendation import SaraminPostingVerifier
from tests.test_additional_job_sources import page


class PublicJobCatalogTest(unittest.TestCase):
    def test_catalog_filters_and_constructs_only_fixed_source_urls(self):
        fixtures = {
            'rallit': {'data': {'items': [{'id': 123, 'title': '백엔드 개발자', 'status': {'code': 'HIRING'}, 'jobLevels': ['BEGINNER'], 'url': 'https://evil.test'}, {'id': 124, 'title': '백엔드 개발자', 'status': {'code': 'CLOSE'}, 'jobLevels': ['BEGINNER']}]}},
            'wanted': {'data': [{'id': 123, 'annual_from': 0}, {'id': 124, 'annual_from': 3}, {'id': True, 'annual_from': 0}, {'id': -1, 'annual_from': 0}, {'id': 'evil', 'annual_from': 0}]},
            'jumpit': {'result': {'positions': [{'id': 123, 'newcomer': True}, {'id': 124, 'newcomer': False}]}},
        }
        for source, payload in fixtures.items():
            requests = []
            def respond(request):
                requests.append(request)
                return httpx.Response(200, json=payload)
            rows = search_public_catalog(source, httpx.Client(transport=httpx.MockTransport(respond)))
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0]['content'], '')
            self.assertNotIn('evil', rows[0]['url'])
            self.assertEqual(len(requests), 2)
            self.assertTrue(all(request.method == 'GET' for request in requests))
            self.assertTrue(all('authorization' not in request.headers for request in requests))

    def test_candidate_and_request_bounds(self):
        payload = {'data': [{'id': i, 'annual_from': 0} for i in range(1, 101)]}
        requests = []
        def respond(request):
            requests.append(request)
            return httpx.Response(200, json=payload)
        rows = search_public_catalog('wanted', httpx.Client(transport=httpx.MockTransport(respond)))
        self.assertEqual(len(rows), 20)
        self.assertEqual(len(requests), 1)
        self.assertEqual(requests[0].url.params['years'], '0')
        self.assertEqual(requests[0].url.params['sort'], 'job.latest_order')

    def test_second_page_failure_keeps_first_page(self):
        def respond(request):
            self.assertEqual(request.url.params['career'], '0')
            if request.url.params['page'] == '2': return httpx.Response(503)
            return httpx.Response(200, json={'result': {'positions': [{'id': 123, 'newcomer': True}]}})
        self.assertEqual(len(search_public_catalog('jumpit', httpx.Client(transport=httpx.MockTransport(respond)))), 1)

    def test_discovery_keeps_either_success_and_deduplicates_ids(self):
        for catalog_ok, web_ok in [(True, False), (False, True), (True, True)]:
            def respond(request):
                if request.method == 'GET':
                    return httpx.Response(200, json={'data': [{'id': 123, 'annual_from': 0}]}) if catalog_ok else httpx.Response(503)
                return httpx.Response(200, json={'results': [{'url': 'https://www.wanted.co.kr/wd/123'}]}) if web_ok else httpx.Response(503)
            provider = TavilyAdditionalJobSearch('fake', 'wanted', httpx.Client(transport=httpx.MockTransport(respond)))
            self.assertEqual(provider.search(['PRIVATE README']), [{'url': 'https://www.wanted.co.kr/wd/123', 'content': ''}])

    def test_rallit_redirect_only_same_official_host_and_posting_id(self):
        today = datetime(2026, 10, 4, tzinfo=ZoneInfo('Asia/Seoul'))
        for target, success in [('/positions/123/backend', True), ('https://evil.test/positions/123/backend', False), ('/positions/999/backend', False), ('http://www.rallit.com/positions/123/backend', False), ('https://user@www.rallit.com/positions/123/backend', False)]:
            requests = []
            def respond(request):
                requests.append(str(request.url))
                return httpx.Response(308, headers={'location': target}) if len(requests) == 1 else httpx.Response(200, text=page('rallit'))
            result, reason = SaraminPostingVerifier(httpx.Client(transport=httpx.MockTransport(respond))).verify_with_reason('https://www.rallit.com/positions/123', today=today)
            self.assertEqual(result is not None, success)
            self.assertEqual(len(requests), 2 if success else 1)
            self.assertEqual(reason, 'verified' if success else 'unsafe_redirect')

    def test_malformed_catalog_does_not_create_candidates(self):
        for payload in ({}, {'data': {}}, {'data': [{'id': '/evil', 'annual_from': 0}]}):
            self.assertEqual(search_public_catalog('wanted', httpx.Client(transport=httpx.MockTransport(lambda _: httpx.Response(200, json=payload)))), [])
