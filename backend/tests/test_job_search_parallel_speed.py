import threading
import unittest
from types import SimpleNamespace

from app.services.saramin_recommendation import SaraminRecommendationUnavailable
from app.services.tavily_job_search import PlayMcpTavilyJobSearch


class JobSearchParallelSpeedTests(unittest.TestCase):
    def test_five_source_supplements_start_together_and_keep_partial_success(self):
        barrier = threading.Barrier(5, timeout=3)
        called = []
        lock = threading.Lock()

        def provider(source):
            def search_more(_):
                with lock:
                    called.append(source)
                barrier.wait()
                if source == "jumpit":
                    raise SaraminRecommendationUnavailable("test failure")
                return [{"url": f"https://example.com/{source}", "content": ""}]
            return SimpleNamespace(source=source, search_more=search_more)

        sources = ("saramin", "jobkorea", "rallit", "wanted", "jumpit")
        providers = [provider(source) for source in sources]
        result = PlayMcpTavilyJobSearch(providers[0], providers[1], tuple(providers[2:])).search_more([])
        self.assertCountEqual(called, sources)
        self.assertEqual(len(result), 4)
        self.assertNotIn("https://example.com/jumpit", [row["url"] for row in result])


if __name__ == "__main__":
    unittest.main()
