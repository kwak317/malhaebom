from __future__ import annotations
import json
import sys
import unittest
from datetime import date
from pathlib import Path
from types import SimpleNamespace
import httpx
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.services.additional_job_sources import extra_posting_key, parse_extra_posting, parse_extra_posting_with_reason
from app.services.tavily_job_search import TavilyAdditionalJobSearch, PlayMcpTavilyJobSearch
from app.services.saramin_recommendation import SaraminRecommendationUnavailable, SaraminRecommendationService
from app.schemas.saramin_recommendation import SaraminRecommendationRequest

TODAY = date(2026, 10, 4)

def page(source, **changes):
    if source == 'rallit':
        data = dict(id=123, status={'code': 'HIRING'}, jobLevels=['BEGINNER'], companyName='테스트', title='백엔드 개발자', isAlwaysHiring=True, responsibilities='백엔드 서버 개발과 API 구현을 담당합니다.', basicQualifications='Java Spring 사용 경험', preferredQualifications='')
    else:
        data = dict(id=123, status='active', career={'is_newbie': True}, company={'company_name': '테스트'}, position='백엔드 개발자', close_time='2026-11-01', main_tasks='백엔드 서버 개발과 API 구현을 담당합니다.', requirements='Java Spring 사용 경험', preferred_points='')
    data.update(changes)
    props = {'position' if source == 'rallit' else 'initialData': data}
    return '<script id="__NEXT_DATA__">' + json.dumps({'props': {'pageProps': props}}) + '</script><button>지원하기</button>'

class AdditionalSourcesTest(unittest.TestCase):
    def test_only_exact_individual_https_urls(self):
        urls = {'rallit': 'https://www.rallit.com/positions/123/backend', 'wanted': 'https://www.wanted.co.kr/wd/123', 'jumpit': 'https://jumpit.saramin.co.kr/position/123'}
        for source, url in urls.items():
            self.assertEqual(extra_posting_key(url + '?tracking=1'), (source, '123'))
            for bad in (url.replace('https:', 'http:'), url.replace('https://', 'https://user@'), url.replace('.co.kr', '.co.kr.evil.test').replace('.com/', '.com.evil.test/'), url + '/extra'):
                self.assertIsNone(extra_posting_key(bad))
        self.assertEqual(extra_posting_key('https://www.rallit.com/positions/123'), ('rallit', '123'))

    def test_live_and_closed_rallit(self):
        self.assertIsNotNone(parse_extra_posting('rallit', '123', page('rallit'), TODAY))
        for change in ({'status': {'code': 'CLOSE'}}, {'status': {'code': 'FINISH'}}, {'jobLevels': ['SENIOR']}, {'isAlwaysHiring': False, 'endedAt': '2026-09-01'}):
            self.assertIsNone(parse_extra_posting('rallit', '123', page('rallit', **change), TODAY))
        self.assertIsNone(parse_extra_posting('rallit', '999', page('rallit'), TODAY))

    def test_wanted_needs_open_ui_and_newbie_and_valid_deadline(self):
        self.assertIsNotNone(parse_extra_posting('wanted', '123', page('wanted'), TODAY))
        for change in ({'status': 'close'}, {'career': {'is_newbie': False}}, {'close_time': '2026-09-01'}, {'close_time': None}):
            self.assertIsNone(parse_extra_posting('wanted', '123', page('wanted', **change), TODAY))
        self.assertIsNone(parse_extra_posting('wanted', '123', page('wanted') + '<p>공고는 마감되었습니다</p>', TODAY))
        self.assertIsNotNone(parse_extra_posting('wanted', '123', page('wanted', close_time=None) + '<p>상시 채용</p>', TODAY))

    def test_jumpit_source_details_and_closed(self):
        markup = '<meta property="og:description" content="테스트 - 백엔드 개발자 채용"><h1>백엔드 개발자</h1><p>주요업무 백엔드 서버 API 개발 및 유지보수 자격요건 Java 사용 경험 복지 및 혜택</p><p>포지션 경력/학력/마감일/근무지역 정보 경력 신입 학력 무관 마감일 2026-11-01 근무지역 서울</p>'
        self.assertIsNotNone(parse_extra_posting('jumpit', '123', markup, TODAY))
        for bad in (markup + '<button>마감된 포지션</button>', markup.replace('2026-11-01', '2026-09-01'), markup.replace('경력 신입', '경력 5년'), markup.replace('자격요건', '없음')):
            self.assertIsNone(parse_extra_posting('jumpit', '123', bad, TODAY))

    def test_malformed_data_fails_closed(self):
        for source in ('rallit', 'wanted', 'jumpit'):
            self.assertIsNone(parse_extra_posting(source, '123', '<script id="__NEXT_DATA__">{bad}</script>', TODAY))

    def test_discovery_does_not_send_private_readme_or_trust_snippets(self):
        for source, domain, path in [('rallit', 'rallit.com', '/positions/123/backend'), ('wanted', 'wanted.co.kr', '/wd/123'), ('jumpit', 'jumpit.saramin.co.kr', '/position/123')]:
            requests = []
            def respond(request):
                requests.append(json.loads(request.content))
                return httpx.Response(200, json={'results': [{'url': f'https://{domain}{path}?track=1', 'content': 'unverified'}, {'url': 'https://evil.test/wd/123'}]})
            provider = TavilyAdditionalJobSearch('fake', source, httpx.Client(transport=httpx.MockTransport(respond)))
            result = provider.search(['PRIVATE README'])
            self.assertEqual(len(result), 1)
            self.assertEqual(result[0]['content'], '')
            self.assertEqual(requests[0]['include_domains'], [domain])
            self.assertNotIn('PRIVATE README', str(requests))

    def test_five_sources_keep_partial_success(self):
        def fail(_): raise SaraminRecommendationUnavailable('failed')
        provider = lambda source: SimpleNamespace(source=source, search=lambda _: [{'url': source}])
        search = PlayMcpTavilyJobSearch(SimpleNamespace(search=fail), provider('jobkorea'), tuple(provider(s) for s in ('rallit', 'wanted', 'jumpit')))
        self.assertEqual(search.sources, ('saramin', 'jobkorea', 'rallit', 'wanted', 'jumpit'))
        self.assertEqual(len(search.search([])), 4)

    def test_recommendations_limit_each_of_five_sources(self):
        patterns = {'saramin': 'https://www.saramin.co.kr/zf_user/jobs/view?rec_idx={}', 'jobkorea': 'https://m.jobkorea.co.kr/Recruit/GI_Read/{}', 'rallit': 'https://www.rallit.com/positions/{}/backend', 'wanted': 'https://www.wanted.co.kr/wd/{}', 'jumpit': 'https://jumpit.saramin.co.kr/position/{}'}
        rows = [{'url': pattern.format(i)} for pattern in patterns.values() for i in range(1, 8)]
        search = SimpleNamespace(sources=tuple(patterns), search=lambda _: rows)
        def verify(url, *, today):
            return (url, '신입 백엔드 개발자', url, today.date(), '신입', 'REST API 서버 개발')
        result = SaraminRecommendationService(search, SimpleNamespace(verify=verify)).recommend(SaraminRecommendationRequest(selected_ncs_ids=['skill-server']))
        self.assertEqual(len(result.recommendations), 25)
        counts = {source: 0 for source in patterns}
        from app.services.saramin_recommendation import _posting_key
        for job in result.recommendations: counts[_posting_key(job.source_url)[0]] += 1
        self.assertEqual(set(counts.values()), {5})

    def test_wanted_due_time_fallback_and_closed_priority(self):
        markup = page('wanted', close_time=None, due_time='2026-11-01T00:00:00')
        parsed, reason = parse_extra_posting_with_reason('wanted', '123', markup, TODAY)
        self.assertEqual(reason, 'verified')
        self.assertEqual(parsed[2], date(2026, 11, 1))
        for changes, expected in [({'close_time': None, 'due_time': '2026-09-01'}, 'deadline_expired'),
                                  ({'status': 'close', 'due_time': '2026-11-01'}, 'closed'),
                                  ({'career': {'is_newbie': False}}, 'experience')]:
            self.assertEqual(parse_extra_posting_with_reason('wanted', '123', page('wanted', **changes), TODAY), (None, expected))
        self.assertEqual(parse_extra_posting_with_reason('wanted', '123', '<p>invalid</p>', TODAY), (None, 'source_structure'))

    def test_supplementary_discovery_is_recent_and_private_input_free(self):
        from datetime import datetime
        from zoneinfo import ZoneInfo
        from app.services.tavily_job_search import TavilyJobKoreaSearch
        for source in ('jobkorea', 'rallit', 'wanted', 'jumpit'):
            bodies = []
            def respond(request):
                bodies.append(json.loads(request.content))
                return httpx.Response(200, json={'results': []})
            client = httpx.Client(transport=httpx.MockTransport(respond))
            provider = TavilyJobKoreaSearch('fake', client) if source == 'jobkorea' else TavilyAdditionalJobSearch('fake', source, client)
            provider.search_more(['PRIVATE README'])
            recent = [body for body in bodies if body.get('time_range') == 'month']
            self.assertEqual(len(recent), 1)
            self.assertEqual(recent[0]['search_depth'], 'advanced')
            now = datetime.now(ZoneInfo('Asia/Seoul'))
            self.assertIn(f'{now.year} {now.month}월', recent[0]['query'])
            self.assertIn('site:', recent[0]['query'])
            self.assertNotIn('PRIVATE README', str(bodies))

    def test_recommendation_logs_reasons_and_context_mismatch_without_private_text(self):
        source = 'https://www.wanted.co.kr/wd/123'
        request = SaraminRecommendationRequest(selected_ncs_ids=['skill-server'])
        for verified, reason, expected in [(None, 'closed', "'closed': 1"),
            (('PRIVATE COMPANY', '개발자', source, TODAY, '신입', 'unrelated text'), 'verified', "'context_mismatch': 1")]:
            search = SimpleNamespace(sources=('wanted',), search=lambda _: [{'url': source}])
            verifier = SimpleNamespace(verify_with_reason=lambda *args, **kwargs: (verified, reason))
            with self.assertLogs('app.services.saramin_recommendation', level='INFO') as logs:
                result = SaraminRecommendationService(search, verifier).recommend(request)
            self.assertEqual(result.recommendations, [])
            self.assertIn(expected, str(logs.output))
            self.assertNotIn('PRIVATE COMPANY', str(logs.output))
            self.assertNotIn(source, str(logs.output))

    def test_wanted_public_active_page_without_button_and_hidden_pages(self):
        markup = page('wanted').replace('<button>지원하기</button>', '')
        self.assertIsNotNone(parse_extra_posting('wanted', '123', markup, TODAY))
        for changes in ({'hidden': True}, {'is_private': True}, {'status': 'unknown'}):
            self.assertIsNone(parse_extra_posting('wanted', '123', page('wanted', **changes), TODAY))
