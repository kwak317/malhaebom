import unittest
from types import SimpleNamespace

from app.schemas.saramin_recommendation import SaraminRecommendationRequest
from app.services.saramin_recommendation import SaraminRecommendationService, _posting_key
from app.services.tavily_job_search import PlayMcpTavilyJobSearch


class JobSearchTargetedSupplementTests(unittest.TestCase):
    def test_only_insufficient_sources_are_searched_and_duplicates_do_not_fill_quota(self):
        for duplicate in (False, True):
            with self.subTest(duplicate=duplicate):
                called = []
                sources = ("saramin", "jobkorea", "rallit", "wanted", "jumpit")
                patterns = (
                    "https://www.saramin.co.kr/zf_user/jobs/view?rec_idx={}",
                    "https://m.jobkorea.co.kr/Recruit/GI_Read/{}",
                    "https://www.rallit.com/positions/{}/backend",
                    "https://www.wanted.co.kr/wd/{}",
                    "https://jumpit.saramin.co.kr/position/{}",
                )

                def provider(source, pattern):
                    def search(_):
                        count = 5 if source in ("saramin", "wanted") else 1
                        return [{"url": pattern.format(i), "content": ""} for i in range(1, count + 1)]

                    def search_more(_):
                        called.append(source)
                        return [{"url": pattern.format(i), "content": ""} for i in range(6, 10)]
                    return SimpleNamespace(source=source, search=search, search_more=search_more)

                def verify(url, *, today):
                    source, number = _posting_key(url)
                    company = f"{source}기업{number}"
                    if duplicate and source == "saramin" and int(number) <= 5:
                        company = "중복기업"
                    return company, "백엔드 개발자", url, today.date(), "신입", "REST API 서버 개발"

                providers = [provider(source, pattern) for source, pattern in zip(sources, patterns)]
                search = PlayMcpTavilyJobSearch(providers[0], providers[1], tuple(providers[2:]))
                result = SaraminRecommendationService(search, SimpleNamespace(verify=verify)).recommend(
                    SaraminRecommendationRequest(selected_ncs_ids=["skill-server"])
                )
                self.assertCountEqual(called, ["jobkorea", "rallit", "jumpit"] + (["saramin"] if duplicate else []))
                self.assertEqual(len(result.recommendations), 25)
                for source in sources:
                    self.assertEqual(sum(_posting_key(job.source_url)[0] == source for job in result.recommendations), 5)


if __name__ == "__main__":
    unittest.main()
