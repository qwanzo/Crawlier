import unittest
from crawlier import Crawlier

class TestCrawlier(unittest.TestCase):
    def test_init(self):
        c = Crawlier("example.com")
        self.assertEqual(c.target_domain, "example.com")

    def test_run_crawl(self):
        from crawlier import run_crawl
        logs = list(run_crawl("example.com", max_threads=1, max_depth=1))
        self.assertTrue(len(logs) > 0)

if __name__ == "__main__":
    unittest.main()
